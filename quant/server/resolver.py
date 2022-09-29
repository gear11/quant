from ariadne import QueryType, SubscriptionType, MutationType
import random
import asyncio
from queue import Queue, Empty

from ..service.watchlist import WatchListService
from ..service.symbol_search import SymbolSearchService
from ..markets import TickEvent
from ..util.events import observe
import logging
from ariadne import make_executable_schema, load_schema_from_path


_log = logging.getLogger(__name__)
_symbols = ('MSFT', 'AAPL', 'IBKR', 'TSLA', 'INTU', 'IBM', 'SWIR')


class Resolver:

    def __init__(self, watchlist_service: WatchListService, symbol_search_service: SymbolSearchService):
        self.watchlist_service = watchlist_service
        self.watchlist = watchlist_service.watchlist
        self.symbol_search_service = symbol_search_service
        query = QueryType()
        query.set_field('listSymbols', Resolver._list_symbols)
        query.set_field('searchSymbols', self._search_symbols)
        query.set_field('getWatchList', self.get_watchlist)
        mutation = MutationType()
        mutation.set_field('addSymbol', self.add_symbol)
        mutation.set_field('removeSymbol', self.remove_symbol)
        subscription = SubscriptionType()
        subscription.set_source('counter', Resolver._counter_source)
        subscription.set_field('counter', Resolver._counter)
        subscription.set_source('tickBars', Resolver._tick_bar_source)
        subscription.set_field('tickBars', Resolver._tick_bar)

        type_defs = load_schema_from_path('graphql/schema.graphql')
        self.schema = make_executable_schema(type_defs, query, subscription, mutation)

    def _search_symbols(self, *_, query=None):
        result, error = None, None
        try:
            result = self.symbol_search_service.search_symbols(query)
        except Exception as e:
            error = e
        _log.warning(result)
        return Resolver._payload('symbols', result, error)

    @staticmethod
    def _payload(result_name, result, error):
        if result is not None:
            return {
                "success": True,
                result_name: result
            }
        _log.warning(f'Error producing {result_name}: {error}')
        return {
            "success": False,
            "errors": [str(error)]
        }

    @staticmethod
    def _list_symbols(*_):
        count = random.randint(0, len(_symbols))
        cur_symbols = random.sample(_symbols, count)
        try:
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
    def get_watchlist(self, *_):
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
    def _counter(count, _):
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
    def _tick_bar(tick_bar, _):
        print('Getting tick bars')
        print(f'{tick_bar}')
        return tick_bar

    def add_symbol(self, _, __, symbol):
        _log.warning(f'Adding symbol {symbol}')
        self.watchlist.add_symbol(symbol)
        self.watchlist_service.save(self.watchlist)
        return self._watchlist_payload()

    def remove_symbol(self, _, __, symbol):
        _log.warning(f'Removing symbol {symbol}')
        self.watchlist.remove_symbol(symbol)
        self.watchlist_service.save(self.watchlist)
        return self._watchlist_payload()
