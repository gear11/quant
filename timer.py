import time


class Timer:

    DEFAULT_MESSAGE = 'T({0}) {1:.3f}s step ({2:.3f}s total)'
    instances = 0

    def __init__(self, name=None):
        Timer.instances += 1
        self.name = name if name else Timer.instances
        self.base = time.perf_counter()
        self.t = [0.0]

    def __call__(self, *args, **kwargs):
        total = time.perf_counter() - self.base
        self.t.append(total)
        delta = total - self.t[-2]

        if args and type(args[0]) is str:
            message = args[0] if len(args[0]) else Timer.DEFAULT_MESSAGE
            print(message.format(self.name, delta, total))
        return self.t[-1] - self.t[-2]

    def __getitem__(self, item):
        return self.t.__getitem__(item)

    def diff_last(self):
        return self.t[-1] - self.t[-2]


def main():
    t = Timer('foo')

    t()
    time.sleep(1)
    print(t(''))
    time.sleep(2)
    print(t(''))

    t = Timer()

    t()
    time.sleep(1)
    print(t(''))
    time.sleep(2)
    print(t(''))


if __name__ == "__main__":
    main()
