import unittest
import inspect

from unittest.mock import Mock, patch

from application import entrypoint
from application.market_scanner import MarketScanner
from application.providers.yahoo_chart_provider import YahooChartProvider
from application.sources.yahoo_discovery_source import YahooDiscoverySource
from application.sources.static_instrument_source import StaticInstrumentSource
from data.yahoo.yahoo_session import FetchResult, OutcomeKind, ScreenerPagination


class FakeSession:
    def paginate_screener(self, size=250):
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=ScreenerPagination(total=0, pages=[]),
            message=None,
        )

    def fetch_chart(self, symbol, variant="daily"):
        return FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)


class TestEntrypointComposition(unittest.TestCase):
    def _patch_heavy(self):
        # Patch everything constructed by build_runtime_service except the
        # data-source components we want to inspect as real objects.
        patchers = [
            patch.object(entrypoint, "SQLiteHistoryRepository", return_value=Mock()),
            patch.object(entrypoint, "RuntimeService", return_value=Mock()),
            patch.object(entrypoint, "OpportunityDeduplicator", return_value=Mock()),
            patch.object(entrypoint, "AlertBuilder", return_value=Mock()),
            patch.object(entrypoint, "AlertDispatcher", return_value=Mock()),
            patch.object(entrypoint, "HunterEngine", return_value=Mock()),
            patch.object(entrypoint, "TechnicalEngine", return_value=Mock()),
            patch.object(entrypoint, "NewsFilterConfig", return_value=Mock()),
            patch.object(entrypoint, "NewsPipeline", return_value=Mock()),
            patch.object(entrypoint, "DecisionEngine", return_value=Mock()),
            patch.object(entrypoint, "RankingEngine", return_value=Mock()),
            patch.object(entrypoint, "RiskEngine", return_value=Mock()),
            patch.object(entrypoint, "AnalystEngine", return_value=Mock()),
            patch.object(entrypoint, "MasterEngine", return_value=Mock()),
            patch.object(entrypoint, "OutcomeComputer", return_value=Mock()),
            patch.object(entrypoint, "TradingCalendar", return_value=Mock()),
            patch.object(entrypoint, "OutcomeConfig", return_value=Mock()),
        ]
        for p in patchers:
            p.start()
        return patchers

    def _build_and_capture(self, **kwargs):
        created = {}

        original = MarketScanner

        def fake_market_scanner(universe, provider):
            created["universe"] = universe
            created["provider"] = provider
            return original(universe, provider)

        patchers = self._patch_heavy()
        patch.object(entrypoint, "MarketScanner", side_effect=fake_market_scanner).start()
        try:
            runtime = entrypoint.build_runtime_service(**kwargs)
        finally:
            patch.stopall()
        return runtime, created

    def test_default_build_wires_dynamic_yahoo_source_and_provider(self):
        fake_session = FakeSession()
        runtime, created = self._build_and_capture(yahoo_session=fake_session)

        # build_runtime_service returned an object (no TypeError).
        self.assertIsNotNone(runtime)

        universe = created["universe"]
        provider = created["provider"]
        self.assertIsInstance(universe._source, YahooDiscoverySource)
        self.assertIsInstance(provider, YahooChartProvider)

    def test_no_static_instrument_source_by_default(self):
        src = inspect.getsource(entrypoint.build_runtime_service)
        # build_runtime_service must not construct StaticInstrumentSource by default.
        self.assertNotIn("StaticInstrumentSource()", src)

    def test_static_source_still_requires_tickers(self):
        with self.assertRaises(TypeError):
            StaticInstrumentSource()

    def test_explicit_static_requires_approved_ticker_list(self):
        with self.assertRaises(ValueError):
            entrypoint.build_runtime_service(
                yahoo_session=FakeSession(), source_kind="static", static_tickers=None
            )

    def test_explicit_static_wires_static_source(self):
        created = {}

        original = MarketScanner

        def fake_market_scanner(universe, provider):
            created["universe"] = universe
            created["provider"] = provider
            return original(universe, provider)

        patchers = self._patch_heavy()
        patch.object(entrypoint, "MarketScanner", side_effect=fake_market_scanner).start()
        try:
            entrypoint.build_runtime_service(
                yahoo_session=FakeSession(),
                source_kind="static",
                static_tickers=["AAA.WA", "BBB.WA"],
            )
        finally:
            patch.stopall()

        self.assertIsInstance(created["universe"]._source, StaticInstrumentSource)
        self.assertEqual(created["universe"].get_universe(), ["AAA.WA", "BBB.WA"])


if __name__ == "__main__":
    unittest.main()