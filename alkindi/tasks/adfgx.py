import os
import random
import re
from datetime import datetime
from unidecode import unidecode
from decimal import Decimal

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
    hint_lines = hints.split('\n')
    permutation = read_permutation(hint_lines[0])
    substitution_grid = read_grid(hint_lines[-5:])
    initial_permutation = empty_permutation(permutation)
    initial_grid = empty_grid(substitution_grid)
    return {
        'task_dir': task_dir,
        'full_data': {
            'cipher_text': cipher_text,
            'hints': hints,
            'plain_text': plain_text,
            'answer': answer,
            'permutation': permutation,
            'substitution_grid': substitution_grid,
        },
        'team_data': {
            'cipher_text': cipher_text,
            'permutation': initial_permutation,
            'substitution_grid': initial_grid,
        }
    }


def task_file(dir, name):
    full_path = os.path.join(dir, name)
    if not os.path.isfile(full_path):
        raise RuntimeError("missing file: {}".format(full_path))
    return full_path


def read_permutation(text):
    chars = list(text)
    return [p[0] for p in sorted(enumerate(chars), key=lambda p: p[1])]


def empty_permutation(permutation):
    return [None for i in permutation]


def read_grid(lines):
    return [
        [ALPHABET.index(cell) for cell in line.strip().split(' ')]
        for line in lines[-5:]
    ]


def empty_grid(grid):
    return [[None for cell in row] for row in grid]


def find_in_grid(grid, value):
    for row, row_cells in enumerate(grid):
        for col, cell in enumerate(row_cells):
            if cell == value:
                return (row, col)
    return (None, None)


def get_subst_decipher_hint(task, row, col):
    dst_hints = task['team_data']['substitution_grid']
    if dst_hints[row][col] is not None:
        return False
    src_hints = task['full_data']['substitution_grid']
    dst_hints[row][col] = src_hints[row][col]
    return True


def get_subst_cipher_hint(task, rank):
    src_hints = task['full_data']['substitution_grid']
    dst_hints = task['team_data']['substitution_grid']
    row, col = find_in_grid(src_hints, rank)
    if dst_hints[row][col] is not None:
        return True
    dst_hints[row][col] = src_hints[row][col]
    return True


def get_perm_decipher_hint(task, line):
    dst_hints = task['team_data']['permutation']
    if dst_hints[line] is not None:
        return False
    src_hints = task['full_data']['permutation']
    dst_hints[line] = src_hints[line]
    return True


def get_perm_cipher_hint(task, line):
    src_hints = task['full_data']['permutation']
    inv_line = src_hints.index(line)
    dst_hints = task['team_data']['permutation']
    if dst_hints[inv_line] is not None:
        return False
    dst_hints[inv_line] = src_hints[inv_line]
    return True


def get_current_score(task):
    team_data = task['team_data']
    score = INITIAL_SCORE
    if 'hint_queries' not in team_data:
        return score
    for query in team_data['hint_queries']:
        score -= get_hint_cost(query)
    return score


def get_hint_cost(query):
    if query['type'] == 'subst-decipher':
        return 35
    elif query['type'] == 'subst-cipher':
        return 50
    elif query['type'] == 'perm-decipher':
        return 200
    elif query['type'] == 'perm-cipher':
        return 200
    else:
        return (INITIAL_SCORE + 1)


def save_hint_query(task, query):
    team_data = task['team_data']
    if 'hint_queries' not in team_data:
        team_data['hint_queries'] = []
    query['submitted_at'] = datetime.utcnow().isoformat()
    team_data['hint_queries'].append(query)


def get_hint(task, query):
    score = get_current_score(task)
    cost = get_hint_cost(query)
    if cost > score:
        return False
    save_hint_query(task, query)
    if query['type'] == 'subst-decipher':
        row = int(query['row'])
        col = int(query['col'])
        return get_subst_decipher_hint(task, row, col)
    if query['type'] == 'subst-cipher':
        rank = int(query['rank'])
        return get_subst_cipher_hint(task, rank)
    if query['type'] == 'perm-decipher':
        line = int(query['line'])
        return get_perm_decipher_hint(task, line)
    if query['type'] == 'perm-cipher':
        line = int(query['line'])
        return get_perm_cipher_hint(task, line)
    return False


def reset_hints(task):
    team_data = task['team_data']
    team_data['substitution_grid'] = empty_grid(team_data['substitution_grid'])
    team_data['permutation'] = empty_permutation(team_data['permutation'])


def canon_input(input):
    # Map to ASCII, strip, uppercase.
    input = unidecode(input).strip().upper()
    # Remove all non-alphanum characters.
    input = re.sub('[^0-9A-Z]*', '', input)
    input = re.sub('W', 'V', input)
    return input


def grade(task, data):

    # Scores above score_threshold are considered solutions.
    score_threshold = Decimal('1')

    base_score = get_current_score(task)

    in_c = canon_input(data.get('c', ''))
    in_m1 = canon_input(data.get('m1', ''))
    in_m2 = canon_input(data.get('m2', ''))
    in_m3 = canon_input(data.get('m3', ''))
    in_metals = sorted((in_m1, in_m2, in_m3))

    total_len = len(in_c) + len(in_m1) + len(in_m2) + len(in_m3)
    if total_len == 0 or total_len > 100:
        return None

    (ex_c, ex_m1, ex_m2, ex_m3) = task['full_data']['answer'].split('\n')
    ex_c = canon_input(ex_c)
    ex_m1 = canon_input(ex_m1)
    ex_m2 = canon_input(ex_m2)
    ex_m3 = canon_input(ex_m3)
    ex_metals = sorted((ex_m1, ex_m2, ex_m3))

    city_equal = Decimal(int(ex_c == in_c))
    metals_equal = Decimal(int(ex_metals == in_metals))

    score_factor = (
        city_equal * Decimal('0.5') +
        metals_equal * Decimal('0.5')
    )
    score = Decimal(base_score) * score_factor
    is_solution = score >= score_threshold
    is_full_solution = score_factor == Decimal('1')

    team_data = task['team_data']
    return {
        'input': {'c': in_c, 'm1': in_m1, 'm2': in_m2, 'm3': in_m3},
        'expected': {'c': ex_c, 'm1': ex_m1, 'm2': ex_m2, 'm3': ex_m3},
        'hints': {
            'substitution_grid': team_data['substitution_grid'],
            'permutation': team_data['permutation'],
            'hint_queries': team_data.get('hint_queries')
        },
        'feedback': {
            'city': city_equal == Decimal(1),
            'metals': metals_equal == Decimal(1)
        },
        'base_score': str(base_score),
        'actual_score': str(score),
        'is_solution': is_solution,
        'is_full_solution': is_full_solution,
    }


def test_grader():
    print(grade(
        {'full_data': {'answer.txt': "14\n449\n134 avenue de Wagram"},
         'team_data': {'score': 490}},
        {"n1": '14', "n2": '449', 'a': "134 avenue de Vagram"}))


if __name__ == '__main__':
    import json
    task = get_task('/home/sebc/alkindi/tasks/adfgx/INDEX', choice=0)
    print("Task: {}".format(json.dumps(task)))
    print("Initial score: {}".format(get_current_score(task)))
    print("Grade city: {}".format(grade(task, {
        'c': 'francfort'
    })))
    print("Grade metals: {}".format(grade(task, {
        'm1': 'yttrium',
        'm2': 'terbium',
        'm3': 'gadolinium'
    })))
    print("Grade city+metals: {}".format(grade(task, {
        'c': 'francfort',
        'm1': 'yttrium',
        'm2': 'terbium',
        'm3': 'gadolinium'
    })))
