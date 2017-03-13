
import random


def as_int(s):
    """ Return the int value of string input ``s`` is it is not ``None``,
    return ``None`` otherwise."""
    if s is None:
        return None
    return int(s)


def generate_code():
    # TODO: prevent rn/m confusion
    charsAllowed = "2346789abcdefghijkmnpqrtuvwxyz"
    code = ""
    for pos in range(0, 8):
        code += random.choice(charsAllowed)
    return code
