
from pyramid.httpexceptions import HTTPNotModified

from alkindi.auth import get_user_profile, reset_user_principals
from alkindi.contexts import (
    ApiContext, UserApiContext, TeamApiContext, ADMIN_GROUP
)
from alkindi.globals import app
from alkindi.model import ModelError
import alkindi.views as views


def includeme(config):
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
    config.add_view(model_error_view, context=ModelError, renderer='json')
    api_get(config, UserApiContext, '', read_user)
    api_post(config, UserApiContext, 'create_team', create_team)
    api_post(config, UserApiContext, 'join_team', join_team)
    api_post(config, UserApiContext, 'leave_team', leave_team)
    api_post(config, UserApiContext, 'update_team', update_team)
    api_get(config, TeamApiContext, '', read_team)


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
    # This view handles alkindi.model.ModelError.
    return {'error': str(error), 'source': 'model'}


def index_view(request):
    # Prepare the frontend's config for injection as JSON in a script tag.
    assets_template = request.static_url('alkindi_r2_front:assets/{}') \
        .replace('%7B%7D', '{}')
    csrf_token = request.session.get_csrf_token()
    frontend_config = {
        'assets_template': assets_template,
        'csrf_token': csrf_token,
        'api_url': request.resource_url(get_api(request)),
        'login_url': request.route_url('login'),
        'logout_url': request.route_url('logout')
    }
    # Add info about the logged-in user (if any) to the frontend config.
    user_id = request.authenticated_userid
    if user_id is not None:
        frontend_config['seed'] = views.view_user_seed(user_id)
    return {
        'frontend_config': frontend_config
    }


def get_api(request):
    return ApiContext(request.root)


def read_user(request):
    user_id = request.context.user_id
    return views.view_user_seed(user_id)


def read_team(request):
    team = request.context.team
    check_etag(request, team['revision'])
    return {'team': views.view_user_team(team)}


def create_team(request):
    """ Create a team for the context's user.
        An administrator can also perform the action on a user's behalf.
    """
    # Refresh the user profile in case their badges changed.
    update_user_profile(request, request.context.user_id)
    app.db.commit()
    # Create the team.
    user_id = request.context.user_id
    success = app.model.create_team(user_id)
    if success:
        app.db.commit()
        # Ensure the user gets team credentials.
        reset_user_principals(request)
    return {'success': success}


def join_team(request):
    """ Add the context's user to an existing team.
        An administrator can also perform the action on a user's behalf.
    """
    # Refresh the user profile in case their badges changed.
    update_user_profile(request, request.context.user_id)
    app.db.commit()
    # Find the team corresponding to the provided code.
    data = request.json_body
    team_id = None
    if ADMIN_GROUP in request.effective_principals:
        # Accept a team_id if the authenticated user is an admin.
        if 'team_id' in data:
            team_id = data['team_id']
    if team_id is None:
        code = data['code']
        team_id = app.model.find_team_by_code(code)
    if team_id is None:
        return {'success': False}
    # Add the user to the team.
    user = request.context.user
    success = app.model.join_team(user, team_id)
    if success:
        app.db.commit()
        # Ensure the user gets team credentials.
        reset_user_principals(request)
    return {'success': success}


def leave_team(request):
    user_id = request.context.user_id
    result = app.model.leave_team(user_id)
    app.db.commit()
    # Clear the user's team credentials.
    reset_user_principals(request)
    return {'success': result}


def update_team(request):
    user_id = request.context.user_id
    user = app.model.load_user(user_id)
    team_id = user['team_id']
    if team_id is None:
        return {'error': 'no team'}
    # If the user is not an admin, they must be the team's creator.
    if ADMIN_GROUP not in request.effective_principals:
        if user_id != app.model.get_team_creator(team_id):
            return {'error': 'permission denied (not team creator)'}
    app.model.update_team(team_id, request.json_body)
    app.db.commit()
    return {'success': True}


def update_user_profile(request, user_id=None):
    profile = get_user_profile(request.session, user_id)
    if profile is None:
        raise RuntimeError("failed to get the user's profile")
    app.model.update_user(user_id, profile)
