
from datetime import datetime

from .utils import generate_access_code

# TODO: add started_at to attempts
# TODO: when the first attempt starts, *lock* the team.


class ModelError(RuntimeError):
    pass


class Model:

    def __init__(self, db):
        self.db = db

    def commit(self):
        self.db.commit()

    def find_user(self, foreign_id):
        """ Find the user with the given foreign_id and return their id,
            or None if no such user exists.
        """
        users = self.db.tables.users
        row = self.db.first(
            self.db.query(users)
                .fields(users.id)
                .where(users.foreign_id == foreign_id))
        if row is None:
            return None
        return row[0]

    def import_user(self, profile):
        foreign_id = profile['idUser']
        users = self.db.tables.users
        query = self.db.query(users).insert({
            users.created_at: datetime.utcnow(),
            users.foreign_id: foreign_id,
            users.team_id: None,
            users.username: profile['sLogin'],
            users.firstname: profile['sFirstName'],
            users.lastname: profile['sLastName'],
            users.badges: ' '.join(profile['badges']),
        })
        user_id = self.db.insert(query)
        return user_id

    def update_user(self, user_id, profile):
        self.__update_row(self.db.tables.users, user_id, {
            'username': profile['sLogin'],
            'firstname': profile['sFirstName'],
            'lastname': profile['sLastName'],
            'badges': ' '.join(profile['badges']),
        })

    def get_user_principals(self, user_id):
        user_id = int(user_id)
        users = self.db.tables.users
        query = self.db.query(users) \
            .where(users.id == user_id) \
            .fields(users.team_id)
        row = self.db.first(query)
        if row is None:
            raise ModelError('invalid user')
        principals = ['u:{}'.format(user_id)]
        team_id = row[0]
        if team_id is None:
            return principals
        team_members = self.db.tables.team_members
        query = self.db.query(team_members) \
            .where(team_members.user_id == user_id) \
            .where(team_members.team_id == team_id) \
            .fields(team_members.is_qualified, team_members.is_creator)
        row = self.db.first(query)
        if row is None:
            raise ModelError('missing team_member row')
        principals.append('t:{}'.format(team_id))
        if self.db.view_bool(row[0]):
            principals.append('ts:{}'.format(team_id))
        if self.db.view_bool(row[1]):
            principals.append('tc:{}'.format(team_id))
        return principals

    def create_team(self, user_id):
        """ Create a team for the specified user.
            The user's badges are used to determine the round with which the
            team is associated.
            Return a boolean indicating whether the team was created.
        """
        # Verify that the user exists and does not already belong to a team.
        user = self.load_user(user_id)
        if user['team_id'] is not None:
            # User is already in a team.
            return False
        # Select a round based on the user's badges.
        round_id = self.select_round_with_badges(user['badges'])
        if round_id is None:
            # The user does not have access to any open round.
            return False
        # Generate an unused code.
        code = generate_access_code()
        while self.find_team_by_code(code) is not None:
            code = generate_access_code()
        # Create the team.
        teams = self.db.tables.teams
        query = self.db.query(teams).insert({
            teams.created_at: datetime.utcnow(),
            teams.round_id: round_id,
            teams.code: code,
            teams.is_open: True,
            teams.is_locked: False
        })
        team_id = self.db.insert(query)
        # Create the team_members row.
        self.__add_team_member(
            team_id, user_id, is_qualified=True, is_creator=True)
        # Update the user's team_id.
        self.__set_user_team_id(user_id, team_id)
        return True

    def join_team(self, user, team_id):
        """ Add a user to a team.
            Registration for the team's round must be open.
            Return a boolean indicating if the team member was added.
        """
        # Verify that the user does not already belong to a team.
        if user['team_id'] is not None:
            # User is already in a team.
            return False
        # Verify that the team exists, is open, and not locked.
        team = self.load_team(team_id)
        if team['is_locked']:
            # Team is locked (an attempt was started).
            return False
        if not team['is_open']:
            # Team is closed (by its creator).
            return False
        round_id = team['round_id']
        # Verify that the round is open for registration.
        if not self.__is_round_registration_open(round_id):
            return False
        # Look up the badges that grant access to the team's round, to
        # figure out whether the user is qualified for that round.
        user_badges = user['badges']
        badges = self.db.tables.badges
        if len(user_badges) == 0:
            is_qualified = False
        else:
            row = self.db.first(
                self.db.query(badges).fields(badges.id)
                    .where(badges.round_id == round_id)
                    .where(badges.symbol.in_(user_badges))
                    .where(badges.is_active))
            is_qualified = row is not None
        # Create the team_members row.
        user_id = user['id']
        self.__add_team_member(team_id, user_id, is_qualified=is_qualified)
        # Update the user's team_id.
        self.__set_user_team_id(user_id, team_id)
        return True

    def leave_team(self, user):
        """ Remove a user from their team.
        """
        # The user must be member of a team.
        user_id = user['id']
        team_id = user['team_id']
        if user['team_id'] is None:
            return False
        # The team must not be locked.
        team = self.load_team(team_id)
        if team['is_locked']:
            return False
        # Clear the user's team_id.
        self.__set_user_team_id(user_id, None)
        # Delete the team_members row.
        team_members = self.db.tables.team_members
        tm_query = self.db.query(team_members) \
            .where(team_members.team_id == team_id) \
            .where(team_members.user_id == user_id)
        (is_creator,) = self.db.first(
            tm_query.fields(team_members.is_creator))
        self.db.delete(tm_query)
        # If the user was the team creator, select the earliest member
        # as the new creator.
        if is_creator:
            query = self.db.query(team_members) \
                .where(team_members.team_id == team_id)
            row = self.db.first(
                query.fields(team_members.user_id)
                     .order_by(team_members.joined_at))
            if row is None:
                # Team has become empty, delete it.
                teams = self.db.tables.teams
                team_query = self.db.query(teams) \
                    .where(teams.id == team_id)
                self.db.delete(team_query)
            else:
                # Promote the selected user as the creator.
                new_creator_id = row[0]
                self.db.update(
                    query.where(team_members.user_id == new_creator_id),
                    {team_members.is_creator: True})
        return True

    def update_team(self, team_id, settings):
        """ Update a team's settings.
            These settings are available:
                is_open: can users join the team?
                is_locked: can users join or leave the team?
            No checks are performed in this function.
        """
        self.__update_row(self.db.tables.teams, team_id, settings)

    def find_team_by_code(self, code):
        teams = self.db.tables.teams
        row = self.db.first(
            self.db.query(teams)
                .fields(teams.id)
                .where(teams.code == code))
        if row is None:
            return None
        (team_id,) = row
        return team_id

    def load_user(self, user_id):
        if user_id is None:
            return None
        keys = [
            'id', 'created_at', 'foreign_id', 'team_id',
            'username', 'firstname', 'lastname', 'badges'
        ]
        result = self.__load_row(self.db.tables.users, user_id, keys)
        if result is None:
            return None
        result['badges'] = result['badges'].split(' ')
        return result

    def load_team(self, team_id):
        if team_id is None:
            return None
        keys = [
            'id', 'revision', 'created_at', 'round_id', 'code',
            'is_open', 'is_locked', 'message'
        ]
        result = self.__load_row(self.db.tables.teams, team_id, keys)
        for key in ['is_open', 'is_locked']:
            result[key] = self.db.view_bool(result[key])
        return result

    def load_round(self, round_id):
        if round_id is None:
            return None
        keys = [
            'id', 'created_at', 'updated_at', 'title',
            'registration_opens_at', 'training_opens_at',
            'min_team_size', 'max_team_size', 'min_team_ratio',
            'max_attempts', 'questions_path'
        ]
        return self.__load_row(self.db.tables.rounds, round_id, keys)

    def load_team_members(self, team_id, users=False):
        team_members = self.db.tables.team_members
        if users:
            users = self.db.tables.users
            query = self.db.query(team_members & users)
            query = query.where(team_members.user_id == users.id)
            query = query.where(team_members.team_id == team_id)
            query = query.fields(
                team_members.joined_at,     # 0
                team_members.is_qualified,  # 1
                team_members.is_creator,    # 2
                users.id,                   # 3
                users.username,             # 4
                users.firstname,            # 5
                users.lastname,             # 6
            )
            query = query.order_by(team_members.joined_at)
            return [
                {
                    'joined_at': row[0],
                    'is_qualified': self.db.view_bool(row[1]),
                    'is_creator': self.db.view_bool(row[2]),
                    'user': {
                        'id': row[3],
                        'username': row[4],
                        'firstname': row[5],
                        'lastname': row[6],
                    }
                }
                for row in self.db.all(query)
            ]
        query = self.db.query(team_members) \
            .where(team_members.team_id == team_id) \
            .fields(team_members.user_id, team_members.joined_at,
                    team_members.is_qualified, team_members.is_creator)
        return [
            {
                'user_id': row[0],
                'joined_at': row[1],
                'is_qualified': self.db.view_bool(row[2]),
                'is_creator': self.db.view_bool(row[3])
            }
            for row in self.db.all(query)
        ]

    def get_team_creator(self, team_id):
        team_members = self.db.tables.team_members
        tm_query = self.db.query(team_members) \
            .where(team_members.team_id == team_id) \
            .where(team_members.is_creator)
        row = self.db.first(tm_query.fields(team_members.user_id))
        if row is None:
            raise ModelError('team has no creator')
        return row[0]

    def select_round_with_badges(self, badges):
        """ Select a round (active, registration open) for which the
            badges qualify, and return its id.
            If no round qualifies, None is returned.
        """
        rounds = self.db.tables.rounds
        if len(badges) == 0:
            return None
        badges_table = self.db.tables.badges
        now = datetime.now()
        row = self.db.first(
            self.db.query(rounds & badges_table)
                .fields(rounds.id)
                .where(badges_table.round_id == rounds.id)
                .where(badges_table.symbol.in_(badges))
                .where(badges_table.is_active)
                .where(rounds.registration_opens_at <= now))
        if row is None:
            # If no round was found, the user does not have a badge that
            # grants them access to a round and we cannot create a team.
            return None
        (round_id,) = row
        return round_id

    def cancel_current_team_attempt(self, team_id):
        attempts = self.db.tables.attempts
        query = self.db.query(attempts) \
            .where(attempts.team_id == team_id) \
            .where(attempts.is_current)
        self.db.delete(query)
        # If a training attempt exists, make it current.
        query = self.db.query(attempts) \
            .where(attempts.team_id == team_id) \
            .where(attempts.is_training) \
            .fields(attempts.id)
        row = self.db.first(query,)
        if row is not None:
            (attempt_id,) = row
            self.__update_row(attempts, attempt_id, {'is_current': True})

    def load_team_current_attempt(self, team_id):
        attempts = self.db.tables.attempts
        keys = [
            'id', 'team_id', 'round_id', 'question_id',
            'created_at', 'started_at', 'closes_at',
            'is_current', 'is_training', 'is_unsolved'
        ]
        query = self.db.query(attempts) \
            .where(attempts.team_id == team_id) \
            .where(attempts.is_current) \
            .fields(*[getattr(attempts, key) for key in keys])
        row = self.db.first(query)
        if row is None:
            return None
        result = {key: row[i] for i, key in enumerate(keys)}
        for key in ['is_current', 'is_training', 'is_unsolved']:
            result[key] = self.db.view_bool(result[key])
        return result

    def count_team_timed_attempts(self, team_id):
        attempts = self.db.tables.attempts
        query = self.db.query(attempts) \
            .where(attempts.team_id == team_id) \
            .where(~attempts.is_training) \
            .fields(attempts.id.count())
        return self.db.scalar(query)

    def create_attempt(self, round_id, team_id, members, is_training=True):
        attempts = self.db.tables.attempts
        attempt_id = self.__insert_row(attempts, {
            'team_id': team_id,
            'round_id': round_id,
            'question_id': None,  # set when question is accessed
            'created_at': datetime.utcnow(),
            'started_at': None,   # set when enough codes have been entered
            'closes_at': None,    # set when question is accessed
            'is_current': True,
            'is_training': is_training,
            'is_unsolved': True
        })
        # TODO: create codes
        return attempt_id

    def set_attempt_not_current(self, attempt_id):
        attempts = self.db.tables.attempts
        self.__update_row(attempts, attempt_id, {'is_current': False})

    # --- private methods below ---

    def __load_row(self, table, id, keys):
        query = self.db.query(table)
        query = query.fields(*[getattr(table, key) for key in keys])
        query = query.where(table.id == id)
        row = self.db.first(query)
        if row is None:
            return None
        return {key: row[i] for i, key in enumerate(keys)}

    def __insert_row(self, table, attrs):
        query = self.db.query(table)
        query = query.insert({
            getattr(table, key): attrs[key] for key in attrs
        })
        return self.db.insert(query)

    def __update_row(self, table, id, attrs):
        query = self.db.query(table).where(table.id == id)
        query = query.update({
            getattr(table, key): attrs[key] for key in attrs
        })
        cursor = self.db.execute(query)
        cursor.close()

    def __add_team_member(self, team_id, user_id,
                          is_qualified=False, is_creator=False):
        team_members = self.db.tables.team_members
        query = self.db.query(team_members).insert({
            team_members.team_id: team_id,
            team_members.user_id: user_id,
            team_members.joined_at: datetime.utcnow(),
            team_members.is_qualified: is_qualified,
            team_members.is_creator: is_creator
        })
        self.db.execute(query)

    def __is_round_registration_open(self, round_id):
        rounds = self.db.tables.rounds
        (registration_opens_at,) = self.db.first(
            self.db.query(rounds)
                .fields(rounds.registration_opens_at)
                .where(rounds.id == round_id))
        now = datetime.now()
        return (registration_opens_at <= now)

    def __set_user_team_id(self, user_id, team_id):
        self.__update_row(self.db.tables.users, user_id, {'team_id': team_id})

    def get_team_stats(self, team_id):
        """ Return (n_members, n_qualified) for the given team.
        """
        team_members = self.db.tables.team_members
        tm_query = self.db.query(team_members) \
            .where(team_members.team_id == team_id)
        n_members = self.db.scalar(
            tm_query.fields(team_members.user_id.count()))
        n_qualified = self.db.scalar(
            tm_query.where(team_members.is_qualified)
            .fields(team_members.user_id.count()))
        return (n_members, n_qualified)
