
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(
    page_title="Forex Intelligence",
    page_icon="📈",
    layout="wide"
)

MARKETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "EUR/GBP": "EURGBP=X",
    "GBP/JPY": "GBPJPY=X",
    "USD/ZAR": "ZAR=X",
    "Gold (Futures)": "GC=F",
    "Silver (Futures)": "SI=F",
    "NASDAQ 100": "^NDX",
    "S&P 500": "^GSPC",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
}

@st.cache_data(ttl=900)
def load_market(ticker):
    data = yf.download(
        ticker,
        period="2y",
        interval="1d",
        auto_adjust=False,
        progress=False
    )
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna()

def analyze(data):
    df = data.copy()
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    df["Bullish"] = (
        (df["Close"] > df["Open"]) &
        (df["Close"].shift(1) < df["Open"].shift(1)) &
        (df["Close"] > df["Open"].shift(1))
    )
    df["Bearish"] = (
        (df["Close"] < df["Open"]) &
        (df["Close"].shift(1) > df["Open"].shift(1)) &
        (df["Close"] < df["Open"].shift(1))
    )

    df["Buy"] = (df["EMA20"] > df["EMA50"]) & df["Bullish"]
    df["Sell"] = (df["EMA20"] < df["EMA50"]) & df["Bearish"]
    return df

def test_signals(df, horizon=5):
    results = []
    for i in range(50, len(df) - horizon - 1):
        side = 1 if df["Buy"].iloc[i] else (
            -1 if df["Sell"].iloc[i] else 0
        )
        if side == 0:
            continue
        entry = df["Open"].iloc[i + 1]
        exit_price = df["Close"].iloc[i + horizon]
        outcome = side * (exit_price - entry) / entry
        results.append({
            "Date": str(df.index[i].date()),
            "Direction": "BUY" if side == 1 else "SELL",
            "Return %": outcome * 100,
            "Correct": outcome > 0
        })
    return pd.DataFrame(results)

st.title("📈 Forex Intelligence")
st.caption("Market research, strategy signals and historical testing")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Market Analysis", "Backtesting", "Accuracy"]
)
market = st.sidebar.selectbox("Choose Market", list(MARKETS))
custom = st.sidebar.text_input("Or enter a Yahoo Finance ticker")
ticker = custom.strip() or MARKETS[market]

try:
    raw = load_market(ticker)
except Exception as exc:
    st.error(f"Market data unavailable: {exc}")
    st.stop()

if len(raw) < 60:
    st.warning("Insufficient market data. Try another instrument.")
    st.stop()

data = analyze(raw)
latest = data.iloc[-1]
trades = test_signals(data)

if page in ["Dashboard", "Market Analysis"]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Instrument", market)
    c2.metric("Last Price", f"{latest['Close']:.5f}")
    signal = "BUY" if latest["Buy"] else (
        "SELL" if latest["Sell"] else "WAIT"
    )
    c3.metric("Latest Signal", signal)

    fig = go.Figure()
    chart = data.tail(150)
    fig.add_trace(go.Candlestick(
        x=chart.index,
        open=chart["Open"],
        high=chart["High"],
        low=chart["Low"],
        close=chart["Close"],
        name="Price"
    ))
    fig.add_trace(go.Scatter(
        x=chart.index, y=chart["EMA20"], name="EMA 20"
    ))
    fig.add_trace(go.Scatter(
        x=chart.index, y=chart["EMA50"], name="EMA 50"
    ))
    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Signals are experimental technical observations, "
        "not guaranteed trading recommendations."
    )

elif page == "Backtesting":
    st.subheader("Historical Signal Backtesting")
    st.caption(
        "Next-candle entry, five-bar holding period. "
        "No spread, slippage or trading fees included."
    )
    if trades.empty:
        st.warning("No signals found.")
    else:
        st.metric("Signals Tested", len(trades))
        st.metric("Win Rate", f"{trades['Correct'].mean():.1%}")
        st.metric(
            "Average Return",
            f"{trades['Return %'].mean():+.3f}%"
        )
        st.line_chart(trades["Return %"].cumsum())
        st.dataframe(trades.iloc[::-1], use_container_width=True)

elif page == "Accuracy":
    st.subheader("Prediction Accuracy")
    st.caption(
        "Historical directional signal results for the selected market. "
        "These are not tracked live predictions."
    )
    if trades.empty:
        st.warning("No evaluated signals yet.")
    else:
        wins = int(trades["Correct"].sum())
        losses = len(trades) - wins
        c1, c2, c3 = st.columns(3)
        c1.metric("Win Rate", f"{wins / len(trades):.1%}")
        c2.metric("Correct", wins)
        c3.metric("Incorrect", losses)
        st.bar_chart(pd.DataFrame({
            "Count": [wins, losses]
        }, index=["Correct", "Incorrect"]))
        st.dataframe(trades, use_container_width=True)

