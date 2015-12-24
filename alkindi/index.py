
from pyramid.httpexceptions import HTTPFound, HTTPSeeOther
from pyramid.security import unauthenticated_userid, forget

from alkindi.auth import (
    oauth2_provider_uri, accept_oauth2_code,
    maybe_refresh_oauth2_token)
from alkindi.contexts import ApiContext


def includeme(config):
    config.add_route('index', '/', request_method='GET')
    config.add_view(
        index_view, route_name='index', renderer='templates/index.mako')
    config.add_route('login', '/login', request_method='GET')
    config.add_view(login_view, route_name='login')
    config.add_view(
        logout_view, context=ApiContext, name='logout',
        request_method='POST', renderer='json', check_csrf=True)
    config.add_route('oauth_callback', '/oauth/callback', request_method='GET')
    config.add_view(
        oauth_callback_view, route_name='oauth_callback',
        renderer='templates/after_login.mako')


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


def index_view(request):
    # Prepare the frontend's config for injection as JSON in a script tag.
    assets_template = request.static_url('alkindi_r2_front:assets/{}') \
        .replace('%7B%7D', '{}')
    csrf_token = request.session.get_csrf_token()
    frontend_config = {
        'assets_template': assets_template,
        'csrf_token': csrf_token,
        'api_url': request.resource_url(get_api(request)),
        'login_url': request.route_url('login')
    }
    # Add info about the logged-in user to the frontend config.
    if unauthenticated_userid(request) is not None:
        user = maybe_refresh_oauth2_token(request)
        if user is not None:
            frontend_config['user'] = {
                'username': user.get('sLogin'),
                'isSelected': False  # XXX
            }
    return {
        'frontend_config': frontend_config
    }


def login_view(request):
    # Opening this view in a new window will take the user to the
    # identity provider (IdP) for authentication.  The IdP will
    # eventually redirect the user to the OAuth2 callback view below.
    raise HTTPSeeOther(oauth2_provider_uri(request))


def oauth_callback_view(request):
    # This view handles the outcome of authentication performed by the
    # identity provider.
    error = request.params.get('error')
    if error is not None:
        return {
            'error': error,
            'error_description': request.params.get('error_description')
        }
    code = request.params.get('code')
    user = accept_oauth2_code(request, code=code)
    # The template posts the user object (encoded as JSON) to the parent
    # window, causing the frontend to update its state.
    return {
        'user': user,
        'origin': request.headers.get('Origin')
    }


def logout_view(request):
    forget(request)
    request.session.clear()
    return {}


def get_api(request):
    return ApiContext(request.root)
