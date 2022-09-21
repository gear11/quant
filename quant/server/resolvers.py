from ariadne import QueryType, SubscriptionType
import random
import asyncio
from queue import Queue, Empty
from ..markets import TickEvent
from ..util.events import observe
import logging

log = logging.getLogger(__name__)


query = QueryType()
subscription = SubscriptionType()
symbols = ('MSFT', 'AAPL', 'IBKR', 'TSLA', 'INTU', 'IBM', 'SWIR')


@query.field('listSymbols')
def list_symbols_resolver(*_):
    count = random.randint(0, len(symbols))
    cur_symbols = random.sample(symbols, count)
    try:
        print(cur_symbols)
        payload = {
            "success": True,
            "symbols": [{'name': s} for s in cur_symbols]
        }
    except Exception as error:
        payload = {
            "success": False,
            "errors": [str(error)]
        }
    return payload


"""
watchlist = [
    {
        'symbol': symbols[0],
        'time': '2022-09-08 09:30:10',
        'open': 256.21,
        'high': 256.65,
        'low': 256.45,
        'close': 256.34,
        'wap': 256.22,
        'volume': 69
    }
]
"""
watchlist = None


def set_watchlist(new_watchlist):
    global watchlist
    watchlist = new_watchlist


@query.field('getWatchList')
def get_watchlist_resolver(*_):
    try:
        payload = {
            "success": True,
            "items": [tick_bar.to_gql() for _, tick_bar in watchlist.items()]
        }
    except Exception as error:
        print(error)
        payload = {
            "success": False,
            "errors": [str(error)]
        }
    log.debug(f'{payload}')
    return payload


@subscription.source("counter")
async def counter_generator(*_):
    i = 0
    while True:
        i += 1
        await asyncio.sleep(1)
        yield {'success': True, 'count': i}


@subscription.field("counter")
def counter_resolver(count, _):
    print(f'{count}')
    return count


@subscription.source("tickBars")
async def tick_bar_generator(*_):
    print('New tick bar generator')
    queue = Queue()

    def on_event(e):
        queue.put(e)

    observe(TickEvent, lambda e: queue.put(e), weak=True)
    while True:
        try:
            event = queue.get(block=False)
            yield {'success': True, 'tick_bar': event.tick_bar}
        except Empty:
            await asyncio.sleep(1)


@subscription.field("tickBars")
def tick_bar_resolver(tick_bar, _):
    print('Getting tick bars')
    print(f'{tick_bar}')
    return tick_bar
