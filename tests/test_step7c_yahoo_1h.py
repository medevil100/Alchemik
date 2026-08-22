"""Test-first RED — Yahoo interval=1h i rozpoznanie stanu świecy (7C)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from application.providers.yahoo_chart_provider import YahooChartProvider
from data.yahoo.yahoo_session import FetchResult, OutcomeKind


class TestYahooVariant1h:
    def test_intraday_uses_interval_1h(self):
        from data.yahoo import yahoo_session as mod
        variants = mod._get_variant_params() if hasattr(mod, "_get_variant_params") else None
        if variants is None:
            variants = getattr(mod, "VARIANTS", None)
        assert variants is not None
        intraday = variants["intraday"]
        assert intraday["interval"] == "1h"
        assert intraday["range"] == "5d"


class TestCandleStateDetection:
    def test_open_when_observation_before_close(self):
        candle_start = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        observed_at = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        assert YahooChartProvider._classify_candle_state(candle_start, observed_at) == "OPEN"

    def test_closed_when_observation_at_or_after_next_hour(self):
        candle_start = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        observed_at = datetime(2026, 8, 21, 13, 0, tzinfo=timezone.utc)
        assert YahooChartProvider._classify_candle_state(candle_start, observed_at) == "CLOSED"

    def test_closed_when_candle_start_is_past_hour(self):
        candle_start = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        observed_at = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        assert YahooChartProvider._classify_candle_state(candle_start, observed_at) == "CLOSED"

    def test_exact_close_boundary_no_rounding(self):
        candle_start = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)
        observed_at = candle_start + timedelta(hours=1)
        assert YahooChartProvider._classify_candle_state(candle_start, observed_at) == "CLOSED"

    def test_partial_hour_open_no_rounding(self):
        candle_start = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)
        observed_at = candle_start + timedelta(minutes=30)
        assert YahooChartProvider._classify_candle_state(candle_start, observed_at) == "OPEN"


class _SequenceClock:
    """Deterministyczny zegar — zwraca kolejne czasy z listy (bez patchowania)."""

    def __init__(self, times):
        self._times = list(times)
        self._idx = 0

    def __call__(self):
        value = self._times[self._idx]
        self._idx = min(self._idx + 1, len(self._times) - 1)
        return value


def _ts(dt: datetime) -> float:
    return dt.timestamp()


def _intraday_result(timestamps, symbol="AAA.WA"):
    n = len(timestamps)
    return FetchResult(
        kind=OutcomeKind.SUCCESS_WITH_DATA,
        data={
            "variant": "intraday",
            "http_status": 200,
            "captured_at": "2026-08-21T12:15:00+00:00",
            "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                     "currency": "PLN", "exchangeName": "WSE"},
            "timestamp": timestamps,
            "open": [1.0] * n,
            "high": [1.5] * n,
            "low": [0.5] * n,
            "close": [1.1] * n,
            "volume": [10] * n,
            "events": {},
        },
        message=None,
    )


class _FakeChartSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def fetch_chart(self, symbol, variant="daily"):
        self.calls.append((symbol, variant))
        return self._results.pop(0)


class TestIntradayCandleClassification:
    def test_previous_closed_and_last_open(self):
        observed_at = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        prev = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        cur = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        provider = YahooChartProvider(
            _FakeChartSession([_intraday_result([_ts(prev), _ts(cur)])]),
            clock=lambda: observed_at,
        )
        md = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert md[0].candle_state == "CLOSED"
        assert md[1].candle_state == "OPEN"

    def test_exact_boundary_is_closed(self):
        candle = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        provider = YahooChartProvider(
            _FakeChartSession([_intraday_result([_ts(candle)])]),
            clock=lambda: candle + timedelta(hours=1),
        )
        md = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert md[0].candle_state == "CLOSED"

    def test_market_data_carries_timeframe_and_candle_state(self):
        observed_at = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        prev = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        cur = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        provider = YahooChartProvider(
            _FakeChartSession([_intraday_result([_ts(prev), _ts(cur)])]),
            clock=lambda: observed_at,
        )
        md = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert md[0].timeframe == "1h"
        assert md[1].timeframe == "1h"
        assert md[0].candle_state == "CLOSED"
        assert md[1].candle_state == "OPEN"

    def test_all_rows_share_single_observed_at(self):
        observed_at = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        prev = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        cur = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        provider = YahooChartProvider(
            _FakeChartSession([_intraday_result([_ts(prev), _ts(cur)])]),
            clock=lambda: observed_at,
        )
        md = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert {m.observed_at for m in md} == {observed_at}

    def test_clock_called_once_per_result_and_again_on_next(self):
        candledt = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc)
        clock = _SequenceClock([t1, t2])
        provider = YahooChartProvider(
            _FakeChartSession([
                _intraday_result([_ts(candledt)]),
                _intraday_result([_ts(candledt)]),
            ]),
            clock=clock,
        )
        first = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        second = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert first[0].observed_at == t1
        assert second[0].observed_at == t2
        assert first[0].observed_at != second[0].observed_at

    def test_clock_not_called_for_daily(self):
        candle = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        calls = []

        def clock():
            calls.append(1)
            return datetime.now(timezone.utc)

        daily_result = FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data={
                "variant": "daily",
                "http_status": 200,
                "captured_at": "2026-08-21T12:15:00+00:00",
                "meta": {"symbol": "AAA.WA"},
                "timestamp": [_ts(candle)],
                "open": [1.0], "high": [1.5], "low": [0.5],
                "close": [1.1], "volume": [10], "events": {},
            },
            message=None,
        )
        provider = YahooChartProvider(
            _FakeChartSession([daily_result]),
            clock=clock,
        )
        provider.scan(["AAA.WA"])
        assert calls == []


class TestObservedAtTransport:
    """Transport request-scoped observed_at przez FetchResult (7C/12)."""

    def test_fetch_result_default_is_none(self):
        plain = FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)
        assert plain.observed_at is None

    def test_fetch_result_preserves_observed_at(self):
        t1 = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        r = FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA, data={}, message=None,
                        observed_at=t1)
        assert r.observed_at == t1

    def test_provider_uses_fetch_result_observed_at(self):
        t1 = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 21, 12, 16, tzinfo=timezone.utc)
        candle = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        result = _intraday_result([_ts(candle)])
        result.observed_at = t1
        calls = []

        def clock():
            calls.append(1)
            return t2

        provider = YahooChartProvider(_FakeChartSession([result]), clock=clock)
        md = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert md[0].observed_at == t1
        assert calls == []

    def test_fallback_normal_path_uses_own_clock_once(self):
        t1 = datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc)
        candle = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        calls = []

        def clock():
            calls.append(1)
            return t1

        clock_seq = _SequenceClock([t1, t2])
        provider = YahooChartProvider(
            _FakeChartSession([
                _intraday_result([_ts(candle)]),
                _intraday_result([_ts(candle)]),
            ]),
            clock=clock_seq,
        )
        first = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        second = provider.fetch_intraday(["AAA.WA"])["AAA.WA"]["market_data"]
        assert first[0].observed_at == t1
        assert second[0].observed_at == t2
        assert first[0].observed_at != second[0].observed_at

    def test_daily_does_not_touch_observed_at(self):
        candle = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        calls = []

        def clock():
            calls.append(1)
            return datetime.now(timezone.utc)

        daily_result = FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data={
                "variant": "daily",
                "http_status": 200,
                "captured_at": "2026-08-21T12:15:00+00:00",
                "meta": {"symbol": "AAA.WA"},
                "timestamp": [_ts(candle)],
                "open": [1.0], "high": [1.5], "low": [0.5],
                "close": [1.1], "volume": [10], "events": {},
            },
            message=None,
            observed_at=datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc),
        )
        provider = YahooChartProvider(_FakeChartSession([daily_result]), clock=clock)
        provider.scan(["AAA.WA"])
        assert calls == []