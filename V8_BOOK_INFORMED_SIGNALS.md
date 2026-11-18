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

## V8.0 zero-trade diagnostic and V8.1 candidate

The November 18, 2026 user-supplied multi-market test of `trend-pullback-confluence-v1` reported **0 trades across 15 FX pairs** in BOTH development and later periods (5y daily candles, five-bar horizon, 4 bps assumed round-trip costs). It therefore has **no estimable historical win rate** and must not be marketed as accurate.

The absence of signals does not identify which specific gate is responsible. V8.1 is a **separate research hypothesis**, not a tuned winning strategy:

- New model version: `trend-pullback-reclaim-v2`.
- Preserve v1 flags and historical model identity exactly.
- Align EMA20/EMA50, require EMA50's five-bar direction to match the candidate trade.
- Look for an opposite-colour correction candle and a test of the EMA20 vicinity in the **previous three completed bars**, rather than insisting on the previous two and a single-bar EMA20 test.
- Confirm the current bar direction, close above (BUY) or below (SELL) EMA20, and a close that advances beyond the previous close.
- Use a normal-sized body (>= 0.10 ATR14) and limit current distance from EMA20 to 1.5 ATR14 to avoid buying/selling a heavily extended move.
- Do not apply the v1 hard 40-bar relative-range-location threshold. This simplifies the entry definition but does NOT prove that filter caused the zero signals.
- Keep trend-only **BUY bias / SELL bias / Neutral** separate from actionable **BUY / SELL / WAIT**.
- Both versions remain independent research candidates in Streamlit, scheduled daily collection, and the retrospective 15-market benchmark.

V8.1 parameters are disclosed, mechanistic assumptions rather than rules quoted verbatim from the books. Tests include artificial bullish and bearish entry constructions, empty candles, finite warmup, causal prefixes, version registration and absence of BUY+SELL overlap. All actual V8.1 forecast accuracy and profitability remain **UNVALIDATED**.

**Next checks:** (1) run **V8 Signal Engine Tests** and check every new V8.1 test; (2) run **Research V5 Strategy Benchmarks** using the original 5y/5-bar/4bps assumptions; (3) inspect the v2 trade count across all markets before considering its returns; (4) collect fresh timestamped versioned forecasts and wait until outcomes become available. These retrospective diagnostics are repeatedly inspected development data and cannot be treated as independent prospective validation.

## V8.1 observed result and V8.2 diagnostic

The later November 18, 2026 user-supplied five-year/15-FX-pair benchmark returned **0 development trades and 2 later-period trades in 2 markets** for `trend-pullback-reclaim-v2`. Its later-period median per-active-market win percentage was 50%, with median market mean net return **-0.61610%** at an estimated four basis-point transaction cost. Two trades cannot support an accuracy claim; V8.1 is not validated.

V8.2 deliberately **does not introduce another trading model or change any signal thresholds**. The separate `diagnose_pullback_v2.py` module compares the existing V8.1 signal code to a cumulative bar-level filter funnel:

- eligible past-bars / ATR
- EMA trend
- recent opposing candle
- recent EMA20 test
- directional reclaim
- adequate body and acceptable extension
- final actual versioned BUY or SELL decision

It checks both directions and both retrospective segments across the same 15 FX pairs. The diagnostic fails closed if the independently reconstructed filters disagree with the versioned model, and emits detailed market CSVs plus combined rows. Counts are bars passing filter conditions, **not trades**; overlapping bars are not combined into trades. The user's previously inspected development and later periods are NOT independent validation. Use the funnel only to locate rare conditions before any separate candidate is proposed.

Run GitHub Actions → **V8.2 Signal Filter Diagnosis** → Run workflow with `5y`. Expand `Diagnose V8.1 BUY and SELL gates` and read `V8.2 FILTER FUNNEL`. The new workflow and tests are committed but not yet verified by Actions.

## V8.2 follow-up: isolated final-gate diagnostic

The original V8.2 results from November 18 showed that after directional confirmation, the combined **minimum candle body plus EMA20 extension limit** rejected nearly all candidate bars. The later-period funnel had 284 BUY and 195 SELL directional confirmations, but only 1 of each survived both final filters; development had zero. These are overlapping candle-level conditions, **not trades**.

The updated `diagnose_pullback_v2.py` now reports:
1. **Minimum candle body** (cumulative pass count: close/open movement >= 0.10 ATR14)
2. **EMA20 extension limit** (cumulative count after body, distance <= 1.5 ATR14)
3. **EMA20 extension pass (independent)** measured directly against directional confirmations, irrespective of candle body
4. **Minimum body pass (independent)** measured directly against directional confirmations, irrespective of EMA20 distance

These separate counts reveal whether one or both conditions are causing the near-zero signal frequency. They do NOT prove that removing either filter improves accuracy; a larger sample can still lose money. No V8.1 signal code or stored records are changed. Run **V8.2 Signal Filter Diagnosis** again and compare stage counts before developing another version.

## V8.2 latest result and V8.3 OHLC source audit

The November 18, 2026 user-supplied isolated filter counts show a **body-size gate bottleneck**:

- Development: after directional reclaim, BUY 87 and SELL 59; minimum body passed BUY 0 and SELL 1; EMA20 extension independently passed BUY 75 and SELL 48.
- Later period: after directional reclaim, BUY 284 and SELL 195; body passed only BUY 1 and SELL 1; extension independently passed BUY 250 and SELL 169.
- The final combined gates passed only one BUY and one SELL in later period. These are candidate candle counts, not non-overlapping trades.
- The 0.10 ATR candle body threshold failing for 477/479 directional reclaim candles (in the later period) is unusual enough to **audit price data before altering the filter**. It may be due to source OHLC characteristics or the interaction between candle conditions. Neither cause has yet been verified; do not assert a provider bug.

New `audit_fx_candle_quality.py` read-only diagnostic records the frequency of exactly/nearly equal Open/Close, candles below 0.10 ATR body size, median body-to-ATR ratio, close-to-close-to-ATR ratio and range-to-ATR ratio per market and historical period. `V8.3 FX Candle Data Quality` GitHub workflow executes these checks across the 15 original FX research markets, and `test_fx_candle_quality.py` covers synthetic zero-body versus nonzero-body data.

**Do not remove candle-strength filters or substitute close-to-close motion into the candle-body rule until data quality is understood.** Even if the body is an unsuitable proxy on a provider feed, that does not by itself establish any profitable replacement. Any revised model must use a fresh version and prospective evaluation.
