
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

    def view_user(self, foreign_id):
        """ Return the user-view for the user with the given foreign_id.
        """
        users = self.db.tables.users
        query = self.db.query(users) \
            .fields(users.id, users.username, users.team_id) \
            .where(users.foreign_id == foreign_id)
        row = self.db.first(query)
        if row is None:
            raise InputError('no such user')
        (user_id, username, team_id) = row
        result = {
            'username': username,
        }
        if team_id is not None:
            result['team'] = self.view_user_team(team_id)
            teams = self.db.tables.teams
            # Add 'round' and 'question' info.
            (round_id, question_id) = self.db.first(
                self.db.query(teams)
                    .fields(teams.round_id, teams.question_id)
                    .where(teams.id == team_id))
            result['round'] = self.view_user_round(round_id)
            result['question'] = self.view_user_question(question_id)
            # Add is_selected
            team_members = self.db.tables.team_members
            (is_selected,) = self.db.first(
                self.db.query(team_members)
                    .fields(team_members.is_selected)
                    .where((team_members.team_id == team_id) &
                           (team_members.user_id == user_id)))
            result['is_selected'] = self.db.view_bool(is_selected)
        return result

    def view_user_team(self, team_id):
        """ Return the user-view for a team.
            Currently empty.
        """
        return {}

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
            teams.creator_id: user_id,
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
        # Verify that the team exists, and get its round_id.
        round_id = self.get_team_round_id(team_id)
        # Verify that the round is open for registration.
        if not self.is_round_registration_open(round_id):
            return False
        # Look up the badges that grant access to the team's round, to
        # figure out whether the user is selected for that round.
        badges = self.db.tables.badges
        if len(user_badges) == 0:
            is_selected = False
        else:
            row = self.db.first(self.db.query(badges).fields(badges.id).where(
                (badges.round_id == round_id) &
                (badges.symbol.in_(user_badges)) &
                badges.is_active))
            is_selected = row is not None
        # Create the team_members row.
        self.add_team_member(team_id, user_id, is_selected=is_selected)
        # Update the user's team_id.
        self.set_user_team_id(user_id, team_id)
        return True

    # --- private methods below ---

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
                .where(
                    badges_table.round_id == rounds.id &
                    badges_table.symbol.in_(badges) &
                    badges_table.is_active &
                    rounds.allow_register))
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
