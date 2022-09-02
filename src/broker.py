from enum import Enum
from typing import NamedTuple
from decimal import Decimal


class Direction(Enum):
    LONG = 1
    SHORT = -1


class Position(NamedTuple):
    symbol: str
    direction: Direction
    quantity: int


class ExecutedOrder(NamedTuple):
    position: Position
    filled_at: Decimal


class BrokerListener:

    def on_bar(self, symbol, date, open_, high, low, close, volume, wap, count):
        """Load in the file for extracting text."""
        pass
