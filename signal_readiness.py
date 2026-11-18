"""V8.5 evidence gate and conservative paper-risk calculations.

No signal may be called *validated* solely from historical backtesting or
directional correctness. Broker fills, slippage and execution are unknown.
"""
from math import isfinite


def model_readiness(records_row, minimum_evaluated=100, minimum_markets=10):
    """Fail-closed evidence assessment for a single model's forward results.

    The minimum record and market thresholds only permit manual REVIEW.
    Even a high win rate does not prove profitability or independence.
    """
    if not records_row:
        return {
            "status": "NO_FORWARD_EVIDENCE",
            "real_money_ready": False,
            "reason": "No forward evaluation records are available.",
        }
    n = int(records_row.get("evaluated_directional") or 0)
    markets = int(records_row.get("markets_evaluated") or 0)
    invalid = int(records_row.get("invalid_evaluated") or 0)
    if invalid:
        status = "DATA_QUALITY_REVIEW"
        reason = f"{invalid} evaluated forecasts have invalid evidence fields."
    elif n < minimum_evaluated or markets < minimum_markets:
        status = "INSUFFICIENT_FORWARD_SAMPLE"
        reason = (
            f"Only {n} evaluated directional forecasts across {markets} "
            f"markets; review threshold is {minimum_evaluated} and "
            f"{minimum_markets}, respectively."
        )
    else:
        status = "MANUAL_REVIEW_REQUIRED"
        reason = (
            "Minimum directional forecast sample reached, but forecasts "
            "can be correlated and direction accuracy excludes executable "
            "spreads, slippage, and P&L."
        )
    return {
        "status": status,
        "real_money_ready": False,
        "reason": reason,
    }


def paper_risk_budget(balance_usd, risk_pct=0.5, estimated_stop_loss_usd_per_unit=1.0):
    """Paper-only illustrative sizing, not live broker/order instructions.

    Dollar loss per unit is a USER-ENTERED estimate including stop distance,
    pip value and likely costs. This cannot predict realised loss: gaps,
    price slippage and FX conversion may make actual loss larger.
    """
    vals = (balance_usd, risk_pct, estimated_stop_loss_usd_per_unit)
    if not all(isfinite(float(v)) for v in vals):
        raise ValueError("All inputs must be finite.")
    balance, risk, per_unit = map(float, vals)
    if balance <= 0 or per_unit <= 0 or risk <= 0 or risk > 0.5:
        raise ValueError(
            "Positive balance and estimated loss per unit are required; "
            "illustrative risk is capped at 0.5%."
        )
    budget = balance * risk / 100
    return {
        "risk_budget_usd": round(budget, 2),
        "max_paper_units": int(budget // per_unit),
        "risk_pct": risk,
        "paper_only": True,
    }
