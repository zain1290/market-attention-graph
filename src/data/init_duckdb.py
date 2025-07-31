import duckdb

# Connect to DuckDB file
con = duckdb.connect("market_attention.duckdb")

# Create schema
con.execute("""
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT,
    price DOUBLE,
    quantity DOUBLE,
    timestamp TIMESTAMP,
    PRIMARY KEY (ticker, price, timestamp)
)
""")

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
    ticker TEXT,
    PRIMARY KEY (article_id, ticker)
)
""")

# indexes help the live JOINs
con.execute("""
CREATE INDEX IF NOT EXISTS idx_price_tk_ts   ON prices(ticker, timestamp);
CREATE INDEX IF NOT EXISTS idx_news_ts ON news_articles(timestamp);
CREATE INDEX IF NOT EXISTS idx_mention_tk    ON ticker_mentions(ticker);
""")

con.execute("ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS sentiment DOUBLE")

con.close()

print("DuckDB initialized: market_attention.duckdb")
