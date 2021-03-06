
from sqlbuilder.smartsql import func
from datetime import timedelta

from alkindi.errors import ModelError
from alkindi.model.rounds import load_round
from alkindi.model.participations import load_participation
from alkindi.model.round_tasks import load_round_task
from alkindi.model.access_codes import generate_access_codes


def get_current_attempt_id(db, participation_id, round_task_id):
    attempts = db.tables.attempts
    query = db.query(attempts)
    query = query \
        .fields(attempts.id) \
        .where(attempts.participation_id == participation_id) \
        .where(attempts.round_task_id == round_task_id) \
        .where(attempts.is_current)
    row = db.first(query)
    return None if row is None else row[0]


def get_user_current_attempt_id(db, user_id):
    users = db.tables.users
    participations = db.tables.participations
    attempts = db.tables.attempts
    query = db.query(
        attempts +
        participations.on(participations.id == attempts.participation_id) +
        users.on(users.team_id == participations.team_id)
    )
    query = query \
        .fields(attempts.id) \
        .where(users.id == user_id) \
        .where(attempts.is_current) \
        .order_by(participations.created_at.desc())
    row = db.first(query)
    return None if row is None else row[0]


def load_attempt(db, attempt_id, now=None, for_update=False):
    keys = [
        'id', 'participation_id', 'round_task_id', 'ordinal',
        'created_at', 'started_at', 'closes_at',
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved'
    ]
    row = db.load_row(
        db.tables.attempts, attempt_id, keys, for_update=for_update)
    bool_cols = [
        'is_current', 'is_training', 'is_unsolved', 'is_fully_solved']
    for key in bool_cols:
        row[key] = db.load_bool(row[key])
    if now is not None:
        enrich_attempt(db, row, now)
    return row


def load_participation_attempts(db, participation_id, now):
    attempts = db.tables.attempts
    round_tasks = db.tables.round_tasks
    answers = db.tables.answers
    cols = [
        ('id', attempts.id),
        ('round_task_id', attempts.round_task_id),
        ('ordinal', attempts.ordinal),
        ('created_at', attempts.created_at),
        ('started_at', attempts.started_at),
        ('closes_at', attempts.closes_at),
        ('is_current', attempts.is_current, 'bool'),
        ('is_training', attempts.is_training, 'bool'),
        ('is_unsolved', attempts.is_unsolved, 'bool'),
        ('is_fully_solved', attempts.is_fully_solved, 'bool'),
        ('max_score', func.max(answers.score)),
    ]
    query = db.query(
        attempts &
        round_tasks.on(round_tasks.id == attempts.round_task_id) +
        answers.on(answers.attempt_id == attempts.id)) \
        .fields([col[1] for col in cols]) \
        .where(attempts.participation_id == participation_id) \
        .group_by(attempts.id) \
        .order_by(round_tasks.ordinal, attempts.ordinal)
    attempts = db.all_rows(query, cols)
    for attempt in attempts:
        enrich_attempt(db, attempt, now)
    return attempts


def get_attempt_team_id(db, attempt_id):
    attempts = db.tables.attempts
    participations = db.tables.participations
    query = db.query(
        attempts &
        participations.on(participations.id == attempts.participation_id))
    query = query \
        .where(attempts.id == attempt_id) \
        .fields(participations.team_id)
    return db.scalar(query)


def have_attempt_after(db, participation_id, round_task_id, when):
    attempts = db.tables.attempts
    query = db.query(attempts)
    query = query \
        .fields(attempts.id) \
        .where(attempts.participation_id == participation_id) \
        .where(attempts.round_task_id == round_task_id) \
        .where(attempts.created_at >= when)
    return db.count(query) > 0


def create_attempt(db, participation_id, round_task_id, now):
    # Load the participation and round_task, check consistency.
    participation = load_participation(db, participation_id)
    round_task = load_round_task(db, round_task_id)
    if participation['round_id'] != round_task['round_id']:
        raise ModelError('round mismatch')
    # Check that round is open.
    round_ = load_round(db, round_task['round_id'], now=now)
    if round_['status'] != 'open':
        raise ModelError('round not open')
    attempt_id = get_current_attempt_id(db, participation_id, round_task_id)
    is_training = False
    if attempt_id is None:
        # Create the initial attempt (which may or may not be a training
        # attempt, depending on the task_round's options).
        # The team is not locked at this time and may still be changed
        # (depending on round options).  This requires adding an access
        # code when a new member joins the team, and deleting an access
        # code when a member leaves the team.
        is_training = round_task['have_training_attempt']
    else:
        attempt = load_attempt(db, attempt_id, now=now, for_update=True)
        if attempt['is_training']:
            # Current attempt is training.  Team must pass training to
            # create a timed attempt.
            if attempt['is_unsolved']:
                raise ModelError('must pass training')
        else:
            # Timed attempts allow starting the next attempt immediately
            # only if completed.
            # if not attempt['is_completed']:
            most_recent_allowed = now - timedelta(minutes=5)
            if have_attempt_after(db, participation_id, round_task_id, most_recent_allowed):
                raise ModelError('attempt too soon')
        # Optionally limit the number of timed attempts.
        if round_task['max_timed_attempts'] is not None:
            n_attempts = count_timed_attempts(db, participation_id)
            if n_attempts >= round_task['max_timed_attempts']:
                raise ModelError('too many attempts')
        # Reset the is_current flag on the current attempt.
        set_attempt_current(db, attempt_id, is_current=False)
    # Find the greatest attempt ordinal for the (participation, round_task).
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.participation_id == participation_id) \
        .where(attempts.round_task_id == round_task_id) \
        .order_by(attempts.ordinal.desc()) \
        .fields(attempts.ordinal)
    row = db.first(query)
    ordinal = 1 if row is None else (row[0] + 1)
    attempt_id = db.insert_row(attempts, {
        'participation_id': participation_id,
        'round_task_id': round_task_id,
        'ordinal': ordinal,
        'created_at': now,
        'started_at': None,   # set when task is accessed
        'closes_at': None,
        'is_current': True,
        'is_training': is_training,
        'is_unsolved': True
    })
    generate_access_codes(db, participation['team_id'], attempt_id)
    return attempt_id


def cancel_attempt(db, attempt_id):
    attempt = load_attempt(db, attempt_id)
    if attempt['started_at'] is not None:
        raise ModelError('cannot cancel started attempt')
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.id == attempt_id)
    db.delete(query)


# XXX
def reset_to_training_attempt(db, participation_id, round_task_id, now):
    attempt_id = get_current_attempt_id(db, participation_id, round_task_id)
    if attempt_id is not None:
        attempt = load_attempt(db, attempt_id, now=now, for_update=True)
        if not attempt['is_completed']:
            # Handle case where several users click the reset button,
            # avoid giving a confusing error message when the outcome
            # is correct.
            if attempt['is_training']:
                return
            raise ModelError('timed attempt not completed')
        # Clear 'is_current' flag on current attempt.
        set_attempt_current(db, attempt_id, is_current=False)
    # Select the new attempt and make it current.
    # XXX for_update=True
    new_attempt_id = get_latest_training_attempt_id(db, participation_id)
    if new_attempt_id is not None:
        set_attempt_current(db, new_attempt_id, is_current=True)


#
# Functions below this point are used internally by the model.
#


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


def count_timed_attempts(db, participation_id):
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.participation_id == participation_id) \
        .where(~attempts.is_training) \
        .fields(attempts.id.count())
    return db.scalar(query)


def get_latest_training_attempt_id(db, participation_id):
    attempts = db.tables.attempts
    query = db.query(attempts) \
        .where(attempts.participation_id == participation_id) \
        .where(attempts.is_training) \
        .order_by(attempts.created_at.desc()) \
        .fields(attempts.id)
    return db.scalar(query)


def set_attempt_current(db, attempt_id, is_current=True):
    attempts = db.tables.attempts
    db.update_row(attempts, attempt_id, {'is_current': is_current})
