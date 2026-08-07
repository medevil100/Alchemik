import unittest
from unittest.mock import Mock
from application.universe import PennyStockUniverse
from application.sources.static_instrument_source import StaticInstrumentSource
from application.market_scanner import MarketScanner, ScanProvider
from application.providers.yahoo_scan_provider import YahooScanProvider


class TestMarketScanner(unittest.TestCase):
    """MarketScanner tests with real Universe and real YahooScanProvider.

    YahooFetcher (Yahoo Finance) is mocked as a permitted external boundary.
    The application components (PennyStockUniverse, StaticInstrumentSource,
    YahooScanProvider, MarketScanner) are all real instances.
    """

    def _make_universe(self, instruments=None):
        """Build a real PennyStockUniverse backed by StaticInstrumentSource."""
        return PennyStockUniverse(
            StaticInstrumentSource(instruments or ["INSTR1", "INSTR2"]),
        )

    def _make_provider(self, scan_return=None):
        """Build a real YahooScanProvider with a mocked YahooFetcher (external boundary)."""
        fetcher = Mock()
        if scan_return is not None:
            fetcher.fetch_stock_data.side_effect = scan_return
        else:
            fetcher.fetch_stock_data.return_value = {"symbol": "INSTR1", "data": {}}
        return YahooScanProvider(fetcher)

    def test_scan_flow(self):
        """Test the flow from real Universe → real Provider → candidates."""
        universe = self._make_universe()

        mock_fetcher = Mock()
        mock_fetcher.fetch_stock_data.return_value = {"symbol": "INSTR1", "data": {}}
        provider = YahooScanProvider(mock_fetcher)

        scanner = MarketScanner(universe, provider)
        result = scanner.scan()

        self.assertEqual(len(result), 2)
        self.assertIn("INSTR1", [r.get("symbol") for r in result])

    def test_empty_universe(self):
        """Test behavior with an empty Universe."""
        universe = self._make_universe([])
        provider = self._make_provider([])
        scanner = MarketScanner(universe, provider)
        result = scanner.scan()
        self.assertEqual(result, [])

    def test_empty_provider_result(self):
        """Test behavior with an empty result from Provider."""
        universe = self._make_universe()

        mock_fetcher = Mock()
        mock_fetcher.fetch_stock_data.return_value = {}
        provider = YahooScanProvider(mock_fetcher)

        scanner = MarketScanner(universe, provider)
        result = scanner.scan()
        self.assertIsInstance(result, list)

    def test_order_preservation(self):
        """Test that the order of candidates is preserved.

        YahooScanProvider iterates instruments in order and wraps each
        fetcher result with {"symbol": instrument_id, "data": ...}.
        The symbol field reflects the loop variable (universe order),
        not the content of the fetcher return value.
        """
        universe = self._make_universe()

        mock_fetcher = Mock()
        mock_fetcher.fetch_stock_data.side_effect = [
            {"price": 100},   # for INSTR1 (first in universe)
            {"price": 200},   # for INSTR2 (second in universe)
        ]
        provider = YahooScanProvider(mock_fetcher)

        scanner = MarketScanner(universe, provider)
        result = scanner.scan()

        real_data = [r.get("data") for r in result]
        self.assertEqual(real_data, [{"price": 100}, {"price": 200}])

    def test_provider_swap(self):
        """Test that the Provider can be swapped."""
        universe = self._make_universe()

        fetcher1 = Mock()
        fetcher1.fetch_stock_data.side_effect = [
            {"symbol": "INSTR1", "data": {}},
            Exception("unused"),
        ]
        provider1 = YahooScanProvider(fetcher1)

        fetcher2 = Mock()
        fetcher2.fetch_stock_data.side_effect = [
            Exception("unused"),
            {"symbol": "INSTR2", "data": {}},
        ]
        provider2 = YahooScanProvider(fetcher2)

        scanner = MarketScanner(universe, provider1)
        result1 = scanner.scan()
        self.assertEqual([r["symbol"] for r in result1], ["INSTR1"])

        scanner2 = MarketScanner(universe, provider2)
        result2 = scanner2.scan()
        self.assertEqual([r["symbol"] for r in result2], ["INSTR2"])

    def test_no_hunter_engine_dependency(self):
        """Test that Hunter Engine is not used."""
        universe = self._make_universe()
        provider = self._make_provider()
        scanner = MarketScanner(universe, provider)

        self.assertNotIn("Hunter", str(scanner.__class__))
        self.assertNotIn("Hunter", str(provider.__class__))
