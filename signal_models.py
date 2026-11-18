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


# V5.3: liquidity-sweep and reclaim research candidate. This is a
# mechanical wick/rejection proxy, not an identified institutional order.
LIQUIDITY_SWEEP_VERSION = "liquidity-sweep-reclaim-v1"


def liquidity_sweep_reclaim_signals(candles):
    """Detect a completed-bar run beyond a PRIOR extreme and rejection.

    BUY: current low sweeps the lowest low of the preceding 15 candles,
    the close reclaims that level, the candle is bullish and closes in
    its upper half, the lower wick >= 0.15 ATR(14), and EMA20 is not
    falling over three bars. SELL is symmetric for the prior high.

    Only information on/before the signal bar is used; a wick touching
    an extreme without a close back inside does not qualify.
    """
    high, low = candles["High"], candles["Low"]
    open_, close = candles["Open"], candles["Close"]
    prior_low = low.shift(1).rolling(15, min_periods=15).min()
    prior_high = high.shift(1).rolling(15, min_periods=15).max()
    ema20 = close.ewm(span=20, adjust=False).mean()
    atr = _atr(candles)
    span = high - low
    lower_wick = open_.where(open_ < close, close) - low
    upper_wick = high - open_.where(open_ > close, close)
    valid = (
        pd.Series(range(len(candles)), index=candles.index).ge(60)
        & (span > 0) & (atr > 0)
    )
    buy = (
        valid & (low < prior_low) & (close > prior_low)
        & (close > open_) & (close >= low + 0.5 * span)
        & (lower_wick >= 0.15 * atr)
        & (ema20 >= ema20.shift(3))
    )
    sell = (
        valid & (high > prior_high) & (close < prior_high)
        & (close < open_) & (close <= high - 0.5 * span)
        & (upper_wick >= 0.15 * atr)
        & (ema20 <= ema20.shift(3))
    )
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool)


# V8.0 research: book-informed confluence of trend, correction, and
# resumed impulse. Exact numerical thresholds are NEW mechanical assumptions,
# NOT rules supplied verbatim by Weaver, Lebin, or FalconFX.
CONFLUENCE_VERSION = "trend-pullback-confluence-v1"


def confluence_diagnostics(candles):
    """Causal bias and independently actionable pullback continuation flags.

    1. Trend context: EMA20/50 alignment plus slowly moving EMA50 slope.
    2. Previous completed bars show a counter-trend correction toward EMA20.
    3. Current completed bar reclaims EMA20 with a directional candle
       and closes beyond the prior close.
    4. Exclude extended prices near the unfavorable extremes of the previous
       40-bar range (a coarse location proxy, NOT a real supply/demand zone).
    5. Require normal candle body, sufficient volatility, and trend separation.

    WAIT is intentionally allowed; directional bias is always reported
    separately when there is a strong trend.
    """
    close = candles["Close"]
    open_ = candles["Open"]
    high, low = candles["High"], candles["Low"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    atr = _atr(candles)
    prev_high = high.shift(1).rolling(40, min_periods=40).max()
    prev_low = low.shift(1).rolling(40, min_periods=40).min()
    span = (prev_high - prev_low).where(lambda v: v > 0)
    location = (close - prev_low) / span

    trend_up = (
        (ema20 > ema50) & (ema50 > ema50.shift(5))
        & ((ema20 - ema50) > 0.12 * atr)
    )
    trend_down = (
        (ema20 < ema50) & (ema50 < ema50.shift(5))
        & ((ema50 - ema20) > 0.12 * atr)
    )
    # The correction happened on one of the PREVIOUS two bars.
    pullback_up = (
        ((close.shift(1) < open_.shift(1))
         | (close.shift(2) < open_.shift(2)))
        & (low.shift(1) <= ema20.shift(1) + .35 * atr.shift(1))
        & (close.shift(1) > ema50.shift(1) - .45 * atr.shift(1))
    )
    pullback_down = (
        ((close.shift(1) > open_.shift(1))
         | (close.shift(2) > open_.shift(2)))
        & (high.shift(1) >= ema20.shift(1) - .35 * atr.shift(1))
        & (close.shift(1) < ema50.shift(1) + .45 * atr.shift(1))
    )
    strong_body = (close - open_).abs() >= .18 * atr
    normal_range = (high - low >= .45 * atr) & (high - low <= 3 * atr)
    enough = pd.Series(range(len(candles)), index=candles.index) >= 65
    valid = enough & atr.gt(0) & span.notna() & strong_body & normal_range

    buy = (
        valid & trend_up & pullback_up & (close > open_)
        & (close > close.shift(1)) & (close > ema20)
        & location.lt(.85)
    )
    sell = (
        valid & trend_down & pullback_down & (close < open_)
        & (close < close.shift(1)) & (close < ema20)
        & location.gt(.15)
    )
    bias = pd.Series("NEUTRAL", index=candles.index, dtype="object")
    bias.loc[trend_up] = "BULLISH"
    bias.loc[trend_down] = "BEARISH"
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool), bias


def confluence_signals(candles):
    buy, sell, _ = confluence_diagnostics(candles)
    return buy, sell


# V8.1: a separate, mechanically simpler pullback/reclaim candidate.
# V8.0 is preserved as a frozen, testable historical research version.
# Changes here are hypotheses addressing the V8.0 zero-signal failure,
# not performance-optimised parameters or a faithful proprietary system.
PULLBACK_V2_VERSION = "trend-pullback-reclaim-v2"


def pullback_v2_diagnostics(candles):
    """Trend + recently tested EMA20 + completed-bar reclaim (causal).

    Countertrend candles and EMA20 tests must occur within the PREVIOUS
    three bars; current bar must close back with the prevailing trend.
    A maximum EMA20 distance rejects runaway extended moves without the
    previous 40-bar range location filter that starved the V8.0 signals.
    All comparisons use bars available at the signal candle close.
    """
    close = candles["Close"]
    open_ = candles["Open"]
    high, low = candles["High"], candles["Low"]
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    atr = _atr(candles)
    eligible = (pd.Series(range(len(candles)), index=candles.index) >= 65) & atr.gt(0)

    rising = (ema20 > ema50) & (ema50 > ema50.shift(5))
    falling = (ema20 < ema50) & (ema50 < ema50.shift(5))
    # Countertrend correction and level test can occur on different bars
    # within the completed three-bar correction phase.
    recent_bear = (
        (close.shift(1) < open_.shift(1))
        | (close.shift(2) < open_.shift(2))
        | (close.shift(3) < open_.shift(3))
    )
    recent_bull = (
        (close.shift(1) > open_.shift(1))
        | (close.shift(2) > open_.shift(2))
        | (close.shift(3) > open_.shift(3))
    )
    tested_support = (
        (low.shift(1) <= ema20.shift(1) + .50 * atr.shift(1))
        | (low.shift(2) <= ema20.shift(2) + .50 * atr.shift(2))
        | (low.shift(3) <= ema20.shift(3) + .50 * atr.shift(3))
    )
    tested_resistance = (
        (high.shift(1) >= ema20.shift(1) - .50 * atr.shift(1))
        | (high.shift(2) >= ema20.shift(2) - .50 * atr.shift(2))
        | (high.shift(3) >= ema20.shift(3) - .50 * atr.shift(3))
    )
    body_ok = (close - open_).abs() >= .10 * atr
    distance_ok = (close - ema20).abs() <= 1.5 * atr

    buy = (
        eligible & rising & recent_bear & tested_support
        & (close > open_) & (close > close.shift(1)) & (close > ema20)
        & body_ok & distance_ok
    )
    sell = (
        eligible & falling & recent_bull & tested_resistance
        & (close < open_) & (close < close.shift(1)) & (close < ema20)
        & body_ok & distance_ok
    )
    bias = pd.Series("NEUTRAL", index=candles.index, dtype="object")
    bias.loc[rising] = "BULLISH"
    bias.loc[falling] = "BEARISH"
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool), bias


def pullback_v2_signals(candles):
    buy, sell, _ = pullback_v2_diagnostics(candles)
    return buy, sell


# V8.4: close-to-close confirmed continuation research candidate.
# The V8.3 Yahoo FX audit found unreliable daily Open/Close bodies.
# This model intentionally NEVER reads candle Open, High or Low.
# It uses only observed Close history and fixed, disclosed thresholds.
CLOSE_CONFIRM_VERSION = "close-trend-pullback-v1"


def close_trend_diagnostics(candles):
    """Causal daily close trend + pullback + close-change confirmation.

    Book-inspired interpretation of trend/correction/impulse, not a full
    implementation of FalconFX, Weaver or Lebin discretionary strategies.
    Directional bias is separate from an actionable completed-bar flag.
    """
    close = candles["Close"].astype(float)
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    change = close.diff()
    # Causal, robust price-move scale: preceding 20 absolute changes;
    # current bar never enters the scale used to confirm itself.
    scale = change.abs().shift(1).rolling(20, min_periods=20).median()
    ready = (
        pd.Series(range(len(candles)), index=candles.index).ge(65)
        & scale.gt(0) & close.gt(0)
    )
    up = (ema20 > ema50) & (ema50 > ema50.shift(5))
    down = (ema20 < ema50) & (ema50 < ema50.shift(5))
    # Recent correction is countertrend in CLOSE-TO-CLOSE terms.
    pullback_buy = (
        (change.shift(1) < 0) | (change.shift(2) < 0)
        | (change.shift(3) < 0)
    )
    pullback_sell = (
        (change.shift(1) > 0) | (change.shift(2) > 0)
        | (change.shift(3) > 0)
    )
    # Require the recent correction to approach the 20-bar mean, not
    # simply an arbitrary opposite-colour Open/Close daily candle.
    near_mean_buy = pd.concat([
        (close.shift(k) - ema20.shift(k)).abs()
        <= 1.25 * scale.shift(k) for k in (1, 2, 3)
    ], axis=1).any(axis=1)
    near_mean_sell = near_mean_buy
    confirmation_buy = (
        change >= .40 * scale
    ) & (close > ema20) & (
        (close - ema20) <= 2.5 * scale
    )
    confirmation_sell = (
        change <= -.40 * scale
    ) & (close < ema20) & (
        (ema20 - close) <= 2.5 * scale
    )
    buy = ready & up & pullback_buy & near_mean_buy & confirmation_buy
    sell = ready & down & pullback_sell & near_mean_sell & confirmation_sell
    bias = pd.Series("NEUTRAL", index=candles.index, dtype="object")
    bias.loc[up] = "BULLISH"
    bias.loc[down] = "BEARISH"
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool), bias


def close_trend_signals(candles):
    buy, sell, _ = close_trend_diagnostics(candles)
    return buy, sell


MODEL_LABELS = {
    BASELINE_VERSION: "EMA + Engulfing (original)",
    MOMENTUM_VERSION: "EMA + RSI + MACD (experimental)",
    CHANNEL_VERSION: "Channel Breakout (book-informed research)",
    SUPPLY_DEMAND_VERSION: "Supply/Demand Rejection (book-informed research)",
    STRUCTURE_VERSION: "Market Structure Retest (Falcon-inspired research)",
    LIQUIDITY_SWEEP_VERSION: "Liquidity Sweep + Reclaim (V5.3 research)",
    CONFLUENCE_VERSION: "Trend + Pullback Confluence (book-informed V8 research)",
    PULLBACK_V2_VERSION: "Trend Pullback + Reclaim (V8.1 research)",
    CLOSE_CONFIRM_VERSION: "Close Trend + Pullback (V8.4 FX data-safe research)",
}


def apply_research_model(candles, model_version):
    """Return deterministic per-candle BUY/SELL flags for supported candidates."""
    if model_version == MOMENTUM_VERSION:
        return momentum_signals(candles)
    if model_version == CHANNEL_VERSION:
        return channel_breakout_signals(candles)
    if model_version == SUPPLY_DEMAND_VERSION:
        return supply_demand_rejection_signals(candles)
    if model_version == STRUCTURE_VERSION:
        return structure_retest_signals(candles)
    if model_version == LIQUIDITY_SWEEP_VERSION:
        return liquidity_sweep_reclaim_signals(candles)
    if model_version == CONFLUENCE_VERSION:
        return confluence_signals(candles)
    if model_version == PULLBACK_V2_VERSION:
        return pullback_v2_signals(candles)
    if model_version == CLOSE_CONFIRM_VERSION:
        return close_trend_signals(candles)
    raise ValueError(f"Unsupported research model: {model_version}")
