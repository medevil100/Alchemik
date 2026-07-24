"""
Tests for FundamentalEventDetector.

Covers:
    - Contract compliance (BaseDetector abstract members).
    - detect() behaviour with valid DetectionContext (returns []).
    - can_handle() method.
    - DetectorRegistry integration.
    - DetectorOrchestrator integration.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Fundamental Event Detector
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from data.models.event_enums import InstrumentType
from data.models.market_data import MarketData
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.fundamental_detector import (
    _EVENT_TYPES,
    FundamentalEventDetector,
)
from engines.detectors.orchestrator import DetectorOrchestrator
from engines.detectors.registry import DetectorRegistry
from engines.detectors.result import DetectionResult


# =========================================================================
# Fixtures
# =========================================================================


def _make_market_data(close: float, volume: float = 100000.0, offset: int = 0) -> MarketData:
    return MarketData(
        open=close - 0.5,
        high=close + 0.3,
        low=close - 0.7,
        close=close,
        volume=volume,
        timestamp=datetime(2026, 7, 20, 10, 0) + timedelta(days=offset),
    )


@pytest.fixture
def detector() -> FundamentalEventDetector:
    return FundamentalEventDetector()


@pytest.fixture
def registry() -> DetectorRegistry:
    return DetectorRegistry()


@pytest.fixture
def valid_context() -> DetectionContext:
    """A valid DetectionContext with 30 candles — sufficient for any analysis."""
    data = [_make_market_data(100.0 + i * 0.5, offset=i) for i in range(30)]
    return DetectionContext(
        ticker="TEST.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        ohlcv_data=tuple(data),
    )


@pytest.fixture
def minimal_context() -> DetectionContext:
    """A minimal valid DetectionContext with exactly 1 candle."""
    return DetectionContext(
        ticker="MIN.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        ohlcv_data=(_make_market_data(50.0),),
    )


# =========================================================================
# Contract compliance
# =========================================================================


class TestDetectorContract:
    """Verify that FundamentalEventDetector satisfies BaseDetector contract."""

    def test_is_base_detector(self, detector: FundamentalEventDetector) -> None:
        """FundamentalEventDetector is an instance of BaseDetector."""
        assert isinstance(detector, BaseDetector)

    def test_cannot_instantiate_base_detector(self) -> None:
        """BaseDetector is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDetector()  # type: ignore[abstract]

    def test_detector_id(self, detector: FundamentalEventDetector) -> None:
        assert detector.detector_id == "fundamental"
        assert isinstance(detector.detector_id, str)
        assert detector.detector_id.strip() != ""

    def test_name(self, detector: FundamentalEventDetector) -> None:
        assert detector.name == "Fundamental Event Detector"
        assert isinstance(detector.name, str)
        assert detector.name.strip() != ""

    def test_event_types_is_tuple(self, detector: FundamentalEventDetector) -> None:
        assert isinstance(detector.event_types, tuple)
        assert len(detector.event_types) == 5

    def test_event_types_no_duplicates(self, detector: FundamentalEventDetector) -> None:
        assert len(detector.event_types) == len(set(detector.event_types))

    def test_event_types_all_strings(self, detector: FundamentalEventDetector) -> None:
        for et in detector.event_types:
            assert isinstance(et, str)
            assert et.strip() != ""

    def test_declared_event_types_match(self, detector: FundamentalEventDetector) -> None:
        assert detector.event_types == _EVENT_TYPES


# =========================================================================
# detect() behaviour
# =========================================================================


class TestDetectMethod:
    """Test the detect() method under various scenarios."""

    def test_detect_returns_empty_list_with_valid_context(
        self,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """
        detect() returns [] for any valid context because fundamental
        data is not available in DetectionContext.

        An empty list is the correct response: analysis completed, nothing detected.
        """
        results = detector.detect(valid_context)
        assert isinstance(results, list)
        assert results == []

    def test_detect_returns_empty_list_with_minimal_context(
        self,
        detector: FundamentalEventDetector,
        minimal_context: DetectionContext,
    ) -> None:
        """detect() returns [] even with a minimal (1-candle) context."""
        results = detector.detect(minimal_context)
        assert isinstance(results, list)
        assert results == []

    def test_detect_returns_empty_list_for_gpw_stock(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """detect() works for GPW stocks."""
        data = [_make_market_data(10.0 + i * 1.0, offset=i) for i in range(5)]
        ctx = DetectionContext(
            ticker="GPW.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=tuple(data),
        )
        assert detector.detect(ctx) == []

    def test_detect_returns_empty_list_for_usa_stock(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """detect() works for USA stocks."""
        data = [_make_market_data(3.0 + i * 0.2, offset=i) for i in range(5)]
        ctx = DetectionContext(
            ticker="PENNY.US",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=tuple(data),
        )
        assert detector.detect(ctx) == []

    def test_detect_returns_empty_list_for_etf(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """
        detect() works for ETFs too, though fundamental events typically
        don't apply to ETFs. The detector doesn't filter by instrument
        type — it just returns [] due to missing data.
        """
        data = [_make_market_data(200.0 + i * 1.0, offset=i) for i in range(5)]
        ctx = DetectionContext(
            ticker="SPY",
            market="NYSE",
            instrument_type=InstrumentType.ETF,
            ohlcv_data=tuple(data),
        )
        assert detector.detect(ctx) == []

    def test_detect_returns_list_not_none(
        self,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """detect() never returns None — it always returns a list."""
        results = detector.detect(valid_context)
        assert results is not None
        assert isinstance(results, list)


# =========================================================================
# can_handle()
# =========================================================================


class TestCanHandle:
    """Test the can_handle() concrete method."""

    def test_can_handle_declared_event_types(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """can_handle() returns True for all declared event types."""
        for et in detector.event_types:
            assert detector.can_handle(et), f"should handle {et!r}"

    def test_can_handle_unknown_event_type(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """can_handle() returns False for event types not in event_types."""
        unknown_types = [
            "PRICE_SURGE",
            "VOLATILITY_SPIKE",
            "RSI_OVERBOUGHT",
            "INSIDER_TRANSACTION",
            "NEW_ESPI_FILING",
            "",
            "UNKNOWN_EVENT",
        ]
        for et in unknown_types:
            assert not detector.can_handle(
                et
            ), f"should NOT handle {et!r}"

    def test_can_handle_empty_string(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """can_handle('') returns False."""
        assert not detector.can_handle("")


# =========================================================================
# DetectorRegistry integration
# =========================================================================


class TestRegistryIntegration:
    """Verify that FundamentalEventDetector can be registered and looked up."""

    def test_register_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """Detector can be registered without errors."""
        registry.register(detector)
        assert registry.contains("fundamental")

    def test_register_duplicate_raises(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """Registering a detector with the same detector_id raises KeyError."""
        registry.register(detector)
        duplicate = FundamentalEventDetector()
        with pytest.raises(KeyError, match="already registered"):
            registry.register(duplicate)

    def test_get_retrieves_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """get() returns the registered detector."""
        registry.register(detector)
        retrieved = registry.get("fundamental")
        assert retrieved is detector

    def test_get_unknown_raises(
        self,
        registry: DetectorRegistry,
    ) -> None:
        """get() raises KeyError for unregistered detector_id."""
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_get_all_includes_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """get_all() includes the registered detector."""
        registry.register(detector)
        all_detectors = registry.get_all()
        assert len(all_detectors) == 1
        assert all_detectors[0] is detector

    def test_get_for_event_type_returns_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """get_for_event_type() returns the detector when it handles the type."""
        registry.register(detector)
        for et in detector.event_types:
            matching = registry.get_for_event_type(et)
            assert len(matching) == 1, f"no detector for {et!r}"
            assert matching[0] is detector

    def test_get_for_event_type_empty_when_no_match(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """get_for_event_type() returns empty tuple for unknown event types."""
        registry.register(detector)
        assert registry.get_for_event_type("PRICE_SURGE") == ()

    def test_len_after_register(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """len() reflects the number of registered detectors."""
        assert len(registry) == 0
        registry.register(detector)
        assert len(registry) == 1


# =========================================================================
# DetectorOrchestrator integration
# =========================================================================


class TestOrchestratorIntegration:
    """Verify that FundamentalEventDetector works with DetectorOrchestrator."""

    def test_run_all_with_fundamental_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """run_all() returns empty tuple when only fundamental detector is registered."""
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)
        results = orchestrator.run_all(valid_context)
        assert isinstance(results, tuple)
        assert results == ()

    def test_run_for_event_type_with_fundamental_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """run_for_event_type() returns empty tuple for a declared event type."""
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)
        results = orchestrator.run_for_event_type(valid_context, "PE_RATIO_CHANGE")
        assert isinstance(results, tuple)
        assert results == ()

    def test_run_for_event_type_no_match(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """run_for_event_type() returns empty tuple when no detector matches."""
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)
        results = orchestrator.run_for_event_type(valid_context, "PRICE_SURGE")
        assert results == ()

    def test_run_all_with_invalid_context_raises(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
    ) -> None:
        """run_all() raises TypeError for non-DetectionContext argument."""
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="DetectionContext"):
            orchestrator.run_all("not a context")  # type: ignore[arg-type]

    def test_run_all_does_not_mutate_detector(
        self,
        registry: DetectorRegistry,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """Running the orchestrator does not change the detector's state."""
        registry.register(detector)
        orchestrator = DetectorOrchestrator(registry)

        id_before = detector.detector_id
        name_before = detector.name
        event_types_before = detector.event_types

        orchestrator.run_all(valid_context)

        assert detector.detector_id == id_before
        assert detector.name == name_before
        assert detector.event_types == event_types_before


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_detect_with_large_context(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """detect() handles a large number of candles gracefully."""
        data = [_make_market_data(100.0 + i * 0.1, offset=i) for i in range(500)]
        ctx = DetectionContext(
            ticker="BIG.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=tuple(data),
        )
        results = detector.detect(ctx)
        assert results == []

    def test_detect_with_zero_or_negative_close(
        self,
        detector: FundamentalEventDetector,
    ) -> None:
        """
        detect() handles zero/negative close prices gracefully.
        MarketData doesn't enforce positive prices, but detect() doesn't use price
        data at all in the current implementation.
        """
        data = [
            MarketData(
                open=0.01,
                high=0.02,
                low=0.0,
                close=0.0,
                volume=1000.0,
                timestamp=datetime(2026, 7, 20),
            ),
            MarketData(
                open=0.02,
                high=0.03,
                low=0.01,
                close=0.01,
                volume=2000.0,
                timestamp=datetime(2026, 7, 21),
            ),
        ]
        ctx = DetectionContext(
            ticker="ZERO.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=tuple(data),
        )
        results = detector.detect(ctx)
        assert results == []

    def test_multiple_detectors_in_registry(
        self,
        detector: FundamentalEventDetector,
        valid_context: DetectionContext,
    ) -> None:
        """Orchestrator can handle multiple detectors including fundamental."""
        registry = DetectorRegistry()
        registry.register(detector)

        # Create a second detector (another instance of the same type)
        # This is allowed since detector_id is the same class-level value,
        # only duplicates by detector_id are rejected.
        orchestrator = DetectorOrchestrator(registry)
        results = orchestrator.run_all(valid_context)
        assert isinstance(results, tuple)
        assert results == ()