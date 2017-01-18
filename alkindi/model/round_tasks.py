
def round_task_columns(db):
    round_tasks = db.tables.round_tasks
    tasks = db.tables.tasks
    return [
        ('id', round_tasks.id),
        ('title', round_tasks.title),
        ('round_id', round_tasks.round_id),
        ('ordinal', round_tasks.ordinal),
        ('attempt_duration', round_tasks.attempt_duration),
        ('max_timed_attempts', round_tasks.max_timed_attempts),
        ('max_attempt_answers', round_tasks.max_attempt_answers),
        ('hide_scores', round_tasks.hide_scores, 'bool'),
        ('have_training_attempt', round_tasks.have_training_attempt, 'bool'),
        ('max_score', round_tasks.max_score),
        ('generate_params', round_tasks.generate_params, 'json'),
        ('task_id', tasks.id),
        ('frontend_url', tasks.frontend_url)
    ]


def load_round_task(db, round_task_id, for_update=False):
    round_tasks = db.tables.round_tasks
    tasks = db.tables.tasks
    cols = round_task_columns(db)
    query = db.query(round_tasks & tasks.on(round_tasks.task_id == tasks.id)) \
        .where(round_tasks.id == round_task_id)
    return db.first_row(query, cols)


def load_round_tasks(db, round_id):
    round_tasks = db.tables.round_tasks
    tasks = db.tables.tasks
    cols = round_task_columns(db)
    query = db.query(round_tasks & tasks.on(round_tasks.task_id == tasks.id)) \
        .where(round_tasks.round_id == round_id) \
        .order_by(round_tasks.ordinal)
    return db.all_rows(query, cols)
