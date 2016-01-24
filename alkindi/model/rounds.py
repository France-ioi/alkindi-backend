
def load_round(db, round_id, now=None):
    keys = [
        'id', 'created_at', 'updated_at', 'title',
        'registration_opens_at', 'training_opens_at',
        'min_team_size', 'max_team_size', 'min_team_ratio',
        'max_attempts', 'max_answers', 'duration',
        'status', 'allow_team_changes', 'have_training_attempt',
        'tasks_path', 'task_module', 'task_url'
    ]
    row = db.load_row(db.tables.rounds, round_id, keys)
    bool_cols = ['allow_team_changes', 'have_training_attempt']
    for key in bool_cols:
        row[key] = db.load_bool(row[key])
    if now is not None:
        row['is_registration_open'] = row['registration_opens_at'] <= now
        row['is_training_open'] = row['training_opens_at'] <= now
    return row


def find_round_ids_with_badges(db, badges, now):
    """ Returns a list of all the ids of all the rounds (active,
        registration open) for which the badges qualify.
    """
    rounds = db.tables.rounds
    if len(badges) == 0:
        return None
    badges_table = db.tables.badges
    query = db.query(rounds & badges_table) \
              .fields(rounds.id) \
              .where(badges_table.round_id == rounds.id) \
              .where(badges_table.symbol.in_(badges)) \
              .where(badges_table.is_active) \
              .where(rounds.registration_opens_at <= now) \
              .order_by(rounds.id.desc())  # XXX temporary fix
    return [row[0] for row in db.all(query)]
