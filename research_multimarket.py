"""V5.1: multi-market retrospective benchmarking of fixed research signal rules.

No trading, secrets, or Supabase writes. Historical checks are exploratory:
none of these samples are a genuinely untouched/prospective validation set.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from signal_models import BASELINE_VERSION, MODEL_LABELS
from forecast_engine import model_flags

# FX-only to make comparisons economically more coherent than mixing asset classes.
FX_MARKETS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X", "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X", "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X", "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X", "GBP/JPY": "GBPJPY=X",
    "EUR/AUD": "EURAUD=X", "AUD/JPY": "AUDJPY=X",
    "GBP/AUD": "GBPAUD=X", "EUR/CHF": "EURCHF=X",
    "NZD/JPY": "NZDJPY=X",
}


def cleaned_history(frame, now=None):
    """Keep only completed daily bars in chronological UTC order."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    df = frame.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close"]
    if any(c not in df.columns for c in required):
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.dropna(subset=required).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.to_datetime(now, utc=True)
    return df.loc[df.index + pd.Timedelta(days=1) <= now].copy()



def trade_rows(df, version, horizon=5, cost_bps=4.0, min_history=60):
    """Trade signal at close i, entry i+1 open, exit i+horizon close.

    Signal indicators are calculated on the full past-to-present input,
    but evaluate only completed exits. Skip trades whose holding windows
    overlap; model-specific signals are intentionally not blended.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if cost_bps < 0:
        raise ValueError("cost_bps must be >= 0")
    if len(df) < min_history + horizon + 1:
        return pd.DataFrame()

    buy, sell = model_flags(df, version)
    rows = []
    next_allowed = min_history
    for i in range(min_history, len(df) - horizon):
        if i < next_allowed:
            continue
        direction = 1 if bool(buy.iloc[i]) else -1 if bool(sell.iloc[i]) else 0
        if direction == 0:
            continue
        entry = float(df.Open.iloc[i + 1])
        exit_price = float(df.Close.iloc[i + horizon])
        if not (np.isfinite(entry) and np.isfinite(exit_price) and
                entry > 0 and exit_price > 0):
            continue
        gross_pct = 100 * direction * (exit_price / entry - 1)
        rows.append({
            "signal_position": i,
            "exit_position": i + horizon,
            "signal_at": df.index[i].isoformat(),
            "exit_at": df.index[i + horizon].isoformat(),
            "direction": "BUY" if direction == 1 else "SELL",
            "gross_return_pct": gross_pct,
            "net_return_pct": gross_pct - cost_bps / 100,
        })
        next_allowed = i + horizon + 1
    return pd.DataFrame(rows)


def summarise(part, market, version, window, eligible_bars):
    count = len(part)
    values = (part["net_return_pct"].astype(float)
              if count else pd.Series(dtype=float))
    win_count = int((values > 0).sum()) if count else 0
    gross_gain = float(values[values > 0].sum()) if count else 0.0
    gross_loss = float(-values[values < 0].sum()) if count else 0.0
    return {
        "market": market, "model": version, "window": window,
        "eligible_bars": int(eligible_bars), "trades": count,
        "net_wins": win_count,
        "net_win_pct": round(100 * win_count / count, 2) if count else None,
        "mean_net_pct": round(float(values.mean()), 5) if count else None,
        "compound_net_pct": round(
            100 * (float((1 + values / 100).prod()) - 1), 4
        ) if count else None,
        "profit_factor": round(gross_gain / gross_loss, 3)
        if gross_loss > 0 else None,
    }


def evaluate_market(df, market, split_fraction=0.70, horizon=5, cost_bps=4.0):
    if not 0.5 <= split_fraction <= 0.9:
        raise ValueError("Split must be between 0.50 and 0.90")
    if len(df) < 150:
        return []
    split = int(len(df) * split_fraction)
    rows = []
    # Signal and exit must BOTH fall inside each evaluation segment;
    # do not count trades straddling the split.
    for version in MODEL_LABELS:
        trades = trade_rows(df, version, horizon=horizon, cost_bps=cost_bps)
        if trades.empty:
            parts = {"Development": trades, "Later period": trades}
        else:
            parts = {
                "Development": trades.loc[trades["exit_position"] < split],
                "Later period": trades.loc[trades["signal_position"] >= split],
            }
        for window, part in parts.items():
            available = (split - 60 if window == "Development"
                         else len(df) - split - horizon)
            rows.append(summarise(
                part, market, version, window, max(0, available)
            ))
    return rows


def aggregate_market_balanced(results):
    """Give each market equal weight in the win-rate diagnostic.

    Do not silently pool overlapping/correlated currency-pair forecasts.
    Report total trade count alongside the number of markets with trades.
    """
    rows = []
    for (model, window), group in results.groupby(["model", "window"]):
        active = group.loc[group.trades > 0]
        rows.append({
            "model": model, "window": window,
            "markets_tested": int(len(group)),
            "markets_with_trades": int(len(active)),
            "trades_total": int(group.trades.sum()),
            "median_market_net_win_pct": (
                round(float(active.net_win_pct.median()), 2)
                if len(active) else None
            ),
            "median_market_mean_net_pct": (
                round(float(active.mean_net_pct.median()), 5)
                if len(active) else None
            ),
            "positive_mean_markets": (
                int((active.mean_net_pct > 0).sum()) if len(active) else 0
            ),
        })
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--period", default="5y",
                   choices=["2y", "5y", "10y"])
    p.add_argument("--horizon", type=int, default=5)
    p.add_argument("--cost-bps", type=float, default=4.0)
    p.add_argument("--split", type=float, default=0.70)
    p.add_argument("--output-dir", default="research_outputs")
    p.add_argument("--max-markets", type=int, default=15)
    args = p.parse_args()

    if args.horizon < 1 or args.cost_bps < 0 or args.max_markets < 1:
        p.error("invalid horizon, cost or market count")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    for market, ticker in list(FX_MARKETS.items())[:args.max_markets]:
        try:
            candles = yf.download(
                ticker, period=args.period, interval="1d",
                auto_adjust=False, progress=False, threads=False,
            )
            candles = cleaned_history(candles)
            if len(candles) < 150:
                errors.append(f"{market}: insufficient candles ({len(candles)})")
                continue
            results.extend(evaluate_market(
                candles, market, split_fraction=args.split,
                horizon=args.horizon, cost_bps=args.cost_bps,
            ))
            print(f"{market}: {len(candles)} completed bars")
        except Exception as exc:
            errors.append(f"{market}: {type(exc).__name__} ({str(exc)[:100]})")

    if not results:
        raise RuntimeError("No markets could be evaluated. " + "; ".join(errors))

    frame = pd.DataFrame(results)
    summary = aggregate_market_balanced(frame)
    frame.to_csv(output / "per_market_research.csv", index=False)
    summary.to_csv(output / "market_balanced_summary.csv", index=False)
    (output / "run_notes.txt").write_text(
        "V5.1 RESEARCH ONLY, NOT VERIFIED OUT-OF-SAMPLE ACCURACY\n"
        f"Period: {args.period}; horizon: {args.horizon} bars; "
        f"round-trip cost: {args.cost_bps} bps; chronological split: "
        f"{args.split:.0%}\n"
        f"Successful markets: {frame.market.nunique()}; "
        f"unavailable: {len(errors)}\n" + "\n".join(errors) + "\n"
    )
    print("\nMARKET-BALANCED DIAGNOSTIC (not forward accuracy)")
    print(summary.to_string(index=False))
    if errors:
        print("\nMissing market data:")
        for err in errors:
            print(err)


if __name__ == "__main__":
    main()
