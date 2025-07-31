import asyncio
import os

import pandas as pd
import redis
import websockets
import json
from datetime import datetime
import csv
from pathlib import Path
import duckdb
from src.data.database_utils import publish_price

SYMBOLS = ["btcusdt", "xrpusdt"]
BINANCE_WS_URL = "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/xrpusdt@trade"

# stream trades and write them to a database
async def stream_prices():
    async with websockets.connect(BINANCE_WS_URL) as ws:
        while True:
            msg = await ws.recv()
            wrapper = json.loads(msg)
            trade = wrapper["data"]

            timestamp = datetime.utcfromtimestamp(trade['T'] / 1000)
            ts = f"{timestamp:%F %T}"
            ticker = trade["s"][:-4]
            price = float(trade["p"])
            quantity = float(trade["q"])
            print(price)

            await publish_price(ticker, price, quantity, ts)

if __name__ == '__main__':
    try:
        asyncio.run(stream_prices())
    except KeyboardInterrupt:
        print("Stream stopped by user")