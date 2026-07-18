import unittest
from datetime import datetime

from data.models.ai_signal import AISignal
from data.models.analysis_result import AnalysisResult
from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem
from data.models.ranking_result import RankingResult
from data.models.full_ranking import FullRanking
from engines.risk.engine import RiskEngine, RiskResult

class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RiskEngine()
        
        # Mock data
        self.company = CompanyInfo(symbol="TEST", name="Test Company")
        self.market_data = [MarketData(open=100, high=105, low=95, close=102, volume=1000, timestamp=datetime.now())]
        self.news = [NewsItem(
            title="Test News",
            source="Test Source",
            publish_date=datetime.now(),
            url="https://example.com"
        )]
        self.signals = [AISignal(
            signal_type="buy",
            confidence=0.8,
            generated_at=datetime.now(),
            reasoning="Test reasoning"
        )]
        self.analysis_result = AnalysisResult(
            company=self.company,
            market_data=self.market_data,
            news=self.news,
            signals=self.signals,
            generated_at=datetime.now()
        )
        self.ranking_result = FullRanking(
            results=[RankingResult(instrument_id="TEST", score=0.7, details={})],
            timestamp=datetime.now().isoformat()
        )
    
    def test_risk_assessment(self):
        result = self.engine.assess_risk(self.analysis_result, self.ranking_result)
        self.assertIsInstance(result, RiskResult)
        self.assertEqual(result.instrument_id, "TEST")
        self.assertTrue(0.0 <= result.risk_score <= 1.0)
        self.assertIn(result.risk_level, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    
    def test_risk_score_range(self):
        # Test edge cases
        result = self.engine.assess_risk(self.analysis_result, self.ranking_result)
        self.assertTrue(0.0 <= result.risk_score <= 1.0)
    
    def test_risk_level_assignment(self):
        # Test all threshold boundaries
        test_cases = [
            (0.1, "LOW"),
            (0.3, "MEDIUM"),
            (0.6, "HIGH"),
            (0.8, "CRITICAL")
        ]
        for score, expected in test_cases:
            with self.subTest(score=score):
                # Override _calculate_risk_score to return fixed value
                original_method = self.engine._calculate_risk_score
                self.engine._calculate_risk_score = lambda *_: score
                result = self.engine.assess_risk(self.analysis_result, self.ranking_result)
                self.assertEqual(result.risk_level, expected)
                self.engine._calculate_risk_score = original_method
    
    def test_position_size_calculation(self):
        # Test position size decreases with higher risk
        low_risk_result = RiskResult(
            instrument_id="TEST",
            risk_score=0.1,
            risk_level="LOW",
            confidence=0.9,
            risk_factors=[],
            max_position_size=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            timestamp=datetime.now()
        )
        high_risk_result = RiskResult(
            instrument_id="TEST",
            risk_score=0.9,
            risk_level="CRITICAL",
            confidence=0.9,
            risk_factors=[],
            max_position_size=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            timestamp=datetime.now()
        )
        low_size = self.engine._calculate_position_size(low_risk_result.risk_score)
        high_size = self.engine._calculate_position_size(high_risk_result.risk_score)
        self.assertLess(high_size, low_size)
    
    def test_import(self):
        # Test public import
        from engines.risk import RiskEngine
        self.assertIsNotNone(RiskEngine)

if __name__ == "__main__":
    unittest.main()