import asyncio
import redis.asyncio as redis, os
from dotenv import load_dotenv

load_dotenv()
r   = redis.from_url(os.getenv("REDIS_URL"))
PRICE_STREAM  = "prices_stream"
NEWS_STREAM = "news_stream"

async def publish_price(ticker, price, quantity, timestamp):
    await r.xadd(PRICE_STREAM, {
        "ticker": ticker,
        "price": float(price),
        "quantity": float(quantity),
        "timestamp": timestamp
    })

async def publish_news(article_id, title, timestamp, tickers):
    await r.xadd(NEWS_STREAM, {
        "table" : "article",
        "article_id": article_id,
        "title": title,
        "timestamp": timestamp.isoformat()
    })

    for ticker in tickers:
        await r.xadd(NEWS_STREAM, {
            "table" : "mention",
            "article_id": article_id,
            "ticker": ticker
        })