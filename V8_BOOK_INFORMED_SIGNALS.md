# V8.0 — Book-informed signal engine research

**Status: new candidate committed, accuracy NOT established.** V5 and V7 historical runs did not validate any of the previous six models. V8 is separately versioned, so old predictions and model-specific performance remain intact.

## Source ideas and what is actually implemented

User-supplied source texts revisited for this implementation:

- Christopher Weaver, *The 4 Keys to Profitable Forex Trend Trading*: continuation trades in the direction of a trend, trend lines, channels, Fibonacci and triangle confirmations. In V8 we use only the **trend-continuation and confirmation principles**, NOT a complete geometric trend-line or Fibonacci method.
- Jode Lebin, *Trade Like Pro: The Ultimate Trading*: top-down market context, supply/demand location, zone freshness and avoiding buying high in the curve or selling low. In V8 we use a **prior 40-bar range location proxy** and avoid upper/lower extremes in the unfavourable direction. The app **does not** detect genuine fresh/original supply/demand zones yet.
- FalconFX strategy handbooks: impulsive versus corrective phases and identifying continuation versus reversal. In V8 we approximate an **opposite-colour correction over the previous two candles** and a **current directional continuation candle**. This is NOT the complete discretionary Falcon strategy and does not make claims about institutional order flow.

The exact numeric thresholds (EMA periods 20/50, ATR ratio 0.12, correction tolerance, 40-bar location, wick/body thresholds) are **software research assumptions**, not thresholds directly quoted from these texts. They must not be optimized repeatedly against the same inspected EUR/USD/15-pair dataset and then marketed as proven.

## V8 registered candidate

Version: `trend-pullback-confluence-v1`.

A completed-bar **BUY** requires:
1. EMA20 > EMA50, EMA50 rising over five bars, and separated by > 0.12 ATR;
2. A bearish correction within the preceding two bars approaching EMA20 and not grossly violating EMA50;
3. Current bullish candle closes above prior close and EMA20;
4. Candle body >= 0.18 ATR, candle range between 0.45 and 3 ATR;
5. Current close below 85% of the PRIOR 40-bar high/low range (avoid chasing the upper extreme).

**SELL** uses the symmetric bearish trend/correction/impulse logic, and requires price above 15% of the prior 40-bar range.

**WAIT** is a normal outcome when these filters do not align. The terminal separately displays a **BUY bias / SELL bias / Neutral** based only on trend evidence. **A bias is not a BUY/SELL entry and is never automatically saved as one.** For other selected models, the bias shown is a basic EMA context label.

All signal model versions are unchanged except the introduction of this new seventh model; forward collection skips WAIT by default. Versioned forward collection records the new model, and historical benchmarking automatically includes it through `MODEL_LABELS`.

## How to measure improvement

1. Run GitHub Actions -> **V8 Signal Engine Tests**, and ensure the full unittest suite and static release gate are green.
2. Run **Research V5 Strategy Benchmarks** using 5y and 5 bars. It now includes the new model. Compare trade frequency and estimated **net** returns at the same 4 bps assumptions. Because this data has been repeatedly examined during development, the result is exploratory only.
3. Use **Research V5.5 Predictor Readiness** to test 2/5/10-bar holding horizons under 0/4/10 bps assumed costs. Any positive backtest remains unvalidated.
4. Use **Collect forward predictions**, with `dry_run=true` first, to inspect market-by-market signals, then let the scheduled collector save new versioned BUY/SELL forecasts.
5. Monitor **V6 Forward Prediction Evidence** after genuinely future candles complete. Compare evaluated sample sizes and possible accuracy degradation; do not claim an edge from small or overlapping/correlated samples.

## Known limitations

- This remains a daily-candle mechanical strategy, **not** a true multi-timeframe implementation. It uses only OHLC proxies; it does not ingest economic-calendar events, broker liquidity, tick spreads or institutional orders.
- A model may still show WAIT often, especially on a quiet or strongly extended candle. Generating a SELL every day because a trend is bearish can create false trading signals. Bias is therefore separated.
- This release does not provide calibrated probability, guaranteed accuracy, broker execution, stop-loss execution or trading recommendations.
- The V7 static release gate has been updated to expect the seventh registered research model. Existing historical models and data remain version-identifiable.

**Release principle:** prefer an honest WAIT and a descriptive directional bias over a fabricated high-confidence BUY or SELL.
