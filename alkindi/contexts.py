
from pyramid.security import DENY_ALL, Allow

from alkindi.globals import app
from alkindi.auth import ADMIN_GROUP


def includeme(config):
    config.set_root_factory(RootContext)


class RootContext:

    __parent__ = None
    __name__ = None
    __acl__ = [DENY_ALL]

    def __init__(self, request):
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

    @property
    def user(self):
        return app.model.load_user(self.user_id)


class UsersApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        return UserApiContext(self, user_id=int(path_element))


class TeamApiContext(ApiContextBase):

    def __init__(self, parent, team):
        self.__parent__ = parent
        self.team_id = team['id']
        self.team = team
        self._members = None

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 'tc:{}'.format(self.team_id), ['read']),
            (Allow, 't:{}'.format(self.team_id), ['read', 'change']),
        ]

    @property
    def members(self):
        if self._members is None:
            self._members = app.model.load_team_members(self.team_id)
        return self._members


class TeamsApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        team = app.model.load_team(int(path_element))
        if team is None:
            raise KeyError()
        return TeamApiContext(self, team=team)


class WorkspaceRevisionApiContext(ApiContextBase):

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 't:{}'.format(self.team_id), ['read']),
            (Allow, 'u:{}'.format(self.creator_id), ['read', 'change']),
        ]

    @property
    def workspace_revision(self):
        return app.model.load_workspace_revision(self.workspace_revision_id)


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
