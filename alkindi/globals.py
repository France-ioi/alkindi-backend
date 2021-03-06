
import os
import sys
import codecs
import json
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
        TODO: put the Globals instance in thread-local storage.
    """

    def __init__(self):
        # Set the locale using the LANG environment variable.
        locale.setlocale(locale.LC_ALL, '')
        # Set up the logger.
        self.logger = logging.getLogger("alkindi")
        # The redis connection is established at first use.
        self._redis = None
        self._dict = dict()
        self._assets_pregenerator = None

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

    def assets_pregenerator(self):
        cdn_dict = json.loads(self.get('assets_pregenerator', '{}'))
        nocdn_dict = json.loads(self.get('nocdn_assets_pregenerator', '{}'))

        def pregenerator(request, elements, kwargs):
            if 'nocdn' in request.params:
                kwargs = dict(kwargs)
                for key, value in nocdn_dict.items():
                    kwargs[key] = value
            else:
                kwargs = dict(kwargs)
                for key, value in cdn_dict.items():
                    kwargs[key] = value
            return elements, kwargs

        return pregenerator


app = Globals()
