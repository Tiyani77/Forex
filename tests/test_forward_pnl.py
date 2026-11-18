"""V8.6 forward reference-return accounting, no fake executed trades."""
import unittest
import pandas as pd
from forward_pnl import (evaluated_reference_returns,
                         reference_summary, reference_scenarios)


def record(ident="a", model="model-a", status="evaluated",
           signed_return=1.0, signal="BUY", correct=True,
           recorded="2026-01-02T06:00:00Z", outcome="2026-01-09T00:00:00Z",
           ticker="EURUSD=X", anchor="2026-01-01T00:00:00Z"):
    return {
        "id": ident, "model_version": model, "ticker": ticker,
        "instrument": "EUR/USD", "timeframe": "1d", "signal": signal,
        "status": status, "correct": correct,
        "signal_bar_at": anchor, "recorded_at": recorded,
        "outcome_bar_at": outcome, "horizon_bars": 5,
        "directional_return_pct": signed_return,
    }


class ForwardPnlTests(unittest.TestCase):
    def test_pending_wait_and_unavailable_excluded(self):
        source = [
            record("a"), record("b", status="pending", signed_return=None),
            record("c", status="unavailable"),
            record("d", signal="WAIT", correct=None),
        ]
        rows = evaluated_reference_returns(source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.iloc[0]["id"], "a")

    def test_cost_is_basis_points_and_label_is_reference(self):
        rows = evaluated_reference_returns([record()], cost_bps=10)
        self.assertAlmostEqual(rows.iloc[0]["directional_return_pct"], 1.0)
        self.assertAlmostEqual(
            rows.iloc[0]["cost_adjusted_reference_pct"], .9
        )
        self.assertNotIn("profit", " ".join(rows.columns).lower())

    def test_same_forecast_deduplicated(self):
        one = record("one")
        two = record("two")
        rows = evaluated_reference_returns([one, one, two])
        self.assertEqual(len(rows), 1)

    def test_unique_model_versions_do_not_merge(self):
        rows = evaluated_reference_returns([
            record("one", model="alpha"),
            record("two", model="beta"),
        ])
        self.assertEqual(len(rows), 2)
        board = reference_summary(rows, ["alpha", "beta", "gamma"])
        self.assertEqual(list(board.evaluated), [1, 1, 0])
        self.assertTrue(pd.isna(board.iloc[2]["mean_cost_adjusted_pct"]))

    def test_invalid_timestamps_not_forward_evidence(self):
        rows = evaluated_reference_returns([
            record("late", recorded="2026-01-11T00:00:00Z"),
            record("same", outcome="2026-01-01T00:00:00Z"),
            record("good"),
        ])
        self.assertEqual(rows["id"].tolist(), ["good"])

    def test_invalid_return_and_direction_verdict_rejected(self):
        rows = evaluated_reference_returns([
            record("bad", signed_return=float("inf")),
            record("contradiction", signed_return=-1, correct=True),
            record("good", signed_return=-1, correct=False,
                   signal="SELL", ticker="GBPUSD=X"),
        ])
        self.assertEqual(rows.id.tolist(), ["good"])

    def test_zero_and_negative_return_are_nonwinning(self):
        rows = evaluated_reference_returns([
            record("zero", signed_return=0, correct=False),
            record("negative", signed_return=-.4, correct=False,
                   ticker="GBPUSD=X")
        ])
        self.assertEqual(len(rows), 2)
        summary = reference_summary(rows)
        self.assertEqual(summary.iloc[0].cost_adjusted_positive_pct, 0)

    def test_higher_cost_cannot_improve_result(self):
        source = [
            record("one", signed_return=1.2),
            record("two", signed_return=-.8, correct=False,
                   ticker="GBPUSD=X"),
        ]
        scenarios = reference_scenarios(source, (0, 4, 10))
        self.assertEqual(len(scenarios), 3)
        self.assertEqual(list(scenarios.evaluated), [2, 2, 2])
        means = scenarios.mean_cost_adjusted_pct.tolist()
        self.assertGreaterEqual(means[0], means[1])
        self.assertGreaterEqual(means[1], means[2])

    def test_empty_history_reports_no_performance(self):
        rows = evaluated_reference_returns([])
        board = reference_summary(rows, ["alpha"])
        self.assertEqual(board.iloc[0]["evaluated"], 0)
        self.assertTrue(pd.isna(board.iloc[0]["mean_cost_adjusted_pct"]))
        self.assertTrue(reference_scenarios([]).empty)

    def test_does_not_modify_records(self):
        original = [record()]
        snapshot = dict(original[0])
        evaluated_reference_returns(original)
        self.assertEqual(original[0], snapshot)

    def test_invalid_costs_rejected(self):
        for cost in (-1, 1001, float("nan")):
            with self.assertRaises(ValueError):
                evaluated_reference_returns([record()], cost)


if __name__ == "__main__":
    unittest.main()
