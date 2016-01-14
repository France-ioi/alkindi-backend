
def load_round(db, round_id, now):
    keys = [
        'id', 'created_at', 'updated_at', 'title',
        'registration_opens_at', 'training_opens_at',
        'min_team_size', 'max_team_size', 'min_team_ratio',
        'max_attempts', 'max_answers', 'tasks_path', 'task_url'
    ]
    row = db.load_row(db.tables.rounds, round_id, keys)
    # datetime_cols = [
    #     'registration_opens_at', 'training_opens_at']
    # for key in datetime_cols:
    #     row[key] = db.view_datetime(row[key])
    row['is_registration_open'] = row['registration_opens_at'] <= now
    row['is_training_open'] = row['training_opens_at'] <= now
    return row


def is_round_registration_open(db, round_id, now):
    rounds = db.tables.rounds
    (registration_opens_at,) = db.first(
        db.query(rounds)
          .fields(rounds.registration_opens_at)
          .where(rounds.id == round_id))
    return (registration_opens_at <= now)


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
              .where(rounds.registration_opens_at <= now)
    return [row[0] for row in db.all(query)]
