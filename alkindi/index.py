
from datetime import datetime, timedelta
import requests

from pyramid.exceptions import PredicateMismatch
from pyramid.httpexceptions import HTTPFound, HTTPForbidden, HTTPNotFound
from pyramid.session import check_csrf_token
from ua_parser import user_agent_parser

from alkindi.auth import (
    get_user_profile, get_oauth2_token, reset_user_principals)
from alkindi.contexts import (
    ApiContext, UserApiContext, TeamApiContext, AttemptApiContext,
    UserAttemptApiContext, ParticipationRoundTaskApiContext,
    ParticipationApiContext)
from alkindi.errors import ApiError, ApplicationError
import alkindi.views as views
from alkindi.globals import app

from alkindi.model.users import (
    load_user, update_user, get_user_team_id, find_user_by_username)
from alkindi.model.teams import (
    find_team_by_code, update_team)
from alkindi.model.team_members import (
    create_user_team, join_team, leave_team, get_team_creator)
from alkindi.model.rounds import find_round_ids_with_badges, load_round
from alkindi.model.participations import (
    load_participation, create_participation,
    get_team_latest_participation_id,
    mark_participation_code_entered)
from alkindi.model.attempts import (
    load_attempt, create_attempt, reset_to_training_attempt)
from alkindi.model.workspace_revisions import (
    store_revision)
from alkindi.model.task_instances import assign_task_instance
from alkindi.model.hints import (
    get_task_instance_hint, reset_task_instance_hints)
from alkindi.model.access_codes import (
    get_access_code, clear_access_codes, unlock_access_code)
from alkindi.model.answers import (
    grade_answer)


def includeme(config):
    config.add_view(
        application_error_view, context=ApplicationError, renderer='json')
    config.add_view(not_found_view, context=HTTPNotFound)

    config.include('alkindi.legacy')

    config.add_route('start', '/start', request_method='GET')
    config.add_view(
        start_view, route_name='start', renderer='templates/start.mako')

    api_post(
        config, ApiContext, 'refresh', refresh_action, permission='access')

    # Team (permission='change')
    api_post(config, UserApiContext, 'add_badge', add_badge_action)
    api_post(config, UserApiContext, 'create_team', create_team_action)
    api_post(config, UserApiContext, 'join_team', join_team_action)
    api_post(config, UserApiContext, 'leave_team', leave_team_action)
    api_post(config, UserApiContext, 'update_team', update_team_action)

    # Attempts
    api_post(
        config, ParticipationRoundTaskApiContext, 'create_attempt',
        create_attempt_action, permission='create_attempt')
    api_post(
        config, AttemptApiContext, 'start',
        start_attempt_action, permission='start')
    api_post(
        config, AttemptApiContext,
        'reset_to_training', reset_team_to_training_action)

    # api_post(config, UserApiContext, 'cancel_attempt', cancel_attempt_action)
    # api_post(config, UserApiContext, 'access_code', enter_access_code_action)

    # Hints
    api_post(
        config, AttemptApiContext,
        'get_hint', get_hint_action, permission='get_hint')
    api_post(
        config, AttemptApiContext,
        'reset_hints', reset_hints_action, permission='reset_hints')

    # Answers
    api_post(
        config, UserAttemptApiContext,
        'answer', submit_user_attempt_answer_action, permission='answer')

    # Revisions
    api_post(
        config, UserAttemptApiContext,
        'store_revision', store_revision_action, permission='store_revision')

    # Participations
    api_post(
        config, ParticipationApiContext,
        'enter_code', enter_participation_code_action, permission='access')


    # Deprecated routes and views -- frontend stuff is planned to be
    # completely separated from the backend.
    config.add_route(
        'ancient_browser', '/ancient_browser', request_method='GET')
    config.add_view(
        ancient_browser_view, route_name='ancient_browser',
        renderer='templates/ancient_browser.mako')


def not_found_view(error, request):
    if request.method == 'POST' and isinstance(error, PredicateMismatch):
        # Return a 403 error on CSRF token mismatch.
        if not check_csrf_token(request, raises=False):
            return HTTPForbidden()
    return error


def api_post(config, context, name, view, permission='change'):
    config.add_view(
        view, context=context, name=name,
        request_method='POST', check_csrf=True,
        permission=permission, renderer='json')


def application_error_view(error, request):
    # This view handles alkindi.errors.ApplicationError.
    request.db.rollback()
    return {'success': False, 'error': str(error), 'source': 'model'}


def ancient_browser_view(request):
    if not is_ancient_browser(request):
        raise HTTPFound(request.route_url('index'))
    ua = request.headers['User-Agent']
    return user_agent_parser.Parse(ua)


def start_view(request):
    # Redirect ancient browsers (detection is performed by the reverse
    # proxy).
    # if 'ancient' not in request.params and is_ancient_browser(request):
    #    raise HTTPFound(request.route_url('ancient_browser'))
    # Prepare the frontend's config for injection as JSON in a script tag.
    csrf_token = request.session.get_csrf_token()
    override = get_user_context(request, request.params)
    frontend_config = {
        'csrf_token': csrf_token,
        'backend_url': request.resource_url(request.root),
        'login_url': request.route_url('login'),
        'logout_url': request.route_url('logout'),
        'override': override
    }
    # Add info about the logged-in user (if any) to the frontend config.
    try:
        frontend_config['seed'] = views.view_requesting_user(request.db, **override)
    except ApplicationError as error:
        frontend_config['seed'] = {'error': str(error)}
    request.response.cache_control = 'max-age=0, private'
    request.response.content_type = 'application/javascript'
    return {
        'frontend_config': frontend_config
    }


def refresh_action(request):
    json_request = request.json_body
    kwargs = get_user_context(request, json_request)
    view = views.view_requesting_user(request.db, **kwargs)
    # print("\033[91mrequest\033[0m {}".format(json_request))
    attempt_id = view.get('current_attempt_id')
    if attempt_id is not None:
        # TODO: if json_request.get('attempt_id') != attempt_id: ...
        # Access code request.
        if json_request.get('access_code'):
            access_code = get_access_code(request.db, attempt_id, view.get(user_id))
            for attempt in view['attempts']:
                if attempt.get('id') == attempt_id:
                    attempt['access_code'] = access_code
        # History request.
        if json_request.get('history'):
            views.add_revisions(request.db, view, attempt_id)
        # Answers request.
        if json_request.get('answers'):
            views.add_answers(request.db, view, attempt_id)
    view['success'] = True
    return view


def get_user_context(request, params):
    user_id = request.authenticated_userid
    result = {
        'user_id': user_id
    }
    if 'g:admin' in request.effective_principals:
        result['is_admin'] = True
        if params.get('user') is not None:
            result['user_id'] = find_user_by_username(
                request.db, params['user'])
        if params.get('user_id') is not None:
            result['user_id'] = int(params['user_id'])
    if 'participation_id' in params:
        result['participation_id'] = \
            int(params['participation_id'])
    if 'attempt_id' in params:
        result['attempt_id'] = int(params['attempt_id'])
    return result


def reset_team_to_training_action(request):
    team_id = request.context.team_id
    participation_id = get_team_latest_participation_id(request.db, team_id)
    round_task_id = None
    raise ApiError('XXX missing round_task_id')
    reset_to_training_attempt(
        request.db, participation_id, round_task_id, now=datetime.utcnow())
    return {'success': True}


def add_badge_action(request):
    data = request.json_body
    user_id = request.context.user_id
    user = load_user(request.db, user_id)
    foreign_id = user['foreign_id']
    access_token = get_oauth2_token(request, refresh=True)
    params = {
        'badgeUrl': app['requested_badge'],
        'idUser': foreign_id,
        'qualCode': data.get('code')
    }
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(access_token)
    }
    req = requests.post(
        app['add_badge_uri'],
        headers=headers, data=params,
        verify='/etc/ssl/certs/ca-certificates.crt')
    req.raise_for_status()
    result = req.json()
    print("\033[91mresult\033[0m {}".format(result))
    success = result.get('success')
    if not success:
        return {
            'success': False,
            'profileUpdated': False,
            'error': result.get('error', 'undefined')
        }
    profileUpdated = False
    profile = get_user_profile(request, foreign_id)
    if profile is not None:
        update_user(request.db, user['id'], profile)
        profileUpdated = True
    return {
        'success': True,
        'profileUpdated': profileUpdated
    }


def create_team_action(request):
    """ Create a team for the context's user.
        An administrator can also perform the action on a user's behalf.
    """
    # Create the team.
    now = datetime.utcnow()
    user_id = request.context.user_id
    user = load_user(request.db, user_id)
    # Select a round based on the user's badges.
    round_ids = find_round_ids_with_badges(request.db, user['badges'], now)
    if len(round_ids) == 0:
        # The user does not have access to any open round.
        raise ApiError('not qualified for any open round')
    if len(round_ids) > 1:
        # XXX The case where a user has badges for multiple open rounds
        # is currently handled by picking the first one, which is the
        # one that has the greatest id.  This is unsatisfactory.
        pass
    round_id = round_ids[0]
    round_ = load_round(request.db, round_id, now)
    if not round_['is_registration_open']:
        raise ApiError('registration is closed')
    # Create the team.
    team_id = create_user_team(request.db, user_id, now)
    # Create a participation.
    create_participation(request.db, team_id, round_id, now=now)
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
        team_id = find_team_by_code(request.db, code)
    if team_id is None:
        raise ApiError('unknown team code')
    user_id = request.context.user_id
    # Add the user to the team.
    join_team(request.db, user_id, team_id, now=datetime.utcnow())
    # Ensure the user gets team credentials.
    reset_user_principals(request)
    return {'success': True}


def leave_team_action(request):
    now = datetime.utcnow()
    user_id = request.context.user_id
    team_id = get_user_team_id(request.db, user_id)
    # Remove the user from their current team.
    leave_team(request.db, user_id=user_id, team_id=team_id, now=now)
    # Clear the user's access codes in all of the team's attempts.
    clear_access_codes(request.db, user_id=user_id, team_id=team_id)
    # Clear the user's team credentials.
    reset_user_principals(request)
    return {'success': True}


def update_team_action(request):
    user_id = request.context.user_id
    user = load_user(request.db, user_id)
    team_id = user['team_id']
    if team_id is None:
        raise ApiError('no team')
    # If the user is not an admin, they must be the team's creator.
    if request.by_admin:
        if user_id != get_team_creator(request.db, team_id):
            raise ApiError('not team creator')
        # The creator can only change some settings.
        allowed_keys = ['is_open']
        body = request.json_body
        settings = {key: body[key] for key in allowed_keys}
    else:
        # Admins can change all settings.
        settings = request.json_body
    update_team(request.db, team_id, settings)
    return {'success': True}


def create_attempt_action(request):
    participation_id = request.context.participation['id']
    round_task_id = request.context.round_task['id']
    create_attempt(
        request.db, participation_id, round_task_id,
        now=datetime.utcnow())
    return {'success': True}


# Disabled:
#
# def cancel_attempt_action(request):
#     user_id = request.context.user_id
#     team_id = get_user_team_id(request.db, user_id)
#     participation_id = get_team_latest_participation_id(request.db, team_id)
#     if participation_id is None:
#         raise ApiError('no current participation')
#     attempt_id = get_current_attempt_id(request.db, participation_id)
#     if attempt_id is None:
#         raise ApiError('no current attempt')
#     cancel_attempt(request.db, attempt_id)
#     reset_to_training_attempt(
#         request.db, participation_id, now=datetime.utcnow())
#     return {'success': True}


# Disabled:
#
# def enter_access_code_action(request):
#     data = request.json_body
#     code = data['code']
#     user_id = request.context.user_id
#     participation_id = get_user_latest_participation_id(request.db, user_id)
#     if participation_id is None:
#         raise ApiError('no current participation')
#     attempt_id = get_current_attempt_id(request.db, participation_id)
#     if attempt_id is None:
#         raise ApiError('no current attempt')
#     success = unlock_access_code(request.db, attempt_id, user_id, code)
#     if not success:
#         raise ApiError('unknown access code')
#     return {'success': success}


def start_attempt_action(request):
    attempt_id = request.context.attempt_id
    # This will fail if the team is invalid.
    assign_task_instance(request.db, attempt_id, now=datetime.utcnow())
    return {'success': True}


def get_hint_action(request):
    now = datetime.utcnow()
    attempt_id = request.context.attempt_id
    query = request.json_body
    success = get_task_instance_hint(request.db, attempt_id, query, now=now)
    return {'success': success}


def reset_hints_action(request):
    attempt_id = request.context.attempt_id
    reset_task_instance_hints(request.db, attempt_id)
    return {'success': True}


def store_revision_action(request):
    user_id = request.context.user_id
    attempt_id = request.context.attempt_id
    query = request.json_body
    revision_id = store_revision_query(request.db, user_id, attempt_id, query)
    return {'success': True, 'revision_id': revision_id}


def submit_user_attempt_answer_action(request):
    now = datetime.utcnow()
    attempt_id = request.context.attempt_id
    attempt = load_attempt(request.db, attempt_id)
    participation = load_participation(request.db, attempt['participation_id'])
    round_ = load_round(request.db, participation['round_id'])
    if round_['status'] != 'open':
        return {'success': False, 'error': 'round not open'}
    if participation['started_at'] is not None and round_['duration'] is not None:
        duration = timedelta(minutes=round_['duration'])
        deadline = participation['started_at'] + duration
        if now > deadline:
            return {'success': False, 'error': 'past deadline'}
    submitter_id = request.context.user_id
    query = request.json_body
    answer = query['answer']
    revision_id = None
    if 'data' in query:
        revision = query['data']
        revision_id = store_revision_query(
            request.db, submitter_id, attempt_id, revision)
    answer, feedback = grade_answer(
        request.db, attempt_id, submitter_id, revision_id, answer, now=now)
    return {
        'success': True,
        'answer_id': answer['id'],
        'revision_id': revision_id,
        'feedback': feedback,
        'score': answer['score']
    }


def enter_participation_code_action(request):
    now = datetime.utcnow()
    participation = request.context.participation
    query = request.json_body
    code = query['code']
    if code is None:
        return {'error': 'missing participation code'}
    if code != participation['access_code']:
        return {'error': 'invalid participation code'}
    mark_participation_code_entered(request.db, participation['id'], now)
    request.db.commit()
    return {'success': True,}


def store_revision_query(db, user_id, attempt_id, query):
    workspace_id = getStr(query.get('workspace_id'))
    parent_id = getInt(query.get('parent_id'))
    title = getStr(query.get('title'))
    state = query['state']
    return store_revision(
        db, user_id, attempt_id,
        workspace_id, parent_id, title, state, now=datetime.utcnow())


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
