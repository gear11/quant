from ..util import Parser
from ..markets import WatchList
from ..sql.types import watchlist_load, watchlist_save
import logging

_log = logging.getLogger(__name__)


class WatchListService:
    def __init__(self):
        pass

    def load(self) -> WatchList:
        return watchlist_load()

    def save(self, watchlist: WatchList):
        watchlist_save(watchlist)


def store_and_retrieve(symbols):
    watchlist = WatchList(symbols)
    WatchListService().save(watchlist)

    retrieved = WatchListService().load()
    assert watchlist == retrieved
    return watchlist


if __name__ == '__main__':
    parser = Parser()
    parser.add_argument('symbols', nargs='+', help='symbols')
    args = parser.parse_args()
    w = store_and_retrieve(args.symbols)
    print(w)
