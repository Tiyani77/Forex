"""UI contract for the terminal visual redesign; no strategy-rule changes."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TerminalVisualContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "app.py").read_text(encoding="utf-8")

    def test_signal_orb_is_driven_by_real_model_signal(self):
        self.assertIn('class="signal-orb {color_class}"', self.source)
        self.assertIn('f\'{signal}</div>\'', self.source)
        self.assertIn("signal-hero-desc", self.source)

    def test_market_context_uses_real_selection(self):
        self.assertIn('f\'<span class="fi-chip">◉ {label}</span>\'', self.source)
        self.assertIn('f\'<span class="fi-chip">◷ {tf} timeframe</span>\'', self.source)

    def test_research_only_cautions_remain(self):
        self.assertIn("NOT VALIDATED", self.source)
        self.assertIn("All signals remain experimental and unvalidated.", self.source)
        self.assertIn("No calibrated confidence percentage yet.", self.source)

    def test_forward_dashboard_remains(self):
        self.assertIn("V8.6 · Forward return & cost dashboard", self.source)
        self.assertIn("evaluated_reference_returns(", self.source)

    def test_no_fake_market_confidence_or_auto_trade(self):
        self.assertNotIn("90.1%", self.source)
        self.assertNotIn("Unlimited trades", self.source)


if __name__ == "__main__":
    unittest.main()
