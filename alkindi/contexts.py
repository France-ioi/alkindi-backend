
from pyramid.security import DENY_ALL, Allow

from alkindi.globals import app


ADMIN_GROUP = 'g:admin'


def includeme(config):
    config.set_root_factory(RootContext)


class RootContext:

    __parent__ = None
    __name__ = None
    __acl__ = [DENY_ALL]

    def __init__(self):
        pass

    def __getitem__(self, path_element):
        if path_element == 'api':
            return ApiContext(self)
        raise KeyError


class ApiContextBase:

    __acl__ = [DENY_ALL]

    def __init__(self, parent, **kwargs):
        self.__parent__ = parent
        for key, value in kwargs.items():
            setattr(self, key, value)


class UserApiContext(ApiContextBase):

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 'u:{}'.format(self.user_id), ['read', 'change'])
        ]


class UsersApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        return UserApiContext(self, user_id=int(path_element))


class TeamApiContext(ApiContextBase):

    def __init__(self, parent, team):
        self.__parent__ = parent
        self.team = team
        self.members = app.model.load_team_members(team['id'])

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 'tc:{}'.format(self.team_id), ['read']),
            (Allow, 't:{}'.format(self.team_id), ['read', 'change']),
        ]


class TeamsApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        team = app.model.load_team(int(path_element))
        if team is None:
            raise KeyError()
        return TeamApiContext(self, team=team)


class ApiContext(ApiContextBase):

    __name__ = 'api'

    def __init__(self, parent):
        self.__parent__ = parent

    FACTORIES = {
        'users': UsersApiContext,
        'teams': TeamsApiContext,
    }

    def __getitem__(self, path_element):
        factory = self.FACTORIES.get(path_element)
        if factory:
            return factory(self)
        raise KeyError()
