import argparse
import logging
from collections.abc import Set, Iterable
from typing import Dict

from .timeutil import Timer as UtilTimer

Timer = UtilTimer


def diff(a: Iterable, b: Iterable) -> (Set, Set):
    added = [e for e in b if e not in set(a)]
    removed = [e for e in a if e not in set(b)]
    return added, removed


def reverse(d: Dict) -> Dict:
    return {v: k for k, v in d.items()}


class Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument('--debug', dest='debug', action='store_const', const=True, default=False,
                          help='Log at debug level')
        self.add_argument('--info', dest='info', action='store_const', const=True, default=False,
                          help='Log at info level')

    def parse_args(self, *args, **kwargs):
        parsed = super().parse_args(*args, **kwargs)
        level = logging.DEBUG if parsed.debug else logging.INFO if parsed.info else logging.WARNING
        logging.basicConfig(level=level)
        logging.getLogger('root').setLevel(level)
        return parsed

    def allow_additional_args(self):
        self.add_argument('additional', nargs='+', help='Ignored arguments')
        return self
