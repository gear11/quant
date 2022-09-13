from typing import Callable


class Bidict:
    """A bi-directional dictionary"""

    def __init__(self):
        self.dict = {}
        self.reverse = {}

    def __setitem__(self, key, value):
        self.dict.__setitem__(key, value)
        self.reverse.__setitem__(value, key)

    def __getitem__(self, item):
        return self.dict.__getitem__(item)

    def __contains__(self, item):
        return self.dict.__contains__(item)


class Accumulator:
    """Accumulates results from a callback"""

    def __init__(self, on_complete: Callable):
        self.on_complete = on_complete
