import math
import unittest

from data.yahoo.yahoo_session import FetchResult, OutcomeKind
from application.providers.yahoo_chart_provider import YahooChartProvider


def chart_result(symbol, timestamps, open_, high, low, close, volume,
                 meta=None, variant="daily"):
    return FetchResult(
        kind=OutcomeKind.SUCCESS_WITH_DATA,
        data={
            "variant": variant,
            "http_status": 200,
            "captured_at": "2026-08-15T00:00:00+00:00",
            "meta": meta or _valid_meta(symbol),
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "events": {},
        },
        message=None,
    )


def _valid_meta(symbol):
    return {
        "symbol": symbol,
        "instrumentType": "EQUITY",
        "currency": "PLN",
        "exchangeName": "WSE",
    }


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
        self._results = list(results)
        self.calls = []

    def fetch_chart(self, symbol, variant="daily"):
        self.calls.append((symbol, variant))
        return self._results.pop(0)


class FakeDiscoverySource:
    def __init__(self, snapshot=None):
        self.accepted_snapshot = snapshot or {}


class TestYahooChartIdentityValidation(unittest.TestCase):
    def _scan(self, result, discovery=None):
        session = FakeChartSession([result])
        provider = YahooChartProvider(session, discovery_source=discovery)
        return provider, provider.scan(["AAA.WA"])

    def test_meta_symbol_mismatch_rejected(self):
        provider, output = self._scan(ok("OTHER.WA"))
        self.assertEqual(output, [])
        self.assertFalse(provider.last_scan[0]["accepted"])
        self.assertIn("meta_symbol_mismatch", provider.last_scan[0]["reasons"])

    def test_instrument_type_not_equity_rejected(self):
        meta = _valid_meta("AAA.WA")
        meta["instrumentType"] = "MUTUALFUND"
        provider, output = self._scan(ok("AAA.WA"), ) if False else (None, None)
        # direct construction
        session = FakeChartSession([chart_result("AAA.WA", [1], [1.0], [1.0], [1.0], [1.0], [1], meta=meta)])
        provider = YahooChartProvider(session)
        output = provider.scan(["AAA.WA"])
        self.assertEqual(output, [])
        self.assertIn("instrument_type_not_equity", provider.last_scan[0]["reasons"])

    def test_currency_not_pln_rejected(self):
        meta = _valid_meta("AAA.WA")
        meta["currency"] = "USD"
        session = FakeChartSession([chart_result("AAA.WA", [1], [1.0], [1.0], [1.0], [1.0], [1], meta=meta)])
        provider = YahooChartProvider(session)
        output = provider.scan(["AAA.WA"])
        self.assertEqual(output, [])
        self.assertIn("currency_not_pln", provider.last_scan[0]["reasons"])

    def test_exchange_name_not_wse_rejected(self):
        meta = _valid_meta("AAA.WA")
        meta["exchangeName"] = "NAS"
        session = FakeChartSession([chart_result("AAA.WA", [1], [1.0], [1.0], [1.0], [1.0], [1], meta=meta)])
        provider = YahooChartProvider(session)
        output = provider.scan(["AAA.WA"])
        self.assertEqual(output, [])
        self.assertIn("exchange_name_not_wse", provider.last_scan[0]["reasons"])

    def test_discovery_snapshot_conflict_rejected(self):
        discovery = FakeDiscoverySource({} )
        discovery.accepted_snapshot["AAA.WA"] = {
            "symbol": "AAA.WA", "quoteType": "EQUITY", "exchange": "WSE",
            "market": "pl_market", "currency": "USD", "regularMarketPrice": 1.0,
        }
        session = FakeChartSession([ok("AAA.WA")])
        provider = YahooChartProvider(session, discovery_source=discovery)
        output = provider.scan(["AAA.WA"])
        self.assertEqual(output, [])
        self.assertIn("discovery_currency_not_pln", provider.last_scan[0]["reasons"])


class TestYahooChartHistoryValidation(unittest.TestCase):
    def _run(self, result):
        session = FakeChartSession([result])
        provider = YahooChartProvider(session)
        return provider, provider.scan(["AAA.WA"])

    def test_all_rows_incomplete_not_returned_as_empty_data(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[None, 2.0, 3.0],
            high=[1.0, None, 3.0],
            low=[1.0, 2.0, None],
            close=[1.0, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(output, [])
        self.assertIn("no_complete_rows", provider.last_scan[0]["reasons"])

    def test_empty_timestamps_rejected(self):
        result = chart_result("AAA.WA", [], [], [], [], [], [])
        provider, output = self._run(result)
        self.assertEqual(output, [])
        self.assertIn("empty_timestamps", provider.last_scan[0]["reasons"])

    def test_duplicate_timestamps_rejected(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 1, 2],
            open_=[1.0, 2.0, 3.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(output, [])
        self.assertIn("duplicate_timestamps", provider.last_scan[0]["reasons"])

    def test_non_increasing_timestamps_rejected(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 3, 2],
            open_=[1.0, 2.0, 3.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(output, [])
        self.assertIn("timestamps_not_increasing", provider.last_scan[0]["reasons"])

    def test_length_mismatch_rejected(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[1.0, 2.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(output, [])
        self.assertIn("length_mismatch", provider.last_scan[0]["reasons"])

    def test_infinite_value_rejected(self):
        # Krok 2/8: nieskończona wartość odrzuca TYLKO wadliwy wiersz.
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[1.0, float("inf"), 3.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 2)
        self.assertEqual(provider.last_scan[0]["rejected_rows"], 1)
        self.assertEqual(
            provider.last_scan[0]["rejection_reasons"].get("non_numeric_or_infinite"), 1
        )

    def test_non_numeric_value_rejected(self):
        # Krok 2/8: nienumeryczna wartość odrzuca TYLKO wadliwy wiersz.
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[1.0, "2.0", 3.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 2)
        self.assertEqual(provider.last_scan[0]["rejected_rows"], 1)
        self.assertEqual(
            provider.last_scan[0]["rejection_reasons"].get("non_numeric_or_infinite"), 1
        )

    def test_negative_volume_rejected(self):
        # Krok 2/8: ujemny wolumen odrzuca TYLKO wadliwy wiersz.
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[1.0, 2.0, 3.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[1, -1, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 2)
        self.assertEqual(provider.last_scan[0]["rejected_rows"], 1)
        self.assertEqual(
            provider.last_scan[0]["rejection_reasons"].get("negative_volume"), 1
        )

    def test_volume_zero_preserved(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[1.0, 2.0, 3.0],
            high=[1.0, 2.0, 3.0],
            low=[1.0, 2.0, 3.0],
            close=[1.0, 2.0, 3.0],
            volume=[0, 100, 200],
        )
        provider, output = self._run(result)
        self.assertEqual(len(output), 1)
        volumes = [d.volume for d in output[0]["data"]]
        self.assertIn(0, volumes)

    def test_ohlc_inconsistency_rejected(self):
        # Krok 2/8: naruszenie OHLC odrzuca TYLKO wadliwy wiersz.
        result = chart_result(
            "AAA.WA",
            timestamps=[1, 2, 3],
            open_=[5.0, 2.0, 3.0],
            high=[4.0, 5.0, 6.0],   # row 0: high < open
            low=[1.0, 1.0, 1.0],
            close=[4.5, 2.0, 3.0],
            volume=[1, 2, 3],
        )
        provider, output = self._run(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 2)
        self.assertEqual(provider.last_scan[0]["rejected_rows"], 1)
        self.assertEqual(
            provider.last_scan[0]["rejection_reasons"].get("ohlc_inconsistency"), 1
        )

    def test_short_valid_history_accepted(self):
        result = chart_result(
            "AAA.WA",
            timestamps=[1],
            open_=[1.0],
            high=[1.0],
            low=[1.0],
            close=[1.0],
            volume=[5],
        )
        provider, output = self._run(result)
        self.assertEqual(len(output), 1)
        self.assertEqual(len(output[0]["data"]), 1)

    def test_one_symbol_error_does_not_remove_others(self):
        session = FakeChartSession([
            ok("AAA.WA"),
            FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message="HTTP 404"),
            ok("CCC.WA"),
        ])
        provider = YahooChartProvider(session)
        output = provider.scan(["AAA.WA", "BBB.WA", "CCC.WA"])
        self.assertEqual([r["symbol"] for r in output], ["AAA.WA", "CCC.WA"])

    def test_diagnostics_cleared_before_each_scan(self):
        session = FakeChartSession([ok("AAA.WA"), ok("BBB.WA")])
        provider = YahooChartProvider(session)
        provider.scan(["AAA.WA"])
        provider.scan(["BBB.WA"])
        self.assertEqual(len(provider.last_scan), 1)
        self.assertEqual(provider.last_scan[0]["symbol"], "BBB.WA")

    def test_diagnostics_have_required_fields(self):
        session = FakeChartSession([ok("AAA.WA")])
        provider = YahooChartProvider(session)
        provider.scan(["AAA.WA"])
        diag = provider.last_scan[0]
        for key in ("symbol", "outcome_kind", "accepted", "reasons",
                    "raw_rows", "valid_rows", "variant"):
            self.assertIn(key, diag)


if __name__ == "__main__":
    unittest.main()