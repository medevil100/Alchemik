import unittest
from datetime import datetime, timezone

from data.yahoo.yahoo_session import FetchResult, OutcomeKind
from application.providers.yahoo_chart_provider import YahooChartProvider


def chart_result(symbol, timestamps, open_, high, low, close, volume,
                 events=None):
    return FetchResult(
        kind=OutcomeKind.SUCCESS_WITH_DATA,
        data={
            "variant": "daily",
            "meta": {"symbol": symbol},
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "events": events or {},
        },
        message=None,
    )


def ok(symbol="AAA.WA"):
    return chart_result(
        symbol,
        timestamps=[1690000000, 1690000001, 1690000002],
        open_=[1.0, 2.0, 3.0],
        high=[1.5, 2.5, 3.5],
        low=[0.5, 1.5, 2.5],
        close=[1.1, 2.1, 3.1],
        volume=[0, 100, 200],
    )


class FakeChartSession:
    def __init__(self, results):
        self._results = results
        self.calls = []

    def fetch_chart(self, symbol, variant="daily"):
        self.calls.append((symbol, variant))
        return self._results.pop(0)


class TestYahooChartProvider(unittest.TestCase):
    def test_scans_daily_for_each_instrument(self):
        provider = YahooChartProvider(FakeChartSession([ok("AAA.WA"), ok("BBB.WA")]))
        result = provider.scan(["AAA.WA", "BBB.WA"])

        self.assertEqual([r["symbol"] for r in result], ["AAA.WA", "BBB.WA"])
        self.assertEqual(
            [c for c in provider._session.calls],
            [("AAA.WA", "daily"), ("BBB.WA", "daily")],
        )

    def test_normalizes_ohlcv_and_timestamps(self):
        provider = YahooChartProvider(FakeChartSession([ok()]))
        [record] = provider.scan(["AAA.WA"])

        data = record["data"]
        self.assertEqual(len(data), 3)
        self.assertAlmostEqual(data[0].open, 1.0)
        self.assertAlmostEqual(data[0].high, 1.5)
        self.assertAlmostEqual(data[0].low, 0.5)
        self.assertAlmostEqual(data[0].close, 1.1)
        self.assertEqual(data[0].volume, 0)
        self.assertEqual(data[0].timestamp, datetime.fromtimestamp(1690000000, tz=timezone.utc))

    def test_volume_zero_preserved(self):
        provider = YahooChartProvider(FakeChartSession([ok()]))
        [record] = provider.scan(["AAA.WA"])
        volumes = [d.volume for d in record["data"]]
        self.assertIn(0, volumes)

    def test_short_history_preserved(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1690000000],
            open_=[1.0], high=[1.0], low=[1.0], close=[1.0], volume=[5],
        )
        provider = YahooChartProvider(FakeChartSession([result]))
        [record] = provider.scan(["AAA.WA"])
        self.assertEqual(len(record["data"]), 1)

    def test_error_is_omitted_without_stopping_others(self):
        provider = YahooChartProvider(
            FakeChartSession([
                ok("AAA.WA"),
                FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message=None),
                ok("CCC.WA"),
            ])
        )
        result = provider.scan(["AAA.WA", "BBB.WA", "CCC.WA"])
        self.assertEqual([r["symbol"] for r in result], ["AAA.WA", "CCC.WA"])

    def test_does_not_invent_missing_values(self):
        # Unequal array lens must be treated as parse/missing fields, not padded.
        result = FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data={
                "variant": "daily",
                "meta": {"symbol": "AAA.WA"},
                "timestamp": [1690000000, 1690000001],
                "open": [1.0],
                "high": [1.0],
                "low": [1.0],
                "close": [1.0],
                "volume": [5],
                "events": {},
            },
            message=None,
        )
        provider = YahooChartProvider(FakeChartSession([result]))
        output = provider.scan(["AAA.WA"])
        self.assertEqual(output, [])


if __name__ == "__main__":
    unittest.main()