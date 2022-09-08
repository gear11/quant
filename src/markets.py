from __future__ import annotations

import pandas as pd
from decimal import Decimal
from typing import NamedTuple
from datetime import datetime
from enum import Enum
import dateparser
from util.events import Event, observe


class Resolution(Enum):
    DAY = 1
    MINUTE = 2
    TICK = 3
    VOLUME_BAR = 4
    DOLLAR_BAR = 5


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


def is_crypto(symbol):
    return symbol.upper() in ('BTC', 'ETH')


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


class TickEvent(Event):
    def __init__(self, tick_bar: TickBar):
        self.tick_bar = tick_bar


class SymbolData:

    labels = ['Open', 'High', 'Low', 'Close', 'Volume', 'Ref Price']

    def __init__(self, symbol: str, data=None):
        self.symbol = symbol.upper()
        if data:
            self.date_index = data['Date']
            self.columns = {k: v for (k, v) in data.items() if k != 'Date'}
        else:
            self.date_index = []
            self.columns = {label: [] for label in SymbolData.labels}

    def append_bar(self, bar: TickBar):
        self.date_index.append(bar.date)
        self.columns['Open'].append(bar.open)
        self.columns['High'].append(bar.high)
        self.columns['Low'].append(bar.low)
        self.columns['Close'].append(bar.close)
        self.columns['Volume'].append(bar.volume)
        self.columns['Ref Price'].append(bar.wap)

    @property
    def data_frame(self):
        return pd.DataFrame(index=self.date_index, data=self.columns)

    def __len__(self):
        return len(self.date_index)


def decimal(num) -> Decimal | None:
    return Decimal('%.2f' % num) if num is not None else None


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
        price = decimal(price)
        print(f'ADDING {symbol} AT {price}')
        symbol = symbol.upper()
        if symbol not in self.last_price:
            self.last_price[symbol] = TickBar(symbol, datetime.now(), price, price, price, price, price, 0)
