import os, asyncio, duckdb, redis.asyncio as redis
from dotenv import load_dotenv
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

load_dotenv()
r   = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
DB  = Path(__file__).resolve().parent / "market_attention.duckdb"
con = duckdb.connect(DB, read_only=False)
con.execute("PRAGMA threads=4")

GROUP = "writer_grp"
PRICE_STREAM  = "prices_stream"
NEWS_STREAM   = "news_stream"
analyzer = SentimentIntensityAnalyzer()

def get_sentiment(text):
    return analyzer.polarity_scores(text)["compound"]

async def ensure_groups():
    for stream in (PRICE_STREAM, NEWS_STREAM):
        try:
            await r.xgroup_create(stream, GROUP, id="$", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e): raise

async def process_prices(messages):
    for _, m in messages:
        print(m)

    rows = {(
        m["ticker"], float(m["price"]), float(m["quantity"]), m["timestamp"]
    ) for _, m in messages}
    rows = list(rows)
    print(rows)
    print(type(rows))

    con.executemany("""
        INSERT INTO prices (ticker, price, quantity, timestamp) VALUES (?, ?, ? ,?) 
        ON CONFLICT DO NOTHING
    """, rows)

async def process_news(messages):
    articles, mentions = [], []
    for _, m in messages:
        if m['table'] == 'article':
            sentiment = get_sentiment(m['title'])
            articles.append((m['article_id'], m['title'], m['timestamp'], sentiment))
        else:
            mentions.append((m['article_id'], m['ticker']))
    if not articles and not mentions:
        return

    con.execute("BEGIN")
    if articles:
        con.executemany("""
            INSERT INTO news_articles (article_id, title, timestamp, sentiment) VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
        """, articles)
    if mentions:
        con.executemany("""
            INSERT INTO ticker_mentions (article_id, ticker) VALUES (?, ?)
            ON CONFLICT DO NOTHING
        """, mentions)
    con.execute("COMMIT")

async def consume(stream, handler):
    while True:
        resp = await r.xreadgroup(GROUP, "writer", {stream: ">"}, count=100, block=1000)
        if resp:
            msgs = [(m_id, {k: v for k, v in m.items()}) for m_id, m in resp[0][1]]
            await  handler(msgs)
            await r.xack(stream, GROUP, *[mid for mid, _ in msgs])

async def snapshot_to_parquet():
    while True:
        try:
            con.execute("COPY (SELECT * FROM prices) TO 'data/prices.parquet' (FORMAT PARQUET)")
            con.execute("COPY (SELECT * FROM news_articles) TO 'data/news_articles.parquet' (FORMAT PARQUET)")
            con.execute("COPY (SELECT * FROM ticker_mentions) TO 'data/ticker_mentions.parquet' (FORMAT PARQUET)")
        except Exception as e:
            print("Parquet export error:", e)
        await asyncio.sleep(1)  # export every second

async def main():
    await ensure_groups()
    await asyncio.gather(
        consume(PRICE_STREAM, process_prices),
        consume(NEWS_STREAM,  process_news),
        snapshot_to_parquet()
    )

if __name__ == "__main__":
    asyncio.run(main())
