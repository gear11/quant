import time

from quant.ibkr import BrokerContext
from quant.util import Parser
import xml.etree.ElementTree as ET


def on_scanner_data(data):
    for item in data:
        print(item)


def get_scanner_params(filename):
    with BrokerContext() as broker:
        scanner_data = broker.get_scanner_tags()

    with open(filename, 'w') as f:
        f.write(scanner_data)


def get_scan_types(filename):
    with open(filename, 'r') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        for scan_type in root.findall('./ScanTypeList/ScanType'):
            scan_code, display_name = None, None
            for child in scan_type:
                if child.tag == 'displayName':
                    display_name = child.text
                if child.tag == 'scanCode':
                    scan_code = child.text
            print(f'{scan_code}: {display_name}')


def start_scanner(*tag_pairs):
    if len(tag_pairs) % 2 > 0:
        raise IOError('Must have an even number of arguments of the form [tag name] [tag value]')
    tags = {tag_pairs[i]: tag_pairs[i+1] for i in range(0, len(tag_pairs), 2)} if tag_pairs else []
    with BrokerContext() as broker:
        key = broker.create_scanner(tags, on_scanner_data)
        try:
            while True:
                time.sleep(1)
        finally:
            broker.cancel_scanner(key)


def main():
    commands = {
        'scan': start_scanner,
        'params': get_scanner_params,
        'types': get_scan_types
    }
    parser = Parser()
    parser.allow_additional_args()
    args = parser.parse_args()

    added = args.additional
    command = commands[added[0]]
    command(*added[1:])


if __name__ == '__main__':
    main()
