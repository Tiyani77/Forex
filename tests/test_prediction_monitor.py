"""V6.2 pending-observation monitor offline regression tests."""
import unittest

import pandas as pd

from prediction_monitor import pending_diagnostic


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.candles = pd.DataFrame(
            {"Close": range(10)},
            index=pd.date_range("2026-11-01", periods=10, tz="UTC")
        )
        self.record = {
            "timeframe": "1d",
            "horizon_bars": 5,
            "signal_bar_at": "2026-11-06T00:00:00Z",
            "recorded_at": "2026-11-07T08:00:00Z",
        }

    def test_counts_bars_after_signal_only(self):
        result = pending_diagnostic(
            self.record, self.candles.iloc[:8],
            now="2026-11-08T12:00:00Z"
        )
        self.assertEqual(result["reason"], "waiting_for_completed_bars")
        self.assertEqual(result["bars_seen"], 2)
        self.assertEqual(result["bars_remaining"], 3)
        self.assertFalse(result["review_suggested"])

    def test_ready_when_horizon_seen(self):
        record = dict(self.record, signal_bar_at="2026-11-04T00:00:00Z")
        result = pending_diagnostic(
            record, self.candles, now="2026-11-11T00:00:00Z"
        )
        self.assertEqual(result["reason"], "ready_for_evaluation")
        self.assertEqual(result["bars_remaining"], 0)

    def test_missing_candles_requires_attention_if_aged(self):
        result = pending_diagnostic(
            self.record, pd.DataFrame(), now="2026-12-01T00:00:00Z"
        )
        self.assertEqual(result["reason"], "no_market_data")
        self.assertTrue(result["review_suggested"])

    def test_missing_anchor_is_not_progress(self):
        record = dict(self.record, signal_bar_at="2026-10-01T00:00:00Z")
        result = pending_diagnostic(
            record, self.candles, now="2026-11-08T12:00:00Z"
        )
        self.assertEqual(result["reason"], "signal_bar_missing")
        self.assertEqual(result["bars_seen"], 0)

    def test_monitor_does_not_modify_forecast(self):
        original = self.record.copy()
        pending_diagnostic(self.record, self.candles,
                           now="2026-11-08T12:00:00Z")
        self.assertEqual(original, self.record)


if __name__ == "__main__":
    unittest.main()
