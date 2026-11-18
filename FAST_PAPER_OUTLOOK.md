# Fast paper outlook — separate unvalidated research model

The user-facing issue with earlier research was that the restrictive
`close-trend-pullback-v1` produced WAIT on all 28 markets in a daily run,
and on eight of 12 fresh intraday FX markets in one 5m trial. This was not
a software error: it was the model's restrictive pattern requirement.

## What's new

A NEW independent model, `close-momentum-probe-v1`, uses only completed
Close values and measures EMA8 vs EMA21 plus current EMA8 slope and
close position. If the completed candles are trending up it can return BUY,
if trending down SELL, otherwise WAIT. The hypotheses are:
- BUY when EMA8 > EMA21, EMA8 rising over prior candle, and Close > EMA8.
- SELL when EMA8 < EMA21, EMA8 falling over prior candle, and Close < EMA8.
- WAIT on mixed/flat/warmup data. A signal is NOT guaranteed.

The old nine research models are unchanged. This is a TENTH model
for prospective comparison, not an optimisation of old historical results.

## In Streamlit

- Trading Terminal opens with 15m and Fast Direction Probe by default.
- BUY/SELL/WAIT orb reflects the actual completed-candle model, never an
  invented constant signal. Market trend/bias remains distinct.
- The first screen is simplified; in-depth charts and analytics remain
  available. Forward results go into Prediction History.
- No claimed calibrated confidence, profitable trade or auto-order action.

## In GitHub Actions

1. **V8 Signal Engine Tests** to verify model and app source.
2. **Intraday Paper Trial (5m / 15m)**.
3. For a fast test choose timeframe **15m** and model
   **close-momentum-probe-v1**, `dry_run=false`.
4. Valid BUY/SELL signals saved to the existing Supabase history are
   evaluated after **two future completed candles**, via the existing
   **Evaluate Forex Predictions** workflow.
5. The collector skips delayed Yahoo bars that could make a supposed
   future prediction actually retrospective. Therefore no stored trade
   is possible if the feed is too late. There is no bypass for this.

## Data-provider next steps

Yahoo is not a validated broker quote feed. Another forex provider is
preferable for near-real-time tests, but it requires proper account
credentials and a consistent collection + evaluation feed:
- Twelve Data Forex API offers exchange-rate/forex data endpoints with
  coverage and timing dependent on the subscription.
- OANDA v20 practice API offers candlesticks and broker-related pricing
  where eligible, with an API token/account.
- Never paste API credentials into GitHub source or conversation text.
  Configure them via GitHub Actions secrets and Streamlit secrets.

To prevent fabricated forward accuracy or source mismatch, no provider
switch has been made to already stored forward outcomes. Using a new feed
needs an explicit data-source tag/isolated model evaluation cohort.

**No evidence presently establishes this strategy can make money.**
Increased signal frequency can produce more losses as easily as more wins.
Use paper trading and nonessential money only once independent evidence
justifies future considerations.
