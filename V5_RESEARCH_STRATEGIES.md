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

## V5.2 diagnostic results (reported 2026-11-15)

The same 15 FX pairs, five-year daily candles, five-bar horizon and 4 bps assumed transaction costs yielded:

| Version | Later-period trades | Median market net win rate | Median market average net return | Positive-mean markets |
| --- | ---: | ---: | ---: | ---: |
| `falcon-structure-retest-v1` | 30 | 33.33% | -0.11618% | 6/15 |

Its earlier development window had 19 trades in 11 markets, median market net win rate 0%, and median average net return -0.36270%. This *does not establish* an advantage. The later period was examined during development; it should not be described as untouched or prospective evidence for new versions.

## V5.3: Liquidity sweep + reclaim research candidate

**Version:** `liquidity-sweep-reclaim-v1` — distinct from all earlier versions.

A causal mechanical approximation of liquidity sweeps / false breakouts, broadly related to price-action and structural level concepts from the supplied trading books. **Not** a faithful representation of discretionary order flow, institutionally verified liquidity, or the complete Falcon/Lebin approaches.

Signal-bar requirements (evaluated at completed candle close):

- Prior reference high/low: extreme of the **previous 15 candles** only (the current candle is excluded with `shift(1)`).
- BUY: low breaks previous 15-bar low, then closes **back above** that level; bullish candle, close in upper half, lower wick >= 0.15 × ATR(14), EMA20 nondecreasing over three candles.
- SELL: high breaks previous 15-bar high, then closes **back below** that level; bearish candle, close in lower half, upper wick >= 0.15 × ATR(14), EMA20 nonincreasing over three candles.
- At least 60 candles of prior warm-up; otherwise WAIT. No look-ahead or future bar confirmation.
- Default research benchmark: trade next candle open and close five bars after the signal, with a fixed 4 bps indicative round-trip cost.

The 15-bar threshold and other numerical conditions are **research assumptions**, not numbers quoted from the books. They were fixed when the candidate was written and are not claimed to have an empirically established edge.

### Evaluation gates

The research workflow runs no-look-ahead/unit checks and produces chronological comparisons on the same 15 markets; such retrospective diagnostics are *not* independent prospective evidence. The existing strategy versions and stored predictions remain untouched. A useful live confidence claim requires accumulating genuine new, versioned forward predictions and accounting for correlation, uncertain win-rate intervals, trading costs and risk.

## V5.3 diagnostic observed on 2026-11-15

The 15-pair daily V5.3 benchmark reports:
- `liquidity-sweep-reclaim-v1`: **44 later-period trades** across 14 markets; median market net win rate **10.00%**, median market average net return **-0.39391%**, only **2/15** positive-mean markets.
- Its development-period sample was 13 trades across 7 markets, median net win rate 0%, median market mean net -0.21519%.
- **No benefit is established.** Do not automatically make liquidity-sweep predictions the default. Do not tune numerical levels merely to fit the repeatedly inspected 15-pair data.

## V5.4: predeclared robustness checks

The dedicated `Research V5.4 Predictor Robustness` GitHub Actions workflow tests **all existing versioned models without modifying their signal rules**. Predeclared axes are holding horizons of **2, 5, 10 daily bars** and approximate round-trip trading costs of **0, 4, 10 basis points**. A chronological 70/30 development/later-period split is retained, but we only report the later-period diagnostics because this period has already been observed by the developer.

**Two different measurements are shown**:
- Gross direction-correct rate: share of simulated trades whose entry-to-exit price change favoured the model's chosen BUY/SELL direction, *without* cost deductions.
- Net win rate: share with a positive simulated net return *after* the declared basis-point cost.

This distinction is essential: the independently saved forward-prediction `correct` field is based on signal-close to outcome-close direction, while historical simulation here uses **next-bar open** for entry; they are not directly interchangeable.

The script reports number of actual trades and markets with trades. If a model has no trades, do **not** interpret NaN / missing metrics as zero accuracy. Changing the horizon changes non-overlapping trade selection, so differences are scenario sensitivity, not a controlled causal claim.

Outputs: `v54_sensitivity_by_market.csv`, `v54_sensitivity_summary.csv`, `v54_notes.txt`. A positive result after exploring these scenarios is **not** prospective validation; only forecasts timestamped before outcomes can provide that evidence.
