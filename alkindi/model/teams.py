
from alkindi.utils import generate_code


def load_team(db, team_id, for_update=False):
    if team_id is None:
        return None
    keys = [
        'id', 'revision', 'created_at', 'round_id', 'code',
        'is_open', 'is_locked', 'message', 'score'
    ]
    result = db.load_row(db.tables.teams, team_id, keys,
                         for_update=True)
    for key in ['is_open', 'is_locked']:
        result[key] = db.load_bool(result[key])
    return result


def create_empty_team(db, round_id, now):
    """ Creates a team for the specified round.
        Returns the team id.
    """
    # Generate an unused team access code.
    # XXX lock teams table
    code = generate_code()
    while find_team_by_code(db, code) is not None:
        code = generate_code()
    # Create the team.
    teams = db.tables.teams
    query = db.query(teams).insert({
        teams.created_at: now,
        teams.round_id: round_id,
        teams.code: code,
        teams.is_open: True,
        teams.is_locked: False
    })
    return db.insert(query)


def find_team_by_code(db, code):
    teams = db.tables.teams
    row = db.first(
        db.query(teams)
            .fields(teams.id)
            .where(teams.code == code))
    if row is None:
        return None
    (team_id,) = row
    return team_id


def update_team(db, team_id, settings):
    """ Update a team's settings.
        These settings are available:
            is_open: can users join the team?
            is_locked: can users join or leave the team?
        No checks are performed in this function.
    """
    db.update_row(db.tables.teams, team_id, settings)
