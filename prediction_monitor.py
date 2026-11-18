"""V6.2 read-only diagnostics for a pending prediction.

No Supabase calls, no mutation, no accuracy estimates. 'Observed' means the
evaluator's downloaded candle frame, which deliberately excludes its newest
potentially-forming bar.
"""
import pandas as pd


def pending_diagnostic(record, candles, now=None):
    now = (pd.Timestamp.now(tz="UTC") if now is None
           else pd.to_datetime(now, utc=True))
    timeframe = str(record.get("timeframe", ""))
    horizon = int(record.get("horizon_bars", 0))
    signal_at = pd.to_datetime(record.get("signal_bar_at"), utc=True)
    recorded_at = pd.to_datetime(record.get("recorded_at"), utc=True)
    if horizon < 1:
        return {"reason": "invalid_horizon", "bars_seen": 0,
                "bars_remaining": None, "age_days": None}

    age_days = max(0.0, (now - recorded_at).total_seconds() / 86400.0)
    if candles is None or candles.empty:
        reason = "no_market_data"
        seen = 0
    else:
        index = pd.to_datetime(candles.index, utc=True)
        matches = index == signal_at
        if not matches.any():
            reason = "signal_bar_missing"
            seen = 0
        else:
            position = int(matches.argmax())
            seen = max(0, len(index) - position - 1)
            reason = "waiting_for_completed_bars" if seen < horizon else "ready_for_evaluation"

    remaining = max(0, horizon - seen)
    # A conservative operational review flag, NOT an assertion the trade
    # should have matured. Weekends, exchange holidays and data gaps occur.
    review_days = 14 if timeframe == "1d" else 7
    return {
        "reason": reason,
        "bars_seen": seen,
        "bars_remaining": remaining,
        "age_days": round(age_days, 1),
        "review_suggested": bool(age_days >= review_days and
                                reason != "ready_for_evaluation"),
    }
