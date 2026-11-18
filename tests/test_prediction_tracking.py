"""V6.3 offline, non-mutating forecast history health tests."""
import unittest
from unittest.mock import patch

import pandas as pd

from prediction_tracking import tracking_overview


def record(status="pending", recorded_at="2026-11-15T08:00:00Z",
           signal="BUY", ident="x", outcome_bar_at=None):
    return {
        "id": ident, "ticker": "EURUSD=X",
        "instrument": "EUR/USD", "timeframe": "1d",
        "model_version": "v1", "signal": signal, "status": status,
        "recorded_at": recorded_at,
        "signal_bar_at": "2026-11-14T00:00:00Z",
        "horizon_bars": 5, "outcome_bar_at": outcome_bar_at,
        "correct": None,
    }


class TrackingOverviewTests(unittest.TestCase):
    def test_recent_pending_is_waiting_not_error(self):
        raw = pd.DataFrame([record()])
        original = raw.copy(deep=True)
        rows, counts = tracking_overview(raw, now="2026-11-18T00:00:00Z")
        self.assertEqual(counts["pending"], 1)
        self.assertEqual(counts["aged_pending"], 0)
        self.assertEqual(rows.iloc[0]["Data quality"], "OK")
        self.assertIn("Awaiting completed", rows.iloc[0]["Operational state"])
        pd.testing.assert_frame_equal(raw, original)

    def test_old_daily_is_review_not_failure(self):
        rows, counts = tracking_overview(
            pd.DataFrame([record(recorded_at="2026-10-01T00:00:00Z")]),
            now="2026-11-18T00:00:00Z")
        self.assertEqual(counts["aged_pending"], 1)
        self.assertIn("Review pending age", rows.iloc[0]["Operational state"])

    def test_evaluated_without_outcome_timestamp_flagged(self):
        rows, counts = tracking_overview(
            pd.DataFrame([record(status="evaluated")]),
            now="2026-11-18T00:00:00Z")
        self.assertEqual(counts["evaluated"], 1)
        self.assertEqual(counts["missing_fields"], 1)
        self.assertEqual(rows.iloc[0]["Data quality"], "Missing or invalid fields")

    def test_wait_does_not_count_as_directional(self):
        rows, counts = tracking_overview(
            pd.DataFrame([record(signal="WAIT")]),
            now="2026-11-18T00:00:00Z")
        self.assertEqual(counts["pending"], 0)
        self.assertEqual(counts["aged_pending"], 0)

    def test_empty_history(self):
        rows, counts = tracking_overview(pd.DataFrame(),
                                         now="2026-11-18T00:00:00Z")
        self.assertTrue(rows.empty)
        self.assertEqual(counts["missing_fields"], 0)

    def test_invalid_horizon(self):
        sample = record()
        sample["horizon_bars"] = -2
        rows, counts = tracking_overview(
            pd.DataFrame([sample]), now="2026-11-18T00:00:00Z")
        self.assertEqual(counts["missing_fields"], 1)


class PaginatedHistoryTests(unittest.TestCase):
    def test_pages_and_end(self):
        # prediction_store imports Streamlit; installed by collector workflow.
        from prediction_store import list_predictions_paginated
        def fake_call(_method, _path, *, params):
            off = int(params["offset"])
            size = int(params["limit"])
            return [{"id": str(i)} for i in range(off, min(off + size, 5))]
        with patch("prediction_store._call", side_effect=fake_call):
            rows, truncated = list_predictions_paginated(
                page_size=2, max_records=12)
        self.assertEqual(len(rows), 5)
        self.assertFalse(truncated)

    def test_cap_is_visible(self):
        from prediction_store import list_predictions_paginated
        def fake_call(_method, _path, *, params):
            off = int(params["offset"])
            size = int(params["limit"])
            return [{"id": str(i)} for i in range(off, off + size)]
        with patch("prediction_store._call", side_effect=fake_call):
            rows, truncated = list_predictions_paginated(
                page_size=2, max_records=4)
        self.assertEqual(len(rows), 4)
        self.assertTrue(truncated)


if __name__ == "__main__":
    unittest.main()
