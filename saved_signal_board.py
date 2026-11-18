"""Read-only presentation of real saved forward paper signals.

Stored BUY/SELL is a historical prediction with a timestamp, NOT the live
decision for the currently selected candle. This module never invents
signals or upgrades WAIT to a trade.
"""
import pandas as pd

SUPPORTED_TIMEFRAMES = {"5m", "15m"}
SUPPORTED_SIGNALS = {"BUY", "SELL"}


def latest_saved_signals(records, *, model_version=None, limit=12, now=None):
    """Return newest valid, timestamped saved intraday forecasts.

    This intentionally includes evaluated and pending records, but labels
    their statuses and ages. Duplicate forecast IDs are removed.
    """
    if not isinstance(records, list):
        return []
    now_utc = pd.Timestamp.now(tz="UTC") if now is None else pd.to_datetime(now, utc=True)
    selected = []
    for r in records:
        if not isinstance(r, dict):
            continue
        if r.get("signal") not in SUPPORTED_SIGNALS:
            continue
        tf = r.get("timeframe")
        if tf not in SUPPORTED_TIMEFRAMES:
            continue
        if model_version and r.get("model_version") != model_version:
            continue
        if r.get("status") not in ("pending", "evaluated", "unavailable"):
            continue
        try:
            recorded = pd.to_datetime(r.get("recorded_at"), utc=True, errors="coerce")
            bar_at = pd.to_datetime(r.get("signal_bar_at"), utc=True, errors="coerce")
            if pd.isna(recorded) or pd.isna(bar_at):
                continue
            if recorded > now_utc or bar_at > recorded:
                continue
            age_min = max(0, int((now_utc - recorded).total_seconds() // 60))
        except (ValueError, TypeError, OverflowError):
            continue
        selected.append({
            "id": r.get("id"),
            "pair": r.get("instrument") or r.get("ticker") or "Unknown",
            "ticker": r.get("ticker"),
            "timeframe": tf,
            "signal": r["signal"],
            "status": r["status"],
            "model_version": r.get("model_version", ""),
            "signal_bar_at": bar_at,
            "recorded_at": recorded,
            "age_minutes": age_min,
            "reference_close": r.get("reference_close"),
        })
    selected.sort(key=lambda x: x["recorded_at"], reverse=True)
    unique = []
    seen = set()
    for r in selected:
        key = r["id"] or (
            r["ticker"], r["timeframe"], r["model_version"],
            r["signal_bar_at"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
        if len(unique) >= limit:
            break
    return unique
