

from datetime import datetime
import requests
import json

from pyramid.exceptions import PredicateMismatch
from pyramid.httpexceptions import HTTPFound, HTTPForbidden, HTTPNotFound
from pyramid.request import Request
from pyramid.session import check_csrf_token
from ua_parser import user_agent_parser

from alkindi.auth import get_user_profile, reset_user_principals
from alkindi.contexts import (
    ApiContext, UserApiContext, TeamApiContext, UserAttemptApiContext)
from alkindi.globals import app
from alkindi.errors import ApiError, ModelError
import alkindi.views as views
from alkindi_r2_front import version as front_version

from alkindi.model.users import (
    load_user, update_user, get_user_team_id)
from alkindi.model.teams import (
    create_team, find_team_by_code, update_team)
from alkindi.model.team_members import (
    join_team, leave_team, get_team_creator)
from alkindi.model.attempts import (
    get_user_current_attempt_id, start_attempt, cancel_attempt,
    reset_team_to_training_attempt)
from alkindi.model.tasks import assign_task
from alkindi.model.access_codes import (
    get_access_code, clear_access_codes, unlock_access_code)


def includeme(config):
    config.add_view(model_error_view, context=ModelError, renderer='json')
    config.add_view(api_error_view, context=ApiError, renderer='json')
    config.add_view(not_found_view, context=HTTPNotFound)

    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')

    config.add_route(
        'ancient_browser', '/ancient_browser', request_method='GET')
    config.add_view(
        ancient_browser_view, route_name='ancient_browser',
        renderer='templates/ancient_browser.mako')

    config.include('alkindi.legacy')

    api_post(config, UserApiContext, '', refresh_action)
    api_post(config, UserApiContext, 'qualify', qualify_user_action)
    api_post(config, UserApiContext, 'create_team', create_team_action)
    api_post(config, UserApiContext, 'join_team', join_team_action)
    api_post(config, UserApiContext, 'leave_team', leave_team_action)
    api_post(config, UserApiContext, 'update_team', update_team_action)
    api_post(config, UserApiContext, 'start_attempt', start_attempt_action)
    api_post(config, UserApiContext, 'cancel_attempt', cancel_attempt_action)
    api_post(config, UserApiContext, 'access_code', enter_access_code_action)
    api_post(config, UserApiContext, 'assign_attempt_task', assign_attempt_task_action)
    api_post(config, UserApiContext, 'get_hint', get_hint_action)
    api_post(config, UserApiContext, 'reset_hints', reset_hints_action)
    api_post(config, UserApiContext, 'store_revision', store_revision_action)
    api_post(config, TeamApiContext, 'reset_to_training', reset_team_to_training_action)
    api_post(config, UserAttemptApiContext, 'answers', submit_user_attempt_answer_action)

    # XXX playfair
    config.add_view(
        user_task_view, context=UserApiContext, name='task.html',
        request_method='GET', permission='read',
        renderer='templates/playfair.mako')


def not_found_view(error, request):
    if request.method == 'POST' and isinstance(error, PredicateMismatch):
        # Return a 403 error on CSRF token mismatch.
        if not check_csrf_token(request, raises=False):
            return HTTPForbidden()
    return error


def get_api(request):
    return ApiContext(request.root)


def api_post(config, context, name, view):
    config.add_view(
        view, context=context, name=name,
        request_method='POST', check_csrf=True,
        permission='change', renderer='json')


def model_error_view(error, request):
    # This view handles alkindi.errors.ModelError.
    return {'success': False, 'error': str(error), 'source': 'model'}


def api_error_view(error, request):
    # This view handles alkindi.errors.ApiError.
    return {'success': False, 'error': str(error), 'source': 'API'}


def ancient_browser_view(request):
    if not is_ancient_browser(request):
        raise HTTPFound(request.route_url('index'))
    ua = request.headers['User-Agent']
    return user_agent_parser.Parse(ua)


def index_view(request):
    # Redirect ancient browsers (detection is performed by the reverse
    # proxy).
    if 'ancient' not in request.params and is_ancient_browser(request):
        raise HTTPFound(request.route_url('ancient_browser'))
    # Prepare the frontend's config for injection as JSON in a script tag.
    assets_template = request.static_url('alkindi_r2_front:assets/{}') \
        .replace('%7B%7D', '{}')
    csrf_token = request.session.get_csrf_token()
    frontend_config = {
        'nocdn': 'nocdn' in request.params,
        'frontend_version': front_version,
        'assets_template': assets_template,
        'csrf_token': csrf_token,
        'api_url': request.resource_url(get_api(request)),
        'login_url': request.route_url('login'),
        'logout_url': request.route_url('logout')
    }
    user_id = request.authenticated_userid
    if 'g:admin' in request.effective_principals:
        if 'user_id' in request.params:
            user_id = int(request.params['user_id'])
    # Add info about the logged-in user (if any) to the frontend config.
    if user_id is not None:
        frontend_config['seed'] = views.view_requesting_user(app.db, user_id)
    request.response.cache_control = 'max-age=0, private'
    return {
        'frontend_config': frontend_config
    }


def internal_request_view(request, path):
    subreq = Request.blank(path)
    return request.invoke_subrequest(subreq)


def refresh_action(request):
    user_id = request.context.user_id
    json_request = request.json_body
    view = views.view_requesting_user(app.db, user_id)
    # print("\033[91mrequest\033[0m {}".format(json_request))
    attempt_id = view.get('current_attempt_id')
    if attempt_id is not None:
        # TODO: if json_request.get('attempt_id') != attempt_id: ...
        # Access code request.
        if json_request.get('access_code'):
            access_code = get_access_code(app.db, attempt_id, user_id)
            for attempt in view['attempts']:
                if attempt.get('id') == attempt_id:
                    attempt['access_code'] = access_code
        # History request.
        if json_request.get('history'):
            views.add_revisions(app.db, view, attempt_id)
        # Answers request.
        if json_request.get('answers'):
            views.add_answers(app.db, view, attempt_id)
    view['success'] = True
    return view


def user_task_view(request):
    request.response.cache_control = 'max-age=0, private'
    user_id = request.context.user_id
    return views.view_user_task(app.db, user_id)


def user_view(request):
    request.response.cache_control = 'max-age=0, private'
    user_id = request.context.user_id
    return views.view_user_seed(user_id)


def reset_team_to_training_action(request):
    team_id = request.context.team_id
    reset_team_to_training_attempt(app.db, team_id, now=datetime.utcnow())
    app.db.commit()
    return {'success': True}


def qualify_user_action(request):
    user_id = request.context.user_id
    user = load_user(app.db, user_id)
    foreign_id = user['foreign_id']
    data = request.json_body
    url = 'http://www.france-ioi.org/alkindi/apiQualificationAlkindi.php'
    payload = {
        'userID': foreign_id,
        'qualificationCode': data.get('code')
    }
    headers = {'Accept': 'application/json'}
    req = requests.post(url, data=payload, headers=headers)
    req.raise_for_status()
    try:
        body = json.loads(req.text)
    except:
        body = {}
    codeStatus = body.get('codeStatus')
    userIDStatus = body.get('userIDStatus')
    profileUpdated = False
    if codeStatus == 'registered' and userIDStatus == 'registered':
        profile = get_user_profile(request, foreign_id)
        if profile is not None:
            update_user(app.db, user['id'], profile)
            app.db.commit()
            profileUpdated = True
    return {
        'success': True,
        'codeStatus': codeStatus,
        'userIDStatus': userIDStatus,
        'profileUpdated': profileUpdated
    }


def create_team_action(request):
    """ Create a team for the context's user.
        An administrator can also perform the action on a user's behalf.
    """
    # Create the team.
    now = datetime.utcnow()
    user_id = request.context.user_id
    create_team(user_id, now)
    app.db.commit()
    # Ensure the user gets team credentials.
    reset_user_principals(request)
    return {'success': True}


def join_team_action(request):
    """ Add the context's user to an existing team.
        An administrator can also perform the action on a user's behalf.
    """
    # Find the team corresponding to the provided code.
    data = request.json_body
    team_id = None
    if request.by_admin:
        # Accept a team_id if the authenticated user is an admin.
        if 'team_id' in data:
            team_id = data['team_id']
    if team_id is None:
        code = data['code']
        team_id = find_team_by_code(app.db, code)
    if team_id is None:
        raise ApiError('unknown team code')
    user_id = request.context.user_id
    # Add the user to the team.
    join_team(app.db, user_id, team_id, now=datetime.utcnow())
    app.db.commit()
    # Ensure the user gets team credentials.
    reset_user_principals(request)
    return {'success': True}


def leave_team_action(request):
    user_id = request.context.user_id
    team_id = get_user_team_id(app.db, user_id)
    # Remove the user from their current team.
    leave_team(app.db, user_id=user_id, team_id=team_id)
    # Clear the user's access codes in all of the team's attempts.
    clear_access_codes(app.db, user_id=user_id, team_id=team_id)
    app.db.commit()
    # Clear the user's team credentials.
    reset_user_principals(request)
    return {'success': True}


def update_team_action(request):
    user_id = request.context.user_id
    user = load_user(app.db, user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    # If the user is not an admin, they must be the team's creator.
    if request.by_admin:
        if user_id != get_team_creator(app.db, team_id):
            raise ApiError('not team creator')
        # The creator can only change some settings.
        allowed_keys = ['is_open']
        body = request.json_body
        settings = {key: body[key] for key in allowed_keys}
    else:
        # Admins can change all settings.
        settings = request.json_body
    update_team(app.db, team_id, settings)
    app.db.commit()
    return {'success': True}


def start_attempt_action(request):
    user_id = request.context.user_id
    user = load_user(app.db, user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    start_attempt(app.db, team_id, now=datetime.utcnow())
    app.db.commit()
    return {'success': True}


def cancel_attempt_action(request):
    user_id = request.context.user_id
    team_id = get_user_team_id(app.db, user_id)
    attempt_id = get_user_current_attempt_id(app.db, user_id)
    if attempt_id is None:
        raise ApiError('no current attempt')
    cancel_attempt(app.db, attempt_id)
    reset_team_to_training_attempt(app.db, team_id, now=datetime.utcnow())
    app.db.commit()
    return {'success': True}


def enter_access_code_action(request):
    data = request.json_body
    code = data['code']
    user_id = request.context.user_id
    attempt_id = get_user_current_attempt_id(app.db, user_id)
    if attempt_id is None:
        raise ApiError('no current attempt')
    success = unlock_access_code(app.db, attempt_id, user_id, code)
    app.db.commit()
    if not success:
        raise ApiError('unknown access code')
    return {'success': success}


def assign_attempt_task_action(request):
    user_id = request.context.user_id
    attempt_id = get_user_current_attempt_id(app.db, user_id)
    if attempt_id is None:
        raise ApiError('no current attempt')
    # This will fail if the team is invalid.
    assign_task(app.db, attempt_id, now=datetime.utcnow())
    app.db.commit()
    return {'success': True}


def get_hint_action(request):
    user_id = request.context.user_id
    query = request.json_body
    success = get_user_task_hint(app.db, user_id, query)
    app.db.commit()
    return {'success': success}


def reset_hints_action(request):
    user_id = request.context.user_id
    reset_user_task_hints(app.db, user_id)
    app.db.commit()
    return {'success': True}


def store_revision_action(request):
    user_id = request.context.user_id
    query = request.json_body
    state = query['state']
    title = getStr(query.get('title'))
    workspace_id = getStr(query.get('workspace_id'))
    parent_id = getInt(query.get('parent_id'))
    revision_id = store_revision(
        app.db, user_id, parent_id, title, state,
        workspace_id=workspace_id)
    app.db.commit()
    return {'success': True, 'revision_id': revision_id}


def submit_user_attempt_answer_action(request):
    attempt_id = request.context.attempt_id
    submitter_id = request.context.user_id
    answer = grade_answer(
        app.db, attempt_id, submitter_id, request.json_body,
        now=datetime.utcnow())
    answer
    app.db.commit()
    return {
        'success': True, 'answer_id': answer['id'],
        'feedback': json.loads(answer['grading'])['feedback']
    }


def getInt(input, defaultValue=None):
    if input is None:
        return defaultValue
    return int(input)


def getStr(input, defaultValue=None):
    if input is None:
        return defaultValue
    return str(input)


MinimumFamilyVersion = {
    'Chrome':    30,
    'Chromium':  30,
    'Firefox':   30,
    'IE':         9,
    'Edge':      13,
    'Iceweasel': 38,
    'Safari':     8,
    'Opera':     34,
}


def is_ancient_browser(request):
    ua = request.headers.get('User-Agent')
    if ua is None:
        return True
    ua = user_agent_parser.Parse(ua)
    ua = ua.get('user_agent')
    if ua is None:
        return True
    family = ua.get('family')
    if family in MinimumFamilyVersion:
        major = int(ua['major'])
        if major >= MinimumFamilyVersion[family]:
            return False
    return True
