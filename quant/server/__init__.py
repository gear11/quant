from sqlite3 import Connection

import uvicorn
from ariadne.asgi.handlers import GraphQLWSHandler, GraphQLHTTPHandler
# from ariadne.asgi.handlers import GraphQLTransportWSHandler
from ariadne.asgi import GraphQL
import logging
import sqlite3 as sl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..service.watchlist import WatchListService
from ..service.symbol_search import SymbolSearchService
from .resolver import Resolver
from ..util import Parser, events
from ..markets import TickEvent
from ..sources import init_market_data

_log = logging.getLogger(__name__)


def run_server(res, listen_port):
    app = GraphQL(res.schema,
                  http_handler=GraphQLHTTPHandler(),
                  websocket_handler=GraphQLWSHandler(keepalive=5),
                  debug=True)
    config = uvicorn.Config(app, port=listen_port, log_level='info', workers=4, ws_ping_interval=3, timeout_keep_alive=60)
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
    search_service = SymbolSearchService(con)

    engine = create_engine("sqlite:///sqlite/scanner/scanner.db", echo=_log.level == logging.DEBUG, future=True)
    session = sessionmaker(bind=engine, future=True)()
    watchlist_service = WatchListService(session)

    init_market_data(args.source, watchlist_service)
    events.observe(TickEvent, _log.info)

    res = Resolver(watchlist_service, search_service)
    run_server(res, 5000)


if __name__ == "__main__":
    main()
