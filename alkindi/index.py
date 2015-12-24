
from alkindi.auth import get_user_identity
from alkindi.contexts import ApiContext


def includeme(config):
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
    # config.add_view(
    #     endpoint_view, context=ApiContext, name='endpoint',
    #     request_method='POST', renderer='json', check_csrf=True)


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
    user = get_user_identity(request)
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
