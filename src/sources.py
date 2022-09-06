from markets import DataRequest, SymbolData, TickEvent
import pandas_datareader as pdr
from ibkr import InteractiveBroker
import time
from datetime import datetime, timedelta
from util import events


class YahooData:

    @staticmethod
    def fetch(request: DataRequest):
        df = pdr.get_data_yahoo(request.symbol, start=request.start, end=request.end)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
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

        broker = InteractiveBroker()
        broker.start()
        broker.get_history(request)

        while len(data) < request.size_in_days():
            time.sleep(.1)
        broker.shutdown()
        return data.data_frame
