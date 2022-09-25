from ariadne import QueryType, SubscriptionType, MutationType
import random
import asyncio
from queue import Queue, Empty
from ..markets import TickEvent, WatchList
from ..util.events import observe
import logging
from ariadne import make_executable_schema, load_schema_from_path


_log = logging.getLogger(__name__)
_symbols = ('MSFT', 'AAPL', 'IBKR', 'TSLA', 'INTU', 'IBM', 'SWIR')


class Resolver:

    def __init__(self, watchlist: WatchList):
        self.watchlist = watchlist
        query = QueryType()
        query.set_field('listSymbols', Resolver._list_symbols_resolver)
        query.set_field('getWatchList', self.get_watchlist_resolver)
        mutation = MutationType()
        mutation.set_field('addSymbol', self.add_symbol)
        mutation.set_field('removeSymbol', self.remove_symbol)
        subscription = SubscriptionType()
        subscription.set_source('counter', Resolver._counter_source)
        subscription.set_field('counter', Resolver._counter_resolver)
        subscription.set_source('tickBars', Resolver._tick_bar_source)
        subscription.set_field('tickBars', Resolver._tick_bar_resolver)

        type_defs = load_schema_from_path('graphql/schema.graphql')
        self.schema = make_executable_schema(type_defs, query, subscription, mutation)

    @staticmethod
    def _list_symbols_resolver(*_):
        count = random.randint(0, len(_symbols))
        cur_symbols = random.sample(_symbols, count)
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
    def get_watchlist_resolver(self, *_):
        return self._watchlist_payload()

    def _watchlist_payload(self, error=None):
        if error:
            _log.error(error)
            return {
                "success": False,
                "errors": [str(error)]
            }
        payload = {
                "success": True,
                "items": [tick_bar.to_gql() for _, tick_bar in self.watchlist.items()]
            }
        _log.info(f'Watchlist {payload}')
        return payload

    @staticmethod
    async def _counter_source(*_):
        i = 0
        while True:
            i += 1
            await asyncio.sleep(1)
            yield {'success': True, 'count': i}

    @staticmethod
    def _counter_resolver(count, _):
        _log.debug(f'{count}')
        return count

    @staticmethod
    async def _tick_bar_source(*_):
        _log.info('New tick bar generator')
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

    @staticmethod
    def _tick_bar_resolver(tick_bar, _):
        print('Getting tick bars')
        print(f'{tick_bar}')
        return tick_bar

    def add_symbol(self, _, __, symbol):
        _log.warning(f'Adding ${symbol}')
        self.watchlist.add_symbol(symbol)
        return self._watchlist_payload()

    def remove_symbol(self, _, __, symbol):
        _log.warning(f'Removing ${symbol}')
        self.watchlist.remove_symbol(symbol)
        return self._watchlist_payload()
