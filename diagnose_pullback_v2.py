"""V8.2 observational filter funnel for the *unchanged* V8.1 strategy.

No model thresholds are changed, and no results are used to choose trades.
The funnel counts bar-level conditions; it is NOT a backtest, trade count,
predictive accuracy estimate, or feature-importance attribution.
"""
import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

from research_multimarket import FX_MARKETS, cleaned_history
from signal_models import _atr, pullback_v2_signals


STAGES = ("Eligible bars", "EMA trend", "Countertrend candle in last 3",
          "EMA20 touched in last 3", "Directional reclaim",
          "Body and extension", "Final qualifying signal")


def filter_funnel(candles, split=0.70):
    if not 0.5 <= split <= 0.9:
        raise ValueError("split must be between 0.50 and 0.90")
    if candles.empty:
        return []
    close = candles["Close"]
    opn = candles["Open"]
    high = candles["High"]
    low = candles["Low"]
    e20 = close.ewm(span=20, adjust=False).mean()
    e50 = close.ewm(span=50, adjust=False).mean()
    atr = _atr(candles)
    eligible = ((pd.Series(range(len(candles)), index=candles.index) >= 65)
                & atr.gt(0))
    rising = (e20 > e50) & (e50 > e50.shift(5))
    falling = (e20 < e50) & (e50 < e50.shift(5))
    past_bear = pd.concat([
        close.shift(k) < opn.shift(k) for k in (1, 2, 3)
    ], axis=1).any(axis=1)
    past_bull = pd.concat([
        close.shift(k) > opn.shift(k) for k in (1, 2, 3)
    ], axis=1).any(axis=1)
    support = pd.concat([
        low.shift(k) <= e20.shift(k) + 0.5 * atr.shift(k)
        for k in (1, 2, 3)
    ], axis=1).any(axis=1)
    resistance = pd.concat([
        high.shift(k) >= e20.shift(k) - 0.5 * atr.shift(k)
        for k in (1, 2, 3)
    ], axis=1).any(axis=1)
    direction_buy = ((close > opn) & (close > close.shift(1))
                     & (close > e20))
    direction_sell = ((close < opn) & (close < close.shift(1))
                      & (close < e20))
    body = ((close - opn).abs() >= 0.10 * atr)
    extension = ((close - e20).abs() <= 1.5 * atr)
    b, s = pullback_v2_signals(candles)

    rows = []
    cutoff = int(len(candles) * split)
    for window, indexes in (
        ("Development", candles.index[:cutoff]),
        ("Later period", candles.index[cutoff:]),
    ):
        for side, trend, correction, level, direction, actual in (
            ("BUY", rising, past_bear, support, direction_buy, b),
            ("SELL", falling, past_bull, resistance, direction_sell, s),
        ):
            current = eligible.copy()
            gates = (
                eligible, trend, correction, level, direction,
                body & extension
            )
            for idx, (stage, gate) in enumerate(zip(STAGES, gates)):
                if idx:
                    current = current & gate
                rows.append({
                    "period": window,
                    "side": side,
                    "stage": stage,
                    "passing_bars": int(current.loc[indexes].sum()),
                    "stage_order": idx,
                    "eligible_bars": int(eligible.loc[indexes].sum()),
                })
            # Check that standalone independent diagnostic reproduces
            # the exact, versioned output of the actual signal model.
            if not current.fillna(False).equals(
                (eligible & actual).fillna(False)
            ):
                raise AssertionError(
                    "V8.1 model and diagnostic funnel are inconsistent"
                )
            rows.append({
                "period": window, "side": side,
                "stage": STAGES[-1],
                "stage_order": len(STAGES)-1,
                "passing_bars": int(actual.loc[indexes].sum()),
                "eligible_bars": int(eligible.loc[indexes].sum()),
            })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="5y", choices=["2y", "5y", "10y"])
    p.add_argument("--output-dir", default="research_outputs")
    p.add_argument("--split", type=float, default=0.7)
    args = p.parse_args()
    all_rows, errors = [], []
    for market, ticker in FX_MARKETS.items():
        try:
            downloaded = yf.download(
                ticker, period=args.period, interval="1d",
                auto_adjust=False, progress=False, threads=False
            )
            candles = cleaned_history(downloaded)
            if len(candles) < 150:
                errors.append(f"{market}: insufficient candle history")
                continue
            for row in filter_funnel(candles, args.split):
                all_rows.append({"market": market, **row})
            print(f"{market}: {len(candles)} completed bars")
        except Exception as exc:
            errors.append(f"{market}: {type(exc).__name__}")
    if not all_rows:
        raise RuntimeError("No valid markets: " + "; ".join(errors))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    full = pd.DataFrame(all_rows)
    aggregate = full.groupby(
        ["period", "side", "stage_order", "stage"], as_index=False
    ).agg(
        passing_bars=("passing_bars", "sum"),
        eligible_bars=("eligible_bars", "sum"),
        markets=("market", "nunique"),
    ).sort_values(["period", "side", "stage_order"])
    full.to_csv(output / "v82_v81_filter_funnel_per_market.csv", index=False)
    aggregate.to_csv(output / "v82_v81_filter_funnel_summary.csv", index=False)
    (output / "v82_v81_funnel_notes.txt").write_text(
        "V8.2 OBSERVATIONAL RESEARCH — not validation, trade entries, "
        "or accuracy.\n"
        "Cumulative AND-gate bar counts for v8.1, separately BUY and SELL.\n"
        "These bar counts can overlap across adjacent candles; "
        "backtests skip overlapping trades.\n"
        "The V8.1 signal rules remain unchanged. Existing inspected history "
        "must NOT be described as an untouched test set.\n"
        + "\n".join(errors)
    )
    print("\nV8.2 FILTER FUNNEL — UNCHANGED V8.1 RULES (bar counts)")
    print(aggregate.to_string(index=False))
    if errors:
        print("\nUnavailable: " + "; ".join(errors))


if __name__ == "__main__":
    main()
