
def load_round_task(db, round_task_id, for_update=False):
    cols = [
        'id', 'round_id', 'task_id', 'have_training_attempt',
        'max_timed_attempts', 'hide_scores', 'attempt_duration',
        'max_attempt_answers', 'max_score'
    ]
    row = db.load_row(
        db.tables.round_tasks, round_task_id, cols,
        for_update=for_update)
    for key in ['have_training_attempt']:
        row[key] = db.load_bool(row[key])
    return row


def load_round_tasks(db, round_id):
    round_tasks = db.tables.round_tasks
    tasks = db.tables.tasks
    cols = [
        ('id', round_tasks.id),
        ('task_id', tasks.id),
        ('title', tasks.title),
        ('have_training_attempt', round_tasks.have_training_attempt),
        ('max_timed_attempts', round_tasks.max_timed_attempts),
        ('hide_scores', round_tasks.hide_scores),
        ('attempt_duration', round_tasks.attempt_duration),
        ('max_attempt_answers', round_tasks.max_attempt_answers),
        ('max_score', round_tasks.max_score)
    ]
    query = db.query(round_tasks & tasks.on(round_tasks.task_id == tasks.id)) \
        .fields([col[1] for col in cols]) \
        .where(round_tasks.round_id == round_id) \
        .order_by(round_tasks.ordinal)
    rows = db.all_rows(query, cols)
    results = []
    for row in rows:
        result = {}
        for key in ['id', 'task_id', 'title', 'max_timed_attempts',
                    'attempt_duration', 'max_attempt_answers', 'max_score']:
            result[key] = row[key]
        for key in ['have_training_attempt', 'hide_scores']:
            result[key] = db.load_bool(row[key])
        results.append(result)
    return results
