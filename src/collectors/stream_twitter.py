import asyncio
import time
import hashlib
import duckdb
from datetime import datetime, timezone
from pathlib import Path
from random import randint

import pandas as pd
from duckdb.duckdb import execute
from twikit import Client, TooManyRequests, errors

# CONFIGURATION
MIN_FOLLOWERS = 10000
COMPANY_NAMES = {
    "Google": "GOOGL",
    "Apple": "AAPL",
    "Amazon": "AMZN",
    "Nvidia": "NVDA",
    "Microsoft": "MSFT",
    "Bitcoin": "BTC",
    "Ripple": "XRP"
}
keywords = [key for key in COMPANY_NAMES.keys()]
QUERY = " OR ".join(f'"{kw}"' for kw in keywords)

DB_PATH = (Path(__file__).resolve().parent.parent / "data" / "market_attention.duckdb")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def hash_id(text):
    return hashlib.sha256(text.encode()).hexdigest()

async def authenticate():
    client = Client(language='en-US')
    client.load_cookies("cookies.json")
    await client._get_guest_token()
    return client

async def latest_tweets(client: Client):
    try:
        return await client.search_tweet(QUERY, "Latest", count=100)
    except errors.NotFound:
        await client._get_guest_token()
        return await client.search_tweet(QUERY, "Latest", count=100)

def save_to_db(con, tweets):
    con.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            article_id TEXT PRIMARY KEY,
            title TEXT,
            timestamp TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS ticker_mentions (
            article_id TEXT,
            ticker TEXT
        )
    """)

    for tweet in tweets:
        if tweet.user.followers_count < MIN_FOLLOWERS:
            continue

        tweet_id = hash_id(tweet.id)
        title = tweet.text
        published = tweet.created_at
        timestamp = datetime.strptime(published, "%a %b %d %H:%M:%S %z %Y")

        mentions = [
            ticker for name, ticker in COMPANY_NAMES.items()
            if (name.lower() in title.lower()) or (ticker.lower() in title.lower())
        ]

        if not mentions:
            continue

        try:
            con.execute("""
                INSERT INTO news_articles (article_id, title, timestamp)
                VALUES (?, ?, ?)
            """, (tweet_id, title, timestamp))
        except duckdb.ConstraintException:
            continue

        for ticker in mentions:
            con.execute("""
                INSERT INTO ticker_mentions (article_id, ticker)
                VALUES (?, ?)
            """, (tweet_id, ticker))

async def main_loop():
    con = duckdb.connect(DB_PATH)
    client = await authenticate()
    tweet_count = 0

    while True:
        try:
            # tweets, cursor = await poll_tweets(client, cursor)
            tweets = await latest_tweets(client)
        except TooManyRequests as e:
            reset_time = datetime.fromtimestamp(e.rate_limit_reset)
            print(f"[{datetime.utcnow()}] Rate limit hit. Waiting until {reset_time}")
            wait = (reset_time - datetime.utcnow()).total_seconds()
            print(f"[{datetime.utcnow()}] Sleeping for {int(wait)} s")
            await asyncio.sleep(wait)
            continue

        if tweets:
            save_to_db(con, tweets)
            tweet_count += len(tweets)
            print(f"[{datetime.utcnow()}] Stored {len(tweets)} tweets (total {tweet_count} tweets)")
        else:
            print(f"[{datetime.utcnow()}] No tweets returned")

        await asyncio.sleep(20)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
        # con = duckdb.connect(DB_PATH)
        # pd.set_option("display.max_rows", None)  # show all when printing
        # df = con.execute("SELECT ticker, COUNT(ticker) AS mentions FROM ticker_mentions GROUP BY ticker ORDER BY mentions").fetchdf()
        # print(df)

        # con.execute("""
        #     DELETE FROM news_articles;
        #     DELETE FROM ticker_mentions;
        # """)
    except KeyboardInterrupt:
        print("Twitter stream stopped.")
