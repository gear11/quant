from abc import ABC
from collections import defaultdict
from typing import Type
import traceback
import logging

log = logging.getLogger(__name__)


class Event(ABC):
    """Base class for all events"""""


observers = defaultdict(list)


def observe(clazz: Type[Event], observer: callable):
    log.info(f'Adding {observer!r} for event type {clazz!r}')
    observers[clazz].append(observer)


def emit(event: Event):
    clazz = type(event)
    for observer in observers[clazz]:
        try:
            if observer(event):
                log.debug(f'Removing {observer!r} for event type {clazz!r}')
                stop_observing(clazz, observer)
        except Exception:  # noqa Don't allow bad observers to hang us
            log.info(f'Error in observer {observer!r}:')
            print(traceback.format_exc())


def stop_observing(clazz: Type[Event], ob):
    """Removes the observer from any of the event types"""
    observers[clazz] = [o for o in observers[clazz] if o != ob]
