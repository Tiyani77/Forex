# V6.0 — Genuine forward prediction evidence

The V5.5 research audit completed on November 15, 2026. The results for all six versioned research strategies were **NOT_VALIDATED**. Historic split reports have been inspected repeatedly during strategy development; a profitable-looking segment in them is not an untouched validation set.

## What changed

- `forward_evidence.py`: read-only, paginated Supabase query; grouped performance for each actually recorded model version; CSV audit with data coverage, evaluated BUY/SELL count, wins, raw directional correctness, and 95% Wilson intervals.
- `.github/workflows/forward_evidence.yml`: manual and weekly audit. Credentials remain in GitHub Actions secrets; the uploaded artifact contains only aggregated model statistics and explanatory caveats.
- `tests/test_forward_evidence.py`: no-live-database tests for denominators, WAIT handling, late records, duplication and conservative evidence status.

## Correctness and eligibility

Only `status=evaluated`, `signal=BUY/SELL`, non-null correctness and internally consistent recording/outcome times contribute to an accuracy numerator or denominator. `WAIT` is *not* a correct directional prediction, `pending` is not yet evidence, and `unavailable` is not scored.

For a model with `n` genuinely scored predictions, the report gives the observed win rate and a 95% Wilson interval. That interval assumes independent Bernoulli samples; forecasts across correlated currency pairs and overlapping days are not independent, so the displayed interval could be overly narrow.

The report marks:
- No evaluated directional forecasts: `NO_EVALUATED_FORWARD_SIGNALS`
- Fewer than 100 evaluated forecasts or fewer than 10 active markets: `INSUFFICIENT_FORWARD_EVIDENCE`
- At least 100 and 10 markets: `REVIEW_REQUIRED_CORRELATED_SAMPLE`

**No condition means the model is validated.** A model still needs independent review for correlated FX exposures, repeated testing, costs, regime stability, and economic relevance.

## Important distinctions

- Forward `correct` compares the **signal reference close** to the outcome close: this is a direction check, *not* a realizable next-open entry P&L.
- Historical backtests simulate **next-bar open entry** and a selected bar-close exit with assumed basis-point costs. These outputs are not directly comparable to the forward `correct` field.
- This script audits stored evaluator verdicts and recording/outcome timestamps, but does not reconstruct every original Yahoo bar or independently validate the price feed. The evaluator remains responsible for rejecting late recordings.
- No live order placement, portfolio sizing, or broker execution is implemented. No forecast probabilities are calibrated in this release.

## Run

GitHub Actions → **V6 Forward Prediction Evidence** → **Run workflow**. Inspect `V6.0 FORWARD EVIDENCE` logs. Download `v6-forward-evidence` artifact for `forward_model_evidence.csv`.

Do not select a winning strategy from this report unless both sample adequacy and independent review are achieved. The automatic weekly audit is informational, not a trading system.


## V6.1: Checking whether forward signals are actually collected

The first V6.0 report (2026-11-15) showed only five pre-existing records:
- `ema-rsi-momentum-v1`: four recorded BUY/SELL forecasts, all still pending.
- `ema20-ema50-engulf-v1`: one WAIT (abstention), no scored forecast.
- All four newer book-informed strategies: no saved directional forecasts yet.

This does not prove a data collector outage. The automated collector runs at **06:15 UTC every calendar day**, and default collection intentionally skips WAIT signals. In addition, each directional prediction has a **five-completed-daily-bar** evaluation horizon; Nov 12–13 forecasts may legitimately await several weekday bars after the weekend.

V6.1 adds per-version `BUY / SELL / WAIT` counts to the collection logs without storing WAITs as wins. A GitHub Actions **Collect forward predictions** manual run defaults to `dry_run=true`: it **does not write to Supabase** and should produce the counts in the job log. Do not make repeated manual runs with `dry_run=false` on stale bars merely to inflate the database; versioned data must remain truly forward.

Evaluate stored forecasts with **Evaluate Forex Predictions** when sufficient daily candles have completed. Rerun **V6 Forward Prediction Evidence** afterward to see whether evaluated directional sample counts increase.

A successful log with mostly WAIT signals is evidence of model selectivity, not a signal-collection failure. The app should not promise that any particular number of forecasts will be produced each day.
