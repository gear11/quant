from broker import *



class TestBroker:


    def test_order(self):
        position = Position('AAPL', Direction.LONG, 100)
        order = Order(position, 999)
        new_order = order.update_status(OrderStatus.SUBMITTED, Decimal(99.95), 99)

    def test_position(self):
        position = Position('AAPL', Direction.LONG, 100)
        reversed = position.reverse()

        assert position.symbol == reversed.symbol




