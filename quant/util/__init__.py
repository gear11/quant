import argparse
import logging


class Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument('--debug', dest='debug', action='store_const', const=True, default=False,
                          help='Log at debug level')
        self.add_argument('--info', dest='info', action='store_const', const=True, default=False,
                          help='Log at info level')

    def parse_args(self, *args, **kwargs):
        parsed = super().parse_args(*args, **kwargs)
        level = logging.DEBUG if parsed.debug else logging.INFO if parsed.info else logging.WARNING
        logging.basicConfig(level=level)
        logging.getLogger('root').setLevel(level)
        return parsed

    def ignore_args(self):
        self.add_argument('ignore', nargs='+', help='Ignored arguments')
        return self
