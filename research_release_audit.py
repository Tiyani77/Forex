"""V5.5 conservative research audit. No automatic model promotion.

Consumes per-market sensitivity CSV from the V5.4 research workflow.
The report describes historical evidence only: it never treats an already
inspected historical split as untouched validation or predicts profitability.
"""
import argparse
from pathlib import Path

import pandas as pd

from research_robustness import COSTS_BPS, HORIZONS, sensitivity_summary
from signal_models import MODEL_LABELS


REQUIRED = {
    "model", "market", "horizon", "cost_bps", "trades",
    "net_win_pct", "mean_net_pct", "gross_direction_correct_pct"
}


def audit_research(detail):
    missing = REQUIRED - set(detail.columns)
    if missing:
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    if detail.empty:
        raise ValueError("Cannot audit empty research data")
    # Ensure no duplicate market/model/scenario records masquerade as evidence.
    key = ["model", "market", "horizon", "cost_bps"]
    if detail.duplicated(subset=key).any():
        raise ValueError("Duplicate market/model/scenario rows")
    unexpected = set(detail.model.unique()) - set(MODEL_LABELS)
    if unexpected:
        raise ValueError("Unknown model versions: " + ", ".join(sorted(unexpected)))

    # The same model must be tested on the same set of markets at each
    # fixed scenario; otherwise the stress-test coverage is incomplete.
    baseline = detail.loc[
        (detail.horizon == 5) & (detail.cost_bps == 4.0)
    ]
    if baseline.empty:
        raise ValueError("Missing required 5-bar, 4-bps scenario")

    rows = []
    for model in MODEL_LABELS:
        group = detail.loc[detail.model == model]
        if group.empty:
            raise ValueError(f"No records for {model}")
        for horizon in HORIZONS:
            for cost in COSTS_BPS:
                count = len(group.loc[
                    (group.horizon == horizon) & (group.cost_bps == cost)
                ])
                if count != group.market.nunique():
                    raise ValueError(
                        f"Incomplete scenario coverage: {model} {horizon} {cost}"
                    )

        reference = group.loc[
            (group.horizon == 5) & (group.cost_bps == 4.0)
        ]
        active = reference.loc[reference.trades > 0]
        trades = int(reference.trades.sum())
        markets = int(reference.market.nunique())
        active_markets = int(len(active))
        median_net = (
            float(active.mean_net_pct.median()) if active_markets else None
        )
        positive_markets = int(
            (active.mean_net_pct > 0).sum()
        ) if active_markets else 0
        # Inspect 4 bps estimates across all *predeclared* horizons, not
        # just the most flattering horizon.
        horizon_positive = 0
        horizon_nonempty = 0
        for horizon in HORIZONS:
            segment = group.loc[
                (group.horizon == horizon) & (group.cost_bps == 4.0)
                & (group.trades > 0)
            ]
            if segment.empty:
                continue
            horizon_nonempty += 1
            if float(segment.mean_net_pct.median()) > 0:
                horizon_positive += 1

        if trades < 50 or active_markets < 10:
            diagnosis = "INSUFFICIENT_SAMPLE"
        elif median_net is None or median_net <= 0:
            diagnosis = "NEGATIVE_HISTORICAL_MEDIAN"
        elif horizon_positive < len(HORIZONS):
            diagnosis = "HORIZON_SENSITIVE_EXPLORATORY"
        else:
            diagnosis = "POSITIVE_HISTORICAL_DIAGNOSTIC_ONLY"

        rows.append({
            "model_version": model,
            "market_count": markets,
            "active_markets_5bar": active_markets,
            "trades_5bar_4bps": trades,
            "median_market_mean_net_pct_5bar_4bps": (
                round(median_net, 5) if median_net is not None else None
            ),
            "positive_mean_markets_5bar_4bps": positive_markets,
            "horizons_positive_median_at_4bps": horizon_positive,
            "horizons_with_trades_at_4bps": horizon_nonempty,
            "research_diagnosis": diagnosis,
            "production_status": "NOT_VALIDATED",
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="research_outputs/v54_sensitivity_by_market.csv"
    )
    parser.add_argument("--output-dir", default="research_outputs")
    args = parser.parse_args()
    details = pd.read_csv(args.input)
    report = audit_research(details)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report.to_csv(out / "v55_release_audit.csv", index=False)
    (out / "v55_release_audit_notes.txt").write_text(
        "V5.5 MODEL READINESS AUDIT — NOT FORWARD ACCURACY\n"
        "No automatic strategy activation, suppression or optimization.\n"
        "All six models remain NOT_VALIDATED regardless of retrospective results.\n"
        "INSUFFICIENT_SAMPLE: fewer than 50 5-bar/4-bps trades or "
        "fewer than 10 markets with such trades.\n"
        "NEGATIVE_HISTORICAL_MEDIAN: median per-active-market average "
        "net trade return is not positive at five bars and 4 bps.\n"
        "HORIZON_SENSITIVE_EXPLORATORY: median positive at five bars, "
        "but not across all three predeclared horizons at 4 bps.\n"
        "POSITIVE_HISTORICAL_DIAGNOSTIC_ONLY is not proof and does not "
        "qualify for automated trading or forward-accuracy claims.\n"
        "Historical periods already inspected during development are "
        "not untouched validation. Genuine forward samples are required.\n"
    )
    print("\nV5.5 RESEARCH RELEASE AUDIT — NO MODEL VALIDATED")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
