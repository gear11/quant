import urllib.request
import time
import random
import os
import logging
from util import Parser

_log = logging.getLogger(__name__)

SYMBOL_DATA = 'https://query1.finance.yahoo.com/v1/finance/lookup?formatted=true&lang=en-US&region=US' \
              '&query=QQQQQ&type=TTTTT&count=CCCCC&start=SSSSS&corsDomain=finance.yahoo.com'

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
             ' (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'

if __name__ == "__main__":

    Parser().parse_args()

    symbol_type = 'etf'

    for ch in range(ord('a'), ord('z') + 1):
        query = chr(ch)
        dir_name = f'yahoo/lookup/etf/{query}'
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
        first, last, count = 0, 5000, 50
        for start in range(first, last, count):

            json_path = f'{dir_name}/yahoo_symbols_{start}_{start+count}.json'
            if os.path.exists(json_path):
                _log.debug(f'Skipping already fetched path {json_path}')
                continue

            url = SYMBOL_DATA.replace('CCCCC', str(count)).replace('SSSSS', str(start)).replace('QQQQQ', query).replace('TTTTT', symbol_type)
            _log.info(f'Fetching {url}')
            req = urllib.request.Request(url)
            req.add_header('user-agent', USER_AGENT)
            req.add_header('referer', SYMBOL_DATA)
            response = urllib.request.urlopen(req)
            data = response.read().decode('utf-8')

            _log.info(f'Writing to {json_path}')
            with open(json_path, 'w') as file:
                file.write(data)

            if len(data) == 88:
                _log.warning(f'Reached end of letter {query}')
                break
            time.sleep(random.randint(5, 10))
