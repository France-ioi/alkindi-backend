
from datetime import datetime

from .utils import generate_access_code


class InputError(RuntimeError):
    pass


class Model:

    def __init__(self, db):
        self.db = db

    def commit(self):
        self.db.commit()

    def import_user(self, foreign_id, username):
        users = self.db.tables.users
        query = self.db.query(users).insert({
            users.created_at: datetime.utcnow(),
            users.foreign_id: foreign_id,
            users.team_id: None,
            users.username: username
        })
        user_id = self.db.insert(query)
        return user_id

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

    def view_user(self, user_id, badges):
        """ Return the user-view for the user with the given id.
        """
        users = self.db.tables.users
        query = self.db.query(users) \
            .fields(users.username, users.team_id) \
            .where(users.id == user_id)
        row = self.db.first(query)
        if row is None:
            raise InputError('no such user')
        (username, team_id) = row
        result = {
            'id': user_id,
            'username': username,
        }
        if team_id is None:
            # If the user has not team, we look for a round to which a
            # badge grants access.
            round_id = self.select_round_with_badges(badges)
            if round_id is not None:
                result['accessible_round'] = self.view_user_round(round_id)
        else:
            # Add 'team', 'round' and 'question' info.
            team = self.load_team(team_id)
            result['team'] = self.view_user_team(team)
            result['round'] = self.view_user_round(team['round_id'])
            result['question'] = self.view_user_question(team['question_id'])
            # Add is_selected
            team_members = self.db.tables.team_members
            (is_selected,) = self.db.first(
                self.db.query(team_members)
                    .fields(team_members.is_selected)
                    .where(team_members.team_id == team_id)
                    .where(team_members.user_id == user_id))
            result['is_selected'] = self.db.view_bool(is_selected)
        return result

    def create_team(self, user_id, badges):
        """ Create a team for the specified user, and associate it with
            a round based on the given badges.
            Registration for the round must be open, and the badge must
            be valid.
            Return a boolean indicating if the team was created.
        """
        # Verify that the user exists and does not already belong to a team.
        team_id = self.get_user_team_id(user_id)
        if team_id is not None:
            # User is already in a team.
            return False
        # Select a round based on the user's badges.
        round_id = self.select_round_with_badges(badges)
        # Generate an unused code.
        code = generate_access_code()
        while self.get_team_id_by_code(code) is not None:
            code = generate_access_code()
        # Create the team.
        teams = self.db.tables.teams
        query = self.db.query(teams).insert({
            teams.created_at: datetime.utcnow(),
            teams.round_id: round_id,
            teams.question_id: None,
            teams.code: code
        })
        team_id = self.db.insert(query)
        # Create the team_members row.
        self.add_team_member(team_id, user_id,
                             is_selected=True, is_creator=True)
        # Update the user's team_id.
        self.set_user_team_id(user_id, team_id)
        return True

    def join_team(self, user_id, team_id, user_badges):
        """ Add a user to a team.
            Registration for the team's round must be open.
            Return a boolean indicating if the team member was added.
        """
        # Verify that the user exists and does not already belong to a team.
        current_team_id = self.get_user_team_id(user_id)
        if current_team_id is not None:
            # User is already in a team.
            return False
        # Verify that the team exists, is open, and get its round_id.
        team = self.load_team(
            self.db.tables.teams, team_id, ['is_open, round_id'])
        if not team['is_open']:
            # Team is closed.
            return False
        round_id = team['round_id']
        # Verify that the round is open for registration.
        if not self.is_round_registration_open(round_id):
            return False
        # Look up the badges that grant access to the team's round, to
        # figure out whether the user is selected for that round.
        badges = self.db.tables.badges
        if len(user_badges) == 0:
            is_selected = False
        else:
            row = self.db.first(
                self.db.query(badges).fields(badges.id)
                    .where(badges.round_id == round_id)
                    .where(badges.symbol.in_(user_badges))
                    .where(badges.is_active))
            is_selected = row is not None
        # Create the team_members row.
        self.add_team_member(team_id, user_id, is_selected=is_selected)
        # Update the user's team_id.
        self.set_user_team_id(user_id, team_id)
        return True

    def leave_team(self, user_id):
        """ Remove a user from their team.
        """
        # The user must be member of a team.
        team_id = self.get_user_team_id(user_id)
        if team_id is None:
            return False
        # The team must not have accessed the question.
        team = self.load_team(team_id)
        if team['question_id'] is not None:
            return False
        # The round must be open  for registration.
        if not self.is_round_registration_open(team['round_id']):
            return False
        # Clear the user's team_id.
        self.set_user_team_id(user_id, None)
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

    # --- private methods below ---

    def load_team(self, team_id):
        keys = [
            'id', 'created_at', 'round_id', 'question_id', 'code', 'is_open'
        ]
        result = self.load_row(self.db.tables.teams, team_id, keys)
        result['is_open'] = self.db.view_bool(result['is_open'])
        return result

    def load_row(self, table, id, keys):
        query = self.db.query(table)
        query = query.fields(*[getattr(table, key) for key in keys])
        query = query.where(table.id == id)
        row = self.db.first(query)
        return {key: row[i] for i, key in enumerate(keys)}

    def view_user_team(self, team):
        """ Return the user-view for a team.
            Currently empty.
        """
        members = self.view_team_members(team['id'])
        creator = [m for m in members if m['is_creator']]
        return {
            'id': team['id'],
            'code': team['code'],
            'is_open': team['is_open'],
            'creator': creator[0]['user'],
            'members': members
        }

    def view_team_members(self, team_id):
        team_members = self.db.tables.team_members
        users = self.db.tables.users
        query = self.db.query(team_members & users)
        query = query.where(team_members.user_id == users.id)
        query = query.where(team_members.team_id == team_id)
        query = query.fields(
            team_members.joined_at,
            team_members.is_selected,
            team_members.is_creator,
            users.id,
            users.username)
        query = query.order_by(team_members.joined_at)
        members = []
        for row in self.db.all(query):
            members.append({
                'joined_at': row[0],
                'is_selected': self.db.view_bool(row[1]),
                'is_creator': self.db.view_bool(row[2]),
                'user': {
                    'id': row[3],
                    'username': row[4]
                }
            })
        return members

    def view_user_round(self, round_id):
        """ Return the user-view for a round.
        """
        if round_id is None:
            return None
        rounds = self.db.tables.rounds
        (title, allow_register) = self.db.first(
            self.db.query(rounds)
                .fields(rounds.title, rounds.allow_register)
                .where(rounds.id == round_id))
        return {
            'title': title,
            'allow_register': self.db.view_bool(allow_register)
        }

    def view_user_question(self, question_id):
        """ Return the user-view for a question.
        """
        if question_id is None:
            return None
        questions = self.db.tables.questions
        (team_data,) = self.db.first(
            self.db.query(questions)
                .fields(questions.team_data)
                .where(questions.id == question_id))
        return {
            'team_data': team_data
        }

    def add_team_member(self, team_id, user_id,
                        is_selected=False, is_creator=False):
        team_members = self.db.tables.team_members
        query = self.db.query(team_members).insert({
            team_members.team_id: team_id,
            team_members.user_id: user_id,
            team_members.joined_at: datetime.utcnow(),
            team_members.is_selected: is_selected,
            team_members.is_creator: is_creator
        })
        self.db.execute(query)

    def select_round_with_badges(self, badges):
        rounds = self.db.tables.rounds
        badges_table = self.db.tables.badges
        row = self.db.first(
            self.db.query(rounds & badges_table)
                .fields(rounds.id)
                .where(badges_table.round_id == rounds.id)
                .where(badges_table.symbol.in_(badges))
                .where(badges_table.is_active)
                .where(rounds.allow_register))
        if row is None:
            # If no round was found, the user does not have a badge that
            # grants them access to a round and we cannot create a team.
            return False
        (round_id,) = row
        return round_id

    def is_round_registration_open(self, round_id):
        rounds = self.db.tables.rounds
        (allow_register,) = self.db.first(
            self.db.query(rounds)
                .fields(rounds.allow_register)
                .where(rounds.id == round_id))
        return self.db.view_bool(allow_register)

    def get_user_foreign_id(self, user_id):
        users = self.db.tables.users
        return self.get_field(users, user_id, users.foreign_id)

    def get_user_team_id(self, user_id):
        users = self.db.tables.users
        return self.get_field(users, user_id, users.team_id)

    def get_team_round_id(self, team_id):
        teams = self.db.tables.teams
        return self.get_field(teams, team_id, teams.round_id)

    def get_team_question_id(self, team_id):
        teams = self.db.tables.teams
        return self.get_field(teams, team_id, teams.question_id)

    def get_team_id_by_code(self, code):
        teams = self.db.tables.teams
        row = self.db.first(
            self.db.query(teams)
                .fields(teams.id)
                .where(teams.code == code))
        if row is None:
            return None
        (team_id,) = row
        return team_id

    def set_user_team_id(self, user_id, team_id):
        users = self.db.tables.users
        query = self.db.query(users).where(users.id == user_id) \
            .update({users.team_id: team_id})
        self.db.execute(query)

    def get_field(self, table, id, field):
        row = self.db.first(
            self.db.query(table)
                .fields(field)
                .where(table.id == id))
        if row is None:
            raise InputError('no such row')
        return row[0]
