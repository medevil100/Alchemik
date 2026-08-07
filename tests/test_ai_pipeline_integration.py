import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem
from data.models.ai_signal import AISignal
from engines.ai.pipeline import AIPipeline


THIRTY_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=60)


def _make_market_data(count: int = 60) -> list[MarketData]:
    """Build sufficient OHLCV data for all indicator windows."""
    base = THIRTY_DAYS_AGO
    data = []
    for i in range(count):
        ts = base + timedelta(days=i)
        data.append(
            MarketData(
                timestamp=ts,
                open=100.0 + i * 0.1,
                high=105.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=104.0 + i * 0.1,
                volume=1_000_000 + i * 10_000,
            )
        )
    return data


class TestAIPipelineIntegration(unittest.TestCase):
    """Test the AIPipeline with real internal engines, only mocking the external AI provider."""

    def setUp(self):
        self.company = CompanyInfo(
            name="Test Company",
            symbol="TEST",
            sector="Technology",
        )
        self.market_data = _make_market_data(60)
        self.news = [
            NewsItem(
                title="Test News",
                source="Test Source",
                publish_date=datetime.now(),
                url="https://example.com/test-news",
                summary="Test summary",
            )
        ]

        # Only mock the external AI provider boundary
        self.mock_ai_provider = MagicMock()
        self.mock_ai_provider.send_prompt.return_value = AISignal(
            signal_type="buy",
            confidence=0.9,
            generated_at=datetime.now(),
            reasoning="Test reasoning",
        )

        # Patch AIProvider and AIProviderConfig at the module level
        self.ai_provider_patcher = patch(
            'engines.ai.pipeline.AIProvider', return_value=self.mock_ai_provider
        )
        self.ai_config_patcher = patch(
            'engines.ai.pipeline.AIProviderConfig',
            autospec=True,
        )
        self.mock_ai_provider_class = self.ai_provider_patcher.start()
        self.mock_config_class = self.ai_config_patcher.start()

        self.pipeline = AIPipeline()

    def tearDown(self):
        self.ai_provider_patcher.stop()
        self.ai_config_patcher.stop()

    def test_full_pipeline_flow(self):
        """Test the complete AI Pipeline flow from input to AISignal output."""
        result = self.pipeline.run_pipeline(self.company, self.market_data, self.news)

        # Verify the pipeline produced a real result
        self.assertIsInstance(result, AISignal)
        self.assertTrue(hasattr(result, "signal_type"))
        self.assertTrue(hasattr(result, "confidence"))
        self.assertTrue(hasattr(result, "reasoning"))

    def test_empty_input_handling(self):
        """Test pipeline behavior with empty input data.

        With real engines, empty OHLCV data causes TechnicalEngine to raise
        ValueError (not enough data points for SMA window). The pipeline
        wraps this in a RuntimeError.
        """
        with self.assertRaises(Exception):
            self.pipeline.run_pipeline(self.company, [], [])


if __name__ == '__main__':
    unittest.main()