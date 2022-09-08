"""
 Functions for colored and bold output to the console
"""
from decimal import Decimal
from markets import TickBar
from pandas import DataFrame
import datetime
import dateparser
from numpy import float64


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def wrap(msg, color: str):
    return f'{color}{msg}{Colors.END}'


def announce(msg):
    print(wrap(msg, Colors.BLUE))


def error(msg):
    print(wrap(msg, Colors.RED))


def warn(msg):
    print(wrap(msg, Colors.WARNING))


def render_val(value, comparison=None, bold=False):
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


def render_bar(bar: TickBar, prev_close=None, prev_wap=None):
    render_bar_data(bar.symbol, bar.date, bar.open, bar.close, bar.wap, bar.volume, prev_close, prev_wap)
    date_str = bar.date.strftime("%Y-%m-%d %H:%M:%S")
    close_str = render_val(bar.close, prev_close if prev_close else bar.open)
    wap_str = render_val(bar.wap, prev_wap if prev_wap else bar.wap, bold=True)
    return f'{date_str} {bar.symbol} {wap_str}' \
           f' O{render_val(bar.open)}-H{render_val(bar.high, bar.open)}' \
           f'-L{render_val(bar.low, bar.open)}-C{close_str}' \
           f' {bar.volume: >4}'


def render_bar_data(symbol, date, open_, high, low, close, ref_price, volume, prev_close=None, prev_ref_price=None):
    date_str = date.strftime("%Y-%m-%d %H:%M:%S")
    close_str = render_val(close, prev_close if prev_close else open_)
    ref_price_str = render_val(ref_price, prev_ref_price if prev_ref_price else ref_price, bold=True)
    return f'{date_str} {symbol} {ref_price_str}' \
           f' O{render_val(open_)}-H{render_val(high, open_)}' \
           f'-L{render_val(low, open_)}-C{close_str}' \
           f' {volume: >4}'


def print_data_frame(symbol, df: DataFrame):
    for index, row in df.iterrows():
        date = index if type(index) is datetime else dateparser.parse(str(index))
        args = [row[label] for label in df]
        print(render_bar_data(symbol.upper(), date, *args))
