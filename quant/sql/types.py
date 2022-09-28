from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from ..markets import WatchList

_log = logging.getLogger(__name__)
Base = declarative_base()
session = None


def get_engine():
    return create_engine("sqlite:///sqlite/scanner/scanner.db", echo=_log.level == logging.DEBUG, future=True)


def get_session():
    global session
    if session is None:
        engine = get_engine()
        session = sessionmaker(bind=engine, future=True)()
    return session


def watchlist_load() -> WatchList:
    items = get_session().query(WatchListItem).all()
    watchlist = WatchList()
    for item in items:
        watchlist.add_symbol(item.symbol, 0)
    return watchlist


def watchlist_save(watchlist: WatchList):
    get_session().query(WatchListItem).delete()
    get_session().add_all([WatchListItem(symbol=symbol) for symbol in watchlist.symbols()])
    get_session().commit()


# See: https://docs.sqlalchemy.org/en/14/orm/quickstart.html
class WatchListItem(Base):
    __tablename__ = 'watchlist'

    symbol = Column(String, primary_key=True)


def main():
    Base.metadata.create_all(get_engine())


if __name__ == '__main__':
    main()
