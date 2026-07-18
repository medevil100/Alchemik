import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from engines.master.engine import MasterEngine
from data.models import (
    FinalAnalysisResult,
    MarketData,
    Company as CompanyInfo,
    NewsItem,
    AISignal,
    RankingResult,
    RiskResult,
    HunterResult,
    AnalysisResult
)

class TestMasterEngine(unittest.TestCase):
    def setUp(self):
        # Mock all dependencies
        self.mock_technical_engine = Mock()
        self.mock_news_engine = Mock()
        self.mock_ai_engine = Mock()
        self.mock_ranking_engine = Mock()
        self.mock_risk_engine = Mock()
        self.mock_hunter_engine = Mock()
        self.mock_analyst_engine = Mock()

        # Configure mock returns
        self.market_data = MarketData(
            open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000, timestamp=1234567890
        )
        self.news_item = NewsItem(
            title="Test News",
            source="Test Source",
            publish_date=datetime.fromisoformat("2023-01-01"),
            url="http://example.com",
            summary="Test Content",
            sentiment=0.5
        )
        self.mock_technical_engine.analyze.return_value = self.market_data
        self.mock_news_engine.process.return_value = [self.news_item]
        self.mock_ai_engine.decide.return_value = AISignal(
            signal_type="BUY",
            confidence=0.9,
            generated_at=datetime.now(),
            reasoning="Test"
        )
        self.mock_ranking_engine.rank.return_value = RankingResult(
            instrument_id="TEST",
            score=0.95,
            details={}
        )
        self.mock_risk_engine.assess.return_value = RiskResult(
            instrument_id="TEST",
            risk_level="LOW",
            risk_score=0.2,
            confidence=0.9,
            risk_factors=[],
            max_position_size=1000.0,
            stop_loss=95.0,
            take_profit=110.0,
            timestamp=datetime.now()
        )
        self.mock_hunter_engine.hunt.return_value = HunterResult(
            instrument_id="TEST",
            hunter_score=0.9,
            priority=1,
            ranking_score=0.95,
            risk_score=0.2,
            risk_level="LOW",
            confidence=0.9,
            reasons=[],
            warnings=[],
            timestamp=datetime.now()
        )
        self.mock_analyst_engine.analyze.return_value = AnalysisResult(
            company=CompanyInfo(
                symbol="TEST",
                name="Test Company",
                sector="Test Sector"
            ),
            market_data=[self.market_data],
            news=[self.news_item],
            signals=[AISignal(
                signal_type="BUY",
                confidence=0.9,
                generated_at=datetime.now(),
                reasoning="Test"
            )],
            generated_at=datetime.now()
        )

        # Initialize MasterEngine with mocked dependencies
        self.master_engine = MasterEngine(
            technical_engine=self.mock_technical_engine,
            news_engine=self.mock_news_engine,
            ai_engine=self.mock_ai_engine,
            ranking_engine=self.mock_ranking_engine,
            risk_engine=self.mock_risk_engine,
            hunter_engine=self.mock_hunter_engine,
            analyst_engine=self.mock_analyst_engine
        )

    def test_run_analysis_sequence(self):
        symbol = "TEST"
        result = self.master_engine.run_analysis(symbol)

        # Verify each dependency was called exactly once
        self.mock_technical_engine.analyze.assert_called_once_with([symbol])
        self.mock_news_engine.process.assert_called_once_with([symbol])
        self.mock_ai_engine.process_data.assert_called_once_with({"symbol": symbol, "technical": self.market_data, "news": [self.news_item]})
        self.mock_ranking_engine.calculate_ranking.assert_called_once_with([self.mock_ai_engine.process_data.return_value])
        self.mock_risk_engine.assess_risk.assert_called_once_with(self.mock_ai_engine.process_data.return_value, self.mock_ranking_engine.calculate_ranking.return_value)
        self.mock_hunter_engine.scan.assert_called_once_with([{"symbol": symbol, "risk": self.mock_risk_engine.assess_risk.return_value, "ranking": self.mock_ranking_engine.calculate_ranking.return_value}])
        self.mock_analyst_engine.generate_analysis.assert_called_once_with(self.mock_hunter_engine.scan.return_value)

        # Verify the result is a FinalAnalysisResult
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis("")
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis(123)

    def test_error_handling(self):
        # Simulate an error in one of the engines
        self.mock_technical_engine.analyze.side_effect = Exception("Technical Engine Error")
        with self.assertRaises(Exception) as context:
            self.master_engine.run_analysis("TEST")
        self.assertIn("Technical Engine Error", str(context.exception))

if __name__ == "__main__":
    unittest.main()