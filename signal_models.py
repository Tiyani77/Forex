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


# V5 book-informed, mechanical research candidates. These are interpretations
# of structural concepts, not verbatim proprietary/discretionary rule sets.
CHANNEL_VERSION = "weaver-channel-breakout-v1"
SUPPLY_DEMAND_VERSION = "lebin-supply-demand-rejection-v1"


def _atr(candles, period=14):
    high, low, close = candles["High"], candles["Low"], candles["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def channel_breakout_signals(candles):
    """Research interpretation of trend-continuation channel breakouts.

    20-bar channel boundaries are shifted one bar back: the signal bar
    may close outside the PREVIOUS channel, not a channel including itself.
    An EMA slope/trend check requires directional continuation.
    No future candle, swing confirmation or outcome is referenced.
    """
    close = candles["Close"]
    high, low = candles["High"], candles["Low"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    prior_high = high.shift(1).rolling(20, min_periods=20).max()
    prior_low = low.shift(1).rolling(20, min_periods=20).min()
    atr = _atr(candles)
    candle_body = (close - candles["Open"]).abs()
    normal_body = candle_body >= 0.25 * atr
    warm = pd.Series(range(len(candles)), index=candles.index) >= 60
    buy = (warm & (close > prior_high) & (ema20 > ema50)
           & (ema20 > ema20.shift(3)) & (close > candles["Open"])
           & normal_body)
    sell = (warm & (close < prior_low) & (ema20 < ema50)
            & (ema20 < ema20.shift(3)) & (close < candles["Open"])
            & normal_body)
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool)


def supply_demand_rejection_signals(candles):
    """Research interpretation of supply/demand pullback confirmation.

    The previous 20-bar range (excluding the current bar) is the zone
    proxy. A lower/upper quartile touch followed by a directional close,
    together with an existing EMA trend, is treated as rejection.
    Actual discretionary fresh/original supply-demand zones require
    richer structure analysis; this proxy does not claim equivalence.
    """
    high, low = candles["High"], candles["Low"]
    close, open_ = candles["Close"], candles["Open"]
    prior_high = high.shift(1).rolling(20, min_periods=20).max()
    prior_low = low.shift(1).rolling(20, min_periods=20).min()
    width = prior_high - prior_low
    demand_ceiling = prior_low + 0.25 * width
    supply_floor = prior_high - 0.25 * width
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    atr = _atr(candles)
    meaningful = (width > 0) & (atr > 0)
    warm = pd.Series(range(len(candles)), index=candles.index) >= 60
    buy = (warm & meaningful & (ema20 > ema50)
           & (low <= demand_ceiling) & (close > demand_ceiling)
           & (close > open_) & (close > low + 0.6 * (high - low)))
    sell = (warm & meaningful & (ema20 < ema50)
            & (high >= supply_floor) & (close < supply_floor)
            & (close < open_) & (close < high - 0.6 * (high - low)))
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool)


# Corrected V5.2 channel model. V1 remains unchanged for auditability.
# In v1 the bearish EMA slope comparison pointed the wrong way, so the
# revised model must get a fresh version ID for independently scored records.
CHANNEL_V2_VERSION = "weaver-channel-breakout-v2"


def channel_breakout_v2_signals(candles):
    """Fixed bearish trend slope; all other published v1 thresholds retained."""
    close = candles["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    prior_high = candles["High"].shift(1).rolling(20, min_periods=20).max()
    prior_low = candles["Low"].shift(1).rolling(20, min_periods=20).min()
    atr = _atr(candles)
    body = (close - candles["Open"]).abs()
    warm = pd.Series(range(len(candles)), index=candles.index) >= 60
    buy = (
        warm & (close > prior_high) & (ema20 > ema50)
        & (ema20 > ema20.shift(3))
        & (close > candles["Open"]) & (body >= 0.25 * atr)
    )
    sell = (
        warm & (close < prior_low) & (ema20 < ema50)
        & (ema20 < ema20.shift(3))
        & (close < candles["Open"]) & (body >= 0.25 * atr)
    )
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool)


# V5.2: operationalised market-structure breakout plus retest.
# Structural level on signal bar uses the highest high / lowest low of the
# prior 20 bars (excludes current bar) and a previous structural breach.
# A retest entry must emerge within three bars AFTER a breach; no future bars
# are needed for the current decision.
STRUCTURE_VERSION = "falcon-structure-retest-v1"


def structure_retest_signals(candles):
    """Candidate inspired by Falcon continuation / price-action structure.

    One event is a break beyond the previous 20-bar swing envelope.
    Within the following 1-3 bars, price must touch that broken level and
    close back on the continuation side with a confirming candle body.
    Break level is frozen on the breakout bar; shifting the event makes
    the retest causal. Not a claim to implement complete Falcon patterns.
    """
    close = candles["Close"]
    open_ = candles["Open"]
    high = candles["High"]
    low = candles["Low"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    prev_high = high.shift(1).rolling(20, min_periods=20).max()
    prev_low = low.shift(1).rolling(20, min_periods=20).min()
    atr = _atr(candles)

    break_up = (close > prev_high) & (ema20 > ema50)
    break_down = (close < prev_low) & (ema20 < ema50)
    # Break was identified on an earlier completed bar, not current.
    # Only the MOST RECENT breakout in the lookback can trigger one retest.
    recent_up = break_up.shift(1, fill_value=False) | break_up.shift(
        2, fill_value=False
    ) | break_up.shift(3, fill_value=False)
    recent_down = break_down.shift(1, fill_value=False) | break_down.shift(
        2, fill_value=False
    ) | break_down.shift(3, fill_value=False)

    last_break_up_level = pd.Series(float("nan"), index=candles.index)
    last_break_down_level = pd.Series(float("nan"), index=candles.index)
    for k in (3, 2, 1):
        last_break_up_level = last_break_up_level.where(
            ~break_up.shift(k, fill_value=False), prev_high.shift(k)
        )
        last_break_down_level = last_break_down_level.where(
            ~break_down.shift(k, fill_value=False), prev_low.shift(k)
        )

    small_buffer = 0.10 * atr
    bullish = (
        recent_up & (ema20 > ema50)
        & (low <= last_break_up_level + small_buffer)
        & (close > last_break_up_level)
        & (close > open_)
        & (close > close.shift(1))
    )
    bearish = (
        recent_down & (ema20 < ema50)
        & (high >= last_break_down_level - small_buffer)
        & (close < last_break_down_level)
        & (close < open_)
        & (close < close.shift(1))
    )
    # Three prior bars plus indicators; independent of future market data.
    warm = pd.Series(range(len(candles)), index=candles.index) >= 60
    return (
        (warm & bullish).fillna(False).astype(bool),
        (warm & bearish).fillna(False).astype(bool),
    )


MODEL_LABELS = {
    BASELINE_VERSION: "EMA + Engulfing (original)",
    MOMENTUM_VERSION: "EMA + RSI + MACD (experimental)",
    CHANNEL_VERSION: "Channel Breakout (book-informed research)",
    CHANNEL_V2_VERSION: "Channel Breakout V2 (corrected research)",
    SUPPLY_DEMAND_VERSION: "Supply/Demand Rejection (book-informed research)",
    STRUCTURE_VERSION: "Market Structure Retest (Falcon-inspired research)",
}


def apply_research_model(candles, model_version):
    """Return deterministic per-candle BUY/SELL flags for supported candidates."""
    if model_version == MOMENTUM_VERSION:
        return momentum_signals(candles)
    if model_version == CHANNEL_VERSION:
        return channel_breakout_signals(candles)
    if model_version == CHANNEL_V2_VERSION:
        return channel_breakout_v2_signals(candles)
    if model_version == SUPPLY_DEMAND_VERSION:
        return supply_demand_rejection_signals(candles)
    if model_version == STRUCTURE_VERSION:
        return structure_retest_signals(candles)
    raise ValueError(f"Unsupported research model: {model_version}")
