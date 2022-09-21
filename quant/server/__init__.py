from ariadne import make_executable_schema, load_schema_from_path
# from ariadne.asgi.handlers import GraphQLTransportWSHandler
from ariadne.asgi.handlers import GraphQLWSHandler
from ariadne.asgi import GraphQL
from .resolvers import query, subscription, set_watchlist
from ..markets import WatchList, TickEvent
from ..sources import IBKRMarketData
from ..util.events import observe
# from ..util import Parser
import logging

log = logging.getLogger(__name__)

# logging.basicConfig()


# Parser().ignore_args().parse_args()

type_defs = load_schema_from_path('graphql/schema.graphql')
schema = make_executable_schema(type_defs, query, subscription)
app = GraphQL(schema,
              websocket_handler=GraphQLWSHandler(keepalive=15),
              debug=True)


watchlist = WatchList()
watchlist.add_symbol('MSFT', 0)
# watchlist.add_symbol('INTU', 0)
IBKRMarketData(watchlist).start()
set_watchlist(watchlist)


def on_event(e):
    log.warning(e)


observe(TickEvent, log.warning, weak=True)
