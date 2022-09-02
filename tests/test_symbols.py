from symbols import SymbolData
from datetime import datetime


class TestSymbolData:

    def test_symbol(self):
        sd = SymbolData('msft')
        assert sd.symbol == 'MSFT'

    def test_append(self):
        sd = SymbolData('foo')
        sd.append_bar(datetime.now(), 1, 2, 3, 4, 5)
        print(sd.data)


