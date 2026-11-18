# V6.2 — Read-only pending prediction monitoring

The evaluation run shared on November 18, 2026 passed **39 tests**, had **27 pending forecasts**, returned **27 not_ready**, and had **0 errors**. No completed forward outcomes were scored in that run.

## New monitoring behavior

The original evaluator determines whether a prediction is `evaluated`, `not_ready`, `unavailable` or otherwise unscorable. **V6.2 does not change any of those outcomes, the bar horizon, or the database.**

After the evaluator reports `not_ready`, `no_data` or `signal_bar_missing`, the read-only monitor logs:
- The reason for waiting or missing data;
- How many subsequent bars are visible in the evaluator's **already-downloaded, latest-bar-excluded** candle history;
- How many more observed bars are needed to reach the prediction's horizon;
- Pending age in days;
- A *manual review suggestion* after 14 days for daily forecasts or 7 days for shorter timeframes (these thresholds are operational reminders, not estimated maturity dates).

The log also prints waiting counts by model and number of ageing records needing manual investigation. No record IDs, credentials, or secret payloads are printed.

## Important limitations

A `not_ready` status is normal when fewer than five daily future bars have completed. Weekends, exchange holidays and missing provider candles can extend this period. The monitor does not forecast the date of the next available bar. `review_suggested` does not mean a signal should be counted as incorrect; it only prompts a data-quality check.

Run GitHub Actions → **Evaluate Forex Predictions** and inspect **V6.2 pending monitoring**. The workflow also runs the no-network `test_prediction_monitor.py` regression tests. The new code has not been claimed validated in CI until the workflow runs.
