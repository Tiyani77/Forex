# Fast intraday forward paper trial — November 2026

**No broker integration, real-money orders or verified profitability.**

## Aim

Instead of waiting for five daily candles, independently collect the EXISTING
`close-trend-pullback-v1` BUY/SELL signals on **completed 5m/15m Yahoo candles**
and evaluate each after **two subsequent completed candles**. This accelerates
the mechanics of forward evidence gathering but does not improve the strategy's
underlying predictive accuracy.

## How to run

1. GitHub Actions -> **Intraday Paper Trial (5m / 15m)** -> Run workflow.
2. Choose `5m`, and **dry_run=false** to save valid forward BUY/SELL forecasts
   to the same Supabase prediction database already used by Prediction History.
   First choose `dry_run=true` for an observation-only preview if desired.
3. Open the workflow summary: `buy`, `sell`, `wait`, `saved`,
   `duplicate`, `stale`, `insufficient`, `errors`.
4. GitHub Actions -> **Evaluate Forex Predictions** -> Run workflow after
   enough **new completed** intraday candles exist.
5. Streamlit -> **Prediction History** -> **Quick intraday paper trial** and
   **V8.6 Forward return & cost dashboard**.

The collector is also set to attempt runs at 07/22/37/52 UTC minutes on
weekdays. The evaluator adds weekday checks at 11/26/41/56 UTC, alongside its
existing hourly schedule. GitHub Actions cron does **not** guarantee exact
start times, and Yahoo is not a verified low-latency FX quote feed.

## Time validity

- Calculates only from the penultimate downloaded candle via the same shared
  forecasting engine used in the Trading Terminal.
- Requires the signal candle to have closed, but its **very next candle must
  not yet have completed** when collecting. Expired/delayed candles are skipped
  as `stale_provider_bar_skip`, not saved retroactively.
- Rechecks freshness after any database duplicate checks and immediately
  before saving. Outcome bars are evaluated separately with the existing
  late-recording and completed-bar protections.
- If the source is 15 minutes delayed, **there may be zero eligible records**.
  That is not a software failure or permission to backdate predictions.
- `WAIT` is printed and counted, **not saved as a BUY/SELL prediction**;
  therefore no outcomes are fabricated to satisfy a test deadline.
- No original model thresholds, versions, signal direction or daily collector
  settings are modified.

## Key limitations

- A 5-minute forecast is a different market horizon from the earlier daily
  benchmark: the model was NOT verified on this intraday horizon.
- The saved reference price is the signal candle close, **not the obtainable
  market entry price**, so cost-adjusted directional return is not broker P&L.
- Overnight and cross-market dependence, spreads, quote latency, slippage and
  uncertain candle close conventions preclude a real-money claim.
- Short-window outcomes should not be treated as evidence of a profitable
  strategy merely because they are quickly available.

This is a prospective, falsifiable technical trial, not a guaranteed generator
of profitable trade calls.
