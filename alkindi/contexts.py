
from pyramid.security import Allow, Authenticated

from alkindi.auth import ADMIN_GROUP
from alkindi.model.users import get_user_team_id
from alkindi.model.attempts import get_attempt_team_id
from alkindi.model.workspace_revisions import get_workspace_revision_ownership
from alkindi.model.participations import load_participation
from alkindi.model.round_tasks import load_round_task


def includeme(config):
    config.set_root_factory(RootContext)


class RootContext:

    __parent__ = None
    __name__ = None

    def __init__(self, request):
        self.request = request

    def __getitem__(self, path_element):
        if path_element == 'api':
            return ApiContext(self)
        raise KeyError

    @property
    def db(self):
        return self.request.db


class ApiContextBase:

    def __init__(self, parent, **kwargs):
        self.__parent__ = parent
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    @property
    def db(self):
        return self.__parent__.db


########################################################################
#
# /c1/n1/c2/n2
#


class ParticipationRoundTaskApiContext(ApiContextBase):

    def __str__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, self.participation['id'],
            self.round_task['id'])

    @property
    def __acl__(self):
        team_id = self.participation['team_id']
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 't:{}'.format(team_id), ['read', 'create_attempt'])
        ]


class UserAttemptApiContext(ApiContextBase):

    def __str__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, self.user_id, self.attempt_id)

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 'u:{}'.format(self.user_id), ['read', 'change'])
        ]


class WorkspaceRevisionApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(self.__class__.__name__,
                               self.workspace_revision_id)

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 't:{}'.format(self.team_id), ['read']),
            (Allow, 'u:{}'.format(self.creator_id), ['read', 'change']),
        ]


########################################################################
#
# /c1/n1/c2
#

class UserAttemptsApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.user_id)

    def __getitem__(self, path_element):
        # Users only see their team's attempts.
        attempt_id = int(path_element)
        team_id = get_attempt_team_id(self.db, attempt_id)
        user_team_id = get_user_team_id(self.db, self.user_id)
        if team_id is None or team_id != user_team_id:
            raise KeyError()
        return UserAttemptApiContext(
            self, user_id=self.user_id, attempt_id=attempt_id)


class ParticipationTasksApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(
            self.__class__.__name__, self.participation_id)

    def __getitem__(self, path_element):
        print("ParticipationTasksApiContext")
        round_task_id = int(path_element)
        round_task = load_round_task(self.db, round_task_id)
        print("participation {} round_task {}".format(self.participation, round_task))
        if round_task is None:
            raise KeyError()
        if self.participation['round_id'] != round_task['round_id']:
            raise KeyError()
        return ParticipationRoundTaskApiContext(
            self,
            participation=self.participation, round_task=round_task)


########################################################################
#
# /c1/n1
#

class UserApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.user_id)

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 'u:{}'.format(self.user_id), ['read', 'change'])
        ]

    def __getitem__(self, path_element):
        if path_element == 'attempts':
            return UserAttemptsApiContext(self, user_id=self.user_id)
        raise KeyError()


class TeamApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.team_id)

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 'tc:{}'.format(self.team_id), ['read']),
            (Allow, 't:{}'.format(self.team_id), ['read', 'change']),
        ]


class ParticipationApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.participation)

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'change']),
            (Allow, 't:{}'.format(self.participation['team_id']), ['read'])
        ]

    def __getitem__(self, path_element):
        if path_element == 'tasks':
            return ParticipationTasksApiContext(
                self, participation=self.participation)
        raise KeyError()


class AttemptApiContext(ApiContextBase):

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.attempt_id)

    @property
    def __acl__(self):
        return [
            (Allow, ADMIN_GROUP, ['read', 'start']),
            (Allow, 't:{}'.format(self.team_id), ['read', 'start'])
        ]


########################################################################
#
# /c1
#

class UsersApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        return UserApiContext(self, user_id=int(path_element))


class TeamsApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        team_id = int(path_element)
        # We do not verify that the team exists, the user will get
        # a 403 error if the team is not in their credentials.
        return TeamApiContext(self, team_id=team_id)


class ParticipationsApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        participation_id = int(path_element)
        participation = load_participation(self.db, participation_id)
        return ParticipationApiContext(self, participation=participation)


class AttemptsApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        attempt_id = int(path_element)
        # We need to look up the attempt's team_id for AttemptApiContext
        # to be able to build its ACL.
        team_id = get_attempt_team_id(self.db, attempt_id)
        if team_id is None:
            raise KeyError()
        return AttemptApiContext(self, attempt_id=attempt_id, team_id=team_id)


class WorkspaceRevisionsApiContext(ApiContextBase):

    def __getitem__(self, path_element):
        revision_id = int(path_element)
        ownership = get_workspace_revision_ownership(self.db, revision_id)
        if ownership is None:
            raise KeyError()
        team_id, creator_id = ownership
        return WorkspaceRevisionApiContext(
            self, workspace_revision_id=revision_id,
            team_id=team_id, creator_id=creator_id)


########################################################################
#
# /
#

class ApiContext(ApiContextBase):

    __name__ = 'api'

    def __init__(self, parent):
        self.__parent__ = parent

    @property
    def __acl__(self):
        return [(Allow, Authenticated, ['access'])]

    FACTORIES = {
        'users': UsersApiContext,
        'teams': TeamsApiContext,
        'participations': ParticipationsApiContext,
        'attempts': AttemptsApiContext,
        'workspace_revisions': WorkspaceRevisionsApiContext,
    }

    def __getitem__(self, path_element):
        factory = self.FACTORIES.get(path_element)
        if factory:
            return factory(self)
        raise KeyError()
