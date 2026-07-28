import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from engines.master import MasterEngine
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.ai import DecisionEngine
from engines.hunter import HunterEngine
from data.models import MarketData, NewsItem, AISignal, FinalAnalysisResult

class TestMasterEngineE2E(unittest.TestCase):
    def setUp(self):
        # Mock TechnicalEngine — return an object with market_data attribute
        self.mock_technical_engine = MagicMock(spec=TechnicalEngine)
        _ohlcv_data_e2e = [
            MarketData(
                open=100.0, high=105.0, low=95.0, close=102.0,
                volume=1000000, timestamp=datetime.now(),
            )
        ]
        self._technical_result = MagicMock()
        self._technical_result.market_data = _ohlcv_data_e2e
        self.mock_technical_engine.analyze.return_value = self._technical_result

        # Mock NewsPipeline
        self.mock_news_engine = MagicMock(spec=NewsPipeline)
        self.mock_news_engine.process.return_value = [
            NewsItem(
                title="Test News Title",
                source="Test Source",
                publish_date=datetime.now(),
                url="https://example.com",
                summary="Test summary",
                sentiment=0.5
            )
        ]

        # Mock DecisionEngine
        self.mock_ai_engine = MagicMock(spec=DecisionEngine)
        self.mock_ai_engine.process_data.return_value = AISignal(
            signal_type="buy",
            confidence=0.8,
            generated_at=datetime.now(),
            reasoning="Strong technical and news signals."
        )

        # Mock HunterEngine
        self.mock_hunter_engine = MagicMock(spec=HunterEngine)
        self.mock_hunter_engine.analyze = MagicMock(return_value=None)  # Or any mock return value

        # Mock PriceDetector and VolumeDetector (return empty — no events)
        self.mock_price_detector = MagicMock()
        self.mock_price_detector.detect.return_value = []
        self.mock_volume_detector = MagicMock()
        self.mock_volume_detector.detect.return_value = []

        # Mock RankingEngine (to avoid market_data check)
        self.mock_ranking_engine = MagicMock()
        self.mock_ranking_engine.calculate_ranking.return_value = MagicMock()
        
        # Mock RiskEngine (to avoid company check)
        self.mock_risk_engine = MagicMock()
        self.mock_risk_engine.assess_risk.return_value = MagicMock()
        
        # Mock AnalystEngine
        self.mock_analyst_engine = MagicMock()
        mock_final_result = MagicMock(spec=FinalAnalysisResult)
        mock_final_result.final_rating = 0.8  # Example rating
        mock_final_result.recommendation = "buy"
        mock_final_result.generated_at = datetime.now()
        mock_final_result.confidence_level = 0.9  # Example confidence
        mock_final_result.positive_factors = ["Strong technical signals", "Positive news sentiment"]
        mock_final_result.negative_factors = []
        mock_final_result.risk_factors = []
        mock_final_result.warnings = []
        mock_final_result.summary = "Mock summary"
        mock_final_result.symbol = "MOCK_SYMBOL"
        mock_final_result.analysis_date = datetime.now()
        mock_final_result.notes = "Mock analysis result"
        self.mock_analyst_engine.generate_analysis.return_value = mock_final_result
        
        # Initialize MasterEngine with mocks
        self.master_engine = MasterEngine(
            technical_engine=self.mock_technical_engine,
            news_engine=self.mock_news_engine,
            ai_engine=self.mock_ai_engine,
            hunter_engine=self.mock_hunter_engine,
            ranking_engine=self.mock_ranking_engine,
            risk_engine=self.mock_risk_engine,
            analyst_engine=self.mock_analyst_engine,
            price_detector=self.mock_price_detector,
            volume_detector=self.mock_volume_detector,
        )

    def test_full_pipeline_flow(self):
        # Run analysis with OHLCV data
        symbol = "MOCK_SYMBOL"
        ohlcv_data = [
            MarketData(
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000,
                timestamp=datetime.now()
            ),
            MarketData(
                open=102.0,
                high=108.0,
                low=101.0,
                close=107.0,
                volume=2000000,
                timestamp=datetime.now()
            ),
        ]
        result = self.master_engine.run_analysis(symbol, ohlcv_data=ohlcv_data)

        # Validate FinalAnalysisResult
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, symbol)
        self.assertTrue(0.0 <= result.final_rating <= 1.0)
        self.assertIn(result.recommendation, ["buy", "hold", "sell"])  # Update with valid values from config
        self.assertIsNotNone(result.generated_at)

        # Validate no real HTTP requests were made
        self.mock_technical_engine.analyze.assert_called_once()
        # News/process may not be called (no events → run_news=False)
        self.mock_ai_engine.process_data.assert_called_once()

    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis("")

if __name__ == "__main__":
    unittest.main()