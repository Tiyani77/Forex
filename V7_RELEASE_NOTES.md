# Forex Intelligence V7.1 — Release candidate

**Status:** Software integration committed; pending GitHub Actions and deployed Streamlit verification. **No model is validated for reliable forecasting or trading profits.**

## V7.0 — Shared prediction engine

- `forecast_engine.py` is now the single dispatch point for the six versioned research rules. The original EMA20/EMA50 engulfing model retains the same thresholds and candle confirmation rules; the other five models still run through their existing implementations.
- Trading Terminal, manually saved forward predictions, scheduled collection and historical research all call the shared model dispatcher, instead of maintaining parallel copies.
- Completed daily signal candles use a UTC label + one calendar day convention, consistent with the previous daily collector and terminal. Intraday terminal signals continue to exclude the latest bar as a conservative convention.
- Terminal and manual saving now refer to the same completed candle, model version, price and BUY/SELL/WAIT result.
- `prediction_store.prediction_exists` queries Supabase for the exact five-field forecast identity before each collector/manual insert:
  `ticker`, `timeframe`, `signal_bar_at`, `model_version`, `horizon_bars`.
  This removes the old failure mode of checking only the latest 500 records.

**Important:** An application-level read-before-write duplicate check is NOT atomic. To prevent duplicate inserts from simultaneous clients, apply a database-side unique constraint on the five identity columns through a reviewed migration. Do not modify the existing Supabase schema without checking and resolving historical duplicates first.

## V7.1 — Final polish and release verification

- App now identifies itself as `V7.1 Release Candidate` and distinguishes unvalidated BUY/SELL rule outputs from probabilistic forecast confidence and real-world trading P&L.
- The Prediction History page explicitly distinguishes timestamped forward outcomes from retrospective research. WAIT and pending are not scored as wins or losses.
- `.github/workflows/release_v7.yml` contains an offline release gate: compilation, full regression tests, source/module integrity checks, duplicate guards and explicit caution that no trading model is validated.
- `tests/test_forecast_integration_v7.py` covers shared baseline parity, completed-bar timing, causal stability and exact dedup database lookup.
- `tests/test_release_health.py` checks the release contract and failure conditions.

## How to verify

1. GitHub Actions → **V7.1 Final Release Checks** → **Run workflow**. Verify all tests and `STATIC_RELEASE_GATE_PASSED`. This workflow also runs on pushes to the main integration files.
2. GitHub Actions → **Collect forward predictions** → **Run workflow** with **dry_run: true**. Confirm all six model names appear and the latest completed bar is shown. Dry-run does not change Supabase.
3. GitHub Actions → **Evaluate Forex Predictions** → **Run workflow**. Confirm there are no errors; `not_ready` means there are not enough completed future bars and is not a failing test.
4. Open the deployed Streamlit app and check:
   - Header/sidebar: V7.1 Release Candidate.
   - Trading Terminal: selected model and last completed candle.
   - Prediction History: V6.3 lifecycle, age, data quality and forward performance.
   - Manually saving the *same* prediction twice returns a duplicate notice rather than a second row.
5. After some future outcomes complete, run **V6 Forward Prediction Evidence** and verify evaluated BUY/SELL counts without treating tiny samples as proven edges.

## Release limitations (must remain visible)

- The system uses market-data-provider historical/delayed candle proxies, not a broker execution feed.
- The app is NOT an order placement system. It has no live broker integration, commission reconciliation, slippage realization, position sizing or stop-loss execution.
- Forward `correct` compares reference candle close with outcome close. Backtests simulate next-bar open entry and estimated costs. These are different metrics.
- The historical development splits have been repeatedly inspected; they are not untouched out-of-sample validation.
- Independence assumptions for Wilson confidence intervals are not reliable with overlapping/correlated markets.
- Forward evaluation and prediction collection run under separate scheduled workflows. Schedule delays, unavailable provider candles, weekends and exchange holidays can delay outcomes.
- Source-level release checks do not replace deployment smoke testing, end-to-end Supabase checks, security review, or sufficient genuinely forward observations.

**Acceptance:** A green release workflow plus successful deployed UI and collection/evaluator checks establishes a *working research app release candidate*, not predictive accuracy or profitable trading.
