import argparse
import logging
from collections.abc import Set, Iterable
from typing import Dict

from .timeutil import Timer as UtilTimer
from .console import Console, Colors

Timer = UtilTimer
console = Console


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
        root = logging.getLogger('root')
        level = logging.DEBUG if parsed.debug else logging.INFO if parsed.info else logging.WARNING
        root.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(ColoredFormatter())
        root.addHandler(handler)

        return parsed

    def allow_additional_args(self):
        self.add_argument('additional', nargs='+', help='Ignored arguments')
        return self


class ColoredFormatter(logging.Formatter):

    _colors = {
        logging.DEBUG: Colors.BLUE,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED
    }

    def __init__(self):
        super().__init__('%(asctime)s: %(levelname)s: %(name)s: %(message)s')

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        if record.levelno in ColoredFormatter._colors:
            return console.wrap(s, ColoredFormatter._colors[record.levelno])
        return s
