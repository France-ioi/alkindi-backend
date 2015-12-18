
import os
import sys
import codecs
import locale
import logging

from redis import StrictRedis

from .utils import as_int


__all__ = ['app']


class Globals:
    """ A single instance of this class is used for global state that
        persists across requests, that is reused during a request, or
        that needs to be accessible outside of requests (such as in
        console tools).
        This includes mainly the connections to redis and postgresql.
    """

    def __init__(self):
        # Set the locale using the LANG environment variable.
        locale.setlocale(locale.LC_ALL, '')
        # Set up the logger.
        self.logger = logging.getLogger("alkindi")
        # The redis connection is established at first use.
        self._redis = None
        self._dict = dict()
        # XXX connect to postgresql (also lazily).

    def wrap_middleware(self, app):
        """ Wrap our middleware around the given WSGI app, so that
            our before_request and after_request hooks are called.
        """
        return GlobalsResetMiddleware(app, self)

    def before_request(self):
        # Perform pre-request setup here.
        pass

    def after_request(self):
        # Perform post-request teardown here.
        # Clear 'assets_timestamp' after every request so that the
        # next request reloads it from redis.
        self._dict.pop('assets_timestamp', None)

    @property
    def redis_settings(self):
        """ Retrieve redis connection settings from the environment
            to ease deployment with docker.
        """
        host = os.environ.get('REDIS_HOST', '127.0.0.1')
        port = as_int(os.environ.get('REDIS_PORT', '6379'))
        db = as_int(os.environ.get('REDIS_DB', '0'))
        return {'host': host, 'port': port, 'db': db}

    @property
    def redis(self):
        if self._redis is None:
            self._redis = StrictRedis(**self.redis_settings)
            if self.get('configured') != 'yes':
                self.logger.fatal("redis is not configured, see configure.sh")
                sys.exit(4)
        return self._redis

    def get(self, key, default=None):
        if key in self._dict:
            value = self._dict[key]
        else:
            value = self.redis.get(key)
            if value is not None:
                value = codecs.decode(value)
            self._dict[key] = value
        return value if value is not None else default

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError('missing redis key {}'.format(key))
        return value


class GlobalsResetMiddleware:
    """ Reset the global state at the end of each request
    """

    def __init__(self, app, globals):
        self.app = app
        self.globals = globals

    def __call__(self, environ, start_response):
        self.globals.before_request()
        result = self.app(environ, start_response)
        self.globals.after_request()
        return result


app = Globals()
