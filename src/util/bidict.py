class Bidict:

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
