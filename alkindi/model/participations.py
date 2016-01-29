

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
    cols = ['id', 'created_at', 'team_id', 'round_id', 'score']
    return db.load_row(
        db.tables.participations, participation_id, cols,
        for_update=for_update)


# from alkindi.model.rounds import load_round, find_round_ids_with_badges
#     # Create a participation.
#     # Select a round based on the user's badges.
#     round_ids = find_round_ids_with_badges(db, user['badges'], now)
#     if len(round_ids) == 0:
#         # The user does not have access to any open round.
#         raise ModelError('not qualified for any open round')
#     if len(round_ids) > 1:
#         # XXX The case where a user has badges for multiple open rounds
#         # is currently handled by picking the first one, which is the
#         # one that has the greatest id.  This is unsatisfactory.
#         pass
#     round_id = round_ids[0]
#     create_participation(db, team_id, round_id, now=now)
#     return team_id
