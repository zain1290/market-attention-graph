import feedparser
import duckdb
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import time
import pandas as pd

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
DB_PATH = (Path(__file__).resolve().parent.parent / "data" / "market_attention.duckdb")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def hash_id(text):
    return hashlib.sha256(text.encode()).hexdigest()

def poll_rss(con):
    print(f"[{datetime.utcnow()}] Polling RSS feeds...")
    total = 0

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            timestamp = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)

            mentions = [
                ticker for name, ticker in COMPANY_NAMES.items()
                if (name.lower() in title.lower()) or (ticker.lower() in title.lower())
            ]
            if mentions:
                store_article(con, title, link, timestamp, mentions)
                total += 1

    print(f"[+] Stored {total} matched articles.")

def store_article(con, title, url, timestamp, mentions):
    article_id = hash_id(url)

    try:
        con.execute("""
            INSERT INTO news_articles (article_id, title, timestamp)
            VALUES (?, ?, ?)
        """, (article_id, title, timestamp))
    except duckdb.ConstraintException:
        return

    for ticker in mentions:
        con.execute("""
            INSERT INTO ticker_mentions (article_id, ticker)
            VALUES (?, ?)
        """, (article_id, ticker))


if __name__ == "__main__":
    con = duckdb.connect(DB_PATH)
    try:
        while True:
            poll_rss(con)
            time.sleep(900)

            # con = duckdb.connect(DB_PATH)
            # pd.set_option("display.max_rows", None)  # show all when printing
            # df = con.execute("SELECT * FROM news_articles ORDER BY timestamp").fetchdf()
            # print(df)

            # con.execute("""
            #     DELETE FROM news_articles;
            #     DELETE FROM ticker_mentions;
            # """)
    except KeyboardInterrupt:
        print("RSS stream stopped.")
