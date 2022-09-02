from __future__ import annotations

from typing import NamedTuple
from datetime import datetime
from enum import Enum
import dateparser


class Resolution(Enum):
    DAY = 1
    MINUTE = 2
    TICK = 3
    VOLUME_BAR = 4
    DOLLAR_BAR = 5


class Request(NamedTuple):
    start: datetime
    end: datetime
    symbols: list[str]
    resolution: Resolution = Resolution.DAY

    @classmethod
    def make(cls, start: datetime | str, end: datetime | str, symbols: list | str, res=Resolution.DAY) -> Request:
        start = start if type(start) is datetime else dateparser.parse(start)
        end = end if type(end) is datetime else dateparser.parse(end)
        symbols = symbols if type(symbols) is list else [symbols]
        return Request(start, end, symbols, res)
