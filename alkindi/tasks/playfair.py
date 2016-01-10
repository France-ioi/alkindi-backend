import os
import random
import re
from unidecode import unidecode
from difflib import SequenceMatcher
from decimal import Decimal

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


def canon_number(input):
    return re.sub('[^0-9]*', '', input)


def canon_address(input):
    # Map to ASCII, strip, uppercase.
    input = unidecode(input).strip().upper()
    # Remove all non-alphanum characters.
    input = re.sub('[^0-9A-Z]*', '', input)
    input = re.sub('W', 'V', input)
    return input


def grade(task, data):

    # Scores above score_threshold are considered solutions.
    score_threshold = Decimal('0.1')
    hints_score = task['team_data']['score']

    in_n1 = canon_number(data.get('n1', ''))
    in_n2 = canon_number(data.get('n2', ''))
    in_ad = canon_address(data.get('a', ''))

    (ex_n1, ex_n2, ex_ad) = task['full_data']['answer.txt'].split('\n')
    ex_n1 = canon_number(ex_n1)
    ex_n2 = canon_number(ex_n2)
    ex_ad = canon_address(ex_ad)

    numbers_equal = Decimal(int(ex_n1 == in_n1 and ex_n2 == in_n2))
    address_ratio = Decimal(str(SequenceMatcher(None, ex_ad, in_ad).ratio()))
    address_errors = address_ratio * Decimal(len(ex_ad))

    grading = {
        'input': {'n1': in_n1, 'n2': in_n2, 'ad': in_ad},
        'expected': {'n1': ex_n1, 'n2': ex_n2, 'ad': ex_ad},
        'numbers_equal': str(numbers_equal),
        'address_ratio': str(address_ratio),
        'address_errors': str(address_errors)
    }

    score = ((Decimal(hints_score) *
              (numbers_equal * Decimal('0.5') +
               Decimal(int(in_ad == ex_ad)) * Decimal('0.5'))) /
             Decimal(INITIAL_SCORE))

    is_solution = score >= score_threshold

    return (grading, score, is_solution)


def test_grader():
    print(grade(
        {'full_data': {'answer.txt': "14\n449\n134 avenue de Wagram"},
         'team_data': {'score': 490}},
        {"n1": '14', "n2": '449', 'a': "134 avenue de Vagram"}))


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
