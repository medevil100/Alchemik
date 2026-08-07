"""End-to-end test for MasterEngine with real engines — no engine mocks."""

import unittest
from datetime import datetime, timedelta

from engines.master.engine import MasterEngine
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.news.filter import NewsFilterConfig
from engines.ai import DecisionEngine
from engines.hunter import HunterEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.analyst import AnalystEngine
from engines.composer.engine import ComposerEngine
from engines.quality.engine import QualityEngine
from data.models import MarketData, FinalAnalysisResult


HUNTER_CONFIG = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.5,
    "max_risk_score": 0.7,
    "min_confidence": 0.6,
    "max_results": 10,
    "priority_thresholds": [0.9, 0.7, 0.5],
}


class TestMasterEngineE2E(unittest.TestCase):
    """Full pipeline with zero engine mocks."""

    def setUp(self):
        news_config = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        self.master_engine = MasterEngine(
            technical_engine=TechnicalEngine(),
            news_engine=NewsPipeline(news_config),
            ai_engine=DecisionEngine(),
            ranking_engine=RankingEngine(),
            risk_engine=RiskEngine(),
            hunter_engine=HunterEngine(HUNTER_CONFIG),
            analyst_engine=AnalystEngine(),
            composer_engine=ComposerEngine(),
            quality_engine=QualityEngine(),
        )

    def test_full_pipeline_flow(self):
        """Real MasterEngine with ≥35 candles for MACD slow(26)+signal(9)."""
        symbol = "TST"
        ohlcv_data = [
            MarketData(open=100.0, high=101.0, low=99.5, close=100.5,
                       volume=500_000,
                       timestamp=datetime(2026, 1, 1) + timedelta(days=d))
            for d in range(35)
        ]
        result = self.master_engine.run_analysis(symbol, ohlcv_data=ohlcv_data)
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, symbol)
        self.assertTrue(0.0 <= result.final_rating <= 1.0)
        self.assertIsInstance(result.recommendation, str)
        self.assertIsNotNone(result.generated_at)

    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):
            self.master_engine.run_analysis("")

    def test_no_ohlcv_returns_result(self):
        result = self.master_engine.run_analysis("TST")
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, "TST")


if __name__ == "__main__":
    unittest.main()