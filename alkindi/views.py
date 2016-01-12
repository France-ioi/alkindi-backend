
from datetime import datetime

from alkindi.globals import app
from alkindi.model import ModelError


AllowHtmlAttrs = {
    '*': ['class'],
    'a': ['href', 'title'],
}

AllowHtmlTags = [
    'div', 'span', 'p', 'ul', 'ol', 'li', 'h1', 'h2', 'h3',
    'b', 'i', 'strong', 'em'
]


def view_requesting_user(user_id):
    view = {}
    view['now'] = now = datetime.utcnow()
    user = app.model.load_user(user_id)
    if user is None:
        return None
    view['user'] = view_user(user)
    team_id = user['team_id']

    if team_id is None:
        # If the user has no team, we look for a round to which a
        # badge grants access.
        badges = user['badges']
        round_id = app.model.select_round_with_badges(badges)
        if round_id is not None:
            round_ = app.model.load_round(round_id, now)
            view['round'] = view_round(round_)
        return view

    # Load round, team, members.
    team = app.model.load_team(team_id)
    round_ = app.model.load_round(team['round_id'], now)
    view['team'] = view_team(team, round_)
    view['round'] = view_round(round_)

    # Do not return attempts if the team is invalid.
    if view['team']['is_invalid']:
        return view

    attempts = app.model.load_team_attempts(team_id)
    view['attempts'] = view_round_attempts(round_, attempts)
    # Find the team's current attempt, and the current attempt's view.
    current_attempt = None
    for attempt in attempts:
        if attempt['is_current']:
            current_attempt = attempt
    if current_attempt is None:
        return view

    # Focus on the current attempt.
    current_attempt_view = None
    for attempt_view in view['attempts']:
        if current_attempt['id'] == attempt_view.get('id'):
            current_attempt_view = attempt_view
    attempt_id = current_attempt['id']
    view['current_attempt_id'] = attempt_id
    members_view = view['team']['members']
    access_codes = app.model.load_unlocked_access_codes(attempt_id)
    add_members_access_codes(members_view, access_codes)
    if current_attempt['is_training']:
        needs_codes = not have_one_code(members_view)
    else:
        needs_codes = not have_code_majority(members_view)
    current_attempt_view['needs_codes'] = needs_codes
    # Add task data, if available.
    try:
        task = app.model.load_task_team_data(attempt_id)
    except ModelError:
        task = None
    if task is not None:
        view['task'] = task
        view['task']['url'] = round_['task_url']
        current_attempt_view['has_task'] = True
        # Give the user the id of their latest revision for the
        # current attempt, to be loaded into the crypto tab on
        # first access.
        revision_id = app.model.load_user_latest_revision_id(
            user_id, attempt_id)
        view['my_latest_revision_id'] = revision_id

    return view


def view_user(user):
    """ Return the user-view for a user.
    """
    keys = ['id', 'username', 'firstname', 'lastname']
    return {key: user[key] for key in keys}


def view_team(team, round_=None):
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
        result['round_access'] = list(causes.keys())
        result['is_invalid'] = len(causes) != 0
    return result


def add_members_access_codes(members, access_codes):
    code_map = {code['user_id']: code for code in access_codes}
    for member in members:
        user_id = member['user_id']
        if user_id in code_map:
            member['access_code'] = code_map[user_id]['code']


def have_one_code(members):
    n_codes = len([m for m in members if 'access_code' in m])
    return n_codes >= 1


def have_code_majority(members):
    n_members = len(members)
    n_codes = len([m for m in members if 'access_code' in m])
    return n_codes * 2 >= n_members


def validate_members_for_round(members, round_):
    """ Return a dict whose keys indicate reasons why the given
        team members cannot start training for the given round.
    """
    result = {}
    n_members = len(members)
    n_qualified = len([m for m in members if m['is_qualified']])
    if n_members < round_['min_team_size']:
        result['team_too_small'] = True
    if n_members > round_['max_team_size']:
        result['team_too_large'] = True
    if n_qualified < n_members * round_['min_team_ratio']:
        result['insufficient_qualified_users'] = True
    return result


def view_round(round_):
    """ Return the user-view for a round.
    """
    keys = [
        'id', 'title',
        'registration_opens_at', 'training_opens_at',
        'is_registration_open', 'is_training_open',
        'min_team_size', 'max_team_size', 'min_team_ratio',
        'max_attempts', 'max_answers'
    ]
    return {key: round_[key] for key in keys}


def view_user_workspace_revision(workspace_revision):
    return workspace_revision


def view_user_task(user_id):
    user = app.model.load_user(user_id)
    team_id = user['team_id']
    attempt = app.model.load_team_current_attempt(team_id)
    return app.model.load_task_team_data(attempt['id'])


def view_revision(revision):
    keys = [
        'id', 'parent_id', 'creator_id', 'workspace_id',
        'created_at', 'title', 'is_active', 'is_precious',
    ]
    return {key: revision[key] for key in keys}


def view_workspace(workspace):
    keys = [
        'id', 'created_at', 'updated_at', 'title'
        # 'attempt_id' omitted
    ]
    return {key: workspace[key] for key in keys}


def add_revisions(view, attempt_id):
    # Load revisions.
    revisions = app.model.load_attempt_revisions(attempt_id)
    # Load related entities.
    user_ids = set()
    workspace_ids = set()
    for revision in revisions:
        user_ids.add(revision['creator_id'])
        workspace_ids.add(revision['workspace_id'])
    users = app.model.load_users(user_ids)
    workspaces = app.model.load_workspaces(workspace_ids)
    # Prepare views.
    view['users'] = [view_user(user) for user in users]
    view['workspaces'] = \
        [view_workspace(workspace) for workspace in workspaces]
    view['revisions'] = revisions


def add_answers(view, attempt_id):
    answers = app.model.load_limited_attempt_answers(attempt_id)
    view['answers'] = answers
    user_ids = set()
    for answer in answers:
        user_ids.add(answer['submitter_id'])
    users = app.model.load_users(user_ids)
    user_views = [view_user(user) for user in users]
    view['users'] = user_views


def view_round_attempts(round_, attempts):
    openNext = False
    views = []
    for attempt in attempts:
        views.append(view_attempt(attempt))
        if attempt['is_completed']:
            openNext = True
    if len(views) == 0:
        views.append({
            'ordinal': 0, 'is_current': True, 'is_training': True})
    while len(views) <= round_['max_attempts']:
        views.append({
            'ordinal': len(views), 'is_unsolved': True,
            'is_current': openNext, 'duration': 60})  # XXX
        openNext = False
    while not views[0]['is_current']:
        views = views[1:] + views[:1]
    return views


def view_answers(answers):
    user_ids = set()
    for answer in answers:
        user_ids.add(answer['submitter_id'])
    users = app.model.load_users(user_ids)
    user_views = [view_user(user) for user in users]
    return {
        'answers': answers,
        'users': user_views
    }


def view_attempt(attempt):
    keys = [
        'id', 'ordinal', 'created_at', 'started_at', 'closes_at',
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved',
        'is_closed', 'is_completed'
    ]
    view = {key: attempt[key] for key in keys}
    if not attempt['is_training']:
        view['duration'] = 60
    return view
