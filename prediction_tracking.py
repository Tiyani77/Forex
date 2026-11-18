"""V6.3 descriptive quality checks for stored forward forecast records.

No exchange calendar is assumed. Days elapsed are NOT future candles elapsed;
only the GitHub evaluator can verify observed completed candle bars.
"""
import pandas as pd


def tracking_overview(history, now=None, review_daily_days=14,
                      review_intraday_days=7):
    """Return per-record operational health and a compact actionable summary.

    This function does not mutate Supabase, impute missing outcomes, or
    classify predictions as correct/incorrect. A stale pending forecast
    is merely flagged for investigation.
    """
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.to_datetime(now, utc=True)
    if history is None:
        history = pd.DataFrame()
    rows = history.copy()
    needed = (
        "id", "ticker", "instrument", "timeframe", "model_version",
        "signal", "status", "recorded_at", "signal_bar_at",
        "horizon_bars", "outcome_bar_at", "correct"
    )
    for column in needed:
        if column not in rows:
            rows[column] = None
    if rows.empty:
        rows["Age days"] = pd.Series(dtype=float)
        rows["Data quality"] = pd.Series(dtype=str)
        rows["Operational state"] = pd.Series(dtype=str)
        return rows, {
            "pending": 0, "evaluated": 0, "unavailable": 0,
            "aged_pending": 0, "missing_fields": 0, "unusual_status": 0,
        }
    rows["signal"] = rows["signal"].fillna("").astype(str).str.upper()
    rows["status"] = rows["status"].fillna("").astype(str).str.lower()
    recorded = pd.to_datetime(rows["recorded_at"], utc=True, errors="coerce")
    signal_bars = pd.to_datetime(rows["signal_bar_at"], utc=True, errors="coerce")
    horizons = pd.to_numeric(rows["horizon_bars"], errors="coerce")
    ages = ((now - recorded).dt.total_seconds() / 86400.0).clip(lower=0)
    rows["Age days"] = ages.round(1)
    known_status = rows["status"].isin(["pending", "evaluated", "unavailable"])
    directional = rows["signal"].isin(["BUY", "SELL"])
    valid_horizon = horizons.between(1, 100)
    essential = (
        recorded.notna() & signal_bars.notna()
        & rows["ticker"].notna() & rows["timeframe"].notna()
        & valid_horizon
    )
    # Evaluated forecast without an outcome timestamp merits inspection,
    # but is not automatically labelled incorrect.
    evaluated_no_outcome = (
        rows["status"].eq("evaluated")
        & pd.to_datetime(rows["outcome_bar_at"], utc=True,
                         errors="coerce").isna()
    )
    rows["Data quality"] = "OK"
    rows.loc[~essential | evaluated_no_outcome, "Data quality"] = (
        "Missing or invalid fields"
    )
    rows.loc[~known_status, "Data quality"] = "Unknown status"

    review_days = rows["timeframe"].eq("1d").map({
        True: review_daily_days, False: review_intraday_days
    })
    aged = (directional & rows["status"].eq("pending")
            & ages.ge(review_days).fillna(False))
    rows["Operational state"] = "Other"
    rows.loc[rows["status"].eq("pending"), "Operational state"] = (
        "Awaiting completed future candles"
    )
    rows.loc[rows["status"].eq("evaluated"), "Operational state"] = (
        "Outcome recorded"
    )
    rows.loc[rows["status"].eq("unavailable"), "Operational state"] = (
        "Outcome unavailable"
    )
    rows.loc[aged, "Operational state"] = (
        "Review pending age / provider data"
    )
    rows.loc[rows["Data quality"].ne("OK"), "Operational state"] = (
        "Review stored data fields"
    )

    filtered = rows.loc[directional]
    summary = {
        "pending": int(filtered["status"].eq("pending").sum()),
        "evaluated": int(filtered["status"].eq("evaluated").sum()),
        "unavailable": int(filtered["status"].eq("unavailable").sum()),
        "aged_pending": int(aged.sum()),
        "missing_fields": int(
            rows["Data quality"].eq("Missing or invalid fields").sum()
        ),
        "unusual_status": int((~known_status).sum()),
    }
    return rows, summary
