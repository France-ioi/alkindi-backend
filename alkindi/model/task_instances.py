
from datetime import timedelta
import json

from alkindi.errors import ModelError
from alkindi.model.rounds import load_round
from alkindi.model.team_members import validate_team
from alkindi.model.participations import load_participation
from alkindi.model.attempts import load_attempt
from alkindi.model.workspaces import create_attempt_workspace
from alkindi.model.round_tasks import load_round_task
from alkindi.model.tasks import load_task
from alkindi.tasks import task_generate


def load_task_instance(db, attempt_id, for_update=False):
    keys = [
        'attempt_id', 'created_at', 'updated_at', 'full_data', 'team_data'
    ]
    task_instances = db.tables.task_instances
    result = db.load_row(
        task_instances, {'attempt_id': attempt_id}, keys,
        for_update=for_update)
    for key in ['full_data', 'team_data']:
        result[key] = db.load_json(result[key])
    return result


def load_user_task_instance(db, attempt_id):
    """ Return a limited view of the team data for the given attempt,
        or None if there is no task assigned to the attempt.
        The data returned is safe to show to the user.
    """
    keys = ['created_at', 'updated_at', 'team_data']
    task_instances = db.tables.task_instances
    row = db.load_row(
        task_instances, {'attempt_id': attempt_id}, keys)
    row['team_data'] = json.loads(row['team_data'])
    return row


def assign_task_instance(db, attempt_id, now):
    """ Assign a task to the attempt.
        The team performing the attempt must be valid, otherwise
        an exception is raised.
    """
    attempt = load_attempt(db, attempt_id, now=now)
    if attempt['started_at'] is not None:
        return ModelError('already have a task')
    participation_id = attempt['participation_id']
    participation = load_participation(db, participation_id)
    # The team must be valid to obtain a task.
    team_id = participation['team_id']
    round_id = participation['round_id']
    validate_team(db, team_id, round_id, now=now)
    # Verify that the round is open for training (and implicitly for
    # timed attempts).
    round_ = load_round(db, round_id, now=now)
    if round_['status'] != 'open':
        raise ModelError('round not open')
    if now < round_['training_opens_at']:
        raise ModelError('training is not open')
    # Load the round_task
    round_task_id = attempt['round_task_id']
    round_task = load_round_task(db, round_task_id)
    # TODO: check round_task['have_training_attempt'] if next ordinal is 1
    # TODO: check round_task['max_timed_attempts'] if next ordinal is >1

    task = load_task(db, round_task['task_id'])  # backend_url
    backend_url = task['backend_url']
    auth = task['backend_auth']
    task_params = round_task['generate_params']
    seed = str(attempt_id)  # TODO add a participation-specific key to the seed
    team_data, full_data = task_generate(backend_url, task_params, seed, auth)

    try:
        # Lock the task_instances table to prevent concurrent inserts.
        db.execute('LOCK TABLES task_instances WRITE, attempts READ').close()
        attrs = {
            'attempt_id': attempt_id,
            'created_at': now,
            'updated_at': now,
            'full_data': db.dump_json(full_data),
            'team_data': db.dump_json(team_data)
        }
        task_instances = db.tables.task_instances
        db.insert_row(task_instances, attrs)
    finally:
        db.execute('UNLOCK TABLES').close()

    # Update the attempt.
    attempt_attrs = {'started_at': now}
    attempt_duration = round_task['attempt_duration']
    if attempt_duration is not None:
        # Set the closing time on the attempt.
        attempt_attrs['closes_at'] = now + timedelta(minutes=attempt_duration)
    attempts = db.tables.attempts
    db.update_row(attempts, attempt_id, attempt_attrs)

    # Create the team's workspace.
    create_attempt_workspace(db, attempt_id, now)


def get_user_task_instance_hint(db, attempt_id, query, now):
    load_attempt(db, attempt_id, for_update=True)
    task = load_task_instance(db, attempt_id, for_update=True)
    if task is None:
        raise ModelError('no task')

    # XXX call backend
    success = False

    if not success:
        return False

    score = 0  # XXX update score
    attempts = db.tables.attempts
    db.update_row(attempts, attempt_id, {'score': score})

    task_instances = db.tables.task_instances
    db.update_row(task_instances, {'attempt_id': attempt_id}, {
        'team_data': db.dump_json(task['team_data']),
        'updated_at': now
    })

    return True


def reset_user_task_instance_hints(db, attempt_id, now, force=False):
    # XXX to rewrite
    attempt = load_attempt(db, attempt_id, for_update=True)
    if not force and not attempt['is_training']:
        raise ModelError('forbidden')
    task = load_task_instance(db, attempt_id)
    if task is None:
        raise ModelError('no task')
    # reset_hints updates task in-place
    score = 0  # XXX reset score
    task_instances = db.tables.task_instances
    db.update_row(attempts, attempt_id, {'score': score})
    db.update_row(task_instances, {'attempt_id': attempt_id}, {
        'team_data': db.dump_json(task['team_data']),
        'updated_at': now
    })
