"""
Tests for the Ranking Engine.
"""
import unittest
from datetime import datetime
from engines.ranking import RankingEngine
from data.models.analysis_result import AnalysisResult
from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem
from data.models.ai_signal import AISignal

class TestRankingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RankingEngine()
        
    def test_empty_input(self):
        """Test handling of empty input list."""
        result = self.engine.calculate_ranking([])
        self.assertEqual(len(result.results), 0)
        
    def test_basic_ranking(self):
        """Test basic ranking functionality."""
        # Create mock analysis results
        results = [
            AnalysisResult(
                company=CompanyInfo(name="Company 1", symbol="INST1"),
                market_data=[MarketData(
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                    volume=1000.0,
                    timestamp=datetime.now()
                )],
                news=[NewsItem(
                    title="Test News 1",
                    source="Test Source",
                    publish_date=datetime.now(),
                    url="https://example.com/news1",
                    sentiment=0.6
                )],
                signals=[AISignal(
                    signal_type="hold",
                    confidence=0.7,
                    generated_at=datetime.now()
                )],
                generated_at="2026-07-13T12:00:00Z"
            ),
            AnalysisResult(
                company=CompanyInfo(name="Company 2", symbol="INST2"),
                market_data=[MarketData(
                    open=90.0,
                    high=90.0,
                    low=90.0,
                    close=90.0,
                    volume=1000.0,
                    timestamp=datetime.now()
                )],
                news=[NewsItem(
                    title="Test News 2",
                    source="Test Source",
                    publish_date=datetime.now(),
                    url="https://example.com/news2",
                    sentiment=0.9
                )],
                signals=[AISignal(
                    signal_type="hold",
                    confidence=0.5,
                    generated_at=datetime.now()
                )],
                generated_at="2026-07-13T12:00:00Z"
            )
        ]
        
        ranking = self.engine.calculate_ranking(results)
        
        # Should have 2 results
        self.assertEqual(len(ranking.results), 2)
        
        # Should be sorted highest to lowest
        self.assertGreater(ranking.results[0].score, ranking.results[1].score)
        
        # First should be INST1 (1.0*0.4 + 0.6*0.3 + 0.7*0.3 = 0.79)
        self.assertEqual(ranking.results[0].instrument_id, "INST1")
        self.assertAlmostEqual(ranking.results[0].score, 0.79)
        
    def test_missing_data(self):
        """Test handling of missing data components."""
        results = [
            AnalysisResult(
                company=CompanyInfo(name="Company 1", symbol="INST1"),
                market_data=[MarketData(
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                    volume=1000.0,
                    timestamp=datetime.now()
                )],
                news=[],
                signals=[AISignal(
                    signal_type="hold",
                    confidence=0.7,
                    generated_at=datetime.now()
                )],
                generated_at="2026-07-13T12:00:00Z"
            )
        ]
        
        ranking = self.engine.calculate_ranking(results)
        
        # Should still calculate score (1.0*0.4 + 0.7*0.3 = 0.61)
        self.assertEqual(ranking.results[0].instrument_id, "INST1")
        self.assertAlmostEqual(ranking.results[0].score, 0.61)

if __name__ == "__main__":
    unittest.main()