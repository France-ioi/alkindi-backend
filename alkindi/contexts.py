
from pyramid.security import unauthenticated_userid


def includeme(config):
    config.set_root_factory(RootContext)


class RootContext:

    __parent__ = None
    __name__ = None

    def __init__(self, request):
        self.request = request

    def __getitem__(self, path_element):
        if path_element == 'api':
            if unauthenticated_userid(self.request) is not None:
                return ApiContext(self)
        raise KeyError


class ApiContext:

    __name__ = 'api'

    def __init__(self, parent):
        self.__parent__ = parent
