
from alkindi.globals import app


def view_user(user_id, badges):
    """ Return the user-view for the user with the given id.
    """
    user = app.model.load_user(user_id)
    keys = ['id', 'username', 'firstname', 'lastname']
    result = {key: user[key] for key in keys}
    team_id = user['team_id']
    if team_id is None:
        # If the user has not team, we look for a round to which a
        # badge grants access.
        round_id = app.model.select_round_with_badges(badges)
        if round_id is not None:
            round = app.model.load_round(round_id)
            result['accessible_round'] = view_user_round(round)
    else:
        # Add 'team', 'round' and 'question' info.
        team = app.model.load_team(team_id)
        result['team'] = view_user_team(team)
        round_id = team['round_id']
        round = app.model.load_round(round_id)
        result['round'] = view_user_round(round)
        if team['question_id'] is None:
            result['question_blocked'] = \
                app.model.test_question_blocked(team, round)
        else:
            result['question'] = view_user_question(team['question_id'])
        # Add is_selected
        team_members = app.db.tables.team_members
        (is_selected,) = app.db.first(
            app.db.query(team_members)
                  .fields(team_members.is_selected)
                  .where(team_members.team_id == team_id)
                  .where(team_members.user_id == user_id))
        result['is_selected'] = app.db.view_bool(is_selected)
    return result


def view_user_team(team):
    """ Return the user-view for a team.
        Currently empty.
    """
    members = view_team_members(team['id'])
    creator = [m for m in members if m['is_creator']]
    return {
        'id': team['id'],
        'code': team['code'],
        'is_open': team['is_open'],
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
        team_members.joined_at,
        team_members.is_selected,
        team_members.is_creator,
        users.id,
        users.username,
        users.firstname,
        users.lastname)
    query = query.order_by(team_members.joined_at)
    members = []
    for row in app.db.all(query):
        members.append({
            'joined_at': row[0],
            'is_selected': app.db.view_bool(row[1]),
            'is_creator': app.db.view_bool(row[2]),
            'user': {
                'id': row[3],
                'username': row[4],
                'firstname': row[5],
                'lastname': row[6],
            }
        })
    return members


def view_user_round(round):
    """ Return the user-view for a round.
    """
    keys = [
        'title',
        'allow_register', 'register_from', 'register_until',
        'allow_access', 'access_from', 'access_until',
        'min_team_size', 'max_team_size', 'min_team_ratio'
    ]
    return {key: round[key] for key in keys}


def view_user_question(question_id):
    """ Return the user-view for a question.
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
