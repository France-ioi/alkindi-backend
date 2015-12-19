
from pyramid.httpexceptions import HTTPFound
from pyramid.security import unauthenticated_userid, forget

from alkindi.auth import (
    oauth2_provider_uri, accept_oauth2_code,
    maybe_refresh_oauth2_token)
from alkindi_r2_front import version as front_version


def includeme(config):
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
    config.add_route('login', '/login', request_method='GET')
    config.add_view(
        login_view, route_name='login', renderer='templates/login.mako')
    config.add_route('logout', '/logout', request_method='POST')
    config.add_view(logout_view, route_name='logout')
    config.add_route('oauth_callback', '/oauth/callback', request_method='GET')
    config.add_view(oauth_callback_view, route_name='oauth_callback')


def ensure_authenticated(request):
    # Refresh the access token if we have an expired one.
    maybe_refresh_oauth2_token(request)
    # Get the user id from the redis session.
    user_id = unauthenticated_userid(request)
    if user_id is not None:
        return
    raise HTTPFound(request.route_url('login', _query={
        'redirect': request.url
    }))


def oauth_callback_view(request):
    code = request.params.get('code')
    accept_oauth2_code(request, code=code)


def index_view(request):
    ensure_authenticated(request)
    csrf_token = request.session.get_csrf_token()
    assets_template = request.static_url('alkindi_r2_front:assets/{}') \
        .replace('%7B%7D', '{}')
    return {
        'user_id': unauthenticated_userid(request),
        'username': request.session.get('username'),
        'csrf_token': csrf_token,
        'frontend_config': {
            'user': {
                'username': request.session.get('username'),
                'isSelected': False
            },
            'assets_template': assets_template,
            'logout_url': request.route_url('logout')
        }
    }


def login_view(request):
    redirect = request.params.get('redirect')
    return {
        'authenticate_uri': oauth2_provider_uri(request, redirect=redirect),
        'error': request.params.get('error'),
        'error_code': request.params.get('code'),
        'error_description': request.params.get('error_description'),
    }


def logout_view(request):
    forget(request)
    request.session.clear()
    url = request.route_url('index')
    return HTTPFound(location=url)
