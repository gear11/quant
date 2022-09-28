from sqlite3 import Connection
import sqlite3 as sl
from ..markets import SymbolInfo
from ..util import Parser, Timer
import logging

_log = logging.getLogger(__name__)


class SymbolSearchService:
    def __init__(self, con: Connection):
        self.con = con

    def search_symbols(self, query: str) -> [SymbolInfo]:
        _log.warning(f'Searching on {query}')
        if len(query) < 2:
            raise ValueError(f'Query string must have length > 2: "{query}"')
        qarg = f'%{query}%'
        cursor = self.con.execute(
            "SELECT * FROM symbols WHERE (symbol LIKE ? OR shortName LIKE ?) AND symbol NOT LIKE '%.%' "
            "ORDER BY rank DESC LIMIT 10", [qarg, qarg])
        _log.info('Here')
        return [self._from_dict(dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def _from_dict(d: dict) -> SymbolInfo:
        _log.warning(f'{d}')
        return SymbolInfo(symbol=d['symbol'], company_name=d['shortName'], industry=d['industryName'],
                          exchange=d['exchange'], rank=d['rank'], type=d['quoteType'])


def main():
    args = Parser().allow_additional_args().parse_args()
    con: Connection = sl.connect(args.additional[0])
    con.row_factory = sl.Row
    service = SymbolSearchService(con)
    with Timer():
        print(service.search_symbols('GOO'))
