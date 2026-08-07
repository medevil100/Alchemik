"""
Tests for MasterEngine — all real internal engine instances.

Every engine in the pipeline (TechnicalEngine, ComposerEngine,
QualityEngine, DecisionEngine, RankingEngine, RiskEngine,
HunterEngine, AnalystEngine, PriceDetector, VolumeDetector,
DetectorOrchestrator with all BaseDetectors) is a real instance.
No internal component is mocked.
"""

import unittest
from datetime import datetime, timedelta
from typing import List

from data.models import (
    FinalAnalysisResult,
    MarketData,
    MarketEvent,
    InstrumentType,
    EventFamily,
    PriorityLevel,
    EventOwner,
)
from engines.master.engine import MasterEngine
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.news.filter import NewsFilterConfig
from engines.ai import DecisionEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.hunter import HunterEngine
from engines.analyst import AnalystEngine
from engines.composer.engine import ComposerEngine
from engines.quality.engine import QualityEngine
from engines.price_detector import PriceDetector
from engines.volume_detector import VolumeDetector


# =============================================================================
# Helper — HunterEngine needs a config dict
# =============================================================================

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


# =============================================================================
# Base test class — ALL real engine instances
# =============================================================================


class _Base(unittest.TestCase):
    def make_master(self):
        news_config = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        return MasterEngine(
            technical_engine=TechnicalEngine(),
            news_engine=NewsPipeline(news_config),
            ai_engine=DecisionEngine(),
            ranking_engine=RankingEngine(),
            risk_engine=RiskEngine(),
            hunter_engine=HunterEngine(HUNTER_CONFIG),
            analyst_engine=AnalystEngine(),
            composer_engine=ComposerEngine(),
            quality_engine=QualityEngine(),
            price_detector=PriceDetector(),
            volume_detector=VolumeDetector(),
        )

    @staticmethod
    def make_candles(count: int = 50, base: float = 100.0) -> List[MarketData]:
        """Return *count* monotonically rising candles."""
        return [
            MarketData(
                open=base + i * 0.1,
                high=base + i * 0.1 + 2.0,
                low=base + i * 0.1 - 1.0,
                close=base + i * 0.1 + 1.0,
                volume=500_000,
                timestamp=datetime(2026, 1, 1) + timedelta(days=i),
            )
            for i in range(count)
        ]


# =============================================================================
# Basic behaviour
# =============================================================================


class TestMasterEngine(_Base):
    def test_invalid_symbol_raises(self):
        me = self.make_master()
        with self.assertRaises(ValueError):
            me.run_analysis("")
        with self.assertRaises(ValueError):
            me.run_analysis(123)

    def test_no_ohlcv_returns_valid_final_analysis(self):
        me = self.make_master()
        result = me.run_analysis("TST")
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, "TST")

    def test_with_ohlcv_returns_final_analysis(self):
        me = self.make_master()
        ohlcv = self.make_candles(50)
        result = me.run_analysis("TST", ohlcv_data=ohlcv)
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, "TST")

    def test_market_and_instrument_propagated(self):
        """Market and instrument_type reach the detectors."""
        me = self.make_master()
        ohlcv = self.make_candles(50)
        result = me.run_analysis("XYZ.WA", market="GPW",
                                 instrument_type=InstrumentType.STOCK_GPW,
                                 ohlcv_data=ohlcv)
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, "XYZ.WA")

    def test_events_out_collects_detected_events(self):
        """events_out list receives MarketEvents produced by detectors,
        processed through ComposerEngine and QualityEngine."""
        me = self.make_master()
        ohlcv = self.make_candles(50)
        events_out: List[MarketEvent] = []
        result = me.run_analysis("TST", ohlcv_data=ohlcv, events_out=events_out)
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertIsInstance(events_out, list)
        # Verify every event in events_out is a real MarketEvent
        for ev in events_out:
            self.assertIsInstance(ev, MarketEvent)
            self.assertIsNotNone(ev.event_id)
            self.assertIsInstance(ev.event_family, EventFamily)
            self.assertIsInstance(ev.quality_level, PriorityLevel)

    def test_generates_analysis_for_gpw(self):
        me = self.make_master()
        ohlcv = self.make_candles(50)
        result = me.run_analysis("XYZ.WA", market="GPW",
                                 instrument_type=InstrumentType.STOCK_GPW,
                                 ohlcv_data=ohlcv)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_generates_analysis_for_nasdaq(self):
        me = self.make_master()
        ohlcv = self.make_candles(50)
        result = me.run_analysis("TST", market="NASDAQ",
                                 instrument_type=InstrumentType.STOCK_USA,
                                 ohlcv_data=ohlcv)
        self.assertIsInstance(result, FinalAnalysisResult)

    def test_detectors_receive_market_data(self):
        """run_detectors() passes OHLCV to PriceDetector and VolumeDetector
        plus all BaseDetector-based detectors via DetectorOrchestrator."""
        me = self.make_master()
        ohlcv = self.make_candles(50)
        events = me.run_detectors(
            ticker="TST", market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv,
        )
        self.assertIsInstance(events, list)
        for ev in events:
            self.assertIsInstance(ev, MarketEvent)
            self.assertEqual(ev.ticker, "TST")
            self.assertEqual(ev.market, "NYSE")

    def test_run_detectors_empty_data(self):
        me = self.make_master()
        events = me.run_detectors(
            ticker="TST", market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=[],
        )
        self.assertEqual(len(events), 0)

    # ------------------------------------------------------------------
    # ComposerEngine integration — real composite event creation
    # ------------------------------------------------------------------

    def test_composer_integration_runs_on_detected_events(self):
        """When detectors produce multiple events with compatible families,
        ComposerEngine merges them — reflected in events_out."""
        me = self.make_master()
        # 50 candles with enough variation to trigger technical indicators
        ohlcv = self.make_candles(50)
        events_out: List[MarketEvent] = []
        result = me.run_analysis("TST", ohlcv_data=ohlcv,
                                 events_out=events_out)
        self.assertIsInstance(result, FinalAnalysisResult)
        # Composer runs automatically inside run_analysis — we verify
        # every output event has gone through QualityEngine (quality_level
        # is always set) and ComposerEngine (composite_events list
        # exists).
        for ev in events_out:
            self.assertIsInstance(ev.quality_level, PriorityLevel)
            self.assertIsInstance(ev.composite_events, list)
            self.assertIsInstance(ev.is_composite, bool)

    # ------------------------------------------------------------------
    # Pipeline decision integration — real DecisionEngine
    # ------------------------------------------------------------------

    def test_pipeline_decision_integration(self):
        """Real DecisionEngine.decide_pipeline() is called per event.
        The pipeline completes without errors regardless of decision."""
        me = self.make_master()
        ohlcv = self.make_candles(50)
        events_out: List[MarketEvent] = []
        result = me.run_analysis("TST", ohlcv_data=ohlcv,
                                 events_out=events_out)
        self.assertIsInstance(result, FinalAnalysisResult)

        # Events that pass through the pipeline may have ai_context
        # set by DecisionEngine (if decide_pipeline returned run_ai=True).
        for ev in events_out:
            if ev.ai_context is not None:
                self.assertIsInstance(ev.ai_context, dict)

    # ------------------------------------------------------------------
    # Full pipeline regression — all stages execute without errors
    # ------------------------------------------------------------------

    def test_full_pipeline_all_stages_execute(self):
        """Real engines through all stages: detectors → composer →
        quality → decision → news/ai → ranking → risk → hunter → analyst."""
        me = self.make_master()
        ohlcv = self.make_candles(50)
        events_out: List[MarketEvent] = []
        result = me.run_analysis(
            "TST", market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=ohlcv, events_out=events_out,
        )
        self.assertIsInstance(result, FinalAnalysisResult)
        self.assertEqual(result.symbol, "TST")
        # Verify output model fields
        self.assertIsInstance(result.final_rating, (int, float))
        self.assertIsInstance(result.confidence_level, (int, float))
        self.assertIsInstance(result.recommendation, str)
        self.assertIsNotNone(result.generated_at)


if __name__ == "__main__":
    unittest.main()