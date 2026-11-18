"""V8.6 forward forecast cost-sensitivity dashboard (read-only).

IMPORTANT: directional_return_pct is measured from the completed SIGNAL-bar
close to a future OUTCOME close, not from an executable next-price fill.
Net values subtract a hypothetical round-trip cost from that *reference*
return. They are NOT realised P&L, broker profits, executable trade
backtests, or an investable portfolio equity curve.
"""
import math
import pandas as pd


OUTPUT_COLUMNS = [
    "id", "recorded_at", "instrument", "ticker", "timeframe",
    "model_version", "signal", "signal_bar_at", "outcome_bar_at",
    "horizon_bars", "directional_return_pct", "cost_bps",
    "cost_adjusted_reference_pct",
]
SUMMARY_COLUMNS = [
    "model_version", "evaluated", "markets",
    "mean_reference_pct", "mean_cost_adjusted_pct",
    "median_cost_adjusted_pct", "cost_adjusted_positive_pct",
    "negative_mean_after_cost", "sum_reference_pct_diagnostic",
]


def _timestamp(column):
    return pd.to_datetime(column, errors="coerce", utc=True)


def _is_bool(v):
    if isinstance(v, bool):
        return True
    return v in (0, 1, "true", "false", "True", "False", "t", "f")


def evaluated_reference_returns(records, cost_bps=4.0):
    """Extract only completed, plausibly time-valid, forward directional rows.

    No arbitrary missing returns are imputed. Duplicate IDs and duplicate
    version+market+signal-bar+horizon forecasts are counted only once.
    The return is the signed signal-reference-close to outcome-close move.
    """
    cost = float(cost_bps)
    if not math.isfinite(cost) or cost < 0 or cost > 1000:
        raise ValueError("Cost assumption must be between 0 and 1000 bps.")
    source = pd.DataFrame(records).copy()
    if source.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    required = (
        "id", "recorded_at", "ticker", "timeframe",
        "model_version", "signal", "signal_bar_at",
        "outcome_bar_at", "horizon_bars", "status",
        "correct", "directional_return_pct",
    )
    for name in required:
        if name not in source:
            source[name] = None
    if "instrument" not in source:
        source["instrument"] = source["ticker"]
    source = source.loc[
        source["signal"].astype(str).str.upper().isin(["BUY", "SELL"])
        & source["status"].astype(str).str.lower().eq("evaluated")
    ].copy()
    if source.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    source["signal"] = source["signal"].astype(str).str.upper()
    source["recorded_at"] = _timestamp(source["recorded_at"])
    source["signal_bar_at"] = _timestamp(source["signal_bar_at"])
    source["outcome_bar_at"] = _timestamp(source["outcome_bar_at"])
    source["directional_return_pct"] = pd.to_numeric(
        source["directional_return_pct"], errors="coerce"
    )
    source["horizon_bars"] = pd.to_numeric(
        source["horizon_bars"], errors="coerce"
    )
    duration = source["timeframe"].map({
        "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15),
        "1h": pd.Timedelta(hours=1),
        "4h": pd.Timedelta(hours=4),
        "1d": pd.Timedelta(days=1),
    })
    good = (
        source["recorded_at"].notna()
        & source["signal_bar_at"].notna()
        & source["outcome_bar_at"].notna()
        & source["id"].notna()
        & source["ticker"].notna()
        & source["model_version"].notna()
        & source["horizon_bars"].between(1, 100)
        & duration.notna()
        & (source["recorded_at"] >= source["signal_bar_at"])
        & (source["outcome_bar_at"] > source["signal_bar_at"])
        & (source["recorded_at"] < source["outcome_bar_at"] + duration)
        & source["directional_return_pct"].notna()
        & source["directional_return_pct"].map(math.isfinite)
        & source["correct"].map(_is_bool)
    )
    source = source.loc[good].copy()
    if source.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    # An evaluator's direction correctness and return should agree;
    # zero return is a non-winning directional outcome.
    verdict = source["correct"].map(
        lambda x: x is True or x in (1, "true", "True", "t")
    )
    source = source.loc[
        verdict.eq(source["directional_return_pct"].gt(0))
    ].copy()
    source = source.sort_values(["recorded_at", "id"])
    source = source.drop_duplicates(subset=["id"], keep="first")
    source = source.drop_duplicates(
        subset=["ticker", "timeframe", "model_version",
                "signal_bar_at", "horizon_bars"],
        keep="first",
    )
    source["cost_bps"] = cost
    source["cost_adjusted_reference_pct"] = (
        source["directional_return_pct"] - cost / 100.0
    )
    return source[OUTPUT_COLUMNS].reset_index(drop=True)


def reference_summary(rows, model_versions=None):
    """Descriptive independent-model aggregates, never an equity curve."""
    if rows.empty:
        if model_versions is None:
            return pd.DataFrame(columns=SUMMARY_COLUMNS)
        return pd.DataFrame([
            {"model_version": version, "evaluated": 0,
             "markets": 0, "mean_reference_pct": None,
             "mean_cost_adjusted_pct": None,
             "median_cost_adjusted_pct": None,
             "cost_adjusted_positive_pct": None,
             "negative_mean_after_cost": None,
             "sum_reference_pct_diagnostic": None}
            for version in model_versions
        ], columns=SUMMARY_COLUMNS)
    out = []
    versions = list(model_versions) if model_versions is not None else []
    versions += [v for v in rows["model_version"].unique() if v not in versions]
    for version in versions:
        group = rows.loc[rows["model_version"].eq(version)]
        if group.empty:
            out.append({"model_version": version, "evaluated": 0,
                "markets": 0, "mean_reference_pct": None,
                "mean_cost_adjusted_pct": None,
                "median_cost_adjusted_pct": None,
                "cost_adjusted_positive_pct": None,
                "negative_mean_after_cost": None,
                "sum_reference_pct_diagnostic": None})
            continue
        net = group["cost_adjusted_reference_pct"].astype(float)
        out.append({
            "model_version": version,
            "evaluated": int(len(group)),
            "markets": int(group["ticker"].nunique()),
            "mean_reference_pct": round(
                float(group["directional_return_pct"].mean()), 4
            ),
            "mean_cost_adjusted_pct": round(float(net.mean()), 4),
            "median_cost_adjusted_pct": round(float(net.median()), 4),
            "cost_adjusted_positive_pct": round(
                100 * float((net > 0).mean()), 2
            ),
            "negative_mean_after_cost": bool(net.mean() <= 0),
            # Sum is for an uninvestable equal-notional reference
            # diagnostic only; NEVER present it as account profitability.
            "sum_reference_pct_diagnostic": round(float(net.sum()), 4),
        })
    return pd.DataFrame(out, columns=SUMMARY_COLUMNS)


def reference_scenarios(records, cost_levels=(0.0, 4.0, 10.0)):
    """Apply multiple costs to identical evaluated forecasts."""
    reports = []
    for cost in cost_levels:
        rows = evaluated_reference_returns(records, cost)
        for _, item in reference_summary(rows).iterrows():
            reports.append({
                "model_version": item["model_version"],
                "cost_bps": float(cost),
                "evaluated": int(item["evaluated"]),
                "mean_cost_adjusted_pct": item["mean_cost_adjusted_pct"],
                "cost_adjusted_positive_pct": item["cost_adjusted_positive_pct"],
            })
    return pd.DataFrame(
        reports, columns=["model_version", "cost_bps", "evaluated",
                          "mean_cost_adjusted_pct",
                          "cost_adjusted_positive_pct"]
    )
