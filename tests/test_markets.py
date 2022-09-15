from quant.markets import SymbolData, TickBar
from datetime import datetime


class TestSymbolData:

    def test_condense(self):
        symbol = 'foo'
        sd = SymbolData(symbol)
        sd.append_bar(TickBar.new(symbol, datetime.now(), 100, 110, 90, 100, 100, 4))
        sd.append_bar(TickBar.new(symbol, datetime.now(), 100, 120, 80, 115, 90, 13))
        sdc = sd.condense(2)
        print(sdc)
        print(sdc[0])
        assert len(sdc) == 1
        assert sdc[0].open == 100
        assert sdc[0].high == 120
        assert sdc[0].low == 80
        assert sdc[0].close == 115
        assert sdc[0].wap == 95
        assert sdc[0].volume == 17
