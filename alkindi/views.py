
from datetime import datetime

from alkindi.errors import ModelError
from alkindi.model.rounds import (
    load_round, load_rounds, find_round_ids_with_badges)
from alkindi.model.round_tasks import load_round_tasks
from alkindi.model.users import load_user, load_users
from alkindi.model.teams import (
    load_team, count_teams_in_round, count_teams_in_round_region)
from alkindi.model.team_members import load_team_members
from alkindi.model.regions import load_region
from alkindi.model.participations import load_team_participations
from alkindi.model.attempts import (
    load_participation_attempts, get_user_current_attempt_id)
from alkindi.model.access_codes import load_unlocked_access_codes
from alkindi.model.task_instances import load_user_task_instance
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


def view_requesting_user(
        db, user_id=None, participation_id=None, attempt_id=None,
        is_admin=False):

    now = datetime.utcnow()
    view = {
        'now': now,
        'is_admin': is_admin
    }
    if user_id is None:
        return view

    #
    # Add the user.
    #
    user = load_user(db, user_id)
    if user is None:
        return view
    view['user_id'] = user_id
    view['user'] = view_user(user)
    team_id = user['team_id']

    #
    # Quick return path when the user has no team.
    #
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

    #
    # Add the team and team members.
    #
    team = load_team(db, team_id)
    members = load_team_members(db, team['id'], users=True)
    team_view = view['team'] = view_team(team, members)

    #
    # Add the team's participations.
    #
    participations = load_team_participations(db, team_id)
    round_ids = set()
    for participation in participations:
        round_ids.add(participation['round_id'])
    rounds = load_rounds(db, round_ids, now)
    view['participations'] = [
        view_team_participation(
            participation,
            rounds[participation['round_id']])
        for participation in participations
    ]
    if len(participations) == 0:
        return view

    # Mark the lastest (or selected) participation as current.
    if participation_id is None:
        participation = participations[-1]
    else:
        participation = get_by_id(participations, participation_id)
        if participation is None:
            return view
    view['participation_id'] = participation['id']
    for pview in view['participations']:
        if pview['id'] == participation['id']:
            pview['is_current'] = True

    #
    # Add the current participation's round.
    #
    round_id = participation['round_id']
    round_ = rounds[round_id]
    view['round'] = view_round(round_)

    #
    # Add the tasks for the current round.
    #
    round_tasks = load_round_tasks(db, round_id)
    view['round']['task_ids'] = [str(rt['id']) for rt in round_tasks]
    round_task_views = view['round_tasks'] = {
        str(rt['id']): view_round_task(rt) for rt in round_tasks
    }

    if False:  # XXX disabled
        # XXX Horrible constant initial_round_id, should be looked up in a
        #     competition table.
        initial_round_id = 2
        # Add total number of teams for the competition, and total number
        # of teams within the same region (if non-null).
        if team_view['rank'] is not None:
            team_view['n_teams'] = count_teams_in_round(db, initial_round_id)

    # XXX A team's validity should be checked against settings for a
    #     competition rather than a round.
    causes = validate_members_for_round(members, round_)
    team_view['round_access'] = list(causes.keys())
    team_view['is_invalid'] = len(causes) != 0

    # Add the user's region to the view.
    region = load_region(db, team['region_id'])
    if region is not None:
        team_view['region'] = view_region(region)
        if team_view['rank_region'] is not None:
            team_view['n_teams_region'] = count_teams_in_round_region(
                db, initial_round_id, region['id'])

    # Do not return attempts if the team is invalid.
    if team_view['is_invalid']:
        return view

    # Load the participation attempts.
    attempts = load_participation_attempts(db, participation['id'], now)
    view_task_attempts(attempts, round_task_views)
    print("attempts {} {}".format(attempt_id, attempts))

    # Find the requested attempt.
    current_attempt = get_by_id(attempts, attempt_id)
    if current_attempt is None:
        return view
    view['attempt_id'] = attempt_id

    # Focus on the current attempt.
    current_round_task = round_task_views[str(current_attempt['round_task_id'])]
    current_attempt_view = None
    for attempt_view in current_round_task['attempts']:
        if attempt_id == attempt_view.get('id'):
            current_attempt_view = attempt_view
    view['attempt'] = current_attempt_view
    view['round_task'] = current_round_task  # XXX duplicates attempts :(

    if False:  # Access codes are disabled
        members_view = view['team']['members']
        access_codes = load_unlocked_access_codes(db, attempt_id)
        add_members_access_codes(members_view, access_codes)
        if current_attempt['is_training']:
            needs_codes = not have_one_code(members_view)
        else:
            needs_codes = not have_code_majority(members_view)
        current_attempt_view['needs_codes'] = needs_codes

    # Add task instance data, if available.
    try:
        # XXX Previously load_task_instance_team_data which did not parse
        #     full_data.
        # /!\ task contains sensitive data
        # XXX If the round is closed, load and pass full_data?
        task_instance = load_user_task_instance(db, attempt_id)
    except ModelError:
        return view

    view['team_data'] = task_instance['team_data']

    # Add a list of the workspace revisions for this attempt.
    add_revisions(db, view, attempt_id)

    # Give the user the id of their latest revision for the
    # current attempt, to be loaded into the crypto tab on
    # first access.
    revision_id = load_user_latest_revision_id(
        db, user_id, attempt_id)
    view['my_latest_revision_id'] = revision_id

    return view


def get_by_id(items, id):
    try:
        return next(item for item in items if item['id'] == id)
    except StopIteration:
        return None


def view_user(user):
    """ Return the user-view for a user.
    """
    keys = ['id', 'username', 'firstname', 'lastname']
    return {key: user[key] for key in keys}


def view_team(team, members):
    """ Return the user-view for a team.
    """
    keys = ['id', 'code', 'is_open', 'is_locked', 'rank', 'rank_region']
    result = {key: team[key] for key in keys}
    result['members'] = members
    creators = [m for m in members if m['is_creator']]
    if len(creators) > 0:
        result['creator'] = creators[0]['user']
    return result


def view_region(region):
    keys = ['id', 'name']
    return {key: region[key] for key in keys}


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
        'id', 'title', 'status',
        'registration_opens_at', 'is_registration_open',
        'training_opens_at', 'is_training_open',
        'min_team_size', 'max_team_size', 'min_team_ratio',
        'allow_team_changes'
    ]
    return {key: round_[key] for key in keys}


def view_team_participation(participation, round_):
    view = {
        'id': participation['id'],
        'created_at': participation['created_at'],
        'round': view_round(round_),
        'is_qualified': participation['is_qualified'],
        'score': participation['score']
    }
    if participation['access_code'] is not None:
        if participation['access_code_entered']:
            view['access_code'] = 'provided'
        else:
            view['access_code'] = 'required'
    return view


def view_user_workspace_revision(workspace_revision):
    return workspace_revision


def view_user_task(db, user_id):
    attempt_id = get_user_current_attempt_id(db, user_id)
    return load_task_instance_team_data(db, attempt_id)


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
    hide_scores = view['round']['hide_scores']
    view['answers'] = [view_answer(answer, hide_scores) for answer in answers]
    user_ids = set()
    for answer in answers:
        user_ids.add(answer['submitter_id'])
    users = load_users(db, user_ids)
    user_views = [view_user(user) for user in users]
    view['users'] = user_views


def view_round_task(round_task):
    view = {
        'attempts': []
    }
    fields = [
        'id', 'task_id', 'title', 'frontend_url',
        'have_training_attempt', 'max_timed_attempts', 'hide_scores',
        'attempt_duration', 'max_attempt_answers', 'max_score',
    ]
    for key in fields:
        view[key] = round_task[key]
    return view


def view_task_attempts(attempts, round_task_views):
    # Add each attempt's view to its round_task's view.
    for attempt in attempts:
        round_task_id = str(attempt['round_task_id'])
        round_task_view = round_task_views[round_task_id]
        attempt_view = view_attempt(attempt, round_task_view)
        round_task_view['attempts'].append(attempt_view)


def view_answer(answer, hide_scores):
    view = {}
    cols = [
        'id', 'submitter_id', 'ordinal', 'created_at', 'answer']
    if not hide_scores:
        cols.append('score')
        cols.append('is_solution')
        cols.append('is_full_solution')
    for col in cols:
        view[col] = answer[col]
    return view


def view_attempt(attempt, round_task_view):
    print('view_attempt {} {}'.format(attempt, round_task_view))
    keys = [
        'id', 'ordinal', 'created_at', 'started_at', 'closes_at',
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved',
        'is_closed', 'is_completed'
    ]
    view = {key: attempt[key] for key in keys}
    if not attempt['is_training']:
        view['duration'] = round_task_view['attempt_duration']
    if not round_task_view['hide_scores']:
        view['score'] = score = attempt['max_score']
        view['ratio'] = score / round_task_view['max_score'] \
            if score is not None else None
    return view
