from sources import *


class TestSources:

    def test_yahoo_current_price(self):
        price = YahooData.current_price('intu')
        assert type(price) is float
        assert price > 100
        assert price < 1000
