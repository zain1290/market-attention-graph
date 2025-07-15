# Market Attention Graph

A real-time, graph-based project modeling co-mention relationships and volatility prediction for key stocks and cryptocurrencies.
“When attention shifts to a stock, how does it propagate to related names (supply chain, sector, correlated firms), and can we preemptively detect ‘spillover volatility’?”

#### Tickers Tracked:
- Stocks: Google, Apple, Amazon, Nvidia, Microsoft
- Crypto: Bitcoin, XRP


### Project: Market Attention Propagation Model (Python, ML, Graphs)

- Design a graph-based model to analyze how co-mentions of companies across real-time financial news, social media, and job listings drive short-term volatility in U.S. equities.

- Engineer a temporal attention graph, and apply ML classifiers to predict volatility clusters based on information propagation.

- Build a real-time dashboard using Dash + Plotly to visualize attention flows and signal alerts.

---

---

1. Data Pipeline | Scrape/stream data from:

- Alpaca for live stock prices

- Binance for live crypto prices

- GDELT

- RSS Feed 

- Filtered X.com(Twitter) stream

---

2. Attention Graph Construction:

- Nodes: Companies (tickers)

- Edges: Links if companies are co-mentioned, in same news thread

- Edge weight: Strength/frequency of attention co-occurrence

- Update the graph over time → temporal graph

---

3. Volatility Prediction Module

- Use historical price data (e.g., yfinance, polygon.io)

- For each "attention wave", look at: local volatility spike, trade volume, bid-ask spread changes

- Label events where volatility jumped and use classification (XGBoost, LSTM, or Random Forest) to predict when that will happen based on attention patterns.

---

4. Visualization Dashboard

- Use plotly, networkx, or dash to show:

- Real-time attention graph

- Volatility clusters (heatmap)

- Predicted vs. realized volatility spikes