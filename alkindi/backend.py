"""
The Paster application entry point.
"""

from datetime import datetime, date
import decimal
import json
import os
import sys
import traceback

from pyramid.events import NewRequest, BeforeRender
from pyramid.config import Configurator
from pyramid.renderers import JSON
from pyramid.static import QueryStringConstantCacheBuster
from pyramid.renderers import render
from pyramid.tweens import EXCVIEW

from alkindi import helpers
from alkindi.globals import app
from alkindi_r2_front import (
    version as front_version,
    min_build as front_min)
from alkindi.errors import ApplicationError


def application(_global_config, **settings):
    """ Returns the Pyramid WSGI application.
    """

    print(
        "=== {}Z worker {} starting (front {}{})".format(
            datetime.utcnow().isoformat(), os.getpid(),
            front_version, 'min' if front_min else ''))

    config = Configurator(settings=settings)
    # config.include('pyramid_debugtoolbar')
    config.include(set_session_factory)
    config.include('pyramid_mako')

    config.add_subscriber(add_headers, NewRequest)
    config.add_subscriber(log_api_failure, BeforeRender)
    config.add_subscriber(set_renderer_context, BeforeRender)
    config.add_tween('alkindi.backend.transaction_manager_tween_factory',
                     under=EXCVIEW)

    # Serve versioned static assets from alkindi-r2-front at /front
    config.add_static_view(
        name='front', path='alkindi_r2_front:',
        cache_max_age=(2592000 if front_min else 0),
        pregenerator=app.assets_pregenerator())
    config.add_cache_buster(
        'alkindi_r2_front:', QueryStringConstantCacheBuster(front_version))

    # Set up a json renderer that handles datetime objects.
    config.include(add_json_renderer)

    config.include('.contexts')
    config.include('.auth')
    config.include('.index')
    config.include('.misc')

    return config.make_wsgi_app()


def add_headers(event):
    def callback(request, response):
        response.headers.update({
            'Access-Control-Allow-Origin': 'https://suite.concours-alkindi.fr',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Max-Age': '1728000',
            'X-Frontend-Version': front_version
        })
    event.request.add_response_callback(callback)


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
    event['front_version'] = front_version
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
    # The transaction manager tween is inserted under the exception view
    # above (under=EXCVIEW), so the connection to the DB has been closed
    # when execution reaches this point.
    ex = None
    if isinstance(context, Exception):
        ex = context
    if app.get('error_log_target') != 'db':
        print('\033[91mAPI Failure: \033[1m{}\033[0m'.format(context))
        if ex is not None:
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import TerminalFormatter
            lines = traceback.format_exception(type(ex), ex, ex.__traceback__)
            if isinstance(ex, ApplicationError) and type(ex.args) is tuple:
                lines.append('full arguments: {}'.format(ex.args))
            tbtext = ''.join(lines)
            lexer = get_lexer_by_name("pytb", stripall=True)
            formatter = TerminalFormatter()
            sys.stderr.write(highlight(tbtext, lexer, formatter))
        return
    context_obj = {
        'context': str(context)
    }
    if ex is not None:
        context_obj['exception'] = \
            traceback.format_exception_only(type(ex), ex)
        context_obj['trace'] = traceback.format_tb(ex.__traceback__)
        if isinstance(ex, ApplicationError) and type(ex.args) is tuple:
            context_obj['args'] = ex.args
    app.db.ensure_connected()
    app.db.log_error({
        'created_at': datetime.utcnow(),
        'request_url': request.url,
        'request_body': request.body,
        'request_headers': json.dumps(dict(request.headers)),
        'context': json.dumps(context_obj),
        'user_id': request.unauthenticated_userid,
        'response_body': render('json', value)
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


def transaction_manager_tween_factory(handler, registry):

    def tween(request):

        try:
            # print("\033[93mTM begin\033[0m")
            app.db.ensure_connected()
            app.db.start_transaction()
            result = handler(request)
            app.db.commit()
            # print("\033[92mTM commit\033[0m")
            return result
        except:
            # print("\033[91mTM rollback\033[0m")
            app.db.rollback()
            raise
        finally:
            # print("\033[94mTM close\033[0m")
            app.db.close()

    return tween
