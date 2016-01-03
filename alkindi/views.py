
from alkindi.globals import app


def view_user_seed(user_id):
    init = {}
    user = app.model.load_user(user_id)
    init['user'] = view_user(user)
    team_id = user['team_id']
    if team_id is None:
        # If the user has no team, we look for a round to which a
        # badge grants access.
        badges = user['badges']
        round_id = app.model.select_round_with_badges(badges)
        if round_id is not None:
            round = app.model.load_round(round_id)
            init['round'] = view_user_round(round)
        return init
    # Add team data.
    team = app.model.load_team(team_id)
    init['team'] = view_user_team(team)
    # Add round data.
    round = app.model.load_round(team['round_id'])
    init['round'] = view_user_round(round)
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


def view_user_team(team):
    """ Return the user-view for a team.
    """
    members = view_team_members(team['id'])
    creator = [m for m in members if m['is_creator']]
    return {
        'id': team['id'],
        'code': team['code'],
        'is_open': team['is_open'],
        'is_locked': team['is_locked'],
        'creator': creator[0]['user'],
        'members': members
    }


def view_team_members(team_id):
    team_members = app.db.tables.team_members
    users = app.db.tables.users
    query = app.db.query(team_members & users)
    query = query.where(team_members.user_id == users.id)
    query = query.where(team_members.team_id == team_id)
    query = query.fields(
        team_members.joined_at,    # 0
        team_members.is_selected,  # 1
        team_members.is_creator,   # 2
        users.id,                  # 3
        users.username,            # 4
        users.firstname,           # 5
        users.lastname,            # 6
    )
    query = query.order_by(team_members.joined_at)
    members = []
    for row in app.db.all(query):
        view = {
            'joined_at': row[0],
            'is_selected': app.db.view_bool(row[1]),
            'is_creator': app.db.view_bool(row[2]),
            'user': {
                'id': row[3],
                'username': row[4],
                'firstname': row[5],
                'lastname': row[6],
            }
        }
        members.append(view)
    return members


def view_user_attempt(attempt):
    keys = ['id', 'created_at', 'closes_at', 'is_current', 'is_training']
    # TODO: add info on which user has submitted their code.
    return {key: round[key] for key in keys}


def view_user_round(round):
    """ Return the user-view for a round.
    """
    keys = [
        'id', 'title',
        'allow_register', 'register_from', 'register_until',
        'allow_access', 'access_from', 'access_until',
        'min_team_size', 'max_team_size', 'min_team_ratio'
    ]
    return {key: round[key] for key in keys}


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
