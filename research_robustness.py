"""V5.4: preset holding-period and trading-cost sensitivity diagnostics.

Uses original versioned signal rules without fitting any parameter.
All figures remain retrospective model-development diagnostics.
"""
import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

from research_multimarket import (
    FX_MARKETS, cleaned_history, trade_rows, aggregate_market_balanced,
    summarise,
)
from signal_models import MODEL_LABELS

# Predeclared rather than selected after seeing returns.
HORIZONS = (2, 5, 10)
COSTS_BPS = (0.0, 4.0, 10.0)


def market_sensitivity(candles, market, split_fraction=0.70):
    """Same price history, independently simulated for each horizon and cost.

    The evaluation split is chronological, and no trade may cross its
    boundary. Trades differ by horizon because overlapping positions
    are intentionally skipped in each independently defined scenario.
    """
    if len(candles) < 150:
        return []
    split = int(len(candles) * split_fraction)
    observations = []
    for version in MODEL_LABELS:
        for horizon in HORIZONS:
            for cost in COSTS_BPS:
                trades = trade_rows(
                    candles, version, horizon=horizon, cost_bps=cost
                )
                if trades.empty:
                    selected = trades
                else:
                    selected = trades.loc[
                        trades["signal_position"] >= split
                    ].copy()
                summary = summarise(
                    selected, market, version, "Later period",
                    max(0, len(candles) - split - horizon)
                )
                summary["horizon"] = horizon
                summary["cost_bps"] = cost
                if selected.empty:
                    summary["gross_direction_correct_pct"] = None
                else:
                    summary["gross_direction_correct_pct"] = round(
                        100 * float(
                            (selected["gross_return_pct"] > 0).mean()
                        ), 2
                    )
                observations.append(summary)
    return observations


def sensitivity_summary(market_results):
    """Equal-weight median across active markets for each scenario."""
    grouped = []
    for (model, horizon, cost), subset in market_results.groupby(
        ["model", "horizon", "cost_bps"]
    ):
        active = subset.loc[subset["trades"] > 0]
        grouped.append({
            "model": model,
            "horizon": int(horizon),
            "cost_bps": float(cost),
            "markets_with_trades": int(len(active)),
            "trades_total": int(subset["trades"].sum()),
            "median_market_gross_direction_correct_pct": (
                round(float(active["gross_direction_correct_pct"].median()), 2)
                if len(active) else None
            ),
            "median_market_net_win_pct": (
                round(float(active["net_win_pct"].median()), 2)
                if len(active) else None
            ),
            "median_market_mean_net_pct": (
                round(float(active["mean_net_pct"].median()), 5)
                if len(active) else None
            ),
            "markets_with_positive_mean_net": int(
                (active["mean_net_pct"] > 0).sum()
            ) if len(active) else 0,
        })
    return pd.DataFrame(grouped).sort_values(
        ["model", "horizon", "cost_bps"]
    ).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=("2y", "5y", "10y"),
                        default="5y")
    parser.add_argument("--split", type=float, default=0.70)
    parser.add_argument("--max-markets", type=int, default=15)
    parser.add_argument("--output-dir", default="research_outputs")
    args = parser.parse_args()
    if not 0.5 <= args.split <= 0.9 or args.max_markets < 1:
        parser.error("Invalid split or market count")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    observations = []
    failures = []
    for market, ticker in list(FX_MARKETS.items())[:args.max_markets]:
        try:
            prices = yf.download(
                ticker, period=args.period, interval="1d",
                auto_adjust=False, progress=False, threads=False
            )
            prices = cleaned_history(prices)
            if len(prices) < 150:
                failures.append(f"{market}: insufficient history")
                continue
            observations.extend(
                market_sensitivity(prices, market, args.split)
            )
            print(f"{market}: {len(prices)} completed daily bars")
        except Exception as exc:
            failures.append(f"{market}: {type(exc).__name__}")

    if not observations:
        raise RuntimeError("No valid market data for sensitivity analysis")
    detail = pd.DataFrame(observations)
    summary = sensitivity_summary(detail)
    detail.to_csv(output / "v54_sensitivity_by_market.csv", index=False)
    summary.to_csv(output / "v54_sensitivity_summary.csv", index=False)
    (output / "v54_notes.txt").write_text(
        "V5.4 DEVELOPMENT DIAGNOSTIC — NOT FORWARD ACCURACY\n"
        "Prespecified horizons: 2, 5, 10 daily bars. "
        "Indicative round-trip costs: 0, 4, 10 bps.\n"
        "Entry at next bar open, exit at close of signal+horizon bar; "
        "no overlapping simulated positions.\n"
        "Gross direction win rate reflects simulated entry-to-exit "
        "price direction. Net win rates subtract estimated costs.\n"
        "These retrospective results have been inspected during "
        "development and must not be called untouched holdout data.\n"
        f"Markets used: {detail.market.nunique()}. "
        f"Missing markets: {len(failures)}.\n" + "\n".join(failures)
    )
    print("\nV5.4 SENSITIVITY DIAGNOSTIC (NOT FORWARD ACCURACY)")
    print(summary.to_string(index=False))
    if failures:
        print("Unavailable markets: " + "; ".join(failures))


if __name__ == "__main__":
    main()
