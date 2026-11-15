"""V5.5 conservative release audit tests (offline, synthetic data)."""
import unittest

import pandas as pd

from research_release_audit import audit_research
from signal_models import MODEL_LABELS


def fixture(trades=80, mean=0.03):
    rows = []
    for model in MODEL_LABELS:
        for market in ("A", "B", "C", "D", "E", "F",
                       "G", "H", "I", "J", "K", "L"):
            for horizon in (2, 5, 10):
                for cost in (0.0, 4.0, 10.0):
                    rows.append({
                        "model": model, "market": market,
                        "horizon": horizon, "cost_bps": cost,
                        "trades": trades // 12,
                        "net_win_pct": 51.0,
                        "gross_direction_correct_pct": 53.0,
                        "mean_net_pct": mean - cost / 100.0,
                    })
    return pd.DataFrame(rows)


class AuditTests(unittest.TestCase):
    def test_all_models_explicitly_unvalidated(self):
        report = audit_research(fixture(trades=120, mean=0.2))
        self.assertEqual(len(report), len(MODEL_LABELS))
        self.assertEqual(set(report.production_status), {"NOT_VALIDATED"})

    def test_sparse_model_not_promoted_by_huge_return(self):
        report = audit_research(fixture(trades=12, mean=50))
        self.assertEqual(
            set(report.research_diagnosis), {"INSUFFICIENT_SAMPLE"}
        )

    def test_negative_model_classified(self):
        report = audit_research(fixture(trades=120, mean=-0.2))
        self.assertEqual(
            set(report.research_diagnosis),
            {"NEGATIVE_HISTORICAL_MEDIAN"}
        )

    def test_duplicate_rows_rejected(self):
        sample = fixture()
        with self.assertRaises(ValueError):
            audit_research(pd.concat([sample, sample.iloc[:1]]))

    def test_missing_scenario_rejected(self):
        sample = fixture()
        sample = sample.drop(sample.index[0])
        with self.assertRaises(ValueError):
            audit_research(sample)

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            audit_research(pd.DataFrame({"model": list(MODEL_LABELS)}))


if __name__ == "__main__":
    unittest.main()
