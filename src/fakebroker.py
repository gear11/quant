import queue

from broker import Broker, Position, Order, BrokerListener, OrderStatus
from markets import DataRequest, Bar
import threading
import time
from queue import Queue
import random
from datetime import datetime
from decimal import Decimal


class FakeBroker(Broker):
    """A fake broker that will satisfy all orders in a random time"""

    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.shutdown_request = False
        self.listeners: list[BrokerListener] = []
        self._fake_broker_thread = FakeBrokerThread(self.queue, self.listeners)

    def start(self):
        print('Starting Fake Broker Thread')
        ib_thread = threading.Thread(target=self._run, daemon=True)
        ib_thread.start()

    def shutdown(self):
        self.shutdown_request = True

    def cancel_pending_orders(self):
        self._fake_broker_thread.cancel_pending_orders()

    def listen(self, symbol: str, listener: BrokerListener):
        self.listeners.append(listener)

    def subscribe_real_time(self, symbol):
        self._fake_broker_thread.add_symbol(symbol)

    def get_history(self, request: DataRequest):
        self._fake_broker_thread.get_history(request)

    def place_order(self, position: Position) -> Order:
        order = Order(position, OrderStatus.PENDING)
        self._fake_broker_thread.orders.append(order)
        return order

    def _run(self):
        self._fake_broker_thread.run()

    def current_position(self) -> Position:
        return sum(order.position for order in self._fake_broker_thread.orders)


class FakeBrokerThread:

    def __init__(self, queue: Queue, listeners: list[BrokerListener]):
        self.queue = queue
        self.listeners = listeners
        self.shutdown_request = False
        self.orders: list[Order] = []
        self.prices = {}

    def cancel_pending_orders(self):
        new_orders = []
        for order in self.orders:
            new_status = order.status
            if order.status in (OrderStatus.UNPOSTED, OrderStatus.PENDING):
                new_status = OrderStatus.CANCELLED
            new_orders.append(order.update_status(new_status))
        self.orders = new_orders

    def add_symbol(self, symbol):
        if symbol not in self.prices:
            self.prices[symbol] = to_dec(random.uniform(10, 100))

    def run(self):
        while not self.shutdown_request:

            try:
                position = self.queue.get(block=True, timeout=1)
            except queue.Empty:
                pass
            else:
                self.add_symbol(position.symbol)
                self.orders.append(Order(position, OrderStatus.PENDING, len(self.orders)))

            self.update_orders()

            if int(time.time()) % 5 == 0:
                self.update_prices()

    def update_prices(self):
        for symbol, price in self.prices.items():
            bar = self.next_bar(price)
            self.prices[symbol] = bar.close
            for listener in self.listeners:
                listener.on_bar(symbol, bar)

    def get_history(self, request: DataRequest):
        days = (request.end - request.start).days
        self.add_symbol(request.symbol)
        price = self.prices[request.symbol]
        bars = []
        for _ in range(days):
            bar = self.next_bar(price)
            bars.append(bar)
            price = bar.close

        for bar in reversed(bars):
            for listener in self.listeners:
                listener.on_bar(request.symbol, bar)

    def next_bar(self, prev_close):
        date = datetime.now()
        price = float(prev_close)
        high = random.uniform(price, price * 1.01)
        low = random.uniform(price * 0.99, price)
        close = random.uniform(low, high)
        volume = int(random.uniform(300, 600))
        wap = close
        return Bar(date, prev_close, to_dec(high), to_dec(low), to_dec(close), to_dec(wap), volume)

    def update_orders(self):
        new_orders = []
        for order in self.orders:
            new_status = order.status
            filled_at = None
            filled_quantity = None
            if order.status is OrderStatus.UNPOSTED:
                new_status = OrderStatus.PENDING
            elif order.status is OrderStatus.PENDING:
                new_status = OrderStatus.SUBMITTED
            elif order.status is OrderStatus.SUBMITTED:
                new_status = OrderStatus.FILLED
                filled_quantity = order.position.quantity
                filled_at = self.prices[order.position.symbol]
            new_order = order.update_status(new_status, filled_at, filled_quantity)
            new_orders.append(new_order)

            if new_status != order.status:
                for listener in self.listeners:
                    listener.on_order_status(new_order)

        self.orders = new_orders


def to_dec(num):
    return Decimal('%.2f' % num)



