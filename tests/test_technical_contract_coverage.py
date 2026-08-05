"""Contract-level tests for TECHNICAL event types that lacked dedicated tests.

Every test uses the real TechnicalEventDetector, real MarketData, real
MasterEngine, and validates both the detector output and the MarketEvent contract.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from data.models.event_enums import EventFamily, InstrumentType
from data.models.market_data import MarketData
from engines.detectors.context import DetectionContext
from engines.detectors.technical_detector import TechnicalEventDetector
from engines.master.engine import (
    MasterEngine,
    _result_to_market_event,
    _build_default_registry,
)
from engines.detectors.result import DetectionResult
from engines.news.pipeline import NewsPipeline
from engines.news.filter import NewsFilterConfig
from engines.hunter.engine import HunterEngine
from engines.ranking.engine import RankingEngine
from engines.risk.engine import RiskEngine
from engines.analyst.engine import AnalystEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
_DAY = 0


def _next_ts() -> datetime:
    global _DAY
    ts = _BASE_DATE + timedelta(days=_DAY)
    _DAY += 1
    return ts


def _reset_ts() -> None:
    global _DAY
    _DAY = 0


def _md(open_: float, high: float, low: float, close: float,
        volume: float = 1000.0) -> MarketData:
    return MarketData(open=open_, high=high, low=low, close=close,
                      volume=volume, timestamp=_next_ts())


def _ctx(*candles: MarketData) -> DetectionContext:
    return DetectionContext(ticker="TST", market="GPW",
                           instrument_type=InstrumentType.STOCK_GPW,
                           ohlcv_data=tuple(candles))


HUNTER_CONFIG = {"ranking_weight": 0.4, "risk_weight": 0.3,
                 "confidence_weight": 0.3, "min_ranking_score": 0.5,
                 "max_risk_score": 0.7, "min_confidence": 0.6,
                 "max_results": 10, "priority_thresholds": [0.9, 0.7, 0.5]}


class _BaseContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.detector = TechnicalEventDetector()
        cls.registry = _build_default_registry()
        news_config = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        cls.master = MasterEngine(
            news_engine=NewsPipeline(news_config),
            hunter_engine=HunterEngine(HUNTER_CONFIG),
            ranking_engine=RankingEngine(),
            risk_engine=RiskEngine(),
            analyst_engine=AnalystEngine(),
            detector_registry=cls.registry,
        )
        cls.catalogue_family = EventFamily.TECHNICAL

    def _assert_event_in_results(self, results: list[DetectionResult],
                                 event_type: str, msg="") -> DetectionResult:
        types = {r.event_type for r in results}
        self.assertIn(event_type, types,
                      f"{event_type} not found. Detected: {sorted(types)}. {msg}")
        for r in results:
            if r.event_type == event_type:
                return r
        self.fail(f"{event_type} not findable")

    def _result_to_market_event(self, det_result):
        return _result_to_market_event(det_result, "TST", "GPW",
                                       InstrumentType.STOCK_GPW,
                                       "Technical Event Detector",
                                       self.catalogue_family)

    def _assert_market_event_contract(self, me, expected_type):
        self.assertEqual(me.ticker, "TST")
        self.assertEqual(me.market, "GPW")
        self.assertEqual(me.event_type, expected_type)
        self.assertEqual(me.event_family, EventFamily.TECHNICAL)
        self.assertIsNotNone(me.event_id)
        self.assertGreater(len(me.history), 0)
        self.assertGreaterEqual(me.confidence_level, 0.0)
        self.assertLessEqual(me.confidence_level, 1.0)

    def _run_through_master_engine(self, ohlcv, expected_type):
        events_out: list = []
        result = self.master.run_analysis("TST", "GPW",
                                          InstrumentType.STOCK_GPW,
                                          ohlcv_data=ohlcv,
                                          events_out=events_out)
        self.assertIsNotNone(result)
        types = {ev.event_type for ev in events_out}
        self.assertIn(expected_type, types,
                      f"MasterEngine did not produce {expected_type}. Got: {sorted(types)}")


# ===========================================================================
# BB_SQUEEZE — Bollinger Bands width falls below threshold (0.5)
# ===========================================================================

class TestBBSqueezeContract(_BaseContractTest):

    def test_bb_squeeze_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Phase 1: 30 wide-range candles
        for i in range(30):
            candles.append(_md(8.0, 20.0, 2.0, 10.0 + (1.0 if i % 2 == 0 else -1.0), 2000.0))
        # Phase 2: 17 tight candles — enough so the last 20 BB widths
        # contain ~3 wide + 17 tight → ratio ≈ 0.61 drops below 0.5
        # …but we need it strictly ≤ 0.5. Verify with 18 tight candles:
        for _ in range(18):
            candles.append(_md(10.0, 10.01, 9.99, 10.0, 500.0))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        r = self._assert_event_in_results(results, "BB_SQUEEZE",
                                          "Need width_ratio <= 0.5 after squeeze")
        me = self._result_to_market_event(r)
        self._assert_market_event_contract(me, "BB_SQUEEZE")
        self._run_through_master_engine(candles, "BB_SQUEEZE")


# ===========================================================================
# MORNING_EVENING_STAR (5.6) — requires ≥3 candles for detection,
# plus ≥35 background candles so that MACD's EMA(26) + signal EMA(9)
# both have enough data.
# ===========================================================================

class TestMorningEveningStarContract(_BaseContractTest):

    def test_evening_star_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Background: flat market — MasterEngine needs ≥ 26 (EMA26) +
        # ≥ 9 valid MACD values (signal EMA9 needs ≥9 valid macd values)
        # → need at least 35 total valid values → ~35 candles minimum.
        for _ in range(32):
            candles.append(_md(10.0, 10.02, 9.98, 10.0, 500.0))
        # Pattern: big up → small gap → big down (evening star)
        big_up = _md(10.0, 13.0, 9.8, 12.8, 2000.0)
        small = _md(12.9, 13.1, 12.7, 12.9, 500.0)
        big_down = _md(12.8, 13.0, 10.0, 11.0, 3000.0)
        candles.extend([big_up, small, big_down])
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        r = self._assert_event_in_results(results, "MORNING_EVENING_STAR")
        me = self._result_to_market_event(r)
        self._assert_market_event_contract(me, "MORNING_EVENING_STAR")
        self._run_through_master_engine(candles, "MORNING_EVENING_STAR")


# ===========================================================================
# THREE_WHITE_SOLDIERS (5.7)
# ===========================================================================

class TestThreeWhiteSoldiersContract(_BaseContractTest):

    def test_three_white_soldiers_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # MasterEngine needs ≥ 35 candles (EMA26 + signal EMA9)
        for _ in range(32):
            candles.append(_md(10.0, 10.02, 9.98, 10.0, 500.0))
        c1 = _md(10.0, 12.0, 9.8, 11.5)
        c2 = _md(11.0, 13.0, 10.5, 12.5)
        c3 = _md(12.0, 14.0, 11.5, 13.5)
        candles.extend([c1, c2, c3])
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        r = self._assert_event_in_results(results, "THREE_WHITE_SOLDIERS")
        me = self._result_to_market_event(r)
        self._assert_market_event_contract(me, "THREE_WHITE_SOLDIERS")
        self._run_through_master_engine(candles, "THREE_WHITE_SOLDIERS")


# ===========================================================================
# THREE_BLACK_CROWS (5.8)
# ===========================================================================

class TestThreeBlackCrowsContract(_BaseContractTest):

    def test_three_black_crows_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # MasterEngine needs ≥ 35 candles (EMA26 + signal EMA9)
        for _ in range(32):
            candles.append(_md(10.0, 10.02, 9.98, 10.0, 500.0))
        c1 = _md(20.0, 20.5, 18.0, 18.5)
        c2 = _md(19.0, 19.5, 17.0, 17.5)
        c3 = _md(18.0, 18.5, 16.0, 16.5)
        candles.extend([c1, c2, c3])
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        r = self._assert_event_in_results(results, "THREE_BLACK_CROWS")
        me = self._result_to_market_event(r)
        self._assert_market_event_contract(me, "THREE_BLACK_CROWS")
        self._run_through_master_engine(candles, "THREE_BLACK_CROWS")


# ===========================================================================
# MA_SLOPE_CHANGE (6.2) — slope of SMA(20) changes sign.
# ===========================================================================

class TestMASlopeChangeContract(_BaseContractTest):

    def test_ma_slope_change_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Rising phase: 30 candles going up (positive SMA slope)
        for i in range(30):
            p = 10.0 + i * 0.15
            candles.append(_md(p, p + 0.05, p - 0.05, p))
        # Falling phase: 8 candles dropping with step -0.35
        # 30+8=38 ≥ 35 needed for MasterEngine (EMA26 + signal EMA9)
        for i in range(8):
            p = 10.0 + 29 * 0.15 + i * -0.35
            candles.append(_md(p, p + 0.05, p - 0.05, p))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        r = self._assert_event_in_results(results, "MA_SLOPE_CHANGE",
                                          "Slope should flip positive→negative")
        me = self._result_to_market_event(r)
        self._assert_market_event_contract(me, "MA_SLOPE_CHANGE")
        self._run_through_master_engine(candles, "MA_SLOPE_CHANGE")


# ===========================================================================
# TREND_STRUCTURE_CHANGE (6.5) — swing structure reversal.
# Build descending peaks with at least 3 candles of lower highs on each side
# so _find_swings can detect swing points.
# ===========================================================================

class TestTrendStructureChangeContract(_BaseContractTest):

    def test_trend_structure_change_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Build 5 descending peaks: 22, 20, 18, 16, 14
        # Each needs 3 bars before + 3 bars after with lower highs.
        # Pattern per peak: 3 low bars → spike peak → 3 low bars.
        for i in range(5):
            peak_h = 22.0 - i * 2.0
            # 3 ascending bars before (lower than peak)
            for j in range(3):
                p = peak_h - 6.0 + j * 0.5
                candles.append(_md(p, p + 0.3, p - 0.5, p + 0.2, 500.0))
            # Peak bar
            candles.append(_md(peak_h - 1.0, peak_h, peak_h - 1.5, peak_h * 0.98, 2000.0))
            # 3 descending bars after (lower highs)
            for j in range(3):
                p = peak_h * 0.98 - j * 0.3
                candles.append(_md(p + 0.2, p + 0.3, p - 0.5, p - 0.1, 500.0))
        # Add 2 more bars with lower high to satisfy last_two_highs check
        candles.append(_md(10.0, 11.0, 9.0, 10.5, 500.0))
        candles.append(_md(9.0, 10.0, 8.0, 9.5, 500.0))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        self._assert_event_in_results(results, "TREND_STRUCTURE_CHANGE")
        for r in results:
            if r.event_type == "TREND_STRUCTURE_CHANGE":
                me = self._result_to_market_event(r)
                self._assert_market_event_contract(me, "TREND_STRUCTURE_CHANGE")
                break
        self._run_through_master_engine(candles, "TREND_STRUCTURE_CHANGE")


# ===========================================================================
# RSI_DIVERGENCE (7.3) — bearish: price higher high, RSI lower high
# ===========================================================================

class TestRSIDivergenceContract(_BaseContractTest):

    def test_rsi_divergence_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Phase 1: 10 strong up-days → RSI rises to ~85
        for i in range(10):
            p = 10.0 + i * 0.5
            candles.append(_md(p, p + 0.6, p - 0.1, p + 0.4, 2000.0))
        # Phase 2: 10 days sideways-to-down → RSI peaks then declines
        for i in range(10):
            p = 15.0 - i * 0.15
            candles.append(_md(p, p + 0.2, p - 0.4, p - 0.15, 800.0))
        # Phase 3: 15 days weak uptrend — price slowly makes new highs
        # but closes are marginal → RSI cannot recover → bearish divergence
        for i in range(15):
            p = 13.5 + i * 0.1
            candles.append(_md(p + 0.2, p + 0.3, p - 0.2, p + 0.05, 500.0))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        self._assert_event_in_results(results, "RSI_DIVERGENCE")
        for r in results:
            if r.event_type == "RSI_DIVERGENCE":
                me = self._result_to_market_event(r)
                self._assert_market_event_contract(me, "RSI_DIVERGENCE")
                break
        self._run_through_master_engine(candles, "RSI_DIVERGENCE")


# ===========================================================================
# MACD_ZERO_CROSS (7.5) — MACD line crosses through zero
# ===========================================================================

class TestMACDZeroCrossContract(_BaseContractTest):

    def test_macd_zero_cross_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Phase 1: prolonged steep decline to push MACD deeply negative
        for i in range(40):
            p = 50.0 + i * -0.4
            candles.append(_md(p, p + 0.05, p - 0.05, p, 800.0))
        # Phase 2: sharp rally → MACD crosses above zero
        for i in range(12):
            p = 50.0 + 39 * -0.4 + i * 0.7
            candles.append(_md(p, p + 0.3, p - 0.1, p, 1500.0))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        self._assert_event_in_results(results, "MACD_ZERO_CROSS")
        for r in results:
            if r.event_type == "MACD_ZERO_CROSS":
                me = self._result_to_market_event(r)
                self._assert_market_event_contract(me, "MACD_ZERO_CROSS")
                break
        self._run_through_master_engine(candles, "MACD_ZERO_CROSS")


# ===========================================================================
# OBV_DIVERGENCE (8.1) — price up, OBV down (bearish divergence).
# ===========================================================================

class TestOBVDivergenceContract(_BaseContractTest):

    def test_obv_divergence_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Build an uptrend where price rises, but OBV falls (bearish divergence).
        # Price up + OBV down requires enough down-close days in the lookback
        # so that cumulative OBV declines even as price trend is up.
        for i in range(25):
            p = 10.0 + i * 0.3
            # Up days with low volume
            candles.append(_md(p, p + 0.5, p - 0.1, p + 0.3, volume=200.0))
            # Down days with high volume → OBV drops significantly
            candles.append(_md(p + 0.5, p + 0.6, p - 0.1, p - 0.05, volume=2000.0))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        self._assert_event_in_results(results, "OBV_DIVERGENCE")
        for r in results:
            if r.event_type == "OBV_DIVERGENCE":
                me = self._result_to_market_event(r)
                self._assert_market_event_contract(me, "OBV_DIVERGENCE")
                break
        self._run_through_master_engine(candles, "OBV_DIVERGENCE")


# ===========================================================================
# ATR_EXPANSION (8.3) — already works — verified separately.
# ===========================================================================

class TestATRExpansionContract(_BaseContractTest):

    def test_atr_expansion_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        for _ in range(34):
            candles.append(_md(10.0, 10.2, 9.8, 10.0))
        candles.append(_md(10.0, 15.0, 5.0, 10.0, volume=5000.0))
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        r = self._assert_event_in_results(results, "ATR_EXPANSION",
                                          "Should emit alongside VOLATILITY_SPIKE")
        me = self._result_to_market_event(r)
        self._assert_market_event_contract(me, "ATR_EXPANSION")
        self._run_through_master_engine(candles, "ATR_EXPANSION")


# ===========================================================================
# FIBONACCI_HIT (8.4) — price touches a Fibonacci retracement level.
# ===========================================================================

class TestFibonacciHitContract(_BaseContractTest):

    def test_fibonacci_hit_detected(self) -> None:
        _reset_ts()
        candles: list[MarketData] = []
        # Build descending peaks 22→12 with clear troughs 15→5
        # so _find_swings can detect both highs and lows.
        for i in range(6):
            peak_h = 22.0 - i * 2.0
            trough_l = 15.0 - i * 2.0
            for j in range(3):
                p = trough_l + j * 0.3
                candles.append(_md(p, p + 0.3, p - 0.2, p + 0.1, 500.0))
            candles.append(_md(peak_h - 1.0, peak_h, trough_l, peak_h * 0.98, 2000.0))
            for j in range(3):
                p = peak_h * 0.98 - j * 0.5
                candles.append(_md(p + 0.2, p + 0.3, p - 0.5, p - 0.1, 500.0))
        # Last swing: high=14.0, low=4.8, diff=9.2
        # 0.5 Fibo retracement from high: 14.0 - 9.2*0.5 = 9.4
        # Tolerance: 9.2 * 1.0% = 0.092
        # Replace just the last candle so close=9.4 (hits the 0.5 level)
        last = candles[-1]
        candles[-1] = _md(9.39, 9.42, 9.37, 9.4, 600.0)
        ctx = _ctx(*candles)
        results = self.detector.detect(ctx)
        self._assert_event_in_results(results, "FIBONACCI_HIT")
        for r in results:
            if r.event_type == "FIBONACCI_HIT":
                me = self._result_to_market_event(r)
                self._assert_market_event_contract(me, "FIBONACCI_HIT")
                break
        self._run_through_master_engine(candles, "FIBONACCI_HIT")


if __name__ == "__main__":
    unittest.main()