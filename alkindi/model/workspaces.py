

def workspace_columns(db):
    workspaces = db.tables.workspaces
    return [
        ('id', workspaces.id),
        ('attempt_id', workspaces.attempt_id),
        ('created_at', workspaces.created_at),
        ('updated_at', workspaces.updated_at),
        ('title', workspaces.title)
    ]


def load_workspace(db, workspace_id, for_update=False):
    workspaces = db.tables.workspaces
    cols = workspace_columns(db)
    query = db.query(workspaces) \
        .where(workspaces.id == workspace_id)
    return db.first_row(query, cols)


def load_workspaces(db, workspace_ids):
    if len(workspace_ids) == 0:
        return []
    workspaces = db.tables.workspaces
    cols = workspace_columns(db)
    query = db.query(workspaces) \
        .where(workspaces.id.in_(list(workspace_ids)))
    return db.all_rows(query, cols)


def create_attempt_workspace(db, attempt_id, now, title='None'):
    workspaces = db.tables.workspaces
    workspace_id = db.insert_row(workspaces, {
        'created_at': now,
        'updated_at': now,
        'attempt_id': attempt_id,
        'title': title,
    })
    return workspace_id


def get_attempt_default_workspace_id(db, attempt_id):
    # XXX This code is temporary, and valid only because we currently
    # have a single workspace created for each attempt.
    workspaces = db.tables.workspaces
    query = db.query(workspaces) \
        .where(workspaces.attempt_id == attempt_id) \
        .fields(workspaces.id)
    row = db.first(query)
    return None if row is None else row[0]
