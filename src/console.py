"""
 Functions for colored and bold output to the console
"""


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    OKCYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def blue(msg):
    return f'{Colors.BLUE}{msg}{Colors.ENDC}'


def announce(msg):
    print(f'{blue(msg)}')


def fmt(value, comparison=None, bold=False):
    comparison = value if comparison is None else comparison
    start_color = Colors.RED if value < comparison else Colors.GREEN if value > comparison else ''
    bold = Colors.BOLD if bold else ''
    val_str = f'{value:.2f}' if type(value) is float else f'{value}'
    return f'{start_color}{bold}{val_str}{Colors.ENDC}'
