
from datetime import datetime
import time
import uuid

from oauthlib import oauth2
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.httpexceptions import HTTPSeeOther
from pyramid.security import remember, forget
import requests

from alkindi.globals import app
from alkindi.model.users import (
    find_user_by_foreign_id, import_user, update_user,
    get_user_principals)


ADMIN_GROUP = 'g:admin'


#
# Pyramid routes and views
#

def includeme(config):
    config.include(set_authorization_policy)
    config.include(set_authentication_policy)
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
    config.add_request_method(get_by_admin, 'by_admin', reify=True)


def set_authorization_policy(config):
    authorization_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authorization_policy)


def set_authentication_policy(config):
    authentication_policy = SessionAuthenticationPolicy(
        callback=authentication_callback)
    config.set_authentication_policy(authentication_policy)


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
    user_id = find_user_by_foreign_id(request.db, profile['idUser'])
    if user_id is None:
        user_id = import_user(request.db, profile, now=datetime.utcnow())
    else:
        update_user(request.db, user_id, profile)
    request.db.commit()
    # Clear the user's cached principals to force them to be refreshed.
    reset_user_principals(request)
    remember(request, str(user_id))
    # The view template posts the result (encoded as JSON) to the parent
    # window, causing the frontend to update its state.
    # The Origin header is passed to the template to limit recipients.
    # Pass the CSRF token to the login window so that it can send it to
    # the front.
    return {
        'user_id': user_id,
        'csrf_token': request.session.get_csrf_token(),
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

def get_user_profile(request, foreign_id=None, refresh=True):
    """ Query the identity provider for the specified foreign_id,
        authenticating using the access token from the request's session.
        If foreign_id is None, the profile of the authenticated user will
        be obtained.
        Set refresh to False to disable automatic access token refresh.
        If the query fails or if the access token has expired and cannot
        be refreshed, None is returned.
    """
    access_token = get_oauth2_token(request, refresh)
    idp_uri = app['identity_provider_uri']
    params = {}
    if foreign_id is not None:
        params['idUser'] = foreign_id
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(access_token)
    }
    req = requests.get(
        idp_uri, headers=headers, verify='/etc/ssl/certs/ca-certificates.crt')
    req.raise_for_status()
    profile = req.json()
    if 'idUser' not in profile:
        raise RuntimeError('profile object has no idUser key')
    return profile


def authentication_callback(userid, request):
    principals = request.session.get('principals')
    if principals is None:
        principals = get_user_principals(request.db, userid)
        print("get_user_principals({}) = {}".format(userid, principals))
        request.session['principals'] = principals
    return principals


def reset_user_principals(request):
    request.session['principals'] = None


def get_by_admin(request):
    return ADMIN_GROUP in request.effective_principals


#
# Private definitions
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
        # Clear the expired access token, log out, and bail out.
        del session['access_token_expires']
        del session['access_token']
        forget(request)
        raise AuthenticationError('access token has expired')
    # Refresh the token.
    refresh_uri = app['oauth_refresh_uri']
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    # Bug in oauthlib?  prepare_refresh_body should include the client_id
    # and client_secret in the body but does not, so we add the manually.
    client_id = app['oauth_client_id']
    client_secret = app['oauth_client_secret']
    body = get_oauth_client().prepare_refresh_body(
        client_id=client_id, client_secret=client_secret,
        refresh_token=refresh_token)
    req = requests.post(
        refresh_uri, headers=headers, data=body,
        verify='/etc/ssl/certs/ca-certificates.crt')
    token = req.json()
    return accept_oauth2_token(session, token)


def oauth2_provider_uri(request):
    """ Generate an authorization URL.
    """
    authorise_uri = app['oauth_authorise_uri']
    callback_uri = request.route_url('oauth_callback')
    request.session['oauth_state'] = state = str(uuid.uuid4())
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
    saved_state = request.session.get('oauth_state')
    if saved_state != state:
        forget(request)
        request.session.clear()
        raise AuthenticationError('bad state')
    token = exchange_code_for_token(request, code, state)
    del request.session['oauth_state']
    return accept_oauth2_token(request.session, token)


def accept_oauth2_token(session, token):
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
    # Store the token data in the (redis) session.
    # The expiry time is stored as a UTC timestamp.
    session['access_token'] = access_token
    session['access_token_expires'] = time.time() + int(token_expiry)
    session['refresh_token'] = token.get('refresh_token')
    return access_token


def get_oauth_client():
    client_id = app['oauth_client_id']
    return oauth2.WebApplicationClient(client_id)


def format_error_value(value):
    message = "{}: {}".format(value['error'], value['error_description'])
    return message


def exchange_code_for_token(request, code, state, **kwargs):
    """ Exchange the given OAuth2 code for an access token.
    """
    token_uri = app['oauth_token_uri']
    callback_uri = request.route_url('oauth_callback')
    client_secret = app['oauth_client_secret']
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
