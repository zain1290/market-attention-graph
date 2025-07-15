import os, asyncio, orjson, duckdb, redis.asyncio as redis
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
r   = redis.from_url(os.getenv("REDIS_URL"))
DB  = Path(__file__).resolve().parent / "data" / "market_attention.duckdb"
con = duckdb.connect(DB, read_only=False)
con.execute("PRAGMA threads=4")

GROUP = "writer_grp"
PRICE_STREAM  = "prices_stream"
NEWS_STREAM   = "news_stream"

async def ensure_groups():
    for stream in (PRICE_STREAM, NEWS_STREAM):
        try:
            await r.xgroup_create(stream, GROUP, id="$", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e): raise

async def process_prices(messages):
    rows = [(
        m['ticker'], float(m['price']), float(m['quantity']), m['timestamp']
    ) for _, m in messages]

    con.execute("""
        INSERT INTO prices VALUES (?, ?, ? ,?) 
        ON CONFLICT DO NOTHING
    """, rows)

async def process_news(messages):
    articles, mentions = [], []
    for _, m in messages:
        if m['table'] == 'article':
            articles.append((m['article_id'], m['text'], m['timestamp']))
        else:
            mentions.append((m['article_id'], m['ticker']))
    if not articles and not mentions:
        return

    con.execute("BEGIN")
    if articles:
        con.executemany("""
            INSERT INTO news_articles VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING
        """, articles)
    if mentions:
        con.executemany("""
            INSERT INTO news_mentions VALUES (?, ?)
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

async def main():
    await ensure_groups()
    await asyncio.gather(
        consume(PRICE_STREAM, process_prices),
        consume(NEWS_STREAM,  process_news)
    )

if __name__ == "__main__":
    asyncio.run(main())
