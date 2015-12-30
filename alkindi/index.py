
from alkindi.auth import get_user_identity
from alkindi.contexts import ApiContext, UserApiContext


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
    api_get(config, UserApiContext, '', read_user)
    api_post(config, UserApiContext, 'join_team', join_team)


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
    user = get_user_profile(request)
    if user is not None:
        frontend_config['user'] = {
            'username': user.get('sLogin'),
            'isSelected': False  # XXX
        }
    return {
        'frontend_config': frontend_config
    }


def get_api(request):
    return ApiContext(request.root)


def read_user(request):
    user_id = request.context.user_id
    from pyramid.security import unauthenticated_userid
    return {'user_id': user_id, 'auth_id': unauthenticated_userid(request)}


def join_team(request):
    return {}
