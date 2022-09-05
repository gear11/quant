"""

"""
from ibapi.client import EClient
from ibapi.common import TickerId, BarData
from ibapi.wrapper import EWrapper, OrderState, OrderId, Order
from ibapi.contract import Contract
import threading
import time
from datetime import datetime
from broker import Broker, BrokerListener, Position, Direction, Order as BrokerOrder, OrderStatus
import console
import markets
from decimal import Decimal
import timer

LIVE_TRADING_PORT = 7496
SIMULATED_TRADING_PORT = 7497
CONNECTION_ID = 1


class InteractiveBroker(Broker):

    def p_or_l(self):
        pass

    def current_position(self) -> Position:
        return sum(order.position for order in self.orders.values() if order.status is OrderStatus.FILLED)

    def __init__(self):
        super().__init__()
        self.ib = IBApi(self)
        self.ib.connect('127.0.0.1', SIMULATED_TRADING_PORT, CONNECTION_ID)
        self.symbols = {}
        self.orders = {}

    @property
    def open_orders(self) -> list[BrokerOrder]:
        return [order for order in self.orders.values() if order.status in (OrderStatus.SUBMITTED, OrderStatus.PENDING)]

    @property
    def filled_orders(self) -> list[BrokerOrder]:
        return [order for order in self.orders.values() if order.status is OrderStatus.FILLED]

    def start(self):
        print('Starting IB Thread')
        ib_thread = threading.Thread(target=self.ib.run, daemon=True)
        ib_thread.start()
        while not self.ib.ready:
            time.sleep(.1)

    def shutdown(self):
        self.ib.disconnect()

    def cancel_pending_orders(self):
        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                console.announce(f'Cancelling pending order {order}')
                self.ib.cancelOrder(order.order_id)

    def listen(self, symbol: str, listener: BrokerListener):
        symbol = symbol.upper()
        try:
            self._find_id(symbol)
        except ValueError:
            symbol_id = len(self.symbols)
            self.symbols[symbol_id] = (symbol_id, symbol, listener)
        else:
            console.error(f'Already listening to {symbol}')

    def subscribe_real_time(self, symbol):
        console.announce(f'Subscribing to realtime data for {symbol}')
        contract = contract_for(symbol)
        what_to_show = 'MIDPOINT' if markets.is_forex(symbol) else 'TRADES'
        self.ib.reqRealTimeBars(self._find_id(symbol), contract, 5, what_to_show, False, [])

    def get_history(self, request: markets.DataRequest):  # , start: datetime, end: datetime = None):
        contract = contract_for(request.symbol)
        # query_time = (datetime.today() - timedelta(days=180)).strftime("%Y%m%d %H:%M:%S")
        query_time = request.end.strftime("%Y%m%d %H:%M:%S")
        duration = timer.to_time_string(request.end - request.start)

        what_to_show = 'MIDPOINT' if markets.is_forex(request.symbol) else 'TRADES'
        self.ib.reqHistoricalData(self._find_id(request.symbol), contract, query_time, duration, "1 day", what_to_show,
                                  1, 1, False, [])

    def place_order(self, position: Position) -> BrokerOrder:
        order = Order()
        order.orderType = 'MKT'  # or 'LMT' ...
        order.action = 'BUY' if position.direction is Direction.LONG else 'SELL'

        if markets.is_crypto(position.symbol):
            order.cashQty = position.quantity
        else:
            order.totalQuantity = position.quantity

        order_id = self.ib.next_order_id()
        broker_order = BrokerOrder(position, OrderStatus.PENDING, order_id)
        self.orders[order_id] = broker_order
        self.ib.placeOrder(order_id, contract_for(position.symbol), order)
        return broker_order

    def _find_id(self, symbol):
        for symbol_id, a_symbol, listener in self.symbols.values():
            if a_symbol == symbol:
                return symbol_id
        raise ValueError(f'No such symbol {symbol}')

    def _on_bar_update(self, req_id: TickerId, date, open_: float, high: float, low: float, close: float,
                       volume: int, wap: float):
        if type(date) is int:
            date = datetime.utcfromtimestamp(date)
        elif type(date) is str:
            date = datetime.strptime(date, '%Y%m%d')
        _, symbol, listener = self.symbols[req_id]
        wap = Decimal(wap) if wap else None
        bar = markets.Bar(date, Decimal(open_), Decimal(high), Decimal(low), Decimal(close), wap, volume)
        listener.on_bar(symbol, bar)

    def _on_order_status(self, order_id, status, filled, avg_fill_price):
        status = to_order_status(status)
        console.warn(f'Received open order status: {order_id} {status} {filled} {avg_fill_price} {status}')
        if order_id in self.orders:
            cur_order = self.orders[order_id]
            new_order = cur_order.update_status(status, avg_fill_price, filled)
            for _, _, listener in self.symbols.values():
                listener.on_order_status(new_order)
            self.orders[order_id] = new_order
        else:
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
    def __init__(self, broker: InteractiveBroker):
        EClient.__init__(self, self)
        self.broker = broker
        self.reqIds(-1)
        self.order_id = 0
        self.ready = False

    def realtimeBar(self, req_id: TickerId, date: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        self.broker._on_bar_update(req_id, date, open_, high, low, close, volume, wap) # noqa Module local

    def error(self, req_id: TickerId, error_code: int, error_str: str):
        print(f'ERROR: {req_id} {error_code}: {error_str} ')

    def historicalData(self, req_id, bar: BarData):
        # print(f'{req_id} {bar}')
        self.broker._on_bar_update(req_id, bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume, bar.average) # noqa Module local

    def nextValidId(self, order_id):
        # print(f'Next valid ID: {order_id}')
        EWrapper.nextValidId(self, order_id)
        self.order_id = order_id
        self.ready = True

    def next_order_id(self):
        self.order_id += 1
        return self.order_id

    def openOrder(self, order_id: OrderId, contract: Contract, order: Order, order_state: OrderState):
        super().openOrder(order_id, contract, order, order_state)
        # print(f'Order confirmation received: {order_id} {contract} {order} {order_state.status} {order_state.completedStatus} {order_state.commission}')
        #     print("OpenOrder. PermId:", intMaxString(order.permId), "ClientId:", intMaxString(order.clientId), " OrderId:", intMaxString(orderId),
        #           "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
        #           "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
        #           "TotalQty:", decimalMaxString(order.totalQuantity), "CashQty:", floatMaxString(order.cashQty),
        #           "LmtPrice:", floatMaxString(order.lmtPrice), "AuxPrice:", floatMaxString(order.auxPrice), "Status:", orderState.status,
        #           "MinTradeQty:", intMaxString(order.minTradeQty), "MinCompeteSize:", intMaxString(order.minCompeteSize),
        #           "competeAgainstBestOffset:", "UpToMid" if order.competeAgainstBestOffset == COMPETE_AGAINST_BEST_OFFSET_UP_TO_MID else floatMaxString(order.competeAgainstBestOffset),
        #           "MidOffsetAtWhole:", floatMaxString(order.midOffsetAtWhole),"MidOffsetAtHalf:" ,floatMaxString(order.midOffsetAtHalf))
        #
        #     order.contract = contract
        #     self.permId2ord[order.permId] = order

    def orderStatus(self, order_id: OrderId, status: str, filled: float, remaining: float, avg_fill_price: float,
                    perm_id: int, parent_id: int, last_fill_price: float, client_id: int, why_held: str, mkt_cap_price: float):
        console.warn(f'Received IB order status {order_id} {status}')
        super().orderStatus(order_id, status, filled, remaining, avg_fill_price, perm_id, parent_id, last_fill_price,
                            client_id, why_held, mkt_cap_price)
        self.broker._on_order_status(order_id, status, filled, avg_fill_price) # noqa Module local
        # print("OrderStatus. Id:", order_id, "Status:", status, "Filled:", c.render_val(filled),
        #       "Remaining:", c.render_val(remaining), "AvgFillPrice:", c.render_val(avg_fill_price),
        #       "PermId:", c.render_val(perm_id), "ParentId:", c.render_val(parent_id), "LastFillPrice:",
        #       c.render_val(last_fill_price), "ClientId:", c.render_val(client_id), "WhyHeld:",
        #       why_held, "MktCapPrice:", c.render_val(mkt_cap_price))


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
