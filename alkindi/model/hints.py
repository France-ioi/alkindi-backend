
from alkindi.errors import ModelError
from alkindi.model.rounds import load_round
from alkindi.model.participations import load_participation
from alkindi.model.attempts import load_attempt
from alkindi.model.round_tasks import load_round_task
from alkindi.model.tasks import load_task
from alkindi.model.task_instances import load_task_instance
from alkindi.tasks import task_grant_hint


def get_task_instance_hint(db, attempt_id, query, now):

    # Load the attempt and check that it is still open.
    attempt = load_attempt(db, attempt_id, now)
    if attempt['is_closed']:
        raise ModelError('attempt is closed')

    # Load the participation and verify that the round is still open.
    participation = load_participation(db, attempt['participation_id'])
    round_ = load_round(db, participation['round_id'], now)
    if round_['status'] != 'open':
        raise ModelError('round not open')

    # Obtain task backend URL and Authorization header.
    round_task = load_round_task(db, attempt['round_task_id'])
    task = load_task(db, round_task['task_id'])
    backend_url = task['backend_url']
    auth = task['backend_auth']

    # Load the task instance.
    task_instance = load_task_instance(db, attempt_id, for_update=True)
    if task_instance is None:
        raise ModelError('no task instance')
    full_data = task_instance['full_data']
    team_data = task_instance['team_data']

    # Get the task backend to validate the hint request and apply the hint
    # from full_data onto team_data.
    print('grantHint query {}'.format(query))
    result = task_grant_hint(backend_url, full_data, team_data, query, auth)
    # result: {success, task, full_task}
    print('grantHint result {}'.format(result))

    # If successful, update the task instance.
    # 'full_data' is also updated in case the task needs to store extra private
    # information there.
    if result['success']:
        task_instances = db.tables.task_instances
        db.update_row(task_instances, {'attempt_id': attempt_id}, {
            'full_data': db.dump_json(task['full_task']),
            'team_data': db.dump_json(task['task']),
            'updated_at': now
        })

    return result['success']


def reset_task_instance_hints(db, attempt_id, now, force=False):
    # XXX to rewrite
    attempt = load_attempt(db, attempt_id, for_update=True)
    if not force and not attempt['is_training']:
        raise ModelError('forbidden')
    raise ModelError('not implemented')
