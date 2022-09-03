from enum import Enum
from typing import NamedTuple
from decimal import Decimal
from markets import Bar


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

    def on_bar(self, symbol, bar: Bar):
        """Load in the file for extracting text."""
        pass
