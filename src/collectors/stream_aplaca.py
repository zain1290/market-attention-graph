import os
import json
import asyncio
import pandas as pd
import websockets
from dotenv import load_dotenv
from datetime import datetime, timezone
import csv
from pathlib import Path
import duckdb

# database connection
DB_PATH = (Path(__file__).resolve().parent.parent/"data"/"market_attention.duckdb")
con = duckdb.connect(DB_PATH)

# Load credentials
load_dotenv()
ALPACA_KEY_ID = os.getenv("ALPACA_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

STOCKS = ["AAPL", "GOOGL", "AMZN", "MSFT", "NVDA"]
ALPACA_WS_URL = "wss://stream.data.alpaca.markets/v2/iex"

async def stream_alpaca():
    async with websockets.connect(ALPACA_WS_URL) as ws:
        # authentication
        auth_msg = {
            "action": "auth",
            "key": ALPACA_KEY_ID,
            "secret": ALPACA_SECRET_KEY
        }
        await ws.send(json.dumps(auth_msg))
        response = await ws.recv()
        sub_msg = {
            "action": "subscribe",
            "trades": STOCKS
        }
        await ws.send(json.dumps(sub_msg))

        # stream data
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)

                for entry in data:
                    if entry.get("T") == "t":
                        timestamp = entry["t"]
                        ticker = entry["S"]
                        price = entry["p"]
                        quantity = entry["s"]
                        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%F %T")

                        con.execute("""
                            INSERT INTO prices (ticker, price, quantity, timestamp)
                            VALUES (?, ?, ?, ?)
                            """, (ticker, float(price), float(quantity), ts))

            except websockets.exceptions.ConnectionClosed:
                await asyncio.sleep(5)
                return await stream_alpaca()

if __name__ == "__main__":
    try:
        asyncio.run(stream_alpaca())
        # con = duckdb.connect(DB_PATH)
        # pd.set_option("display.max_rows", None)  # show all when printing
        # df = con.execute("SELECT * FROM prices ORDER BY timestamp").fetchdf()
        # print(df)

        # con.execute("""
        #     DELETE FROM prices;
        # """)
    except KeyboardInterrupt:
        print("Stream stopped by user.")
