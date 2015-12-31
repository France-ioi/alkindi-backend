
from alkindi.auth import get_user_profile
from alkindi.contexts import ApiContext, UserApiContext, ADMIN_GROUP
from alkindi.globals import app
from alkindi.model import InputError


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


def includeme(config):
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
    config.add_view(input_error_view, context=InputError, renderer='json')
    api_get(config, UserApiContext, '', read_user)
    api_post(config, UserApiContext, 'create_team', create_team)
    api_post(config, UserApiContext, 'join_team', join_team)
    api_post(config, UserApiContext, 'leave_team', leave_team)


def input_error_view(error, request):
    # This view handles alkindi.model.InputError.
    return {'error': str(error)}


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
    profile = get_user_profile(request)
    if profile is not None:
        user_id = app.model.find_user(profile['id'])
        if user_id is not None:
            badges = profile['badges']
            frontend_config['user'] = app.model.view_user(user_id, badges)
    return {
        'frontend_config': frontend_config
    }


def get_api(request):
    return ApiContext(request.root)


def read_user(request):
    user_id = request.context.user_id
    return app.model.view_user(user_id)


def create_team(request):
    """ Create a team for the context's user.
        An administrator can also perform the action for a user.
    """
    # Get the user's foreign_id to query the profile.
    user_id = request.context.user_id
    foreign_id = app.model.get_user_foreign_id(user_id)
    # Get the user's badges from their profile.
    profile = get_user_profile(request, user_id=foreign_id)
    if profile is None:
        return {'error': 'failed to get profile'}
    badges = profile['badges']
    # Create the team.
    result = app.model.create_team(user_id, badges)
    app.db.commit()
    return {'success': result}


def join_team(request):
    """ Add the context's user to an existing team.
        An administrator can also perform the action for a user.
    """
    # Find the team corresponding to the provided code.
    data = request.json_body
    team_id = None
    if ADMIN_GROUP in request.effective_principals:
        # Accept a team_id if the authenticated user is an admin.
        if 'team_id' in data:
            team_id = data['team_id']
    if team_id is None:
        code = data['code']
        team_id = app.model.get_team_id_by_code(code)
    if team_id is None:
        return False
    # Get the user's foreign_id to query the profile.
    user_id = request.context.user_id
    foreign_id = app.model.get_user_foreign_id(user_id)
    # Get the user's badges from their profile.
    profile = get_user_profile(request, user_id=foreign_id)
    if profile is None:
        return {'error': 'failed to get profile'}
    badges = profile['badges']
    # Add the user to the team.
    result = app.model.join_team(user_id, team_id, badges)
    app.db.commit()
    return {'success': result}


def leave_team(request):
    user_id = request.context.user_id
    result = app.model.leave_team(user_id)
    app.db.commit()
    return {'success': result}
