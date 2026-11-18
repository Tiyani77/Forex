"""V7 release invariants: same completed-bar signal and exact duplicate keys.

This test suite uses synthetic candles and mocked database calls only.
"""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from forecast_engine import (
    baseline_signals, latest_signal, latest_completed_position,
    model_flags, signal_label,
)
from signal_models import BASELINE_VERSION, MODEL_LABELS
from collect_predictions import prediction as collector_prediction
from prediction_store import prediction_exists


class SharedForecastEngineTests(unittest.TestCase):
    def setUp(self):
        n = 150
        x = np.arange(n)
        close = 100 + x * .02 + np.sin(x / 7) * 1.3
        self.candles = pd.DataFrame(
            {
                "Open": close - 0.2 * np.cos(x / 3),
                "High": close + .7,
                "Low": close - .7,
                "Close": close,
            },
            index=pd.date_range("2026-01-01", periods=n, tz="UTC"),
        )
        self.clock = "2026-06-02T09:00:00Z"

    def test_baseline_dispatcher_returns_original_engulfing_rule(self):
        buy1, sell1 = baseline_signals(self.candles)
        buy2, sell2 = model_flags(self.candles, BASELINE_VERSION)
        pd.testing.assert_series_equal(buy1, buy2)
        pd.testing.assert_series_equal(sell1, sell2)

    def test_all_registered_models_use_same_completed_bar(self):
        for version in MODEL_LABELS:
            latest = latest_signal(
                self.candles, version, now=self.clock
            )
            self.assertIsNotNone(latest)
            self.assertEqual(latest["position"], 149)
            buy, sell = model_flags(self.candles, version)
            self.assertEqual(
                latest["signal"],
                signal_label(buy.iloc[-1], sell.iloc[-1])
            )

    def test_signal_stable_when_forming_future_bar_appended(self):
        base = self.candles.iloc[:-1]
        for version in MODEL_LABELS:
            expected = latest_signal(base, version, now="2026-05-30T10:00:00Z")
            extended = latest_signal(
                self.candles, version, now="2026-05-30T10:00:00Z"
            )
            self.assertEqual(expected, extended, version)

    def test_incomplete_bar_not_considered_daily(self):
        # Last indexed bar starts today: it has not completed yet.
        pos = latest_completed_position(
            self.candles, "1d", now="2026-05-30T12:00:00Z"
        )
        self.assertEqual(pos, 148)

    def test_intraday_always_excludes_most_recent_bar(self):
        pos = latest_completed_position(self.candles, "1h")
        self.assertEqual(pos, 148)

    def test_no_conflicting_trade_directions(self):
        with self.assertRaises(ValueError):
            signal_label(True, True)

    def test_unknown_model_version_rejected(self):
        with self.assertRaises(ValueError):
            model_flags(self.candles, "invented-model-v999")

    def test_collector_calls_shared_engine(self):
        with patch("collect_predictions.latest_signal") as shared:
            shared.return_value = {
                "signal": "SELL", "signal_bar_at": "2026-11-17T00:00:00+00:00",
                "reference_close": 1.105, "model_version": BASELINE_VERSION,
                "position": 149,
            }
            result = collector_prediction(
                "EUR/USD", "EURUSD=X", "1d", self.candles, BASELINE_VERSION
            )
        shared.assert_called_once_with(
            self.candles, BASELINE_VERSION, timeframe="1d"
        )
        self.assertEqual(result["signal"], "SELL")
        self.assertEqual(result["signal_bar_at"], "2026-11-17T00:00:00+00:00")


class ExactDuplicateLookupTests(unittest.TestCase):
    def test_duplicate_lookup_uses_full_identity(self):
        with patch("prediction_store._call", return_value=[{"id": "exists"}]) as db:
            self.assertTrue(prediction_exists(
                "EURUSD=X", "1d", "2026-11-17T00:00:00Z",
                BASELINE_VERSION, 5
            ))
        args = db.call_args.kwargs["params"]
        self.assertEqual(args["ticker"], "eq.EURUSD=X")
        self.assertEqual(args["timeframe"], "eq.1d")
        self.assertEqual(args["model_version"], "eq." + BASELINE_VERSION)
        self.assertEqual(args["horizon_bars"], "eq.5")
        self.assertIn("2026-11-17", args["signal_bar_at"])

    def test_nonduplicate_returns_false(self):
        with patch("prediction_store._call", return_value=[]):
            self.assertFalse(prediction_exists(
                "JPY=X", "1d", "2026-11-17T00:00:00Z",
                BASELINE_VERSION, 5
            ))


if __name__ == "__main__":
    unittest.main()
