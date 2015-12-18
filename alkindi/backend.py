"""
The Paster application entry point.
"""

import json

from pyramid.config import Configurator
from pyramid.events import BeforeRender
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import SessionAuthenticationPolicy

from alkindi import helpers
from alkindi.globals import app


def application(_global_config, **settings):
    """ Returns the Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_debugtoolbar')
    config.include(set_session_factory)
    config.include(set_authorization_policy)
    config.include(set_authentication_policy)
    config.include('pyramid_mako')
    config.add_subscriber(set_renderer_context, BeforeRender)
    config.add_static_view(name='front', path='alkindi_r2_front:')
    config.include('.contexts')
    config.include('.index')
    config.include('.misc')
    return app.wrap_middleware(config.make_wsgi_app())


def get_redis(request, **kwargs):
    return app.redis


def set_session_factory(config):
    from pyramid_redis_sessions import RedisSessionFactory
    settings = json.loads(app.get('session_settings', '{}'))
    settings['secret'] = app['session_secret']
    settings['client_callable'] = get_redis
    session_factory = RedisSessionFactory(**settings)
    config.set_session_factory(session_factory)


def set_authorization_policy(config):
    authorization_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authorization_policy)


def set_authentication_policy(config):
    authentication_policy = SessionAuthenticationPolicy(
        callback=get_user_principals)
    config.set_authentication_policy(authentication_policy)


def get_user_principals(userid, request):
    return []


def set_renderer_context(event):
    event['g'] = app
    event['h'] = helpers
