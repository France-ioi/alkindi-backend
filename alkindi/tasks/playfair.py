import os
import random
import re


def get_task(index):
    with open(index, 'r') as f:
        lines = f.read().strip().split('\n')
        line = random.choice(lines)
        base_dir = os.path.dirname(index)
        task_txt = os.path.join(base_dir, line)
        if not os.path.isfile(task_txt):
            raise RuntimeError("missing task file: {}".format(task_txt))
        task_dir = os.path.dirname(task_txt)
        hints_txt = task_file(task_dir, 'hints.txt')
        plain_txt = task_file(task_dir, 'plain.txt')
        answer_txt = task_file(task_dir, 'answer.txt')
    with open(task_txt, 'r') as f:
        task = f.read().strip()
    with open(hints_txt, 'r') as f:
        hints_grid = f.read().strip()
    with open(plain_txt, 'r') as f:
        plain_text = f.read().strip()
    with open(answer_txt, 'r') as f:
        answer = f.read().strip()
    task_lines = task.split('\n')
    grid_pos = len(task_lines) - 5
    cipher_text = '\n'.join(task_lines[:grid_pos])
    initial_grid = '\n'.join(task_lines[grid_pos:])
    return {
        'full_data': {
            'plain_text': plain_text,
            'cipher_text': cipher_text,
            'hints': parse_grid(hints_grid),
            'answer_txt': answer,
        },
        'team_data': {
            'cipher_text': cipher_text,
            'hints': parse_grid(initial_grid)
        }
    }


def task_file(dir, name):
    full_path = os.path.join(dir, name)
    if not os.path.isfile(full_path):
        raise RuntimeError("missing file: {}".format(full_path))
    return full_path


ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVXYZ'


def parse_grid(text):
    chars = re.split('\s+', text)
    indices = [ALPHABET.find(c) for c in chars]
    objects = [
        {'q': 'unknown'} if i == -1 else
        {'q': 'confirmed', 'l': i} for i in indices
    ]
    span = 5
    return [objects[i:i+span] for i in range(0, len(chars), span)]


if __name__ == '__main__':
    task = get_task('/home/sebc/alkindi/tasks/playfair/INDEX')
    print(task)
