"""V8.4 CLOSE-ONLY retrospective diagnostic — no trade execution or optimisation.

Next completed daily CLOSE is the simulated entry; future CLOSE is exit.
This is deliberately not comparable to the old next-OPEN FX backtests:
Yahoo's FX Open was seen to be anomalously close to its own Close.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

from signal_models import CLOSE_CONFIRM_VERSION
from forecast_engine import model_flags
from research_multimarket import FX_MARKETS, cleaned_history


def close_only_trade_rows(candles, version=CLOSE_CONFIRM_VERSION,
                          horizon=5, cost_bps=4.0, start_bar=65):
    """Nonoverlapping close-to-close simulations; signal at i, enter i+1.

    A trading horizon h exits at close i+1+h, not the signal candle close.
    No future candle is included in the signal computation.
    """
    if horizon < 1 or cost_bps < 0:
        raise ValueError("horizon must be positive and cost nonnegative")
    if len(candles) < start_bar + horizon + 2:
        return pd.DataFrame(columns=[
            "signal_bar", "entry_bar", "exit_bar", "direction", "net_pct",
            "gross_pct"
        ])
    close = candles["Close"].astype(float)
    if version == "ema20-ema50-close-bias-benchmark":
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        buys, sells = ema20 > ema50, ema20 < ema50
    else:
        buys, sells = model_flags(candles, version)
    rows = []
    next_allowed = start_bar
    for i in range(start_bar, len(candles) - horizon - 1):
        if i < next_allowed:
            continue
        direction = 1 if bool(buys.iloc[i]) else -1 if bool(sells.iloc[i]) else 0
        if direction == 0:
            continue
        entry_at = i + 1
        exit_at = i + horizon + 1
        entry = float(close.iloc[entry_at])
        exit_ = float(close.iloc[exit_at])
        if not np.isfinite(entry) or not np.isfinite(exit_) or min(entry, exit_) <= 0:
            continue
        gross = 100 * direction * (exit_ / entry - 1)
        rows.append({
            "signal_bar": i, "entry_bar": entry_at, "exit_bar": exit_at,
            "direction": "BUY" if direction == 1 else "SELL",
            "gross_pct": gross, "net_pct": gross - cost_bps / 100,
        })
        next_allowed = exit_at + 1
    return pd.DataFrame(rows)


def market_report(candles, market, split=.70, cost_bps=4.0, horizon=5):
    if not .5 <= split <= .9:
        raise ValueError("split out of bounds")
    split_bar = int(len(candles) * split)
    rows = []
    for version in (CLOSE_CONFIRM_VERSION, "ema20-ema50-close-bias-benchmark"):
        trades = close_only_trade_rows(
            candles, version, horizon=horizon, cost_bps=cost_bps
        )
        for period in ("Development", "Later period"):
            if period == "Development":
                subset = trades.loc[trades.exit_bar < split_bar]
            else:
                subset = trades.loc[trades.signal_bar >= split_bar]
            n = len(subset)
            net = subset.net_pct
            rows.append({
                "market": market, "model": version, "window": period,
                "trades": n,
                "net_win_pct": float((net > 0).mean() * 100) if n else np.nan,
                "mean_net_pct": float(net.mean()) if n else np.nan,
                "gross_direction_win_pct": (
                    float((subset.gross_pct > 0).mean() * 100) if n else np.nan
                ),
            })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="5y", choices=("2y", "5y", "10y"))
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--cost-bps", type=float, default=4.0)
    p.add_argument("--split", type=float, default=.70)
    p.add_argument("--output-dir", default="research_outputs")
    args = p.parse_args()
    if args.horizon < 1 or args.cost_bps < 0 or not .5 <= args.split <= .9:
        p.error("Invalid arguments")
    rows, errors = [], []
    for market, ticker in FX_MARKETS.items():
        try:
            raw = yf.download(
                ticker, period=args.period, interval="1d",
                auto_adjust=False, progress=False, threads=False
            )
            candles = cleaned_history(raw)
            if len(candles) < 150:
                errors.append(f"{market}: insufficient candles")
                continue
            rows.extend(market_report(
                candles, market, args.split, args.cost_bps, args.horizon
            ))
            print(f"{market}: {len(candles)} completed close bars")
        except Exception as exc:
            errors.append(f"{market}: {type(exc).__name__}")
    if not rows:
        raise RuntimeError("No markets analysed; " + "; ".join(errors))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    detail = pd.DataFrame(rows)
    summary_rows = []
    for (version, window), sample in detail.groupby(["model", "window"]):
        active = sample.loc[sample.trades > 0]
        summary_rows.append({
            "model": version, "window": window,
            "markets": int(len(sample)),
            "active_markets": int(len(active)),
            "trades": int(sample.trades.sum()),
            "median_market_net_win_pct": (
                float(active.net_win_pct.median()) if len(active) else np.nan
            ),
            "median_market_mean_net_pct": (
                float(active.mean_net_pct.median()) if len(active) else np.nan
            ),
            "positive_mean_markets": (
                int((active.mean_net_pct > 0).sum()) if len(active) else 0
            ),
        })
    summary = pd.DataFrame(summary_rows)
    detail.to_csv(output / "v84_close_only_per_market.csv", index=False)
    summary.to_csv(output / "v84_close_only_summary.csv", index=False)
    (output / "v84_readme.txt").write_text(
        "RESEARCH ONLY; no forward accuracy, no validated trading edge.\n"
        f"Period={args.period}, horizon={args.horizon} bars AFTER entry, "
        f"cost={args.cost_bps} bps, split={args.split}.\n"
        "Entry uses close i+1 after signal i; exit uses close i+1+horizon. "
        "This differs from previous next-open backtests and is not "
        "a broker fill guarantee.\n"
        "Both time segments have already been inspected in previous "
        "experiments and are not untouched holdout evidence.\n"
        "The simple EMA direction benchmark represents constant "
        "trend exposure, NOT a proper investable portfolio.\n"
        + "\n".join(errors)
    )
    print("\nV8.4 CLOSE-ONLY MODEL VS EMA BASELINE (not forward accuracy)")
    print(summary.to_string(index=False))
    if errors:
        print("Data unavailable: " + "; ".join(errors))


if __name__ == "__main__":
    main()
