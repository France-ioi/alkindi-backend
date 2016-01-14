
from sqlbuilder.smartsql import func

from alkindi.errors import ModelError
from alkindi.model.teams import load_team
from alkindi.model.rounds import load_round
from alkindi.model.access_codes import (
    generate_access_codes, load_access_codes, generate_access_code)


# TODO: make (team_id, ordinal) the primary key (rather than a unique index).
# TODO: remove round_id and use that of the team (also remove from index).

def get_user_current_attempt_id(db, user_id):
    users = db.tables.users
    attempts = db.tables.attempts
    query = db.query(users & attempts) \
        .where(users.id == user_id) \
        .where(attempts.team_id == users.team_id) \
        .where(attempts.is_current) \
        .fields(attempts.id)
    row = db.first(query)
    return None if row is None else row[0]


def load_attempt(db, attempt_id, now=None):
    keys = [
        'id', 'team_id', 'round_id',
        'created_at', 'started_at', 'closes_at',
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved'
    ]
    row = db.load_row(db.tables.attempts, attempt_id, keys)
    bool_cols = [
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved']
    for key in bool_cols:
        row[key] = db.load_bool(row[key])
    if now is not None:
        enrich_attempt(db, row, now)
    return row


def load_team_attempts(db, team_id, now):
    attempts = db.tables.attempts
    tasks = db.tables.tasks
    answers = db.tables.answers
    cols = [
        ('id', attempts.id),
        ('round_id', attempts.round_id),
        ('team_id', attempts.team_id),
        ('ordinal', attempts.ordinal),
        ('created_at', attempts.created_at),
        ('started_at', attempts.started_at),
        ('closes_at', attempts.closes_at),
        ('is_current', attempts.is_current, 'bool'),
        ('is_training', attempts.is_training, 'bool'),
        ('is_unsolved', attempts.is_unsolved, 'bool'),
        ('is_fully_solved', attempts.is_fully_solved, 'bool'),
        ('task_id', tasks.attempt_id),
        ('max_score', func.max(answers.score)),
    ]
    query = db.query(
            attempts +
            tasks.on(tasks.attempt_id == attempts.id) +
            answers.on(answers.attempt_id == attempts.id)) \
        .fields([col[1] for col in cols]) \
        .where(attempts.team_id == team_id) \
        .order_by(attempts.ordinal) \
        .group_by(attempts.id)
    attempts = db.all_rows(query, cols)
    for attempt in attempts:
        enrich_attempt(db, attempt, now)
    return attempts


def get_attempt_team_id(db, attempt_id):
    attempts = db.tables.attempts
    return db.load_scalar(
        table=attempts, value=attempt_id, column='team_id')


def start_attempt(db, team_id, now):
    attempt_id = get_team_current_attempt_id(db, team_id)
    if attempt_id is None:
        # Create a training attempt.
        # The team is not locked at this time and can still be
        # changed (which requires creating an access code when
        # a new member joins the team, and deleting an access
        # code when a user leaves the team).
        create_attempt(db, team_id, now=now, is_training=True)
    else:
        attempt = load_attempt(db, attempt_id, now=now)
        if attempt['is_training']:
            # Current attempt is training.  Team must pass training to
            # create a timed attempt.
            if attempt['is_unsolved']:
                raise ModelError('must pass training')
        else:
            # Timed attempts allow starting the next attempt immediately
            # only if completed.
            if not attempt['is_completed']:
                raise ModelError('timed attempt in progress')
        # Load the attempt's round.
        round_id = attempt['round_id']
        round_ = load_round(db, round_id, now=now)
        # Limit the number of timed attempts.
        n_attempts = count_team_timed_attempts(db, team_id)
        if n_attempts == round_['max_attempts']:
            raise ModelError('too many attempts')
        # Reset the is_current flag on the current attempt.
        set_attempt_not_current(db, attempt['id'])
        # Create a timed attempt.
        create_attempt(db, team_id, now=now, is_training=False)


def cancel_attempt(db, attempt_id):
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.id == attempt_id)
    db.delete(query)


def reset_team_to_training_attempt(db, team_id, now):
    team = load_team(db, team_id)
    round_id = team['round_id']
    attempt_id = get_team_current_attempt_id(db, team_id)
    if attempt_id is not None:
        attempt = load_attempt(db, attempt_id)
        if not is_attempt_completed(db, attempt, now=now):
            # Handle case where several users click the reset button,
            # avoid giving a confusing error message when the outcome
            # is correct.
            if attempt['is_training']:
                return
            raise ModelError('timed attempt not completed')
        # Clear 'is_current' flag on current attempt.
        db.update_row(db.tables.attempts, attempt_id, {
            'is_current': False
        })
    # Select the new attempt and make it current.
    new_attempt_id = get_team_latest_training_attempt_id(
        db, team_id, round_id)
    if new_attempt_id is not None:
        db.update_row(db.tables.attempts, new_attempt_id, {
            'is_current': True
        })


def generate_user_access_code(db, attempt_id, team_id, user_id):
    # If the team has a current attempt, generate an access code for
    # the new user.
    attempt_id = get_team_current_attempt_id(db, team_id)
    if attempt_id is not None:
        codes = load_access_codes(attempt_id)
        used_codes = set([code['code'] for code in codes])
        generate_access_code(attempt_id, user_id, used_codes)


#
# Functions below this point are used internally by the model.
#


def get_team_current_attempt_id(db, team_id):
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.team_id == team_id) \
        .where(attempts.is_current) \
        .fields(attempts.id)
    return db.scalar(query)


def update_attempt_with_grading(db, attempt_id, grading):
    """ Mark the attempt as solved or fully solved according to the
        grading data.
    """
    attrs = {}
    if grading['is_solution']:
        attrs['is_unsolved'] = False
    if grading['is_full_solution']:
        attrs['is_fully_solved'] = True
    if len(attrs) > 0:
        db.update_row(db.tables.attempts, attempt_id, attrs)


#
# Functions below this point are used within the current file only.
#


def enrich_attempt(db, attempt, now):
    if now is not None:
        is_closed = (attempt['closes_at'] is not None and
                     attempt['closes_at'] < now)
        attempt['is_closed'] = is_closed
    if attempt['is_training']:
        # A training attempt is completed by any amount of solving.
        attempt['is_completed'] = not attempt['is_unsolved']
    else:
        # A timed attempt is completed when closed or fully solved.
        is_fully_solved = attempt['is_fully_solved']
        attempt['is_completed'] = is_closed or is_fully_solved


def count_team_timed_attempts(db, team_id):
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.team_id == team_id) \
        .where(~attempts.is_training) \
        .fields(attempts.id.count())
    return db.scalar(query)


def get_team_latest_training_attempt_id(db, team_id, round_id):
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.team_id == team_id) \
        .where(attempts.round_id == round_id) \
        .where(attempts.is_training) \
        .order_by(attempts.created_at.desc()) \
        .fields(attempts.id)
    return db.scalar(query)


def set_attempt_not_current(db, attempt_id):
    attempts = db.tables.attempts
    db.update_row(attempts, attempt_id, {'is_current': False})


def is_attempt_completed(db, attempt, now):
    if attempt['is_training']:
        return not attempt['is_unsolved']
    else:
        is_fully_solved = attempt['is_fully_solved']
        is_closed = (attempt['closes_at'] is not None and
                     attempt['closes_at'] < now)
        return is_fully_solved or is_closed


def create_attempt(db, team_id, now, is_training=True):
    team = load_team(db, team_id)
    # Get the team's current attempt.
    round_id = team['round_id']
    attempts = db.tables.attempts
    # Find the greatest attempt ordinal for the team.
    query = db.query(attempts) \
        .where(attempts.team_id == team_id) \
        .order_by(attempts.ordinal.desc()) \
        .fields(attempts.ordinal)
    row = db.first(query)
    ordinal = 0 if row is None else (row[0] + 1)
    attempt_id = db.insert_row(attempts, {
        'team_id': team_id,
        'ordinal': ordinal,
        'round_id': round_id,
        'created_at': now,
        'started_at': None,   # set when enough codes have been entered
        'closes_at': None,    # set when task is accessed
        'is_current': True,
        'is_training': is_training,
        'is_unsolved': True
    })
    generate_access_codes(db, team_id, attempt_id)
    return attempt_id
