"""
Test module for the Decision Engine.

This module tests the functionality of the Decision Engine, including:
- Importing the DecisionEngine class
- Data connection with Technical Analyzer and News Analyzer
- Unified data model output
- Error handling for invalid or empty input data
"""

import unittest
from unittest.mock import MagicMock, patch
from engines.ai.decision_engine import DecisionEngine
from data.models.analysis_result import AnalysisResult
from data.models.ai_signal import AISignal


class TestDecisionEngine(unittest.TestCase):
    """Test cases for the DecisionEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.decision_engine = DecisionEngine()

    def test_import_decision_engine(self):
        """Test that the DecisionEngine class can be imported."""
        self.assertIsNotNone(DecisionEngine)

    @patch('engines.technical.TechnicalEngine.analyze')
    @patch('engines.news.NewsPipeline.process')
    def test_data_connection(self, mock_news_process, mock_tech_analyze):
        """Test data connection with Technical and News Analyzers."""
        # Mock data for Technical Analyzer (using real contract)
        mock_tech_analyze.return_value = {
            "sma": 100.0,
            "rsi": 50.0,
            "macd": 1.5,
            "vwap": 105.0
        }

        # Mock data for News Analyzer (using real contract)
        mock_news_process.return_value = [
            {"headline": "Test News", "sentiment": 0.5, "relevance": 0.8}
        ]

        # Test input data
        market_data = {
            "technical_analysis": mock_tech_analyze.return_value,
            "news_analysis": mock_news_process.return_value
        }

        result = self.decision_engine.process_data(market_data)

        # Verify the result is an AISignal with expected fields
        self.assertIsInstance(result, AISignal)
        self.assertIsNotNone(result.signal_type)
        self.assertIsNotNone(result.reasoning)
        self.assertIsNotNone(result.confidence)
        self.assertIsNotNone(result.generated_at)

    def test_error_handling(self):
        """Test error handling for invalid or empty input data."""
        with self.assertRaises(RuntimeError):
            self.decision_engine.process_data({})


if __name__ == "__main__":
    unittest.main()