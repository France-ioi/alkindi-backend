
from pyramid.security import unauthenticated_userid, DENY_ALL, Allow

from alkindi.globals import app


ADMIN_GROUP = 'g:admin'


def includeme(config):
    config.set_root_factory(RootContext)


class RootContext:

    __parent__ = None
    __name__ = None
    __acl__ = [DENY_ALL]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, path_element):
        if path_element == 'api':
            # API access requires an authenticated user.
            userid = unauthenticated_userid(self.request)
            print("api {}".format(userid))
            if unauthenticated_userid(self.request) is None:
                raise KeyError
            return ApiContext(self)
        raise KeyError


class ApiContextBase:

    __acl__ = [DENY_ALL]

    def __init__(self, parent, **kwargs):
        self.__parent__ = parent
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def request(self):
        return self.__parent__.request


class UserApiContext(ApiContextBase):

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, self.user_id, ['read', 'change'])
        ]


class UsersApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        print('users/{}'.format(path_element))
        return UserApiContext(self, user_id=path_element)


class ApiContext(ApiContextBase):

    __name__ = 'api'

    def __init__(self, parent):
        self.__parent__ = parent

    FACTORIES = {
        'users': UsersApiContext,
    }

    def __getitem__(self, path_element):
        factory = self.FACTORIES.get(path_element)
        if factory:
            return factory(self)
        raise KeyError()
