
from datetime import datetime

from alkindi.errors import ModelError
from alkindi.model.rounds import load_round, find_round_ids_with_badges
from alkindi.model.users import load_user, load_users
from alkindi.model.teams import load_team
from alkindi.model.team_members import load_team_members
from alkindi.model.attempts import (
    load_team_attempts, get_user_current_attempt_id)
from alkindi.model.access_codes import load_unlocked_access_codes
from alkindi.model.tasks import load_task_team_data
from alkindi.model.answers import load_limited_attempt_answers
from alkindi.model.workspace_revisions import (
    load_user_latest_revision_id, load_attempt_revisions)
from alkindi.model.workspaces import load_workspaces


AllowHtmlAttrs = {
    '*': ['class'],
    'a': ['href', 'title'],
}

AllowHtmlTags = [
    'div', 'span', 'p', 'ul', 'ol', 'li', 'h1', 'h2', 'h3',
    'b', 'i', 'strong', 'em'
]


def view_requesting_user(db, user_id):
    view = {}
    view['now'] = now = datetime.utcnow()
    user = load_user(db, user_id)
    if user is None:
        return None
    view['user'] = view_user(user)
    team_id = user['team_id']

    if team_id is None:
        # If the user has no team, we look for a round to which a
        # badge grants access.
        badges = user['badges']
        round_ids = find_round_ids_with_badges(db, badges, now)
        if len(round_ids) > 0:
            # TODO: resolve this somehow, for example by returning
            # the round views to the user and letting them choose.
            # For now, pick the first one (which has the greatest id).
            round_id = round_ids[0]
            round_ = load_round(db, round_id, now)
            view['round'] = view_round(round_)
        return view

    # Load round, team, members.
    team = load_team(db, team_id)
    round_ = load_round(db, team['round_id'], now)  # XXX team/round
    view['team'] = view_team(db, team, round_)
    view['round'] = view_round(round_)

    # Do not return attempts if the team is invalid.
    if view['team']['is_invalid']:
        return view

    attempts = load_team_attempts(db, team_id, now)  # XXX team/round
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
    access_codes = load_unlocked_access_codes(db, attempt_id)
    add_members_access_codes(members_view, access_codes)
    if current_attempt['is_training']:
        needs_codes = not have_one_code(members_view)
    else:
        needs_codes = not have_code_majority(members_view)
    current_attempt_view['needs_codes'] = needs_codes
    # Add task data, if available.
    try:
        task = load_task_team_data(db, attempt_id)
    except ModelError:
        task = None
    if task is not None:
        view['task'] = task
        view['task']['front'] = round_['task_front']
        current_attempt_view['has_task'] = True
        # Give the user the id of their latest revision for the
        # current attempt, to be loaded into the crypto tab on
        # first access.
        revision_id = load_user_latest_revision_id(
            db, user_id, attempt_id)
        view['my_latest_revision_id'] = revision_id

    return view


def view_user(user):
    """ Return the user-view for a user.
    """
    keys = ['id', 'username', 'firstname', 'lastname']
    return {key: user[key] for key in keys}


def view_team(db, team, round_=None):  # XXX team/round
    """ Return the user-view for a team.
    """
    keys = ['id', 'code', 'is_open', 'is_locked', 'score', 'parent_id']
    result = {key: team[key] for key in keys}
    members = load_team_members(db, team['id'], users=True)
    result['members'] = members
    creators = [m for m in members if m['is_creator']]
    if len(creators) > 0:
        result['creator'] = creators[0]['user']
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
        'max_attempts', 'max_answers', 'status', 'allow_team_changes'
    ]
    return {key: round_[key] for key in keys}


def view_user_workspace_revision(workspace_revision):
    return workspace_revision


def view_user_task(db, user_id):
    attempt_id = get_user_current_attempt_id(db, user_id)
    return load_task_team_data(db, attempt_id)


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


def add_revisions(db, view, attempt_id):
    # Load revisions.
    revisions = load_attempt_revisions(db, attempt_id)
    # Load related entities.
    user_ids = set()
    workspace_ids = set()
    for revision in revisions:
        user_ids.add(revision['creator_id'])
        workspace_ids.add(revision['workspace_id'])
    users = load_users(db, user_ids)
    workspaces = load_workspaces(db, workspace_ids)
    # Prepare views.
    view['users'] = [view_user(user) for user in users]
    view['workspaces'] = \
        [view_workspace(workspace) for workspace in workspaces]
    view['revisions'] = revisions


def add_answers(db, view, attempt_id):
    answers = load_limited_attempt_answers(db, attempt_id)
    view['answers'] = answers
    user_ids = set()
    for answer in answers:
        user_ids.add(answer['submitter_id'])
    users = load_users(db, user_ids)
    user_views = [view_user(user) for user in users]
    view['users'] = user_views


def view_round_attempts(round_, attempts):
    openNext = False
    views = []
    for attempt in attempts:
        views.append(view_attempt(attempt, round_))
        openNext = attempt['is_completed']
    if len(views) == 0:
        if round_['have_training_attempt']:
            views.append({
                'ordinal': 0, 'is_current': True, 'is_training': True})
        else:
            openNext = True
    if round_['max_attempts'] is None:
        views.append({
            'ordinal': len(views), 'is_unsolved': True,
            'is_current': openNext, 'duration': round_['duration']})
    else:
        while len(views) <= round_['max_attempts']:
            views.append({
                'ordinal': len(views), 'is_unsolved': True,
                'is_current': openNext, 'duration': round_['duration']})
            openNext = False
    while not views[0]['is_current']:
        views = views[1:] + views[:1]
    return views


def view_answers(db, answers):
    user_ids = set()
    for answer in answers:
        user_ids.add(answer['submitter_id'])
    users = load_users(db, user_ids)
    user_views = [view_user(user) for user in users]
    return {
        'answers': answers,
        'users': user_views
    }


def view_attempt(attempt, round_):
    keys = [
        'id', 'ordinal', 'created_at', 'started_at', 'closes_at',
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved',
        'is_closed', 'is_completed', 'max_score'
    ]
    view = {key: attempt[key] for key in keys}
    if not attempt['is_training']:
        view['duration'] = round_['duration']
    return view
