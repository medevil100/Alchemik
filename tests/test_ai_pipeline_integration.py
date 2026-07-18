import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem
from data.models.ai_signal import AISignal
from engines.ai.pipeline import AIPipeline


class TestAIPipelineIntegration(unittest.TestCase):
    def setUp(self):
        # Create test data first
        self.company = CompanyInfo(
            name="Test Company",
            symbol="TEST",
            sector="Technology"
        )
        
        self.market_data = [
            MarketData(
                timestamp=datetime.now(),
                open=100.0 + (i * 0.1),
                high=105.0 + (i * 0.1),
                low=99.0 + (i * 0.1),
                close=104.0 + (i * 0.1),
                volume=1000000
            )
            for i in range(60)
        ]
        
        self.news = [
            NewsItem(
                title="Test News",
                source="Test Source",
                publish_date=datetime.now(),
                url="https://example.com/test-news",
                summary="Test summary"
            )
        ]
        
        # Expected results
        self.expected_signal = AISignal(
            signal_type="buy",
            confidence=0.9,
            generated_at=datetime.now(),
            reasoning="Test reasoning"
        )
        
        # Mock all dependencies
        self.mock_technical_engine = MagicMock()
        self.mock_news_pipeline = MagicMock()
        self.mock_decision_engine = MagicMock()
        self.mock_prompt_builder = MagicMock()
        self.mock_ai_provider = MagicMock()
        self.mock_ai_provider.send_prompt.return_value = self.expected_signal
        
        # Configure mocks first
        from data.models.analysis_result import AnalysisResult
        self.mock_technical_engine.analyze.return_value = AnalysisResult(
            company=self.company,
            market_data=self.market_data,
            news=self.news,
            signals=[{"type": "macd", "values": [0.0] * len(self.market_data)}],
            generated_at=datetime.now()
        )
        
        # Apply patches before creating AIPipeline
        self.patchers = [
            patch('engines.ai.pipeline.TechnicalEngine', return_value=self.mock_technical_engine),
            patch('engines.ai.pipeline.NewsPipeline', return_value=self.mock_news_pipeline),
            patch('engines.ai.pipeline.DecisionEngine', return_value=self.mock_decision_engine),
            patch('engines.ai.pipeline.PromptBuilder', return_value=self.mock_prompt_builder),
            patch('engines.ai.pipeline.AIProvider', return_value=self.mock_ai_provider)
        ]
        
        for patcher in self.patchers:
            patcher.start()
        
        # Now create the pipeline
        self.mock_news_pipeline.process.return_value = {"news": "result"}
        self.mock_decision_engine.process_data.return_value = {"decision": "data"}
        self.mock_prompt_builder.build_prompt.return_value = "test prompt"
        
        self.pipeline = AIPipeline()
    
    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()
    
    def test_full_pipeline_flow(self):
        """Test the complete AI Pipeline flow from input to AISignal output."""
        result = self.pipeline.run_pipeline(self.company, self.market_data, self.news)
        
        # Verify all steps were called correctly
        self.mock_technical_engine.analyze.assert_called_once_with(self.market_data)
        self.mock_news_pipeline.process.assert_called_once_with(self.news)
        self.mock_decision_engine.process_data.assert_called_once_with({
            "technical_analysis": self.mock_technical_engine.analyze.return_value,
            "news_analysis": {"news": "result"}
        })
        self.mock_prompt_builder.build_prompt.assert_called_once_with({
            "decision": "data"
        })
        self.mock_ai_provider.send_prompt.assert_called_once_with("test prompt")
        
        # Verify the final result
        self.assertEqual(result, self.expected_signal)
    
    def test_empty_input_handling(self):
        """Test pipeline behavior with empty input data."""
        result = self.pipeline.run_pipeline(self.company, [], [])
        self.assertIsInstance(result, AISignal)


if __name__ == '__main__':
    unittest.main()
