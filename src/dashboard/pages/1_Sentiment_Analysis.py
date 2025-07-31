import streamlit as st
import pandas as pd
import altair as alt
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

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
    
    div[data-testid="stVegaLiteChart"] > div {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.08);
        background-color: #111936;
        padding: 15px 10px 0px 10px;
    }
    
    .element-container img {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.08);
        background-color: #111936;
        height: 500px;
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
    
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #E040FB !important;  /* Bootstrap blue */
        color: white !important;
        border-radius: 6px;
        font-weight: bold;
    }

</style>
""", unsafe_allow_html=True)

# --- Auto-refresh & Layout ---
st_autorefresh(interval=60000, key="refresh")
st.set_page_config(layout="wide")

# --- Load Data ---
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
NEWS_FILE = DATA_DIR / "news_articles.parquet"
MENTIONS_FILE = DATA_DIR / "ticker_mentions.parquet"

mentions_df = pd.read_parquet(MENTIONS_FILE)
articles_df = pd.read_parquet(NEWS_FILE)

df = mentions_df.merge(
    articles_df[['article_id', 'sentiment', 'timestamp']],
    on='article_id',
    how='inner'
)
df = df[df['sentiment'].notnull()]
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['minute'] = df['timestamp'].dt.floor('5min')

# --- Sidebar ---
with st.sidebar:
    st.sidebar.title("Sentiment Analysis")
    tickers = ["GOOGL", "AAPL", "AMZN", "NVDA", "MSFT", "BTC", "XRP"]
    selected_tickers = st.multiselect("Select Tickers", tickers, default=tickers[:3])
    time_window = st.radio("Time Window (hours)", [1, 3, 6, 12, 24], index=2)
    sentiment_category = st.selectbox("Sentiment Type", ["All", "Positive", "Neutral", "Negative"])

# --- Filtering ---
cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window)
cutoff = pd.Timestamp(cutoff).tz_localize(None)
df = df[df['timestamp'] > cutoff]

if sentiment_category != "All":
    if sentiment_category == "Positive":
        df = df[df['sentiment'] > 0.2]
    elif sentiment_category == "Neutral":
        df = df[df['sentiment'].between(-0.2, 0.2)]
    elif sentiment_category == "Negative":
        df = df[df['sentiment'] < -0.2]

df = df[df['ticker'].isin(selected_tickers)]

# --- Aggregations ---
sentiment_avg = df.groupby(['minute', 'ticker'])['sentiment'].mean().reset_index()
sentiment_avg['sentiment'] = (
    sentiment_avg
        .sort_values(['ticker', 'minute'])
        .groupby('ticker')['sentiment']
        .transform(lambda s: s.rolling(window=15, min_periods=1).mean())
)
mention_counts = df.groupby(['minute', 'ticker']).size().reset_index(name='count')
merged = pd.merge(sentiment_avg, mention_counts, on=['minute', 'ticker'])

# --- Layout Row 1: Time Series Charts ---
col1, col2 = st.columns([1, 1])
with col1:
    chart = alt.Chart(merged).mark_line().encode(
        x='minute:T',
        y='sentiment:Q',
        color='ticker:N'
    ).properties(
    height=300,
    width=700,
    title={
        "text": "Sentiment Over Time",
        "anchor": "middle",
        "fontSize": 16,
        "color": "#ADB5BD"
    },
    background="#111936"
    ).configure_axis(
        labelColor="#FFFFFF",
        titleColor="#FFFFFF"
    ).configure_legend(
        labelColor="#ADB5BD",
        titleColor="#FFFFFF"
    )

    st.altair_chart(chart, use_container_width=True)

with col2:
    mention_chart = alt.Chart(merged).mark_area(opacity=0.5).encode(
        x='minute:T',
        y='count:Q',
        color='ticker:N'
    ).properties(
    height=300,
    width=700,
    title={
        "text": "Mentions Over Time",
        "anchor": "middle",
        "fontSize": 16,
        "color": "#ADB5BD"
    },
    background="#111936"
    ).configure_axis(
        labelColor="#FFFFFF",
        titleColor="#FFFFFF"
    ).configure_legend(
        labelColor="#ADB5BD",
        titleColor="#FFFFFF"
    )

    st.altair_chart(mention_chart, use_container_width=True)

# --- Layout Row 2: Correlation Heatmap + Summary Table ---
col3, col4 = st.columns([5, 4])
with col3:
    pivot_df = df.pivot_table(index='minute', columns='ticker', values='sentiment')
    corr = pivot_df.corr(method='pearson')
    fig, ax = plt.subplots(figsize=(6, 5))

    if not corr.empty:
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5, ax=ax, cbar_kws={'label': 'Correlation'}, annot_kws={"color": "black"})
    else:
        empty_corr = pd.DataFrame([[0]], columns=["No data"], index=["No data"])
        sns.heatmap(
            empty_corr, annot=True, cmap='Greys', fmt="", cbar=False,
            linewidths=0.5, ax=ax, annot_kws={"color": "white"}
        )
        ax.text(0.5, 0.5, 'No Data Available', color='white', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, fontweight='bold')

    ax.set_facecolor("#111936")
    fig.patch.set_facecolor("#111936")
    ax.set_title("Ticker Sentiment Correlation", x=0.5, y=1.05, color="#ADB5BD",
                 font='Calibri', fontweight="bold", size=16)
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')

    for label in ax.get_xticklabels():
        label.set_color('white')
    for label in ax.get_yticklabels():
        label.set_color('white')

    if not corr.empty:
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.label.set_color('white')
        cbar.ax.tick_params(colors='white')

    st.pyplot(fig, clear_figure=True)


with col4:
    summary = df.groupby("ticker").agg(
        avg_sentiment=('sentiment', 'mean'),
        mentions=('ticker', 'count')
    ).reindex(tickers).reset_index().fillna(0)

    styled_summary = (summary.style.format({"price": "{:.2f}"}).set_table_styles([
            {'selector': 'thead',
             'props': [('color', '#48cae4'), ('background-color', '#111936'), ("border", "2px solid #2a2e45"), ('font-weight', 'bold')]},
            {'selector': 'tbody td',
             'props': [('color', '#FFFFFF'), ('background-color', '#111936'), ("border", "2px solid #2a2e45"), ('padding', '5px 20px'), ('text-align', 'center')]},
            {'selector': 'tbody tr:nth-child(even)',
             'props': [('background-color', '#ADB5BD'), ('font-weight', 'bold')]},
    ]).hide(axis='index'))

    html1 = styled_summary.to_html()

    st.markdown(
        f"""
            <div style="
                background-color:#111936;
                padding:80px 0px;
                border-radius:16px;
                box-shadow: 0 0 20px rgba(0,255,255,0.08);
                overflow-x:auto;
                display: flex;
                justify-content: center;
                height: 500px;
            ">
                <div style=" color: #ADB5BD; font-weight: bold; text-align: center; padding: 1px">Average Sentiment Summary<div/>
                <div>{html1}<div/>
            """,
        unsafe_allow_html=True
    )

    st.write("")

signal_df = merged.groupby("ticker").agg(
    latest_sentiment=("sentiment", "last"),
    sentiment_delta=("sentiment", lambda x: x.iloc[-1] - x.iloc[0]),
).reset_index()
signal_df = signal_df[abs(signal_df["sentiment_delta"] > 0.4)].sort_values("sentiment_delta", ascending=False)

styled_signal_df = (signal_df.style.format({"price": "{:.2f}"}).set_table_styles([
        {'selector': 'thead',
         'props': [('color', '#48cae4'), ('background-color', '#111936'), ("border", "2px solid #2a2e45"), ('font-weight', 'bold')]},
        {'selector': 'tbody td',
         'props': [('color', '#FFFFFF'), ('background-color', '#111936'), ("border", "2px solid #2a2e45"), ('padding', '5px 20px'), ('text-align', 'center')]},
        {'selector': 'tbody tr:nth-child(even)',
         'props': [('background-color', '#ADB5BD'), ('font-weight', 'bold')]},
]).hide(axis='index'))

html2 = styled_signal_df.to_html()

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
            <div style=" color: #ADB5BD; font-weight: bold; text-align: center; padding: 1px">Sudden Sentiment Shifts<div/>
            <div>{html2}<div/>
        """,
    unsafe_allow_html=True
)


