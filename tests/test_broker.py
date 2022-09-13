from quant.broker import Position, Direction, Order, OrderStatus
from decimal import Decimal


class TestBroker:

    def test_order(self):
        position = Position('AAPL', Direction.LONG, 100)
        order = Order(position, 999)
        new_order = order.update_status(OrderStatus.SUBMITTED, Decimal('99.95'), 99)

        assert new_order.position is position
        assert new_order.status is OrderStatus.SUBMITTED
        assert new_order.filled_at == Decimal('99.95')

    def test_position(self):
        position = Position('AAPL', Direction.LONG, 100)
        reverse = position.reverse()

        assert position.symbol == reverse.symbol

    def test_p_or_l(self):
        quantity = 100
        filled_at = Decimal('159.78')
        position = Position('AAPL', Direction.LONG, quantity)
        order = Order(position, OrderStatus.FILLED, -1, filled_at, quantity)

        current_price = Decimal('187.34')
        profit = (current_price - filled_at) * quantity

        assert order.p_or_l(current_price) == profit, 'Profit of order does not match current price'
