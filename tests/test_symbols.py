from quant.markets import SymbolData, TickBar
from datetime import datetime
from decimal import Decimal


class TestSymbolData:

    def test_symbol(self):
        sd = SymbolData('msft')
        assert sd.symbol == 'MSFT'

    def test_append(self):
        sd = SymbolData('foo')
        sd.append_bar(TickBar('MSFT', datetime.now(), Decimal('1.00'), Decimal('1.90'), Decimal('0.90'), Decimal('1.01'),
                      Decimal('1.00'), 6))
