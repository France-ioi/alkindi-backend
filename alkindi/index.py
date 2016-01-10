
from pyramid.httpexceptions import HTTPNotModified, HTTPFound
from ua_parser import user_agent_parser

from alkindi.auth import get_user_profile, reset_user_principals
from alkindi.contexts import (
    ApiContext, UserApiContext, TeamApiContext,
    WorkspaceRevisionApiContext)
from alkindi.globals import app
from alkindi.errors import ApiError, ModelError
import alkindi.views as views
from alkindi_r2_front import version as front_version


def includeme(config):
    config.add_view(model_error_view, context=ModelError, renderer='json')
    config.add_view(api_error_view, context=ApiError, renderer='json')
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
    config.add_route(
        'ancient_browser', '/ancient_browser', request_method='GET')
    config.add_view(
        ancient_browser_view, route_name='ancient_browser',
        renderer='templates/ancient_browser.mako')
    api_get(config, UserApiContext, '', read_user)
    api_post(config, UserApiContext, 'create_team', create_team)
    api_post(config, UserApiContext, 'join_team', join_team)
    api_post(config, UserApiContext, 'leave_team', leave_team)
    api_post(config, UserApiContext, 'update_team', update_team)
    api_post(config, UserApiContext, 'start_attempt', start_attempt)
    api_post(config, UserApiContext, 'cancel_attempt', cancel_attempt)
    api_get(config, UserApiContext, 'access_code', view_access_code)
    api_post(config, UserApiContext, 'access_code', enter_access_code)
    api_post(
        config, UserApiContext, 'assign_attempt_task', assign_attempt_task)
    api_post(config, UserApiContext, 'get_hint', get_hint)
    api_post(config, UserApiContext, 'reset_hints', reset_hints)
    api_post(config, UserApiContext, 'store_revision', store_revision)
    api_get(config, WorkspaceRevisionApiContext, '', read_workspace_revision)
    api_get(config, TeamApiContext, '', read_team)
    config.add_view(
        view_task, context=UserApiContext, name='task.html',
        request_method='GET', permission='read',
        renderer='templates/playfair.mako')  # XXX


def api_get(config, context, name, view):
    config.add_view(
        view, context=context, name=name,
        request_method='GET',
        permission='read', renderer='json')


def api_post(config, context, name, view):
    config.add_view(
        view, context=context, name=name,
        request_method='POST', check_csrf=True,
        permission='change', renderer='json')


def check_etag(request, etag):
    etag = str(etag)
    if etag in request.if_none_match:
        raise HTTPNotModified()
    request.response.vary = 'Cookie'
    request.response.cache_control = 'max-age=3600, private, must-revalidate'
    request.response.etag = etag


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
        'front_version': front_version,
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
        frontend_config['seed'] = views.view_user_seed(user_id)
    request.response.cache_control = 'max-age=0, private'
    return {
        'frontend_config': frontend_config
    }


def view_task(request):
    request.response.cache_control = 'max-age=0, private'
    user_id = request.context.user_id
    return views.view_user_task(user_id)


def get_api(request):
    return ApiContext(request.root)


def read_user(request):
    request.response.cache_control = 'max-age=0, private'
    user_id = request.context.user_id
    return views.view_user_seed(user_id)


def read_team(request):
    team = request.context.team
    check_etag(request, team['revision'])
    return {'team': views.view_user_team(team)}


def read_workspace_revision(request):
    revision = request.context.workspace_revision
    check_etag(request, revision['created_at'])
    return {
        'success': True,
        'workspace_revision': views.view_user_workspace_revision(revision)
    }


def create_team(request):
    """ Create a team for the context's user.
        An administrator can also perform the action on a user's behalf.
    """
    # Create the team.
    user_id = request.context.user_id
    app.model.create_team(user_id)
    app.db.commit()
    # Ensure the user gets team credentials.
    reset_user_principals(request)
    return {'success': True}


def join_team(request):
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
        team_id = app.model.find_team_by_code(code)
    if team_id is None:
        raise ApiError('unknown code')
    user = request.context.user
    # Verify that the user does not already belong to a team.
    if user['team_id'] is not None:
        raise ApiError('already in a team')
    # Add the user to the team.
    app.model.join_team(user, team_id)
    # Joining a team cancels its attempts.
    app.model.cancel_current_team_attempt(team_id)
    app.db.commit()
    # Ensure the user gets team credentials.
    reset_user_principals(request)
    return {'success': True}


def leave_team(request):
    user_id = request.context.user_id
    user = app.model.load_user(user_id)
    app.model.leave_team(user)
    # Leaving a team cancels its attempts.
    app.model.cancel_current_team_attempt(user['team_id'])
    app.db.commit()
    # Clear the user's team credentials.
    reset_user_principals(request)
    return {'success': True}


def update_team(request):
    user_id = request.context.user_id
    user = app.model.load_user(user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    # If the user is not an admin, they must be the team's creator.
    if request.by_admin:
        if user_id != app.model.get_team_creator(team_id):
            raise ApiError('not team creator')
        # The creator can only change some settings.
        allowed_keys = ['is_open']
        body = request.json_body
        settings = {key: body[key] for key in allowed_keys}
    else:
        # Admins can change all settings.
        settings = request.json_body
    app.model.update_team(team_id, settings)
    app.db.commit()
    return {'success': True}


def start_attempt(request):
    user_id = request.context.user_id
    user = app.model.load_user(user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    # Load team, team members, round.
    team = app.model.load_team(team_id)
    members = app.model.load_team_members(team_id)
    # Get the team's current attempt.
    try:
        attempt = app.model.load_team_current_attempt(team_id)
    except ModelError:
        attempt = None
    if attempt is None:
        # Use the team's round.
        round_id = team['round_id']
        round_ = app.model.load_round(round_id)
        # Check that the team is valid for the round.
        causes = views.validate_members_for_round(members, round_)
        if len(causes) != 0:
            raise ApiError('invalid team')
        # Create a training attempt.
        # The team is not locked at this time, but any change to the
        # team should cancel the attempt.
        app.model.create_attempt(round_id, team_id, members, is_training=True)
    else:
        if attempt['is_training']:
            # Current attempt is training.  Team must pass training to
            # create a timed attempt.
            if attempt['is_unsolved']:
                raise ApiError('must pass training')
        else:
            # XXX Current attempt is timed, do we allow the team to
            # start a new attempt before the time has elapsed?
            pass
        # Load the attempt's round.
        round_id = attempt['round_id']
        round_ = app.model.load_round(round_id)
        # Limit the number of timed attempts.
        n_attempts = app.model.count_team_timed_attempts(team_id)
        if n_attempts == round_['max_attempts']:
            raise ApiError('too many attempts')
        # Reset the is_current flag on the current attempt.
        app.model.set_attempt_not_current(attempt['id'])
        # Create a timed attempt.
        app.model.create_attempt(round_id, team_id, members, is_training=False)
    app.db.commit()
    return {'success': True}


def cancel_attempt(request):
    user_id = request.context.user_id
    user = app.model.load_user(user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    attempt = app.model.load_team_current_attempt(team_id)
    if attempt is None:
        raise ApiError('no attempt')
    if attempt['started_at'] is not None:
        raise ApiError('attempt already started')
    app.model.cancel_current_team_attempt(team_id)
    app.db.commit()
    return {'success': True}


def view_access_code(request):
    user_id = request.context.user_id
    code = app.model.get_current_attempt_access_code(user_id)
    if code is None:
        raise ApiError('no current attempt')
    return {'success': True, 'code': code}


def enter_access_code(request):
    user_id = request.context.user_id
    user = app.model.load_user(user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    data = request.json_body
    code = data['code']
    success = app.model.unlock_current_attempt_access_code(user_id, code)
    app.db.commit()
    if not success:
        raise ApiError('bad access code')
    return {'success': success}


def assign_attempt_task(request):
    user_id = request.context.user_id
    # The team is validated when the attempt is created, and the attempt
    # is automatically cancelled if any member joins or leaves the team.
    # It is therefore safe to assume that the team is valid.
    attempt_id = app.model.get_user_current_attempt_id(user_id)
    if attempt_id is None:
        raise ApiError('no current attempt')
    app.model.assign_attempt_task(attempt_id)
    app.db.commit()
    return {'success': True}


def get_hint(request):
    user_id = request.context.user_id
    query = request.json_body
    success = app.model.get_user_task_hint(user_id, query)
    app.db.commit()
    return {'success': success}


def reset_hints(request):
    user_id = request.context.user_id
    app.model.reset_user_task_hints(user_id)
    app.db.commit()
    return {'success': True}


def store_revision(request):
    user_id = request.context.user_id
    query = request.json_body
    state = query['state']
    title = getStr(query.get('title'))
    parent_id = getInt(query.get('parent_id'))
    revision_id = app.model.store_revision(user_id, parent_id, title, state)
    app.db.commit()
    return {'success': True, 'revision_id': revision_id}

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
    ua = ua['user_agent']
    family = ua['family']
    if family in MinimumFamilyVersion:
        major = int(ua['major'])
        if major >= MinimumFamilyVersion[family]:
            return False
    return True
