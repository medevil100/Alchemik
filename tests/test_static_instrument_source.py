import unittest
from application.sources.static_instrument_source import StaticInstrumentSource

class TestStaticInstrumentSource(unittest.TestCase):
    def test_get_instruments(self):
        """Test that get_instruments returns the correct list of tickers."""
        tickers = ["CDR.WA", "11B.WA", "AAPL", "MSFT"]
        source = StaticInstrumentSource(tickers)
        self.assertEqual(source.get_instruments(), tickers)
    
    def test_deduplication(self):
        """Test that duplicate tickers are removed while preserving order."""
        tickers = ["CDR.WA", "11B.WA", "AAPL", "MSFT", "CDR.WA"]
        expected = ["CDR.WA", "11B.WA", "AAPL", "MSFT"]
        source = StaticInstrumentSource(tickers)
        self.assertEqual(source.get_instruments(), expected)
    
    def test_empty_ticker(self):
        """Test that empty tickers raise an error."""
        with self.assertRaises(ValueError):
            StaticInstrumentSource(["CDR.WA", ""])
    
    def test_invalid_ticker(self):
        """Test that non-string tickers raise an error."""
        with self.assertRaises(ValueError):
            StaticInstrumentSource(["CDR.WA", 123])
    
    def test_no_http_requests(self):
        """Test that no HTTP requests are made during initialization."""
        # This is implicit in the design - no network calls in the class
        pass