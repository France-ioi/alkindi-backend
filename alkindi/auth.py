
from datetime import datetime
import time

from oauthlib import oauth2
import requests
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.security import remember

from alkindi.globals import app


#
# Public functions
#

def redirect_to_oauth2_provider(request, redirect=None):
    """ Redirect the user to the OAuth2 provider.
        A redirect URL, if given, is stored in the user's session and
        the user will be redirected to that URL once authenticated.
    """
    if redirect is not None:
        request.session['redirect'] = redirect
    else:
        del request.session['redirect']
    authorise_uri = app['oauth_authorise_uri']
    callback_uri = request.route_url('oauth_callback')
    oauth_params = {
        'access_type': 'offline',
        'approval_prompt': 'force',
        'redirect_uri': callback_uri
    }
    oauth_uri = get_oauth_client().prepare_request_uri(
        authorise_uri, **oauth_params)
    raise HTTPFound(location=oauth_uri)


def accept_oauth2_code(request, code):
    """ Use an OAuth2 code to complete the authentication process.
    """
    token = exchange_code_for_token(request, code)
    accept_oauth2_token(request, token)
    redirect_user_after_authentication(request)


def accept_oauth2_token(request, token):
    """ Store an OAuth2 token and user details in the session.
    """
    session = request.session
    store_access_token(session, token.get('access_token'))
    user = request_user_identity(session)
    remember_authenticated_user(request, user)
    store_token_expiry(session, token['expires_in'])
    store_refresh_token(session, token.get('refresh_token'))


def get_oauth_client():
    client_id = app['oauth_client_id']
    return oauth2.WebApplicationClient(client_id)


def exchange_code_for_token(request, code, **kwargs):
    """ Exchange the given OAuth2 code for an access token.
    """
    token_uri = app['oauth_token_uri']
    callback_uri = request.route_url('oauth_callback')
    client_secret = app['oauth_client_secret']
    body = get_oauth_client().prepare_request_body(
        code=code, redirect_uri=callback_uri,
        client_secret=client_secret, **kwargs)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    req = requests.post(token_uri, data=body, headers=headers)
    return req.json()


def maybe_refresh_oauth2_token(request):
    session = request.session
    expires_ts = session.get('access_token_expires')
    if expires_ts is None:
        # Do nothing if we do not have token expiry information.
        return
    expires = datetime.fromtimestamp(expires_ts)
    now = datetime.utcnow()
    if (expires > now):
        # Do nothing if the access token is still valid.
        return
    refresh_token = session.get('refresh_token')
    if refresh_token is None:
        # Make the user go through authentication again if we do
        # not have a refresh token.
        redirect_to_oauth2_provider(request, redirect=request.url)
    # Refresh the token.
    refresh_uri = app['oauth_refresh_uri']
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    body = get_oauth_client().prepare_refresh_body(
        refresh_token=refresh_token)
    req = requests.post(refresh_uri, headers=headers, data=body)
    token = req.json()
    accept_oauth2_token(request, token)


def store_access_token(session, access_token):
    if access_token is None:
        raise HTTPForbidden('missing access_token')
    session['access_token'] = access_token


def request_user_identity(session):
    """ Query the identity provider for the authenticated user's
        identity, using the access token found in the user's session.
        If the query fails the access token is cleared and an
        HTTPForbidden exception is raised.
    """
    idp_uri = app['identity_provider_uri']
    access_token = session['access_token']
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(access_token)
    }
    req = requests.get(idp_uri, headers=headers)
    try:
        return req.json()
    except ValueError:
        del session['access_token']
        raise HTTPForbidden('bad access_token')


def remember_authenticated_user(request, user):
    # Make pyramid remember the user's id.
    remember(request, user['id'])
    # Temporarily? store the username in the session.
    request.session['username'] = user.get('username')


def store_token_expiry(session, expires_in):
    """ Store access token expiry in the session as a UTC timestamp.
    """
    session['access_token_expires'] = time.time() + int(expires_in)


def store_refresh_token(session, refresh_token):
    # Store a refresh token if available.
    if refresh_token is None:
        del session['refresh_token']
    else:
        session['refresh_token'] = refresh_token


def redirect_user_after_authentication(request):
    """ Redirect the authenticated user to their final location.
    """
    target_url = request.session.get('redirect')
    if target_url is not None:
        del request.session['redirect']
        raise HTTPFound(target_url)
    # If there is no redirect URL, send the user to the index page.
    raise HTTPFound(request.application_url)
