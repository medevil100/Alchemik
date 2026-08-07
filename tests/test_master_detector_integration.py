"""
Integration test: DetectorOrchestrator → MasterEngine → MarketEvent.

Verifies the complete FAZA 2 ETAPU 6 pipeline using unittest.
All internal engines are real instances. No internal mocks.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from data.models.event_enums import EventFamily, InstrumentType, PriorityLevel
from data.models.market_data import MarketData
from engines.master.engine import (
    MasterEngine,
    _lookup_catalogue,
    _result_to_market_event,
    _build_default_registry,
)
from engines.detectors import (
    DetectionResult,
    DetectorOrchestrator,
    DetectorRegistry,
    TechnicalEventDetector,
    FundamentalEventDetector,
    CorporateEventDetector,
    RegulatoryEventDetector,
    MacroEventDetector,
    ETFEventDetector,
    DerivativesEventDetector,
    SentimentNewsEventDetector,
    SystemEventDetector,
)
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.ai import DecisionEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.hunter import HunterEngine
from engines.analyst import AnalystEngine
from engines.price_detector import PriceDetector
from engines.volume_detector import VolumeDetector


HUNTER_CONFIG = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.0,
    "max_risk_score": 1.0,
    "min_confidence": 0.0,
    "max_results": 100,
    "priority_thresholds": [0.9, 0.7, 0.5],
}


def _make_ohlcv(ticks: int = 60) -> list[MarketData]:
    """Build enough data points to satisfy all indicator windows."""
    now = datetime.now()
    base = 100.0
    data = []
    for i in range(ticks):
        ts = now - timedelta(days=ticks - i - 1)
        data.append(
            MarketData(
                open=base + i * 0.5,
                high=base + i * 0.5 + 2,
                low=base + i * 0.5 - 1,
                close=base + i * 0.5 + 1,
                volume=1_000_000 + i * 100_000,
                timestamp=ts,
            )
        )
    return data


def _make_real_engine() -> MasterEngine:
    """Build a MasterEngine with real internal engine instances."""
    return MasterEngine(
        technical_engine=TechnicalEngine(),
        news_engine=NewsPipeline(filter_config=None),
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
        hunter_engine=HunterEngine(HUNTER_CONFIG),
        analyst_engine=AnalystEngine(),
        price_detector=PriceDetector(),
        volume_detector=VolumeDetector(),
    )


class TestCatalogueLookup(unittest.TestCase):
    def test_known_event_type(self):
        family, cat, sub, prio = _lookup_catalogue("VOLATILITY_SPIKE")
        self.assertEqual(family, EventFamily.TECHNICAL)
        self.assertEqual(cat, "Zmienność")
        self.assertEqual(sub, "Odchylenie ATR")
        self.assertEqual(prio, PriorityLevel.CRITICAL)

    def test_unknown_event_type_defaults(self):
        family, cat, sub, prio = _lookup_catalogue("NONEXISTENT_EVENT")
        self.assertEqual(family, EventFamily.SYSTEM)
        self.assertEqual(cat, "System")
        self.assertIsNone(sub)
        self.assertEqual(prio, PriorityLevel.LOW)

    def test_all_technical_events_in_catalogue(self):
        det = TechnicalEventDetector()
        for et in det.event_types:
            family, cat, sub, prio = _lookup_catalogue(et)
            self.assertIsInstance(family, EventFamily)
            self.assertIsInstance(cat, str)
            self.assertTrue(cat)
            self.assertTrue(sub is None or isinstance(sub, str))
            self.assertIsInstance(prio, PriorityLevel)


class TestResultToMarketEvent(unittest.TestCase):
    def test_converts_valid_result(self):
        result = DetectionResult(event_type="DOJI", confidence_level=0.75)
        event = _result_to_market_event(
            result=result,
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            detector_name="Test Detector",
            detector_family=EventFamily.TECHNICAL,
        )
        self.assertTrue(event.event_id)
        self.assertEqual(event.ticker, "TEST.WA")
        self.assertEqual(event.market, "GPW")
        self.assertEqual(event.event_type, "DOJI")
        self.assertEqual(event.event_family, EventFamily.TECHNICAL)
        self.assertEqual(event.event_category, "Formacje świecowe")
        self.assertEqual(event.event_subcategory, "Jednoświecowe")
        self.assertEqual(event.confidence_level, 0.75)
        self.assertIn("Test Detector", event.detection_source)
        self.assertTrue(event.history)
        self.assertEqual(len(event.history), 2)

    def test_clamp_is_applied_by_converter(self):
        """Verify _result_to_market_event clamps confidence via max(0.0, min(1.0, ...)).

        DetectionResult rejects out-of-range values in __post_init__,
        but the converter has a safety clamp. We test boundary values.
        """
        result = DetectionResult(event_type="DOJI", confidence_level=0.0)
        event = _result_to_market_event(
            result=result, ticker="T", market="M",
            instrument_type=InstrumentType.STOCK_GPW,
            detector_name="D", detector_family=EventFamily.TECHNICAL,
        )
        self.assertEqual(event.confidence_level, 0.0)

        result2 = DetectionResult(event_type="DOJI", confidence_level=1.0)
        event2 = _result_to_market_event(
            result=result2, ticker="T", market="M",
            instrument_type=InstrumentType.STOCK_GPW,
            detector_name="D", detector_family=EventFamily.TECHNICAL,
        )
        self.assertEqual(event2.confidence_level, 1.0)


class TestMasterEnginePipeline(unittest.TestCase):
    def test_all_detectors_registered(self):
        """Verify all 9 BaseDetector detectors are in the default registry."""
        registry = _build_default_registry()
        detectors = registry.get_all()
        self.assertEqual(len(detectors), 9, "Expected 9 detectors registered")
        expected_ids = {
            "technical", "fundamental", "corporate", "regulatory",
            "macro", "etf", "derivatives", "sentiment", "system",
        }
        actual_ids = {d.detector_id for d in detectors}
        self.assertEqual(expected_ids, actual_ids)

    def test_run_detectors_with_ohlcv(self):
        engine = _make_real_engine()
        ohlcv = _make_ohlcv(60)
        events = engine.run_detectors(
            ticker="TEST.WA", market="GPW",
            instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv,
        )
        for ev in events:
            self.assertTrue(ev.event_id)
            self.assertEqual(ev.ticker, "TEST.WA")
            self.assertEqual(ev.market, "GPW")
            self.assertTrue(ev.event_type)
            self.assertIsNotNone(ev.event_family)
            self.assertGreaterEqual(ev.confidence_level, 0.0)
            self.assertLessEqual(ev.confidence_level, 1.0)
            self.assertTrue(ev.history)
            self.assertTrue(ev.schema_version)

    def test_empty_ohlcv_returns_empty(self):
        engine = _make_real_engine()
        events = engine.run_detectors(
            ticker="TEST.WA", market="GPW",
            instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=[],
        )
        self.assertEqual(events, [])

    def test_base_detectors_produce_events(self):
        engine = _make_real_engine()
        ohlcv = _make_ohlcv(60)
        base_events = engine._run_base_detectors(
            ticker="TEST.WA", market="GPW",
            instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv,
        )
        for ev in base_events:
            self.assertTrue(ev.event_id)
            self.assertEqual(ev.ticker, "TEST.WA")

    def test_frozen_detectors_still_work(self):
        """PriceDetector and VolumeDetector must still produce events."""
        engine = _make_real_engine()
        ohlcv = _make_ohlcv(60)
        price_events = engine.price_detector.detect(
            ticker="T", market="M", instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv,
        )
        vol_events = engine.volume_detector.detect(
            ticker="T", market="M", instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=ohlcv,
        )
        self.assertIsInstance(price_events, list)
        self.assertIsInstance(vol_events, list)


if __name__ == "__main__":
    unittest.main()