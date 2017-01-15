
from datetime import timedelta
from decimal import Decimal

from alkindi.errors import ModelError
from alkindi.model.attempts import load_attempt, update_attempt_with_grading
from alkindi.model.participations import (
    load_participation, update_participation)
from alkindi.model.rounds import load_round
from alkindi.model.task_instances import load_task_instance


def grade_answer(db, attempt_id, submitter_id, data, now):
    attempt = load_attempt(db, attempt_id, now)
    participation_id = attempt['participation_id']
    participation = load_participation(
        db, participation_id, for_update=True)
    is_training = attempt['is_training']
    # Fail if the attempt is closed.
    if attempt['is_closed']:
        raise ModelError('attempt is closed')
    # Get the greatest ordinal and nth most recent submitted_at.
    (prev_ordinal, nth_submitted_at) = \
        get_attempt_latest_answer_infos(db, attempt_id, nth=2)
    # Fail if timed(not training) and there are more answers than
    # allowed.
    round_ = load_round(db, participation['round_id'], now)
    if round_['status'] != 'open':
        raise ModelError('round not open')
    max_answers = round_['max_answers']
    if (not is_training and max_answers is not None and
            prev_ordinal >= max_answers):
        raise ModelError('too many answers')
    # Fail if answer was submitted too recently.
    if nth_submitted_at is not None:
        if now < nth_submitted_at + timedelta(minutes=1):
            raise ModelError('too soon')
    ordinal = prev_ordinal + 1
    # Perform grading.
    task_instance = load_task_instance(db, attempt_id)
    grading = None  # XXX TODO task_module.grade(task, data)
    if grading is None:
        raise ModelError('invalid input')
    update_attempt_with_grading(db, attempt_id, grading)
    # Store the answer.
    answers = db.tables.answers
    answer = {
        'attempt_id': attempt_id,
        'submitter_id': submitter_id,
        'ordinal': ordinal,
        'created_at': now,
        'answer': db.dump_json(data),
        'grading': db.dump_json(grading),
        'score': grading['actual_score'],
        'is_solution': grading['is_solution'],
        'is_full_solution': grading['is_full_solution']
    }
    answer['id'] = db.insert_row(answers, answer)
    # Best score for the participation?
    new_score = Decimal(answer['score'])
    if not is_training and (participation['score'] is None or
                            new_score > participation['score']):
        update_participation(
            db, participation_id, {'score': new_score})
    return answer


def get_attempt_latest_answer_infos(db, attempt_id, nth=2):
    """ Returns a pair whose first element is greatest answer ordinal
        for the attempt (or 0, if there are no answers), and whose
        second element is datetime of the nth most recent answer for
        the attempt (or None, if it does not exist).
    """
    answers = db.tables.answers
    query = db.query(answers) \
        .where(answers.attempt_id == attempt_id) \
        .order_by(answers.ordinal.desc()) \
        .fields(answers.ordinal, answers.created_at)[0:nth]
    rows = list(db.all(query))
    if len(rows) == 0:
        return (0, None)
    if len(rows) == 1:
        return (rows[0][0], None)
    return (rows[0][0], rows[-1][1])


def load_limited_attempt_answers(db, attempt_id):
    """ Load the answers for the given attempt, and return only the
        columns that are safe to send back to the user.
    """
    answers = db.tables.answers
    cols = [
        'id', 'submitter_id', 'ordinal', 'created_at', 'answer',
        'score', 'is_solution', 'is_full_solution'
    ]
    query = db.query(answers) \
        .where(answers.attempt_id == attempt_id) \
        .order_by(answers.ordinal.desc())
    query = query.fields(*[getattr(answers, c) for c in cols])
    results = []
    for row in db.all(query):
        result = {c: row[i] for i, c in enumerate(cols)}
        for key in ['is_solution']:
            result[key] = db.load_bool(result[key])
        for key in ['answer']:
            result[key] = db.load_json(result[key])
        results.append(result)
    return results
