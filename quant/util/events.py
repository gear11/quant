from abc import ABC
from collections import defaultdict
from typing import Type
import traceback
import logging
import weakref

log = logging.getLogger(__name__)


class Event(ABC):
    """Base class for all events"""""


observers = defaultdict(list)


def observe(clazz: Type[Event], observer: callable, weak=False):
    log.debug(f'Adding {observer!r} for event type {clazz!r}')
    observers[clazz].append((weak, weakref.ref(observer) if weak else observer))


def emit(event: Event):
    clazz = type(event)
    for (weak, ref) in observers[clazz]:
        if weak:
            observer = ref()
            if observer is None:
                print(f'Observer for {clazz} was GCd')
                stop_observing(clazz, ref)
                continue
            else:
                print(f'Observer for {clazz} WAS NOT GCd')
        else:
            # print(f'Observer for {clazz} is not a weak ref')
            observer = ref

        try:
            if observer(event):
                log.info(f'Removing {observer!r} for event type {clazz!r}')
                stop_observing(clazz, ref)
        except Exception:  # noqa Don't allow bad observers to hang us
            log.warning(f'Error in observer {observer!r}:')
            print(traceback.format_exc())


def stop_observing(clazz: Type[Event], observer_ref):
    """Removes the observer from any of the event types"""
    observers[clazz] = [(w, o) for w, o in observers[clazz] if o != observer_ref]
