"""Offline invariant checks: V8.2 diagnostic reproduces frozen V8.1 model."""
import unittest
import numpy as np
import pandas as pd

from diagnose_pullback_v2 import STAGES, filter_funnel
from signal_models import pullback_v2_signals


class FilterFunnelTests(unittest.TestCase):
    def setUp(self):
        x = np.arange(160)
        c = 100 + x * 0.04 + 1.5 * np.sin(x / 6)
        self.prices = pd.DataFrame({
            "Open": c - .2 * np.cos(x / 4),
            "High": c + .6, "Low": c - .6, "Close": c,
        }, index=pd.date_range("2024-01-01", periods=len(x),
                               tz="UTC", freq="D"))

    def test_funnel_must_match_model(self):
        report = filter_funnel(self.prices)
        self.assertEqual(len(report), 2 * 2 * (len(STAGES) + 2))
        for period in ("Development", "Later period"):
            for side in ("BUY", "SELL"):
                group = [r for r in report if r["period"] == period
                         and r["side"] == side]
                counts = [r["passing_bars"] for r in group[:len(STAGES)]]
                self.assertEqual(len(counts), len(STAGES))
                self.assertEqual(counts, sorted(counts, reverse=True))
                self.assertEqual(counts[-1], counts[-2])
                self.assertEqual(group[-2]["stage"],
                                 "EMA20 extension pass (independent)")
                self.assertEqual(group[-1]["stage"],
                                 "Minimum body pass (independent)")
                self.assertGreaterEqual(group[-1]["passing_bars"], counts[-1])
                self.assertGreaterEqual(group[-2]["passing_bars"], counts[-1])

    def test_report_is_nonmutating(self):
        before = self.prices.copy(deep=True)
        filter_funnel(self.prices)
        pd.testing.assert_frame_equal(self.prices, before)

    def test_empty(self):
        self.assertEqual(filter_funnel(self.prices.iloc[:0]), [])

    def test_actual_model_unchanged(self):
        before = pullback_v2_signals(self.prices)
        filter_funnel(self.prices)
        after = pullback_v2_signals(self.prices)
        for a,b in zip(before, after):
            pd.testing.assert_series_equal(a,b)


if __name__ == "__main__":
    unittest.main()
