"""
The Paster application entry point.
"""

import datetime
import decimal
import json
import os

from pyramid.events import BeforeRender
from pyramid.config import Configurator
from pyramid.renderers import JSON
from pyramid.static import QueryStringConstantCacheBuster

from alkindi import helpers
from alkindi.globals import app
from alkindi_r2_front import (
    version as front_version,
    min_build as front_min)


def application(_global_config, **settings):
    """ Returns the Pyramid WSGI application.
    """

    print(
        "=== {} worker {} starting".format(
            datetime.datetime.now().isoformat(), os.getpid()))

    config = Configurator(settings=settings)
    config.include('pyramid_debugtoolbar')
    config.include(set_session_factory)
    config.include('pyramid_mako')

    config.add_subscriber(set_renderer_context, BeforeRender)

    # Serve versioned static assets from alkindi-r2-front at /front
    config.add_static_view(
        name='front', path='alkindi_r2_front:',
        # cache_max_age=2592000,
        pregenerator=app.assets_pregenerator())
    config.add_cache_buster(
        'alkindi_r2_front:', QueryStringConstantCacheBuster(front_version))

    # Set up a json renderer that handles datetime objects.
    config.include(add_json_renderer)

    config.include('.contexts')
    config.include('.auth')
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


def set_renderer_context(event):
    event['g'] = app
    event['h'] = helpers
    event['front_min'] = '.min' if front_min else ''


def add_json_renderer(config):
    json_renderer = JSON()

    def datetime_adapter(obj, request):
        return "{}Z".format(obj.isoformat())

    def date_adapter(obj, request):
        return obj.isoformat()

    def decimal_adapter(obj, request):
        return str(obj)

    json_renderer.add_adapter(datetime.datetime, datetime_adapter)
    json_renderer.add_adapter(datetime.date, date_adapter)
    json_renderer.add_adapter(decimal.Decimal, decimal_adapter)

    config.add_renderer('json', json_renderer)
