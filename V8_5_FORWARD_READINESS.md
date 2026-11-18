# V8.5 — Forward evidence and paper-only risk controls

**Current commercial status: NOT PROFITABLE OR VALIDATED.**

The latest user-run V8.4 retrospective benchmark of the 15 daily FX pairs (5 years, 5 bars, assumed 4 bps costs) reported 306 later-period simulated close-to-close trades, median market net win rate 52.63%, **median market mean net return -0.071992%**, and 5/15 markets with positive average returns. This does not support selling a high-accuracy trading system or placing real orders.

## What the app now does

In **Trading Terminal**:
- Displays a permanent caution that signals are for **research / paper trading**, not real-money approval;
- Keeps BUY/SELL/WAIT and trend bias separate;
- Provides a collapsible, *illustrative only*, fixed maximum 0.5%-of-hypothetical-balance dollar risk budget with a user-entered estimated dollar loss per unit. This is NOT a forex lot-sizing calculator and makes no claim about real stops or prices. Gaps, spreads, conversion and slippage can exceed this estimate.

In **Prediction History**:
- Reads the existing persisted, timestamped forward predictions and calls the existing `summarise_forward()` evaluator, separately showing the selected model's sample size, accuracy, pending count, markets, and status;
- Applies `model_readiness()` with a **fail-closed** status:
  - no records -> `NO_FORWARD_EVIDENCE`
  - fewer than 100 valid directional evaluations or fewer than 10 markets -> `INSUFFICIENT_FORWARD_SAMPLE`
  - any invalid records -> `DATA_QUALITY_REVIEW`
  - meeting the diagnostic sample threshold -> `MANUAL_REVIEW_REQUIRED`.
- **No status ever approves a model for real-money trading.** Not even 1,000 correct directional predictions can establish profitable execution.

## What still needs to happen to investigate profitability

1. Verify the new automated tests and app deployment. No broker execution is connected.
2. Continue collecting **genuine new** versioned forecasts. Do not backfill a forecast using the outcome already known.
3. Obtain independent broker-quality candle/quote/spread data: Yahoo FX daily Open-to-Close candles were anomalous in our audit.
4. Pre-register evaluation conventions and incorporate plausible spreads, slippage, order timing, account currency and holdout/forward test windows.
5. Analyse realised/paper account net P&L and drawdown. Models should stay **unvalidated** unless repeatable *positive cost-adjusted* evidence supports them.
6. Do not use money needed for rent, groceries, debt repayments or emergencies on speculative leveraged FX positions. Paper trading first.

**Important:** This milestone improves the safety and evidence presentation, not forecast accuracy. It is not a claim that the app makes money.
