
from alkindi.errors import ModelError
from alkindi.model.workspaces import (
    load_workspace, get_attempt_default_workspace_id)


def load_workspace_revision(db, workspace_revision_id):
    keys = [
        'id', 'title', 'workspace_id', 'created_at', 'creator_id',
        'parent_id', 'is_active', 'is_precious', 'state'
    ]
    workspace_revisions = db.tables.workspace_revisions
    result = db.load_row(
        workspace_revisions, workspace_revision_id, keys)
    for key in ['is_active', 'is_precious']:
        result[key] = db.load_bool(result[key])
    for key in ['state']:
        result[key] = db.load_json(result[key])
    return result


def load_attempt_revisions(db, attempt_id):
    # Load the revisions.
    workspaces = db.tables.workspaces
    answers = db.tables.answers
    revisions = db.tables.workspace_revisions
    cols = [
        ('id', revisions.id),
        ('title', revisions.title),
        ('parent_id', revisions.parent_id),
        ('created_at', revisions.created_at),
        ('creator_id', revisions.creator_id),
        ('is_precious', revisions.is_precious, 'bool'),
        ('is_active', revisions.is_active, 'bool'),
        ('workspace_id', revisions.workspace_id),
        ('score', answers.score)
    ]
    query = db.query(revisions & workspaces + answers) \
        .on((revisions.workspace_id == workspaces.id) &
            (revisions.id == answers.revision_id)) \
        .where(workspaces.attempt_id == attempt_id) \
        .order_by(revisions.created_at.desc())
    return db.all_rows(query, cols)


def store_revision(db, user_id, attempt_id, workspace_id, parent_id, title, state, now):
    if workspace_id is None:
        # Use the attempt's default workspace.
        workspace_id = get_attempt_default_workspace_id(db, attempt_id)
    else:
        # Verify that the workspace is attached to the attempt.
        # XXX actually, probably safe to verify that the workspace is
        # attached to an attempt belonging to the same participation.
        workspace = load_workspace(db, workspace_id)
        if workspace['attempt_id'] != attempt_id:
            raise ModelError('invalid workspace for attempt')
    # The parent revision, if set, must belong to the same workspace.
    if parent_id is not None:
        other_workspace_id = get_revision_workspace_id(db, parent_id)
        if other_workspace_id != workspace_id:
            parent_id = None
    revisions = db.tables.workspace_revisions
    revision_id = db.insert_row(revisions, {
        'workspace_id': workspace_id,
        'creator_id': user_id,
        'parent_id': parent_id,
        'title': title,
        'created_at': now,
        'is_active': False,
        'is_precious': True,
        'state': db.dump_json(state)
    })
    return revision_id


def load_user_latest_revision_id(db, user_id, attempt_id):
    workspaces = db.tables.workspaces
    workspace_revisions = db.tables.workspace_revisions
    query = db.query(workspaces & workspace_revisions) \
        .where(workspaces.attempt_id == attempt_id) \
        .where(workspace_revisions.workspace_id == workspaces.id) \
        .where(workspace_revisions.creator_id == user_id) \
        .order_by(workspace_revisions.created_at.desc()) \
        .fields(workspace_revisions.id)
    row = db.first(query)
    return None if row is None else row[0]


def get_workspace_revision_ownership(db, revision_id):
    """ Return the revision's (team_id, creator_id).
    """
    attempts = db.tables.attempts
    workspace_revisions = db.tables.workspace_revisions
    workspaces = db.tables.workspaces
    participations = db.tables.participations
    query = db.query(
        workspace_revisions &
        workspaces.on(workspaces.id == workspace_revisions.workspace_id) &
        attempts.on(attempts.id == workspaces.attempt_id) &
        participations.on(participations.id == attempts.participation_id))
    query = query \
        .where(workspace_revisions.id == revision_id) \
        .fields(participations.team_id, workspace_revisions.creator_id)
    row = db.first(query)
    return None if row is None else row


def get_revision_workspace_id(db, revision_id):
    """ Return the revision's workspace_id.
    """
    workspace_revisions = db.tables.workspace_revisions
    return db.load_scalar(
        table=workspace_revisions, value=revision_id,
        column='workspace_id')
