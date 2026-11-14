"""Deterministic no-network checks for V5 multi-market validation."""
import unittest
import numpy as np
import pandas as pd
from research_multimarket import (
    cleaned_history, trade_rows, evaluate_market, aggregate_market_balanced,
)
from signal_models import MODEL_LABELS


class ResearchTests(unittest.TestCase):
    def setUp(self):
        n = 240
        x = np.arange(n)
        close = 100 + x * 0.03 + 2.5 * np.sin(x / 9)
        self.data = pd.DataFrame(
            {"Open": close - 0.2, "High": close + 0.4,
             "Low": close - 0.4, "Close": close},
            index=pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
        )

    def test_only_complete_bars(self):
        short = self.data.iloc[:10]
        cleaned = cleaned_history(short, now="2020-01-10T12:00:00Z")
        self.assertEqual(len(cleaned), 9)
        self.assertTrue((cleaned.index <= pd.Timestamp("2020-01-09", tz="UTC")).all())

    def test_no_horizon_overlap(self):
        for version in MODEL_LABELS:
            trades = trade_rows(self.data, version, horizon=5)
            if not trades.empty:
                self.assertTrue(
                    (trades.signal_position.diff().dropna() > 5).all()
                )
                self.assertTrue(
                    (trades.exit_position == trades.signal_position + 5).all()
                )

    def test_holdout_does_not_cross_split(self):
        results = evaluate_market(self.data, "synthetic", horizon=5)
        self.assertEqual(len(results), 2 * len(MODEL_LABELS))
        self.assertEqual(
            {r["window"] for r in results}, {"Development", "Later period"}
        )

    def test_later_period_is_unchanged_by_earlier_result_aggregation(self):
        frame = pd.DataFrame([
            {"model": "m", "window": "Later period", "market": "A",
             "trades": 10, "net_win_pct": 80.0, "mean_net_pct": .2},
            {"model": "m", "window": "Later period", "market": "B",
             "trades": 100, "net_win_pct": 20.0, "mean_net_pct": -.1},
        ])
        result = aggregate_market_balanced(frame).iloc[0]
        self.assertEqual(result["median_market_net_win_pct"], 50.0)
        self.assertEqual(result["markets_with_trades"], 2)
        self.assertEqual(result["trades_total"], 110)


if __name__ == "__main__":
    unittest.main()
