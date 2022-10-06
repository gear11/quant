

class ScannerSymbol:
    def __init__(self, symbol):
        self.symbol = symbol
        self.float = 0
        self.avg_daily_vol = 0
        self.last_close = 0


class ScannerData:
    def __init__(self, symbol: ScannerSymbol):
        self.symbol = symbol
        self.recent_price = []
        self.recent_volume = []
        self.recent_volatility = []


class Scanner:

    def __init__(self):
        pass
