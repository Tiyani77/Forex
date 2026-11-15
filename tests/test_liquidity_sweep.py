"""Mechanical wick sweep and reclaim test cases; no live data."""
import unittest
import pandas as pd
from signal_models import LIQUIDITY_SWEEP_VERSION, apply_research_model


class LiquiditySweepTests(unittest.TestCase):
    def candles(self):
        frame = pd.DataFrame({
            "Open": [100.0] * 82,
            "High": [100.5] * 82,
            "Low": [99.5] * 82,
            "Close": [100.0] * 82,
        }, index=pd.date_range("2024-01-01", periods=82, freq="D", tz="UTC"))
        return frame

    def test_bullish_sweep_reclaim(self):
        frame = self.candles()
        frame.loc[frame.index[80], ["Open", "High", "Low", "Close"]] = [
            100.0, 101.0, 98.0, 100.7
        ]
        buys, sells = apply_research_model(frame, LIQUIDITY_SWEEP_VERSION)
        self.assertTrue(bool(buys.iloc[80]))
        self.assertFalse(bool(sells.iloc[80]))

    def test_bearish_sweep_reclaim(self):
        frame = self.candles()
        frame.loc[frame.index[80], ["Open", "High", "Low", "Close"]] = [
            100.0, 102.0, 99.0, 99.3
        ]
        buys, sells = apply_research_model(frame, LIQUIDITY_SWEEP_VERSION)
        self.assertTrue(bool(sells.iloc[80]))
        self.assertFalse(bool(buys.iloc[80]))

    def test_no_reclaim_means_no_signal(self):
        frame = self.candles()
        frame.loc[frame.index[80], ["Open", "High", "Low", "Close"]] = [
            100.0, 100.4, 98.0, 98.5
        ]
        buys, sells = apply_research_model(frame, LIQUIDITY_SWEEP_VERSION)
        self.assertFalse(bool(buys.iloc[80]))
        self.assertFalse(bool(sells.iloc[80]))

    def test_causal_prefix_invariance(self):
        frame = self.candles()
        frame.loc[frame.index[80], ["Open", "High", "Low", "Close"]] = [
            100.0, 101.0, 98.0, 100.7
        ]
        full_buy, full_sell = apply_research_model(frame, LIQUIDITY_SWEEP_VERSION)
        for n in (60, 75, 81):
            part_buy, part_sell = apply_research_model(
                frame.iloc[:n], LIQUIDITY_SWEEP_VERSION
            )
            self.assertTrue(full_buy.iloc[:n].equals(part_buy))
            self.assertTrue(full_sell.iloc[:n].equals(part_sell))


if __name__ == "__main__":
    unittest.main()
