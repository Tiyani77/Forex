"""Deterministic tests of FX OHLC quality report — no market network."""
import unittest
import numpy as np
import pandas as pd
from audit_fx_candle_quality import candle_quality


class FXCandleQualityTests(unittest.TestCase):
    def candles(self, same_open_close=False):
        n = 120
        close = 100 + np.arange(n) * .12
        open_ = close.copy() if same_open_close else close - .25
        return pd.DataFrame({
            "Open": open_, "High": close + .5,
            "Low": close - .5, "Close": close,
        }, index=pd.date_range("2025-01-01", periods=n, tz="UTC"))

    def test_identical_ohlc_open_close_is_reported(self):
        rows = candle_quality(self.candles(True), "Synthetic")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["identical_open_close_pct"] == 100
                            for r in rows))
        self.assertTrue(all(r["body_below_0_10_atr_pct"] == 100
                            for r in rows))

    def test_normal_body_is_not_misclassified_as_zero(self):
        rows = candle_quality(self.candles(False), "Synthetic")
        self.assertTrue(all(r["identical_open_close_pct"] == 0
                            for r in rows))
        self.assertTrue(all(r["median_body_to_atr"] > .1
                            for r in rows))

    def test_does_not_mutate_data(self):
        candles = self.candles(True)
        before = candles.copy(deep=True)
        candle_quality(candles, "Synthetic")
        pd.testing.assert_frame_equal(candles, before)

    def test_empty_is_no_report(self):
        self.assertEqual(candle_quality(self.candles().iloc[:0], "X"), [])


if __name__ == "__main__":
    unittest.main()
