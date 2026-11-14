"""Versioned, deterministic research signal models (not investment advice)."""
import pandas as pd

BASELINE_VERSION = "ema20-ema50-engulf-v1"
MOMENTUM_VERSION = "ema-rsi-momentum-v1"


def momentum_signals(candles):
    """Trend direction plus RSI, MACD and candle-body confirmation.

    Experimental alternative to engulfing, with no fitted parameters.
    Signals are calculated per bar from historical information only.
    """
    close = candles["Close"]
    open_ = candles["Open"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gains / losses.replace(0, float("nan")))
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    histogram = macd - macd.ewm(span=9, adjust=False).mean()
    warm = pd.Series(range(len(candles)), index=candles.index) >= 50
    buy = (warm & (ema20 > ema50) & (close > ema20)
           & rsi.between(52, 75) & (histogram > 0) & (close > open_))
    sell = (warm & (ema20 < ema50) & (close < ema20)
            & rsi.between(25, 48) & (histogram < 0) & (close < open_))
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool)
