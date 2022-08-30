from request import Request
import pandas_datareader as pdr


def fetch_yahoo(request: Request):
    data_frames = []
    for symbol in request.symbols:
        data_frames.append(pdr.get_data_yahoo(symbol, start=request.start, end=request.end))
    return data_frames
