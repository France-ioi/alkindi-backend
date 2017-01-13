
from datetime import timedelta
from importlib import import_module

from alkindi.errors import ModelError
from alkindi.model.rounds import load_round
from alkindi.model.team_members import validate_team
from alkindi.model.participations import load_participation
from alkindi.model.attempts import load_attempt, get_user_current_attempt_id
from alkindi.model.workspaces import create_attempt_workspace
from alkindi.model.round_tasks import load_round_task
from alkindi.model.tasks import load_task


def load_task_instance(db, attempt_id, for_update=False):
    keys = [
        'attempt_id', 'created_at', 'full_data', 'team_data', 'score'
    ]
    task_instances = db.tables.task_instances
    result = db.load_row(
        task_instances, {'attempt_id': attempt_id}, keys,
        for_update=for_update)
    for key in ['full_data', 'team_data']:
        result[key] = db.load_json(result[key])
    return result


def load_task_instance_team_data(db, attempt_id):
    """ Return the team data for the given attempt, or None if there
        is no task assigned to the attempt.
    """
    task_instances = db.tables.task_instances
    row = db.load_row(
        task_instances, {'attempt_id': attempt_id}, ['score', 'team_data'])
    if row is None:
        return None
    result = db.load_json(row['team_data'])
    result['score'] = row['score']
    return result


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

    # TODO: contact backend_url to obtain task, full_task, url
    task = load_task(db, round_task['task_id'])  # backend_url
    backend_url = task['backend_url']
    print("TODO: contact {}".format(backend_url))
    full_data = {}
    team_data = {}

    # TODO: figure out where we store the frontend URL -- could be in task,
    #       round_task, or returned by backend_url and stored in task_instance

    try:
        # Lock the task_instances table to prevent concurrent inserts.
        db.execute('LOCK TABLES task_instances WRITE, attempts READ').close()
        attrs = {
            'attempt_id': attempt_id,
            'created_at': now,
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


def get_user_task_instance_hint(db, user_id, query):
    attempt_id = get_user_current_attempt_id(db, user_id)
    if attempt_id is None:
        raise ModelError('no current attempt')
    task = load_task_instance(db, attempt_id, for_update=True)
    if task is None:
        raise ModelError('no task')
    task_module = get_attempt_task_module(db, attempt_id)
    # get_hint updates task in-place
    success = task_module.get_hint(task, query)
    if not success:
        return False
    score = task_module.get_current_score(task)
    task_instances = db.tables.task_instances
    db.update_row(task_instances, {'attempt_id': attempt_id}, {
        'score': score,
        'team_data': db.dump_json(task['team_data'])
    })
    return True


def reset_user_task_instance_hints(db, user_id, force=False):
    attempt_id = get_user_current_attempt_id(db, user_id)
    if not force and attempt_id is None:
        raise ModelError('no current attempt')
    attempt = load_attempt(db, attempt_id, for_update=True)
    if not force and not attempt['is_training']:
        raise ModelError('forbidden')
    task = load_task_instance(db, attempt_id)
    if task is None:
        raise ModelError('no task')
    # reset_hints updates task in-place
    task_module = get_attempt_task_module(db, attempt_id)
    task_module.reset_hints(task)
    score = task_module.get_current_score(task)
    task_instances = db.tables.task_instances
    db.update_row(task_instances, {'attempt_id': attempt_id}, {
        'score': score,
        'team_data': db.dump_json(task['team_data'])
    })


#
# Functions below this point are used within this file only.
#

def get_attempt_task_module(db, attempt_id):
    attempts = db.tables.attempts
    participations = db.tables.participations
    rounds = db.tables.rounds
    query = db.query(
        attempts &
        participations.on(participations.id == attempts.participation_id) &
        rounds.on(rounds.id == participations.round_id))
    query = query \
        .fields(rounds.task_module) \
        .where(attempts.id == attempt_id)
    module_path = db.scalar(query[:1])
    return get_task_module(module_path)


def get_task_module(module_path):
    try:
        print("module_path {}".format(module_path))
        return import_module(module_path)
    except ImportError:
        raise ModelError('task module not found')


def get_participation_task_dirs(db, participation_id):
    """ Return the list of task_dir(s) in all the task instances accessed by
        the given participation.
    """
    task_instances = db.tables.task_instances
    attempts = db.tables.attempts
    query = db.query(
        task_instances &
        attempts.on(attempts.id == task_instances.attempt_id))
    query = query \
        .where(attempts.participation_id == participation_id) \
        .fields(task_instances.task_dir)
    return [row[0] for row in db.all(query)]


def get_new_task(round_, task_dirs):
    tasks_path = round_['tasks_path']
    task_module = get_task_module(round_['task_module'])
    for i in range(0, 15):  # XXX hard-wired number of tries
        task = task_module.get_task(tasks_path)
        task_dir = task['task_dir']
        if task_dir not in task_dirs:
            task['score'] = task_module.get_current_score(task)
            return task
    raise ModelError('task pool exhausted')


def fix_tasks(db, round_id):
    """ This function can be used to fix all the task instances assigned for a
        given round.  It calls the task module's fix_task function on
        each task, and updates the task instances for which fix_task returns
        True.
    """
    round_ = load_round(db, round_id)
    task_module = get_task_module(round_['task_module'])
    keys = [
        'attempt_id', 'created_at', 'full_data', 'team_data', 'score'
    ]
    task_instances = db.tables.task_instances
    attempts = db.tables.attempts
    query = (
        db.query(
            (task_instances & attempts)
            .on(task_instances.attempt_id == attempts.id))
        .where(attempts.round_id == round_id)
        .fields(*[getattr(task_instances, key) for key in keys]))
    count = 0
    for row in list(db.all(query)):
        task = {key: row[i] for i, key in enumerate(keys)}
        for key in ['full_data', 'team_data']:
            task[key] = db.load_json(task[key])
        if task_module.fix_task(task):
            count += 1
            for key in ['full_data', 'team_data']:
                task[key] = db.dump_json(task[key])
            db.update_row(
                task_instances, {'attempt_id': task['attempt_id']}, task)
    return count
