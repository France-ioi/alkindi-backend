import os
import random
import re
from unidecode import unidecode

__all__ = ['get_task', 'get_hint', 'get_current_score', 'grade']


INITIAL_SCORE = 1000
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVXYZ'


def get_task(index, choice=None):
    with open(index, 'r') as f:
        lines = f.read().strip().split('\n')
        if choice is None:
            line = random.choice(lines)
        else:
            line = lines[choice]
        base_dir = os.path.dirname(index)
        task_txt = os.path.join(base_dir, line)
        if not os.path.isfile(task_txt):
            raise RuntimeError("missing task file: {}".format(task_txt))
        task_dir = os.path.dirname(task_txt)
        hints_txt = task_file(task_dir, 'hints.txt')
        plain_txt = task_file(task_dir, 'plain.txt')
        answer_txt = task_file(task_dir, 'answer.txt')
    with open(task_txt, 'r') as f:
        cipher_text = f.read().strip()
    with open(hints_txt, 'r') as f:
        hints = f.read().strip()
    with open(plain_txt, 'r') as f:
        plain_text = f.read().strip()
    with open(answer_txt, 'r') as f:
        answer = f.read().strip()
    hints = re.sub("'(.)' ?\n?", '\\1', hints)
    answer_lines = answer.split('\n')
    while len(answer_lines[-1]) == 0:
        answer_lines.pop()
    answer_lines = [line.strip() for line in answer_lines]
    return {
        'task_dir': task_dir,
        'full_data': {
            'cipher_text': cipher_text,
            'hints': hints,
            'plain_text': plain_text,
            'answer': answer_lines
        },
        'team_data': {
            'cipher_text': cipher_text
        }
    }


def task_file(dir, name):
    full_path = os.path.join(dir, name)
    if not os.path.isfile(full_path):
        raise RuntimeError("missing file: {}".format(full_path))
    return full_path


def get_current_score(task):
    return 0


def get_hint_cost(query):
    return 0


def get_hint(task, query):
    return False


def reset_hints(task):
    pass


def grade(task, data):

    in1 = unidecode(data.get('input1', '')).strip().split('\n')
    in2 = unidecode(data.get('input2', '')).strip()

    supplied_lines = [s.strip() for s in in1]
    supplied_lines.append(in2)
    expected_lines = task['full_data']['answer']
    print("supplied_lines {} / expected_lines {}".format(
        len(supplied_lines), len(expected_lines)))

    if len(supplied_lines) != len(expected_lines):
        return None
    n_correct = 0
    for p in zip(supplied_lines, expected_lines):
        if p[0] == p[1]:
            n_correct += 1

    score = n_correct * 200
    is_solution = score > 0
    is_full_solution = n_correct == len(expected_lines)

    return {
        'input': {'supplied_lines': supplied_lines},
        'expected': [],
        'feedback': {},
        'base_score': '0',
        'actual_score': str(score),
        'is_solution': is_solution,
        'is_full_solution': is_full_solution,
    }


if __name__ == '__main__':
    import json
    task = get_task('/tmp/tour4/INDEX', choice=0)
    print("Task: {}".format(json.dumps(task)))
    # print("Grade city: {}".format(grade(task, {
    #     'c': 'francfort'
    # })))
