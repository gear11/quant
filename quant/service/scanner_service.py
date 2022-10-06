from ..markets import WatchList
from ..sql.types import watchlist_load, watchlist_save
import logging
from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)


class WatchListService:
    def __init__(self, session: Session):
        self._session = session
        self._watchlist = None

    @property
    def watchlist(self) -> WatchList:
        if not self._watchlist:
            self._load()
        return self._watchlist

    def _load(self):
        self._watchlist = watchlist_load(self._session)
        _log.info(f'Loaded watchlist {self._watchlist}')
        return self._watchlist

    def save(self, watchlist: WatchList):
        if self._watchlist is None:
            self._watchlist = watchlist
        elif watchlist is not self._watchlist:
            self._watchlist.items = watchlist.items
        _log.info(f'Saving watchlist {watchlist}')
        watchlist_save(self._session, watchlist)
