
def load_round(db, round_id, now=None):
    return load_rounds(db, [round_id], now)[round_id]


def load_rounds(db, round_ids, now=None):
    cols = [
        'id', 'created_at', 'updated_at', 'title', 'status',
        'registration_opens_at', 'training_opens_at',
        'min_team_size', 'max_team_size', 'min_team_ratio',
        'allow_team_changes', 'duration'
    ]
    bool_cols = ['allow_team_changes']
    rows = db.load_rows(db.tables.rounds, round_ids, cols)
    result = {}
    for row in rows:
        for key in bool_cols:
            row[key] = db.load_bool(row[key])
        if now is not None:
            row['is_registration_open'] = row['registration_opens_at'] <= now
            row['is_training_open'] = row['training_opens_at'] <= now
        result[row['id']] = row
    return result


def find_round_ids_with_badges(db, badges, now):
    """ Returns a list of all the ids of all the active rounds
        for which the badges qualify.
        The most recently update round is return first.
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
              .order_by(rounds.updated_at.desc())
    return [row[0] for row in db.all(query)]
