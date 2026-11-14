
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from signal_models import (
    BASELINE_VERSION, MOMENTUM_VERSION, CHANNEL_VERSION,
    SUPPLY_DEMAND_VERSION, MODEL_LABELS, momentum_signals,
    apply_research_model,
)

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

APP_VERSION = "V5.0 Research"
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
[data-testid="stTabs"] [role="tab"],
[data-testid="stTabs"] [role="tab"] * {
    color: #c4d4ee !important;
    opacity: 1 !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],
[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {
    color: #9dcbff !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: #79b7ff !important;
}
/* Keep action labels legible in both light and dark button variants. */
[data-testid="stButton"] button[kind="secondary"],
[data-testid="stDownloadButton"] button {
    color: #172338 !important;
}
[data-testid="stButton"] button[kind="secondary"] *,
[data-testid="stDownloadButton"] button * {
    color: #172338 !important;
}
/* Ensure slider captions remain readable against the dark terminal theme. */
div[data-testid="stSlider"] label,
div[data-testid="stSlider"] label *,
div[data-testid="stSlider"] [data-testid="stWidgetLabel"],
div[data-testid="stSlider"] [data-testid="stWidgetLabel"] * {
    color: #c4d4ee !important;
    opacity: 1 !important;
}
/* Improve visibility of editable numerical cost labels. */
div[data-testid="stNumberInput"] label,
div[data-testid="stNumberInput"] label *,
div[data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
div[data-testid="stNumberInput"] [data-testid="stWidgetLabel"] * {
    color: #c4d4ee !important;
    opacity: 1 !important;
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

    # Descriptive, causal regime labels. Thresholds are research assumptions,
    # not optimised against any future returns.
    true_range = pd.concat(
        [
            df.High - df.Low,
            (df.High - df.Close.shift(1)).abs(),
            (df.Low - df.Close.shift(1)).abs(),
        ], axis=1,
    ).max(axis=1)
    atr14 = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    atr_pct_series = 100 * atr14 / df.Close.replace(0, np.nan)
    # Previous 60 completed observations only: the current candle is excluded
    # from the volatility threshold, avoiding any future look-ahead.
    volatility_cutoff = (
        atr_pct_series.rolling(60, min_periods=30).quantile(0.75).shift(1)
    )
    high_vol = atr_pct_series > volatility_cutoff
    trending = (df.EMA20 - df.EMA50).abs() > (0.7 * atr14)
    sufficient = volatility_cutoff.notna() & (atr14 > 0)
    df["Regime"] = np.select(
        [sufficient & high_vol, sufficient & trending],
        ["High volatility", "Trending"],
        default="Sideways",
    )
    df.loc[~sufficient, "Regime"] = "Insufficient history"

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
            "Exit time": str(df.index[i + horizon]),
            "Regime": str(df["Regime"].iloc[i]) if "Regime" in df else "Unknown",
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
        showlegend=bool(fig.layout.showlegend),
        legend=dict(font=dict(color="#e5efff", size=13), bgcolor="rgba(16,26,43,0.88)", bordercolor="#34445d", borderwidth=1),
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
    list(MODEL_LABELS.values()),
    help="Book-informed research candidates are unvalidated.",
)
MODEL_VERSION = next(
    version for version, name in MODEL_LABELS.items()
    if name == strategy_label
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
if MODEL_VERSION != BASELINE_VERSION:
    df["Buy"], df["Sell"] = apply_research_model(df, MODEL_VERSION)
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
            MODEL_LABELS[MODEL_VERSION] + " research signal"
            if signal != "WAIT" else
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
        if MODEL_VERSION in (CHANNEL_VERSION, SUPPLY_DEMAND_VERSION):
            signal_description = (
                "Book-informed price-structure research candidate. "
                "Not a verified forecasting advantage."
            )
        elif MODEL_VERSION == MOMENTUM_VERSION:
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

    # Market regime observations use the conservative penultimate bar.
    # This prevents an in-progress Yahoo candle from being labelled final.
    st.markdown("### Market regime intelligence")
    regime_anchor = df.iloc[-2]
    current_regime = str(regime_anchor["Regime"])
    anchor_timestamp = pd.Timestamp(df.index[-2])
    if anchor_timestamp.tzinfo is None:
        anchor_timestamp = anchor_timestamp.tz_localize("UTC")
    else:
        anchor_timestamp = anchor_timestamp.tz_convert("UTC")

    regime_explanations = {
        "Trending": (
            "The EMA20–EMA50 separation is relatively large "
            "compared with recent average price movement."
        ),
        "Sideways": (
            "EMA separation is relatively small compared "
            "with recent average price movement."
        ),
        "High volatility": (
            "ATR as a share of price exceeds its recent "
            "historical 75th-percentile threshold."
        ),
        "Insufficient history": (
            "There are not enough completed observations "
            "to establish the rolling volatility threshold."
        ),
    }
    st.caption(
        f"Last conservatively selected candle: {anchor_timestamp.isoformat()}. "
        "Descriptive research classification, not a live market quote."
    )
    rcol1, rcol2, rcol3 = st.columns([1.2, 1, 1])
    with rcol1:
        st.metric("Observed market regime", current_regime)
    with rcol2:
        st.metric("Selected strategy", MODEL_LABELS[MODEL_VERSION].split(" (")[0])
    with rcol3:
        st.metric("Regime evidence", "Retrospective only")

    st.write(regime_explanations.get(current_regime, "Regime classification unavailable."))

    # Research-only historical net results use a transparent fixed default of
    # 4 basis points per round trip (2 spread + 1 slippage each side).
    # They do not alter the collector, signal rules or saved predictions.
    regime_trades = backtest(df, horizon, spread_bps=2.0, slippage_bps=1.0)
    regime_subset = (
        regime_trades.loc[regime_trades["Regime"] == current_regime]
        if not regime_trades.empty else regime_trades
    )
    regime_n = len(regime_subset)
    if current_regime == "Insufficient history":
        st.info(
            "Current regime cannot be classified reliably yet. "
            "Historical regime-specific comparisons are unavailable."
        )
    elif regime_n == 0:
        st.info(
            "No completed historical trades for the selected strategy "
            "in this regime and timeframe. There is no regime-specific "
            "performance estimate."
        )
    else:
        regime_net = regime_subset["Net return %"].astype(float)
        regime_win_pct = 100 * float((regime_net > 0).mean())
        regime_avg_pct = float(regime_net.mean())
        a_reg, b_reg, c_reg = st.columns(3)
        a_reg.metric("Historical regime trades", regime_n)
        b_reg.metric("Historical net win rate", f"{regime_win_pct:.1f}%")
        c_reg.metric("Average estimated net / trade", f"{regime_avg_pct:+.3f}%")
        st.caption(
            "Indicative net results use 2 bps round-trip spread plus "
            "1 bp slippage per side (4 bps total). "
            "This cost scenario is fixed on the Trading Terminal; "
            "adjustable assumptions are on Historical Backtesting."
        )
        if regime_n < 30:
            st.warning(
                f"Only {regime_n} historical trade(s) occurred in this regime. "
                "This is too little evidence to establish a reliable advantage. "
                "The selected BUY/SELL/WAIT signal is not changed."
            )
        elif regime_avg_pct <= 0:
            st.warning(
                "Average estimated historical net return in this regime "
                "was not positive. That does not predict the outcome "
                "of the current signal."
            )
        else:
            st.info(
                "Historical average net return was positive in this regime, "
                "but is not a calibrated prediction or probability of profit."
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
        legend=dict(
            orientation="h", y=1.09,
            font=dict(color="#edf3ff", size=13),
            bgcolor="rgba(17,27,44,0.95)",
            bordercolor="#34445d", borderwidth=1,
        ),
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

        st.markdown("#### V5.0 · Book-informed candidate benchmark")
        st.caption(
            "Two mechanical interpretations of your trading books: "
            "trend-continuation channel breakouts (Christopher Weaver) "
            "and price rejection near prior supply/demand range zones "
            "(Jode Lebin, with Falcon-style structure context). "
            "These are experimental, not verified implementations of "
            "complete discretionary book strategies. All models use the "
            "same retrospective bars, holding period and estimated costs."
        )
        v5_rows = []
        for version in MODEL_LABELS:
            candidate = indicators(raw)
            if version != BASELINE_VERSION:
                candidate["Buy"], candidate["Sell"] = apply_research_model(
                    candidate, version
                )
            bt = backtest(
                candidate, horizon, spread_bps, slippage_bps, commission_bps
            )
            values = (
                bt["Net return %"].astype(float)
                if not bt.empty else pd.Series(dtype=float)
            )
            v5_rows.append({
                "Research model": MODEL_LABELS[version],
                "Signals tested": len(bt),
                "Net win %": round(100 * (values > 0).mean(), 1)
                if len(values) else None,
                "Avg net %": round(float(values.mean()), 4)
                if len(values) else None,
                "Net cumulative %": round(
                    float(((1 + values / 100).prod() - 1) * 100), 3
                ) if len(values) else None,
                "Evidence": "No trades" if not len(bt)
                else "Small sample" if len(bt) < 30
                else "Retrospective only",
            })
        st.dataframe(
            pd.DataFrame(v5_rows), hide_index=True,
            use_container_width=True,
        )
        st.warning(
            "This is model development on historical data, not independent "
            "validation. No new model has been proven more accurate; "
            "compare it against the original baselines before live use."
        )

        st.markdown("#### Compare both strategies on identical price history")
        st.caption(
            "Both strategies use the same fetched candles, holding period, "
            "next-open entries, and cost assumptions. Trade dates and counts "
            "may differ. This is an in-sample, retrospective comparison."
        )
        baseline_df = indicators(raw)
        momentum_df = baseline_df.copy()
        momentum_df["Buy"], momentum_df["Sell"] = momentum_signals(momentum_df)

        comparison_rows = []
        for model_name, version, comparison_df in (
            ("EMA + Engulfing", BASELINE_VERSION, baseline_df),
            ("EMA + RSI + MACD", MOMENTUM_VERSION, momentum_df),
        ):
            compared = backtest(
                comparison_df, horizon, spread_bps, slippage_bps, commission_bps
            )
            if compared.empty:
                comparison_rows.append({
                    "Strategy": model_name, "Model": version, "Trades": 0,
                    "Gross win %": None, "Net win %": None,
                    "Avg net %": None, "Cumulative net %": None,
                    "Max net drawdown %": None, "Net profit factor": None,
                })
                continue

            cr = compared["Net return %"].astype(float)
            cg = compared["Gross return %"].astype(float)
            ce = (1 + cr / 100).cumprod()
            cp = np.maximum.accumulate(np.r_[1.0, ce.to_numpy()])[1:]
            gains = cr[cr > 0].sum()
            losses = -cr[cr < 0].sum()
            comparison_rows.append({
                "Strategy": model_name,
                "Model": version,
                "Trades": len(cr),
                "Gross win %": round(100 * (cg > 0).mean(), 1),
                "Net win %": round(100 * (cr > 0).mean(), 1),
                "Avg net %": round(float(cr.mean()), 4),
                "Cumulative net %": round(float((ce.iloc[-1] - 1) * 100), 2),
                "Max net drawdown %": round(float(((ce.to_numpy() / cp) - 1).min() * 100), 2),
                "Net profit factor": round(float(gains / losses), 2)
                if losses > 0 else None,
            })

        comparison_table = pd.DataFrame(comparison_rows)
        # Undefined ratios are not zero; make them readable in the display.
        comparison_display = comparison_table.copy()
        comparison_display["Net profit factor"] = comparison_display[
            "Net profit factor"
        ].apply(lambda value: f"{float(value):.2f}" if pd.notna(value) else "N/A")
        st.dataframe(comparison_display, hide_index=True, use_container_width=True)
        st.caption(
            "No strategy is designated a winner: samples are small and this "
            "comparison has not been validated out-of-sample."
        )

        st.markdown("#### Chronological development vs holdout validation")
        st.caption(
            "A fixed calendar-order split is applied to the same candles for both models. "
            "Indicator warm-up uses earlier candles only. Trades crossing the split are "
            "excluded, so no development outcome finishes in the holdout window. "
            "Both rules were already developed before this test: this is a "
            "retrospective holdout comparison, NOT independent prospective validation."
        )
        development_pct = st.slider(
            "Historical candles assigned to development (%)",
            min_value=50, max_value=85, value=70, step=5,
            key="historical_development_pct",
        )
        split_index = int(len(raw) * development_pct / 100)
        split_index = min(max(split_index, 55), len(raw) - 1)
        cutoff = pd.Timestamp(raw.index[split_index])
        if cutoff.tzinfo is None:
            cutoff = cutoff.tz_localize("UTC")
        else:
            cutoff = cutoff.tz_convert("UTC")
        st.caption(
            f"Holdout begins at {cutoff.date().isoformat()} "
            f"(bar {split_index + 1} of {len(raw)}). "
            "Holding period and trading-cost assumptions match the comparison above."
        )

        holdout_rows = []
        for model_name, version, comparison_df in (
            ("EMA + Engulfing", BASELINE_VERSION, baseline_df),
            ("EMA + RSI + MACD", MOMENTUM_VERSION, momentum_df),
        ):
            all_trades = backtest(
                comparison_df, horizon, spread_bps, slippage_bps, commission_bps
            )
            if all_trades.empty:
                pieces = (("Development", all_trades), ("Holdout", all_trades))
            else:
                signal_dates = pd.to_datetime(all_trades["Signal time"], utc=True)
                exit_dates = pd.to_datetime(all_trades["Exit time"], utc=True)
                pieces = (
                    ("Development", all_trades.loc[exit_dates < cutoff]),
                    ("Holdout", all_trades.loc[signal_dates >= cutoff]),
                )
            for period_name, part in pieces:
                n_part = len(part)
                if not n_part:
                    holdout_rows.append({
                        "Strategy": model_name,
                        "Period": period_name,
                        "Trades": 0,
                        "Net win %": None,
                        "Avg net %": None,
                        "Cumulative net %": None,
                        "Max net drawdown %": None,
                        "Net profit factor": "N/A",
                        "Evidence": "No trades",
                    })
                    continue
                rr = part["Net return %"].astype(float)
                eq = (1 + rr / 100).cumprod()
                peak = np.maximum.accumulate(np.r_[1.0, eq.to_numpy()])[1:]
                gross_gain = rr[rr > 0].sum()
                gross_loss = -rr[rr < 0].sum()
                holdout_rows.append({
                    "Strategy": model_name,
                    "Period": period_name,
                    "Trades": n_part,
                    "Net win %": round(float(100 * (rr > 0).mean()), 1),
                    "Avg net %": round(float(rr.mean()), 4),
                    "Cumulative net %": round(float((eq.iloc[-1] - 1) * 100), 2),
                    "Max net drawdown %": round(
                        float(((eq.to_numpy() / peak) - 1).min() * 100), 2
                    ),
                    "Net profit factor": (
                        f"{gross_gain / gross_loss:.2f}" if gross_loss > 0 else "N/A"
                    ),
                    "Evidence": "Small sample" if n_part < 30 else "Retrospective",
                })
        holdout_table = pd.DataFrame(holdout_rows)
        holdout_display = holdout_table.copy()
        for metric_column in (
            "Net win %", "Avg net %", "Cumulative net %", "Max net drawdown %"
        ):
            holdout_display[metric_column] = holdout_display[
                metric_column
            ].apply(lambda value: f"{float(value):.2f}" if pd.notna(value) else "N/A")
        st.dataframe(holdout_display, hide_index=True, use_container_width=True)
        if any(row["Trades"] < 30 for row in holdout_rows):
            st.warning(
                "At least one segment contains fewer than 30 trades. "
                "Do not infer an edge from its win rate or return; "
                "these samples are particularly unstable."
            )
        st.caption(
            "Changing the split after inspecting the results introduces selection bias. "
            "Prices are Yahoo Finance historical proxies; future tracking in Supabase "
            "remains the independent forward evaluation."
        )

        st.markdown("#### V3.9 · Rolling chronological validation")
        st.caption(
            "Consecutive, non-overlapping evaluation windows for two fixed strategies. "
            "Each window uses signals and outcomes entirely within its date range; "
            "indicator values use only current and prior candles. This is a "
            "walk-forward-style stability check, not a refitted predictive model "
            "or independent forward validation."
        )
        window_count = st.select_slider(
            "Number of chronological evaluation windows",
            options=[3, 4, 5, 6],
            value=4,
            key="rolling_validation_windows",
        )
        first_bar = 50
        last_bar = len(raw) - horizon
        if last_bar - first_bar < window_count:
            st.info("Not enough candles for chronological windows.")
        else:
            edges = np.linspace(
                first_bar, last_bar, window_count + 1, dtype=int
            )
            rolling_rows = []
            for name, version, model_df in (
                ("EMA + Engulfing", BASELINE_VERSION, baseline_df),
                ("EMA + RSI + MACD", MOMENTUM_VERSION, momentum_df),
            ):
                completed = backtest(
                    model_df, horizon, spread_bps, slippage_bps, commission_bps
                )
                if completed.empty:
                    signal_times = pd.Series(dtype="datetime64[ns, UTC]")
                    exit_times = pd.Series(dtype="datetime64[ns, UTC]")
                else:
                    signal_times = pd.to_datetime(
                        completed["Signal time"], utc=True
                    )
                    exit_times = pd.to_datetime(
                        completed["Exit time"], utc=True
                    )
                for window in range(window_count):
                    start = pd.Timestamp(raw.index[edges[window]])
                    end = pd.Timestamp(raw.index[edges[window + 1]])
                    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
                    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
                    # Enforce both signal and exit belong strictly to this window.
                    if completed.empty:
                        part = completed
                    else:
                        part = completed.loc[
                            (signal_times >= start) & (exit_times < end)
                        ]
                    n_window = len(part)
                    if n_window:
                        values = part["Net return %"].astype(float)
                        compounded = float((1 + values / 100).prod() - 1) * 100
                        rolling_win = float((values > 0).mean() * 100)
                    else:
                        compounded = None
                        rolling_win = None
                    rolling_rows.append({
                        "Strategy": name,
                        "Window": window + 1,
                        "Start": str(start.date()),
                        "End (exclusive)": str(end.date()),
                        "Trades": n_window,
                        "Net win %": round(rolling_win, 1) if rolling_win is not None else None,
                        "Cumulative net %": round(compounded, 3) if compounded is not None else None,
                        "Evidence": "Small sample" if n_window else "No trades",
                    })
            rolling = pd.DataFrame(rolling_rows)
            rolling_display = rolling.copy()
            for col in ("Net win %", "Cumulative net %"):
                rolling_display[col] = rolling_display[col].apply(
                    lambda v: f"{float(v):.2f}" if pd.notna(v) else "N/A"
                )
            st.dataframe(
                rolling_display, hide_index=True, use_container_width=True
            )
            chart_data = rolling.loc[rolling["Trades"] > 0].copy()
            if not chart_data.empty:
                chart_data["Window label"] = (
                    "Window " + chart_data["Window"].astype(str)
                )
                fig = px.bar(
                    chart_data, x="Window label", y="Cumulative net %",
                    color="Strategy", barmode="group",
                    title="Estimated net return by chronological window",
                    template="plotly_dark",
                )
                fig.update_layout(
                    paper_bgcolor="#101a2b", plot_bgcolor="#101a2b",
                    font=dict(color="#dce7fa"),
                    legend=dict(font=dict(color="#e5efff")),
                    title_font=dict(color="#f2f6ff"),
                    height=390,
                )
                st.plotly_chart(fig, use_container_width=True)
            st.warning(
                "Rolling window results contain few trades and do not establish "
                "predictive reliability. Window-specific compounding resets in "
                "each segment, and outcomes crossing window edges are excluded."
            )

        st.markdown("#### V4.0 · Market regime analysis")
        st.caption(
            "Mutually exclusive categories determined at each signal candle: "
            "high volatility when ATR(14) as a percentage of price exceeds the "
            "previous 60-bar 75th percentile; otherwise trending when the "
            "absolute EMA20–EMA50 gap exceeds 0.7 × ATR(14); otherwise sideways. "
            "High volatility takes priority. The first observations without "
            "sufficient threshold history are excluded. These are descriptive "
            "thresholds, not an optimised regime predictor."
        )
        regime_names = ("Trending", "Sideways", "High volatility")
        regime_rows = []
        for model_name, model_df in (
            ("EMA + Engulfing", baseline_df),
            ("EMA + RSI + MACD", momentum_df),
        ):
            model_trades = backtest(
                model_df, horizon, spread_bps, slippage_bps, commission_bps
            )
            for regime_name in regime_names:
                part = (
                    model_trades.loc[model_trades["Regime"] == regime_name]
                    if not model_trades.empty else model_trades
                )
                count = len(part)
                if not count:
                    regime_rows.append({
                        "Strategy": model_name, "Regime": regime_name,
                        "Trades": 0, "Net win %": None,
                        "Average net %": None, "Cumulative net %": None,
                        "Net profit factor": None, "Evidence": "No trades",
                    })
                    continue
                values = part["Net return %"].astype(float)
                positive = values.loc[values > 0].sum()
                negative = -values.loc[values < 0].sum()
                compounded = ((1 + values / 100).prod() - 1) * 100
                regime_rows.append({
                    "Strategy": model_name, "Regime": regime_name,
                    "Trades": count,
                    "Net win %": round(float(100 * (values > 0).mean()), 1),
                    "Average net %": round(float(values.mean()), 4),
                    "Cumulative net %": round(float(compounded), 3),
                    "Net profit factor": round(float(positive / negative), 2)
                    if negative > 0 else None,
                    "Evidence": "Small sample" if count < 30 else "Retrospective",
                })

        regime_table = pd.DataFrame(regime_rows)
        regime_display = regime_table.copy()
        for metric in (
            "Net win %", "Average net %", "Cumulative net %", "Net profit factor"
        ):
            regime_display[metric] = regime_display[metric].apply(
                lambda value: f"{float(value):.2f}" if pd.notna(value) else "N/A"
            )
        st.dataframe(regime_display, hide_index=True, use_container_width=True)
        available_regimes = regime_table.loc[regime_table["Trades"] > 0]
        if not available_regimes.empty:
            regime_chart = px.bar(
                available_regimes, x="Regime", y="Average net %",
                color="Strategy", barmode="group",
                title="Average estimated net return per trade by market regime",
                template="plotly_dark",
                category_orders={"Regime": list(regime_names)},
            )
            regime_chart.update_layout(
                paper_bgcolor="#101a2b", plot_bgcolor="#101a2b",
                font=dict(color="#dce7fa"),
                title_font=dict(color="#f2f6ff"),
                legend=dict(font=dict(color="#e5efff")),
                height=390,
            )
            st.plotly_chart(regime_chart, use_container_width=True)
        st.warning(
            "Regime samples can be very small and market conditions are "
            "not stable through time. These retrospective groupings must "
            "not be used to claim that a strategy works reliably in a "
            "particular regime. Live Supabase forward accuracy remains separate."
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
            trade_history["Net return %"] > 0,
            "WIN",
            np.where(
                trade_history["Net return %"] < 0,
                "LOSS",
                "FLAT",
            ),
        )

        trade_history = trade_history.drop(
            columns=["Win", "Net win"]
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
                ),
                "Estimated cost %": st.column_config.NumberColumn(
                    "Estimated costs",
                    format="%.4f%%",
                ),
                "Net return %": st.column_config.NumberColumn(
                    "Estimated net return",
                    format="%.4f%%",
                ),
            },
        )

        st.download_button(
            "Download historical signals CSV",
            data=trades.to_csv(index=False).encode(),
            file_name="historical_signals.csv",
            mime="text/csv",
        )

        st.warning(
            "This is an in-sample simulation with hypothetical trading "
            "costs, not an executable broker performance record. "
            "Out-of-sample validation is still required."
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

        # For daily predictions use the latest completed candle, matching
        # automatic collection. Other timeframes retain the conservative
        # penultimate-candle convention.
        anchor_index = -2
        if tf == "1d":
            latest_start = pd.to_datetime(df.index[-1], utc=True)
            if latest_start + pd.Timedelta(days=1) <= pd.Timestamp.now(tz="UTC"):
                anchor_index = -1
        anchor = df.iloc[anchor_index]
        anchor_time = pd.Timestamp(df.index[anchor_index])

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
                # FORWARD MONITORING: LIVE DATABASE RECORDS ONLY
                # --------------------------------------------

                st.markdown("### Forward prediction monitor")
                st.caption(
                    "These are genuine stored forecasts, not reconstructed "
                    "historical signals. A prediction remains pending until "
                    "the evaluator confirms its specified future outcome. "
                    "No expected completion date is assumed because candles, "
                    "weekends and provider updates vary."
                )

                directional_monitor = history[
                    history["signal"].isin(["BUY", "SELL"])
                ].copy()
                monitored_count = len(directional_monitor)
                monitored_pending = int(
                    (directional_monitor["status"] == "pending").sum()
                )
                monitored_unavailable = int(
                    (directional_monitor["status"] == "unavailable").sum()
                )
                monitored_evaluated = int(
                    (directional_monitor["status"] == "evaluated").sum()
                )

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Tracked BUY / SELL", monitored_count)
                m2.metric("Awaiting outcome", monitored_pending)
                m3.metric("Evaluated", monitored_evaluated)
                m4.metric("Unavailable", monitored_unavailable)

                if monitored_count:
                    st.progress(
                        monitored_evaluated / monitored_count,
                        text=(
                            f"Forward evaluation progress: "
                            f"{monitored_evaluated} of {monitored_count} "
                            "directional forecasts evaluated"
                        ),
                    )
                    status_order = ("pending", "evaluated", "unavailable")
                    monitor_grouped = (
                        directional_monitor.groupby(
                            ["model_version", "status"], dropna=False
                        ).size().unstack(fill_value=0)
                    )
                    monitor_grouped = monitor_grouped.reindex(
                        columns=list(status_order), fill_value=0
                    )
                    monitor_grouped["Total BUY/SELL"] = monitor_grouped.sum(axis=1)
                    monitor_grouped["Evaluation %"] = (
                        100 * monitor_grouped["evaluated"]
                        / monitor_grouped["Total BUY/SELL"]
                    ).round(1)
                    monitor_grouped = monitor_grouped.reset_index()
                    monitor_grouped = monitor_grouped.rename(columns={
                        "model_version": "Strategy",
                        "pending": "Pending",
                        "evaluated": "Evaluated",
                        "unavailable": "Unavailable",
                    })

                    st.markdown("#### Monitoring by strategy")
                    st.dataframe(
                        monitor_grouped,
                        hide_index=True,
                        use_container_width=True,
                    )

                    st.markdown("#### Individual forward predictions")
                    recent = directional_monitor.copy()
                    recent["recorded_at"] = pd.to_datetime(
                        recent["recorded_at"], utc=True, errors="coerce"
                    )
                    recent["signal_bar_at"] = pd.to_datetime(
                        recent["signal_bar_at"], utc=True, errors="coerce"
                    )
                    recent = recent.sort_values(
                        "recorded_at", ascending=False, na_position="last"
                    )
                    recent["Days since recorded"] = (
                        (pd.Timestamp.now(tz="UTC") - recent["recorded_at"])
                        .dt.total_seconds().div(86400).clip(lower=0).round(1)
                    )
                    recent["Outcome"] = recent["status"].map({
                        "pending": "Awaiting future candles",
                        "evaluated": "Evaluated",
                        "unavailable": "Data unavailable",
                    }).fillna("Unknown")

                    monitor_columns = [
                        "recorded_at", "instrument", "signal",
                        "model_version", "timeframe", "signal_bar_at",
                        "horizon_bars", "status", "Days since recorded",
                        "Outcome",
                    ]
                    st.dataframe(
                        recent[monitor_columns].head(100),
                        hide_index=True,
                        use_container_width=True,
                        height=300,
                    )

                    if monitored_pending:
                        st.info(
                            f"{monitored_pending} directional prediction(s) "
                            "are pending. A pending record is not a loss, "
                            "a win or proof of a failed evaluation."
                        )
                    st.caption(
                        "The holding horizon counts subsequent candles, not "
                        "calendar days. 'Days since recorded' is informational "
                        "and is not an estimated settlement countdown. "
                    "Unavailable may include late-recorded historical "
                    "signals excluded from genuine forward scoring."
                    )
                else:
                    st.info(
                        "No saved BUY/SELL predictions yet. "
                        "WAIT is an abstention and is excluded from "
                        "directional performance monitoring."
                    )

                # --------------------------------------------
                # V4.3 FORWARD PERFORMANCE DASHBOARD
                # --------------------------------------------
                st.markdown("### V4.3 · Forward performance dashboard")
                st.caption(
                    "Only Supabase predictions recorded before their outcome "
                    "are used here. WAIT, pending and unavailable records are "
                    "never counted as correct or incorrect. Directional returns "
                    "measure close-to-close moves, not executable trade P&L."
                )
                filter_a, filter_b, filter_c = st.columns(3)
                with filter_a:
                    selected_strategy = st.selectbox(
                        "Strategy",
                        ["All strategies"] + sorted(
                            directional_monitor["model_version"]
                            .dropna().astype(str).unique().tolist()
                        ),
                        key="v43_strategy",
                    )
                with filter_b:
                    selected_instrument = st.selectbox(
                        "Market",
                        ["All markets"] + sorted(
                            directional_monitor["instrument"]
                            .dropna().astype(str).unique().tolist()
                        ),
                        key="v43_market",
                    )
                with filter_c:
                    selected_timeframe = st.selectbox(
                        "Timeframe",
                        ["All timeframes"] + sorted(
                            directional_monitor["timeframe"]
                            .dropna().astype(str).unique().tolist()
                        ),
                        key="v43_timeframe",
                    )

                focused = directional_monitor.copy()
                if selected_strategy != "All strategies":
                    focused = focused.loc[
                        focused["model_version"] == selected_strategy
                    ]
                if selected_instrument != "All markets":
                    focused = focused.loc[
                        focused["instrument"] == selected_instrument
                    ]
                if selected_timeframe != "All timeframes":
                    focused = focused.loc[
                        focused["timeframe"] == selected_timeframe
                    ]

                focused_scored = focused.loc[
                    (focused["status"] == "evaluated")
                    & focused["correct"].notna()
                ].copy()
                # Supabase may return boolean values as Python bools or strings.
                correctness_map = {
                    True: 1, False: 0, 1: 1, 0: 0,
                    "true": 1, "false": 0, "True": 1, "False": 0,
                }
                focused_scored["win"] = (
                    focused_scored["correct"].map(correctness_map)
                )
                focused_scored = focused_scored.dropna(subset=["win"]).copy()
                focused_scored["win"] = focused_scored["win"].astype(int)

                focus_total = len(focused)
                focus_evaluated = len(focused_scored)
                focus_pending = int((focused["status"] == "pending").sum())
                focus_unavailable = int(
                    (focused["status"] == "unavailable").sum()
                )
                focus_accuracy = (
                    100 * focused_scored["win"].mean()
                    if focus_evaluated else None
                )
                fm1, fm2, fm3, fm4 = st.columns(4)
                fm1.metric("Filtered forecasts", focus_total)
                fm2.metric("Evaluated BUY/SELL", focus_evaluated)
                fm3.metric(
                    "Directional accuracy",
                    f"{focus_accuracy:.1f}%" if focus_accuracy is not None
                    else "—",
                )
                fm4.metric("Pending / unavailable",
                           f"{focus_pending} / {focus_unavailable}")

                if focus_evaluated:
                    # Wilson interval is descriptive and does not address
                    # market dependence or strategy selection bias.
                    successes = int(focused_scored["win"].sum())
                    n = focus_evaluated
                    p = successes / n
                    z = 1.96
                    d = 1 + z * z / n
                    center = (p + z * z / (2 * n)) / d
                    half_width = (
                        z * np.sqrt(
                            p * (1 - p) / n + z * z / (4 * n * n)
                        ) / d
                    )
                    st.caption(
                        f"Observed accuracy: {successes}/{n} correctly "
                        f"predicted directions. Approximate Wilson 95% "
                        f"interval: {100 * (center - half_width):.1f}%–"
                        f"{100 * (center + half_width):.1f}%. "
                        "Trade outcomes may be correlated, so the interval "
                        "is not a guarantee of future performance."
                    )
                    if n < 30:
                        st.warning(
                            f"Only {n} evaluated directional forecasts in "
                            "this selection. Too few to infer a reliable edge."
                        )

                    returns_focus = pd.to_numeric(
                        focused_scored["directional_return_pct"],
                        errors="coerce",
                    ).dropna()
                    if not returns_focus.empty:
                        rr1, rr2 = st.columns(2)
                        rr1.metric(
                            "Mean directional price move",
                            f"{returns_focus.mean():+.3f}%",
                        )
                        rr2.metric(
                            "Median directional price move",
                            f"{returns_focus.median():+.3f}%",
                        )
                        st.caption(
                            "Signed price movement relative to the saved "
                            "reference close; excludes spreads, execution "
                            "costs, leverage, sizing and financing."
                        )

                    st.markdown("#### Accuracy as outcomes accumulate")
                    scored_timeline = focused_scored.copy()
                    scored_timeline["outcome_bar_at"] = pd.to_datetime(
                        scored_timeline["outcome_bar_at"],
                        utc=True, errors="coerce",
                    )
                    scored_timeline["evaluated_at"] = pd.to_datetime(
                        scored_timeline["evaluated_at"],
                        utc=True, errors="coerce",
                    )
                    scored_timeline["Timeline date"] = (
                        scored_timeline["outcome_bar_at"].fillna(
                            scored_timeline["evaluated_at"]
                        )
                    )
                    scored_timeline = scored_timeline.dropna(
                        subset=["Timeline date"]
                    ).sort_values(
                        ["Timeline date", "recorded_at"]
                    )
                    if not scored_timeline.empty:
                        scored_timeline["Evaluated count"] = np.arange(
                            1, len(scored_timeline) + 1
                        )
                        scored_timeline["Running accuracy %"] = (
                            scored_timeline["win"].cumsum()
                            / scored_timeline["Evaluated count"] * 100
                        )
                        fig = px.line(
                            scored_timeline,
                            x="Evaluated count", y="Running accuracy %",
                            markers=True,
                            title="Cumulative directional accuracy by evaluated forecast",
                            template="plotly_dark",
                            hover_data=["Timeline date", "instrument", "signal"],
                        )
                        fig.update_layout(
                            paper_bgcolor="#101a2b",
                            plot_bgcolor="#101a2b",
                            font=dict(color="#dce7fa"),
                            title_font=dict(color="#f2f6ff"),
                            yaxis=dict(range=[0, 100]),
                            height=370,
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(
                            "Forecasts are ordered by their outcome candle "
                            "(or evaluation timestamp when missing), not "
                            "by when a backtest would have generated them."
                        )
                else:
                    st.info(
                        "No evaluated BUY/SELL forecasts match these filters "
                        "yet. Accuracy and its trend will appear once future "
                        "outcomes have been recorded. Pending is not a loss."
                    )
                if focus_total:
                    status_summary = (
                        focused.groupby("status").size()
                        .reindex(
                            ["pending", "evaluated", "unavailable"],
                            fill_value=0,
                        ).rename_axis("Status").reset_index(name="Predictions")
                    )
                    status_summary = status_summary.loc[
                        status_summary["Predictions"] > 0
                    ]
                    fig = px.bar(
                        status_summary, x="Status", y="Predictions",
                        text="Predictions",
                        title="Forward prediction status in selection",
                        template="plotly_dark",
                    )
                    fig.update_layout(
                        paper_bgcolor="#101a2b",
                        plot_bgcolor="#101a2b",
                        font=dict(color="#dce7fa"),
                        title_font=dict(color="#f2f6ff"),
                        height=320, showlegend=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("No saved directional records match the filters.")

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
                        "WAIT predictions do not count as correct or incorrect."
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

                history_display = history[show].copy()
                # Display empty outcomes clearly without changing stored values.
                for nullable_col in (
                    "outcome_close", "directional_return_pct", "correct"
                ):
                    if nullable_col in history_display:
                        history_display[nullable_col] = history_display[
                            nullable_col
                        ].apply(
                            lambda value: "—"
                            if pd.isna(value)
                            else (
                                f"{value:.5f}"
                                if isinstance(value, (int, float))
                                and not isinstance(value, bool)
                                else str(value)
                            )
                        )
                st.dataframe(
                    history_display,
                    use_container_width=True,
                    hide_index=True,
                    height=min(420, 40 + 36 * (len(history_display) + 1)),
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
