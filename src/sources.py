from markets import DataRequest, SymbolData, Bar
import pandas_datareader as pdr
from ibkr import InteractiveBroker
from broker import BrokerListener
import time
from datetime import datetime, timedelta
from broker import Order


class YahooData:

    @staticmethod
    def fetch(request: DataRequest):
        df = pdr.get_data_yahoo(request.symbol, start=request.start, end=request.end)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
        return df

    @staticmethod
    def current_price(symbol: str):
        end = datetime.now()
        start = end - timedelta(hours=48)
        df = YahooData.fetch(DataRequest(symbol, start, end))
        return float(df['Close'].iloc[-1])


class IBKRData:

    @staticmethod
    def fetch(request: DataRequest):
        broker = InteractiveBroker()
        broker.start()
        data = SymbolData(request.symbol)

        class Listener(BrokerListener):
            def on_order_status(self, order: Order):
                pass

            def on_bar(self, symbol, bar: Bar):
                data.append_bar(bar)

        broker.listen(request.symbol, Listener())
        broker.get_history(request)

        while len(data) < request.size_in_days():
            time.sleep(.1)
        broker.shutdown()
        return data.data_frame
