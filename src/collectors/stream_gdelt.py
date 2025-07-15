import aiohttp
import asyncio
import hashlib
import duckdb
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd

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
print(keywords)
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&maxrecords=250&STARTDATETIME={start}&ENDDATETIME={end}&page={page}&format=json"
QUERY = "(" + " OR ".join(f'"{kw}"' for kw in keywords) + ")"
DB_PATH = (Path(__file__).resolve().parent.parent / "data" / "market_attention.duckdb")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def hash_id(text):
    return hashlib.sha256(text.encode()).hexdigest()

async def fetch_news():
    all_articles, page = [], 1
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start = now - timedelta(hours=1)
    async with aiohttp.ClientSession() as session:
        while True:
            url = GDELT_URL.format(query=quote_plus(QUERY), page = page, start=start.strftime("%Y%m%d%H%M%S"), end=now.strftime("%Y%m%d%H%M%S"))
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(f"[{datetime.utcnow()}] GDELT fetch failed: {resp.status}")
                    return []
                data = await resp.json()
                rows = data.get("articles", [])
                all_articles.extend(rows)

            if len(rows) <= 250:
                break
            page += 1

    return all_articles

def save_to_db(con, articles):

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

    for art in articles:
        article_id = hash_id(art["url"])
        title = art.get("title", "")
        published = art.get("seendate")
        clean = published.replace("T", "").rstrip("Z")
        timestamp = datetime.strptime(clean, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)

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
            """, (article_id, title, timestamp))
        except duckdb.ConstraintException:
            continue

        for ticker in mentions:
            con.execute("""
                INSERT INTO ticker_mentions (article_id, ticker)
                VALUES (?, ?)
            """, (article_id, ticker))


async def main():
    con = duckdb.connect(DB_PATH)

    while True:
        print(f"[{datetime.utcnow()}] 🔎 Polling GDELT...")
        articles = await fetch_news()
        if articles:
            print(f"[+] {len(articles)} articles fetched.")
            save_to_db(con, articles)
        else:
            print("[-] No articles found.")
        await asyncio.sleep(900)  # 15 min

if __name__ == "__main__":
    try:
        asyncio.run(main())

        # con = duckdb.connect(DB_PATH)
        # pd.set_option("display.max_rows", None)  # show all when printing
        # df = con.execute("SELECT * FROM news_articles ORDER BY timestamp").fetchdf()
        # print(df)

        # con.execute("""
        #     DELETE FROM news_articles;
        #     DELETE FROM ticker_mentions;
        # """)
    except KeyboardInterrupt:
        print("Stream stopped by user")