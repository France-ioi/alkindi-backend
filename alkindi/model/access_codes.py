
from alkindi.utils import generate_code
from alkindi.model.team_members import load_team_members


def load_access_codes(db, attempt_id):
    access_codes = db.tables.access_codes
    query = db.query(access_codes) \
        .where(access_codes.attempt_id == attempt_id) \
        .fields(access_codes.user_id,
                access_codes.code,
                access_codes.is_unlocked)
    return [
        {
            'user_id': row[0],
            'code': row[1],
            'is_unlocked': db.load_bool(row[2])
        }
        for row in db.all(query)
    ]


def load_unlocked_access_codes(db, attempt_id):
    codes = load_access_codes(db, attempt_id)
    return [code for code in codes if code['is_unlocked']]


def get_access_code(db, attempt_id, user_id):
    access_codes = db.tables.access_codes
    query = db.query(access_codes) \
        .where(access_codes.attempt_id == attempt_id) \
        .where(access_codes.user_id == user_id) \
        .fields(access_codes.code)
    return db.scalar(query)


def generate_user_access_code(db, attempt_id, team_id, user_id):
    # If the team has a current attempt, generate an access code for
    # the new user.
    codes = load_access_codes(db, attempt_id)
    used_codes = set([code['code'] for code in codes])
    generate_access_code(db, attempt_id, user_id, used_codes)


def generate_access_code(db, attempt_id, user_id, used_codes):
    # Generate a distinct code for each member.
    code = generate_code()
    while code in used_codes:
        code = generate_code()
    used_codes.add(code)
    access_codes = db.tables.access_codes
    db.insert_row(access_codes, {
        'attempt_id': attempt_id,
        'user_id': user_id,
        'code': code,
        'is_unlocked': False
    })


def generate_access_codes(db, team_id, attempt_id):
    """ Generate a distinct code for each member of the given
        team and attempt.
    """
    used_codes = set()
    members = load_team_members(db, team_id)
    for member in members:
        generate_access_code(db, attempt_id, member['user_id'], used_codes)


def unlock_access_code(db, attempt_id, user_id, code):
    # Mark the access code as unlocked.
    access_codes = db.tables.access_codes
    query = db.query(access_codes) \
        .where(access_codes.attempt_id == attempt_id) \
        .where(access_codes.code == code)
    return db.update(query, {'is_unlocked': True})


def clear_access_codes(db, user_id, team_id):
    # Delete the user's access codes in all of the team's attempts.
    attempts = db.tables.attempts
    subquery = db.query(attempts) \
        .fields(attempts.id) \
        .where(attempts.team_id == team_id) \
        .order_by(attempts.ordinal)
    access_codes = db.tables.access_codes
    query = db.query(access_codes) \
        .where(access_codes.user_id == user_id) \
        .where(access_codes.attempt_id.in_(subquery))
    return db.delete(query)
