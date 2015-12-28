
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
        self.db.execute(query)

    def view_user(self, foreign_id):
        """ Return the user-view for the user with the given foreign_id.
        """
        users = self.db.tables.users
        query = self.db.query(users) \
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
            result['is_selected'] = is_selected
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
            'allow_register': allow_register
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
