"""V6.0 offline forward-evidence checks: denominator and evidence gate."""
import unittest

from forward_evidence import wilson_interval, summarise_forward
from signal_models import MODEL_LABELS


def record(model, signal="BUY", status="evaluated", correct=True,
           ticker="EURUSD=X", ident="x", recorded_at="2026-01-02T06:00:00Z",
           outcome_bar_at="2026-01-08T00:00:00Z"):
    return {
        "id": ident, "model_version": model,
        "ticker": ticker, "signal": signal, "timeframe": "1d",
        "status": status, "correct": correct,
        "recorded_at": recorded_at,
        "outcome_bar_at": outcome_bar_at,
    }


class ForwardEvidenceTests(unittest.TestCase):
    def test_zero_sample_interval_is_unavailable(self):
        self.assertEqual(wilson_interval(0, 0), (None, None))

    def test_wilson_interval_has_valid_order(self):
        lower, upper = wilson_interval(2, 10)
        self.assertTrue(0 <= lower <= .2 <= upper <= 1)

    def test_wait_is_excluded(self):
        rows = [
            record("m", ident="1"),
            record("m", signal="WAIT", correct=None, ident="2"),
            record("m", signal="SELL", status="pending",
                   correct=None, ident="3"),
            record("m", signal="BUY", status="unavailable",
                   correct=None, ident="4"),
        ]
        row = summarise_forward(rows).set_index("model_version").loc["m"]
        self.assertEqual(row.evaluated_directional, 1)
        self.assertEqual(row.correct_directional, 1)
        self.assertEqual(row.wait_total, 1)
        self.assertEqual(row.pending_directional, 1)
        self.assertEqual(row.unavailable_directional, 1)
        self.assertEqual(row.evidence_status, "INSUFFICIENT_FORWARD_EVIDENCE")

    def test_late_outcome_not_counted(self):
        row = summarise_forward([
            record("m", ident="1", recorded_at="2026-01-09T00:00:00Z")
        ]).set_index("model_version").loc["m"]
        self.assertEqual(row.evaluated_directional, 0)
        self.assertEqual(row.invalid_evaluated, 1)

    def test_recorded_during_outcome_candle_before_close(self):
        # Allowed for a 1-bar horizon when it was first recorded
        # while the next daily outcome candle was still forming.
        row = summarise_forward([
            record("m", ident="1",
                   recorded_at="2026-01-08T06:00:00Z",
                   outcome_bar_at="2026-01-08T00:00:00Z")
        ]).set_index("model_version").loc["m"]
        self.assertEqual(row.evaluated_directional, 1)

    def test_duplicate_id_not_double_counted(self):
        item = record("m", ident="same")
        row = summarise_forward([item, item]).set_index("model_version").loc["m"]
        self.assertEqual(row.recorded_total, 1)

    def test_multiple_models_separate(self):
        rows = [record("a", ident="1"), record("b", ident="2", correct=False)]
        result = summarise_forward(rows)
        self.assertEqual(len(result), len(MODEL_LABELS) + 2)
        self.assertEqual(int(result.correct_directional.sum()), 1)

    def test_all_registered_models_shown_without_records(self):
        result = summarise_forward([])
        self.assertEqual(set(result.model_version), set(MODEL_LABELS))
        self.assertEqual(set(result.evidence_status), {"NO_SAVED_SIGNALS"})
        self.assertTrue((result.recorded_total == 0).all())

    def test_sufficient_sample_is_review_not_validated(self):
        rows = [
            record("m", ident=str(i), ticker=f"PAIR{i%10}",
                   correct=(i % 3 != 0))
            for i in range(110)
        ]
        row = summarise_forward(rows).set_index("model_version").loc["m"]
        self.assertEqual(row.evidence_status, "REVIEW_REQUIRED_CORRELATED_SAMPLE")


if __name__ == "__main__":
    unittest.main()
