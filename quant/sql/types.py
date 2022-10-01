from sqlalchemy.exc import OperationalError

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy.orm import declarative_base

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import logging
from ..markets import WatchList

_log = logging.getLogger(__name__)
Base = declarative_base()


def watchlist_load(session: Session) -> WatchList:
    items = session.query(WatchListItem).all()
    watchlist = WatchList()
    for item in items:
        watchlist.add_symbol(item.symbol, 0)
    return watchlist


def watchlist_save(session: Session, watchlist: WatchList):
    try:
        session.query(WatchListItem).delete()
    except OperationalError:
        pass
    session.add_all([WatchListItem(symbol=symbol) for symbol in watchlist.symbols()])
    session.commit()


# See: https://docs.sqlalchemy.org/en/14/orm/quickstart.html
class WatchListItem(Base):
    __tablename__ = 'watchlist'

    symbol = Column(String, primary_key=True)


def main():
    engine = create_engine("sqlite:///sqlite/scanner/scanner.db", echo=_log.level == logging.DEBUG, future=True)
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    main()
