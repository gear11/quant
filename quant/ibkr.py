"""
 Interactive Broker API Wrapper and Broker based on that API
"""
from ibapi.scanner import ScannerSubscription
from ibapi.tag_value import TagValue

from .broker import Broker, Position, Direction, Order as BrokerOrder, OrderStatus, OrderEvent
from .util.timeutil import spans_days, count_trading_days, parse_date
from .util.misc import decimal as d
from .markets import Resolution, WatchList, DataRequest, SymbolData, Symbols, TickEvent, TickBar
from .util import events, channels
from .util.timeutil import Timer
from .util.channel import CallChannels

from ibapi.client import EClient
from ibapi.commission_report import CommissionReport
from ibapi.common import TickerId, BarData
from ibapi.execution import Execution
from ibapi.wrapper import EWrapper, OrderId, Order
from ibapi.contract import Contract, ContractDetails
import threading
import time
from datetime import datetime
import logging
from typing import Callable


_log = logging.getLogger(__name__)
logging.getLogger('ibapi').setLevel(logging.INFO)

LIVE_TRADING_PORT = 7496
SIMULATED_TRADING_PORT = 7497
CONNECTION_ID = 1


class BrokerContext:
    def __init__(self):
        self.started = False

    def __enter__(self):
        self.started = IBApi.instance().start()
        return IBApi.instance()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.started:
            IBApi.instance().shutdown()


class InteractiveBroker(Broker):

    def __init__(self, watchlist: WatchList):
        super().__init__(watchlist)
        self.ib = IBApi.instance()

    def start(self):
        self.ib.start()

    def shutdown(self):
        self.ib.shutdown()

    def cancel_pending_orders(self):
        for order in self.book:
            if order.is_cancellable():
                _log.info(f'Cancelling pending order {order}')
                self.ib.cancelOrder(order.order_id)

    def place_order(self, position: Position) -> BrokerOrder:
        order = self.ib.place_order(position, self.on_order_status)
        self.book.append(order)
        return order

    def on_order_status(self, order_data):
        order_id, status, filled, avg_fill_price = order_data
        status = to_order_status(status)
        _log.info(f'Received open order status: {order_id} {status} {filled} {avg_fill_price} {status}')
        try:
            order, index = self.book.by_order_id(order_id)
            if type(filled) is float and not filled.is_integer():
                _log.warning('Fractional order fill!')
            order = order.update_status(status, d(avg_fill_price), filled)
            self.book[index] = order
            events.emit(OrderEvent(order))
        except KeyError:
            _log.warning(f'Received unknown open order status: {order_id} {status} {filled} {avg_fill_price}')


class IBApi(EWrapper, EClient):

    _instance = None

    @staticmethod
    def instance():
        if not IBApi._instance:
            IBApi._instance = IBApi()
        return IBApi._instance

    def __init__(self):
        EClient.__init__(self, self)
        self.thread_running = False
        self.orders = None
        self.is_connected = False
        self.subscriptions = {}

    def start(self):
        if not self.is_connected:
            _log.info('Connecting to IB Server')
            self.connect('127.0.0.1', SIMULATED_TRADING_PORT, CONNECTION_ID)
            self.is_connected = True
        if not self.thread_running:
            _log.info('Starting IB Thread')
            ib_thread = threading.Thread(target=self.run, daemon=True)
            ib_thread.start()
            t = Timer()
            while not self.thread_running:
                if t.total() > 10:
                    _log.error('Unable to start IB Thread')
                    return False
                time.sleep(.1)
            return True
        else:
            _log.info('IB Thread already started')
            return False

    def shutdown(self):
        self.reader.done = True
        self.disconnect()
        self.is_connected = False
        self.thread_running = False
        self.orders = None

    def place_order(self, position: Position, order_listener: Callable) -> BrokerOrder:
        channel = self.orders.next_channel()
        channel.add_callback(order_listener)
        order = Order()
        order.orderType = 'MKT'  # or 'LMT' ...
        order.action = 'BUY' if position.direction is Direction.LONG else 'SELL'
        if Symbols.is_crypto(position.symbol):
            order.cashQty = position.quantity
        else:
            order.totalQuantity = position.quantity
        self.placeOrder(channel.key, contract_for(position.symbol), order)
        return BrokerOrder(position, OrderStatus.PENDING, channel.key)

    def subscribe_realtime(self, symbol):
        if symbol in self.subscriptions:
            raise ValueError(f'Already subscribed to {symbol}')
        channel = channels.next_channel()
        channel.add_callback(lambda tick_bar: events.emit(TickEvent(tick_bar)))
        channel.metadata = symbol
        self.subscriptions[symbol] = channel
        _log.info(f'Requesting realtime data for {symbol} via req_id {channel.key}')
        contract = contract_for(symbol)
        what_to_show = 'MIDPOINT' if Symbols.is_forex(symbol) else 'TRADES'
        self.reqRealTimeBars(channel.key, contract, 5, what_to_show, False, [])

    def unsubscribe_realtime(self, symbol):
        if symbol not in self.subscriptions:
            raise ValueError(f'Not subscribed to {symbol}')
        _log.info(f'Unsubscribing to realtime data for {symbol}')
        channel = self.subscriptions[symbol]
        self.cancelRealTimeBars(channel.key)
        channel.close()

    def get_scanner_tags(self):
        return channels.channel_for('scannerParams').call(self.reqScannerParameters)

    def scannerParameters(self, xml: str):
        channels.channel_for('scannerParams').close(xml)

    def req_historical_data(self, request: DataRequest) -> SymbolData:
        """Blocking call to underlying API"""

        symbol_data = SymbolData(request.symbol)
        channel = channels.next_channel(metadata=request.symbol, result=symbol_data)
        channel.add_callback(symbol_data.append_bar)

        def make_request():
            _log.info(f'Requesting historical data. Original request: {request}')
            contract = contract_for(request.symbol)
            query_time = request.end.strftime("%Y%m%d-%H:%M:%S")
            duration = to_time_string(request.start, request.end)
            bs = bar_size(request.resolution)
            what_to_show = 'MIDPOINT' if Symbols.is_forex(request.symbol) else 'TRADES'
            _log.debug(f'Requesting historical data. IBKR request:'
                       f' req_id: {channel.key} query_time: {query_time} duration: {duration} bar_size: {bs}')
            self.reqHistoricalData(channel.key, contract, query_time, duration, bs, what_to_show, 1, 1, False, [])

        return channel.call(make_request)

    def create_scanner(self, tags, callback):
        scanner = ScannerSubscription()
        scanner.instrument = "STK"
        scanner.locationCode = "STK.US"
        scanner.scanCode = 'TOP_VOLUME_RATE'
        tags = [TagValue(k, v) for k, v in tags.items()]

        channel = channels.next_channel()
        channel.add_callback(callback)
        self.reqScannerSubscription(channel.key, scanner, [], tags)

        """
        self.reqScannerSubscription(7001, ScannerSubscriptionSamples.HighOptVolumePCRatioUSIndexes(), "", null);

        TagValue
        t1 = new
        TagValue("usdMarketCapAbove", "10000");
        TagValue
        t2 = new
        TagValue("optVolumeAbove", "1000");
        TagValue
        t3 = new
        TagValue("avgVolumeAbove", "100000000");
        List < TagValue > TagValues = new
        List < TagValue > {t1, t2, t3};
        client.reqScannerSubscription(7002, ScannerSubscriptionSamples.HotUSStkByVolume(), null, TagValues); // re
        """

    def cancel_scanner(self, key):
        self.cancelScannerSubscription(key)

    # CALLBACK METHODS FROM IBAPI

    def commissionReport(self, commission_report: CommissionReport):
        super().commissionReport(commission_report)
        print("CommissionReport.", commission_report)

    def error(self, req_id: TickerId, error_code: int, error_str: str):
        super().error(req_id, error_code, error_str)
        _log.error(f'Error. Id:{req_id}, Code: {error_code}, Msg:, {error_str}')

    def execDetails(self, req_id: int, contract: Contract, execution: Execution):
        super().execDetails(req_id, contract, execution)
        print("ExecDetails. ReqId:", req_id, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Currency:", contract.currency, execution)

    def historicalData(self, req_id, bar: BarData):
        _log.debug(f'Received historical data: {bar!r}')
        date = parse_date(bar.date).astimezone()
        channel = channels.channel_for(req_id)
        tick_bar = to_tick_bar(channel.metadata, date, bar.open, bar.high, bar.low, bar.close, bar.average, bar.volume)
        channel.on_data(tick_bar)

    def historicalDataEnd(self, req_id: int, start: str, end: str):
        _log.debug(f'Completed historical data request {req_id}')
        channels.channel_for(req_id).close()

    def nextValidId(self, order_id):
        _log.info(f'Connection ready. Next valid ID: {order_id}')
        EWrapper.nextValidId(self, order_id)
        if self.orders is None:
            self.orders = CallChannels(order_id)
        self.thread_running = True

    def orderStatus(self, order_id: OrderId, status: str, filled: float, remaining: float, avg_fill_price: float,
                    perm_id: int, parent_id: int, last_fill_price: float, client_id: int, why_held: str,
                    mkt_cap_price: float):
        _log.info(f'Received IB order status {order_id} {status}')
        self.orders.channel_for(order_id).on_data((order_id, status, filled, avg_fill_price))

    def realtimeBar(self, req_id: TickerId, date: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        _log.debug(f'Received realtime bar for {req_id}')
        channel = channels.channel_for(req_id)
        tick_bar = to_tick_bar(channel.metadata, date, open_, high, low, close, wap, volume)
        channel.on_data(tick_bar)

    def scannerData(self, req_id: int, rank: int, contract_details: ContractDetails,
                    distance: str, benchmark: str, projection: str, legs_str: str):
        _log.debug('Scanner result')
        channels.channel_for(req_id).buffer((rank, contract_details, distance, benchmark, projection, legs_str))

    def scannerDataEnd(self, req_id: int):
        _log.info('Flushing scanner data')
        channels.channel_for(req_id).flush()

# UTILITY METHODS


def to_tick_bar(symbol: str, date, open_: float, high: float, low: float, close: float,
                wap: float, volume: int):
    if type(date) is int:
        date = datetime.utcfromtimestamp(date).astimezone()
    elif type(date) is str:
        date = parse_date(date).astimezone()
    open_, high, low, close, wap = d(open_), d(high), d(low), d(close), d(wap)
    return TickBar(symbol, date, open_, high, low, close, wap, volume)


def bar_size(resolution: Resolution):
    # See https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_duration
    bar_sizes = {
        Resolution.FIVE_SEC: '5 secs',
        Resolution.MINUTE: '1 min',
        Resolution.DAY: '1 day',
        Resolution.WEEK: '1 week',
        Resolution.MONTH: '1 month'
    }
    return bar_sizes[resolution]


def contract_for(symbol):
    return crypto_contract(symbol) if Symbols.is_crypto(symbol) \
        else forex_contract(symbol) if Symbols.is_forex(symbol) \
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
        total_days, trading_days = count_trading_days(start, end)
        return f'{trading_days if trading_days else total_days} D'  # Include end day
    else:
        secs = (end - start).total_seconds()
        return f'{secs} S'


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
        _log.warning(f'Unrecognized order status from IB API: {status}')
        return OrderStatus.UNKNOWN
