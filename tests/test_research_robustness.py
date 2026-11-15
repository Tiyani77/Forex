"""V5.4 deterministic checks: fixed scenarios, cost and timing invariants."""
import unittest

import numpy as np
import pandas as pd

from research_robustness import (
    HORIZONS, COSTS_BPS, market_sensitivity, sensitivity_summary
)
from signal_models import MODEL_LABELS


class RobustnessTests(unittest.TestCase):
    def setUp(self):
        n = 200
        x = np.arange(n)
        close = 100 + 0.04 * x + 1.8 * np.sin(x / 8)
        self.df = pd.DataFrame(
            {"Open": close - 0.1, "High": close + 0.6,
             "Low": close - 0.6, "Close": close},
            index=pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC")
        )

    def test_prespecified_scenarios(self):
        result = market_sensitivity(self.df, "synthetic")
        self.assertEqual(len(result), len(MODEL_LABELS) * 3 * 3)
        self.assertEqual({x["horizon"] for x in result}, set(HORIZONS))
        self.assertEqual({x["cost_bps"] for x in result}, set(COSTS_BPS))

    def test_higher_cost_cannot_improve_net_win_for_same_trades(self):
        rows = pd.DataFrame(market_sensitivity(self.df, "synthetic"))
        for (model, horizon), subset in rows.groupby(["model", "horizon"]):
            subset = subset.sort_values("cost_bps")
            self.assertEqual(subset["trades"].nunique(), 1)
            actual = subset["net_win_pct"].dropna().to_numpy(dtype=float)
            self.assertTrue((np.diff(actual) <= 0.001).all(),
                            f"{model} horizon {horizon}")

    def test_summary_contains_each_scenario(self):
        rows = pd.DataFrame(market_sensitivity(self.df, "synthetic"))
        summary = sensitivity_summary(rows)
        self.assertEqual(len(summary), len(MODEL_LABELS) * 9)
        self.assertTrue(
            (summary["markets_with_trades"] <= 1).all()
        )


if __name__ == "__main__":
    unittest.main()
