from quant.markets import WatchList
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from quant.service.watchlist import WatchListService
import pytest
import os
from quant.sql.types import Base


class TestWatchListService:

    @pytest.fixture
    def session(self):
        engine = create_engine("sqlite:///test.db", echo=False, future=True)
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine, future=True)()
        engine.dispose()
        os.remove('test.db')

    def test_load_and_save(self, session):
        symbols = ['ABC', 'DEF', 'GHI']
        watchlist = WatchList(symbols)
        WatchListService(session).save(watchlist)

        retrieved = WatchListService(session).watchlist
        assert watchlist == retrieved
