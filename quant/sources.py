from .markets import DataRequest, SymbolData, TickEvent, TickBar, Resolution, WatchList
from .ibkr import BrokerContext, IBApi
from .util import timeutil, diff, events, console
from .util.misc import decimal as d

import pandas_datareader as pdr
import time
from datetime import datetime, timedelta
import random
import threading
import logging

import os
import pandas as pd
from numpy import float64, int64

_log = logging.getLogger(__name__)


def init_market_data(source, watchlist):

    if source == 'random':
        RandomMarketData(watchlist, YahooData.current_price).start()
    elif source == 'live':
        IBKRMarketData(watchlist).start()
    else:
        date = timeutil.parse_date(source)
        IBKRHistoricalMarketData(watchlist, date, 'history').start()


class YahooData:

    intervals = {Resolution.DAY: 'd', Resolution.WEEK: 'w', Resolution.MONTH: 'm'}

    @staticmethod
    def fetch(request: DataRequest):
        if request.resolution not in YahooData.intervals:
            raise ValueError('Only DAY WEEK and MONTH resolutions are supported')
        interval = YahooData.intervals[request.resolution]
        df = pdr.get_data_yahoo(request.symbol, start=request.start, end=request.end, interval=interval)
        df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
        return df

    @staticmethod
    def current_price(symbol: str):
        _log.info(f'Fetching current price of {symbol}')
        end = datetime.now()
        start = end - timedelta(days=4)  # Handle long weekend
        df = YahooData.fetch(DataRequest(symbol, start, end))
        return float(df['Close'].iloc[-1])


class IBKRData:

    @staticmethod
    def fetch_symbol_data(request: DataRequest) -> SymbolData:
        with BrokerContext() as broker:
            symbol_data = broker.req_historical_data(request)
        console.announce(f'Received {len(symbol_data)} tick bars')
        return symbol_data

    @staticmethod
    def fetch(request: DataRequest):
        return IBKRData.fetch_symbol_data(request).data_frame


class IBKRHistoricalMarketData:

    def __init__(self, watchlist: WatchList, start_date: datetime, cache_dir: str = None):
        self.watchlist = watchlist
        if not timeutil.is_trading_day(start_date):
            raise ValueError(f'Date {start_date} is not a trading day. No historical data available')
        self.start_date = start_date
        self.data_cache = DataCache(cache_dir) if cache_dir else None

    def run(self):
        tick_bars = {}
        while True:
            for symbol, tick_bar in self.watchlist.items():
                if symbol not in tick_bars:
                    symbol_data = None
                    if self.data_cache:
                        symbol_data = self.data_cache.load(symbol, self.start_date)
                    if not symbol_data:
                        symbol_data = self.fetch_data(symbol, self.start_date)
                        if self.data_cache:
                            self.data_cache.save(symbol_data)
                    tick_bars[symbol] = (symbol_data, symbol_data.tick_bars())
                try:
                    events.emit(TickEvent((tick_bars[symbol][1]).__next__()))
                except StopIteration:
                    console.warn('Replaying data')
                    tick_bars[symbol] = (tick_bars[symbol][0], tick_bars[symbol][0].tick_bars())

            time.sleep(5)

    @staticmethod
    def fetch_data(symbol, date):
        one_day_later = date + timedelta(days=1)
        request = DataRequest(symbol, date, one_day_later, Resolution.FIVE_SEC)
        return IBKRData.fetch_symbol_data(request)

    def start(self):
        console.announce(f'Starting Historical Market Data Thread at {self.start_date}')
        threading.Thread(target=self.run, daemon=True).start()


class DataCache:

    def __init__(self, cache_dir):
        console.announce(f'Using stored history dir {cache_dir}')
        self.cache_dir = cache_dir

    def load(self, symbol: str, date: datetime) -> SymbolData:
        path = self.path_for(symbol, date)
        if os.path.exists(path):
            data_frame = pd.read_csv(path, dtype={
                'Date': str,
                'Open': float64,
                'High': float64,
                'Low': float64,
                'Close': float64,
                'Ref Price': float64,
                'Volume': int64
            }, parse_dates=['Date'])
            return SymbolData(symbol, data_frame)

    def save(self, data: SymbolData):
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)
        path = self.path_for(data.symbol, data.date_index[0])
        data.data_frame.to_csv(path)

    def path_for(self, symbol, date):
        date_str = date.strftime('%Y-%m-%d')
        filename = f'{date_str}-{symbol}.csv'
        return os.path.join(self.cache_dir, filename)


class RandomMarketData:

    def __init__(self, watchlist, first_open, tick_interval=5):
        self.watchlist = watchlist
        self.first_open = first_open
        self.tick_interval = tick_interval

    @staticmethod
    def next_bar(symbol, prev_close) -> TickBar:
        date = datetime.now()
        price = float(prev_close)
        high = random.uniform(price, price * 1.01)
        low = random.uniform(price * 0.99, price)
        close = random.uniform(low, high)
        volume = int(random.uniform(300, 600))
        wap = close
        return TickBar(symbol, date, prev_close, d(high), d(low), d(close), d(wap), volume)

    def run(self):
        while True:
            for symbol, tick_bar in self.watchlist.items():
                close = tick_bar.close
                if int(tick_bar.close) == 0:
                    _log.info(f'Looking up newly added symbol {symbol}')
                    close = self.first_open(symbol)
                    self.watchlist.add_symbol(symbol, close)
                next_bar = self.next_bar(symbol, close)
                events.emit(TickEvent(next_bar))
                self.watchlist[symbol] = next_bar
            time.sleep(self.tick_interval)

    def start(self):
        console.announce('Starting Random Market Data Thread')
        threading.Thread(target=self.run, daemon=True).start()


class IBKRMarketData:

    def __init__(self, watchlist: WatchList):
        self.watchlist = watchlist

    def run(self):
        while True:
            added, removed = diff(IBApi.instance().subscriptions.keys(), self.watchlist.symbols())
            for symbol in added:
                IBApi.instance().subscribe_realtime(symbol)
            for symbol in removed:
                IBApi.instance().unsubscribe_realtime(symbol)
            time.sleep(1)

    def start(self):
        console.announce('Starting IBKR Market Data Thread')
        IBApi.instance().start()
        threading.Thread(target=self.run, daemon=True).start()
