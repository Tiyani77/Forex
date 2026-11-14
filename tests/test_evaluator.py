"""Regression tests for stored forward predictions; no DB or network access."""
import os
import unittest
from unittest.mock import patch

import pandas as pd

# The evaluator validates these at import time. Dummy values are never used
# for network requests because db_request is patched in the tests.
os.environ.setdefault("SUPABASE_URL", "https://tests.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-only-secret")

import evaluate_predictions as evaluator


def sample():
    index = pd.date_range("2026-01-05", periods=9, freq="D", tz="UTC")
    candles = pd.DataFrame(
        {"Close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0]},
        index=index,
    )
    record = {
        "id": "test-id",
        "signal": "BUY",
        "timeframe": "1d",
        "horizon_bars": 5,
        "signal_bar_at": index[0].isoformat(),
        "recorded_at": "2026-01-06T09:00:00+00:00",
        "reference_close": 100.0,
    }
    return record, candles


class EvaluatorTests(unittest.TestCase):
    def test_genuine_future_buy(self):
        record, candles = sample()
        with patch.object(evaluator, "db_request", return_value=[{"id": "test-id"}]) as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "evaluated")
            payload = db.call_args.kwargs["payload"]
            self.assertEqual(payload["status"], "evaluated")
            self.assertTrue(payload["correct"])
            self.assertAlmostEqual(payload["directional_return_pct"], 5.0)

    def test_genuine_future_sell(self):
        record, candles = sample()
        record["signal"] = "SELL"
        with patch.object(evaluator, "db_request", return_value=[{"id": "test-id"}]) as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "evaluated")
            self.assertFalse(db.call_args.kwargs["payload"]["correct"])

    def test_wait_does_not_inflate_accuracy(self):
        record, candles = sample()
        record["signal"] = "WAIT"
        with patch.object(evaluator, "db_request", return_value=[{"id": "test-id"}]) as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "evaluated")
            self.assertIsNone(db.call_args.kwargs["payload"]["correct"])
            self.assertIsNone(db.call_args.kwargs["payload"]["directional_return_pct"])

    def test_late_recording_is_not_scored(self):
        record, candles = sample()
        # Jan 7 is after the Jan 6 first subsequent bar has completed.
        record["recorded_at"] = "2026-01-07T10:00:00+00:00"
        with patch.object(evaluator, "db_request") as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "late_recording")
            db.assert_not_called()

    def test_already_closed_outcome_is_not_scored(self):
        record, candles = sample()
        record["recorded_at"] = "2026-01-12T12:00:00+00:00"
        with patch.object(evaluator, "db_request") as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "late_recording")
            db.assert_not_called()

    def test_wait_for_horizon(self):
        record, candles = sample()
        with patch.object(evaluator, "db_request") as db:
            self.assertEqual(evaluator.evaluate_one(record, candles.iloc[:5]), "not_ready")
            db.assert_not_called()

    def test_missing_signal_bar(self):
        record, candles = sample()
        record["signal_bar_at"] = "2025-12-01T00:00:00+00:00"
        with patch.object(evaluator, "db_request") as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "signal_bar_missing")
            db.assert_not_called()

    def test_invalid_reference_price(self):
        record, candles = sample()
        record["reference_close"] = -1.0
        with patch.object(evaluator, "db_request") as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "invalid_price")
            db.assert_not_called()

    def test_duplicate_completion_is_prevented(self):
        record, candles = sample()
        with patch.object(evaluator, "db_request", return_value=[]) as db:
            self.assertEqual(evaluator.evaluate_one(record, candles), "already_updated")
            self.assertEqual(db.call_args.kwargs["params"]["status"], "eq.pending")


if __name__ == "__main__":
    unittest.main()
