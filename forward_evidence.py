"""V6.0 — auditable forward-only prediction evidence report.

Read-only Supabase REST, no model updates, credentials never printed.
This report does not equate historical simulations with recorded forecasts.
"""
import argparse
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import requests

FIELDS = (
    "id,recorded_at,instrument,ticker,timeframe,signal,model_version,"
    "signal_bar_at,horizon_bars,status,correct,directional_return_pct,"
    "outcome_bar_at,evaluated_at"
)


def _supabase_config():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if url.endswith("/rest/v1"):
        url = url[:-8]
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname
            or not parts.hostname.endswith(".supabase.co")
            or parts.path not in ("", "/") or not key):
        raise RuntimeError("Supabase secrets are not configured correctly")
    return url, key


def fetch_records(page_size=500):
    """Get every record via a read-only, paginated, ordered endpoint."""
    url, key = _supabase_config()
    headers = {"apikey": key, "Accept": "application/json"}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    records = []
    offset = 0
    while True:
        response = requests.get(
            f"{url}/rest/v1/forex_predictions",
            headers=headers,
            params={
                "select": FIELDS, "order": "recorded_at.asc,id.asc",
                "limit": page_size, "offset": offset,
            },
            timeout=30,
        )
        if not response.ok:
            # Never echo server error bodies: they can contain sensitive info.
            raise RuntimeError(f"Forward evidence read failed: HTTP {response.status_code}")
        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected database response")
        records.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return records


def wilson_interval(wins, n, z=1.959963984540054):
    """95% Wilson score interval for a Bernoulli correctness rate."""
    if n <= 0:
        return None, None
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value in (1, "true", "True", "t"):
        return True
    if value in (0, "false", "False", "f"):
        return False
    return None


def summarise_forward(records):
    """Summarise only genuinely evaluated directional forecasts.

    This is a report on the *stored evaluator verdict*, with an additional
    temporal consistency check. It cannot reconstruct the original observed
    price feed; it deliberately makes no claim of independently auditing
    every candle close or exact execution prices.
    """
    data = pd.DataFrame(records)
    columns = [
        "model_version", "recorded_total", "directional_total",
        "evaluated_directional", "correct_directional", "accuracy_pct",
        "wilson95_low_pct", "wilson95_high_pct", "markets_evaluated",
        "pending_directional", "unavailable_directional",
        "wait_total", "invalid_evaluated", "evidence_status",
    ]
    if data.empty:
        return pd.DataFrame(columns=columns)
    for col in ("model_version", "status", "signal", "ticker",
                "timeframe", "correct", "recorded_at", "outcome_bar_at"):
        if col not in data:
            data[col] = None

    # Avoid counting duplicated database records as independent evidence.
    if "id" in data:
        data = data.drop_duplicates(subset=["id"], keep="first")
    data["signal"] = data["signal"].astype(str).str.upper()
    data["status"] = data["status"].astype(str).str.lower()
    data["recorded_at_utc"] = pd.to_datetime(
        data["recorded_at"], errors="coerce", utc=True
    )
    data["outcome_at_utc"] = pd.to_datetime(
        data["outcome_bar_at"], errors="coerce", utc=True
    )
    rows = []
    for model, group in data.groupby("model_version", dropna=False):
        directional = group.loc[group.signal.isin(["BUY", "SELL"])].copy()
        evaluated = directional.loc[directional.status == "evaluated"].copy()
        evaluated["confirmed"] = evaluated["correct"].map(_as_bool)
        # The outcome bar is labelled by its OPEN. A prediction may be
        # recorded during that bar, provided it was recorded BEFORE close.
        # This secondary check supplements (does not replace) the
        # evaluator's stricter first-future-bar late-recording protection.
        duration = evaluated["timeframe"].map({
            "5m": pd.Timedelta(minutes=5),
            "15m": pd.Timedelta(minutes=15),
            "1h": pd.Timedelta(hours=1),
            "4h": pd.Timedelta(hours=4),
            "1d": pd.Timedelta(days=1),
        })
        temporal_valid = (
            evaluated["recorded_at_utc"].notna()
            & evaluated["outcome_at_utc"].notna()
            & duration.notna()
            & (
                evaluated["outcome_at_utc"] + duration
                > evaluated["recorded_at_utc"]
            )
        )
        trustworthy = evaluated.loc[
            evaluated["confirmed"].notna() & temporal_valid
        ]
        n = len(trustworthy)
        wins = int(trustworthy.confirmed.sum()) if n else 0
        low, high = wilson_interval(wins, n)
        markets = int(trustworthy.ticker.nunique()) if n else 0
        # These are diagnostic thresholds, not a statistical guarantee
        # or evidence of independence across correlated FX pairs.
        if n == 0:
            status = "NO_EVALUATED_FORWARD_SIGNALS"
        elif n < 100 or markets < 10:
            status = "INSUFFICIENT_FORWARD_EVIDENCE"
        else:
            status = "REVIEW_REQUIRED_CORRELATED_SAMPLE"
        rows.append({
            "model_version": model,
            "recorded_total": len(group),
            "directional_total": len(directional),
            "evaluated_directional": n,
            "correct_directional": wins,
            "accuracy_pct": round(100 * wins / n, 2) if n else None,
            "wilson95_low_pct": round(100 * low, 2) if low is not None else None,
            "wilson95_high_pct": round(100 * high, 2) if high is not None else None,
            "markets_evaluated": markets,
            "pending_directional": int((directional.status == "pending").sum()),
            "unavailable_directional": int((directional.status == "unavailable").sum()),
            "wait_total": int((group.signal == "WAIT").sum()),
            "invalid_evaluated": len(evaluated) - n,
            "evidence_status": status,
        })
    return pd.DataFrame(rows, columns=columns).sort_values(
        "model_version"
    ).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="forward_evidence_outputs")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records = fetch_records()
    summary = summarise_forward(records)
    summary.to_csv(output / "forward_model_evidence.csv", index=False)
    (output / "forward_evidence_notes.txt").write_text(
        "V6.0 FORWARD EVIDENCE — NOT BROKER VERIFIED PROFITABILITY\n"
        "Only evaluated BUY/SELL records with valid correctness and temporal "
        "fields count toward model accuracy. WAIT and unavailable do not.\n"
        "95% Wilson intervals ignore correlation across markets and dates. "
        "Do not interpret them as perfectly calibrated confidence intervals "
        "when forecasts are dependent.\n"
        "Threshold of 100 evaluated records and 10 active markets is a "
        "minimum review gate, not proof of accuracy or profitability.\n"
        "Saved directional correctness compares signal-bar reference close "
        "with outcome close; it is not next-open executable net P&L.\n"
        f"Records read: {len(records)}.\n"
    )
    print("V6.0 FORWARD EVIDENCE: no model automatically approved")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
