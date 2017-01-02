

def create_participation(db, team_id, round_id, now):
    participation_id = db.insert_row(db.tables.participations, {
        'team_id': team_id,
        'round_id': round_id,
        'created_at': now,
        'score': None
    })
    return participation_id


def get_user_latest_participation_id(db, user_id):
    participations = db.tables.participations
    users = db.tables.users
    query = db.query(
        participations &
        users.on(users.team_id == participations.team_id))
    query = query \
        .fields(participations.id) \
        .where(users.id == user_id) \
        .order_by(participations.created_at.desc())
    return db.scalar(query[:1])


def get_team_latest_participation_id(db, team_id):
    participations = db.tables.participations
    query = db.query(participations) \
        .where(participations.team_id == team_id) \
        .fields(participations.id) \
        .order_by(participations.created_at.desc())
    return db.scalar(query[:1])


def load_participation(db, participation_id, for_update=False):
    cols = ['id', 'created_at', 'team_id', 'round_id', 'score', 'is_qualified']
    row = db.load_row(
        db.tables.participations, participation_id, cols,
        for_update=for_update)
    for key in ['is_qualified']:
        row[key] = db.load_bool(row[key])
    return row


def load_team_participations(db, team_id):
    participations = db.tables.participations
    cols = [
        ('id', participations.id),
        ('round_id', participations.round_id),
        ('created_at', participations.created_at),
        ('score', participations.score),
        ('score_90min', participations.score_90min),
        ('first_equal_90min', participations.first_equal_90min),
        ('is_qualified', participations.is_qualified)
    ]
    query = db.query(participations) \
        .fields([col[1] for col in cols]) \
        .where(participations.team_id == team_id) \
        .order_by(participations.created_at)
    rows = db.all_rows(query, cols)
    for row in rows:
        for key in ['is_qualified']:
            row[key] = db.load_bool(row[key])
    return rows


def update_participation(db, participation_id, attrs):
    db.update_row(db.tables.participations, participation_id, attrs)
