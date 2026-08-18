import unittest

from data.yahoo.yahoo_session import (
    FetchResult,
    OutcomeKind,
    ScreenerPage,
    ScreenerPagination,
)
from application.sources.yahoo_discovery_source import (
    UniverseContract,
    YahooDiscoverySource,
)


def q(symbol, price, quote_type="EQUITY", exchange="WSE",
      market="pl_market", currency="PLN"):
    return {
        "symbol": symbol,
        "quoteType": quote_type,
        "exchange": exchange,
        "market": market,
        "currency": currency,
        "regularMarketPrice": price,
    }


def pagination_of(total, pages):
    return FetchResult(
        kind=OutcomeKind.SUCCESS_WITH_DATA,
        data=ScreenerPagination(total=total, pages=pages),
        message=None,
    )


def page(start, count, quotes):
    return ScreenerPage(total=count, start=start, count=count, quotes=quotes)


class FakeSession:
    def __init__(self, result):
        self._result = result
        self.paginate_screener_calls = []

    def paginate_screener(self, size=250):
        self.paginate_screener_calls.append(size)
        return self._result


class TestUniverseContract(unittest.TestCase):
    def test_accepts_valid_equity_wse_pln(self):
        self.assertTrue(UniverseContract.accepts(q("AAA.WA", 0.10)))

    def test_accepts_lower_bound_inclusive(self):
        self.assertTrue(UniverseContract.accepts(q("AAA.WA", 0.10)))

    def test_accepts_upper_bound_inclusive(self):
        self.assertTrue(UniverseContract.accepts(q("AAA.WA", 10.00)))

    def test_rejects_below_lower_bound(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", 0.099)))

    def test_rejects_above_upper_bound(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", 10.01)))

    def test_rejects_non_numeric_price(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", None)))
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", "1.0")))

    def test_rejects_non_equity(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", 1.0, quote_type="MUTUALFUND")))

    def test_rejects_wrong_exchange(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", 1.0, exchange="NMS")))

    def test_rejects_wrong_market(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", 1.0, market="us_market")))

    def test_rejects_wrong_currency(self):
        self.assertFalse(UniverseContract.accepts(q("AAA.WA", 1.0, currency="USD")))


class TestYahooDiscoverySource(unittest.TestCase):
    def test_get_instruments_returns_exact_symbols_only(self):
        quotes = [
            q("AAA.WA", 0.5),
            q("BBB.WA", 9.9),
            q("CCC.WA", 50.0),   # rejected: price
            q("DDD.WA", 1.0, quote_type="ETF"),  # rejected: type
            q("EEE.WA", 1.0, exchange="LSE"),    # rejected: exchange
            q("FFF.WA", 1.0, market="us_market"),  # rejected: market
            q("GGG.WA", 1.0, currency="USD"),    # rejected: currency
        ]
        result = pagination_of(7, [page(0, 7, quotes)])
        source = YahooDiscoverySource(FakeSession(result))

        symbols = source.get_instruments()
        self.assertEqual(symbols, ["AAA.WA", "BBB.WA"])

    def test_no_suffix_appended(self):
        # A valid record whose symbol has no .WA suffix stays untouched.
        quotes = [q("AAA", 1.0)]
        source = YahooDiscoverySource(
            FakeSession(pagination_of(1, [page(0, 1, quotes)]))
        )
        self.assertEqual(source.get_instruments(), ["AAA"])

    def test_one_wse_set_without_gpw_nc_field(self):
        # Returned symbols are a plain list of strings; there must be no
        # GPW/NC discriminating field anywhere in the accepted records.
        quotes = [q("AAA.WA", 1.0)]
        source = YahooDiscoverySource(
            FakeSession(pagination_of(1, [page(0, 1, quotes)]))
        )
        symbols = source.get_instruments()
        self.assertIsInstance(symbols, list)
        self.assertTrue(all(isinstance(s, str) for s in symbols))
        self.assertNotIn("GPW", symbols)
        self.assertNotIn("NC", symbols)
        # UniverseContract exposes no segment field.
        self.assertFalse(hasattr(UniverseContract, "segment"))
        self.assertFalse(hasattr(UniverseContract, "gpw_nc"))

    def test_neutral_on_screener_failure_returns_empty_no_fallback(self):
        source = YahooDiscoverySource(
            FakeSession(FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message=None))
        )
        # No automatic fallback: returns empty list silently.
        self.assertEqual(source.get_instruments(), [])

    def test_deduplicates_symbols_and_counts(self):
        quotes = [q("AAA.WA", 1.0), q("AAA.WA", 1.0), q("BBB.WA", 2.0)]
        source = YahooDiscoverySource(
            FakeSession(pagination_of(3, [page(0, 3, quotes)]))
        )
        self.assertEqual(source.get_instruments(), ["AAA.WA", "BBB.WA"])

    def test_snapshot_present_with_safe_fields(self):
        quotes = [q("AAA.WA", 0.5)]
        source = YahooDiscoverySource(
            FakeSession(pagination_of(1, [page(0, 1, quotes)]))
        )
        source.get_instruments()
        snap = source.accepted_snapshot["AAA.WA"]
        for field in ("symbol", "quoteType", "exchange", "market",
                      "currency", "regularMarketPrice"):
            self.assertIn(field, snap)

    def test_snapshot_cleared_before_each_new_discovery(self):
        class MutableSession:
            def __init__(self):
                self.result = pagination_of(1, [page(0, 1, [q("AAA.WA", 1.0)])])

            def paginate_screener(self, size=250):
                return self.result

        session = MutableSession()
        source = YahooDiscoverySource(session)
        source.get_instruments()
        self.assertIn("AAA.WA", source.accepted_snapshot)

        # Next discovery returns only BBB.WA; snapshot for AAA.WA must be gone.
        session.result = pagination_of(1, [page(0, 1, [q("BBB.WA", 1.0)])])
        source.get_instruments()
        self.assertNotIn("AAA.WA", source.accepted_snapshot)
        self.assertIn("BBB.WA", source.accepted_snapshot)

    def test_snapshot_cleared_on_error_no_stale_use(self):
        class MutableSession:
            def __init__(self):
                self.result = pagination_of(1, [page(0, 1, [q("AAA.WA", 1.0)])])

            def paginate_screener(self, size=250):
                return self.result

        session = MutableSession()
        source = YahooDiscoverySource(session)
        source.get_instruments()
        self.assertIn("AAA.WA", source.accepted_snapshot)

        session.result = FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message=None)
        out = source.get_instruments()
        self.assertEqual(out, [])
        self.assertEqual(source.accepted_snapshot, {})
        self.assertEqual(source.last_discovery["outcome_kind"], "HTTP_ERROR")

    def test_diagnostics_success_has_safe_fields(self):
        quotes = [q("AAA.WA", 1.0), q("BBB.WA", 50.0), q("CCC.WA", 2.0)]
        source = YahooDiscoverySource(
            FakeSession(pagination_of(3, [page(0, 3, quotes)]))
        )
        source.get_instruments()
        diag = source.last_discovery
        self.assertEqual(diag["outcome_kind"], "SUCCESS_WITH_DATA")
        self.assertEqual(diag["total_records"], 3)
        self.assertEqual(diag["accepted_count"], 2)
        self.assertEqual(diag["rejected_count"], 1)
        # No cookie/crumb keys present.
        self.assertNotIn("crumb", diag)
        self.assertNotIn("a3", diag)
        self.assertNotIn("cookie", diag)

    def test_diagnostics_error_visible_no_fallback(self):
        err = FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message="HTTP 500")
        source = YahooDiscoverySource(FakeSession(err))
        self.assertEqual(source.get_instruments(), [])
        self.assertEqual(source.last_discovery["outcome_kind"], "HTTP_ERROR")
        self.assertEqual(source.last_discovery["accepted_count"], 0)


if __name__ == "__main__":
    unittest.main()
