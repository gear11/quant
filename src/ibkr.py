"""

"""
from ibapi.client import EClient
from ibapi.common import TickerId
from ibapi.wrapper import EWrapper, OrderState, OrderId, Order
from ibapi.contract import Contract
import threading
import time
from datetime import datetime
from broker import BrokerListener, Position, Direction
import console as c
import symbols

LIVE_TRADING_PORT = 7496
SIMULATED_TRADING_PORT = 7497
CONNECTION_ID = 1


class InteractiveBroker:
    ib: 'IBApi'
    symbols = {}

    def __init__(self):
        self.ib = IBApi(self)
        self.ib.connect('127.0.0.1', SIMULATED_TRADING_PORT, CONNECTION_ID)

    def start(self):
        print('Starting IB Thread')
        ib_thread = threading.Thread(target=self.run_loop, daemon=True)
        ib_thread.start()
        time.sleep(1)

    def run_loop(self):
        self.ib.run()

    def on_bar_update(self, req_id: TickerId, time: int, open_: float, high: float, low: float, close: float,
                      volume: int, wap: float, count: int):
        date = datetime.utcfromtimestamp(time)
        symbol, listener = self.symbols[req_id]
        listener.on_bar(symbol, date, open_, high, low, close, volume, wap, count)

    def listen(self, symbol: str, listener: BrokerListener):
        symbol = symbol.upper()
        if symbol in self.symbols:
            raise f'Already listening to {symbol}'
        id = len(self.symbols)
        self.symbols[id] = (symbol, listener)

        contract = contract_for(symbol)
        data_type = 'MIDPOINT' if symbols.is_forex(symbol) else 'TRADES'
        self.ib.reqRealTimeBars(0, contract, 5, data_type, False, [])

    def get_history(self, symbol, start: datetime, end: datetime = None):
        pass
        # end = end or datetime.now()
        # query_time = (datetime.today() - timedelta(days=180)).strftime("%Y%m%d %H:%M:%S")
        # self.ib.reqHistoricalData(1, contract, query_time, "1 M", "1 day", "MIDPOINT", 1, 1, False, [])

    def open(self, position: Position):
        order = Order()
        order.orderType = 'MKT'  # or 'LMT' ...
        order.action = 'BUY' if position.direction is Direction.LONG else 'SELL'

        if symbols.is_crypto(position.symbol):
            order.cashQty = position.quantity
        else:
            order.totalQuantity = position.quantity

        self.ib.placeOrder(self.ib.next_order_id(), contract_for(position.symbol), order)


class IBApi(EWrapper, EClient):
    def __init__(self, listener):
        EClient.__init__(self, self)
        self.listener = listener
        self.reqIds(-1)
        self.order_id = -1

    def realtimeBar(self, req_id: TickerId, time: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        self.listener.on_bar_update(req_id, time, open_, high, low, close, volume, wap, count)

    def error(self, req_id: TickerId, error_code: int, error_str: str):
        print(f'ERROR: {req_id} {error_code}: {error_str} ')

    def historicalData(self, req_id, bar):
        print("HistoricalData. ReqId:", req_id, "BarData:", bar)

    def nextValidId(self, orderId):
        #EWrapper.nextValidId(orderId)
        self.order_id = orderId
        print("NextValidId:", orderId)

    def next_order_id(self):
        self.order_id += 1
        return self.order_id

    def openOrder(self, order_id: OrderId, contract: Contract, order: Order, order_state: OrderState):
        super().openOrder(order_id, contract, order, order_state)
        print(f'Order confirmation received: {order_id} {contract} {order} {order_state.status} {order_state.completedStatus} {order_state.commission}')
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
                    perm_id: int,parent_id: int, last_fill_price: float, client_id: int,why_held: str, mkt_cap_price: float):
        super().orderStatus(order_id, status, filled, remaining, avg_fill_price, perm_id, parent_id, last_fill_price,
                            client_id, why_held, mkt_cap_price)
        print("OrderStatus. Id:", order_id, "Status:", status, "Filled:", c.fmt(filled),
              "Remaining:", c.fmt(remaining), "AvgFillPrice:", c.fmt(avg_fill_price),
              "PermId:", c.fmt(perm_id), "ParentId:", c.fmt(parent_id), "LastFillPrice:",
              c.fmt(last_fill_price), "ClientId:", c.fmt(client_id), "WhyHeld:",
              why_held, "MktCapPrice:", c.fmt(mkt_cap_price))


def contract_for(symbol):
    return crypto_contract(symbol) if symbols.is_crypto(symbol) \
        else forex_contract(symbol) if symbols.is_forex(symbol) \
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
