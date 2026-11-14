
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from signal_models import BASELINE_VERSION, MOMENTUM_VERSION, momentum_signals

from datetime import datetime, timezone
from prediction_store import (
    config,
    save_prediction,
    list_predictions,
    complete_prediction,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Forex Intelligence | Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "V3.7"
MODEL_VERSION = BASELINE_VERSION


# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown(
    """
<style>
.stApp {
    background: #080d18;
    color: #edf3ff;
}
[data-testid="stSidebar"] {
    background: #101827;
    border-right: 1px solid #25324b;
}
[data-testid="stSidebar"] * {
    color: #e4ecfc !important;
}
[data-testid="stSidebar"] input {
    color: #111827 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #111827 !important;
}
[data-testid="stMetric"] {
    background: #141e30;
    border: 1px solid #273653;
    border-radius: 14px;
    padding: 13px;
}
[data-testid="stMetricLabel"] {
    color: #9eafc9 !important;
}
[data-testid="stMetricValue"] {
    color: #eef5ff !important;
}
.block-container {
    padding-top: 1.3rem;
    max-width: 1750px;
}
h1, h2, h3 {
    letter-spacing: -.025em;
    color: #f2f6ff !important;
}
div[data-testid="stAlert"] {
    border-radius: 12px;
}
.terminal-card {
    background: linear-gradient(145deg, #141d2d, #0e1522);
    border: 1px solid #293852;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 13px;
    box-shadow: 0 10px 24px #0003;
}
.card-label {
    font-size: .78rem;
    color: #a8b8d3;
    letter-spacing: .045em;
    font-weight: 650;
}
.card-title {
    font-size: 1.25rem;
    color: #f0f5ff;
    font-weight: 750;
    margin: 7px 0;
}
.signal-buy {
    color: #62e4a2 !important;
}
.signal-sell {
    color: #ff7e95 !important;
}
.signal-wait {
    color: #eabf6b !important;
}
.signal-big {
    font-size: 3.8rem;
    line-height: 1.25;
    font-weight: 850;
    text-align: center;
    padding: 15px 0;
}
.signal-caption {
    text-align: center;
    color: #a4b5d0;
    font-size: .85rem;
}
.signal-panel {
    background: radial-gradient(
        circle at center,
        #1b3040,
        #111a29 70%
    );
    border: 1px solid #34445d;
    border-radius: 18px;
    padding: 24px 14px;
    margin: 12px 0;
}
.pill {
    display: inline-block;
    padding: 6px 11px;
    border: 1px solid #364660;
    border-radius: 20px;
    background: #1b2740;
    color: #d7e8ff;
    font-size: .78rem;
    margin: 3px;
}
.rule {
    font-size: .87rem;
    color: #c6d3e8;
    line-height: 1.65;
}
.small-note {
    color: #94a6c2;
    font-size: .78rem;
}
[data-testid="stDataFrame"] {
    border: 1px solid #273653;
    border-radius: 12px;
    overflow: hidden;
}
[data-testid="stPlotlyChart"] {
    border: 1px solid #273653;
    border-radius: 16px;
    overflow: hidden;
    background: #101a2b;
}
[data-testid="stTabs"] button {
    color: #c4d4ee !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #79b7ff !important;
}
/* Streamlit versions can style tab text on nested elements. */
[data-testid="stTabs"] button p,
[data-testid="stTabs"] button span {
    color: #c4d4ee !important;
}
[data-testid="stTabs"] button[aria-selected="true"] p,
[data-testid="stTabs"] button[aria-selected="true"] span {
    color: #9dcbff !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: #79b7ff !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SUPPORTED MARKETS
# ============================================================

GROUPS = {
    "Major Forex": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "USD/CHF": "CHF=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CAD": "CAD=X",
        "NZD/USD": "NZDUSD=X",
    },
    "Minor Forex": {
        "EUR/GBP": "EURGBP=X",
        "EUR/JPY": "EURJPY=X",
        "GBP/JPY": "GBPJPY=X",
        "EUR/AUD": "EURAUD=X",
        "AUD/JPY": "AUDJPY=X",
        "GBP/AUD": "GBPAUD=X",
        "EUR/CHF": "EURCHF=X",
        "NZD/JPY": "NZDJPY=X",
    },
    "Exotic Forex": {
        "USD/ZAR": "ZAR=X",
        "USD/MXN": "MXN=X",
        "USD/TRY": "TRY=X",
        "USD/SGD": "SGD=X",
    },
    "Metals (futures proxies)": {
        "Gold Futures": "GC=F",
        "Silver Futures": "SI=F",
    },
    "Indices": {
        "S&P 500": "^GSPC",
        "NASDAQ 100": "^NDX",
        "Dow Jones": "^DJI",
        "DAX": "^GDAXI",
    },
    "Crypto": {
        "BTC/USD": "BTC-USD",
        "ETH/USD": "ETH-USD",
        "SOL/USD": "SOL-USD",
    },
}

ALL = {
    name: (ticker, group)
    for group, items in GROUPS.items()
    for name, ticker in items.items()
}

TIMEFRAMES = {
    "5m": ("5m", "5d"),
    "15m": ("15m", "1mo"),
    "1h": ("60m", "3mo"),
    "4h": ("60m", "3mo"),
    "1d": ("1d", "2y"),
}


# ============================================================
# MARKET DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def fetch(ticker, interval, period):
    data = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]

    if any(col not in data.columns for col in required):
        return pd.DataFrame()

    data = data.dropna(subset=required).sort_index()
    data = data[~data.index.duplicated(keep="last")]

    return data


def resample_4h(data):
    if data.empty:
        return data

    df = data.copy()

    columns = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
    }

    if "Volume" in df.columns:
        columns["Volume"] = "sum"

    df = (
        df.resample("4h", origin="start_day")
        .agg(columns)
        .dropna(subset=["Open", "High", "Low", "Close"])
    )

    return df


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def indicators(data):
    df = data.copy()

    df["EMA20"] = df.Close.ewm(
        span=20, adjust=False
    ).mean()

    df["EMA50"] = df.Close.ewm(
        span=50, adjust=False
    ).mean()

    previous = df.shift(1)

    bullish_engulfing = (
        (previous.Close < previous.Open)
        & (df.Close > df.Open)
        & (df.Open <= previous.Close)
        & (df.Close >= previous.Open)
    )

    bearish_engulfing = (
        (previous.Close > previous.Open)
        & (df.Close < df.Open)
        & (df.Open >= previous.Close)
        & (df.Close <= previous.Open)
    )

    df["BullEngulf"] = bullish_engulfing.fillna(False)
    df["BearEngulf"] = bearish_engulfing.fillna(False)

    df["Buy"] = (
        (df.EMA20 > df.EMA50)
        & df.BullEngulf
    )

    df["Sell"] = (
        (df.EMA20 < df.EMA50)
        & df.BearEngulf
    )

    df["BullFVG"] = (
        df.Low > df.High.shift(2)
    ).fillna(False)

    df["BearFVG"] = (
        df.High < df.Low.shift(2)
    ).fillna(False)

    df["PriorHigh20"] = (
        df.High.shift(1).rolling(20).max()
    )

    df["PriorLow20"] = (
        df.Low.shift(1).rolling(20).min()
    )

    df["BreakUp"] = (
        df.Close > df.PriorHigh20
    ).fillna(False)

    df["BreakDown"] = (
        df.Close < df.PriorLow20
    ).fillna(False)

    return df


# ============================================================
# HISTORICAL BACKTESTING
# ============================================================

def backtest(df, horizon=5, spread_bps=0.0, slippage_bps=0.0, commission_bps=0.0):
    """
    Historical simulation:
    - Signal on completed candle
    - Enter at next candle open
    - Exit after horizon bars
    - Skip overlapping trades

    Returns are indicative price changes, not executable P&L.
    Cost inputs are round-trip spread and commission plus per-side slippage,
    all in basis points of notional; net is an approximate return adjustment.
    """

    results = []
    next_allowed = 50

    for i in range(50, len(df) - horizon):

        if i < next_allowed:
            continue

        side = (
            1 if bool(df.Buy.iloc[i])
            else -1 if bool(df.Sell.iloc[i])
            else 0
        )

        if side == 0:
            continue

        entry = float(df.Open.iloc[i + 1])
        exit_price = float(df.Close.iloc[i + horizon])

        if (
            not np.isfinite(entry)
            or entry <= 0
            or not np.isfinite(exit_price)
        ):
            continue

        trade_return = (
            100 * side * (exit_price - entry) / entry
        )
        total_cost_bps = spread_bps + 2 * slippage_bps + commission_bps
        net_return = trade_return - total_cost_bps / 100.0

        results.append({
            "Signal time": str(df.index[i]),
            "Direction": "BUY" if side == 1 else "SELL",
            "Entry": entry,
            "Exit": exit_price,
            "Gross return %": trade_return,
            "Estimated cost %": total_cost_bps / 100.0,
            "Net return %": net_return,
            "Win": trade_return > 0,
            "Net win": net_return > 0,
        })

        next_allowed = i + horizon + 1

    return pd.DataFrame(results)


def stats(trades):
    if trades.empty:
        return None

    returns = trades["Gross return %"].astype(float)

    wins = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()

    profit_factor = (
        wins / losses if losses > 0 else np.nan
    )

    equity = (1 + returns / 100).cumprod()

    # Include initial capital when calculating peak-to-trough drawdown.
    running_peak = np.maximum.accumulate(np.r_[1.0, equity.to_numpy()])[1:]
    drawdown = (equity.to_numpy() / running_peak - 1) * 100

    return {
        "Trades": len(trades),
        "Win rate %": round(
            float((returns > 0).mean() * 100), 1
        ),
        "Avg gross return %": round(
            float(returns.mean()), 3
        ),
        "Profit factor": (
            round(float(profit_factor), 2)
            if np.isfinite(profit_factor)
            else None
        ),
        "Max drawdown %": round(
            float(drawdown.min()), 2
        ),
    }


# ============================================================
# HELPERS
# ============================================================

def fmt_price(value, name):
    if not np.isfinite(value):
        return "—"

    if (
        name in GROUPS["Indices"]
        or name in GROUPS["Metals (futures proxies)"]
        or name in GROUPS["Crypto"]
    ):
        return f"{value:,.2f}"

    if "JPY" in name:
        return f"{value:,.3f}"

    return f"{value:,.5f}"


def style_backtest(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#101a2b",
        plot_bgcolor="#101a2b",
        font=dict(color="#dce7fa", size=13),
        title_font=dict(color="#f2f6ff", size=19),
        xaxis=dict(title_font=dict(color="#b9cae5"), tickfont=dict(color="#b9cae5")),
        yaxis=dict(title_font=dict(color="#b9cae5"), tickfont=dict(color="#b9cae5")),
        height=400,
        margin=dict(l=28, r=24, t=62, b=42),
        showlegend=False,
        hovermode="x unified",
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#24324b",
        zeroline=False,
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#24324b",
        zeroline=False,
        tickformat=".2f",
    )

    return fig


def forward_leaderboard(history, group_columns):
    """
    Build leaderboard from genuine evaluated BUY/SELL records.

    WAIT predictions are excluded from directional accuracy.
    Pending and unavailable forecasts are tracked separately.
    """

    directional = history[
        history["signal"].isin(["BUY", "SELL"])
    ].copy()

    evaluated = directional[
        (directional["status"] == "evaluated")
        & directional["correct"].notna()
    ].copy()

    if evaluated.empty:
        return pd.DataFrame(), evaluated, directional

    evaluated["correct"] = evaluated["correct"].map({
        True: 1,
        False: 0,
        "true": 1,
        "false": 0,
        "True": 1,
        "False": 0,
        1: 1,
        0: 0,
    })

    evaluated = evaluated.dropna(subset=["correct"])
    evaluated["correct"] = evaluated["correct"].astype(int)

    if evaluated.empty:
        return pd.DataFrame(), evaluated, directional

    board = (
        evaluated.groupby(group_columns, dropna=False)
        .agg(
            Predictions=("id", "count"),
            Correct=("correct", "sum"),
        )
        .reset_index()
    )

    board["Correct"] = board["Correct"].astype(int)

    board["Incorrect"] = (
        board["Predictions"] - board["Correct"]
    )

    board["Accuracy %"] = (
        100 * board["Correct"] / board["Predictions"]
    ).round(1)

    def grouped_count(frame, name):
        if frame.empty:
            return pd.DataFrame(
                columns=group_columns + [name]
            )

        return (
            frame.groupby(group_columns, dropna=False)
            .size()
            .rename(name)
            .reset_index()
        )

    pending = directional[
        directional["status"] == "pending"
    ]

    unavailable = directional[
        directional["status"] == "unavailable"
    ]

    waits = history[
        history["signal"] == "WAIT"
    ]

    for counts in [
        grouped_count(pending, "Pending"),
        grouped_count(unavailable, "Unavailable"),
        grouped_count(waits, "WAIT"),
    ]:
        board = board.merge(
            counts,
            on=group_columns,
            how="left",
        )

    for column in ["Pending", "Unavailable", "WAIT"]:
        board[column] = (
            board[column].fillna(0).astype(int)
        )

    board["Coverage %"] = (
        100
        * board["Predictions"]
        / (
            board["Predictions"]
            + board["Pending"]
            + board["Unavailable"]
        )
    ).round(1)

    return board, evaluated, directional


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## ✦ Forex Intelligence")
st.sidebar.caption(
    f"Market intelligence · {APP_VERSION} terminal"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Trading Terminal",
        "Market Analysis",
        "Historical Backtesting",
        "Historical Accuracy",
        "Prediction History",
    ],
)

category = st.sidebar.selectbox(
    "Market category",
    list(GROUPS),
)

market = st.sidebar.selectbox(
    "Search instrument",
    list(GROUPS[category]),
)

custom = st.sidebar.text_input(
    "Custom Yahoo Finance ticker (optional)",
    placeholder="EURUSD=X",
)

tf = st.sidebar.selectbox(
    "Timeframe",
    list(TIMEFRAMES),
    index=4,
)

strategy_label = st.sidebar.selectbox(
    "Signal strategy",
    ["EMA + Engulfing (original)", "EMA + RSI + MACD (experimental)"],
    help="Compare separately versioned research rules. Performance is not guaranteed.",
)
MODEL_VERSION = (
    MOMENTUM_VERSION if "experimental" in strategy_label else BASELINE_VERSION
)

horizon = st.sidebar.slider(
    "Backtest holding period (bars)",
    2,
    20,
    5,
)

st.sidebar.caption(
    "Market data is delayed/historical. "
    "Intraday history varies. "
    "Gold/silver use futures proxies, not spot prices."
)


# ============================================================
# LOAD SELECTED MARKET
# ============================================================

symbol = (
    custom.strip().upper()
    if custom.strip()
    else ALL[market][0]
)

interval, period = TIMEFRAMES[tf]

try:
    with st.spinner("Loading market candles…"):
        raw = fetch(symbol, interval, period)

        if tf == "4h" and not raw.empty:
            raw = resample_4h(raw)

except Exception as exc:
    st.error(f"Data provider error: {exc}")
    st.stop()

if len(raw) < 60:
    st.error(
        "Insufficient market data for this instrument/timeframe. "
        "Try Daily or another symbol."
    )
    st.stop()

df = indicators(raw)
if MODEL_VERSION == MOMENTUM_VERSION:
    df["Buy"], df["Sell"] = momentum_signals(df)
trades = backtest(df, horizon)
result = stats(trades)

last = df.iloc[-1]

label = (
    custom.strip().upper()
    if custom.strip()
    else market
)

signal = (
    "BUY" if bool(last.Buy)
    else "SELL" if bool(last.Sell)
    else "WAIT"
)

trend = (
    "Bullish"
    if last.EMA20 > last.EMA50
    else "Bearish"
)

color_class = {
    "BUY": "signal-buy",
    "SELL": "signal-sell",
    "WAIT": "signal-wait",
}[signal]


# ============================================================
# RSI, MACD, ATR
# ============================================================

delta = df.Close.diff()

gain = delta.clip(lower=0).ewm(
    alpha=1 / 14,
    adjust=False,
).mean()

loss = (-delta.clip(upper=0)).ewm(
    alpha=1 / 14,
    adjust=False,
).mean()

rsi = 100 - 100 / (
    1 + gain / loss.replace(0, np.nan)
)

macd = (
    df.Close.ewm(span=12, adjust=False).mean()
    - df.Close.ewm(span=26, adjust=False).mean()
)

macd_sig = macd.ewm(
    span=9,
    adjust=False,
).mean()

true_range = pd.concat(
    [
        df.High - df.Low,
        (df.High - df.Close.shift()).abs(),
        (df.Low - df.Close.shift()).abs(),
    ],
    axis=1,
).max(axis=1)

atr = true_range.ewm(
    alpha=1 / 14,
    adjust=False,
).mean()

atr_pct = (
    100 * float(atr.iloc[-1]) / float(last.Close)
)


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown("## ✦ Forex Intelligence")
st.caption(
    "Trading terminal · Market research · "
    "Historical testing | Not financial advice"
)


# ============================================================
# PAGE 1: TRADING TERMINAL
# ============================================================

if page == "Trading Terminal":

    left, center, right = st.columns(
        [1.05, 1.8, 1.1],
        gap="medium",
    )

    with left:
        st.markdown(
            '<div class="terminal-card">'
            '<div class="card-label">MARKET OVERVIEW</div>'
            f'<div class="card-title">{label}</div>'
            '<div class="rule">'
            f"Category: {category}<br>"
            f"Timeframe: {tf}<br>"
            "Source: Yahoo Finance"
            "</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="terminal-card">'
            '<div class="card-label">MARKET TREND</div>'
            f'<div class="card-title">{trend}</div>'
            '<div class="rule">'
            f"EMA 20: {fmt_price(float(last.EMA20), market)}"
            "<br>"
            f"EMA 50: {fmt_price(float(last.EMA50), market)}"
            "</div></div>",
            unsafe_allow_html=True,
        )

        structure = (
            "Up" if bool(last.BreakUp)
            else "Down" if bool(last.BreakDown)
            else "None"
        )

        st.markdown(
            '<div class="terminal-card">'
            '<div class="card-label">MARKET STRUCTURE</div>'
            '<div class="rule">'
            f"20-bar break: <b>{structure}</b><br>"
            "Bullish FVG: "
            f"{'Detected' if bool(last.BullFVG) else 'Not detected'}"
            "<br>"
            "Bearish FVG: "
            f"{'Detected' if bool(last.BearFVG) else 'Not detected'}"
            "</div></div>",
            unsafe_allow_html=True,
        )

        if result:
            st.metric(
                "Historical gross win rate",
                f"{result['Win rate %']:.1f}%",
                help=(
                    f"{result['Trades']} historical simulated "
                    "signals; no trading costs"
                ),
            )

            st.caption(
                f"Based on {result['Trades']} non-overlapping "
                "completed historical trades. "
                "Not signal confidence."
            )
        else:
            st.info(
                "No completed backtest trades for these settings."
            )

    with center:
        signal_message = (
            "EMA + RSI + MACD momentum confirmation"
            if MODEL_VERSION == MOMENTUM_VERSION
            else "EMA trend + engulfing confirmation"
        ) if signal != "WAIT" else (
            "No qualifying setup for the selected strategy on the latest bar"
        )

        st.markdown(
            '<div class="terminal-card">'
            '<div class="card-label" style="text-align:center">'
            "SELECTED INSTRUMENT"
            "</div>"
            '<div class="card-title" '
            'style="text-align:center;font-size:1.7rem">'
            f"{label}</div>"
            '<div class="signal-panel">'
            f'<div class="signal-big {color_class}">'
            f"{signal}</div>"
            f'<div class="signal-caption">{signal_message}</div>'
            "</div>"
            '<div class="signal-caption">'
            f"Last candle: {df.index[-1]}"
            "</div></div>",
            unsafe_allow_html=True,
        )

        st.metric(
            "Last candle close",
            fmt_price(float(last.Close), market),
        )

        st.caption(
            "Historical candle close, "
            "not a live executable quote."
        )

    with right:
        if MODEL_VERSION == MOMENTUM_VERSION:
            signal_description = (
                "Experimental trend + RSI + MACD + candle-body confirmation."
                if signal != "WAIT" else
                "No qualified EMA, RSI and MACD momentum alignment."
            )
        else:
            signal_description = (
                "Bullish EMA alignment and bullish body engulfing."
                if signal == "BUY" else
                "Bearish EMA alignment and bearish body engulfing."
                if signal == "SELL" else
                "Waiting for trend alignment and a qualifying engulfing candle."
            )

        st.markdown(
            '<div class="terminal-card">'
            '<div class="card-label">'
            f"RESEARCH SIGNAL · {MODEL_VERSION}"
            "</div>"
            f'<div class="card-title {color_class}">'
            f"{signal}</div>"
            f'<div class="rule">{signal_description}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        x, y = st.columns(2)

        with x:
            st.metric(
                "RSI (14)",
                (
                    f"{float(rsi.iloc[-1]):.1f}"
                    if np.isfinite(rsi.iloc[-1])
                    else "—"
                ),
            )

            st.metric("EMA trend", trend)

        with y:
            st.metric(
                "ATR / Price",
                f"{atr_pct:.2f}%",
            )

            st.metric(
                "MACD",
                (
                    "Above signal"
                    if macd.iloc[-1] > macd_sig.iloc[-1]
                    else "Below signal"
                ),
            )

        st.markdown(
            '<div class="terminal-card">'
            '<div class="card-label">SIGNAL QUALITY</div>'
            '<div class="rule">'
            "No calibrated confidence percentage yet. "
            "Confidence requires out-of-sample validation "
            "across markets and timeframes."
            "</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("### Price action & detected setups")

    fig = go.Figure()
    view = df.tail(130)

    fig.add_trace(
        go.Candlestick(
            x=view.index,
            open=view.Open,
            high=view.High,
            low=view.Low,
            close=view.Close,
            name="Candles",
            increasing_line_color="#36d6b0",
            decreasing_line_color="#fa718b",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=view.index,
            y=view.EMA20,
            name="EMA 20",
            line=dict(color="#eeb85c", width=1.6),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=view.index,
            y=view.EMA50,
            name="EMA 50",
            line=dict(color="#79a8ff", width=1.6),
        )
    )

    buys = view[view.Buy]
    sells = view[view.Sell]

    fig.add_trace(
        go.Scatter(
            x=buys.index,
            y=buys.Low,
            mode="markers",
            name="BUY setup",
            marker=dict(
                symbol="triangle-up",
                size=11,
                color="#36d6b0",
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=sells.index,
            y=sells.High,
            mode="markers",
            name="SELL setup",
            marker=dict(
                symbol="triangle-down",
                size=11,
                color="#fa718b",
            ),
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#080d18",
        plot_bgcolor="#111b2c",
        height=520,
        margin=dict(l=8, r=8, t=35, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.09),
        font=dict(color="#d7e5fa"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Signals are rule-based research observations. "
        "FVG and market structure are contextual only. "
        "QM/MPL, liquidity sweeps and supply/demand "
        "confluence are planned for later versions."
    )


# ============================================================
# PAGE 2: MARKET ANALYSIS
# ============================================================

elif page == "Market Analysis":

    st.subheader(
        f"Market Analysis · {label} · {tf}"
    )

    st.caption(
        "A dedicated technical breakdown using completed "
        "historical candles. Signals are not live "
        "execution instructions."
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Latest close",
        fmt_price(float(last.Close), market),
    )

    m2.metric("EMA trend", trend)

    m3.metric(
        "RSI (14)",
        (
            f"{float(rsi.iloc[-1]):.1f}"
            if np.isfinite(rsi.iloc[-1])
            else "—"
        ),
    )

    m4.metric(
        "ATR / Price",
        f"{atr_pct:.2f}%",
    )

    analysis_tab, structure_tab, events_tab = st.tabs(
        [
            "Price chart & indicators",
            "Market structure & FVG",
            "Recent detected events",
        ]
    )

    with analysis_tab:
        fig = go.Figure()
        view = df.tail(160)

        fig.add_trace(
            go.Candlestick(
                x=view.index,
                open=view.Open,
                high=view.High,
                low=view.Low,
                close=view.Close,
                name="Candles",
                increasing_line_color="#37d5ad",
                decreasing_line_color="#fa718b",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=view.index,
                y=view.EMA20,
                name="EMA 20",
                line=dict(color="#f5bd61", width=2),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=view.index,
                y=view.EMA50,
                name="EMA 50",
                line=dict(color="#72a7ff", width=2),
            )
        )

        buys = view[view.Buy]
        sells = view[view.Sell]

        fig.add_trace(
            go.Scatter(
                x=buys.index,
                y=buys.Low,
                mode="markers",
                name="BUY setup",
                marker=dict(
                    color="#37d5ad",
                    symbol="triangle-up",
                    size=11,
                ),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=sells.index,
                y=sells.High,
                mode="markers",
                name="SELL setup",
                marker=dict(
                    color="#fa718b",
                    symbol="triangle-down",
                    size=11,
                ),
            )
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#101a2b",
            plot_bgcolor="#101a2b",
            font=dict(color="#dce7fa"),
            height=510,
            margin=dict(l=16, r=16, t=48, b=18),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.12),
            hovermode="x unified",
        )

        fig.update_xaxes(
            showgrid=True,
            gridcolor="#22314a",
        )

        fig.update_yaxes(
            showgrid=True,
            gridcolor="#22314a",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.markdown("#### Indicator interpretation")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"**Trend:** {trend}. "
                f"EMA20 is {fmt_price(float(last.EMA20), market)} "
                f"and EMA50 is "
                f"{fmt_price(float(last.EMA50), market)}."
            )

            st.markdown(
                f"**RSI:** {float(rsi.iloc[-1]):.1f}"
                if np.isfinite(rsi.iloc[-1])
                else "**RSI:** unavailable"
            )

        with col2:
            st.markdown(
                "**MACD:** "
                + (
                    "Above its signal line"
                    if macd.iloc[-1] > macd_sig.iloc[-1]
                    else "Below its signal line"
                )
            )

            st.markdown(
                f"**Volatility:** ATR is {atr_pct:.2f}% "
                "of the latest closing price."
            )

    with structure_tab:
        up = bool(last.BreakUp)
        down = bool(last.BreakDown)

        structure = (
            "Bullish 20-bar breakout"
            if up
            else (
                "Bearish 20-bar breakout"
                if down
                else "No new 20-bar breakout"
            )
        )

        st.markdown(f"### {structure}")

        st.write(
            "A breakout requires the latest close to exceed "
            "the previous 20 completed bars' high, or fall "
            "below their low. This is a simplified structure "
            "proxy, not a full BOS/CHoCH model."
        )

        a, b, c = st.columns(3)

        a.metric(
            "Prior 20-bar high",
            fmt_price(float(last.PriorHigh20), market),
        )

        b.metric(
            "Prior 20-bar low",
            fmt_price(float(last.PriorLow20), market),
        )

        c.metric(
            "Current bar FVG",
            (
                "Bullish"
                if bool(last.BullFVG)
                else (
                    "Bearish"
                    if bool(last.BearFVG)
                    else "None"
                )
            ),
        )

        st.write(
            "**FVG definition:** A bullish gap exists when "
            "the current low exceeds the high two candles "
            "earlier; a bearish gap exists when the current "
            "high is below the low two candles earlier."
        )

        st.write(
            "**Current strategy setup:** "
            + signal
            + ". The V3 rule requires EMA20/EMA50 alignment "
            "and a matching two-candle body engulfing pattern."
        )

    with events_tab:
        recent = df.tail(160)[
            [
                "BullEngulf",
                "BearEngulf",
                "BullFVG",
                "BearFVG",
                "BreakUp",
                "BreakDown",
                "Buy",
                "Sell",
            ]
        ]

        events = (
            recent[recent.any(axis=1)]
            .tail(60)
            .iloc[::-1]
            .copy()
        )

        if events.empty:
            st.info(
                "No events found in the selected history."
            )
        else:
            events.index = events.index.astype(str)
            events.index.name = "Candle time"

            st.dataframe(
                events,
                use_container_width=True,
                height=440,
            )

            st.download_button(
                "Download detected events",
                data=events.to_csv().encode(),
                file_name="market_events.csv",
                mime="text/csv",
            )

    st.info(
        "QM/MPL, liquidity sweeps and full supply/demand "
        "zones are not implemented in this version. "
        "This page shows the rules currently coded."
    )


# ============================================================
# PAGE 3: HISTORICAL BACKTESTING
# ============================================================

elif page == "Historical Backtesting":

    st.subheader(
        f"Historical Strategy Testing · {label} · {tf}"
    )

    st.info(
        "These are retrospective simulations generated "
        "from past candles, not trades placed or predictions "
        "previously issued by the app."
    )

    st.caption(
        f"Completed-bar signal → next-bar open entry → "
        f"close {horizon} bars after the signal. "
        "Non-overlapping positions; estimates exclude financing, "
        "market impact, leverage and position-sizing constraints."
    )

    st.markdown("#### Trading cost assumptions (basis points)")
    st.caption(
        "1 basis point (bp) = 0.01% of notional. "
        "These are editable scenario assumptions, not live broker quotes. "
        "Spread and commission are round-trip; slippage is per side."
    )
    cost_a, cost_b, cost_c = st.columns(3)
    with cost_a:
        spread_bps = st.number_input(
            "Round-trip spread (bps)", min_value=0.0, max_value=100.0,
            value=2.0, step=0.5, key="bt_spread_bps",
        )
    with cost_b:
        slippage_bps = st.number_input(
            "Slippage per side (bps)", min_value=0.0, max_value=100.0,
            value=1.0, step=0.5, key="bt_slippage_bps",
        )
    with cost_c:
        commission_bps = st.number_input(
            "Round-trip commission (bps)", min_value=0.0, max_value=100.0,
            value=0.0, step=0.5, key="bt_commission_bps",
        )

    trades = backtest(df, horizon, spread_bps, slippage_bps, commission_bps)
    result = stats(trades)
    total_cost_bps = spread_bps + 2 * slippage_bps + commission_bps
    st.caption(f"Estimated combined round-trip cost: {total_cost_bps:.2f} bps per trade.")

    if result is None:
        st.warning(
            "No completed historical trades for this "
            "instrument and timeframe."
        )

    else:
        st.caption(f"Selected strategy: {strategy_label} · {MODEL_VERSION}")
        sample_count = len(trades)
        if sample_count < 30:
            st.warning(
                f"Limited sample: only {sample_count} completed historical trades. "
                "Win rates and profit factors are unstable at this size. "
                "Do not interpret them as a reliable trading edge."
            )
        else:
            st.info(
                f"{sample_count} retrospective trades analysed. "
                "Results remain in-sample. Net returns use the cost inputs above."
            )

        returns = trades["Gross return %"].astype(float)
        net_returns = trades["Net return %"].astype(float)
        net_equity = (1 + net_returns / 100).cumprod()
        net_cumulative = (net_equity - 1) * 100
        net_peak = np.maximum.accumulate(np.r_[1.0, net_equity.to_numpy()])[1:]
        net_drawdown = (net_equity.to_numpy() / net_peak - 1) * 100
        net_wins = net_returns[net_returns > 0].sum()
        net_losses = -net_returns[net_returns < 0].sum()
        net_pf = net_wins / net_losses if net_losses > 0 else None

        equity = (1 + returns / 100).cumprod()
        cumulative = (equity - 1) * 100

        running_peak = np.maximum.accumulate(
            np.r_[1.0, equity.to_numpy()]
        )[1:]

        drawdown = (
            equity.to_numpy() / running_peak - 1
        ) * 100

        gross_profit = returns[returns > 0].sum()
        gross_loss = -returns[returns < 0].sum()

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else None
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "Historical signals tested",
            f"{len(trades):,}",
        )

        b.metric(
            "Gross win rate",
            f"{(returns > 0).mean() * 100:.1f}%",
        )

        c.metric(
            "Cumulative gross return",
            f"{cumulative.iloc[-1]:+.2f}%",
        )

        d.metric(
            "Max gross drawdown",
            f"{drawdown.min():.2f}%",
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "Average return / trade",
            f"{returns.mean():+.4f}%",
        )

        b.metric(
            "Profit factor",
            (
                f"{profit_factor:.2f}"
                if profit_factor is not None
                else "N/A"
            ),
        )

        c.metric(
            "Profitable historical signals",
            int((returns > 0).sum()),
        )

        d.metric(
            "Unprofitable / flat signals",
            int((returns <= 0).sum()),
        )

        st.markdown("#### Estimated results after trading costs")
        n1, n2, n3, n4 = st.columns(4)
        n1.metric("Net win rate", f"{(net_returns > 0).mean() * 100:.1f}%")
        n2.metric("Cumulative net return", f"{net_cumulative.iloc[-1]:+.2f}%")
        n3.metric("Max net drawdown", f"{net_drawdown.min():.2f}%")
        n4.metric("Net profit factor", f"{net_pf:.2f}" if net_pf is not None else "N/A")
        st.caption(
            "Both equity curves assume sequential 1× notional reinvestment "
            "across non-overlapping trades. This is an illustrative return index, "
            "not a broker account. Estimates exclude swap, financing, market "
            "impact, changing spreads and currency conversion."
        )

        st.markdown("#### Statistical context")
        win_count = int((returns > 0).sum())
        n = len(returns)
        p_hat = win_count / n
        # Wilson 95% interval, descriptive only; independence is not guaranteed.
        z = 1.96
        denom = 1 + z * z / n
        center = (p_hat + z * z / (2 * n)) / denom
        margin = (
            z * np.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))
            / denom
        )
        st.write(
            f"Observed win rate: **{100 * p_hat:.1f}%** across **{n} trades**. "
            f"Approximate Wilson 95% interval: **{100 * (center - margin):.1f}%–"
            f"{100 * (center + margin):.1f}%**."
        )
        st.caption(
            "This interval assumes independent, representative trade outcomes; "
            "markets can violate these assumptions. It does not account for "
            "strategy selection, changing conditions, or trading costs."
        )

        chart_tab, drawdown_tab, distribution_tab = st.tabs(
            [
                "Cumulative return",
                "Drawdown",
                "Trade returns",
            ]
        )

        x = np.arange(1, len(trades) + 1)

        with chart_tab:
            fig = go.Figure()

            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="#64748b",
            )

            fig.add_trace(
                go.Scatter(
                    x=np.r_[0, x],
                    y=np.r_[0, cumulative.to_numpy()],
                    mode="lines",
                    name="Cumulative gross return",
                    line=dict(
                        color="#52b6ff",
                        width=3,
                    ),
                    fill="tozeroy",
                    fillcolor="rgba(82,182,255,0.09)",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=np.r_[0, x],
                    y=np.r_[0, net_cumulative.to_numpy()],
                    mode="lines",
                    name="Cumulative net return",
                    line=dict(color="#55d6ac", width=3),
                )
            )

            fig.update_layout(
                title="Cumulative gross vs estimated net return (%)",
                showlegend=True,
                xaxis_title="Completed trade number",
                yaxis_title="Return (%)",
            )

            st.plotly_chart(
                style_backtest(fig),
                use_container_width=True,
            )

        with drawdown_tab:
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=drawdown,
                    mode="lines",
                    line=dict(
                        color="#ff7894",
                        width=2.5,
                    ),
                    fill="tozeroy",
                    fillcolor="rgba(255,120,148,0.12)",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=x, y=net_drawdown, mode="lines",
                    name="Net drawdown", line=dict(color="#55d6ac", width=2),
                )
            )
            fig.update_layout(
                title="Peak-to-trough gross vs estimated net drawdown (%)",
                showlegend=True,
                xaxis_title="Completed trade number",
                yaxis_title="Drawdown (%)",
            )

            st.plotly_chart(
                style_backtest(fig),
                use_container_width=True,
            )

        with distribution_tab:
            fig = go.Figure(
                go.Histogram(
                    x=returns,
                    nbinsx=30,
                    marker_color="#8a8bff",
                    name="Trades",
                )
            )

            fig.add_trace(
                go.Histogram(
                    x=net_returns,
                    nbinsx=30,
                    opacity=0.55,
                    marker_color="#55d6ac",
                    name="Estimated net",
                )
            )
            fig.update_layout(
                title="Distribution of gross vs net returns",
                showlegend=True,
                barmode="overlay",
                xaxis_title="Return per trade (%)",
                yaxis_title="Number of trades",
                bargap=0.1,
            )

            st.plotly_chart(
                style_backtest(fig),
                use_container_width=True,
            )

        st.markdown(
            "### Historical simulated signal outcomes"
        )

        trade_history = trades.iloc[::-1].copy()

        trade_history["Gross return %"] = (
            trade_history["Gross return %"].round(4)
        )
        trade_history["Estimated cost %"] = trade_history["Estimated cost %"].round(4)
        trade_history["Net return %"] = trade_history["Net return %"].round(4)

        trade_history["Entry"] = (
            trade_history["Entry"].round(5)
        )

        trade_history["Exit"] = (
            trade_history["Exit"].round(5)
        )

        trade_history["Result"] = np.where(
            trade_history["Gross return %"] > 0,
            "WIN",
            np.where(
                trade_history["Gross return %"] < 0,
                "LOSS",
                "FLAT",
            ),
        )

        trade_history = trade_history.drop(
            columns=["Win"]
        )

        st.dataframe(
            trade_history,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "Gross return %": st.column_config.NumberColumn(
                    "Gross return",
                    format="%.4f%%",
                )
            },
        )

        st.download_button(
            "Download historical signals CSV",
            data=trades.to_csv(index=False).encode(),
            file_name="historical_signals.csv",
            mime="text/csv",
        )

        st.warning(
            "This is an in-sample gross-price simulation. "
            "Spreads, fees, slippage and out-of-sample testing "
            "must be added before interpreting profitability."
        )


# ============================================================
# PAGE 4: HISTORICAL ACCURACY
# ============================================================

elif page == "Historical Accuracy":

    st.subheader(
        "Historical Accuracy · Market comparison"
    )

    st.caption(
        "Compares retrospectively simulated historical "
        "signals on the same timeframe and holding period. "
        "This is not forward-tracked prediction accuracy."
    )

    min_trades = st.slider(
        "Minimum historical signals to rank",
        1,
        30,
        10,
    )

    if st.button(
        "Analyze all supported markets",
        type="primary",
    ):
        rows = []
        failures = []
        items = list(ALL.items())
        progress = st.progress(0)

        for j, (name, (ticker, group)) in enumerate(items):
            try:
                market_history = fetch(
                    ticker,
                    interval,
                    period,
                )

                if tf == "4h" and not market_history.empty:
                    market_history = resample_4h(
                        market_history
                    )

                if len(market_history) < 60:
                    failures.append(name)

                else:
                    market_stats = stats(
                        backtest(
                            indicators(market_history),
                            horizon,
                        )
                    )

                    if market_stats:
                        rows.append({
                            "Market": name,
                            "Category": group,
                            **market_stats,
                        })
                    else:
                        failures.append(name)

            except Exception:
                failures.append(name)

            progress.progress(
                (j + 1) / len(items)
            )

        st.session_state["board"] = pd.DataFrame(rows)
        st.session_state["board_key"] = (tf, horizon)
        st.session_state["failures"] = failures

    board = st.session_state.get(
        "board",
        pd.DataFrame(),
    )

    if not board.empty:

        if st.session_state.get("board_key") != (
            tf,
            horizon,
        ):
            st.warning(
                "Timeframe or holding period changed; "
                "rerun the comparison."
            )

        else:
            ranked = board[
                board.Trades >= min_trades
            ].sort_values(
                ["Win rate %", "Trades"],
                ascending=[False, False],
            )

            st.metric(
                "Markets meeting sample threshold",
                len(ranked),
            )

            if ranked.empty:
                st.warning(
                    "No markets meet this trade-count "
                    "threshold. Try Daily candles or "
                    "lower the threshold."
                )

            else:
                st.dataframe(
                    ranked,
                    use_container_width=True,
                    hide_index=True,
                )

                chart = px.bar(
                    ranked.head(15),
                    x="Market",
                    y="Win rate %",
                    color="Category",
                    template="plotly_dark",
                )

                chart.update_layout(
                    paper_bgcolor="#080d18",
                    plot_bgcolor="#111b2c",
                    height=400,
                )

                st.plotly_chart(
                    chart,
                    use_container_width=True,
                )

                st.download_button(
                    "Download leaderboard CSV",
                    data=ranked.to_csv(index=False),
                    file_name="accuracy_leaderboard.csv",
                    mime="text/csv",
                )

            if st.session_state.get("failures"):
                st.caption(
                    "Unavailable/insufficient data: "
                    + ", ".join(
                        st.session_state["failures"]
                    )
                )

    else:
        st.caption(
            "Click Analyze all supported markets "
            "to begin the comparison."
        )


# ============================================================
# PAGE 5: PREDICTION HISTORY & FORWARD ACCURACY
# ============================================================

elif page == "Prediction History":

    st.subheader(
        "Prediction History & Forward Accuracy"
    )

    st.caption(
        "Verified forward tracking only. "
        "Historical backtest signals are never imported here."
    )

    if not config():
        st.warning(
            "Prediction storage is not connected. "
            "Check your Supabase configuration."
        )

    else:
        st.success(
            "Supabase prediction storage connected."
        )

        # ----------------------------------------------------
        # SAVE PREDICTION
        # ----------------------------------------------------

        st.markdown(
            "### Save a new forward prediction"
        )

        # Use penultimate candle as a conservative anchor.
        anchor = df.iloc[-2]
        anchor_time = pd.Timestamp(df.index[-2])

        if anchor_time.tzinfo is None:
            anchor_time = anchor_time.tz_localize("UTC")
        else:
            anchor_time = anchor_time.tz_convert("UTC")

        anchor_signal = (
            "BUY" if bool(anchor.Buy)
            else "SELL" if bool(anchor.Sell)
            else "WAIT"
        )

        st.write(
            f"**{label}** · {tf} · {anchor_signal} · {strategy_label} · "
            f"reference close "
            f"{fmt_price(float(anchor.Close), market)}"
        )

        st.caption(
            f"Signal bar: {anchor_time.isoformat()}. "
            "WAIT is an abstention and does not count "
            "towards directional accuracy."
        )

        prediction_horizon = st.number_input(
            "Evaluate after N subsequent candles",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
        )

        if st.button(
            "Save forward prediction",
            type="primary",
        ):
            try:
                payload = {
                    "instrument": label,
                    "ticker": symbol,
                    "timeframe": tf,
                    "signal": anchor_signal,
                    "model_version": MODEL_VERSION,
                    "signal_bar_at": anchor_time.isoformat(),
                    "reference_close": float(anchor.Close),
                    "horizon_bars": int(prediction_horizon),
                }

                save_prediction(payload)

                st.success(
                    "Prediction saved. "
                    "GitHub Actions will evaluate it "
                    "when future candle data is available."
                )

            except Exception as exc:
                st.error(
                    f"Could not save prediction: {exc}"
                )

        # ----------------------------------------------------
        # AUTOMATIC EVALUATION STATUS
        # ----------------------------------------------------

        st.markdown(
            "### Automatic prediction evaluation"
        )

        st.caption(
            "GitHub Actions is configured to check "
            "pending predictions hourly. "
            "Actual execution times may vary."
        )

        if st.button("Refresh prediction history"):
            st.rerun()

        # ----------------------------------------------------
        # LOAD SUPABASE HISTORY
        # ----------------------------------------------------

        try:
            records = list_predictions()
            history = pd.DataFrame(records)

            if history.empty:
                st.info(
                    "No saved predictions yet. "
                    "Save your first prediction above."
                )

            else:
                history["signal"] = (
                    history["signal"].fillna("WAIT")
                )

                history["status"] = (
                    history["status"].fillna("pending")
                )

                if "model_version" not in history.columns:
                    history["model_version"] = "unknown"

                history["model_version"] = (
                    history["model_version"].fillna("unknown")
                )

                # --------------------------------------------
                # FORWARD PERFORMANCE METRICS
                # --------------------------------------------

                group_columns = [
                    "instrument",
                    "timeframe",
                    "model_version",
                ]

                board, scored, directional = (
                    forward_leaderboard(
                        history,
                        group_columns,
                    )
                )

                pending = directional[
                    directional["status"] == "pending"
                ]

                unavailable = directional[
                    directional["status"] == "unavailable"
                ]

                waits = history[
                    history["signal"] == "WAIT"
                ]

                completed = history[
                    history["status"] == "evaluated"
                ]

                evaluated_count = len(scored)

                correct_count = (
                    int(scored["correct"].sum())
                    if evaluated_count
                    else 0
                )

                incorrect_count = (
                    evaluated_count - correct_count
                )

                accuracy = (
                    100 * correct_count / evaluated_count
                    if evaluated_count
                    else None
                )

                coverage = (
                    100 * evaluated_count / len(directional)
                    if len(directional)
                    else None
                )

                st.markdown(
                    "### Forward performance overview"
                )

                a, b, c, d = st.columns(4)

                a.metric(
                    "Total saved",
                    len(history),
                )

                b.metric(
                    "Evaluated BUY/SELL",
                    evaluated_count,
                )

                c.metric(
                    "Verified accuracy",
                    (
                        f"{accuracy:.1f}%"
                        if accuracy is not None
                        else "—"
                    ),
                )

                d.metric(
                    "Pending BUY/SELL",
                    len(pending),
                )

                a, b, c, d = st.columns(4)

                a.metric(
                    "Correct",
                    correct_count,
                )

                b.metric(
                    "Incorrect",
                    incorrect_count,
                )

                c.metric(
                    "WAIT abstentions",
                    len(waits),
                )

                d.metric(
                    "Evaluation coverage",
                    (
                        f"{coverage:.1f}%"
                        if coverage is not None
                        else "—"
                    ),
                )

                st.caption(
                    "Directional accuracy excludes WAIT "
                    "signals and pending predictions. "
                    "Coverage compares scored BUY/SELL "
                    "predictions against all saved BUY/SELL "
                    "predictions, including unavailable ones."
                )

                # --------------------------------------------
                # FORWARD ACCURACY LEADERBOARD
                # --------------------------------------------

                st.markdown(
                    "### Forward Accuracy Leaderboard"
                )

                left, right = st.columns(2)

                with left:
                    group_by = st.selectbox(
                        "Compare predictions by",
                        [
                            "Market + Timeframe + Strategy",
                            "Market",
                            "Timeframe",
                            "Strategy",
                        ],
                        key="forward_group_by",
                    )

                with right:
                    min_samples = st.slider(
                        "Minimum evaluated predictions",
                        min_value=1,
                        max_value=100,
                        value=10,
                        key="forward_min_samples",
                    )

                group_options = {
                    "Market + Timeframe + Strategy": [
                        "instrument",
                        "timeframe",
                        "model_version",
                    ],
                    "Market": ["instrument"],
                    "Timeframe": ["timeframe"],
                    "Strategy": ["model_version"],
                }

                selected_groups = group_options[group_by]

                leaderboard, _, _ = forward_leaderboard(
                    history,
                    selected_groups,
                )

                if leaderboard.empty:
                    st.info(
                        "No evaluated BUY/SELL predictions yet. "
                        "Your evaluated WAIT prediction does not "
                        "count as correct or incorrect."
                    )

                else:
                    ranked = leaderboard[
                        leaderboard["Predictions"] >= min_samples
                    ].sort_values(
                        ["Accuracy %", "Predictions"],
                        ascending=[False, False],
                    )

                    if ranked.empty:
                        st.warning(
                            "No groups meet the minimum sample "
                            "threshold. Lower the slider to "
                            "explore early results."
                        )

                    else:
                        st.dataframe(
                            ranked,
                            use_container_width=True,
                            hide_index=True,
                        )

                        chart_data = ranked.head(15).copy()

                        chart_data["Group"] = (
                            chart_data[selected_groups]
                            .astype(str)
                            .agg(" · ".join, axis=1)
                        )

                        fig = px.bar(
                            chart_data,
                            x="Group",
                            y="Accuracy %",
                            color="Predictions",
                            color_continuous_scale="Blues",
                            hover_data=[
                                "Correct",
                                "Incorrect",
                                "Pending",
                                "Unavailable",
                                "WAIT",
                                "Coverage %",
                            ],
                            title="Verified Forward Accuracy",
                            template="plotly_dark",
                        )

                        fig.update_layout(
                            paper_bgcolor="#080d18",
                            plot_bgcolor="#111b2c",
                            font=dict(color="#dce7fa"),
                            height=440,
                            yaxis_range=[0, 100],
                            xaxis_title="",
                            yaxis_title="Directional accuracy (%)",
                            margin=dict(
                                l=25,
                                r=20,
                                t=60,
                                b=100,
                            ),
                        )

                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                        )

                        st.download_button(
                            "Download Forward Leaderboard CSV",
                            data=ranked.to_csv(index=False),
                            file_name="forward_accuracy.csv",
                            mime="text/csv",
                        )

                # --------------------------------------------
                # CORRECT VS INCORRECT CHART
                # --------------------------------------------

                st.markdown(
                    "### Prediction outcomes"
                )

                if evaluated_count:
                    outcome_data = pd.DataFrame({
                        "Outcome": [
                            "Correct",
                            "Incorrect",
                        ],
                        "Count": [
                            correct_count,
                            incorrect_count,
                        ],
                    })

                    fig = px.pie(
                        outcome_data,
                        names="Outcome",
                        values="Count",
                        hole=0.65,
                        color="Outcome",
                        color_discrete_map={
                            "Correct": "#36d6b0",
                            "Incorrect": "#fa718b",
                        },
                        template="plotly_dark",
                    )

                    fig.update_layout(
                        paper_bgcolor="#080d18",
                        plot_bgcolor="#111b2c",
                        height=340,
                        margin=dict(
                            l=20,
                            r=20,
                            t=20,
                            b=20,
                        ),
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

                else:
                    st.caption(
                        "Outcome chart will appear after "
                        "the first BUY or SELL prediction "
                        "has been evaluated."
                    )

                # --------------------------------------------
                # SAVED PREDICTION HISTORY
                # --------------------------------------------

                st.markdown(
                    "### Saved prediction history"
                )

                show = [
                    "recorded_at",
                    "instrument",
                    "timeframe",
                    "model_version",
                    "signal",
                    "horizon_bars",
                    "status",
                    "reference_close",
                    "outcome_close",
                    "directional_return_pct",
                    "correct",
                ]

                show = [
                    column
                    for column in show
                    if column in history.columns
                ]

                st.dataframe(
                    history[show],
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )

                st.download_button(
                    "Download Prediction History CSV",
                    data=history.to_csv(index=False),
                    file_name="forex_prediction_history.csv",
                    mime="text/csv",
                )

        except Exception as exc:
            st.error(
                f"Could not load prediction history: {exc}"
            )

    st.info(
        "Forward accuracy measures directional correctness "
        "against the saved reference close, not executable "
        "trading profitability. Results may be affected by "
        "market data delays, candle timing, transaction "
        "costs and small sample sizes."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Forex Intelligence {APP_VERSION} · "
    "Experimental research tool · "
    "Data may be delayed, incomplete or revised · "
    "Historical gross backtests are not evidence "
    "of future profitability."
)
