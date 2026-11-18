"""V8.5 regression checks: cannot declare an unvalidated signal profitable."""
import unittest
from signal_readiness import model_readiness, paper_risk_budget


class SignalReadinessTests(unittest.TestCase):
    def test_no_evidence_fails_closed(self):
        r = model_readiness(None)
        self.assertFalse(r["real_money_ready"])
        self.assertEqual(r["status"], "NO_FORWARD_EVIDENCE")

    def test_small_sample_fails_closed(self):
        r = model_readiness({
            "evaluated_directional": 40,
            "markets_evaluated": 15,
            "invalid_evaluated": 0,
        })
        self.assertEqual(r["status"], "INSUFFICIENT_FORWARD_SAMPLE")
        self.assertFalse(r["real_money_ready"])

    def test_large_sample_does_not_automatically_approve(self):
        r = model_readiness({
            "evaluated_directional": 2000,
            "markets_evaluated": 15,
            "invalid_evaluated": 0,
        })
        self.assertEqual(r["status"], "MANUAL_REVIEW_REQUIRED")
        self.assertFalse(r["real_money_ready"])

    def test_invalid_record_blocks_review(self):
        r = model_readiness({
            "evaluated_directional": 1000,
            "markets_evaluated": 15,
            "invalid_evaluated": 1,
        })
        self.assertEqual(r["status"], "DATA_QUALITY_REVIEW")

    def test_paper_budget_example(self):
        r = paper_risk_budget(1000, .5, 1)
        self.assertTrue(r["paper_only"])
        self.assertEqual(r["risk_budget_usd"], 5.)
        self.assertEqual(r["max_paper_units"], 5)

    def test_budget_rejects_over_half_percent(self):
        with self.assertRaises(ValueError):
            paper_risk_budget(1000, 1., 1)

    def test_budget_rejects_invalid_inputs(self):
        for args in ((0, .5, 1), (100, .5, 0),
                     (100, .5, float("nan"))):
            with self.assertRaises(ValueError):
                paper_risk_budget(*args)


if __name__ == "__main__":
    unittest.main()
