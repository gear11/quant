"""
 Functions for colored and bold output to the console
"""
from .markets import TickBar

from decimal import Decimal
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


class console: # NOQA
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
        print(cls.wrap(msg, Colors.WARNING))

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

    @classmethod
    def render_bar(cls, bar: TickBar, prev_close=None, prev_wap=None):
        return cls.render_bar_data(bar.symbol, bar.date, bar.open, bar.close, bar.wap, bar.volume, prev_close, prev_wap)

    @classmethod
    def render_bar_data(cls, symbol, date, open_, high, low, close, ref_price, volume, prev_close=None, prev_ref_price=None):
        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
        close_str = cls.render_val(close, prev_close if prev_close else open_)
        ref_price_str = cls.render_val(ref_price, prev_ref_price if prev_ref_price else ref_price, bold=True)
        return f'{date_str} {symbol} {ref_price_str}' \
               f' O{cls.render_val(open_)}-H{cls.render_val(high, open_)}' \
               f'-L{cls.render_val(low, open_)}-C{close_str}' \
               f' {volume: >4}'

    @classmethod
    def print_data_frame(cls, symbol, df: DataFrame, verbose=False):
        prev_close = None
        prev_ref_price = None
        for index, row in df.iterrows():
            date = index if type(index) is datetime else dateparser.parse(str(index))
            args = [row[label] for label in df]
            args.extend([prev_close, prev_ref_price])
            print(cls.render_bar_data(symbol.upper(), date, *args))
            prev_close = row['Close']
            prev_ref_price = row[4]
        if verbose:
            print(df.describe(include='all'))
