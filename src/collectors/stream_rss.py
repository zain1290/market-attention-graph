import asyncio
import feedparser
import duckdb
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import time
import pandas as pd
from src.data.database_utils import publish_news

RSS_FEEDS = [
    "https://finance.yahoo.com/rss/",
    "https://www.investing.com/rss/news_301.rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.marketwatch.com/rss/topstories",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.bloomberg.com/feed/podcast/etf-report.xml",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml"
]
COMPANY_NAMES = {
    "Google": "GOOGL",
    "Apple": "AAPL",
    "Amazon": "AMZN",
    "Nvidia": "NVDA",
    "Microsoft": "MSFT",
    "Bitcoin": "BTC",
    "XRP": "XRP"
}
keywords = [key for key in COMPANY_NAMES.keys()]

def hash_id(text):
    return hashlib.sha256(text.encode()).hexdigest()

async def poll_rss():
    print(f"[{datetime.utcnow()}] Polling RSS feeds...")
    total = 0

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            timestamp = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)
            article_id = hash_id(url)

            mentions = [
                ticker for name, ticker in COMPANY_NAMES.items()
                if (name.lower() in title.lower()) or (ticker.lower() in title.lower())
            ]

            if mentions:
                await publish_news(article_id, title, timestamp, mentions)
                total += 1

    print(f"RSS [+] Stored {total} matched articles.")

async def main():
    while True:
        await poll_rss()
        time.sleep(900)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("RSS stream stopped.")
