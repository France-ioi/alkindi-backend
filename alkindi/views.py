
from datetime import datetime

from alkindi.globals import app


def view_user_seed(user_id):
    init = {}
    user = app.model.load_user(user_id)
    if user is None:
        return None
    init['user'] = view_user(user)
    team_id = user['team_id']
    if team_id is None:
        # If the user has no team, we look for a round to which a
        # badge grants access.
        badges = user['badges']
        round_id = app.model.select_round_with_badges(badges)
        if round_id is not None:
            round_ = app.model.load_round(round_id)
            init['round'] = view_user_round(round_)
        return init
    # Add team and round data.
    team = app.model.load_team(team_id)
    round_ = app.model.load_round(team['round_id'])
    init['team'] = view_user_team(team, round_)
    init['round'] = view_user_round(round_)
    # Find the team's current attempt.
    attempt = app.model.load_team_current_attempt(team_id)
    if attempt is None:
        return init
    init['attempt'] = view_user_attempt(attempt)
    # Add question data, if available.
    question_id = attempt['question_id']
    if question_id is not None:
        init['question'] = view_user_question(question_id)
    return init


def view_user(user):
    """ Return the user-view for a user.
    """
    keys = ['id', 'username', 'firstname', 'lastname']
    return {key: user[key] for key in keys}


def view_user_team(team, round_=None):
    """ Return the user-view for a team.
    """
    members = app.model.load_team_members(team['id'], users=True)
    creator = [m for m in members if m['is_creator']]
    result = {
        'id': team['id'],
        'code': team['code'],
        'is_open': team['is_open'],
        'is_locked': team['is_locked'],
        'creator': creator[0]['user'],
        'members': members
    }
    if round_ is not None:
        causes = validate_members_for_round(members, round_)
        result['round_access'] = causes
        result['is_invalid'] = len(causes) != 0
    return result


def validate_members_for_round(members, round_):
    """ Return a dict whose keys indicate reasons why the given
        team members cannot start training for the given round.
    """
    result = {}
    now = datetime.now()
    if now < round_['training_opens_at']:
        result['has_not_started'] = True
    n_members = len(members)
    n_qualified = len([m for m in members if m['is_qualified']])
    if n_members < round_['min_team_size']:
        result['team_too_small'] = True
    if n_members > round_['max_team_size']:
        result['team_too_large'] = True
    if n_qualified < n_members * round_['min_team_ratio']:
        result['insufficient_qualified_users'] = True
    return result


def view_user_attempt(attempt):
    keys = ['id', 'created_at', 'closes_at', 'is_current', 'is_training']
    # TODO: add info on which user has submitted their code.
    return {key: attempt[key] for key in keys}


def view_user_round(round_):
    """ Return the user-view for a round.
    """
    keys = [
        'id', 'title',
        'registration_opens_at', 'training_opens_at',
        'min_team_size', 'max_team_size', 'min_team_ratio'
    ]
    return {key: round_[key] for key in keys}


def view_user_question(question_id):
    """ Return the user-view for a question.
        Avoid loading the full question data.
    """
    if question_id is None:
        return None
    questions = app.db.tables.questions
    (team_data,) = app.db.first(
        app.db.query(questions)
              .fields(questions.team_data)
              .where(questions.id == question_id))
    return {
        'team_data': team_data
    }
