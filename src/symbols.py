import pandas as pd
from datetime import datetime


def is_crypto(symbol):
    return symbol.upper() in ('BTC', 'ETH')


def is_forex(symbol):
    return symbol.upper() in ('EUR', 'BTC')


class SymbolData:
    def __init__(self, symbol: str, data=None):
        self.symbol = symbol.upper()
        if data:
            self.date_index = data['Date']
            self.columns = {k: v for (k, v) in data.items() if k != 'Date'}
        else:
            self.date_index = []
            self.columns = {'Open': [], 'High': [], 'Low': [], 'Close': [], 'Volume': []}

    def append_bar(self, date, open_, high, low, close, volume):
        date = datetime.utcfromtimestamp(date) if type(date) is int else date
        self.date_index.append(date)
        self.columns['Open'].append(open_)
        self.columns['High'].append(high)
        self.columns['Low'].append(low)
        self.columns['Close'].append(close)
        self.columns['Volume'].append(volume)

    @property
    def data(self):
        return pd.DataFrame(index=self.date_index, data=self.columns)


