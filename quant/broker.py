from .markets import WatchList
from .util.events import Event

from enum import Enum
from typing import NamedTuple
from decimal import Decimal
from abc import abstractmethod, ABC


class Direction(Enum):
    LONG = 1
    SHORT = -1


class OrderStatus(Enum):
    UNPOSTED = 0
    PENDING = 1
    SUBMITTED = 2
    PARTIALLY_FILLED = 3
    FILLED = 4
    CANCELLED = 5
    UNKNOWN = -1


class Position(NamedTuple):
    symbol: str
    direction: Direction
    quantity: int

    def reverse(self):
        direction = Direction.LONG if self.direction is Direction.SHORT else Direction.SHORT
        return Position(symbol=self.symbol, quantity=self.quantity, direction=direction)

    def __str__(self):
        return f'{self.symbol} {self.direction.name} {self.quantity}'

    def __add__(self, other: 'Position | int'):
        if type(other) is int:
            val = self.quantity + other
        elif other.symbol != self.symbol:
            raise ValueError(f'Incompatible positions to add: {other.symbol} {self.symbol}')
        else:
            val = other.quantity * other.direction.value + self.quantity * self.direction.value # noqa PyCharm can't do Enum.value
        if val < 0:
            direction = Direction.SHORT
            val = abs(val)
        else:
            direction = Direction.LONG
        return Position(self.symbol, direction, val)

    def __radd__(self, other: 'Position'):
        return self.__add__(other)


class Order:
    def __init__(self, position: Position, status=OrderStatus.UNPOSTED, order_id=-1, filled_at=Decimal(0),
                 filled_quantity=0):
        self.position = position
        self.status = status
        self.order_id = order_id
        self.filled_at = filled_at
        self.filled_quantity = filled_quantity

    def is_cancellable(self):
        return self.status in (OrderStatus.UNPOSTED, OrderStatus.PENDING)

    def update_status(self, status: OrderStatus, filled_at: Decimal = None, filled_quantity=None) -> 'Order':
        filled_at = filled_at or self.filled_at
        filled_quantity = filled_quantity or self.filled_quantity
        return Order(self.position, status, self.order_id, filled_at, filled_quantity)

    def p_or_l(self, current_price: Decimal):
        if self.status is OrderStatus.UNPOSTED:
            return Decimal(0)
        return Decimal((current_price - self.filled_at) * Decimal(self.filled_quantity) * self.position.direction.value) # noqa PyCharm can't do Enum.value

    def __str__(self):
        msg = f'{self.order_id} {self.position} {self.status.name}'
        if self.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            msg += f' {self.filled_quantity} at {self.filled_at}'
        return msg

    @staticmethod
    def combined_p_or_l(orders: 'list[Order]', current_price: Decimal):
        return sum(order.p_or_l(current_price) for order in orders)


class OrderBook:
    """Collects orders into a list-like class with aggregation operations"""
    def __init__(self):
        self.orders: list[Order] = []
        self.orders_by_id = {}

    def __getitem__(self, item):
        return self.orders.__getitem__(item)

    def __setitem__(self, index: int, order: Order):
        self.orders[index] = order
        self.orders_by_id[order.order_id] = (order, index)

    def __len__(self):
        return len(self.orders)

    def append(self, order: Order):
        self.orders.append(order)
        self.orders_by_id[order.order_id] = (order, len(self.orders) - 1)

    @property
    def open_orders(self) -> list[Order]:
        return [order for order in self.orders if order.status in (OrderStatus.SUBMITTED, OrderStatus.PENDING)]

    @property
    def filled_orders(self) -> list[Order]:
        return [order for order in self.orders if order.status is OrderStatus.FILLED]

    def orders_for(self, symbol):
        return [order for order in self.orders if order.position.symbol == symbol]

    def p_or_l(self, symbol, current_price):
        return sum(order.p_or_l(current_price) for order in self.orders_for(symbol)
                   if order.status is OrderStatus.FILLED)

    def current_position(self, symbol) -> Position:
        return sum(order.position for order in self.orders_for(symbol) if order.status is OrderStatus.FILLED)

    def by_order_id(self, order_id) -> (Order, int):
        return self.orders_by_id[order_id]


class OrderEvent(Event):

    def __init__(self, order: Order):
        self.order = order


class Broker(ABC):

    def __init__(self, watchlist: WatchList):
        self.book = OrderBook()
        self.watchlist = watchlist

    def current_positions(self) -> list[Position]:
        return [self.book.current_position(symbol) for symbol in self.watchlist.symbols()]

    @property
    def open_orders(self) -> list[Order]:
        return self.book.open_orders

    @property
    def filled_orders(self) -> list[Order]:
        return self.book.filled_orders

    def p_or_l(self, symbol=None):
        if symbol:
            return self.book.p_or_l(symbol, self.watchlist[symbol].close)
        else:
            return sum(self.book.p_or_l(symbol, bar.close) for symbol, bar in self.watchlist.items())

    @abstractmethod
    def start(self):
        """Starts up the broker"""

    @abstractmethod
    def shutdown(self):
        """Shuts down this broker"""

    @abstractmethod
    def cancel_pending_orders(self):
        """Cancels pending orders"""

    @abstractmethod
    def place_order(self, position: Position) -> Order:
        """Places an order to acquire the given position"""
