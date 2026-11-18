# V8.6 — Forward return and hypothetical cost dashboard

**Research only. Not a realised profit-and-loss report and not a trading recommendation.**

## Why this version exists

Previous 15-market V8.4 historical research generated 306 later-period simulated signals, but median market net mean return remained negative (-0.071992% under an assumed 4 bps cost). The latest collection and evaluator logs showed **38 pending daily forecasts**, **0 evaluated**, and **0 errors**. Evaluated results cannot be invented before future candles have closed.

The existing evaluator stores a *directional_return_pct* equal to:
- BUY: `100*(outcome_close/reference_signal_close - 1)`
- SELL: the negative of that percentage

The recorded reference is the **signal candle close**. For a forecast saved later, that is not a broker-executable entry price, and it is NOT a profit/loss booked in an account.

V8.6 introduces an explicitly labelled **cost-adjusted reference move**, in percent:

```text
cost_adjusted_reference_pct = directional_return_pct - assumed_round_trip_cost_bps / 100
```

This quantity is a research proxy and only estimates how robust the raw direction is to simple transaction-cost assumptions. It is *not* executable P&L, even when positive. It omits real fills, spreads changing over time, entry latency, swaps, slippage, funding, margin, position sizing and account currency FX conversion. A spread-cost assumption does not repair the missing executable entry-price observation.

## Predicted data provenance and validation

The `forward_pnl.py` extractor:
- Reads stored forward predictions only through the app's existing authenticated Supabase history. Makes NO writes to Supabase.
- Requires status=evaluated, signal BUY/SELL, a finite recorded directional return and a consistent evaluator correctness verdict.
- Requires valid timestamps with outcome later than the signal candle, and forecast recorded before the outcome candle closed.
- Deduplicates by record ID and again by model/ticker/timeframe/signal-candle/horizon to reduce double-counting.
- Excludes WAIT, pending, unavailable, malformed and potentially late records. It does not backfill historical signals.
- Does not merge model performance across versions or fabricate results for empty strategies.

In the Streamlit **Prediction History** section, below the existing forward-readiness dashboard, V8.6 displays:
- Valid evaluated forecast count, pending directional forecasts and assumed round-trip cost;
- Pooled **mean cost-adjusted reference move** (explicitly labelled as correlated, non-executable);
- Per-strategy market coverage, signed-direction reference return, mean/median cost-adjusted proxies, and share positive after assumed cost;
- Per-forecast record details and 0/4/10 bps sensitivity scenarios, only after valid evaluations exist.

No equity curve, cumulative capital growth, Sharpe ratio, dollar profits or trade profitability is claimed: forecasts across strategies, dates and correlated pairs may overlap.

## Instructions

1. GitHub Actions → **V8.6 Forward P&L Proxy Checks** → Run workflow. Check full unittest suite and static wiring.
2. Streamlit → Prediction History → **V8.6 · Forward return & cost dashboard**.
3. While all 38 earlier forecasts remain pending, expect **0 valid evaluated**, blank profit-related metrics and a clear notice. This is correct.
4. Let scheduled collection/evaluation continue. Once five genuinely subsequent completed candles have been observed for an eligible 5-bar forecast, the existing evaluator can provide a return that will be reflected here.
5. Do not interpret a positive reference move as a profitable filled trade. Genuine broker-quality bid/ask quotes, timestamped entry/exit fills or a credible simulated execution model would be needed for executable net P&L analysis.

V8.6 does **not change any BUY/SELL strategy rules or existing stored forecast records**. Model versions remain nine. No model has been declared validated or profitable.

The dedicated V8.6 workflow runs offline tests only; live deployment and live Supabase data must still be separately verified.
