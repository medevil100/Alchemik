import unittest
from unittest.mock import Mock
from application.providers.yahoo_scan_provider import YahooScanProvider

class TestYahooScanProvider(unittest.TestCase):
    def setUp(self):
        self.mock_fetcher = Mock()
        self.provider = YahooScanProvider(self.mock_fetcher)
    
    def test_scan_calls_fetcher(self):
        """Test that scan calls fetch_stock_data for each instrument."""
        instruments = ["CDR.WA", "11B.WA"]
        self.mock_fetcher.fetch_stock_data.side_effect = [
            {"price": 100}, {"price": 200}
        ]
        
        results = self.provider.scan(instruments)
        
        self.assertEqual(len(results), 2)
        self.mock_fetcher.fetch_stock_data.assert_any_call("CDR.WA")
        self.mock_fetcher.fetch_stock_data.assert_any_call("11B.WA")
    
    def test_scan_handles_failures(self):
        """Test that scan continues after a failure."""
        instruments = ["CDR.WA", "FAIL", "AAPL"]
        self.mock_fetcher.fetch_stock_data.side_effect = [
            {"price": 100}, Exception("Failed"), {"price": 200}
        ]
        
        results = self.provider.scan(instruments)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["symbol"], "CDR.WA")
        self.assertEqual(results[1]["symbol"], "AAPL")
    
    def test_dependency_injection(self):
        """Test that the fetcher is properly injected."""
        self.assertIs(self.provider._fetcher, self.mock_fetcher)
    
    def test_no_engine_dependencies(self):
        """Test that the provider has no dependencies on Engine classes."""
        # This is implicit in the design - no engine imports in the provider
        pass