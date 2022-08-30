#!/usr/bin/env python3
"""
Fetch historical financial data from a variety of sources
"""
from __future__ import annotations

import argparse
import dateparser
from sources import fetch_yahoo
from request import Request, Resolution
from pandas import DataFrame
from functools import partial


_fetchers = {
    "yahoo": fetch_yahoo,
}


def fetch(source: str, symbols: list[str], start: str, end='today', resolution=Resolution.DAY) -> list[DataFrame]:
    start = dateparser.parse(start)
    if start is None:
        raise IOError(f'Unrecognized start date: {start}')

    end = dateparser.parse(end)
    if end is None:
        raise IOError(f'Unrecognized end date: {end}')

    request = Request(start, end, symbols, resolution)
    print(f'Fetching {symbols} from {source} between {start} and {end}. Request: {request}')
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
    parser.add_argument('-r', dest='resolution', type=Resolution, help='Resolution type', default=Resolution.DAY)
    args = parser.parse_args()

    data_frames = fetch(args.source, args.symbols, args.start, args.end)
    for index, df in enumerate(data_frames):
        # print(f'{df.shape[0]} {request.resolution.name.lower()}(s) of data for {args.symbol[index]}:')
        print(f'{df.shape[0]} days(s) of data for {args.symbols[index]}:')
        print(df)


if __name__ == "__main__":
    main()
