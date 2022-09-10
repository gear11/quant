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
from datetime import datetime, timedelta
from broker import Broker, Position, Direction, Order as BrokerOrder, OrderStatus, OrderEvent
import console
import markets
from markets import decimal as d, Resolution
from util import events
import logging as log
from util.bidict import Bidict
from typing import Callable
from util.timeutil import spans_days, count_trading_days

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
                console.warn(f'Fractional order fill!')
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
        self.symbol_ids = Bidict()
        self.next_symbol_id = 0
        self.order_listeners = {}
        self.connect('127.0.0.1', SIMULATED_TRADING_PORT, CONNECTION_ID)
        self.historical_req_id = 0
        self.historical_requests = {}

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

    def id_for(self, symbol):
        try:
            return self.symbol_ids[symbol]
        except KeyError:
            self.next_symbol_id += 1
            self.symbol_ids[symbol] = self.next_symbol_id
            return self.next_symbol_id

    def subscribe_realtime(self, symbol):
        console.announce(f'Subscribing to realtime data for {symbol}')
        contract = contract_for(symbol)
        what_to_show = 'MIDPOINT' if markets.is_forex(symbol) else 'TRADES'
        req_id = self.id_for(symbol)
        console.announce(f'Requesting realtime data for {symbol} via req_id {req_id}')
        self.reqRealTimeBars(req_id, contract, 5, what_to_show, False, [])

    def realtimeBar(self, req_id: TickerId, date: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        self.on_bar_update(req_id, date, open_, high, low, close, wap, volume)

    def error(self, req_id: TickerId, error_code: int, error_str: str):
        log.error(f'ERROR: {req_id} {error_code}: {error_str} ')

    def req_historical_data(self, request: markets.DataRequest, callback: Callable):
        contract = contract_for(request.symbol)
        query_time = request.end.strftime("%Y%m%d %H:%M:%S")
        duration = to_time_string(request.start, request.end)
        bar_size = self.bar_size(request.resolution)
        what_to_show = 'MIDPOINT' if markets.is_forex(request.symbol) else 'TRADES'
        self.historical_req_id += 1
        self.historical_requests[self.historical_req_id] = (request, callback)
        self.symbol_ids[request.symbol] = self.historical_req_id
        self.reqHistoricalData(self.historical_req_id, contract, query_time, duration, bar_size, what_to_show,
                               1, 1, False, [])

    def historicalData(self, req_id, bar: BarData):
        log.debug(f'Received historical data: {bar!r}')
        request, _ = self.historical_requests[req_id]
        try:
            date = datetime.strptime(bar.date, '%Y%m%d')
        except ValueError:
            date = datetime.strptime(bar.date, '%Y%m%d  %H:%M:%S')
        if request.start <= date:
            self.on_bar_update(req_id, date, bar.open, bar.high, bar.low, bar.close, bar.average, bar.volume)

    def historicalDataEnd(self, req_id: int, start: str, end: str):
        super().historicalDataEnd(req_id, start, end)
        _, callback = self.historical_requests.pop(req_id)
        callback()

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

    def on_bar_update(self, req_id: TickerId, date, open_: float, high: float, low: float, close: float,
                      wap: float, volume: int):
        if type(date) is int:
            date = datetime.utcfromtimestamp(date)
        elif type(date) is str:
            try:
                date = datetime.strptime(date, '%Y%m%d')
            except ValueError:
                date = datetime.strptime(date, '%Y%m%d  %H:%M:%S')
        open_, high, low, close, wap = d(open_), d(high), d(low), d(close), d(wap)
        try:
            symbol = self.symbol_ids.reverse[req_id]
            tick_bar = markets.TickBar(symbol, date, open_, high, low, close, wap, volume)
            events.emit(markets.TickEvent(tick_bar))
        except KeyError:
            console.error(f'Received bar update for unknown req_id {req_id}')


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
