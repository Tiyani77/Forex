"""V7.0 shared, versioned signal logic for terminal, collector and research.

These functions only inspect provided OHLC candles, never future candles.
Legacy model versions and thresholds are intentionally preserved.
"""
import pandas as pd

from signal_models import BASELINE_VERSION, MODEL_LABELS, apply_research_model


def baseline_signals(candles):
    """Unchanged EMA20/EMA50 + full body engulfing rules (legacy v1)."""
    previous = candles.shift(1)
    ema20 = candles["Close"].ewm(span=20, adjust=False).mean()
    ema50 = candles["Close"].ewm(span=50, adjust=False).mean()
    bullish = (
        (previous["Close"] < previous["Open"])
        & (candles["Close"] > candles["Open"])
        & (candles["Open"] <= previous["Close"])
        & (candles["Close"] >= previous["Open"])
    )
    bearish = (
        (previous["Close"] > previous["Open"])
        & (candles["Close"] < candles["Open"])
        & (candles["Open"] >= previous["Close"])
        & (candles["Close"] <= previous["Open"])
    )
    return (
        ((ema20 > ema50) & bullish).fillna(False).astype(bool),
        ((ema20 < ema50) & bearish).fillna(False).astype(bool),
    )


def model_flags(candles, model_version):
    """Single dispatcher for every supported research strategy."""
    if model_version == BASELINE_VERSION:
        return baseline_signals(candles)
    if model_version not in MODEL_LABELS:
        raise ValueError(f"Unknown model version: {model_version}")
    return apply_research_model(candles, model_version)


def latest_completed_position(candles, timeframe="1d", now=None):
    """Return latest completed-bar position, or None for insufficient data.

    Daily bars use the original UTC date-label + one calendar day rule.
    Intraday conservatively excludes the newest bar as in the existing app.
    This is a data-provider convention, not a claim of market-session hours.
    """
    if candles is None or len(candles) < 2:
        return None
    if timeframe != "1d":
        return len(candles) - 2
    now = (pd.Timestamp.now(tz="UTC") if now is None
           else pd.to_datetime(now, utc=True))
    times = pd.to_datetime(candles.index, utc=True)
    completed = times + pd.Timedelta(days=1) <= now
    positions = [i for i, flag in enumerate(completed) if flag]
    return positions[-1] if positions else None


def signal_label(buy, sell):
    if bool(buy) and bool(sell):
        raise ValueError("Conflicting BUY and SELL on the same bar")
    return "BUY" if bool(buy) else "SELL" if bool(sell) else "WAIT"


def latest_signal(candles, model_version, timeframe="1d", now=None,
                  minimum_bars=60):
    """Return a source-identifiable completed-bar signal, or None."""
    position = latest_completed_position(candles, timeframe, now)
    if position is None or position + 1 < minimum_bars:
        return None
    # Evaluate only the observed prefix to protect against accidental
    # use of any current forming bar by future candidate model code.
    completed = candles.iloc[:position + 1]
    buys, sells = model_flags(completed, model_version)
    moment = pd.to_datetime(completed.index[-1], utc=True)
    return {
        "signal": signal_label(buys.iloc[-1], sells.iloc[-1]),
        "signal_bar_at": moment.isoformat(),
        "reference_close": float(completed["Close"].iloc[-1]),
        "position": position,
        "model_version": model_version,
    }
