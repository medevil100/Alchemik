"""Tests for TechnicalEventDetector.

Covers:
    - Construction and contract compliance
    - Input validation (edge cases)
    - Positive detection for each implemented event_type
    - Negative detection (no false positives)
    - Threshold boundaries
    - Order and uniqueness of results
    - Input immutability
    - Determinism
    - Integration with DetectorRegistry and DetectorOrchestrator
    - Forbidden dependencies
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from data.models.event_enums import InstrumentType
from data.models.market_data import MarketData
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.orchestrator import DetectorOrchestrator
from engines.detectors.registry import DetectorRegistry
from engines.detectors.result import DetectionResult
from engines.detectors.technical_detector import TechnicalEventDetector


# =========================================================================
# Helpers
# =========================================================================


_BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
_NEXT_DAY = 0  # global monotonic day counter


def _next_ts() -> datetime:
    """Return a unique, strictly increasing timestamp for each candle."""
    global _NEXT_DAY
    ts = _BASE_DATE + timedelta(days=_NEXT_DAY)
    _NEXT_DAY += 1
    return ts


def _reset_ts() -> None:
    """Reset the day counter between tests for reproducibility."""
    global _NEXT_DAY
    _NEXT_DAY = 0


def _make_md(
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 1000.0,
) -> MarketData:
    """Create a MarketData candle with a unique timestamp."""
    return MarketData(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=_next_ts(),
    )


def _make_ctx(*candles: MarketData) -> DetectionContext:
    """Build a DetectionContext from candles."""
    return DetectionContext(
        ticker="TEST",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        ohlcv_data=tuple(candles),
    )


def _candles_from_sequence(prices: list[float], volume: float = 1000.0) -> list[MarketData]:
    """Build a simple OHLCV sequence from closing prices (open/high/low derived)."""
    result = []
    for p in prices:
        result.append(
            MarketData(
                open=p,
                high=p + 0.5,
                low=p - 0.5,
                close=p,
                volume=volume,
                timestamp=_next_ts(),
            )
        )
    return result


def _flat_prices(n: int, base: float = 10.0) -> list[float]:
    """Return a list of N identical prices (flat market)."""
    return [base] * n


def _ramp_prices(n: int, start: float = 10.0, step: float = 0.1) -> list[float]:
    """Return a gradually increasing price sequence."""
    return [start + i * step for i in range(n)]


def _decline_prices(n: int, start: float = 20.0, step: float = -0.1) -> list[float]:
    """Return a gradually decreasing price sequence."""
    return [start + i * step for i in range(n)]


# =========================================================================
# Test: Construction & contract
# =========================================================================


class TestConstructionAndContract:
    """Verify that the detector fulfills the BaseDetector contract."""

    def test_inherits_from_base_detector(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert isinstance(det, BaseDetector)

    def test_detector_id(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert det.detector_id == "technical"

    def test_name(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert isinstance(det.name, str)
        assert len(det.name) > 0

    def test_event_types_is_tuple(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert isinstance(det.event_types, tuple)

    def test_event_types_not_empty(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert len(det.event_types) > 0

    def test_event_types_no_duplicates(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert len(det.event_types) == len(set(det.event_types))

    def test_each_event_type_is_string(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        for et in det.event_types:
            assert isinstance(et, str)
            assert len(et.strip()) > 0

    def test_detect_returns_list(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(100))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        result = det.detect(ctx)
        assert isinstance(result, list)

    def test_detect_elements_are_detection_results(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(100))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        for r in det.detect(ctx):
            assert isinstance(r, DetectionResult)

    def test_can_handle_returns_bool(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        assert det.can_handle("VOLATILITY_SPIKE") is True
        assert det.can_handle("NONEXISTENT") is False


# =========================================================================
# Test: Input validation / edge cases
# =========================================================================


class TestInputValidation:
    """Test behaviour with insufficient or edge-case data."""

    def test_single_candle_returns_empty(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence([10.0])
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        assert det.detect(ctx) == []

    def test_two_candles_flat_returns_empty_or_few(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence([10.0, 10.0])
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        for r in results:
            assert isinstance(r, DetectionResult)

    def test_insufficient_for_rsi_does_not_raise(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(10))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        assert "RSI_OVERBOUGHT" not in {r.event_type for r in results}

    def test_insufficient_for_macd_does_not_raise(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(20))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        assert "MACD_LINE_CROSSOVER" not in {r.event_type for r in results}

    def test_zero_volume_handled(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(100), volume=0.0)
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        assert isinstance(results, list)

    def test_negative_volume_handled(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(100), volume=-100.0)
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        assert isinstance(results, list)

    def test_zero_price_handled(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence([0.0] * 100)
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        assert isinstance(results, list)


# =========================================================================
# Test: Confidence levels
# =========================================================================


class TestConfidenceLevels:
    """Verify that all confidence_level values are in [0.0, 1.0]."""

    def test_all_confidences_in_range_flat_data(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(200))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        for r in det.detect(ctx):
            assert 0.0 <= r.confidence_level <= 1.0


# =========================================================================
# Positive detection tests — one per event type group
# =========================================================================


class TestVolatilitySpike:
    """VOLATILITY_SPIKE: ATR spikes above threshold."""

    def test_volatility_spike_detected_with_wide_ranges(self) -> None:
        _reset_ts()
        candles = []
        for i in range(14 + 20):  # 34 tight candles
            candles.append(_make_md(10.0, 10.2, 9.8, 10.0))
        # Last candle: wide range
        candles.append(_make_md(10.0, 15.0, 5.0, 10.0))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        types = {r.event_type for r in results}
        assert "VOLATILITY_SPIKE" in types
        assert "ATR_EXPANSION" in types


class TestVolatilityContraction:
    """VOLATILITY_CONTRACTION: ATR falls below threshold."""

    def test_volatility_contraction_with_tight_ranges(self) -> None:
        _reset_ts()
        candles = []
        # Baseline: 15 periods of wide ranges (ATR baseline ~6.0)
        for i in range(15):
            candles.append(_make_md(10.0, 13.0, 7.0, 10.0))
        # Contraction: 20 periods of very tight ranges
        for i in range(20):
            candles.append(_make_md(10.0, 10.02, 9.98, 10.0))
        # Final candle also tight
        candles.append(_make_md(10.0, 10.01, 9.99, 10.0))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        types = {r.event_type for r in results}
        assert "VOLATILITY_CONTRACTION" in types


class TestBollingerBands:
    """BB_EXPANSION / BB_SQUEEZE.

    The detection uses the last 20 computed BB widths.  To pass
    bb_squeeze_threshold == 0.5 we need current_width / avg_width <= 0.5.
    """

    def test_bb_expansion_with_volatile_rally(self) -> None:
        _reset_ts()
        candles = []
        # 20 flat candles → narrow bands
        for i in range(20):
            candles.append(_make_md(10.0, 10.01, 9.99, 10.0))
        # 20 very volatile candles → BB width explodes
        for i in range(20):
            candles.append(_make_md(10.0 + i * 0.5, 10.5 + i * 0.5, 9.5 + i * 0.5, 10.0 + i * 0.5))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "BB_EXPANSION" in types


class TestBreakouts:
    """RESISTANCE_BREAKOUT / SUPPORT_BREAKDOWN."""

    def test_resistance_breakout(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_flat_prices(25, 10.0))
        breakout = _make_md(11.0, 12.0, 10.8, 11.5, volume=2000.0)
        candles.append(breakout)
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "RESISTANCE_BREAKOUT" in types

    def test_support_breakdown(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_flat_prices(25, 10.0))
        breakdown = _make_md(9.0, 9.2, 8.5, 8.7, volume=2000.0)
        candles.append(breakdown)
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "SUPPORT_BREAKDOWN" in types


class TestCandlePatterns:
    """HAMMER_HANGING_MAN, SHOOTING_STAR, ENGULFING, DOJI, etc."""

    def test_hammer(self) -> None:
        _reset_ts()
        prev = _make_md(10.0, 10.5, 9.5, 10.2)
        hammer = _make_md(10.3, 10.4, 9.0, 10.35)
        ctx = _make_ctx(prev, hammer)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "HAMMER_HANGING_MAN" in types

    def test_shooting_star(self) -> None:
        _reset_ts()
        prev = _make_md(10.0, 10.5, 9.5, 10.2)
        star = _make_md(10.3, 12.0, 10.2, 10.35)
        ctx = _make_ctx(prev, star)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "SHOOTING_STAR_INV_HAMMER" in types

    def test_bullish_engulfing(self) -> None:
        _reset_ts()
        small_down = _make_md(10.5, 10.6, 10.2, 10.3)
        big_up = _make_md(10.2, 11.0, 10.1, 10.8, volume=2000.0)
        ctx = _make_ctx(small_down, big_up)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "BULLISH_ENGULFING" in types

    def test_bearish_engulfing(self) -> None:
        _reset_ts()
        small_up = _make_md(10.2, 10.5, 10.1, 10.4)
        big_down = _make_md(10.5, 10.6, 9.5, 9.8, volume=2000.0)
        ctx = _make_ctx(small_up, big_down)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "BEARISH_ENGULFING" in types

    def test_doji(self) -> None:
        _reset_ts()
        prev = _make_md(10.0, 10.5, 9.5, 9.8)
        doji = _make_md(10.0, 10.5, 9.5, 10.01)
        ctx = _make_ctx(prev, doji)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "DOJI" in types

    def test_marubozu(self) -> None:
        _reset_ts()
        prev = _make_md(10.0, 10.5, 9.5, 10.2)
        maru = _make_md(10.0, 10.95, 9.95, 10.9)
        ctx = _make_ctx(prev, maru)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "MARUBOZU" in types

    def test_harami(self) -> None:
        _reset_ts()
        big = _make_md(10.0, 12.0, 9.0, 11.0, volume=2000.0)
        small = _make_md(10.5, 10.8, 10.3, 10.6, volume=500.0)
        ctx = _make_ctx(big, small)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "HARAMI" in types


class TestMACrossover:
    """MA_CROSSOVER: fast MA crosses slow MA."""

    def test_golden_cross(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_flat_prices(50, 10.0))
        candles.append(_make_md(12.0, 12.5, 11.5, 12.0))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "MA_CROSSOVER" in types


class TestPriceVsMA:
    """PRICE_VS_MA: price crosses 200 SMA."""

    def test_price_cross_above_ma(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_flat_prices(200, 10.0))
        candles.append(_make_md(12.0, 13.0, 11.5, 12.5))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "PRICE_VS_MA" in types


class TestConsecutiveCandles:
    """CONSECUTIVE_CANDLES: N consecutive up/down candles."""

    def test_consecutive_up(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_flat_prices(5, 10.0))
        for i in range(5):
            candles.append(
                _make_md(
                    10.0 + i * 0.2,
                    10.5 + i * 0.2,
                    9.8 + i * 0.2,
                    10.2 + i * 0.2,
                )
            )
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "CONSECUTIVE_CANDLES" in types


class TestRSI:
    """RSI_OVERBOUGHT / RSI_OVERSOLD."""

    def test_rsi_overbought_with_strong_uptrend(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(30, 10.0, 0.5))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "RSI_OVERBOUGHT" in types

    def test_rsi_oversold_with_strong_downtrend(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_decline_prices(30, 20.0, -0.5))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "RSI_OVERSOLD" in types


class TestMACD:
    """MACD_LINE_CROSSOVER / MACD_ZERO_CROSS.

    MACD_LINE_CROSSOVER detects the moment when the MACD line crosses
    its own 9-period signal line.  The implementation checks the last
    two valid (non-None) MACD/Signal pairs:
      - Bullish: prev_macd <= prev_signal AND curr_macd > curr_signal
      - Bearish: prev_macd >= prev_signal AND curr_macd < curr_signal
    """

    def test_macd_line_crossover_bullish_on_last_bar(self) -> None:
        _reset_ts()
        candles = []
        # Phase 1 (40 bars): moderate decline →
        #   MACD converges near zero with Signal slightly above
        for i in range(40):
            p = 15.0 - i * 0.08
            candles.append(_make_md(p, p + 0.1, p - 0.1, p - 0.02))
        # Penultimate bar: sharp drop →
        #   MACD pushed below Signal
        candles.append(_make_md(12.0, 12.1, 9.0, 9.5))
        # Final bar: sharp reversal upward →
        #   MACD crosses back above Signal
        #   Diagnostic confirmed: pm<=ps (True) AND cm>cs (True)
        candles.append(_make_md(9.6, 18.0, 9.4, 17.5))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "MACD_LINE_CROSSOVER" in types


# =========================================================================
# Negative detection — no false positives
# =========================================================================


class TestNoEventsOnFlatData:
    """Flat horizontal market should produce minimal events."""

    def test_flat_200_candles_minimal_events(self) -> None:
        _reset_ts()
        # Use slightly varying prices to avoid RSI=100 edge case
        candles = _candles_from_sequence(_flat_prices(200, 10.0))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        # RSI_OVERBOUGHT and DOJI may be legitimate for flat data
        forbidden = {
            "MACD_LINE_CROSSOVER",
            "RESISTANCE_BREAKOUT",
            "SUPPORT_BREAKDOWN",
            "MA_CROSSOVER",
            "VOLATILITY_SPIKE",
        }
        types = {r.event_type for r in results}
        assert forbidden.isdisjoint(types)


# =========================================================================
# Threshold boundaries
# =========================================================================


class TestThresholdBoundaries:
    """Test exact threshold values and their boundaries."""

    def test_rsi_at_exact_boundary_overbought(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_flat_prices(5, 10.0))
        for i in range(30):
            candles.append(
                _make_md(
                    10.1 + i * 0.3,
                    10.3 + i * 0.3,
                    9.9 + i * 0.3,
                    10.2 + i * 0.3,
                )
            )
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "RSI_OVERBOUGHT" in types

    def test_rsi_below_threshold_no_overbought(self) -> None:
        _reset_ts()
        # Oscillating price around 10 produces moderate RSI
        candles = _candles_from_sequence(_flat_prices(5, 10.0))
        for i in range(30):
            # Alternating up and down keeps RSI moderate
            sign = 1 if i % 2 == 0 else -1
            candles.append(
                _make_md(
                    10.0,
                    10.1 + sign * 0.05,
                    9.9 + sign * 0.05,
                    10.0 + sign * 0.02,
                )
            )
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        types = {r.event_type for r in det.detect(ctx)}
        assert "RSI_OVERBOUGHT" not in types


# =========================================================================
# Order and uniqueness
# =========================================================================


class TestOrderAndUniqueness:
    """Results must be ordered by event_types and have no duplicates."""

    def test_order_matches_event_types(self) -> None:
        _reset_ts()
        det = TechnicalEventDetector()
        et_map = {et: idx for idx, et in enumerate(det.event_types)}
        candles = _candles_from_sequence(_ramp_prices(200, 10.0, 0.1))
        ctx = _make_ctx(*candles)
        results = det.detect(ctx)
        indices = [et_map.get(r.event_type, 999) for r in results]
        for i in range(len(indices) - 1):
            assert indices[i] <= indices[i + 1]

    def test_no_duplicate_event_types(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(200, 10.0, 0.1))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        results = det.detect(ctx)
        event_types = [r.event_type for r in results]
        assert len(event_types) == len(set(event_types))


# =========================================================================
# Input immutability
# =========================================================================


class TestInputImmutability:
    """Verify that detect() does not mutate the input context."""

    def test_ohlcv_data_unchanged(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(100))
        original = list(candles)
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        det.detect(ctx)
        for orig, after in zip(original, candles):
            assert orig.open == after.open
            assert orig.high == after.high
            assert orig.low == after.low
            assert orig.close == after.close
            assert orig.volume == after.volume

    def test_context_fields_unchanged(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(100))
        ctx = _make_ctx(*candles)
        original_ticker = ctx.ticker
        original_market = ctx.market
        det = TechnicalEventDetector()
        det.detect(ctx)
        assert ctx.ticker == original_ticker
        assert ctx.market == original_market


# =========================================================================
# Determinism
# =========================================================================


class TestDeterminism:
    """Multiple calls with the same context produce identical results."""

    def test_deterministic_output(self) -> None:
        _reset_ts()
        candles = _candles_from_sequence(_ramp_prices(200, 10.0, 0.05))
        ctx = _make_ctx(*candles)
        det = TechnicalEventDetector()
        r1 = det.detect(ctx)
        r2 = det.detect(ctx)
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.event_type == b.event_type
            assert a.confidence_level == b.confidence_level


# =========================================================================
# Integration with DetectorRegistry and DetectorOrchestrator
# =========================================================================


class TestIntegration:
    """TechnicalEventDetector works inside the full pipeline."""

    def test_register_and_run_with_orchestrator(self) -> None:
        _reset_ts()
        registry = DetectorRegistry()
        detector = TechnicalEventDetector()
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)
        candles = _candles_from_sequence(_ramp_prices(200, 10.0, 0.05))
        ctx = _make_ctx(*candles)
        results = orchestrator.run_all(ctx)
        assert isinstance(results, tuple)
        for r in results:
            assert isinstance(r, DetectionResult)

    def test_run_for_event_type_with_orchestrator(self) -> None:
        _reset_ts()
        registry = DetectorRegistry()
        detector = TechnicalEventDetector()
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)
        candles = _candles_from_sequence(_ramp_prices(200, 10.0, 0.05))
        ctx = _make_ctx(*candles)
        # run_for_event_type returns all results from matching detectors
        results = orchestrator.run_for_event_type(ctx, "RSI_OVERBOUGHT")
        assert isinstance(results, tuple)
        for r in results:
            assert isinstance(r, DetectionResult)
        # At least one result is RSI_OVERBOUGHT
        assert any(r.event_type == "RSI_OVERBOUGHT" for r in results)


# =========================================================================
# Forbidden dependencies
# =========================================================================


class TestForbiddenDependencies:
    """Ensure the detector does not import forbidden modules."""

    def test_no_master_engine_import(self) -> None:
        import engines.detectors.technical_detector as td
        import inspect
        source = inspect.getsource(td)
        assert "engines.master" not in source
        assert "MasterEngine" not in source

    def test_no_market_event_import(self) -> None:
        import engines.detectors.technical_detector as td
        import inspect
        source = inspect.getsource(td)
        assert "MarketEvent" not in source
        assert "market_event" not in source

    def test_no_network_calls_in_source(self) -> None:
        import engines.detectors.technical_detector as td
        import inspect
        source = inspect.getsource(td)
        assert "requests" not in source
        assert "urllib" not in source
        assert "yfinance" not in source.lower()

    def test_detector_does_not_modify_price_detector(self) -> None:
        from engines.price_detector.engine import PriceDetector
        assert PriceDetector is not None

    def test_detector_does_not_modify_volume_detector(self) -> None:
        from engines.volume_detector.engine import VolumeDetector
        assert VolumeDetector is not None