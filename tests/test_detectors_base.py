"""
Tests for the BaseDetector interface and the DetectionContext / DetectionResult
contracts (ETAP 6 — Krok 1B).

Covers:
    - DetectionContext creation & validation
    - DetectionResult creation & validation
    - BaseDetector abstract interface
    - BaseDetector.can_handle()
    - Frozen invariants
    - Absence of Any, **kwargs, metadata

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11.4, §11.5, §11.6
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from data.models.event_enums import InstrumentType
from data.models.market_data import MarketData
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult

# ==============================================================================
# Helpers
# ==============================================================================

UTC = timezone.utc

NOW = datetime(2026, 7, 22, 14, 0, 0, tzinfo=UTC)


def _md(**kwargs):  # noqa: ANN202
    """Return a minimal valid MarketData instance."""
    defaults = {
        "open": 10.0,
        "high": 11.0,
        "low": 9.5,
        "close": 10.8,
        "volume": 1_000_000.0,
        "timestamp": NOW,
    }
    defaults.update(kwargs)
    return MarketData(**defaults)


def _pd(**kwargs):  # noqa: ANN202
    """Return a minimal valid PriceData instance."""
    defaults = {
        "open": 10.0,
        "high": 11.0,
        "low": 9.5,
        "close": 10.8,
        "prev_close": 10.5,
        "change_pct": 2.86,
        "change_abs": 0.3,
    }
    defaults.update(kwargs)
    return PriceData(**defaults)


def _vd(**kwargs):  # noqa: ANN202
    """Return a minimal valid VolumeData instance."""
    defaults = {
        "current_volume": 1_500_000,
        "avg_volume": 800_000,
        "volume_ratio": 1.875,
        "direction": "up",
    }
    defaults.update(kwargs)
    return VolumeData(**defaults)


# ==============================================================================
# DetectionContext tests
# ==============================================================================


class TestDetectionContext:
    """Unit tests for the DetectionContext model."""

    # -- valid cases -----------------------------------------------------------

    def test_valid_single_candle(self) -> None:
        ctx = DetectionContext(
            ticker="TEST.TK",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=(_md(),),
        )
        assert ctx.ticker == "TEST.TK"
        assert len(ctx.ohlcv_data) == 1

    def test_valid_multiple_candles_chronological(self) -> None:
        md0 = _md(timestamp=NOW)
        md1 = _md(timestamp=NOW + timedelta(minutes=5))
        md2 = _md(timestamp=NOW + timedelta(minutes=10))
        ctx = DetectionContext(
            ticker="TEST.TK",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=(md0, md1, md2),
        )
        assert len(ctx.ohlcv_data) == 3

    def test_ohlcv_data_remains_tuple(self) -> None:
        md0 = _md(timestamp=NOW)
        md1 = _md(timestamp=NOW + timedelta(minutes=5))
        ctx = DetectionContext(
            ticker="A",
            market="B",
            instrument_type=InstrumentType.ETF,
            ohlcv_data=(md0, md1),
        )
        assert isinstance(ctx.ohlcv_data, tuple)

    def test_frozen_cannot_mutate_fields(self) -> None:
        ctx = DetectionContext(
            ticker="A", market="B",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=(_md(),),
        )
        with pytest.raises(FrozenInstanceError):
            ctx.ticker = "OTHER"  # type: ignore[misc]

    # -- ticker ----------------------------------------------------------------

    def test_ticker_empty(self) -> None:
        with pytest.raises(ValueError, match="ticker must not be empty"):
            DetectionContext(
                ticker="", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(_md(),),
            )

    def test_ticker_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="ticker must not be empty"):
            DetectionContext(
                ticker="   ", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(_md(),),
            )

    def test_ticker_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="ticker must be str"):
            DetectionContext(
                ticker=123,  # type: ignore[arg-type]
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(_md(),),
            )

    # -- market ----------------------------------------------------------------

    def test_market_empty(self) -> None:
        with pytest.raises(ValueError, match="market must not be empty"):
            DetectionContext(
                ticker="T", market="",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(_md(),),
            )

    def test_market_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="market must not be empty"):
            DetectionContext(
                ticker="T", market="  ",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(_md(),),
            )

    def test_market_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="market must be str"):
            DetectionContext(
                ticker="T",
                market=None,  # type: ignore[arg-type]
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(_md(),),
            )

    # -- instrument_type -------------------------------------------------------

    def test_instrument_type_plain_str(self) -> None:
        with pytest.raises(TypeError, match="instrument_type must be an InstrumentType"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type="STOCK_GPW",  # type: ignore[arg-type]
                ohlcv_data=(_md(),),
            )

    def test_instrument_type_none(self) -> None:
        with pytest.raises(TypeError, match="instrument_type must be an InstrumentType"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=None,  # type: ignore[arg-type]
                ohlcv_data=(_md(),),
            )

    # -- ohlcv_data ------------------------------------------------------------

    def test_missing_ohlcv_raises(self) -> None:
        with pytest.raises(TypeError):
            DetectionContext(  # type: ignore[call-arg]
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
            )

    def test_empty_tuple(self) -> None:
        with pytest.raises(ValueError, match="ohlcv_data must contain at least one"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(),
            )

    def test_list_instead_of_tuple(self) -> None:
        with pytest.raises(TypeError, match="ohlcv_data must be a tuple"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=[_md()],  # type: ignore[arg-type]
            )

    def test_non_marketdata_element(self) -> None:
        with pytest.raises(TypeError, match="ohlcv_data\\[0\\] must be MarketData"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=("not_marketdata",),  # type: ignore[arg-type]
            )

    def test_reverse_chronological_order(self) -> None:
        md0 = _md(timestamp=NOW + timedelta(minutes=10))
        md1 = _md(timestamp=NOW)
        with pytest.raises(ValueError, match="not in strict chronological order"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(md0, md1),
            )

    def test_duplicate_timestamps(self) -> None:
        ts = NOW
        md0 = _md(timestamp=ts)
        md1 = _md(timestamp=ts)
        with pytest.raises(ValueError, match="not in strict chronological order"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(md0, md1),
            )

    def test_no_ohlcv_is_contract_error_not_detection_failure(self) -> None:
        """Callers cannot create a context without OHLCV at all."""
        with pytest.raises(ValueError, match="ohlcv_data must contain at least one"):
            DetectionContext(
                ticker="T", market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=(),
            )
        # The detector is never called — this is a contract-level failure.


# ==============================================================================
# DetectionResult tests
# ==============================================================================


class TestDetectionResult:
    """Unit tests for the DetectionResult model."""

    def test_minimal_valid(self) -> None:
        r = DetectionResult(event_type="PRICE_SURGE", confidence_level=0.95)
        assert r.event_type == "PRICE_SURGE"
        assert r.confidence_level == 0.95
        assert r.price_data is None
        assert r.volume_data is None

    def test_with_price_data(self) -> None:
        r = DetectionResult(
            event_type="VOLATILITY_SPIKE",
            confidence_level=0.82,
            price_data=_pd(),
        )
        assert isinstance(r.price_data, PriceData)
        assert r.volume_data is None

    def test_with_volume_data(self) -> None:
        r = DetectionResult(
            event_type="VOLUME_SPIKE",
            confidence_level=0.75,
            volume_data=_vd(),
        )
        assert isinstance(r.volume_data, VolumeData)
        assert r.price_data is None

    def test_with_both_price_and_volume(self) -> None:
        r = DetectionResult(
            event_type="VOLUME_SPIKE",
            confidence_level=0.75,
            price_data=_pd(),
            volume_data=_vd(),
        )
        assert isinstance(r.price_data, PriceData)
        assert isinstance(r.volume_data, VolumeData)

    def test_confidence_boundary_zero(self) -> None:
        r = DetectionResult(event_type="X", confidence_level=0.0)
        assert r.confidence_level == 0.0

    def test_confidence_boundary_one(self) -> None:
        r = DetectionResult(event_type="X", confidence_level=1.0)
        assert r.confidence_level == 1.0

    def test_frozen_cannot_mutate_fields(self) -> None:
        r = DetectionResult(event_type="X", confidence_level=0.5)
        with pytest.raises(FrozenInstanceError):
            r.confidence_level = 0.9  # type: ignore[misc]

    # -- event_type ------------------------------------------------------------

    def test_event_type_empty(self) -> None:
        with pytest.raises(ValueError, match="event_type must not be empty"):
            DetectionResult(event_type="", confidence_level=0.5)

    def test_event_type_whitespace(self) -> None:
        with pytest.raises(ValueError, match="event_type must not be empty"):
            DetectionResult(event_type="  ", confidence_level=0.5)

    def test_event_type_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="event_type must be str"):
            DetectionResult(event_type=42, confidence_level=0.5)  # type: ignore[arg-type]

    # -- confidence_level ------------------------------------------------------

    def test_confidence_below_range(self) -> None:
        with pytest.raises(ValueError, match="must be in \\[0.0, 1.0\\]"):
            DetectionResult(event_type="X", confidence_level=-0.1)

    def test_confidence_above_range(self) -> None:
        with pytest.raises(ValueError, match="must be in \\[0.0, 1.0\\]"):
            DetectionResult(event_type="X", confidence_level=1.1)

    def test_confidence_nan(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            DetectionResult(event_type="X", confidence_level=math.nan)

    def test_confidence_positive_infinity(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            DetectionResult(event_type="X", confidence_level=math.inf)

    def test_confidence_negative_infinity(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            DetectionResult(event_type="X", confidence_level=-math.inf)

    def test_confidence_bool(self) -> None:
        with pytest.raises(TypeError, match="must be a real number.*bool"):
            DetectionResult(event_type="X", confidence_level=True)  # type: ignore[arg-type]

    def test_confidence_str(self) -> None:
        with pytest.raises(TypeError, match="must be a real number"):
            DetectionResult(event_type="X", confidence_level="0.5")  # type: ignore[arg-type]

    # -- price_data / volume_data ----------------------------------------------

    def test_price_data_dict_instead_of_model(self) -> None:
        with pytest.raises(TypeError, match="price_data must be None or a PriceData"):
            DetectionResult(
                event_type="X",
                confidence_level=0.5,
                price_data={"open": 10},  # type: ignore[arg-type]
            )

    def test_volume_data_dict_instead_of_model(self) -> None:
        with pytest.raises(TypeError, match="volume_data must be None or a VolumeData"):
            DetectionResult(
                event_type="X",
                confidence_level=0.5,
                volume_data={"direction": "up"},  # type: ignore[arg-type]
            )

    def test_price_data_none_is_valid(self) -> None:
        r = DetectionResult(event_type="X", confidence_level=0.5, price_data=None)
        assert r.price_data is None

    def test_volume_data_none_is_valid(self) -> None:
        r = DetectionResult(event_type="X", confidence_level=0.5, volume_data=None)
        assert r.volume_data is None


# ==============================================================================
# BaseDetector tests
# ==============================================================================


class _ConcreteDetector(BaseDetector):
    """Minimal concrete detector for testing the target contract."""

    @property
    def detector_id(self) -> str:
        return "test_detector"

    @property
    def name(self) -> str:
        return "Test Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return ("EVENT_ALPHA", "EVENT_BETA")

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        # Return the event types as detection results for test verification.
        return [
            DetectionResult(event_type=et, confidence_level=0.9)
            for et in self.event_types
        ]


class TestBaseDetector:
    """Test suite for the target BaseDetector contract."""

    def test_is_abstract_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseDetector()  # type: ignore[abstract]

    def test_missing_abstract_property_raises_error(self) -> None:
        class MissingProperty(BaseDetector):
            def detect(self, context: DetectionContext) -> list[DetectionResult]:
                return []

        with pytest.raises(TypeError):
            MissingProperty()

    def test_missing_abstract_method_raises_error(self) -> None:
        class MissingMethod(BaseDetector):
            @property
            def detector_id(self) -> str:
                return "x"

            @property
            def name(self) -> str:
                return "x"

            @property
            def event_types(self) -> tuple[str, ...]:
                return ()

        with pytest.raises(TypeError):
            MissingMethod()

    def test_concrete_implementation_instantiates(self) -> None:
        detector = _ConcreteDetector()
        assert isinstance(detector, BaseDetector)

    def test_detector_id_property(self) -> None:
        detector = _ConcreteDetector()
        assert detector.detector_id == "test_detector"
        assert isinstance(detector.detector_id, str)

    def test_name_property(self) -> None:
        detector = _ConcreteDetector()
        assert detector.name == "Test Detector"
        assert isinstance(detector.name, str)

    def test_event_types_returns_tuple(self) -> None:
        detector = _ConcreteDetector()
        assert detector.event_types == ("EVENT_ALPHA", "EVENT_BETA")
        assert isinstance(detector.event_types, tuple)

    def test_detect_accepts_detection_context(self) -> None:
        detector = _ConcreteDetector()
        ctx = DetectionContext(
            ticker="T",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=(_md(),),
        )
        results = detector.detect(ctx)
        assert isinstance(results, list)
        assert all(isinstance(r, DetectionResult) for r in results)
        assert [r.event_type for r in results] == ["EVENT_ALPHA", "EVENT_BETA"]

    def test_detect_returns_list_of_detection_result(self) -> None:
        detector = _ConcreteDetector()
        ctx = DetectionContext(
            ticker="T",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=(_md(),),
        )
        results = detector.detect(ctx)
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, DetectionResult) for r in results)

    def test_empty_list_means_no_detection(self) -> None:
        class EmptyDetector(BaseDetector):
            @property
            def detector_id(self) -> str:
                return "empty"

            @property
            def name(self) -> str:
                return "Empty"

            @property
            def event_types(self) -> tuple[str, ...]:
                return ("NOTHING",)

            def detect(self, context: DetectionContext) -> list[DetectionResult]:
                return []

        detector = EmptyDetector()
        ctx = DetectionContext(
            ticker="T",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=(_md(),),
        )
        results = detector.detect(ctx)
        assert results == []

    def test_can_handle_returns_true_for_known(self) -> None:
        detector = _ConcreteDetector()
        assert detector.can_handle("EVENT_ALPHA") is True
        assert detector.can_handle("EVENT_BETA") is True

    def test_can_handle_returns_false_for_unknown(self) -> None:
        detector = _ConcreteDetector()
        assert detector.can_handle("EVENT_GAMMA") is False
        assert detector.can_handle("") is False

    def test_no_any_in_base_detector(self) -> None:
        """Verify that 'Any' is not present in the BaseDetector source."""
        import inspect
        source = inspect.getsource(BaseDetector)
        assert "Any" not in source, "BaseDetector must not contain Any"

    def test_no_kwargs_in_detect_signature(self) -> None:
        """Verify that detect() does not accept **kwargs."""
        import inspect
        sig = inspect.signature(BaseDetector.detect)
        params = list(sig.parameters.values())
        for p in params:
            assert p.kind not in (
                inspect.Parameter.VAR_KEYWORD,
            ), "detect() must not accept **kwargs"

    def test_interface_has_required_members(self) -> None:
        members = dir(BaseDetector)
        assert "detector_id" in members
        assert "name" in members
        assert "event_types" in members
        assert "detect" in members
        assert "can_handle" in members


# ==============================================================================
# Cross-checks — forbidden patterns in the implemented contract
# ==============================================================================


class TestForbiddenPatternsInContract:
    """Confirm the target contract does not contain prohibited constructs."""

    def test_detection_result_has_no_metadata_field(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert "metadata" not in fields

    def test_detection_result_has_no_event_category(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert "event_category" not in fields

    def test_detection_result_has_no_event_subcategory(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert "event_subcategory" not in fields

    def test_detection_result_has_no_priority_raw(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert "priority_raw" not in fields

    def test_detection_result_has_no_timestamp_field(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert "timestamp" not in fields

    def test_detection_result_has_no_ticker_field(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert "ticker" not in fields

    def test_detection_result_has_exactly_four_fields(self) -> None:
        fields = {f.name for f in DetectionResult.__dataclass_fields__.values()}
        assert fields == {"event_type", "confidence_level", "price_data", "volume_data"}

    def test_detection_context_has_no_defaults(self) -> None:
        """All fields of DetectionContext must be required (no defaults)."""
        from dataclasses import MISSING
        for field in DetectionContext.__dataclass_fields__.values():
            assert (
                field.default is MISSING and field.default_factory is MISSING
            ), f"{field.name} must not have a default value"

    def test_detection_result_required_fields_have_no_defaults(self) -> None:
        from dataclasses import MISSING
        for name in ("event_type", "confidence_level"):
            field = DetectionResult.__dataclass_fields__[name]
            assert (
                field.default is MISSING and field.default_factory is MISSING
            ), f"{name} must not have a default value"

    def test_event_types_returns_tuple_not_list(self) -> None:
        detector = _ConcreteDetector()
        assert isinstance(detector.event_types, tuple)
        assert not isinstance(detector.event_types, list)