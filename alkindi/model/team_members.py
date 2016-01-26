
from alkindi.errors import ModelError
from alkindi.model.users import load_user, set_user_team_id
from alkindi.model.teams import load_team, create_empty_team
from alkindi.model.rounds import load_round, find_round_ids_with_badges


def create_user_team(db, user_id, now):
    # Check that the user does not already belong to a team.
    user = load_user(db, user_id)
    if user['team_id'] is not None:
        # User is already in a team.
        raise ModelError('already in a team')
    # Select a round based on the user's badges.
    round_ids = find_round_ids_with_badges(db, user['badges'], now)
    if len(round_ids) == 0:
        # The user does not have access to any open round.
        raise ModelError('not qualified for any open round')
    if len(round_ids) > 1:
        # XXX The case where a user has badges for multiple open rounds
        # is currently handled by picking the first one, which is the
        # one that has the greatest id.  This is unsatisfactory.
        pass
    round_id = round_ids[0]
    team_id = create_empty_team(db, round_id, now)  # XXX team/round
    # Create the team_members row.
    add_team_member(
        db, team_id, user_id, now=now,
        is_qualified=True, is_creator=True)


def get_team_creator(db, team_id):
    team_members = db.tables.team_members
    tm_query = db.query(team_members) \
        .where(team_members.team_id == team_id) \
        .where(team_members.is_creator)
    row = db.first(tm_query.fields(team_members.user_id))
    if row is None:
        raise ModelError('team has no creator')
    return row[0]


def join_team(db, user_id, team_id, now):
    """ Add a user to a team.
        Registration for the team's round must be open.
        Return a boolean indicating if the team member was added.
    """
    # XXX team/round
    # Verify that the user does not already belong to a team.
    user = load_user(db, user_id, for_update=True)
    if user['team_id'] is not None:
        raise ModelError('already in a team')
    # Verify that the team exists and load the round.
    team = load_team(db, team_id)
    # Verify that the team is open and not locked.
    if not team['is_open']:
        # Team is closed (by its creator).
        raise ModelError('team is closed')
    round_id = team['round_id']
    round_ = load_round(round_id, now=now)
    # Verify that the round is open for registration.
    if not round_['is_registration_open']:
        raise ModelError('registration is closed')
    # Look up the badges that grant access to the team's round, to
    # figure out whether the user is qualified for that round.
    user_badges = user['badges']
    badges = db.tables.badges
    if len(user_badges) == 0:
        is_qualified = False
    else:
        row = db.first(
            db.query(badges).fields(badges.id)
                .where(badges.round_id == round_id)
                .where(badges.symbol.in_(user_badges))
                .where(badges.is_active))
        is_qualified = row is not None
    # If the team has already accessed a task (is_locked=True),
    # verify that the team remains valid if the user is added.
    if team['is_locked']:
        if round_['allow_team_changes']:
            user['is_qualified'] = is_qualified
            validate_team(db, team, with_member=user, now=now)
        else:
            raise ModelError('team is locked')
    # Create the team_members row.
    user_id = user['id']
    add_team_member(db, team_id, user_id, now=now, is_qualified=is_qualified)
    # Update the user's team_id.
    set_user_team_id(db, user_id, team_id)
    # If the team has a current attempt, generate a code for the new
    # member.
    from alkindi.model.attempts import get_team_current_attempt_id
    attempt_id = get_team_current_attempt_id(db, team_id)
    if attempt_id is not None:
        from alkindi.model.access_codes import generate_user_access_code
        generate_user_access_code(db, attempt_id, team_id, user_id)


def leave_team(db, user_id, team_id):
    """ Remove a user from their team.
    """
    user = load_user(db, user_id, for_update=True)
    team_id = user['team_id']
    # The user must be member of a team.
    if team_id is None:
        raise ModelError('no team')
    team = load_team(db, team_id)
    # If the team already has an attempt (is_locked=True), verify
    # that the team remains valid if the user is removed.
    if team['is_locked']:
        # We could allow a user to leave the team even when it is
        # locked, with code like this instead of raising an error:
        #     XXX team/round
        #     validate_team(db, team, round_, without_member=user, now=now)
        raise ModelError('team is locked')
    # Clear the user's team_id.
    set_user_team_id(db, user_id, None)
    # Delete the team_members row.
    team_members = db.tables.team_members
    tm_query = db.query(team_members) \
        .where(team_members.team_id == team_id) \
        .where(team_members.user_id == user_id)
    (is_creator,) = db.first(
        tm_query.fields(team_members.is_creator))
    db.delete(tm_query)
    # If the user was the team creator, select the earliest member
    # as the new creator.
    if is_creator:
        query = db.query(team_members) \
            .where(team_members.team_id == team_id)
        row = db.first(
            query.fields(team_members.user_id)
                 .order_by(team_members.joined_at),
            for_update=True)
        if row is None:
            # Team has become empty, delete it.
            teams = db.tables.teams
            team_query = db.query(teams) \
                .where(teams.id == team_id)
            db.delete(team_query)
        else:
            # Promote the selected user as the creator.
            new_creator_id = row[0]
            db.update(
                query.where(team_members.user_id == new_creator_id),
                {team_members.is_creator: True})


#
# Functions below this point are used internally by the model.
#


def add_team_member(db, team_id, user_id, now,
                    is_qualified=False, is_creator=False):
    team_members = db.tables.team_members
    query = db.query(team_members).insert({
        team_members.team_id: team_id,
        team_members.user_id: user_id,
        team_members.joined_at: now,
        team_members.is_qualified: is_qualified,
        team_members.is_creator: is_creator
    })
    db.execute(query)
    # Update the user's team_id.
    set_user_team_id(db, user_id, team_id)


def load_team_members(db, team_id, users=False):
    team_members = db.tables.team_members
    if users:
        users = db.tables.users
        query = db.query(team_members & users)
        query = query.where(team_members.user_id == users.id)
        query = query.where(team_members.team_id == team_id)
        query = query.fields(
            team_members.joined_at,     # 0
            team_members.is_qualified,  # 1
            team_members.is_creator,    # 2
            users.id,                   # 3
            users.username,             # 4
            users.firstname,            # 5
            users.lastname,             # 6
        )
        query = query.order_by(team_members.joined_at)
        return [
            {
                'joined_at': row[0],
                'is_qualified': db.load_bool(row[1]),
                'is_creator': db.load_bool(row[2]),
                'user_id': row[3],
                'user': {
                    'id': row[3],
                    'username': row[4],
                    'firstname': row[5],
                    'lastname': row[6],
                }
            }
            for row in db.all(query)
        ]
    query = db.query(team_members) \
        .where(team_members.team_id == team_id) \
        .fields(team_members.user_id, team_members.joined_at,
                team_members.is_qualified, team_members.is_creator)
    return [
        {
            'user_id': row[0],
            'joined_at': row[1],
            'is_qualified': db.load_bool(row[2]),
            'is_creator': db.load_bool(row[3])
        }
        for row in db.all(query)
    ]


def validate_team(db, team, now, with_member=None, without_member=None):
    """ Raise an exception if the team is invalid for the round.
        If with_member is a user, check with the user added the team.
    """
    # XXX team/round
    team_members = db.tables.team_members
    tm_query = db.query(team_members) \
        .where(team_members.team_id == team['id'])
    n_members = db.count(
        tm_query.fields(team_members.user_id))
    n_qualified = db.count(
        tm_query.where(team_members.is_qualified)
        .fields(team_members.user_id))
    if with_member is not None:
        n_members += 1
        if with_member['is_qualified']:
            n_qualified += 1
    if without_member is not None:
        n_members -= 1
        if with_member['is_qualified']:
            n_qualified -= 1
    round_ = load_round(db, team['round_id'], now=now)
    if n_members < round_['min_team_size']:
        raise ModelError('team too small')
    if n_members > round_['max_team_size']:
        raise ModelError('team too large')
    if n_qualified < n_members * round_['min_team_ratio']:
        raise ModelError('not enough qualified members')
