import networkx as nx
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from matplotlib import pyplot as plt
from streamlit_autorefresh import st_autorefresh
from pathlib import Path

st_autorefresh(interval=60000, key="data_refresh")
st.set_page_config(layout="wide")

# --- Neon Dark Theme CSS ---
st.markdown("""
<style>
    /* Background and base text */
    body, .stApp {
        background-color: #0d1025;
        color: #FFFFFF;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111936 !important;
        border-right: 1px solid #1e2746;
    }

    /* Widget labels */
    section[data-testid="stSidebar"] label,
    .st-af, .st-cg {
        color: #FFFFFF !important;
    }

    /* Plot font */
    .js-plotly-plot .main-svg {
        font-family: 'Segoe UI', sans-serif;
    }
    
    div[data-testid="stDataFrame"] {
        border-radius: 16px;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.08);
        background-color: #111936;
        padding:16px;
        overflow-x:auto;
        display: flex;
        justify-content: center;
        max-height: 400px;
    }
    
    div[data-testid="stPlotlyChart"] > div {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.08);
    background-color: #111936;
    }
    
    .element-container img {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.08);
        background-color: #111936;
        height: 400px;
        padding: 20px 10px 20px 10px;
    }
    
    /* Sidebar header */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #48cae4 !important;
    }
    
    /* Selectbox styling */
    div[data-baseweb="select"] {
        background-color: #0d1025 !important;
        border: 2px solid #48cae4 !important;
        border-radius: 10px !important;
    }
    
    /* Radio buttons */
    div[data-testid="stRadio"] > div {
        gap: 0.5rem;
    }
    
</style>
""", unsafe_allow_html=True)

# --- Sidebar Filters ---
st.sidebar.title("Market Attention Dashboard")
TICKERS = ["GOOGL", "AAPL", "AMZN", "NVDA", "MSFT", "BTC", "XRP"]
ticker = st.sidebar.selectbox("Select Ticker", TICKERS)
hours = st.sidebar.radio("Time Window (hours)", [1, 3, 6, 12, 24], index=2)
since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
since_time = pd.Timestamp(since_time).tz_localize(None)

# --- DB Connection ---
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRICES_FILE = DATA_DIR / "prices.parquet"
NEWS_FILE = DATA_DIR / "news_articles.parquet"
MENTIONS_FILE = DATA_DIR / "ticker_mentions.parquet"


col1,col2 = st.columns([0.7,0.3])

df_price = pd.read_parquet(PRICES_FILE)
df_price["timestamp"] = pd.to_datetime(df_price["timestamp"])
df_price = df_price[
    (df_price["ticker"] == ticker) &
    (df_price["timestamp"] > since_time)
]
df_price = df_price[["timestamp", "price"]].rename(columns={"timestamp": "time"}).set_index("time")

df_mentions = pd.read_parquet(MENTIONS_FILE)
df_articles = pd.read_parquet(NEWS_FILE)
df_mentions = df_mentions[df_mentions["ticker"] == ticker]
df = df_mentions.merge(df_articles, on="article_id")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df[df["timestamp"] > since_time]
df["minute"] = df["timestamp"].dt.floor("min")
df_mentions = df.groupby(pd.Grouper(key="minute", freq="10min")).size().reset_index(name="mentions").rename(columns={"minute": "time"}).set_index("time")

# --- Combine & Plot ---
df_combined = df_price.join(df_mentions, how="outer").sort_index().ffill()
max_mentions = df_combined["mentions"].max()

fig = go.Figure()
# Price Line
fig.add_trace(go.Scatter(
    x=df_combined.index, y=df_combined["price"],
    name="Price", yaxis="y1",
    line=dict(color="#48cae4", width=3),
))
# Mentions Line
fig.add_trace(go.Bar(
    x=df_combined.index,
    y=df_combined["mentions"],
    name="Mentions",
    yaxis="y2",
    marker=dict(
        color="#E040FB",
        line=dict(color="#E040FB", width=0.1)
    ),
    opacity=0.6,
    width=60000
))
fig.update_layout(
    barmode="overlay",
    bargap=0.8,
    paper_bgcolor="#111936", plot_bgcolor="#111936",
    # font=dict(color="#ADB5BD"),

    xaxis=dict(
        title=dict(text="Time", font=dict(color="#FFFFFF")),
        tickfont=dict(color="#FFFFFF"),
        showgrid=True
    ),

    yaxis=dict(
        title=dict(text="Price", font=dict(color="#FFFFFF")),
        tickfont=dict(color="#FFFFFF")
    ),

    yaxis2=dict(
        title=dict(text="Mentions", font=dict(color="#FFFFFF")),
        tickfont=dict(color="#FFFFFF"),
        overlaying="y",
        side="right",
        showgrid=False,
        range=[0, max_mentions * 1.5]
    ),

    title=dict(text=f"{ticker} - Price & Mention Volume", x=0.12, y=0.94, font=dict(color="#ADB5BD", size=16)),
    legend=dict(x=0.98, y=1.125, orientation="h", xanchor="right"),

    height=400,
    width=800,
    margin=dict(t=50, b=20, l=20, r=20)
)
with col1:
    st.plotly_chart(fig, use_container_width=True)

df_mentions = pd.read_parquet(MENTIONS_FILE)
article_ids = df_mentions[df_mentions["ticker"] == ticker]["article_id"].unique()
df_related = df_mentions[df_mentions["article_id"].isin(article_ids)]
df_edges = df_related[df_related["ticker"] != ticker]
df_edges = df_edges.groupby("ticker").size().reset_index(name="weight")
df_edges["source"] = ticker
df_edges = df_edges.rename(columns={"ticker": "target"})

with col2:
    # Draw the network graph
    G = nx.from_pandas_edgelist(df_edges, source="source", target="target", edge_attr="weight")
    pos = nx.spring_layout(G)

    # Normalize edge widths based on weight
    weights = [d["weight"] for _, _, d in G.edges(data=True)]
    max_weight = max(weights) if weights else 1
    widths = [2 + 6 * (w / max_weight) for w in weights]  # edge thickness 2–8 px

    # Draw figure
    fig, ax = plt.subplots(figsize=(4, 4), facecolor='#111936')  # match background
    ax.set_facecolor('#111936')
    ax.axis('off')
    ax.set_title("Co-Mention Graph", x=0.5, y=1.1, size=11,color="#ADB5BD", fontweight="bold")

    nx.draw_networkx(
        G, pos, ax=ax,
        node_color='#48cae4',
        edge_color='#E040FB',
        width=widths,
        node_size=1100,
        font_size=9,
        font_color='#000000'
    )
    st.pyplot(plt)

col3, col4 = st.columns([0.3, 0.7])

df_all_prices = pd.read_parquet(PRICES_FILE)
df_latest = (
    df_all_prices.sort_values("timestamp")
    .groupby("ticker").tail(1)[["ticker", "price"]]
    .sort_values("ticker")
)

with col3:
    styled_df = (df_latest.style.format({"price": "{:.2f}"}).set_table_styles([
            {'selector': 'thead',
             'props': [('color', '#48cae4'), ('background-color', '#111936'), ("border", "2px solid #2a2e45"), ('font-weight', 'bold')]},
            {'selector': 'tbody td',
             'props': [('color', '#FFFFFF'), ('background-color', '#111936'), ("border", "2px solid #2a2e45"), ('padding', '5px 20px'), ('text-align', 'center')]},
            {'selector': 'tbody tr:nth-child(even)',
             'props': [('background-color', '#ADB5BD'), ('font-weight', 'bold')]},
    ]).hide(axis='index'))

    html = styled_df.to_html()
    st.markdown(
        f"""
        <div style="
            background-color:#111936;
            padding:16px;
            border-radius:16px;
            box-shadow: 0 0 20px rgba(0,255,255,0.08);
            overflow-x:auto;
            display: flex;
            justify-content: center;
            max-height: 400px;
        ">
            <div style=" color: #ADB5BD; font-weight: bold; text-align: center; padding: 1px">Live Prices<div/>
            <div>{html}<div/>
        """,
        unsafe_allow_html=True
    )

df_mentions_total = pd.read_parquet(MENTIONS_FILE)
df_mentions_total = df_mentions_total.groupby("ticker").size().reset_index(name="mentions").sort_values("mentions", ascending=False)

# Plot the bar chart
bar_fig = go.Figure(data=[
    go.Bar(
        x=df_mentions_total["ticker"],
        y=df_mentions_total["mentions"],
        marker=dict(color='#48cae4')
    )
])
bar_fig.update_layout(
    barmode='stack',
    paper_bgcolor="#111936",
    plot_bgcolor="#111936",
    font=dict(color="#FFFFFF"),
    xaxis_title="Ticker",
    yaxis_title="Total Mentions",
    height=377,
    title=dict(
        text="Total Mentions Per Ticker",
        x=0.37,
        y=0.94,
        font=dict(color="#ADB5BD", size=16)
    ),
    margin=dict(t=50, b=20, l=20, r=20),
    showlegend=False
)

with col4:
    st.plotly_chart(bar_fig, use_container_width=True)

df_mentions = pd.read_parquet(MENTIONS_FILE)
df_articles = pd.read_parquet(NEWS_FILE)

recent_articles = df_mentions[df_mentions["ticker"] == ticker]
recent_articles = recent_articles.merge(df_articles, on="article_id")
recent_articles = recent_articles[recent_articles["timestamp"] > since_time]
recent_articles = recent_articles.sort_values("timestamp", ascending=False)
df_news = recent_articles[["title", "timestamp"]].drop_duplicates().head(10)
df_news["title"] = df_news["title"].apply(
    lambda x: f'<div title="{x}">{x}</div>'
)

styled_df_articles = (
    df_news.style.set_table_styles([
        {"selector": "thead", "props": [("background-color", "#111936")]},
        {"selector": "thead th", "props": [("color", "#48cae4"), ("border", "2px solid #2a2e45"), ("padding", "8px")]},
        {"selector": "td", "props": [("color", "#FFFFFF"), ("background-color", "#111936"), ("border", "2px solid #2a2e45"), ("padding", "8px"),
            ("white-space", "nowrap"), ("text-overflow", "ellipsis"), ("overflow", "hidden"), ("max-width", "850px")]},
        {"selector": "tr:nth-child(even)", "props": [("background-color", "#0d1025")]},
        {"selector": "table", "props": [("border-collapse", "collapse"), ("width", "100%")]}
    ]).hide(axis='index')
)

html = styled_df_articles.to_html(escape=False)

st.markdown(
    f"""
    <div style="
        background-color:#111936;
        padding:32px;
        border-radius:16px;
        box-shadow: 0 0 20px rgba(0,255,255,0.08);
        overflow-x:auto;
        display: flex;
        justify-content: center;
        max-height: 400px;
    "> 
        <div style=" color: #ADB5BD; font-weight: bold;">Top 10 Recent Articles<div/>
        {html}
    """,
    unsafe_allow_html=True
)
