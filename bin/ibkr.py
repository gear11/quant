from quant.ibkr import IBApi, exec_broker_call


def main():
    def req_scanner_stuff(broker: IBApi) -> str:
        return broker.get_scanner_tags()
    symbol_data = exec_broker_call(req_scanner_stuff)
    print(symbol_data)


if __name__ == '__main__':
    main()
