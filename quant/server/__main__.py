import uvicorn

from ariadne.asgi.handlers import GraphQLWSHandler
from ariadne.asgi import GraphQL
import logging

from .resolver import Resolver
from ..util import Parser, events
from ..markets import WatchList, TickEvent
from ..sources import init_market_data

_log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = Parser()
    parser.add_argument('-s', dest='source', type=str,
                        help='Source of market data: "live", "random" or a date for example "2022-09-08 10:00:00"',
                        default='live')
    args = parser.parse_args()

    watchlist = WatchList()
    watchlist.add_symbol('MSFT', 0)
    watchlist.add_symbol('INTU', 0)
    init_market_data(args.source, watchlist)
    events.observe(TickEvent, _log.info)

    resolver = Resolver(watchlist)
    app = GraphQL(resolver.schema,
                  websocket_handler=GraphQLWSHandler(),
                  debug=True)
    config = uvicorn.Config(app, port=5000, log_level='debug' if args.debug else 'info')
    server = uvicorn.Server(config)
    server.run()
