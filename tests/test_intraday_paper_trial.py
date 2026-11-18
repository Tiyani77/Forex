"""Rapid intraday trial: never record already-known outcomes as forward."""
import unittest
import pandas as pd

from intraday_paper_trial import trial_eligibility
from signal_models import FAST_PROBE_VERSION


def candles(count=100, start="2026-11-18T10:00:00Z", minutes=5):
    idx = pd.date_range(start, periods=count, freq=f"{minutes}min", tz="UTC")
    close = pd.Series(
        [1.1 + i * .00012 + ((i % 8) - 3) * .00002 for i in range(count)],
        index=idx,
    )
    return pd.DataFrame({
        "Open": close.shift(1).fillna(close.iloc[0]),
        "High": close + .0003,
        "Low": close - .0003,
        "Close": close,
    }, index=idx)


class IntradayPaperTrialTests(unittest.TestCase):
    def test_fresh_last_completed_bar(self):
        data = candles()
        # Candidate = penultimate 10:00 +98*5min = 18:10,
        # closes at 18:15, first future candle closes at 18:20.
        candidate_open = data.index[-2]
        decision, reason = trial_eligibility(
            data, "5m", now=candidate_open + pd.Timedelta(minutes=6)
        )
        self.assertIsNotNone(decision)
        self.assertEqual(reason, "eligible_before_first_future_close")
        self.assertEqual(
            pd.to_datetime(decision["signal_bar_at"], utc=True),
            candidate_open,
        )
        self.assertEqual(decision["model_version"], FAST_PROBE_VERSION)

    def test_reject_delayed_feed(self):
        data = candles()
        candidate = data.index[-2]
        decision, reason = trial_eligibility(
            data, "5m", now=candidate + pd.Timedelta(minutes=15)
        )
        self.assertIsNone(decision)
        self.assertEqual(reason, "stale_provider_bar_skip")

    def test_never_uses_unclosed_latest_candle(self):
        data = candles()
        candidate = data.index[-2]
        decision, reason = trial_eligibility(
            data, "5m", now=candidate + pd.Timedelta(minutes=2)
        )
        self.assertIsNotNone(decision)
        self.assertEqual(
            pd.to_datetime(decision["signal_bar_at"], utc=True),
            data.index[-3],
        )

    def test_accepts_newest_bar_when_already_completed(self):
        data = candles()
        last = data.index[-1]
        decision, reason = trial_eligibility(
            data, "5m", now=last + pd.Timedelta(minutes=6)
        )
        self.assertIsNotNone(decision)
        self.assertEqual(reason, "eligible_before_first_future_close")
        self.assertEqual(
            pd.to_datetime(decision["signal_bar_at"], utc=True), last
        )

    def test_reject_no_completed_candles(self):
        data = candles()
        decision, reason = trial_eligibility(
            data, "5m", now=data.index[0] + pd.Timedelta(minutes=2)
        )
        self.assertIsNone(decision)
        self.assertEqual(reason, "signal_bar_not_closed")

    def test_fresh_15m(self):
        data = candles(minutes=15)
        candidate = data.index[-2]
        decision, reason = trial_eligibility(
            data, "15m", now=candidate + pd.Timedelta(minutes=16)
        )
        self.assertIsNotNone(decision)
        self.assertEqual(reason, "eligible_before_first_future_close")

    def test_requires_lookback(self):
        data = candles(count=30)
        decision, reason = trial_eligibility(
            data, "5m", now=data.index[-2] + pd.Timedelta(minutes=6)
        )
        self.assertIsNone(decision)
        self.assertEqual(reason, "insufficient_completed_bars")

    def test_reject_unsupported_timeframe(self):
        with self.assertRaises(ValueError):
            trial_eligibility(candles(), "1d")


if __name__ == "__main__":
    unittest.main()
