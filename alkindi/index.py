
from pyramid.httpexceptions import HTTPFound
from pyramid.security import unauthenticated_userid, forget

from alkindi.auth import (
    redirect_to_oauth2_provider, accept_oauth2_code,
    maybe_refresh_oauth2_token)


def includeme(config):
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
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
    redirect_to_oauth2_provider(request, redirect=request.url)


def oauth_callback_view(request):
    code = request.params.get('code')
    accept_oauth2_code(request, code=code)


def index_view(request):
    ensure_authenticated(request)
    return {
        'user_id': unauthenticated_userid(request),
        'username': request.session.get('username')
    }


def logout_view(request):
    forget(request)
    request.session.clear()
    url = request.route_url('index')
    return HTTPFound(location=url)
