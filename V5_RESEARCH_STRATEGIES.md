# Forex Intelligence V5.0 — Book-informed predictor research

**Status:** Experimental research only; no demonstrated out-of-sample improvement. The initial versions below are deterministic *operationalisations* of ideas from books supplied by the project owner. They are not faithful reproductions of full discretionary training programmes, and they do not assert that a book's author recommends these exact thresholds.

## Sources and concepts

- Christopher Weaver, *The 4 Keys to Profitable Forex Trend Trading* (uploaded PDF): trend lines, channels, Fibonacci retracements, and symmetrical triangles; continuation, bounce, and break entries. This first iteration implements only the **channel break / trend continuation** concept.
- Jode Lebin, *Trade Like Pro: The Ultimate Trading Kit to Master Supply & Demand* (uploaded PDF): price action, multi-timeframe trend, supply/demand zones, reaction confirmation, fresh/overlapping zones, and risk/reward. This first iteration implements a **prior-range rejection proxy**, not a verified fresh/original zone or full multi-timeframe system.
- *Falcon Trading Strategy / FalconFX Strategy Handbook* (uploaded PDF): market structure, continuation vs reversal, plan, discipline, risk management. These themes inform the research approach, but we have **not yet claimed to reproduce Falcon chart patterns mechanically**.

## New independently versioned models

### Channel Breakout — `weaver-channel-breakout-v1`
- Calculate previous **20 bars'** highest high / lowest low, excluding the candidate signal bar.
- Require an actual close beyond that historical channel.
- Require EMA20/EMA50 trend alignment and a three-bar EMA20 slope in the same direction.
- Require directional candle body at least **0.25 × ATR(14)** to exclude tiny breakouts.
- Use a 60-candle warm-up and signal only after the bar completes.

### Supply / Demand Rejection — `lebin-supply-demand-rejection-v1`
- Use the previous 20 bars' high/low range as an **approximate zone proxy**, not an institutionally originated supply/demand zone.
- Define demand as the bottom quarter and supply as the top quarter of that range.
- Require a touch into that quarter followed by a close back out, a directional candle, and a close inside its rejection-side 40%.
- Require EMA20/EMA50 trend alignment and 60-candle warm-up.

Both models have BUY, SELL and WAIT (no qualifying signal) outputs. They are deterministic, independent of the existing original EMA + Engulfing and experimental EMA + RSI + MACD strategies, and can be compared in Historical Backtesting.

## How validation should work

1. **No look-ahead**: signal decisions use only the candidate bar and earlier bars. Unit tests compare full-series signals against truncated historical prefixes.
2. **Comparable outcomes**: same entry/exit horizon, non-overlapping trade policy and cost assumptions for all four strategies.
3. **Retrospective splits are NOT independent evidence**: results observed during model development, including any 70/30 split or rolling windows, are exploratory.
4. **Forward evidence**: nightly collection records new model-versioned daily forecasts in Supabase. Only predictions actually recorded before their outcome become valid forward evidence. WAITs do not count as wins.
5. **No promotion without evidence**: inspect enough evaluated forecasts across markets/time periods, uncertain intervals, trading costs, drawdown and baseline comparisons before relying on any model. Win rate alone is not profitability.

## Scope intentionally deferred

- Hand-drawn trendlines/channels from multiple confirmed pivots
- Fresh institutional supply/demand levels and order blocks
- Falcon complex continuation/reversal pattern geometry
- Fibonacci confluence, symmetrical triangles, multi-timeframe alignment
- Liquidity sweeps, QM/MPL patterns
- Stop-loss, execution-price, and risk/reward simulation

All require their own explicit rules, independent tests, and evidence. No untested filter should be silently labelled “accuracy improving.”

## V5.1 benchmark results and V5.2 response

The 15-pair, five-year daily benchmark supplied by the user produced these **later-period** observations (5-bar horizon, estimated 4 bps round trip):

| Model | Trades | Median market net win rate | Median market average net return | Markets with positive average |
| --- | ---: | ---: | ---: | ---: |
| EMA+RSI+MACD | 342 | 45.0% | -0.08150% | 3 / 15 |
| EMA+Engulfing | 10 | 50.0% | +0.29141% | 5 / 15 |
| Supply/Demand rejection | 124 | 41.67% | -0.10548% | 2 / 15 |
| Channel breakout | 0 | N/A | N/A | 0 / 15 |

Because these results have been used during development, the later period can no longer be represented as independent unexamined validation for subsequent new models. They are diagnostics, not forecasts of success.

### V5.2: Falcon-inspired market structure retest

New independently versioned `falcon-structure-retest-v1` candidate:

- Detect close through the prior 20-bar high/low envelope, excluding the current bar.
- Within the following three bars, look for a touch and directional rejection of that frozen breakout level.
- Confirm EMA20/EMA50 trend alignment and directional closing strength.
- No future observations may influence a historical signal.
- Keep the existing four versions unchanged. V5.2 forecasts are saved under a separate model version.

**Important correction:** An initial diagnosis of a SELL EMA-slope issue in channel breakout v1 was mistaken: inspection confirms v1 already requires a falling EMA20 for SELL. A redundant proposed v2 was removed before release. Do not describe the existing channel model as containing a bearish-slope bug.

Next validation: re-run Research V5 Strategy Benchmarks, compare trade frequency and estimated net performance across markets, and collect future predictions for independent forward evaluation. No model is promoted or labelled more accurate based on these findings alone.
