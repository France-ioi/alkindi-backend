import json
import iso8601
from babel.dates import format_date, format_datetime

__all__ = [
    'HtmlSafeStr', 'classnames', 'literal', 'to_json',
    'localize_date', 'localize_datetime'
]


class HtmlSafeStr(str):

    def __html__(self):
        return self


def classnames(**kws):
    classes = [key for key, value in kws.items() if value]
    return ' '.join(classes)


def literal(text):
    return HtmlSafeStr(text)


def to_json(value):
    return HtmlSafeStr(json.dumps(value))


def localize_date(value, locale='fr_FR'):
    """
    Formats a date object or an iso8601 string with the given locale.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = iso8601.parse_date(value)
    return format_date(value, locale=locale)


def localize_datetime(value, locale='fr_FR'):
    """
    Formats a datetime object or an iso8601 string with the given locale.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = iso8601.parse_date(value)
    return format_datetime(value, locale=locale)
