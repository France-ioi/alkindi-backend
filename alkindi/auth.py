
from datetime import datetime
import time
import uuid

from oauthlib import oauth2
import requests
from pyramid.httpexceptions import HTTPSeeOther
from pyramid.security import remember, forget

from alkindi.globals import app


#
# Pyramid routes and views
#

def includeme(config):
    config.add_route('login', '/login', request_method='GET')
    config.add_view(login_view, route_name='login')
    config.add_route('logout', '/logout', request_method='GET')
    config.add_view(
        logout_view, route_name='logout',
        renderer='templates/after_logout.mako')
    config.add_route('oauth_callback', '/oauth/callback', request_method='GET')
    config.add_view(
        oauth_callback_view, route_name='oauth_callback',
        renderer='templates/after_login.mako')


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
        message = format_error_value(request.params)
        return {'error': message}
    try:
        accept_oauth2_code(request)
    except AuthenticationError as ex:
        return {'error': str(ex)}
    # Get the user identity (refreshing the token should not be needed).
    profile = get_user_profile(request, refresh=False)
    # Make pyramid remember the user's id.
    user_id = app.model.find_user(profile['idUser'])
    if user_id is None:
        user_id = app.model.import_user(profile)
    else:
        app.model.update_user(user_id, profile)
    app.db.commit()
    remember(request, str(user_id))
    # The view template posts the result (encoded as JSON) to the parent
    # window, causing the frontend to update its state.
    # The Origin header is passed to the template to limit recipients.
    return {
        'user_id': user_id,
        'origin': request.headers.get('Origin')
    }


def logout_view(request):
    # Opening this view in a new window will post an 'afterLogout'
    # message to the application then redirect to the logout page
    # of the identity provider.
    # Do not open this view in an iframe, as it would prevent the
    # identity provider from receiving the user's cookies (look up
    # Third-party cookies).
    forget(request)
    request.session.clear()
    return {
        'identity_provider_logout_uri': app['logout_uri']
    }


#
# Public definitions
#

class AuthenticationError(RuntimeError):

    def __init__(self, message):
        super().__init__(message)


def get_oauth2_token(request, refresh=True):
    """ Return the logged-in user's access token.
        If refresh is True and the access token has expired, an attempt
        to refresh the token is made.
        If no access token can be obtained, AuthenticationError is raised.
    """
    session = request.session
    expires_ts = session.get('access_token_expires')
    if expires_ts is None:
        # If we do not have token expiry information, assume that we do
        # not have a token.
        raise AuthenticationError('no access token (expiry)')
    expires = datetime.utcfromtimestamp(expires_ts)
    now = datetime.utcnow()
    if (expires > now):
        # If the access token is still valid, return it.
        return session['access_token']
    # Do we attempt to refresh the token?
    refresh_token = session.get('refresh_token')
    if not refresh or refresh_token is None:
        # Clear the expired access token and bail out.
        del session['access_token_expires']
        del session['access_token']
        return AuthenticationError('access token has expired')
    # Refresh the token.
    refresh_uri = app['oauth_refresh_uri']
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    body = get_oauth_client().prepare_refresh_body(
        refresh_token=refresh_token,
        verify='/etc/ssl/certs/ca-certificates.crt')
    req = requests.post(refresh_uri, headers=headers, data=body)
    token = req.json()
    return accept_oauth2_token(request, token)


def get_user_profile(request, user_id=None, refresh=True):
    """ Query the identity provider for the authenticated user's
        identity, using the access token found in the user's session.
        If the query fails (or if the access token has expired and
        cannot be refreshed), None is returned.
    """
    try:
        access_token = get_oauth2_token(request, refresh)
    except AuthenticationError:
        return None
    idp_uri = app['identity_provider_uri']
    params = {}
    if user_id is not None:
        params['user_id'] = user_id
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(access_token)
    }
    req = requests.get(
        idp_uri, headers=headers, verify='/etc/ssl/certs/ca-certificates.crt')
    try:
        req.raise_for_status()
        profile = req.json()
        print("profile: {}".format(profile))
        if 'idUser' not in profile:
            raise RuntimeError('profile object has no idUser key')
        return profile
    except requests.exceptions.HTTPError:
        return None


#
# Private definitions
#


def oauth2_provider_uri(request):
    """ Generate an authorization URL.
    """
    authorise_uri = app['oauth_authorise_uri']
    callback_uri = request.route_url('oauth_callback')
    # XXX store the state in a database rather than in the session
    request.session['oauth_state'] = state = uuid.uuid4()
    oauth_params = {
        'state': state,
        'redirect_uri': callback_uri,
        'access_type': 'offline'
        # 'approval_prompt': 'force'
    }
    return get_oauth_client().prepare_request_uri(
        authorise_uri, **oauth_params)


def accept_oauth2_code(request):
    """ Use an OAuth2 code to complete the authentication process
        and return an access token.
        AuthenticationError is raised if no token can be obtained.
    """
    code = request.params.get('code')
    state = request.params.get('state')
    # XXX verify state
    token = exchange_code_for_token(request, code)
    return accept_oauth2_token(request, token)


def accept_oauth2_token(request, token):
    """ Store an OAuth2 token in the session, and return the access token.
        AuthenticationError is raised if the token is invalid.
    """
    if 'error' in token:
        raise AuthenticationError(format_error_value(token))
    access_token = token.get('access_token')
    if access_token is None:
        raise AuthenticationError('missing access token')
    token_expiry = token.get('expires_in')
    if token_expiry is None:
        raise AuthenticationError('missing access token expiry')
    refresh_token = token.get('refresh_token')
    # Store the token data in the (redis) session.
    # The expiry time is stored as a UTC timestamp.
    session = request.session
    session['access_token'] = access_token
    session['access_token_expires'] = time.time() + int(token_expiry)
    if refresh_token is None:
        del session['refresh_token']
    else:
        session['refresh_token'] = refresh_token
    return access_token


def get_oauth_client():
    client_id = app['oauth_client_id']
    return oauth2.WebApplicationClient(client_id)


def format_error_value(value):
    message = "{}: {}".format(value['error'], value['error_description'])
    return message


def exchange_code_for_token(request, code, **kwargs):
    """ Exchange the given OAuth2 code for an access token.
    """
    token_uri = app['oauth_token_uri']
    callback_uri = request.route_url('oauth_callback')
    client_secret = app['oauth_client_secret']
    state = request.session['oauth_state']
    body = get_oauth_client().prepare_request_body(
        state=state, code=code, redirect_uri=callback_uri,
        client_secret=client_secret, **kwargs)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    # XXX path to CA bundle should be pulled from configuration
    req = requests.post(
        token_uri, data=body, headers=headers,
        verify='/etc/ssl/certs/ca-certificates.crt')
    req.raise_for_status()
    return req.json()
