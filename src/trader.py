#!/usr/bin/env python3
"""
Command line tool for executing trades
"""
__author__ = "Andy Jenkins"
__license__ = "Apache 2.0"

import argparse
from ibkr import InteractiveBroker
from broker import BrokerListener, Position, Direction
import console as c


class Trader(BrokerListener):
    def __init__(self):
        c.announce('Starting the IBKR interface')
        self.broker = InteractiveBroker()
        self.broker.start()
        self.prev_close = 0
        self.prev_wap = 0
        self.is_open = False
        self.order = None

    def open_position(self, position: Position):
        c.announce(f'Opening position on {position.symbol}: {position}')
        self.listen(position.symbol)
        self.broker.open(position)

    def listen(self, symbol):
        self.broker.listen(symbol, self)

    def on_bar(self, symbol, date, open_, high, low, close, volume, wap, count):
        date_str = date.strftime("%Y%m%d %H:%M:%S")
        close_str = c.fmt(close, self.prev_close if self.prev_close else open_)
        wap_str = c.fmt(wap, self.prev_wap if self.prev_wap else wap, bold=True)
        p_and_l = '[  NA  ]' if not self.order else f'[{self.p_and_l(): >6}]'
        print(f'{date_str} {symbol} {wap_str} O{c.fmt(open_)}-H{c.fmt(high, open_)}-L{c.fmt(low, open_)}-C{close_str}'
              f' {volume: >4} {p_and_l}')
        self.prev_close = close
        self.prev_wap = wap

    def p_and_l(self):
        if not self.order:
            return 0


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


if __name__ == "__main__":
    main()
