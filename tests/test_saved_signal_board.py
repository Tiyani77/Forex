"""UI-safe saved forward signal filtering tests, without Supabase access."""
import unittest
import pandas as pd
from saved_signal_board import latest_saved_signals


def record(i="a", *, signal="BUY", status="pending", recorded="2026-11-18T17:49:00Z", bar="2026-11-18T17:30:00Z", model="close-momentum-probe-v1", tf="15m"):
    return {
        "id": i, "instrument": "EUR/USD", "ticker": "EURUSD=X",
        "timeframe": tf, "signal": signal, "status": status,
        "model_version": model, "recorded_at": recorded,
        "signal_bar_at": bar, "reference_close": 1.097695,
    }


class SavedSignalBoardTests(unittest.TestCase):
    NOW = "2026-11-18T18:00:00Z"

    def test_real_saved_buy_and_sell_are_displayed(self):
        rows = latest_saved_signals([
            record(), record("b", signal="SELL")
        ], now=self.NOW, model_version="close-momentum-probe-v1")
        self.assertEqual([r["signal"] for r in rows], ["BUY", "SELL"])
        self.assertEqual(rows[0]["age_minutes"], 11)

    def test_wait_is_not_a_saved_trade(self):
        self.assertEqual(latest_saved_signals([
            record(signal="WAIT")
        ], now=self.NOW), [])

    def test_missing_dates_and_future_recordings_rejected(self):
        self.assertEqual(latest_saved_signals([
            record(recorded="missing"), record("b", recorded="2026-11-19T01:00:00Z"),
            record("c", bar="2026-11-18T17:59:00Z")
        ], now=self.NOW), [])

    def test_separate_models_and_daily_excluded(self):
        self.assertEqual(latest_saved_signals([
            record(), record("x", model="other"),
            record("d", tf="1d")
        ], now=self.NOW, model_version="close-momentum-probe-v1")[0]["id"], "a")
        self.assertEqual(len(latest_saved_signals([
            record(), record("x", model="other"),
            record("d", tf="1d")
        ], now=self.NOW, model_version="close-momentum-probe-v1")), 1)

    def test_duplicate_forecast_ids_not_double_counted(self):
        rows = latest_saved_signals([
            record(), record(), record("b", signal="SELL")
        ], now=self.NOW)
        self.assertEqual(len(rows), 2)

    def test_newest_first_and_limit(self):
        rows = latest_saved_signals([
            record("first", recorded="2026-11-18T17:35:00Z"),
            record("second", recorded="2026-11-18T17:59:00Z"),
        ], now=self.NOW, limit=1)
        self.assertEqual(rows[0]["id"], "second")

    def test_missing_supabase_records_safe(self):
        self.assertEqual(latest_saved_signals([]), [])
        self.assertEqual(latest_saved_signals(None), [])

    def test_evaluated_is_still_displayed_as_past_forecast(self):
        rows = latest_saved_signals([
            record(status="evaluated")
        ], now=self.NOW)
        self.assertEqual(rows[0]["status"], "evaluated")


if __name__ == "__main__":
    unittest.main()
