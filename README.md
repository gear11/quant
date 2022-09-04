# quant

Some tools I am developing as I work through exercises in quantitative trading. 
I'm trying to synthesize my explorations in a few areas:
- Technical trading, as exemplified in [How to Day Trade for a Living](https://www.amazon.com/How-Day-Trade-Living-Management-ebook/dp/B012C4AU10/)
  by Andrew Aziz
- Trying to write better Python, and get used to some of the newer language features (as in
  [Fluent Python](https://learning.oreilly.com/library/view/fluent-python/9781491946237/) by Luciano Ramalho)
- [Machine Learning Coursework](https://www.coursera.org/specializations/machine-learning-introduction?) on Coursera
- Understand markets and trading better, including options and forex

The tools in here right now include `fetch` and `trader`:
- The `fetch` tool fetches stock market data from International Brokers (IBKR) or Yahoo! Finance.
- The `trader` tool uses the [Interactive Brokers Trader Workstation](https://portal.interactivebrokers.com/en/index.php?f=16040)
and its [Python API](https://interactivebrokers.github.io/tws-api/index.html) to execute trading strategies.

## Fetch

The `fetch` tool can be used to fetch historical data from either Yahoo! or Interactive Brokers.

    % python src/fetch.py -h
    usage: fetch.py [-h] [-F FORMAT] [-f FILE] [-r RESOLUTION] source start end symbols [symbols ...]
    
    Fetch data from a given source
    
    positional arguments:
      source         The source to use, for example "yahoo"
      start          Start date or time (uses dateparser)
      end            End date or time (uses dateparser)
      symbols        Symbols to retrieve
    
    optional arguments:
      -h, --help     show this help message and exit
      -F FORMAT      Output format, default to CSV
      -f FILE        Output to a named file
      -r RESOLUTION  Resolution type

For example:

    % python src/fetch.py yahoo 2_weeks_ago today aapl
    Fetching AAPL from yahoo between 2022-08-21 11:21:58.026296 and 2022-09-04 11:21:58.027818. ...
    Timer(fetch) took 0.858s
    10 days(s) of data for aapl:
    2022-08-22 00:00:00 AAPL 167.57 O169.69-H169.86-L167.14-C167.57 69026800.0
    2022-08-23 00:00:00 AAPL 167.23 O167.08-H168.71-L166.65-C167.23 54147100.0
    ...
    2022-09-01 00:00:00 AAPL 157.96 O156.64-H158.42-L154.67-C157.96 74229900.0
    2022-09-02 00:00:00 AAPL 155.81 O159.75-H160.36-L154.97-C155.81 76905200.0

### Todos
- Granularity is just daily right now. IBKR supports smaller granularity
- Should support additional output formats such as Data Frame
- Should support output to a file in different formats

## Trader
The `trader` is a command-line client for executing trades via the IBKR TWS API. It can be used in manual mode as follows:

    % python src/trader.py buy 100 aapl -d

This will start the trader with a position to execute, but the `-d` option will cause it to not yet place an order.
After some startup debug messages, you get a command prompt:

    Subscribing to realtime data for AAPL
    Commands:
            q: Quit the trader program
            o: Open a delayed-open position
            c: Close an open position
            s: Position and order status
            Q: Force quit, without closing positions
            h: Display this help message
            l: Display last week of data
            r: Reduce the position (prompts for share quantity)

Once the program starts, I open the position by entering the `o` command:

    > o
    Open a delayed-open position
    Opening position: AAPL LONG 10

### Strategy automation

Ultimately I'd like to embed some trading strategies into the tool that could be invoked from the command line,
so that I could do something like:

    % python src/trader.py vwap_long 100 aapl

Where `vwap_long` is a Python strategy to go long in the stock tracking VWAP as a support level.
- Opens a position of LONG 100 AAPL once it is trading above VWAP
- Sets a stop at (rolling) VWAP
- As it generates a positive return, continuously ratchet the stop to halfway between current price and VWAP
- Should continuously output the P and L of the strategy (including commissions) and log its decisions for analysis

## Scanner

I'll also need to develop a scanner to quickly scan market data to identify stocks in play. Characteristics:
- Reasonable stock price
- Reasonable volume and volatility
- Active retail trading


