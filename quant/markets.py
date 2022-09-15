from __future__ import annotations

from .util.events import Event, observe
from .util.misc import decimal as d

import pandas as pd
from decimal import Decimal
from typing import NamedTuple
from datetime import datetime
from enum import Enum
import dateparser


class Resolution(Enum):
    TICK = 0
    FIVE_SEC = 5
    MINUTE = 60
    DAY = 60 * 60 * 24
    WEEK = 60 * 60 * 24 * 7
    MONTH = 60 * 60 * 24 * 7 * 30


def last_seven_days(symbol):
    return DataRequest(symbol, dateparser.parse('7 days ago'), datetime.now())


class DataRequest(NamedTuple):
    symbol: str
    start: datetime
    end: datetime
    resolution: Resolution = Resolution.DAY

    @classmethod
    def make(cls, start: datetime | str, end: datetime | str, symbol: str, res=Resolution.DAY) -> DataRequest:
        start = start if type(start) is datetime else dateparser.parse(start)
        end = end if type(end) is datetime else dateparser.parse(end)
        return DataRequest(symbol, start, end, res)

    def size_in_days(self):
        return (self.end - self.start).days

    def expected_size(self):
        delta = self.end - self.start
        return (delta.seconds + delta.days * 60 * 60 * 24) / self.resolution.value  # NOQA can't figure out enum


class Symbols:

    @staticmethod
    def is_crypto(symbol):
        return symbol.upper() in ('BTC', 'ETH')

    @staticmethod
    def is_forex(symbol):
        return symbol.upper() in ('EUR', 'BTC')


class TickBar(NamedTuple):
    symbol: str
    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    wap: Decimal
    volume: int

    @staticmethod
    def new(symbol: str, date: datetime, open: float, high: float, low: float, close: float, wap: float, volume: int):
        return TickBar(symbol, date, d(open), d(high), d(low), d(close), d(wap), volume)


class TickEvent(Event):
    def __init__(self, tick_bar: TickBar):
        self.tick_bar = tick_bar


class SymbolData:

    labels = ['Open', 'High', 'Low', 'Close', 'Ref Price', 'Volume']

    def __init__(self, symbol: str, data_frame: pd.DataFrame = None):
        self.symbol = symbol.upper()
        if data_frame is not None:
            self.date_index = data_frame['Date']
            self.columns = {k: v for (k, v) in data_frame.items() if k != 'Date'}
        else:
            self.date_index = []
            self.columns = {label: [] for label in SymbolData.labels}

    def append_bar(self, bar: TickBar):
        self.date_index.append(bar.date)
        self.columns['Open'].append(float(bar.open))
        self.columns['High'].append(float(bar.high))
        self.columns['Low'].append(float(bar.low))
        self.columns['Close'].append(float(bar.close))
        self.columns['Ref Price'].append(float(bar.wap))
        self.columns['Volume'].append(bar.volume)

    def __getitem__(self, i) -> TickBar:
        return self.tick_bar(i)

    def tick_bar(self, i) -> TickBar:
        r = [self.columns[key][i] for key in self.columns.keys()]
        r.insert(0, self.date_index[i])
        r.insert(0, self.symbol)
        return TickBar(*r)

    @property
    def data_frame(self):
        data_frame = pd.DataFrame(index=self.date_index, data=self.columns)
        data_frame.index.name = 'Date'
        return data_frame

    def __len__(self):
        return len(self.date_index)

    def tick_bars(self):
        for i, date in enumerate(self.date_index):
            yield TickBar(self.symbol, date,
                          d(self.columns['Open'][i]),
                          d(self.columns['High'][i]),
                          d(self.columns['Low'][i]),
                          d(self.columns['Close'][i]),
                          d(self.columns['Ref Price'][i]),
                          self.columns['Volume'][i])

    def condense(self, factor) -> 'SymbolData':
        cur_ticks = len(self.date_index)
        new_ticks = (cur_ticks // factor) + 1  # Floor division + 2
        date_index = []
        columns = {label: [] for label in self.columns}
        for tick in range(new_ticks):
            start = tick * factor
            if start == cur_ticks:
                break
            end = min(start + factor, cur_ticks)  # Exclusive
            s = slice(start, end)
            print(s)
            date_index.append(self.date_index[end - 1])
            columns['Open'].append(self.columns['Open'][s][0])
            columns['Close'].append(self.columns['Close'][s][-1])
            columns['Low'].append(min(self.columns['Low'][s]))
            columns['High'].append(max(self.columns['High'][s]))
            columns['Ref Price'].append(sum(self.columns['Ref Price'][s])/factor)
            columns['Volume'].append(sum(self.columns['Volume'][s]))

        sd = SymbolData(self.symbol)
        sd.date_index = date_index
        sd.columns = columns
        return sd


class WatchList:
    """
    A dictionary-like object for storing most recent price (bar) data.
    Auto-subscribed to tick bar events
    """
    def __init__(self):
        self.last_price: dict[str, TickBar] = {}
        observe(TickEvent, lambda event: self.__setitem__(event.tick_bar.symbol, event.tick_bar))

    def __setitem__(self, symbol, last_price: TickBar):
        self.last_price[symbol] = last_price

    def __getitem__(self, symbol):
        return self.last_price[symbol]

    def __len__(self):
        return self.last_price.__len__()

    def __contains__(self, item):
        return self.last_price.__contains__(item)

    def items(self):
        return self.last_price.items()

    def last_close(self, symbol):
        return self.last_price[symbol].close

    def symbols(self):
        return self.last_price.keys()

    def add_symbol(self, symbol, price=0):
        price = d(price)
        print(f'ADDING {symbol} AT {price}')
        symbol = symbol.upper()
        if symbol not in self.last_price:
            self.last_price[symbol] = TickBar(symbol, datetime.now(), price, price, price, price, price, 0)
