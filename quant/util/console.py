"""
 Functions for colored and bold output to the console
"""

from decimal import Decimal
from numpy import float64


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    GRAY = '\033[97m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Console:
    @classmethod
    def wrap(cls, msg, color: str):
        return f'{color}{msg}{Colors.END}'

    @classmethod
    def announce(cls, msg):
        print(cls.wrap(msg, Colors.BLUE))

    @classmethod
    def error(cls, msg):
        print(cls.wrap(msg, Colors.RED))

    @classmethod
    def warn(cls, msg):
        print(cls.wrap(msg, Colors.YELLOW))

    @classmethod
    def render_val(cls, value, comparison=None, bold=False):
        if value is None:
            return 'NaN'
        comparison = value if comparison is None else comparison
        start_color = Colors.RED if value < comparison else Colors.GREEN if value > comparison else ''
        bold = Colors.BOLD if bold else ''
        is_float = type(value) in (float, Decimal, float64)
        if is_float and value < 10:
            val_str = f'{value:.3f}'
        elif is_float:
            val_str = f'{value:.2f}'
        else:
            val_str = f'{value}'
        return f'{start_color}{bold}{val_str}{Colors.END}'
