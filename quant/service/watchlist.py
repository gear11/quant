from ..util import Parser
from ..markets import WatchList
from ..sql.types import watchlist_load, watchlist_save
import logging

_log = logging.getLogger(__name__)


class WatchListService:
    def __init__(self):
        self._watchlist = None
        pass

    @property
    def watchlist(self) -> WatchList:
        if not self._watchlist:
            self._load()
        return self._watchlist

    def _load(self):
        self._watchlist = watchlist_load()
        _log.info(f'Loaded watchlist {self._watchlist}')
        return self._watchlist

    def save(self, watchlist: WatchList):
        if watchlist is not self._watchlist:
            self._watchlist.items = watchlist.items
        _log.info(f'Saving watchlist {watchlist}')
        watchlist_save(watchlist)


def store_and_retrieve(symbols):
    watchlist = WatchList(symbols)
    WatchListService().save(watchlist)

    retrieved = WatchListService().watchlist
    assert watchlist == retrieved
    return watchlist


if __name__ == '__main__':
    parser = Parser()
    parser.add_argument('symbols', nargs='+', help='symbols')
    args = parser.parse_args()
    w = store_and_retrieve(args.symbols)
    print(w)
