from enum import Enum
from typing import NamedTuple
from decimal import Decimal
from markets import Bar, DataRequest
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

    def __radd__(self, other: 'Position'):
        if type(other) is int:
            val = other + self.quantity
        elif other.symbol != self.symbol:
            raise ValueError(f'Incompatible positions to add: {other.symbol} {self.symbol}')
        else:
            val = other.quantity * other.direction.value + self.quantity * self.direction.value
        if val < 0:
            direction = Direction.SHORT
            val = abs(val)
        else:
            direction = Direction.LONG
        return Position(self.symbol, direction, val)


class Order:
    def __init__(self, position: Position, status=OrderStatus.UNPOSTED, id=-1, filled_at=Decimal(0), filled_quantity=0):
        self.position = position
        self.status = status
        self.id = id
        self.filled_at = filled_at
        self.filled_quantity = filled_quantity

    def update_status(self, status: OrderStatus, filled_at=None, filled_quantity=None) -> 'Order':
        filled_at = filled_at or self.filled_at
        filled_quantity = filled_quantity or self.filled_quantity
        return Order(self.position, status, self.id, filled_at, filled_quantity)

    def p_or_l(self, current_price):
        if self.status is OrderStatus.UNPOSTED:
            return Decimal(0)
        return Decimal((current_price - self.filled_at) * self.filled_quantity * self.position.direction.value)

    def __str__(self):
        return f'{self.id} {self.position} filled {self.filled_quantity} at {self.filled_at} ({self.status.name})'

    @staticmethod
    def combined_p_or_l(orders: 'list[Order]', current_price: Decimal):
        return sum(order.p_or_l(current_price) for order in orders)


class BrokerListener(ABC):

    @abstractmethod
    def on_bar(self, symbol, bar: Bar):
        """Load in the file for extracting text."""

    @abstractmethod
    def on_order_status(self, order: Order):
        """Load in the file for extracting text."""


class Broker(ABC):

    @property
    @abstractmethod
    def open_orders(self) -> list[Order]:
        """Returns all open orders"""

    @property
    @abstractmethod
    def filled_orders(self) -> list[Order]:
        """Returns all filled orders"""

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
    def listen(self, symbol: str, listener: BrokerListener):
        """Adds the listener to events"""

    @abstractmethod
    def subscribe_real_time(self, symbol):
        """Subscribe to realtime events for the given symbol"""

    @abstractmethod
    def get_history(self, request: DataRequest):  # , start: datetime, end: datetime = None):
        """Get history for the given symbol"""

    @abstractmethod
    def place_order(self, position: Position) -> Order:
        """Places an order to acquire the given position"""

    @abstractmethod
    def current_position(self) -> Position:
        """Computes the current position based on order history"""

    @abstractmethod
    def p_or_l(self):
        """Returns cumulative P or L of filled orders based on fill price and current price"""
