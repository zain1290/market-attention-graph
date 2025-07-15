from dotenv import load_dotenv
import os
import asyncpraw
import asyncio
from datetime import datetime
import re


# load the env file containing my reddit api credentials
load_dotenv()

# access the credentials
client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
user_agent = os.getenv("USER_AGENT")

# safe preview
print("Reddit credentials loaded:", client_id[:4], "***")

TICKERS = {"GOOGL", "AAPL", "AMZN", "NVDA", "MSFT", "BTC", "XRP"}
SUBREDDITS = "personalfinance+stocks+wallstreetbets+investing+CryptoCurrency"

# checks if each new post in the subreddits contains a ticker in its text
async def stream_posts():

    # set up reddit client
    reddit = asyncpraw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

    subreddit = await reddit.subreddit("all")

    async for post in subreddit.stream.submissions(skip_existing=True):
        text = (post.title or "") + " " + (post.selftext or "")
        words = set(re.findall(r"\b[A-Z]{2,5}\b", text.upper()))
        matched = TICKERS & words

        if matched:
            print(f"[{datetime.utcnow()}] [{post.subreddit}] {post.title} ({post.id}) — matched: {matched}")

    await reddit.close()


# Run the stream
if __name__ == "__main__":
    try:
        asyncio.run(stream_posts())
    except KeyboardInterrupt:
        print("Stream stopped by user")
