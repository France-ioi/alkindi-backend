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


def canon_input(input):
    # Map to ASCII, strip, uppercase.
    input = unidecode(input).strip().upper()
    return input


def grade(task, data):

    in1 = data.get('input1', '')
    in2 = data.get('input2', '')

    # in.split('\n').map(in1)
    # canon_input(in2)
    score = 0
    is_solution = score > 0
    is_full_solution = score == 1400

    return {
        'input': [],
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
