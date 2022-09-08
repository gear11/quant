from broker import Broker, Position, Order, OrderStatus, OrderEvent, OrderBook
from markets import DataRequest, decimal as d, WatchList
import threading
from queue import Queue, Empty
from util import events


class FakeBroker(Broker):
    """A fake broker that will satisfy all orders in a fixed time of 2 sec"""

    def __init__(self, watchlist: WatchList):
        super().__init__(watchlist)
        self.queue = Queue()
        self.worker = Worker(self.queue, self.book, self.watchlist)

    def start(self):
        self.worker.start()

    def shutdown(self):
        self.worker.shutdown()

    def cancel_pending_orders(self):
        self.worker.cancel_pending_orders()

    def subscribe_real_time(self, symbol):
        pass

    def get_history(self, request: DataRequest):
        self.worker.get_history(request)

    def place_order(self, position: Position):
        if position.symbol not in self.watchlist:
            raise KeyError(f'Symbol {position.symbol} must be added to watchlist before placing an order')
        self.worker.queue.put(position)


class Worker:

    def __init__(self, queue: Queue, book: OrderBook, watchlist: WatchList):
        self.queue = queue
        self.shutdown_request = False
        self.book = book
        self.watchlist = watchlist

    def start(self):
        print('Starting Fake Broker Thread')
        threading.Thread(target=self.run, daemon=True).start()

    def shutdown(self):
        self.shutdown_request = True

    def cancel_pending_orders(self):
        for i, order in enumerate(self.book):
            if order.is_cancellable():
                self.book[i] = update_order_status(order, OrderStatus.CANCELLED)

    def run(self):
        while not self.shutdown_request:
            try:
                position = self.queue.get(block=True, timeout=1)
            except Empty:
                pass
            else:
                self.book.append(Order(position, OrderStatus.PENDING, order_id=len(self.book)))

            self.update_orders()

            #if int(time.time()) % 5 == 0:
            #    for symbol, bar in self.watchlist.items():
            #        events.emit(TickEvent(self.next_bar(symbol, bar.close)))

    def get_history(self, request: DataRequest):
        pass
        # days = (request.end - request.start).days
        # self.add_symbol(request.symbol)
        # price = self.watchlist[request.symbol]
        # bars = []
        # for _ in range(days):
        #     bar = self.next_bar(request.symbol, price)
        #     bars.append(bar)
        #     price = bar.close
        #
        # for bar in reversed(bars):
        #     events.emit(TickEvent(bar))

    def update_orders(self):
        for i, order in enumerate(self.book):
            if order.status is OrderStatus.UNPOSTED:
                order = update_order_status(order, OrderStatus.PENDING)
            elif order.status is OrderStatus.PENDING:
                order = update_order_status(order, OrderStatus.SUBMITTED)
            elif order.status is OrderStatus.SUBMITTED:
                filled_quantity = order.position.quantity
                filled_at = d(self.watchlist[order.position.symbol].close)
                order = order.update_status(OrderStatus.FILLED, filled_at, filled_quantity)
                order = update_order_status(order, OrderStatus.FILLED)
            self.book[i] = order


def update_order_status(order: Order, status: OrderStatus):
    order = order.update_status(status)
    events.emit(OrderEvent(order))
    return order
