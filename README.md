# Market Attention Dashboard🔹

A real-time market intelligence dashboard combining live price feeds, 
news sentiment, and social signals across Reddit, 
Twitter, and major RSS/News sources.
> Built with: `Streamlit`, `DuckDB`, `async collectors`, `LSTM models`, and a sprinkle of ✨ automation magic.

---  

## 🌐 Quickstart Live Demo (Streamlit Cloud)
> Try the **dashboard demo** using historical snapshots:

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://market-attention-dashboard-zq.streamlit.app/)

<video src="https://github.com/user-attachments/assets/d84693c7-47d7-4450-ae24-2b9352bf6f3f"
       width="600" controls poster="assets/thumbnail.jpg"></video>

---

## ⚡ Full Setup (Live Mode)

> Requires `.env` with credentials and `cookies.json` for Twitter

### 1. Add Environment Variables

```ini
# .env file
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
USER_AGENT=yourapp
ALPACA_KEY=xxx
ALPACA_SECRET=xxx
# cookies.json
{}
```

### 2. Start Collectors

```bash
python run.py
```

> Writes live data into `/data/` using DuckDB + Parquet

### 3. Launch Dashboard

```bash
streamlit run src/dashboard/Z-Dash.py
```

---


## ✨ Tickers Tracked:
- Stocks: Google, Apple, Amazon, Nvidia, Microsoft
- Crypto: Bitcoin, XRP

---

## 🎓 Project: Market Attention Propagation Model (Python, ML, Graphs)

- Design a graph-based model to analyze how co-mentions of companies across real-time financial news and social media drive short-term volatility in U.S. equities.

- Engineer a temporal attention graph, and apply ML classifiers to predict volatility clusters based on information propagation.

- Build a real-time dashboard using Dash + Plotly to visualize attention flows and signal alerts.

---

## 🎡 Features

### 🚀 Unified Dashboard:

- Live & historical price charts (Binance + Alpaca)

- Real-time news mentions from GDELT, RSS, and Twitter (Twikit)

- Multi-ticker price vs return charts

- Adjustable window (1h to 24h) via sidebar

- Interactive visualizations using plotly, networkx, matplotlib, altair and seaborn to show:

  - Real-time attention graph
  - Volatility clusters (heatmap)
  - Predicted vs. realized volatility spikes

---

### 🪀 Intelligent Data Collection:

- Async collectors feed data into a DuckDB instance

- Modular sources:

  - Binance WebSocket (crypto)
  - Alpaca WebSocket (stocks)
  - GDELT API (global news)
  - RSS feeds (Bloomberg, NYTimes, etc)
  - Twitter (via `twikit` and cookies)

### 📈 Attention Graph Construction:

- Nodes: Companies (tickers)

- Edges: Links if companies are co-mentioned, in same news thread

- Edge weight: Strength/frequency of attention co-occurrence, the closer and thicker the edge, the stronger the weight.

- Update the graph over time → temporal graph

---

### 📊 Prototype Forecasting:

- Train model with live data gathered over time, re-train when needed.

- Each ticker has its own LSTM model, trained on:

  - `return` (from price data)
  - `mentions` (from news + X)

- Auto-retrains if model not found or user selects "Retrain now"

- Visual prediction vs actual chart overlay

---

## 📍 Author

· Made with ❤️ by Zain Qureshi · 

---
