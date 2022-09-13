"""
 Interactive Broker API Wrapper and Broker based on that API
"""
from ibapi.client import EClient
from ibapi.commission_report import CommissionReport
from ibapi.common import TickerId, BarData
from ibapi.execution import Execution
from ibapi.wrapper import EWrapper, OrderId, Order
from ibapi.contract import Contract
import threading
import time
from datetime import datetime
from broker import Broker, Position, Direction, Order as BrokerOrder, OrderStatus, OrderEvent
import console
import markets
from markets import Resolution
from util import events
import logging
from typing import Callable
from util.timeutil import spans_days, count_trading_days, parse_date, Waiter
from util.misc import decimal as d

log = logging.getLogger(__name__)
LIVE_TRADING_PORT = 7496
SIMULATED_TRADING_PORT = 7497
CONNECTION_ID = 1


class InteractiveBroker(Broker):

    def __init__(self, watchlist: markets.WatchList):
        super().__init__(watchlist)
        self.ib = IBApi.instance()

    def start(self):
        self.ib.start()

    def shutdown(self):
        self.ib.shutdown()

    def cancel_pending_orders(self):
        for order in self.book:
            if order.is_cancellable():
                console.announce(f'Cancelling pending order {order}')
                self.ib.cancelOrder(order.order_id)

    def place_order(self, position: Position) -> BrokerOrder:
        order = self.ib.place_order(position, self.on_order_status)
        self.book.append(order)
        return order

    def on_order_status(self, order_id, status, filled: float, avg_fill_price: float):
        status = to_order_status(status)
        console.warn(f'Received open order status: {order_id} {status} {filled} {avg_fill_price} {status}')
        try:
            order, index = self.book.by_order_id(order_id)
            if type(filled) is float and not filled.is_integer():
                console.warn('Fractional order fill!')
            order = order.update_status(status, d(avg_fill_price), filled)
            self.book[index] = order
            events.emit(OrderEvent(order))
        except KeyError:
            console.warn(f'Received unknown open order status: {order_id} {status} {filled} {avg_fill_price}')


def to_order_status(status: str) -> OrderStatus:
    if status in ('ApiPending', 'PendingSubmit', 'PendingCancel', 'PreSubmitted'):
        return OrderStatus.PENDING
    elif status == 'Submitted':
        return OrderStatus.SUBMITTED
    elif status == 'Filled':
        return OrderStatus.FILLED
    elif status in ('Cancelled', 'ApiCancelled', 'Inactive'):
        return OrderStatus.CANCELLED
    else:
        console.warn(f'Unrecognized order status from IB API: {status}')
        return OrderStatus.UNKNOWN


class IBApi(EWrapper, EClient):

    _instance = None

    @staticmethod
    def instance():
        if not IBApi._instance:
            IBApi._instance = IBApi()
        return IBApi._instance

    def __init__(self):
        EClient.__init__(self, self)
        self.reqIds(-1)
        self.order_id = 0
        self.ready = False
        # self.req_ids = {}
        # self.next_symbol_id = 0
        self.order_listeners = {}
        self.connect('127.0.0.1', SIMULATED_TRADING_PORT, CONNECTION_ID)
        self.req_id = 0
        self.request_data = {}
        self.realtime_subs = set()

    def start(self):
        if not self.ready:
            console.announce('Starting IB Thread')
            ib_thread = threading.Thread(target=self.run, daemon=True)
            ib_thread.start()
            while not self.ready:
                time.sleep(.1)
        else:
            console.announce('IB Thread already started')

    def shutdown(self):
        self.disconnect()
        self.ready = False

    def place_order(self, position: Position, order_listener: Callable) -> BrokerOrder:
        order = Order()
        order.orderType = 'MKT'  # or 'LMT' ...
        order.action = 'BUY' if position.direction is Direction.LONG else 'SELL'

        if markets.is_crypto(position.symbol):
            order.cashQty = position.quantity
        else:
            order.totalQuantity = position.quantity

        order_id = self.next_order_id()
        self.order_listeners[order_id] = order_listener
        broker_order = BrokerOrder(position, OrderStatus.PENDING, order_id)
        self.placeOrder(order_id, contract_for(position.symbol), order)
        return broker_order

    def subscribe_realtime(self, symbol):
        if symbol in self.realtime_subs:
            raise ValueError(f'Already subscribed to {symbol}')

        console.announce(f'Subscribing to realtime data for {symbol}')
        contract = contract_for(symbol)
        what_to_show = 'MIDPOINT' if markets.is_forex(symbol) else 'TRADES'
        req_id = self.next_request_id()
        self.request_data[req_id] = symbol
        console.announce(f'Requesting realtime data for {symbol} via req_id {req_id}')
        self.reqRealTimeBars(req_id, contract, 5, what_to_show, False, [])

    def realtimeBar(self, req_id: TickerId, date: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        symbol = self.request_data[req_id]
        tick_bar = IBApi.to_tick_bar(symbol, date, open_, high, low, close, wap, volume)
        events.emit(markets.TickEvent(tick_bar))

    def req_historical_data(self, request: markets.DataRequest) -> markets.SymbolData:
        """Blocking call to underlying API"""
        console.announce(f'Requesting historical date: {request}')
        contract = contract_for(request.symbol)
        query_time = request.end.strftime("%Y%m%d-%H:%M:%S")
        duration = to_time_string(request.start, request.end)
        bar_size = self.bar_size(request.resolution)
        what_to_show = 'MIDPOINT' if markets.is_forex(request.symbol) else 'TRADES'
        req_id = self.next_request_id()
        data = markets.SymbolData(request.symbol)
        wait_time = 30
        waiter = Waiter(wait_time)
        self.request_data[req_id] = (request, data, waiter)
        self.reqHistoricalData(req_id, contract, query_time, duration, bar_size, what_to_show, 1, 1, False, [])
        while waiter.still_waiting():
            time.sleep(1)
        if waiter.expired():
            console.warn(f'Historical data request failed to complete in {wait_time}s, results may be incomplete'
                         f' ({len(data)} tick bars).')
        return data

    def historicalData(self, req_id, bar: BarData):
        super().historicalData(req_id, bar)
        log.debug(f'Received historical data: {bar!r}')
        request, data, _ = self.request_data[req_id]
        date = parse_date(bar.date).astimezone()
        if request.start <= date:
            tick_bar = IBApi.to_tick_bar(request.symbol, date, bar.open, bar.high, bar.low, bar.close, bar.average,
                                         bar.volume)
            data.append_bar(tick_bar)

    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)
        request, data, waiter = self.request_data.pop(req_id)
        console.announce(f'Completed historical data request ({len(data)} results): {request}')
        waiter.done()

    def error(self, req_id: TickerId, error_code: int, error_str: str):
        super().error(req_id, error_code, error_str)
        console.error(f'Error. Id:{req_id}, Code: {error_code}, Msg:, {error_str}')

    def bar_size(self, resolution: Resolution):
        # See https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_duration
        bar_sizes = {
            Resolution.FIVE_SEC: '5 secs',
            Resolution.MINUTE: '1 min',
            Resolution.DAY: '1 day',
            Resolution.WEEK: '1 week',
            Resolution.MONTH: '1 month'
        }
        return bar_sizes[resolution]

    def nextValidId(self, order_id):
        log.info(f'Next valid ID: {order_id}')
        EWrapper.nextValidId(self, order_id)
        self.order_id = order_id
        self.ready = True

    def next_order_id(self):
        self.order_id += 1
        return self.order_id

    def next_request_id(self):
        self.req_id += 1
        return self.req_id

    def orderStatus(self, order_id: OrderId, status: str, filled: float, remaining: float, avg_fill_price: float,
                    perm_id: int, parent_id: int, last_fill_price: float, client_id: int, why_held: str,
                    mkt_cap_price: float):
        console.warn(f'Received IB order status {order_id} {status}')
        super().orderStatus(order_id, status, filled, remaining, avg_fill_price, perm_id, parent_id, last_fill_price,
                            client_id, why_held, mkt_cap_price)
        self.order_listeners[order_id](order_id, status, filled, avg_fill_price)

    def commissionReport(self, commission_report: CommissionReport):
        super().commissionReport(commission_report)
        print("CommissionReport.", commission_report)

    def execDetails(self, req_id: int, contract: Contract, execution: Execution):
        super().execDetails(req_id, contract, execution)
        print("ExecDetails. ReqId:", req_id, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Currency:", contract.currency, execution)

    @staticmethod
    def to_tick_bar(symbol: str, date, open_: float, high: float, low: float, close: float,
                    wap: float, volume: int):
        if type(date) is int:
            date = datetime.utcfromtimestamp(date).astimezone()
        elif type(date) is str:
            date = parse_date(date).astimezone()
        open_, high, low, close, wap = d(open_), d(high), d(low), d(close), d(wap)
        return markets.TickBar(symbol, date, open_, high, low, close, wap, volume)


def contract_for(symbol):
    return crypto_contract(symbol) if markets.is_crypto(symbol) \
        else forex_contract(symbol) if markets.is_forex(symbol) \
        else stock_contract(symbol)


def stock_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'  # 'FUT' ETC
    contract.exchange = 'SMART'
    contract.currency = 'USD'
    return contract


def crypto_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'CRYPTO'  # 'FUT' ETC
    contract.exchange = 'PAXOS'
    contract.currency = 'USD'
    return contract


def forex_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'CASH'  # 'FUT' ETC
    contract.exchange = 'IDEALPRO'
    contract.currency = 'USD'
    return contract


def to_time_string(start: datetime, end: datetime):
    if spans_days(start, end):
        days = count_trading_days(start, end)
        return f'{days} D'  # Include end day
    else:
        secs = (end - start).total_seconds()
        return f'{secs} S'
