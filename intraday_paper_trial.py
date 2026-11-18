"""Fast, source-timestamped intraday paper-only forward experiment.

Uses the EXISTING close-trend-pullback-v1 signal unchanged. A 5m or 15m
completed candle can become a forward forecast only if the collector runs
before the *first future candle closes*. Yahoo Finance can be delayed:
stale bars are skipped rather than disguising retrospective captures as
live predictions. Never places a broker order.
"""
import argparse
from datetime import timedelta
import sys

import pandas as pd
import yfinance as yf

from forecast_engine import model_flags, signal_label
from prediction_store import config, prediction_exists, save_prediction
from signal_models import CLOSE_CONFIRM_VERSION, FAST_PROBE_VERSION

MARKETS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "AUD/JPY": "AUDJPY=X",
    "NZD/JPY": "NZDJPY=X",
}
CONFIG = {
    "5m": ("5m", "5d", timedelta(minutes=5)),
    "15m": ("15m", "1mo", timedelta(minutes=15)),
}
HORIZON = 2


def trial_eligibility(candles, timeframe, model_version=FAST_PROBE_VERSION,
                      now=None):
    """Return (decision, reason), rejecting late or future-dated signals.

    Duration is nominal bar length; this is NOT a guarantee that the quote
    provider is real-time or broker-executable. Delayed feeds can result in
    zero eligible captures.
    """
    if timeframe not in CONFIG:
        raise ValueError("Only 5m and 15m completed candles are supported.")
    now_utc = (pd.Timestamp.now(tz="UTC") if now is None
               else pd.to_datetime(now, utc=True))
    if candles is None or candles.empty:
        return None, "insufficient_completed_bars"
    ordered = candles.sort_index()
    times = pd.to_datetime(ordered.index, utc=True)
    duration = pd.Timedelta(CONFIG[timeframe][2])
    # Yahoo may supply a forming last bar, or only fully closed bars.
    # Determine completion by candle timestamps rather than *always*
    # excluding the last provider bar.
    closed_positions = [
        k for k, opened in enumerate(times)
        if opened + duration <= now_utc
    ]
    if not closed_positions:
        return None, "signal_bar_not_closed"
    position = closed_positions[-1]
    if position + 1 < 65:
        return None, "insufficient_completed_bars"
    bar_open = times[position]
    if now_utc >= bar_open + 2 * duration:
        return None, "stale_provider_bar_skip"
    # Only the prefix ending on the completed decision candle is
    # supplied to the existing model. The signal and anchor are
    # computed from genuine provider data, not a synthetic extra bar.
    prefix = ordered.iloc[:position + 1]
    buy, sell = model_flags(prefix, model_version)
    decision = {
        "signal": signal_label(buy.iloc[-1], sell.iloc[-1]),
        "signal_bar_at": bar_open.isoformat(),
        "reference_close": float(prefix["Close"].iloc[-1]),
        "position": position,
        "model_version": model_version,
    }
    return decision, "eligible_before_first_future_close"


def load_candles(ticker, interval, period):
    data = yf.download(
        ticker, interval=interval, period=period, auto_adjust=False,
        progress=False, threads=False,
    )
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close"]
    if any(x not in data.columns for x in required):
        return pd.DataFrame()
    data = data.dropna(subset=required).sort_index()
    data = data[~data.index.duplicated(keep="last")]
    return data


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--timeframe", choices=tuple(CONFIG), default="5m")
    p.add_argument("--model", choices=(FAST_PROBE_VERSION, CLOSE_CONFIRM_VERSION),
                   default=FAST_PROBE_VERSION)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--include-wait", action="store_true",
                   help="Show WAIT preview only; WAIT is never stored")
    args = p.parse_args(argv)
    if not args.dry_run and not config():
        raise RuntimeError("Supabase configuration unavailable.")
    interval, period, duration = CONFIG[args.timeframe]
    now = pd.Timestamp.now(tz="UTC")
    counts = {
        "markets_checked": 0, "buy": 0, "sell": 0, "wait": 0,
        "saved": 0, "duplicate": 0, "stale": 0,
        "insufficient": 0, "errors": 0,
    }
    print(
        f"INTRADAY PAPER TRIAL: {args.timeframe}; {HORIZON} future bars; "
        f"model={args.model}; dry_run={args.dry_run}; now={now}"
    )
    print("Delayed Yahoo candles are NOT live executable broker quotes.")
    for name, ticker in MARKETS.items():
        try:
            candles = load_candles(ticker, interval, period)
            counts["markets_checked"] += 1
            decision, reason = trial_eligibility(
                candles, args.timeframe, model_version=args.model, now=now,
            )
            if decision is None:
                if reason == "stale_provider_bar_skip":
                    counts["stale"] += 1
                else:
                    counts["insufficient"] += 1
                print(f"{name}: SKIP [{reason}]")
                continue
            signal = decision["signal"]
            counts[signal.lower()] += 1
            print(
                f"{name}: {signal} @ {decision['signal_bar_at']} "
                f"close={decision['reference_close']:.6f} "
                f"reason={reason}"
            )
            if signal == "WAIT":
                continue
            if args.dry_run:
                continue
            signal_time = decision["signal_bar_at"]
            if prediction_exists(
                ticker, args.timeframe, signal_time,
                args.model, HORIZON,
            ):
                counts["duplicate"] += 1
                continue
            # Recheck the timestamp just before sending to Supabase,
            # including potential download and duplicate-check latency.
            if pd.Timestamp.now(tz="UTC") >= (
                pd.to_datetime(signal_time, utc=True)
                + 2 * pd.Timedelta(duration)
            ):
                counts["stale"] += 1
                print(f"{name}: SKIP [became_stale_before_save]")
                continue
            payload = {
                "instrument": name,
                "ticker": ticker,
                "timeframe": args.timeframe,
                "signal": signal,
                "model_version": args.model,
                "signal_bar_at": signal_time,
                "reference_close": float(decision["reference_close"]),
                "horizon_bars": HORIZON,
            }
            save_prediction(payload)
            counts["saved"] += 1
        except Exception as exc:
            counts["errors"] += 1
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    print("INTRADAY PAPER TRIAL SUMMARY:", counts)
    if counts["stale"]:
        print(
            "Provider-bar staleness prevented forward capture in some "
            "markets. This is correct: do not backfill those bars."
        )
    if counts["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
