
from datetime import datetime


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
        query = self.db.query().tables(users) \
            .fields(users.id, users.username, users.team_id) \
            .where(users.foreign_id == foreign_id)
        user_id, username, team_id = self.db.first(query)
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
                    .where(team_members.team_id == team_id &
                           team_members.user_id == user_id))
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
            self.db.query()
                .tables(rounds)
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
        rounds = self.db.tables.rounds
        badges_table = self.db.tables.badges
        # Select a round based on the user's badges.
        row = self.db.first(
            self.db.query().tables(rounds & badges_table)
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
        # Generate an unused code.
        code = 'canard'
        while self.get_team_with_code(code) is not None:
            code = code + '1'
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
        team_members = self.db.tables.team_members
        query = self.db.query(team_members).insert({
            team_members.team_id: team_id,
            team_members.user_id: user_id,
            team_members.joined_at: datetime.utcnow(),
            team_members.is_selected: True,
            team_members.is_creator: True
        })
        self.db.execute(query)
        return True

    def get_team_with_code(self, code):
        teams = self.db.tables.teams
        row = self.db.first(
            self.db.query().tables(teams)
                .fields(teams.id)
                .where(teams.code == code))
        if row is None:
            return None
        (team_id,) = row
        return team_id
