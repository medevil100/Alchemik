"""Unit tests for ETFEventDetector."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from data.models.event_enums import InstrumentType
from data.models.market_data import MarketData
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.etf_detector import ETFEventDetector
from engines.detectors.registry import DetectorRegistry
from engines.detectors.orchestrator import DetectorOrchestrator


def _make_ctx():
    now = datetime.now()
    return DetectionContext(ticker="T", market="M", instrument_type=InstrumentType.STOCK_GPW,
        ohlcv_data=(MarketData(open=10, high=11, low=9, close=10.5, volume=1000000, timestamp=now - timedelta(days=1)),
                     MarketData(open=10.5, high=12, low=10, close=11, volume=1200000, timestamp=now)))


class TestETFDetector(unittest.TestCase):
    def setUp(self): self.det = ETFEventDetector()
    def test_is_base_detector(self): self.assertIsInstance(self.det, BaseDetector)
    def test_detector_id(self): self.assertEqual(self.det.detector_id, "etf")
    def test_name_non_empty(self): self.assertTrue(self.det.name)
    def test_event_types_count(self): self.assertEqual(len(self.det.event_types), 4)
    def test_can_handle(self):
        self.assertTrue(self.det.can_handle("ETF_FLOW_SPIKE"))
        self.assertFalse(self.det.can_handle("NO_SUCH"))
    def test_detect_returns_empty(self): self.assertEqual(self.det.detect(_make_ctx()), [])
    def test_registry(self):
        r = DetectorRegistry(); r.register(self.det); self.assertEqual(len(r), 1)
    def test_orchestrator(self):
        r = DetectorRegistry(); r.register(self.det); self.assertEqual(DetectorOrchestrator(r).run_all(_make_ctx()), ())

if __name__ == "__main__": unittest.main()