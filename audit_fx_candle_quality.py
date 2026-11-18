"""V8.3 FX candle-field quality audit: diagnose Open/Close vs ATR anomaly.

Read-only OHLC inspection. Does NOT modify any strategy or claim accuracy.
The audit checks if Yahoo Finance daily Open and Close are unexpectedly
identical/near-identical on large fractions of bars, a potential data-feed
artifact that can make body-confirmed strategies appear inactive.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from research_multimarket import FX_MARKETS, cleaned_history
from signal_models import _atr


def candle_quality(frame, market, split=0.70):
    if frame is None or frame.empty:
        return []
    if not 0.5 <= split <= 0.9:
        raise ValueError("split must be between 0.5 and 0.9")
    opn = frame["Open"].astype(float)
    close = frame["Close"].astype(float)
    high = frame["High"].astype(float)
    low = frame["Low"].astype(float)
    atr = _atr(frame)
    range_ = high - low
    body = (close - opn).abs()
    body_ratio = (body / atr.replace(0, np.nan))
    close_change_ratio = (
        close.diff().abs() / atr.replace(0, np.nan)
    )
    # Price-relative near-identity avoids comparing JPY with non-JPY FX
    # using a single absolute currency-unit tolerance.
    identical = body <= np.maximum(close.abs() * 1e-8, 1e-12)
    flat_body = body_ratio < 0.10
    eligible = pd.Series(range(len(frame)), index=frame.index) >= 65
    cutoff = int(len(frame) * split)
    rows = []
    for period, window in (
        ("Development", frame.index[:cutoff]),
        ("Later period", frame.index[cutoff:]),
    ):
        valid = (eligible.loc[window] & atr.loc[window].gt(0)
                 & range_.loc[window].ge(0))
        ix = window[valid.to_numpy()]
        if not len(ix):
            continue
        br = body_ratio.loc[ix].dropna()
        cc = close_change_ratio.loc[ix].dropna()
        rows.append({
            "market": market,
            "window": period,
            "eligible_bars": int(len(ix)),
            "identical_open_close_pct": round(
                100 * float(identical.loc[ix].mean()), 2
            ),
            "body_below_0_10_atr_pct": round(
                100 * float(flat_body.loc[ix].mean()), 2
            ),
            "median_body_to_atr": round(float(br.median()), 6),
            "median_close_change_to_atr": round(float(cc.median()), 6),
            "median_high_low_to_atr": round(
                float((range_.loc[ix] / atr.loc[ix]).median()), 6
            ),
            "median_absolute_body": round(float(body.loc[ix].median()), 8),
            "median_atr": round(float(atr.loc[ix].median()), 8),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="5y",
                        choices=("2y", "5y", "10y"))
    parser.add_argument("--split", default=.70, type=float)
    parser.add_argument("--output-dir", default="research_outputs")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    observations, errors = [], []
    for market, ticker in FX_MARKETS.items():
        try:
            df = yf.download(
                ticker, period=args.period, interval="1d",
                auto_adjust=False, progress=False, threads=False
            )
            candles = cleaned_history(df)
            if len(candles) < 150:
                errors.append(f"{market}: insufficient history")
                continue
            rows = candle_quality(candles, market, split=args.split)
            observations.extend(rows)
            print(f"{market}: {len(candles)} completed daily bars")
        except Exception as exc:
            errors.append(f"{market}: {type(exc).__name__}")
    if not observations:
        raise RuntimeError("No FX candle data. " + "; ".join(errors))
    report = pd.DataFrame(observations)
    summary = report.groupby("window", as_index=False).agg(
        markets=("market", "nunique"),
        eligible_bars=("eligible_bars", "sum"),
        median_market_identical_open_close_pct=(
            "identical_open_close_pct", "median"
        ),
        median_market_body_below_0_10_atr_pct=(
            "body_below_0_10_atr_pct", "median"
        ),
        median_market_body_to_atr=("median_body_to_atr", "median"),
        median_market_close_change_to_atr=(
            "median_close_change_to_atr", "median"
        ),
    )
    report.to_csv(output / "v83_fx_candle_quality_by_market.csv",
                  index=False)
    summary.to_csv(output / "v83_fx_candle_quality_summary.csv",
                   index=False)
    (output / "v83_fx_candle_quality_notes.txt").write_text(
        "V8.3 DATA QUALITY AUDIT ONLY — no trading signals changed.\n"
        "A very high incidence of Open approximately equal to Close "
        "suggests checking Yahoo OHLC semantics, rounding and alternate "
        "data sources before creating an alternative model.\n"
        "This audit cannot prove provider error by itself. "
        "Close-to-close is a different price movement measurement, "
        "NOT a substitute for actual candle body when identifying "
        "engulfing patterns.\n"
        "Historical periods already inspected are development data.\n"
        + "\n".join(errors)
    )
    print("\nV8.3 FX CANDLE QUALITY AUDIT")
    print(summary.to_string(index=False))
    print("\nPER MARKET OPEN/CLOSE AUDIT")
    print(report.to_string(index=False))
    if errors:
        print("\nUnavailable markets: " + "; ".join(errors))


if __name__ == "__main__":
    main()
