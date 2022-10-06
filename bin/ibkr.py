from quant.ibkr import BrokerContext
from quant.util import Parser


def main():
    parser = Parser()
    parser.add_argument('filename', type=str, help='Output filename')
    args = parser.parse_args()

    with BrokerContext() as broker:
        scanner_data = broker.get_scanner_tags()

    with open(args.filename, 'w') as f:
        f.write(scanner_data)


if __name__ == '__main__':
    main()
