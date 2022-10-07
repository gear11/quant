import time
import logging
from typing import Callable
from .timeutil import Waiter

_log = logging.getLogger(__name__)


class CallChannels:

    def __init__(self, base_req_id=1000):
        self._channels = {}
        self._next_req_id = base_req_id

    def channel_for(self, key, metadata=None, result=None) -> 'CallChannel':
        if key not in self._channels:
            self._channels[key] = CallChannel(self, key, metadata, result)
        return self._channels[key]

    def next_channel(self, metadata=None, result=None) -> 'CallChannel':
        channel = self.channel_for(self._next_req_id, metadata, result)
        self._next_req_id += 1
        return channel

    def close(self, key):
        return self._channels.pop(key)


class CallChannel:

    def __init__(self, channels: CallChannels, key, metadata=None, result=None):
        self.key = key
        self.metadata = metadata
        self.result = result

        self._waiter = None
        self._callbacks = []
        self._buffer = []
        self._channels = channels

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def call(self, call: Callable, max_wait=30):
        if max_wait == 0:
            call()
        else:
            self._waiter = Waiter(max_wait)
            call()
            while self._waiter.still_waiting():
                time.sleep(1)
            if self._waiter.expired():
                _log.warning(f'Call for {self.key} failed to complete in {self._waiter.max_wait}s,'
                             f' results may be incomplete.')
        return self.result

    def on_data(self, data):
        for callback in self._callbacks:
            callback(data)
        if self.result is None:
            self.result = data

    def buffer(self, data):
        self._buffer.append(data)

    def flush(self):
        data = list(self._buffer)
        self._buffer.clear()
        self.on_data(data)

    def close(self, data=None):
        if data is not None:
            self.on_data(data)
        if self._waiter is not None:
            self._waiter.done()
        self._channels.close(self.key)
