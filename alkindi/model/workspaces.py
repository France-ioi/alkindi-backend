

def load_workspaces(db, workspace_ids):
    keys = [
        'id', 'attempt_id',
        'created_at', 'updated_at', 'title'
    ]
    return db.load_rows(db.tables.workspaces, workspace_ids, keys)


def create_attempt_workspace(db, attempt_id, now, title='None'):
    workspaces = db.tables.workspaces
    workspace_id = db.insert_row(workspaces, {
        'created_at': now,
        'updated_at': now,
        'attempt_id': attempt_id,
        'title': title,
    })
    return workspace_id


def get_attempt_workspace_id(db, attempt_id):
    # XXX This code is temporary, and valid only because we currently
    # have a single workspace created for each attempt.
    workspaces = db.tables.workspaces
    query = db.query(workspaces) \
        .where(workspaces.attempt_id == attempt_id) \
        .fields(workspaces.id)
    row = db.first(query)
    return None if row is None else row[0]
