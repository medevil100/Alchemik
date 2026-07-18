"""
Test module for YahooFetcher.

This module tests the yfinance-based implementation of YahooFetcher.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from data.yahoo.yahoo_fetcher import YahooFetcher
from data.yahoo.yahoo_exceptions import RateLimitExceededError, InvalidSymbolError, YahooFinanceError


class TestYahooFetcher(unittest.TestCase):
    """Test cases for YahooFetcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sleep = Mock()
        self.mock_ticker_factory = Mock()
        self.fetcher = YahooFetcher(
            ticker_factory=self.mock_ticker_factory,
            sleep_func=self.mock_sleep
        )

    def test_fetch_stock_data_success(self):
        """Test successful fetch_stock_data call."""
        # Setup proper DataFrame
        import pandas as pd
        mock_history = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0],
                "High": [101.0, 102.0, 103.0],
                "Low": [99.0, 100.0, 101.0],
                "Close": [100.5, 101.5, 102.5],
                "Volume": [1000000, 1100000, 1200000]
            },
            index=pd.to_datetime([
                "2026-01-01",
                "2026-01-02",
                "2026-01-03"
            ])
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        self.mock_ticker_factory.return_value = mock_ticker

        result = self.fetcher.fetch_stock_data("TEST")

        self.assertEqual(len(result), 3)
        # Verify first candle
        self.assertEqual(result[0].open, 100.0)
        self.assertEqual(result[0].high, 101.0)
        self.assertEqual(result[0].low, 99.0)
        self.assertEqual(result[0].close, 100.5)
        self.assertEqual(result[0].volume, 1000000)
        # Verify last candle
        self.assertEqual(result[-1].open, 102.0)
        self.assertEqual(result[-1].high, 103.0)
        self.assertEqual(result[-1].low, 101.0)
        self.assertEqual(result[-1].close, 102.5)
        self.assertEqual(result[-1].volume, 1200000)
        self.mock_ticker_factory.assert_called_once_with("TEST")

    def test_fetch_stock_data_empty_dataframe(self):
        """Test empty DataFrame response (invalid symbol)."""
        # Setup mock
        mock_history = MagicMock()
        mock_history.empty = True
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history
        self.mock_ticker_factory.return_value = mock_ticker

        with self.assertRaises(InvalidSymbolError):
            self.fetcher.fetch_stock_data("INVALID")

    def test_fetch_stock_data_rate_limit(self):
        """Test rate limit exception handling."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("too many requests")
        self.mock_ticker_factory.return_value = mock_ticker

        with self.assertRaises(RateLimitExceededError):
            self.fetcher.fetch_stock_data("TEST")

    def test_fetch_stock_data_delisted_symbol(self):
        """Test delisted symbol exception handling."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("symbol may be delisted")
        self.mock_ticker_factory.return_value = mock_ticker

        with self.assertRaises(InvalidSymbolError):
            self.fetcher.fetch_stock_data("DELISTED")

    def test_fetch_stock_data_general_error(self):
        """Test general error exception handling."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("general error")
        self.mock_ticker_factory.return_value = mock_ticker

        with self.assertRaises(YahooFinanceError):
            self.fetcher.fetch_stock_data("ERROR")

    def test_dependency_injection(self):
        """Test dependency injection with mock ticker factory."""
        mock_ticker = MagicMock()
        mock_history = MagicMock()
        mock_history.empty = False
        mock_history.iterrows.return_value = [
            ("2026-01-01", {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.5, "Volume": 1000000})
        ]
        mock_ticker.history.return_value = mock_history

        fetcher = YahooFetcher(ticker_factory=lambda _: mock_ticker)
        result = fetcher.fetch_stock_data("TEST")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].open, 100.0)
        mock_ticker.history.assert_called_once_with(period="260d")


if __name__ == "__main__":
    unittest.main()