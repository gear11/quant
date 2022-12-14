import time
from collections.abc import Iterable
from datetime import datetime, timedelta
import os


class Waiter:

    def __init__(self, max_wait=None):
        self.waiting = True
        self.max_wait = max_wait
        self.start = time.perf_counter()

    def __call__(self, *args, **kwargs):
        self.done()

    def still_waiting(self) -> bool:
        return self.waiting and time.perf_counter() - self.start <= self.max_wait

    def done(self):
        self.waiting = False

    def expired(self):
        return self.waiting and time.perf_counter() - self.start >= self.max_wait


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

    def total(self):
        return time.perf_counter() - self.base

    def step(self, fmt):
        total = self.total()
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


all_trading_days = set()


def is_trading_day(date: datetime):
    if not all_trading_days:
        # python quant/fetch.py yahoo 2015-01-01 2023-09-10 msft -r=d | cut -c 1-10 > quant/util/trading_days.txt
        path = os.path.join(os.path.dirname(__file__), 'trading_days.txt')
        with open(path, 'r') as file:
            all_trading_days.update(file.read().splitlines())
    date_string = date.strftime('%Y-%m-%d')
    return date_string in all_trading_days


def spans_days(start: datetime, end: datetime):
    return start.strftime('%Y-%m-%d') != end.strftime('%Y-%m-%d')


def count_trading_days(start: datetime, end: datetime):
    trading_days = 0
    total_days = 0
    cur = start
    while cur < end:
        if is_trading_day(cur):
            trading_days += 1
        cur = cur + timedelta(days=1)
        total_days += 1
    return total_days, trading_days


def parse_date(date_str: str) -> datetime:
    formats = ['%Y%m%d', '%Y%m%d  %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d  %H:%M:%S']
    for f in formats:
        try:
            date = datetime.strptime(date_str, f)
            date = date.astimezone()
        except ValueError:
            pass
        else:
            return date
    raise ValueError(f'Could not parse {date_str} via any of {formats}')


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
