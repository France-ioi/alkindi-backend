"""
The Paster application entry point.
"""

from datetime import datetime, date
import decimal
import json
import os

from pyramid.events import NewRequest, BeforeRender
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
        "=== {} worker {} starting (front {}{})".format(
            datetime.now().isoformat(), os.getpid(),
            front_version, 'min' if front_min else ''))

    config = Configurator(settings=settings)
    config.include('pyramid_debugtoolbar')
    config.include(set_session_factory)
    config.include('pyramid_mako')

    config.add_subscriber(add_cors_headers, NewRequest)
    config.add_subscriber(log_api_failure, BeforeRender)
    config.add_subscriber(set_renderer_context, BeforeRender)

    # Serve versioned static assets from alkindi-r2-front at /front
    config.add_static_view(
        name='front', path='alkindi_r2_front:',
        cache_max_age=2592000,
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


def add_cors_headers(event):
    def cors_headers(request, response):
        response.headers.update({
            'Access-Control-Allow-Origin': 'https://suite.concours-alkindi.fr',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Max-Age': '1728000',
        })
    event.request.add_response_callback(cors_headers)


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
    if not event['renderer_name'].endswith('.mako'):
        return
    event['g'] = app
    event['h'] = helpers
    event['front_min'] = '.min' if front_min else ''


def log_api_failure(event):
    # Consider only POST requests that return a json value.
    request = event['request']
    context = event['context']
    if request is None or context is None:
        return
    if event['renderer_name'] != 'json':
        return
    if request.method != 'POST':
        return
    # Consider only values that have a False 'success' property.
    value = event.rendering_val
    success = value.get('success')
    if success is True:
        return
    # Rollback early to prevent any changes to the model from being
    # committed when the error is inserted.
    app.db.rollback()
    app.model.log_error({
        'created_at': datetime.now(),
        'request_url': request.url,
        'request_body': request.body,
        'request_headers': json.dumps(dict(request.headers)),
        'context': str(event['context']),
        'user_id': request.unauthenticated_userid,
        'response_body': json.dumps(value)
    })
    app.db.commit()


def add_json_renderer(config):
    json_renderer = JSON()

    def datetime_adapter(obj, request):
        return "{}Z".format(obj.isoformat())

    def date_adapter(obj, request):
        return obj.isoformat()

    def decimal_adapter(obj, request):
        return str(obj)

    json_renderer.add_adapter(datetime, datetime_adapter)
    json_renderer.add_adapter(date, date_adapter)
    json_renderer.add_adapter(decimal.Decimal, decimal_adapter)

    config.add_renderer('json', json_renderer)
