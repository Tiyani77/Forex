"""Regression check: fast trial is visible, remains research-only."""
import unittest
from pathlib import Path

source = (Path(__file__).resolve().parent.parent / "app.py").read_text(
    encoding="utf-8"
)


class IntradayTrialUiTests(unittest.TestCase):
    def test_quick_progress_displayed(self):
        self.assertIn("#### Quick intraday paper trial", source)
        self.assertIn("Saved 5m/15m trials", source)
        self.assertIn("Awaiting future candles", source)

    def test_only_separate_correct_model_and_timeframes(self):
        self.assertIn('["5m", "15m"]', source)
        self.assertIn('"model_version"].eq(CLOSE_CONFIRM_VERSION)', source)
        self.assertIn('["BUY", "SELL"]', source)

    def test_no_claim_of_live_broker_profit(self):
        self.assertIn("not executable", source.lower())
        self.assertIn("NOT VALIDATED", source)


if __name__ == "__main__":
    unittest.main()
