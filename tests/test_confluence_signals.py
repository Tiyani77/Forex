"""V8.0 book-informed trend/pullback candidate invariants (no market API)."""
import unittest

import numpy as np
import pandas as pd

from signal_models import (
    CONFLUENCE_VERSION, confluence_diagnostics, MODEL_LABELS,
)
from forecast_engine import latest_signal, model_flags


class ConfluenceTests(unittest.TestCase):
    def setUp(self):
        n = 180
        x = np.arange(n)
        close = 100 + .04*x + 1.1 * np.sin(x / 6.0)
        self.prices = pd.DataFrame({
            "Open": close - .12 * np.cos(x/3.0),
            "High": close + .35, "Low": close - .35,
            "Close": close,
        }, index=pd.date_range("2025-01-01", periods=n,
                               freq="D", tz="UTC"))

    def test_model_is_versioned_and_registered(self):
        self.assertIn(CONFLUENCE_VERSION, MODEL_LABELS)

    def test_buy_sell_are_boolean_and_mutually_exclusive(self):
        buy, sell, bias = confluence_diagnostics(self.prices)
        self.assertTrue(buy.index.equals(self.prices.index))
        self.assertTrue(sell.index.equals(self.prices.index))
        self.assertTrue(pd.api.types.is_bool_dtype(buy))
        self.assertTrue(pd.api.types.is_bool_dtype(sell))
        self.assertFalse((buy & sell).any())
        self.assertFalse(buy.iloc[:65].any())
        self.assertFalse(sell.iloc[:65].any())
        self.assertTrue(set(bias).issubset(
            {"BULLISH", "BEARISH", "NEUTRAL"}
        ))

    def test_no_lookahead_when_future_bars_appended(self):
        full_buy, full_sell, full_bias = confluence_diagnostics(
            self.prices
        )
        for length in (65, 90, 130, 179):
            b, s, bias = confluence_diagnostics(
                self.prices.iloc[:length]
            )
            pd.testing.assert_series_equal(full_buy.iloc[:length], b)
            pd.testing.assert_series_equal(full_sell.iloc[:length], s)
            pd.testing.assert_series_equal(full_bias.iloc[:length], bias)

    def test_market_bias_is_not_automatic_trade(self):
        # Steady uptrend has bullish bias but no correction/entry setup.
        n = 110
        close = np.linspace(100.0, 111.0, n)
        frame = pd.DataFrame({
            "Open": close - .03,
            "High": close + .15,
            "Low": close - .15,
            "Close": close,
        }, index=pd.date_range("2025-01-01", periods=n,
                               freq="D", tz="UTC"))
        buy, sell, bias = confluence_diagnostics(frame)
        self.assertEqual(bias.iloc[-1], "BULLISH")
        self.assertFalse(bool(buy.iloc[-1]))
        self.assertFalse(bool(sell.iloc[-1]))
        observed = latest_signal(
            frame, CONFLUENCE_VERSION, timeframe="1d",
            now="2025-05-01T10:00:00Z"
        )
        self.assertEqual(observed["signal"], "WAIT")

    def test_engine_matches_diagnostics(self):
        b, s, _ = confluence_diagnostics(self.prices)
        engine_b, engine_s = model_flags(
            self.prices, CONFLUENCE_VERSION
        )
        pd.testing.assert_series_equal(b, engine_b)
        pd.testing.assert_series_equal(s, engine_s)

    def test_empty_data_safe(self):
        b, s, bias = confluence_diagnostics(self.prices.iloc[:0])
        self.assertEqual(len(b), 0)
        self.assertEqual(len(s), 0)
        self.assertEqual(len(bias), 0)


if __name__ == "__main__":
    unittest.main()
