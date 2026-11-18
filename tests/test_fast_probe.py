"""New frequent directional paper probe: deliberately no profitability claims."""
import unittest
import numpy as np
import pandas as pd
from signal_models import FAST_PROBE_VERSION, fast_probe_diagnostics
from forecast_engine import latest_signal, model_flags


def bars(n=125):
    idx = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    close = pd.Series(np.linspace(1.02, 1.08, n), index=idx)
    return pd.DataFrame({
        "Open": close, "High": close + .001,
        "Low": close - .001, "Close": close,
    }, index=idx)


class FastProbeTests(unittest.TestCase):
    def test_strong_uptrend_generates_buy(self):
        df = bars()
        buy, sell = model_flags(df, FAST_PROBE_VERSION)
        self.assertTrue(buy.iloc[-1])
        self.assertFalse(sell.iloc[-1])
        decision = latest_signal(df, FAST_PROBE_VERSION, timeframe="5m")
        self.assertEqual(decision["signal"], "BUY")

    def test_strong_downtrend_generates_sell(self):
        df = bars()
        df["Close"] = pd.Series(np.linspace(1.08, 1.02, len(df)), index=df.index)
        buy, sell = model_flags(df, FAST_PROBE_VERSION)
        self.assertTrue(sell.iloc[-1])
        self.assertFalse(buy.iloc[-1])

    def test_flat_market_stays_wait(self):
        df = bars()
        df["Close"] = 1.01
        buy, sell = model_flags(df, FAST_PROBE_VERSION)
        self.assertFalse(buy.any())
        self.assertFalse(sell.any())

    def test_ignores_open_high_low(self):
        df = bars()
        x, y = model_flags(df, FAST_PROBE_VERSION)
        altered = df.copy()
        altered["Open"] *= 0.5
        altered["High"] *= 3
        altered["Low"] *= .1
        x2, y2 = model_flags(altered, FAST_PROBE_VERSION)
        self.assertTrue(x.equals(x2))
        self.assertTrue(y.equals(y2))

    def test_causal_against_future_append(self):
        df = bars()
        x, y = model_flags(df, FAST_PROBE_VERSION)
        for n in (42, 70, 100):
            xa, ya = model_flags(df.iloc[:n], FAST_PROBE_VERSION)
            self.assertTrue(x.iloc[:n].equals(xa))
            self.assertTrue(y.iloc[:n].equals(ya))

    def test_exclusive_and_warmup(self):
        df = bars()
        x, y, outlook = fast_probe_diagnostics(df)
        self.assertFalse((x & y).any())
        self.assertFalse(x.iloc[:30].any())
        self.assertFalse(y.iloc[:30].any())
        self.assertEqual(outlook.iloc[-1], "BULLISH")

    def test_empty_safe(self):
        df = bars().iloc[:0]
        x, y = model_flags(df, FAST_PROBE_VERSION)
        self.assertTrue(x.empty and y.empty)


if __name__ == "__main__":
    unittest.main()
