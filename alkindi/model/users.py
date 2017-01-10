
from alkindi.errors import ModelError


def load_user(db, user_id, for_update=False):
    results = load_users(db, (user_id,), for_update)
    if len(results) == 0:
        raise ModelError('no such user')
    return results[0]


def import_user(db, profile, now):
    foreign_id = profile['idUser']
    users = db.tables.users
    query = db.query(users).insert({
        users.created_at: now,
        users.foreign_id: foreign_id,
        users.team_id: None,
        users.username: profile['sLogin'],
        users.firstname: profile['sFirstName'],
        users.lastname: profile['sLastName'],
        users.badges: ' '.join(profile['aBadges']),
    })
    user_id = db.insert(query)
    return user_id


def update_user(db, user_id, profile):
    db.update_row(db.tables.users, user_id, {
        'username': profile['sLogin'],
        'firstname': profile['sFirstName'],
        'lastname': profile['sLastName'],
        'badges': ' '.join(profile['aBadges']),
    })


def get_user_principals(db, user_id):
    user_id = int(user_id)
    users = db.tables.users
    query = db.query(users) \
        .where(users.id == user_id) \
        .fields(users.team_id, users.is_admin)
    row = db.first(query)
    if row is None:
        raise ModelError('invalid user')
    principals = ['u:{}'.format(user_id)]
    team_id = row[0]
    if row[1]:
        principals.append('g:admin')
    if team_id is None:
        return principals
    team_members = db.tables.team_members
    query = db.query(team_members) \
        .where(team_members.user_id == user_id) \
        .where(team_members.team_id == team_id) \
        .fields(team_members.is_qualified, team_members.is_creator)
    row = db.first(query)
    if row is None:
        raise ModelError('missing team_member row')
    principals.append('t:{}'.format(team_id))
    if db.load_bool(row[0]):
        principals.append('ts:{}'.format(team_id))
    if db.load_bool(row[1]):
        principals.append('tc:{}'.format(team_id))
    if False:
        # Add credentials for user participations.
        participations = db.tables.participations
        query = db.query(participations) \
            .where(participations.team_id == team_id) \
            .fields(participations.id)
        for row in db.all(query):
            principals.append('p:{}'.format(row[0]))
    return principals


#
# Functions below this point are used internally by the model.
#


def load_users(db, user_ids, for_update=False):
    keys = [
        'id', 'created_at', 'foreign_id', 'team_id',
        'username', 'firstname', 'lastname', 'badges'
    ]
    results = db.load_rows(db.tables.users, user_ids, keys,
                           for_update=for_update)
    for result in results:
        result['badges'] = result['badges'].split(' ')
    return results


def find_user_by_username(db, username):
    """ Find the user with the given username and return their id,
        or None if no such user exists.
    """
    users = db.tables.users
    return db.load_scalar(
        table=users, value={'username': username}, column='id')


def find_user_by_foreign_id(db, foreign_id):
    """ Find the user with the given foreign_id and return their id,
        or None if no such user exists.
    """
    users = db.tables.users
    return db.load_scalar(
        table=users, value={'foreign_id': foreign_id}, column='id')


def get_user_team_id(db, user_id):
    users = db.tables.users
    return db.load_scalar(
        table=users, value=user_id, column='team_id')


def set_user_team_id(db, user_id, team_id):
    db.update_row(db.tables.users, user_id, {'team_id': team_id})
