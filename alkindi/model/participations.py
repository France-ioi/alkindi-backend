
from alkindi.utils import generate_code


def participations_columns(db):
    participations = db.tables.participations
    return [
        ('id', participations.id),
        ('team_id', participations.team_id),
        ('round_id', participations.round_id),
        ('created_at', participations.created_at),
        ('score', participations.score),
        ('score_90min', participations.score_90min),
        ('first_equal_90min', participations.first_equal_90min),
        ('is_qualified', participations.is_qualified, 'bool'),
        ('access_code', participations.access_code),
        ('access_code_entered', participations.access_code_entered, 'bool'),
        ('started_at', participations.started_at),
        ('rank_national', participations.rank_national),
        ('rank_big_regional', participations.rank_big_regional),
        ('rank_regional', participations.rank_regional)
    ]


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
    participations = db.tables.participations
    cols = participations_columns(db)
    query = db.query(participations) \
        .where(participations.id == participation_id)
    return db.first_row(query, cols)


def load_team_participations(db, team_id):
    participations = db.tables.participations
    cols = participations_columns(db)
    query = db.query(participations) \
        .where(participations.team_id == team_id) \
        .order_by(participations.created_at)
    return db.all_rows(query, cols)


def update_participation(db, participation_id, attrs):
    db.update_row(db.tables.participations, participation_id, attrs)


def advance_participations(db, round_id, next_round_id, now):
    participations = db.tables.participations
    gen_access_codes = True
    cols = [
        ('team_id', participations.team_id)
    ]
    query = db.query(participations) \
        .where(
            (participations.round_id == round_id) &
            participations.is_qualified)
    for row in db.all_rows(query, cols):
        participation = {
            'team_id': row['team_id'],
            'round_id': next_round_id,
            'created_at': now,
            'updated_at': now
        }
        if gen_access_codes:
            participation['access_code'] = generate_code()
        db.insert_row(participations, participation)


def find_participation_by_code(db, code):
    participations = db.tables.participations
    cols = [
        ('team_id', participations.team_id)
    ]
    query = db.query(participations) \
        .fields(participations.id) \
        .where(participations.access_code == code)
    row = db.first(query)
    return None if row is None else row[0]


def mark_participation_code_entered(db, participation_id, now):
    attrs = {'access_code_entered': 1}
    update_participation(db, participation_id, attrs)
