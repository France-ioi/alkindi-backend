
def load_task(db, task_id, for_update=False):
    keys = ['id', 'created_at', 'updated_at', 'title', 'backend_url']
    tasks = db.tables.tasks
    result = db.load_row(tasks, task_id, keys, for_update=for_update)
    return result
