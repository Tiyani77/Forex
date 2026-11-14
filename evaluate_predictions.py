
"""
Forex Intelligence — Automatic Prediction Evaluator

Runs through GitHub Actions.
Uses GitHub repository secrets for Supabase access.
No Streamlit dependency required.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit

import pandas as pd
import yfinance as yf
import requests


TABLE = "forex_predictions"

TIMEFRAMES = {
    "5m": ("5m", "5d", timedelta(minutes=5)),
    "15m": ("15m", "1mo", timedelta(minutes=15)),
    "1h": ("60m", "3mo", timedelta(hours=1)),
    "4h": ("60m", "3mo", timedelta(hours=4)),
    "1d": ("1d", "2y", timedelta(days=1)),
}


def get_config():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    ).strip()

    url = url.rstrip("/")

    if url.endswith("/rest/v1"):
        url = url[:-8]

    parts = urlsplit(url)

    if (
        parts.scheme != "https"
        or not parts.hostname
        or not parts.hostname.endswith(".supabase.co")
        or parts.path not in ("", "/")
        or not key
    ):
        raise RuntimeError(
            "Missing or invalid GitHub Supabase secrets."
        )

    return url, key


BASE_URL, API_KEY = get_config()


def db_request(method, params=None, payload=None):
    headers = {
        "apikey": API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # New Supabase secret keys are not JWTs.
    if not API_KEY.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {API_KEY}"

    if method in ("PATCH", "POST"):
        headers["Prefer"] = "return=representation"

    response = requests.request(
        method,
        f"{BASE_URL}/rest/v1/{TABLE}",
        headers=headers,
        params=params,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        code = ""
        try:
            code = str(response.json().get("code", ""))
        except (ValueError, AttributeError):
            pass

        raise RuntimeError(
            f"Supabase HTTP {response.status_code}"
            + (f", code {code}" if code else "")
        )

    return response.json() if response.content else []


def get_pending_predictions():
    records = []
    offset = 0
    page_size = 500

    while True:
        page = db_request(
            "GET",
            params={
                "select": "*",
                "status": "eq.pending",
                "order": "recorded_at.asc",
                "limit": str(page_size),
                "offset": str(offset),
            },
        )

        records.extend(page)

        if len(page) < page_size:
            break

        offset += page_size

    return records


def download_candles(ticker, timeframe):
    interval, period, duration = TIMEFRAMES[timeframe]

    data = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]

    if any(col not in data.columns for col in required):
        return pd.DataFrame()

    data = data.dropna(subset=required).sort_index()
    data = data[~data.index.duplicated(keep="last")]

    if timeframe == "4h":
        columns = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        }

        if "Volume" in data.columns:
            columns["Volume"] = "sum"

        data = (
            data.resample("4h", origin="start_day")
            .agg(columns)
            .dropna(subset=required)
        )

    data.index = pd.to_datetime(data.index, utc=True)

    # Conservative approach: exclude the newest bar, which
    # may still be forming or have incomplete provider data.
    if len(data) <= 1:
        return pd.DataFrame()

    return data.iloc[:-1].copy()


def evaluate_one(record, candles):
    if candles.empty:
        return "no_data"

    signal = record["signal"]
    timeframe = record["timeframe"]
    horizon = int(record["horizon_bars"])
    if horizon < 1 or horizon > 100:
        return "invalid_horizon"
    if timeframe not in TIMEFRAMES:
        return "invalid_timeframe"

    signal_time = pd.to_datetime(
        record["signal_bar_at"], utc=True
    )
    recorded_time = pd.to_datetime(
        record["recorded_at"], utc=True
    )

    # The signal bar must be present in downloaded history.
    matching = candles.index == signal_time

    if not matching.any():
        return "signal_bar_missing"

    signal_position = int(matching.argmax())

    # N subsequent completed bars after the signal bar.
    target_position = signal_position + horizon

    if target_position >= len(candles):
        return "not_ready"

    target_time = candles.index[target_position]

    # Never evaluate a forecast using a target candle
    # that was already available when it was saved.
    # The provider index is the START of the outcome candle.
    # A prediction recorded after that opening can still be legitimate
    # provided it was saved before the outcome candle CLOSED.
    duration = TIMEFRAMES[timeframe][2]
    outcome_close_time = target_time.to_pydatetime() + duration
    if outcome_close_time <= recorded_time.to_pydatetime():
        return "outcome_preceded_recording"

    # For intraday and daily data, wait for the entire outcome bar to close.
    now = datetime.now(timezone.utc)
    if outcome_close_time > now:
        return "not_ready"

    close = float(candles["Close"].iloc[target_position])
    reference = float(record["reference_close"])

    if (
        not pd.notna(reference) or not pd.notna(close)
        or not (0 < reference < float("inf"))
        or not (0 < close < float("inf"))
    ):
        return "invalid_price"

    raw_move_pct = (close / reference - 1) * 100

    if signal == "BUY":
        directional_return = raw_move_pct
        correct = directional_return > 0

    elif signal == "SELL":
        directional_return = -raw_move_pct
        correct = directional_return > 0

    else:
        # WAIT is an abstention, not a directional forecast.
        directional_return = None
        correct = None

    update = {
        "status": "evaluated",
        "evaluated_at": now.isoformat(),
        "outcome_bar_at": target_time.isoformat(),
        "outcome_close": close,
        "directional_return_pct": directional_return,
        "correct": correct,
    }

    # Conditional update prevents a completed prediction
    # from being updated again by another evaluator.
    updated = db_request(
        "PATCH",
        params={
            "id": f"eq.{record['id']}",
            "status": "eq.pending",
        },
        payload=update,
    )

    return "evaluated" if updated else "already_updated"


def main():
    print("Forex Intelligence — Evaluation started")

    pending = get_pending_predictions()
    print(f"Pending predictions: {len(pending)}")

    counts = {}
    cache = {}
    errors = 0

    for record in pending:
        ticker = record["ticker"]
        timeframe = record["timeframe"]
        cache_key = (ticker, timeframe)

        try:
            if timeframe not in TIMEFRAMES:
                raise ValueError("Unsupported timeframe")

            if cache_key not in cache:
                cache[cache_key] = download_candles(
                    ticker, timeframe
                )

            result = evaluate_one(
                record,
                cache[cache_key],
            )

            counts[result] = counts.get(result, 0) + 1

            print(
                f"{ticker} {timeframe} "
                f"{record['signal']}: {result}"
            )

        except Exception as exc:
            errors += 1
            print(
                f"Prediction {record.get('id', 'unknown')} "
                f"failed: {type(exc).__name__}"
            )

    print("Evaluation summary:")

    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    print(f"  errors: {errors}")

    if errors:
        sys.exit(1)

    print("Evaluation run completed successfully.")


if __name__ == "__main__":
    main()
