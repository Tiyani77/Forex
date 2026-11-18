# V6.3 — Prediction Tracking & Reliability

**Scope:** A read-only, transparent view of actual saved forward predictions in the Streamlit **Prediction History** page. No forecast model thresholds, stored records, evaluation semantics, Supabase schema or execution settings are changed.

## Improvements

1. The dashboard now calls `list_predictions_paginated(page_size=500, max_records=5000)`. Results are sorted deterministically by `recorded_at.desc,id.desc`. If more than 5,000 records exist, an explicit warning says all visible statistics reflect only the most recent 5,000. This replaces the previous silent 500-record cutoff on this screen.
2. A new **V6.3 Prediction tracking reliability** section shows pending/evaluated directional forecasts, ageing review flags and data-quality flags.
3. An operational lifecycle table shows the last 100 directional records with their model, direction, holding horizon, recorded timestamp and status. Older rows remain in the paginated dataset used by aggregate metrics.
4. A separate table appears for records needing manual attention (missing timestamps/ticker/timeframe/horizon, unexpected status, unusually old pending forecasts). None is automatically counted as a loss.
5. `prediction_tracking.py` contains deterministic, no-side-effect diagnostics; `tests/test_prediction_tracking.py` covers normal pending, ageing, incomplete evaluated outcomes, WAIT exclusion, empty input and paginated reads.

## Semantics and safeguards

- **Calendar days are NOT completed future candle bars.** The monitor in the GitHub evaluation job counts actually observed bars; this dashboard only computes *elapsed wall-clock age*, so it must not invent a completion date.
- Manual review thresholds: 14 days for daily records and 7 days for shorter timeframes. They are operational review triggers, not timeouts or trading rules.
- Directional accuracy remains based only on completed BUY/SELL evaluations and excludes pending, WAIT and unavailable predictions.
- V6.3 does not promote any of the six researched trading models as validated or profitable.
- Aggregates in the dashboard are capped to the displayed history window. If the cap is reached, the page alerts the user.
- Data-quality flags do not change existing database rows.

## Verification

GitHub Actions → **Evaluate Forex Predictions**. Its unittest discovery and Python compile checks now cover the new helper and tests. Check the newly deployed Streamlit **Prediction History** page for the V6.3 section. No release should be considered tested until those actions and the page load succeed.
