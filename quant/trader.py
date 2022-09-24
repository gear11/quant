from .broker import Broker, Position, Direction, OrderEvent
from .console import console, Colors
from .sources import init_market_data
from .util import events, Parser
from .markets import TickEvent, TickBar, WatchList
from .fakebroker import FakeBroker
from .ibkr import InteractiveBroker

import traceback
from functools import partial
import time
import logging

log = logging.getLogger(__name__)


class Trader:
    def __init__(self, position: Position, broker: Broker):
        self.broker = broker
        self.prev_close = 0
        self.prev_wap = 0
        self.initial_position = position
        self.symbol = position.symbol
        self.is_open = False  # Did we open a position?
        self.is_closed = False  # Did we close out our open position?

        events.observe(TickEvent, lambda event: self.on_bar(event.tick_bar))
        events.observe(OrderEvent, lambda event: console.announce(f'Received order status: {event.order}'))

    def open_position(self):
        if self.is_open:
            console.error(f'Position ALREADY OPEN: {self.initial_position}')
            return

        console.announce(f'Opening position: {self.initial_position}')
        self.broker.place_order(self.initial_position)
        self.is_open = True

    def on_bar(self, bar: TickBar):
        msg = console.render_bar(bar, self.prev_close, self.prev_wap)
        if self.is_open:
            msg += console.wrap(f' [P/L: ${self.broker.p_or_l()}]', Colors.BLUE)
        print(msg)
        self.prev_close = bar.close
        self.prev_wap = bar.wap

    def status(self):
        if self.is_open and not self.is_closed:
            print(f'\tCurrent position OPEN: {self.broker.current_positions()} with P/L {self.broker.p_or_l()}')
        elif self.is_closed:
            print(f'\tCurrent position CLOSED: {self.initial_position} with P/L {self.broker.p_or_l()}')
        else:
            print(f'\tPosition not yet open: {self.initial_position}')

        orders = self.broker.open_orders
        print(f'\tOpen orders: {len(orders)}')
        if orders:
            for order in orders:
                print(f'\t\t{order}')
        orders = self.broker.filled_orders
        print(f'\tFilled orders: {len(orders)}')
        if orders:
            for order in orders:
                print(f'\t\t{order}')

    def reduce_position(self, quantity: int):
        if not self.has_open_position():
            console.error('No position to reduce!')
        elif quantity < 1:
            console.error('Cannot reduce by a negative!')
        else:
            current_pos = self.broker.current_positions()[0]  # Assume only one position
            if current_pos.quantity < quantity:
                raise ValueError(f'Cannot reduce {quantity} with current position only {current_pos.quantity}.')
            reduce = Position(self.symbol, current_pos.reverse().direction, quantity)
            console.announce(f'Placing reduce order {reduce}')
            self.broker.place_order(reduce)

    def close_position(self):
        if not self.has_open_position():
            console.error('No open position to close')
            return

        open_orders = self.broker.open_orders
        console.announce(f'Closing/awaiting {len(open_orders)} open orders: {open_orders}')
        self.broker.cancel_pending_orders()
        self.await_open_orders()

        for position in self.broker.current_positions():
            reversal = position.reverse()
            console.announce(f'Placing reversal order {reversal}')
            self.broker.place_order(reversal)
            self.await_open_orders()

        self.is_closed = True

    def await_open_orders(self):
        while self.broker.open_orders:
            for order in self.broker.open_orders:
                print(order)
            time.sleep(1)

    def shutdown(self, force=False):
        if self.has_open_position() and not force:
            console.error('You must first close your open position')
        else:
            self.broker.shutdown()
            self.broker = None

    def has_open_position(self):
        if not self.is_open or self.is_closed:
            return False
        return any(position.quantity for position in self.broker.current_positions())

    def is_active(self):
        return self.broker is not None


def main():
    parser = Parser(description='Execute a trade')
    parser.add_argument('direction', type=str, help='Direction of trade: buy or sell', choices=['buy', 'sell'])
    parser.add_argument('quantity', type=int, help='Number of shares to buy or sell')
    parser.add_argument('symbol', type=str, help='Symbol to trade')
    parser.add_argument('-d', dest='delay', action='store_const',
                        const=True, default=False,
                        help='Delay open until the open command is issued')
    parser.add_argument('-f', dest='fake', action='store_const',
                        const=True, default=False,
                        help='Use the fake broker')
    parser.add_argument('-s', dest='source', type=str,
                        help='Source of market data: "live", "random" or a date for example "2022-09-08 10:00:00"',
                        default='live')
    parser.add_argument('-H', dest='history', type=str, help='Directory for storing history', default='history')
    args = parser.parse_args()

    logging.getLogger('ibapi').setLevel(logging.WARN)

    watchlist = WatchList()
    watchlist.add_symbol(args.symbol)
    broker = init_broker(watchlist, use_fake=args.fake)
    init_market_data(args.source, watchlist)

    direction = Direction.LONG if args.direction == 'buy' else Direction.SHORT
    position = Position(args.symbol.upper(), direction, args.quantity)
    trader = Trader(position, broker)
    if not args.delay:
        trader.open_position()
    run_command_loop(trader)


def init_broker(watchlist, use_fake=False):
    if use_fake:
        console.announce('Using FAKE broker')
        broker = FakeBroker(watchlist)
    else:
        console.announce('Using Interactive Broker')
        broker = InteractiveBroker(watchlist)
    console.announce('Starting the Broker interface')
    broker.start()
    return broker


def run_command_loop(trader: Trader):

    commands = {
        'q': ('Quit the trader program', trader.shutdown),
        'o': ('Open a delayed-open position', trader.open_position),
        'c': ('Close an open position', trader.close_position),
        's': ('Position and order status', trader.status),
        'Q': ('Force quit, without closing positions', partial(trader.shutdown, True)),
    }

    def help_menu():
        print('Commands:')
        for key, command_def in commands.items():
            print(f'\t{key}: {command_def[0]}')

    commands['h'] = ('Display this help menu', help_menu)

    def reduce(amount: int = 0):
        if not trader.has_open_position():
            console.error('No open position to reduce')
            return 1
        amount = int(amount or input('Reduce position by how many shares? '))
        trader.reduce_position(amount)

    commands['r'] = ('Reduce the position (prompts for share quantity)', reduce)

    help_menu()
    while trader.is_active():
        tokens = input('').split(' ')
        command = tokens[0]
        if command not in commands:
            console.announce(f'Unrecognized command {command}')
            help_menu()
        else:
            command = commands[command]
            console.announce(command[0])
            try:
                args = tokens[1:] if len(tokens) > 1 else []
                if command[1](*args):
                    trader.status()
            except Exception:  # noqa Catch everything we can to prevent hang with an open position
                console.error(f'Error executing "{" ".join(tokens)}":')
                print(traceback.format_exc())
                trader.status()


if __name__ == "__main__":
    main()
