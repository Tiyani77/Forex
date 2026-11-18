"""V8.4: close-only strategy invariants, timing, and data integrity."""
import unittest
import numpy as np
import pandas as pd
from signal_models import CLOSE_CONFIRM_VERSION, close_trend_diagnostics
from forecast_engine import model_flags
from research_close_signals import close_only_trade_rows, market_report


class CloseSignalsTests(unittest.TestCase):
    def setUp(self):
        n = 220
        x = np.arange(n)
        close = 100 + .065*x + 1.4 * np.sin(x / 5)
        self.candles = pd.DataFrame({
            "Open": close.copy(), "High": close + .6,
            "Low": close - .6, "Close": close
        }, index=pd.date_range("2024-01-01", periods=n, tz="UTC"))

    def test_data_robustness_when_all_opens_equal_close(self):
        buy, sell, bias = close_trend_diagnostics(self.candles)
        self.assertFalse((buy & sell).any())
        self.assertFalse(buy.iloc[:65].any())
        self.assertFalse(sell.iloc[:65].any())
        self.assertEqual(len(bias), len(self.candles))
        self.assertTrue(set(bias).issubset({"BULLISH", "BEARISH", "NEUTRAL"}))

    def test_model_unaffected_by_open_high_low_changes(self):
        a, b = model_flags(self.candles, CLOSE_CONFIRM_VERSION)
        altered = self.candles.copy()
        altered["Open"] = altered["Close"] * 1.3
        altered["High"] = altered["Close"] * 2
        altered["Low"] = altered["Close"] * .5
        x, y = model_flags(altered, CLOSE_CONFIRM_VERSION)
        pd.testing.assert_series_equal(a, x)
        pd.testing.assert_series_equal(b, y)

    def test_no_future_lookahead(self):
        full = close_trend_diagnostics(self.candles)
        for n in (65, 100, 160, 210):
            earlier = close_trend_diagnostics(self.candles.iloc[:n])
            for whole, part in zip(full, earlier):
                pd.testing.assert_series_equal(whole.iloc[:n], part)

    def test_empty_data(self):
        b, s, bias = close_trend_diagnostics(self.candles.iloc[:0])
        self.assertEqual((len(b), len(s), len(bias)), (0, 0, 0))

    def test_next_close_entry_is_after_signal(self):
        rows = close_only_trade_rows(
            self.candles, "ema20-ema50-close-bias-benchmark", horizon=5
        )
        self.assertGreater(len(rows), 0)
        self.assertTrue((rows.entry_bar == rows.signal_bar + 1).all())
        self.assertTrue((rows.exit_bar == rows.entry_bar + 5).all())
        self.assertTrue((rows.signal_bar.diff().dropna() > 5).all())

    def test_higher_cost_reduces_same_trades_returns(self):
        zero = close_only_trade_rows(
            self.candles, "ema20-ema50-close-bias-benchmark", cost_bps=0
        )
        ten = close_only_trade_rows(
            self.candles, "ema20-ema50-close-bias-benchmark", cost_bps=10
        )
        self.assertEqual(len(zero), len(ten))
        np.testing.assert_allclose(
            zero.net_pct.to_numpy() - ten.net_pct.to_numpy(), .1
        )

    def test_report_respects_split(self):
        report = market_report(self.candles, "test")
        self.assertEqual(len(report), 4)
        self.assertEqual(
            {r["window"] for r in report}, {"Development", "Later period"}
        )


if __name__ == "__main__":
    unittest.main()
