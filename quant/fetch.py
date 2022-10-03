#!/usr/bin/env python3
"""
Fetch historical financial data from a variety of sources
"""
from __future__ import annotations

import argparse
import dateparser
from .sources import YahooData, IBKRData
from .markets import DataRequest, Resolution
from pandas import DataFrame
from functools import partial
from .util.timeutil import Timer
from datetime import datetime
from .markets import render_bar_data


_fetchers = {
    "yahoo": YahooData.fetch,
    "ibkr": IBKRData.fetch,
}


def fetch(source: str, symbol: str, start: str, end='today', resolution=Resolution.DAY) -> DataFrame:
    start = dateparser.parse(start, settings={'TIMEZONE': 'US/Eastern'}).astimezone()
    if start is None:
        raise IOError(f'Unrecognized start date: {start}')

    end = dateparser.parse(end, settings={'TIMEZONE': 'US/Eastern'}).astimezone()
    if end is None:
        raise IOError(f'Unrecognized end date: {end}')

    request = DataRequest(symbol, start, end, resolution)
    print(f'Fetching {symbol} from {source} between {start} and {end}. Request: {request}')
    return _fetchers[source](request)


# Makes it easy to import and use in Jupyter, for example:
#  from fetch import yahoo
#  df = yahoo(['MSFT'], '2 weeks ago')[0]
yahoo = partial(fetch, 'yahoo')


def main():
    parser = argparse.ArgumentParser(description='Fetch data from a given source')
    parser.add_argument('source', type=str, help='The source to use, for example "yahoo"')
    parser.add_argument('start', type=str, help='Start date or time (uses dateparser)')
    parser.add_argument('end', type=str, help='End date or time (uses dateparser)')
    parser.add_argument('symbols', nargs='+', help='Symbols to retrieve')
    parser.add_argument('-F', dest='format', type=str, default='csv', help='Output format, default to CSV')
    parser.add_argument('-f', dest='file', type=str, help='Output to a named file')
    resolutions = argconv(M=Resolution.MONTH, w=Resolution.WEEK, d=Resolution.DAY, m=Resolution.MINUTE, f=Resolution.FIVE_SEC)
    parser.add_argument('-r', dest='resolution', type=resolutions, help='Resolution type', default=Resolution.DAY)
    args = parser.parse_args()

    with Timer('fetch'):
        data_frames = []
        for symbol in args.symbols:
            symbol = symbol.upper()
            data_frames.append(fetch(args.source, symbol, args.start, args.end, args.resolution))
    for index, df in enumerate(data_frames):
        print(f'{df.shape[0]} {args.resolution.name.lower()}(s) of data for {args.symbols[index].upper()}:')
        print_data_frame(args.symbols[index], df)


def argconv(**convs):
    def parse_argument(arg):
        if arg in convs:
            return convs[arg]
        else:
            msg = "invalid choice: {!r} (choose from {})"
            choices = ", ".join(sorted(repr(choice) for choice in convs.keys()))
            raise argparse.ArgumentTypeError(msg.format(arg, choices))
    return parse_argument


def print_data_frame(symbol, df: DataFrame, verbose=False):
    prev_close = None
    prev_ref_price = None
    for index, row in df.iterrows():
        date = index if type(index) is datetime else dateparser.parse(str(index))
        args = [row[label] for label in df]
        args.extend([prev_close, prev_ref_price])
        print(render_bar_data(symbol.upper(), date, *args))
        prev_close = row['Close']
        prev_ref_price = row[4]
    if verbose:
        print(df.describe(include='all'))


if __name__ == "__main__":
    main()
