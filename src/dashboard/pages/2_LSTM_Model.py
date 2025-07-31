import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import LSTM, Dense, Input
from tensorflow.keras.losses import MeanSquaredError
from tensorflow.keras.models import Sequential, load_model

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

# Config & sidebar
st.set_page_config(page_title="LSTM Stock Return Predictor", layout="wide")

DATA_DIR      = Path(__file__).resolve().parents[2] / "data"
PRICES_FILE   = DATA_DIR / "prices.parquet"
MENTIONS_FILE = DATA_DIR / "ticker_mentions.parquet"
NEWS_FILE     = DATA_DIR / "news_articles.parquet"

TICKERS = ["GOOGL", "AAPL", "AMZN", "NVDA", "MSFT", "BTC", "XRP"]

st.sidebar.title("LSTM Model")
ticker      = st.sidebar.selectbox("Select Ticker", TICKERS, index=0)
st.sidebar.write("1 Hour Time Frame")
hours_back  = 1
retrain_now = st.sidebar.checkbox("Retrain model now")
since_time = (pd.Timestamp.utcnow() - pd.Timedelta(hours=hours_back)).tz_localize(None)

SEQ_LEN = 10
MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH  = MODEL_DIR / f"lstm_model_{ticker}.h5"
SCALER_PATH = MODEL_DIR / f"scaler_{ticker}.pkl"

# Parquet loaders
@st.cache_data(ttl=60)
def load_prices(tkr: str, since_: pd.Timestamp) -> pd.DataFrame:
    df = pd.read_parquet(PRICES_FILE)
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
          .dt.tz_convert(None)
    )
    df = df[
        (df["ticker"] == tkr.split("-")[0]) &
        (df["timestamp"] > since_)
    ]
    df = (df[["timestamp", "price"]]
            .rename(columns={"timestamp": "time"})
            .set_index("time")
            .sort_index())
    df["return"] = df["price"].pct_change()
    return df.dropna(subset=["return"])

@st.cache_data(ttl=300)
def load_mentions(tkr: str, since_: pd.Timestamp) -> pd.DataFrame:
    ment = pd.read_parquet(MENTIONS_FILE)
    art  = pd.read_parquet(NEWS_FILE)

    ment = ment[ment["ticker"] == tkr.split("-")[0]]
    df = ment.merge(art, on="article_id")

    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
          .dt.tz_convert(None)
    )
    df = df[df["timestamp"] > since_]

    df["bucket"] = df["timestamp"].dt.floor("10min")
    df = (df.groupby("bucket").size()
            .rename("mentions")
            .to_frame()
            .rename_axis("time")
            .sort_index())
    return df

# Fetch & merge
prices_df   = load_prices(ticker, since_time)
if prices_df.empty:
    st.error("❌ No price rows found in parquet for this window.")
    st.stop()

mentions_df = load_mentions(ticker, since_time)
merged_df   = prices_df.join(mentions_df, how="left").fillna({"mentions": 0})

# Build sequences
def make_sequences(df: pd.DataFrame, n: int):
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[["return", "mentions"]])
    X, y = [], []
    for i in range(n, len(scaled)):
        X.append(scaled[i-n:i])
        y.append(scaled[i][0])
    return np.array(X), np.array(y), scaler

X, y, scaler = make_sequences(merged_df, SEQ_LEN)
if len(X) < 50:
    st.warning("Need ≥50 rows for a meaningful train/val split.")
    st.stop()

split = int(0.8 * len(X))
X_train, X_val = X[:split], X[split:]
y_train, y_val = y[:split], y[split:]

# Model load / train
def build_model():
    m = Sequential([Input(shape=(SEQ_LEN, 2)),
                    LSTM(64),
                    Dense(1)])
    m.compile(optimizer="adam", loss=MeanSquaredError())
    return m

if retrain_now or not (os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH)):
    model   = build_model()
    history = model.fit(X_train, y_train,
                        validation_data=(X_val, y_val),
                        epochs=5, batch_size=32, verbose=0)
    model.save(MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    st.toast("✅ Model retrained & saved.")
else:
    model   = load_model(MODEL_PATH)
    scaler  = joblib.load(SCALER_PATH)

# Inference & metrics
y_pred = model.predict(X_val, verbose=0).flatten()

scale_min = scaler.data_min_[0]
scale_max = scaler.data_max_[0]
y_pred = y_pred * (scale_max - scale_min) + scale_min
y_val  = y_val  * (scale_max - scale_min) + scale_min

val_df = pd.DataFrame({"time": range(len(y_val)), "true": y_val, "pred": y_pred})
fig = go.Figure()
fig.add_trace(go.Scatter(x=val_df["time"], y=val_df["true"], name="True", line=dict(color="#48cae4", width=3)))
fig.add_trace(go.Scatter(x=val_df["time"], y=val_df["pred"], name="Predicted", line=dict(color="#E040FB", width=3, dash="dash")))
fig.update_layout(
    height=300,
    paper_bgcolor="#111936",
    plot_bgcolor="#111936",
    xaxis=dict(title="Time", tickfont_color="#FFF"),
    yaxis=dict(title="Return", tickfont_color="#FFF"),
    title=dict(text="Validation – Returns", x=0.05, y=0.92, font=dict(color="#ADB5BD")),
    legend=dict(orientation="h", y=1.1, x=0.95, xanchor="right"),
    margin=dict(t=40, b=10, l=10, r=10),
)
st.plotly_chart(fig, use_container_width=True)

# Price path visual
df_price = pd.read_parquet(PRICES_FILE)
df_price["timestamp"] = pd.to_datetime(df_price["timestamp"])
df_price = df_price[
    (df_price["ticker"] == ticker) &
    (df_price["timestamp"] > since_time)
]
df_price = df_price[["timestamp", "price"]].rename(columns={"timestamp": "time"}).set_index("time").sort_index().ffill()

actual_px = df_price["price"].iloc[-len(y_val):]
base_px   = float(actual_px.iloc[0])
pred_px   = [base_px]

for r in y_pred[1:]:
    pred_px.append(pred_px[-1] * (1 + r))

ymin = actual_px.min() * 0.995
ymax = actual_px.max() * 1.005

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_price.index, y=df_price['price'], name="Actual Price", line=dict(color="#48cae4", width=3)))
fig.add_trace(go.Scatter(x=actual_px.index, y=pred_px, name="Predicted Price", line=dict(color="#E040FB", width=3, dash="dash")))
fig.update_yaxes(range=[ymin, ymax])
fig.update_layout(
    paper_bgcolor="#111936", plot_bgcolor="#111936",
    xaxis=dict(title="Time", tickfont_color="#fff"),
    yaxis=dict(title="Price", tickfont_color="#fff"),
    title=dict(text=f"{ticker} – Live Price vs Prediction", x=0.05, y=0.95, font=dict(color="#ADB5BD")),
    legend=dict(orientation="h", y=1.2, x=0.95, xanchor="right"),
    height=400, margin=dict(t=50, b=20, l=20, r=20),
)
st.plotly_chart(fig, use_container_width=True)
