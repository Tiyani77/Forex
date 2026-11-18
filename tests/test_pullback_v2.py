"""V8.1 deterministic signal behavior and no-lookahead tests."""
import unittest

import numpy as np
import pandas as pd

from forecast_engine import model_flags, latest_signal
from signal_models import (
    PULLBACK_V2_VERSION, CONFLUENCE_VERSION, MODEL_LABELS,
    pullback_v2_diagnostics
)


class PullbackReclaimV2Tests(unittest.TestCase):
    def setUp(self):
        n = 180
        x = np.arange(n)
        close = 100 + 0.055 * x + 0.8 * np.sin(x / 5.0)
        self.frame = pd.DataFrame({
            "Open": close - .1 * np.cos(x / 4),
            "High": close + .5,
            "Low": close - .5,
            "Close": close,
        }, index=pd.date_range("2025-01-01", periods=n, tz="UTC"))

    def test_separate_version_preserves_v1(self):
        self.assertIn(PULLBACK_V2_VERSION, MODEL_LABELS)
        self.assertIn(CONFLUENCE_VERSION, MODEL_LABELS)
        self.assertNotEqual(PULLBACK_V2_VERSION, CONFLUENCE_VERSION)

    def test_causal_boolean_and_no_conflicts(self):
        full_b, full_s, full_bias = pullback_v2_diagnostics(self.frame)
        self.assertTrue(pd.api.types.is_bool_dtype(full_b))
        self.assertTrue(pd.api.types.is_bool_dtype(full_s))
        self.assertFalse((full_b & full_s).any())
        self.assertFalse(full_b.iloc[:65].any())
        self.assertFalse(full_s.iloc[:65].any())
        self.assertTrue(set(full_bias).issubset(
            {"BULLISH", "BEARISH", "NEUTRAL"}
        ))
        for n in (66, 90, 125, 179):
            b, s, bias = pullback_v2_diagnostics(self.frame.iloc[:n])
            pd.testing.assert_series_equal(full_b.iloc[:n], b)
            pd.testing.assert_series_equal(full_s.iloc[:n], s)
            pd.testing.assert_series_equal(full_bias.iloc[:n], bias)

    def test_shared_model_dispatch(self):
        b, s, _ = pullback_v2_diagnostics(self.frame)
        eb, es = model_flags(self.frame, PULLBACK_V2_VERSION)
        pd.testing.assert_series_equal(b, eb)
        pd.testing.assert_series_equal(s, es)

    def test_steady_trend_does_not_force_trade(self):
        n = 120
        c = np.linspace(100, 110, n)
        frame = pd.DataFrame({
            "Open": c - .08, "High": c + .2,
            "Low": c - .2, "Close": c
        }, index=pd.date_range("2025-01-01", periods=n, tz="UTC"))
        buy, sell, bias = pullback_v2_diagnostics(frame)
        self.assertEqual(bias.iloc[-1], "BULLISH")
        self.assertFalse(bool(buy.iloc[-1]))
        self.assertFalse(bool(sell.iloc[-1]))
        forecast = latest_signal(
            frame, PULLBACK_V2_VERSION,
            timeframe="1d", now="2025-05-10T10:00:00Z"
        )
        self.assertEqual(forecast["signal"], "WAIT")

    def test_empty_market_safe(self):
        buy, sell, bias = pullback_v2_diagnostics(
            self.frame.iloc[:0]
        )
        self.assertEqual(len(buy), 0)
        self.assertEqual(len(sell), 0)
        self.assertEqual(len(bias), 0)


if __name__ == "__main__":
    unittest.main()
