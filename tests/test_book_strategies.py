"""V5 research candidate invariants. No web, broker, or Supabase access."""
import unittest
import numpy as np
import pandas as pd
from signal_models import (
    CHANNEL_VERSION, SUPPLY_DEMAND_VERSION,
    STRUCTURE_VERSION, LIQUIDITY_SWEEP_VERSION, CONFLUENCE_VERSION,
    MODEL_LABELS,
    apply_research_model,
)


class BookStrategyTests(unittest.TestCase):
    def setUp(self):
        n = 180
        x = np.arange(n)
        close = 100 + 0.045 * x + 1.4 * np.sin(x / 7)
        self.candles = pd.DataFrame({
            "Open": close - 0.13 * np.sin(x / 3),
            "High": close + 0.7,
            "Low": close - 0.7,
            "Close": close,
        }, index=pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"))

    def test_candidates_are_registered(self):
        self.assertIn(CHANNEL_VERSION, MODEL_LABELS)
        self.assertIn(SUPPLY_DEMAND_VERSION, MODEL_LABELS)
        self.assertIn(STRUCTURE_VERSION, MODEL_LABELS)
        self.assertIn(LIQUIDITY_SWEEP_VERSION, MODEL_LABELS)
        self.assertIn(CONFLUENCE_VERSION, MODEL_LABELS)

    def test_boolean_aligned_no_conflicts(self):
        for model in (CHANNEL_VERSION, SUPPLY_DEMAND_VERSION, STRUCTURE_VERSION,
                      LIQUIDITY_SWEEP_VERSION):
            buy, sell = apply_research_model(self.candles, model)
            self.assertTrue(buy.index.equals(self.candles.index))
            self.assertTrue(sell.index.equals(self.candles.index))
            self.assertTrue(pd.api.types.is_bool_dtype(buy))
            self.assertTrue(pd.api.types.is_bool_dtype(sell))
            self.assertFalse((buy & sell).any())
            self.assertFalse(buy.iloc[:60].any())
            self.assertFalse(sell.iloc[:60].any())

    def test_no_future_lookahead(self):
        for model in (CHANNEL_VERSION, SUPPLY_DEMAND_VERSION,
                      STRUCTURE_VERSION, LIQUIDITY_SWEEP_VERSION,
                      CONFLUENCE_VERSION):
            full_buy, full_sell = apply_research_model(self.candles, model)
            for cutoff in (65, 100, 140):
                prefix_buy, prefix_sell = apply_research_model(
                    self.candles.iloc[:cutoff], model
                )
                self.assertTrue(
                    full_buy.iloc[:cutoff].equals(prefix_buy),
                    f"Future candle changed BUY signals: {model}"
                )
                self.assertTrue(
                    full_sell.iloc[:cutoff].equals(prefix_sell),
                    f"Future candle changed SELL signals: {model}"
                )

    def test_empty_market_data_is_not_a_signal(self):
        empty = self.candles.iloc[:0]
        for model in (CHANNEL_VERSION, SUPPLY_DEMAND_VERSION,
                      STRUCTURE_VERSION, LIQUIDITY_SWEEP_VERSION,
                      CONFLUENCE_VERSION):
            buy, sell = apply_research_model(empty, model)
            self.assertEqual(len(buy), 0)
            self.assertEqual(len(sell), 0)


if __name__ == "__main__":
    unittest.main()
