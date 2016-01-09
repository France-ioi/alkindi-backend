import os
import random
import re


INITIAL_SCORE = 500


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
    cipher_text = '\n'.join(task_lines[0:2])
    firstname = task_lines[2]
    initial_grid = '\n'.join(task_lines[grid_pos:])
    hints = parse_grid(hints_grid)
    initial_hints = parse_grid(initial_grid)
    return {
        'task_dir': task_dir,
        'score': INITIAL_SCORE,
        'full_data': {
            'plain_text': plain_text,
            'cipher_text': cipher_text,
            'answer_txt': answer,
            'firstname': firstname,
            'hints': hints,
            'initial_hints': initial_hints,
        },
        'team_data': {
            'cipher_text': cipher_text,
            'firstname': firstname,
            'hints': initial_hints
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
        {'q': 'hint', 'l': i} for i in indices
    ]
    span = 5
    return [objects[i:i+span] for i in range(0, len(chars), span)]


def get_hint(task, query):
    try:
        if query['type'] == 'grid':
            return get_grid_hint(task, int(query['row']), int(query['col']))
        if query['type'] == 'alphabet':
            return get_alphabet_hint(task, int(query['rank']))
        return False
    except KeyError:
        return False


def get_grid_hint(task, row, col):
    if task['score'] < 10:
        return False
    try:
        dst_hints = task['team_data']['hints']
        if 'l' in dst_hints[row][col]:
            return False
        src_hints = task['full_data']['hints']
        cell = src_hints[row][col]
        dst_hints[row][col] = cell
        task['score'] -= 10
        return True
    except IndexError:
        return False


def get_alphabet_hint(task, rank):
    if task['score'] < 10:
        return False
    src_hints = task['full_data']['hints']
    dst_hints = task['team_data']['hints']
    for row, row_cells in enumerate(src_hints):
        for col, cell in enumerate(row_cells):
            if cell['l'] == rank and 'l' not in dst_hints[row][col]:
                task['score'] -= 10
                dst_hints[row][col] = cell
                return True
    return False


def print_hints(hints):
    for row_cells in hints:
        for cell in row_cells:
            if 'l' in cell:
                print(ALPHABET[cell['l']], end=' ')
            else:
                print(' ', end=' ')
        print('')


def reset_hints(task):
    task['score'] = INITIAL_SCORE
    task['team_data']['hints'] = task['full_data']['initial_hints']


def fix_hints(hints):
    for row_cells in hints:
        for cell in row_cells:
            q = cell.get('q')
            if q == 'hint':
                return False
            if q == 'confirmed':
                cell['q'] = 'hint'
    return True


def fix_task(task):
    # Use a binary or to always check all three grids.
    return (fix_hints(task['full_data']['hints']) |
            fix_hints(task['full_data']['initial_hints']) |
            fix_hints(task['team_data']['hints']))


if __name__ == '__main__':
    task = get_task('/home/sebc/alkindi/tasks/playfair/INDEX')
    print('fixed? {}'.format(fix_task(task)))
    print('fixed again? {}'.format(fix_task(task)))
    print_hints(task['team_data']['hints'])
    print("Initial score={}\n".format(task['score']))

    print("Getting a grid hint:")
    get_hint(task, {'type': 'grid', 'row': 0, 'col': 0})
    print_hints(task['team_data']['hints'])
    print("New score={}\n".format(task['score']))

    print("Getting an alphabet hint:")
    get_hint(task, {'type': 'alphabet', 'rank': 4})
    print_hints(task['team_data']['hints'])
    print("New score={}\n".format(task['score']))
