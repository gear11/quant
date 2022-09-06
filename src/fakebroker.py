import console
from broker import Broker, Position, Order, OrderStatus, OrderEvent
from markets import DataRequest, TickBar, TickEvent, decimal as d
import threading
import time
from queue import Queue, Empty
import random
from datetime import datetime
from sources import YahooData
from numpy import NaN
from util import events


class FakeBroker(Broker):
    """A fake broker that will satisfy all orders in a random time"""

    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self._worker = Worker(self.queue)
        self.shutdown_request = False

    def start(self):
        print('Starting Fake Broker Thread')
        ib_thread = threading.Thread(target=self._run, daemon=True)
        ib_thread.start()

    def shutdown(self):
        self.shutdown_request = True

    def cancel_pending_orders(self):
        self._worker.cancel_pending_orders()

    def subscribe_real_time(self, symbol):
        self._worker.add_symbol(symbol)

    def get_history(self, request: DataRequest):
        self._worker.get_history(request)

    def place_order(self, position: Position):
        self._worker.queue.put(position)

    def _run(self):
        self._worker.run()

    def current_position(self) -> Position:
        return sum(order.position for order in self._worker.orders)

    @property
    def open_orders(self) -> list[Order]:
        return [order for order in self._worker.orders if order.status in (OrderStatus.SUBMITTED, OrderStatus.PENDING)]

    @property
    def filled_orders(self) -> list[Order]:
        return [order for order in self._worker.orders if order.status is OrderStatus.FILLED]

    def p_or_l(self):
        if not self.filled_orders:
            return NaN
        first = self.filled_orders[0]
        return Order.combined_p_or_l(self.filled_orders, self._worker.latest_price[first.position.symbol])


class Worker:

    def __init__(self, queue: Queue):
        self.queue = queue
        self.shutdown_request = False
        self.orders: list[Order] = []
        self.latest_price = {}

    def cancel_pending_orders(self):
        for i, order in enumerate(self.orders):
            if order.status in (OrderStatus.UNPOSTED, OrderStatus.PENDING):
                self.orders[i] = update_order_status(order, OrderStatus.CANCELLED)

    def add_symbol(self, symbol):
        if symbol not in self.latest_price:
            console.announce(f'Looking up price of {symbol} from Yahoo')
            self.latest_price[symbol] = YahooData.current_price(symbol)

    def run(self):
        while not self.shutdown_request:
            try:
                position = self.queue.get(block=True, timeout=1)
            except Empty:
                pass
            else:
                self.add_symbol(position.symbol)
                self.orders.append(Order(position, OrderStatus.PENDING, order_id=len(self.orders)))

            self.update_orders()

            if int(time.time()) % 5 == 0:
                self.update_prices()

    def update_prices(self):
        for symbol, price in self.latest_price.items():
            bar = self.next_bar(symbol, price)
            self.latest_price[symbol] = bar.close
            events.emit(TickEvent(bar))

    def get_history(self, request: DataRequest):
        days = (request.end - request.start).days
        self.add_symbol(request.symbol)
        price = self.latest_price[request.symbol]
        bars = []
        for _ in range(days):
            bar = self.next_bar(request.symbol, price)
            bars.append(bar)
            price = bar.close

        for bar in reversed(bars):
            events.emit(TickEvent(bar))

    def next_bar(self, symbol, prev_close) -> TickBar:  # noqa No reason to make this static
        date = datetime.now()
        price = float(prev_close)
        high = random.uniform(price, price * 1.01)
        low = random.uniform(price * 0.99, price)
        close = random.uniform(low, high)
        volume = int(random.uniform(300, 600))
        wap = close
        return TickBar(symbol, date, prev_close, d(high), d(low), d(close), d(wap), volume)

    def update_orders(self):
        for i, order in enumerate(self.orders):
            if order.status is OrderStatus.UNPOSTED:
                order = update_order_status(order, OrderStatus.PENDING)
            elif order.status is OrderStatus.PENDING:
                order = update_order_status(order, OrderStatus.SUBMITTED)
            elif order.status is OrderStatus.SUBMITTED:
                filled_quantity = order.position.quantity
                filled_at = d(self.latest_price[order.position.symbol])
                order = order.update_status(OrderStatus.FILLED, filled_at, filled_quantity)
                order = update_order_status(order, OrderStatus.FILLED)
            self.orders[i] = order


def update_order_status(order: Order, status: OrderStatus):
    order = order.update_status(status)
    events.emit(OrderEvent(order))
    return order

