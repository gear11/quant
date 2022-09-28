from sqlite3 import Connection

import uvicorn
from ariadne.asgi.handlers import GraphQLWSHandler
# from ariadne.asgi.handlers import GraphQLTransportWSHandler
from ariadne.asgi import GraphQL
import logging
import sqlite3 as sl

from ..service.watchlist import WatchListService
from ..service.symbol_search import SymbolSearchService
from .resolver import Resolver
from ..util import Parser, events
from ..markets import TickEvent
from ..sources import init_market_data

_log = logging.getLogger(__name__)


def run_server(res, listen_port):
    app = GraphQL(res.schema,
                  websocket_handler=GraphQLWSHandler(),
                  debug=True)
    config = uvicorn.Config(app, port=listen_port, log_level='info', workers=4)
    server = uvicorn.Server(config)
    server.run()


def main():
    parser = Parser()
    parser.add_argument('-s', dest='source', type=str,
                        help='Source of market data: "live", "random" or a date for example "2022-09-08 10:00:00"',
                        default='live')
    args = parser.parse_args()

    con: Connection = sl.connect('sqlite/lookup/symbols.db')
    con.row_factory = sl.Row

    watchlist_service = WatchListService()
    init_market_data(args.source, watchlist_service.load())
    events.observe(TickEvent, _log.info)

    res = Resolver(watchlist_service, SymbolSearchService(con))
    run_server(res, 5000)


if __name__ == "__main__":
    main()
