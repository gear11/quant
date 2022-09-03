#!/usr/bin/env python3
"""
Command line tool for executing trades
"""
__author__ = "Andy Jenkins"
__license__ = "Apache 2.0"

import argparse
from ibkr import InteractiveBroker
from broker import BrokerListener, Position, Direction
from markets import Bar
import console


class Trader(BrokerListener):
    def __init__(self):
        console.announce('Starting the IBKR interface')
        self.broker = InteractiveBroker()
        self.broker.start()
        self.prev_close = 0
        self.prev_wap = 0
        self.is_open = False
        self.order = None

    def open_position(self, position: Position):
        console.announce(f'Opening position on {position.symbol}: {position.direction.name} {position.quantity}')
        self.listen(position.symbol)
        self.broker.subscribe_real_time(position.symbol)
        self.broker.open(position)

    def listen(self, symbol):
        self.broker.listen(symbol, self)

    def on_bar(self, symbol, bar: Bar):
        console.print_bar(symbol, bar)
        self.prev_close = bar.close
        self.prev_wap = bar.wap

    def p_and_l(self):
        if not self.order:
            return 0

    def shutdown(self):
        self.broker.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Execute a trade')
    parser.add_argument('direction', type=str, help='Direction of trade: buy or sell', choices=['buy', 'sell'])
    parser.add_argument('quantity', type=int, help='Number of shares to buy or sell')
    parser.add_argument('symbol', type=str, help='Symbol to trade')

    args = parser.parse_args()

    direction = Direction.LONG if args.direction == 'buy' else Direction.SHORT
    position = Position(args.symbol.upper(), direction, args.quantity)

    trader = Trader()
    trader.open_position(position)

    input('Enter anything to quit\n')
    trader.shutdown()


if __name__ == "__main__":
    main()
