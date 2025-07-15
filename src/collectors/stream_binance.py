import asyncio
import pandas as pd
import websockets
import json
from datetime import datetime
import csv
from pathlib import Path
import duckdb

# database connection
DB_PATH = (Path(__file__).resolve().parent.parent/"data"/"market_attention.duckdb")
con = duckdb.connect(DB_PATH)

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

            con.execute("""
                INSERT INTO prices (ticker, price, quantity, timestamp)
                VALUES (?, ?, ?, ?)
                """, (ticker, float(price), float(quantity), ts))

if __name__ == '__main__':
    try:
        asyncio.run(stream_prices())
        # con = duckdb.connect(DB_PATH)
        # pd.set_option("display.max_rows", None)  # show all when printing
        # df = con.execute("SELECT * FROM prices ORDER BY timestamp").fetchdf()
        # print(df)

        # con.execute("""
        #     DELETE FROM prices;
        # """)
    except KeyboardInterrupt:
        print("Stream stopped by user")