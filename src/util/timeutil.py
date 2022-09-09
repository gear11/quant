import time
from collections.abc import Iterable


class Waiter:

    def __init__(self, max_wait=None):
        self.waiting = True
        self.max_wait = max_wait
        self.start = time.perf_counter()

    def __call__(self, *args, **kwargs):
        self.waiting = False

    def still_waiting(self):
        return self.waiting or time.perf_counter() - self.start >= self.max_wait


class Timer:

    DEFAULT_MESSAGE = 'Timer({0}) {1:.3f}s step ({2:.3f}s total)'
    instances = 0

    def __init__(self, name=None):
        Timer.instances += 1
        self.name = name if name else Timer.instances
        self.base = time.perf_counter()
        self.t = [0.0]

    def __call__(self, *args, **kwargs):
        return self.step(args[0])

    def __getitem__(self, item):
        return self.t.__getitem__(item)

    def step(self, fmt):
        total = time.perf_counter() - self.base
        self.t.append(total)
        delta = total - self.t[-2]

        if type(fmt) is str:
            message = fmt if len(fmt) else Timer.DEFAULT_MESSAGE
            print(message.format(self.name, delta, total))
        return self.t[-1] - self.t[-2]

    def diff_last(self):
        return self.t[-1] - self.t[-2]

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.step('Timer({0}) took {1:.3f}s')


def timed_release(iterable: Iterable, delay: float):
    for item in iterable:
        yield item
        time.sleep(delay)


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
