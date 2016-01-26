
from datetime import timedelta
from importlib import import_module

from alkindi.errors import ModelError
from alkindi.model.teams import load_team
from alkindi.model.rounds import load_round
from alkindi.model.team_members import validate_team
from alkindi.model.attempts import load_attempt, get_user_current_attempt_id
from alkindi.model.workspaces import create_attempt_workspace


def load_task(db, attempt_id, for_update=False):
    keys = [
        'attempt_id', 'created_at', 'full_data', 'team_data', 'score'
    ]
    tasks = db.tables.tasks
    result = db.load_row(
        tasks, attempt_id, keys, key='attempt_id', for_update=for_update)
    for key in ['full_data', 'team_data']:
        result[key] = db.load_json(result[key])
    return result


def load_task_team_data(db, attempt_id):
    """ Return the team data for the given attempt, or None if there
        is no task assigned to the attempt.
    """
    tasks = db.tables.tasks
    row = db.load_row(
        tasks, attempt_id, ['score', 'team_data'], key='attempt_id')
    if row is None:
        return None
    result = db.load_json(row['team_data'])
    result['score'] = row['score']
    return result


def assign_task(db, attempt_id, now):
    """ Assign a task to the attempt.
        The team performing the attempt must be valid, otherwise
        an exception is raised.
        If this is a training attempt, the team is locked.
    """
    attempt = load_attempt(db, attempt_id, now=now)
    if attempt['started_at'] is not None:
        return ModelError('already have a task')
    team_id = attempt['team_id']
    # The team must be valid to obtain a task.
    team = load_team(db, team_id, for_update=True)
    validate_team(db, team, now=now)
    # TODO: check number of access codes entered
    # Verify that the round is open for training (and implicily for
    # timed attempts).
    round_id = attempt['round_id']
    round_ = load_round(db, round_id, now=now)
    if round_['status'] != 'open':
        raise ModelError('round not open')
    if now < round_['training_opens_at']:
        raise ModelError('training is not open')
    duration = round_['duration']
    # Allocate a task that the team has never had, and associate it
    # with the attempt.
    task = get_new_team_task(db, round_, team_id)
    task_attrs = {
        'attempt_id': attempt_id,
        'created_at': now,
        'task_dir': task['task_dir'],
        'score': task['score'],
        'full_data': db.dump_json(task['full_data']),
        'team_data': db.dump_json(task['team_data']),
    }
    tasks = db.tables.tasks
    db.insert_row(tasks, task_attrs)
    attempt_attrs = {'started_at': now}
    if attempt['is_training']:
        # Lock the team.
        teams = db.tables.teams
        db.update_row(teams, team_id, {'is_locked': True})
    else:
        # Set the closing time on the attempt.
        attempt_attrs['closes_at'] = now + timedelta(minutes=duration)
    attempts = db.tables.attempts
    db.update_row(attempts, attempt_id, attempt_attrs)
    # Create the team's workspace.
    create_attempt_workspace(db, attempt_id, now)


def get_user_task_hint(db, user_id, query):
    attempt_id = get_user_current_attempt_id(db, user_id)
    if attempt_id is None:
        raise ModelError('no current attempt')
    task = load_task(db, attempt_id, for_update=True)
    if task is None:
        raise ModelError('no task')
    task_module = get_attempt_task_module(db, attempt_id)
    # get_hint updates task in-place
    success = task_module.get_hint(task, query)
    if not success:
        return False
    score = task_module.get_current_score(task)
    tasks = db.tables.tasks
    db.update_row(tasks, attempt_id, {
        'score': score,
        'team_data': db.dump_json(task['team_data'])
    }, key='attempt_id')
    return True


def reset_user_task_hints(db, user_id, force=False):
    attempt_id = get_user_current_attempt_id(db, user_id)
    if not force and attempt_id is None:
        raise ModelError('no current attempt')
    attempt = load_attempt(db, attempt_id, for_update=True)
    if not force and not attempt['is_training']:
        raise ModelError('forbidden')
    task = load_task(db, attempt_id)
    if task is None:
        raise ModelError('no task')
    # reset_hints updates task in-place
    task_module = get_attempt_task_module(db, attempt_id)
    task_module.reset_hints(task)
    score = task_module.get_current_score(task)
    tasks = db.tables.tasks
    db.update_row(tasks, attempt_id, {
        'score': score,
        'team_data': db.dump_json(task['team_data'])
    }, key='attempt_id')


#
# Functions below this point are used within this file only.
#

def get_round_task_module(round_):
    try:
        return import_module(round_['task_module'])
    except ImportError:
        raise ModelError('task module not found')


def get_attempt_task_module(db, attempt_id):
    attempt = load_attempt(db, attempt_id)
    round_ = load_round(db, attempt['round_id'])
    return get_round_task_module(round_)


def get_new_team_task(db, round_, team_id):  # XXX team/round
    tasks = db.tables.tasks
    attempts = db.tables.attempts
    tasks_path = round_['tasks_path']
    # XXX better to load task_dir for all of the team's tasks, and
    #     generate until we obtain a new one
    # XXX lock the tasks table?
    task_module = get_round_task_module(round_)
    for i in range(0, 15):  # XXX hard-wired number of tries
        task = task_module.get_task(tasks_path)
        task_dir = task['task_dir']
        query = db.query(tasks & attempts) \
            .where(tasks.attempt_id == attempts.id) \
            .where(attempts.team_id == team_id) \
            .where(tasks.task_dir == task_dir) \
            .fields(tasks.attempt_id)
        row = db.first(query)
        if row is None:
            task['score'] = task_module.get_current_score(task)
            return task
    raise ModelError('task pool exhausted')


def fix_tasks(db, round_id):
    """ This function can be used to fix all the tasks assigned for a
        given round.  It calls the task module's fix_task function on
        each task, and updates the tasks for which fix_task returns True.
    """
    round_ = load_round(db, round_id)
    task_module = get_round_task_module(round_)
    keys = [
        'attempt_id', 'created_at', 'full_data', 'team_data', 'score'
    ]
    tasks = db.tables.tasks
    attempts = db.tables.tasks
    query = (
        db.query(
            (tasks & attempts)
            .on(tasks.attempt_id == attempts.id))
        .where(attempts.round_id == round_id)
        .fields(*[getattr(tasks, key) for key in keys]))
    count = 0
    for row in list(db.all(query)):
        task = {key: row[i] for i, key in enumerate(keys)}
        for key in ['full_data', 'team_data']:
            task[key] = db.load_json(task[key])
        if task_module.fix_task(task):
            count += 1
            for key in ['full_data', 'team_data']:
                task[key] = db.dump_json(task[key])
            db.update_row(tasks, task['attempt_id'], task,
                          key='attempt_id')
    return count
