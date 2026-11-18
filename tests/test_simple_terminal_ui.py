"""Check that the streamlined terminal preserves research functionality."""
import unittest
from pathlib import Path

APP = (Path(__file__).resolve().parent.parent / "app.py").read_text(
    encoding="utf-8"
)


class SimpleTerminalUiTests(unittest.TestCase):
    def test_sidebar_shows_only_core_inputs_by_default(self):
        self.assertIn('st.sidebar.selectbox(\n    "Market category"', APP)
        self.assertIn('st.sidebar.selectbox(\n    "Search instrument"', APP)
        self.assertIn('st.sidebar.selectbox(\n    "Timeframe"', APP)
        self.assertIn('st.sidebar.selectbox(\n    "Signal strategy"', APP)
        self.assertIn('with st.sidebar.expander("⚙ More options"', APP)

    def test_signal_is_still_shared_engine_output(self):
        self.assertIn('signal = terminal_decision["signal"]', APP)
        self.assertIn('f\'<div class="signal-orb {color_class}">{signal}</div>\'', APP)
        self.assertIn('latest_signal(\n    raw, MODEL_VERSION', APP)

    def test_advanced_research_is_still_available(self):
        self.assertIn('with st.expander("🔎 See indicators & signal details"', APP)
        self.assertIn('with st.expander("📊 More market research"', APP)
        self.assertIn('with st.expander("🛡️ Safety & paper-trading tools"', APP)
        self.assertIn('st.markdown("### 📈 Price chart")', APP)

    def test_evidence_and_history_not_removed(self):
        self.assertIn('V8.6 · Forward return & cost dashboard', APP)
        self.assertIn('list_predictions_paginated(', APP)
        self.assertIn('NOT VALIDATED', APP)

    def test_sidebar_still_allows_custom_ticker_and_backtest_horizon(self):
        self.assertIn('custom = st.text_input(', APP)
        self.assertIn('horizon = st.slider(', APP)
        self.assertIn('symbol = (\n    custom.strip().upper()', APP)


if __name__ == "__main__":
    unittest.main()
