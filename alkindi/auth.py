
from datetime import datetime
import time
import uuid

from oauthlib import oauth2
import requests
from pyramid.httpexceptions import HTTPForbidden
from pyramid.security import remember

from alkindi.globals import app


#
# Public functions
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


def accept_oauth2_code(request, code):
    """ Use an OAuth2 code to complete the authentication process
        and return the authenticated user's identity, or a dict
        containing an 'error' key.
    """
    # XXX get code from request.params.get('code')
    # XXX verify request.params.get('state')
    token = exchange_code_for_token(request, code)
    if 'error' in token:
        return token
    return accept_oauth2_token(request, token)


def accept_oauth2_token(request, token):
    """ Store an OAuth2 token and user details in the session,
        and return the authenticated user's identity.
    """
    session = request.session
    store_access_token(session, token.get('access_token'))
    user = request_user_identity(session)
    remember_authenticated_user(request, user)
    store_token_expiry(session, token['expires_in'])
    store_refresh_token(session, token.get('refresh_token'))
    return user


def get_oauth_client():
    client_id = app['oauth_client_id']
    return oauth2.WebApplicationClient(client_id)


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
    return req.json()


def maybe_refresh_oauth2_token(request):
    session = request.session
    expires_ts = session.get('access_token_expires')
    if expires_ts is None:
        # Do nothing if we do not have token expiry information.
        return None
    expires = datetime.fromtimestamp(expires_ts)
    now = datetime.utcnow()
    if (expires > now):
        # If the access token is still valid, return the user identity.
        return request_user_identity(session)
    refresh_token = session.get('refresh_token')
    if refresh_token is None:
        # Make the user go through authentication again if we do
        # not have a refresh token.
        return None
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
    req = requests.get(
        idp_uri, headers=headers, verify='/etc/ssl/certs/ca-certificates.crt')
    try:
        req.raise_for_status()
        return req.json()
    except requests.exceptions.HTTPError:
        message = 'failed to get user identity: {} {}'.format(
            req.status_code, req.text)
        raise HTTPForbidden(message)
    except ValueError:
        del session['access_token']
        raise HTTPForbidden('bad access_token')


def remember_authenticated_user(request, user):
    # Make pyramid remember the user's id.
    remember(request, user['id'])
    # Temporarily? store the username in the session.
    request.session['username'] = user.get('sLogin')


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
