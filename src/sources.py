from markets import DataRequest, SymbolData, TickEvent, TickBar, decimal as d, WatchList
import pandas_datareader as pdr
from ibkr import InteractiveBroker, IBApi
import time
from datetime import datetime, timedelta
from util import events
import random
import threading
import console


class YahooData:

    @staticmethod
    def fetch(request: DataRequest):
        df = pdr.get_data_yahoo(request.symbol, start=request.start, end=request.end)
        df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
        return df

    @staticmethod
    def current_price(symbol: str):
        end = datetime.now()
        start = end - timedelta(days=4)  # Handle long weekend
        df = YahooData.fetch(DataRequest(symbol, start, end))
        return float(df['Close'].iloc[-1])


class IBKRData:

    @staticmethod
    def fetch(request: DataRequest):

        data = SymbolData(request.symbol)
        events.observe(TickEvent, lambda event: data.append_bar(event.tick_bar))

        broker = InteractiveBroker(WatchList())
        broker.start()
        broker.get_history(request)

        while len(data) < request.size_in_days():
            time.sleep(.1)
        broker.shutdown()
        return data.data_frame


class RandomMarketData:

    def __init__(self, watchlist: WatchList, tick_interval=5):
        self.tick_interval = tick_interval
        self.watchlist = watchlist

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
                next_bar = self.next_bar(symbol, tick_bar.close)
                events.emit(TickEvent(next_bar))
                self.watchlist[symbol] = next_bar
            time.sleep(self.tick_interval)

    def start(self):
        console.announce('Starting Random Market Data Thread')
        threading.Thread(target=self.run, daemon=True).start()


class IBKRMarketData:

    def __init__(self, watchlist: WatchList):
        self.watchlist = watchlist
        self.subscribed = set()

    def run(self):
        while True:
            for symbol in self.watchlist.symbols():
                if symbol not in self.subscribed:
                    IBApi.instance().subscribe_realtime(symbol)
                    self.subscribed.add(symbol)
            time.sleep(1)

    def start(self):
        console.announce('Starting IBKR Market Data Thread')
        IBApi.instance().start()
        threading.Thread(target=self.run, daemon=True).start()
