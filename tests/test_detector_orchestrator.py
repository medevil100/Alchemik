"""
Tests for DetectorOrchestrator — ETAP 6 — Krok 3.

Covers:
    - Construction (valid, same instance, type checks, no *args/**kwargs, no detect)
    - run_all() behaviour (empty registry, ordering, flattening, identity, validation)
    - run_for_event_type() behaviour (filtering, ordering, flattening, identity)
    - Context validation (all invalid types rejected)
    - event_type validation (relies on registry)
    - Invalid detect() results (all malformed returns => TypeError)
    - Exception propagation (no catching, no retry, subsequent detectors not called)
    - Forbidden responsibilities (no banned methods, no Any, no async, no parallelism)

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest

from data.models.event_enums import InstrumentType
from data.models.market_data import MarketData
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.orchestrator import DetectorOrchestrator
from engines.detectors.registry import DetectorRegistry
from engines.detectors.result import DetectionResult

# ==============================================================================
# Helpers
# ==============================================================================

UTC = timezone.utc
NOW = datetime(2026, 7, 22, 14, 0, 0, tzinfo=UTC)


def _md(**kwargs):  # noqa: ANN202
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


def _ctx(**kwargs):  # noqa: ANN202
    """Return a minimal valid DetectionContext."""
    defaults = {
        "ticker": "TEST.TK",
        "market": "GPW",
        "instrument_type": InstrumentType.STOCK_GPW,
        "ohlcv_data": (_md(),),
    }
    defaults.update(kwargs)
    return DetectionContext(**defaults)


def _res(**kwargs):  # noqa: ANN202
    """Return a minimal valid DetectionResult."""
    defaults = {
        "event_type": "PRICE_SURGE",
        "confidence_level": 0.9,
    }
    defaults.update(kwargs)
    return DetectionResult(**defaults)


# ==============================================================================
# Stub detector for testing
# ==============================================================================


class StubDetector(BaseDetector):
    """
    Minimal concrete detector for orchestrator tests.

    Supports controlling:
        - detector_id, name, event_types
        - list of DetectionResult to return
        - a call counter
        - last received context
        - an optional exception to raise from detect()
    """

    def __init__(
        self,
        detector_id: str = "stub",
        name: str = "Stub Detector",
        event_types: tuple[str, ...] = ("EVENT_X",),
        results: list[DetectionResult] | None = None,
        raise_exc: BaseException | None = None,
    ) -> None:
        self._detector_id = detector_id
        self._name = name
        self._event_types = event_types
        self._results: list[DetectionResult] = (
            results if results is not None else [_res()]
        )
        self._raise_exc = raise_exc
        self._call_count = 0
        self._last_context: DetectionContext | None = None

    @property
    def detector_id(self) -> str:
        return self._detector_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def event_types(self) -> tuple[str, ...]:
        return self._event_types

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        self._call_count += 1
        self._last_context = context
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._results


# ==============================================================================
# Construction tests
# ==============================================================================


class TestConstruction:
    """Tests for DetectorOrchestrator constructor."""

    def test_valid_registry_accepted(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        assert isinstance(orch, DetectorOrchestrator)

    def test_same_registry_instance_preserved(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        assert orch._registry is registry

    def test_none_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be a DetectorRegistry"):
            DetectorOrchestrator(None)  # type: ignore[arg-type]

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(TypeError, match="must be a DetectorRegistry"):
            DetectorOrchestrator("not_a_registry")  # type: ignore[arg-type]

    def test_constructor_does_not_accept_args(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError):
            DetectorOrchestrator(registry, "extra")  # type: ignore[call-arg]

    def test_constructor_does_not_accept_kwargs(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError):
            DetectorOrchestrator(registry=registry, extra="value")  # type: ignore[call-arg]

    def test_constructor_does_not_call_detect(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1")
        registry.register(detector)
        DetectorOrchestrator(registry)
        assert detector._call_count == 0


# ==============================================================================
# run_all() tests
# ==============================================================================


class TestRunAll:
    """Tests for DetectorOrchestrator.run_all()."""

    def test_empty_registry_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert result == ()
        assert isinstance(result, tuple)

    def test_result_is_tuple(self) -> None:
        registry = DetectorRegistry()
        registry.register(StubDetector(detector_id="d1", results=[_res()]))
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert isinstance(result, tuple)

    def test_one_detector_called_once(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", results=[_res()])
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        orch.run_all(_ctx())
        assert detector._call_count == 1

    def test_multiple_detectors_each_called_once(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="first", results=[_res()])
        d2 = StubDetector(detector_id="second", results=[_res()])
        d3 = StubDetector(detector_id="third", results=[_res()])
        registry.register(d1)
        registry.register(d2)
        registry.register(d3)
        orch = DetectorOrchestrator(registry)
        orch.run_all(_ctx())
        assert d1._call_count == 1
        assert d2._call_count == 1
        assert d3._call_count == 1

    def test_registration_order_preserved(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="first", results=[_res(event_type="FIRST")])
        d2 = StubDetector(detector_id="second", results=[_res(event_type="SECOND")])
        d3 = StubDetector(detector_id="third", results=[_res(event_type="THIRD")])
        registry.register(d1)
        registry.register(d2)
        registry.register(d3)
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert [r.event_type for r in result] == ["FIRST", "SECOND", "THIRD"]

    def test_result_order_per_detector_preserved(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(
            detector_id="d1",
            results=[_res(event_type="E1"), _res(event_type="E2"), _res(event_type="E3")],
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert [r.event_type for r in result] == ["E1", "E2", "E3"]

    def test_results_are_flattened(self) -> None:
        registry = DetectorRegistry()
        d_a = StubDetector(
            detector_id="a", results=[_res(event_type="A1"), _res(event_type="A2")]
        )
        d_b = StubDetector(
            detector_id="b", results=[_res(event_type="B1")]
        )
        d_c = StubDetector(
            detector_id="c", results=[],
        )
        d_d = StubDetector(
            detector_id="d", results=[_res(event_type="D1"), _res(event_type="D2")]
        )
        registry.register(d_a)
        registry.register(d_b)
        registry.register(d_c)
        registry.register(d_d)
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert [r.event_type for r in result] == ["A1", "A2", "B1", "D1", "D2"]

    def test_detector_returning_empty_list_is_valid(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", results=[])
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert result == ()

    def test_all_detectors_return_empty_gives_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        registry.register(StubDetector(detector_id="d1", results=[]))
        registry.register(StubDetector(detector_id="d2", results=[]))
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert result == ()

    def test_same_context_instance_to_each_detector(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", results=[_res()])
        d2 = StubDetector(detector_id="d2", results=[_res()])
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        ctx = _ctx()
        orch.run_all(ctx)
        assert d1._last_context is ctx
        assert d2._last_context is ctx

    def test_same_result_instances_returned(self) -> None:
        registry = DetectorRegistry()
        r1 = _res(event_type="E1")
        r2 = _res(event_type="E2")
        detector = StubDetector(detector_id="d1", results=[r1, r2])
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        assert result[0] is r1
        assert result[1] is r2

    def test_every_registered_detector_is_called(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", results=[_res()])
        d2 = StubDetector(detector_id="d2", results=[_res()])
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        orch.run_all(_ctx())
        assert d1._call_count == 1
        assert d2._call_count == 1

    def test_run_all_does_not_filter_by_event_type(self) -> None:
        """run_all() calls ALL detectors regardless of event_types."""
        registry = DetectorRegistry()
        d1 = StubDetector(
            detector_id="d1", event_types=("ALPHA",), results=[_res(event_type="ALPHA")]
        )
        d2 = StubDetector(
            detector_id="d2", event_types=("BETA",), results=[_res(event_type="BETA")]
        )
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        result = orch.run_all(_ctx())
        event_types_from_results = [r.event_type for r in result]
        assert "ALPHA" in event_types_from_results
        assert "BETA" in event_types_from_results
        assert d1._call_count == 1
        assert d2._call_count == 1

    def test_registry_not_modified(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", results=[_res()])
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        orch.run_all(_ctx())
        assert len(registry) == 1
        assert registry.get("d1") is detector


# ==============================================================================
# run_for_event_type() tests
# ==============================================================================


class TestRunForEventType:
    """Tests for DetectorOrchestrator.run_for_event_type()."""

    def test_no_match_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        registry.register(StubDetector(detector_id="d1", event_types=("ALPHA",)))
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "BETA")
        assert result == ()
        assert isinstance(result, tuple)

    def test_one_matching_detector_is_called(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(
            detector_id="d1", event_types=("ALPHA",), results=[_res()]
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "ALPHA")
        assert len(result) == 1
        assert detector._call_count == 1

    def test_non_matching_detector_not_called(self) -> None:
        registry = DetectorRegistry()
        d_match = StubDetector(
            detector_id="match", event_types=("ALPHA",), results=[_res()]
        )
        d_no_match = StubDetector(
            detector_id="no_match", event_types=("BETA",), results=[_res()]
        )
        registry.register(d_match)
        registry.register(d_no_match)
        orch = DetectorOrchestrator(registry)
        orch.run_for_event_type(_ctx(), "ALPHA")
        assert d_match._call_count == 1
        assert d_no_match._call_count == 0

    def test_multiple_matching_detectors_called(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(
            detector_id="d1", event_types=("SHARED",), results=[_res(event_type="D1")]
        )
        d2 = StubDetector(
            detector_id="d2", event_types=("SHARED",), results=[_res(event_type="D2")]
        )
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "SHARED")
        assert d1._call_count == 1
        assert d2._call_count == 1
        assert [r.event_type for r in result] == ["D1", "D2"]

    def test_overlapping_event_types_work(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(
            detector_id="d1",
            event_types=("ALPHA", "BETA"),
            results=[_res(event_type="ALPHA")],
        )
        d2 = StubDetector(
            detector_id="d2",
            event_types=("ALPHA", "GAMMA"),
            results=[_res(event_type="GAMMA")],
        )
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "ALPHA")
        assert d1._call_count == 1
        assert d2._call_count == 1
        assert len(result) == 2

    def test_registration_order_preserved(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(
            detector_id="first", event_types=("EVT",), results=[_res(event_type="FIRST")]
        )
        d2 = StubDetector(
            detector_id="second", event_types=("EVT",), results=[_res(event_type="SECOND")]
        )
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "EVT")
        assert [r.event_type for r in result] == ["FIRST", "SECOND"]

    def test_result_order_preserved(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(
            detector_id="d1",
            event_types=("EVT",),
            results=[_res(event_type="A"), _res(event_type="B"), _res(event_type="C")],
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "EVT")
        assert [r.event_type for r in result] == ["A", "B", "C"]

    def test_results_are_flattened(self) -> None:
        registry = DetectorRegistry()
        d_a = StubDetector(
            detector_id="a",
            event_types=("EVT",),
            results=[_res(event_type="A1"), _res(event_type="A2")],
        )
        d_b = StubDetector(
            detector_id="b",
            event_types=("EVT",),
            results=[_res(event_type="B1")],
        )
        registry.register(d_a)
        registry.register(d_b)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "EVT")
        assert [r.event_type for r in result] == ["A1", "A2", "B1"]

    def test_same_context_instance_passed(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", event_types=("EVT",), results=[_res()])
        d2 = StubDetector(detector_id="d2", event_types=("EVT",), results=[_res()])
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        ctx = _ctx()
        orch.run_for_event_type(ctx, "EVT")
        assert d1._last_context is ctx
        assert d2._last_context is ctx

    def test_same_result_instances_returned(self) -> None:
        registry = DetectorRegistry()
        r1 = _res(event_type="R1")
        r2 = _res(event_type="R2")
        detector = StubDetector(
            detector_id="d1", event_types=("EVT",), results=[r1, r2]
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "EVT")
        assert result[0] is r1
        assert result[1] is r2

    def test_each_matching_detector_called_once(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", event_types=("EVT",), results=[_res()])
        d2 = StubDetector(detector_id="d2", event_types=("EVT",), results=[_res()])
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        orch.run_for_event_type(_ctx(), "EVT")
        assert d1._call_count == 1
        assert d2._call_count == 1

    def test_empty_registry_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "EVT")
        assert result == ()

    def test_uses_registry_public_api(self) -> None:
        """Verify run_for_event_type uses registry.get_for_event_type()."""
        registry = DetectorRegistry()
        d1 = StubDetector(
            detector_id="d1", event_types=("ALPHA",), results=[_res(event_type="ALPHA")]
        )
        d2 = StubDetector(
            detector_id="d2", event_types=("BETA",), results=[_res(event_type="BETA")]
        )
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        result = orch.run_for_event_type(_ctx(), "ALPHA")
        assert d1._call_count == 1
        assert d2._call_count == 0
        assert [r.event_type for r in result] == ["ALPHA"]

    def test_non_matching_detectors_have_zero_calls(self) -> None:
        registry = DetectorRegistry()
        d_match = StubDetector(
            detector_id="match", event_types=("TARGET",), results=[_res()]
        )
        d_other = StubDetector(
            detector_id="other", event_types=("OTHER",), results=[_res()]
        )
        registry.register(d_match)
        registry.register(d_other)
        orch = DetectorOrchestrator(registry)
        orch.run_for_event_type(_ctx(), "TARGET")
        assert d_other._call_count == 0


# ==============================================================================
# Context validation tests
# ==============================================================================


class TestContextValidation:
    """Tests confirming context type validation for both methods."""

    def test_run_all_none_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_all(None)  # type: ignore[arg-type]

    def test_run_all_dict_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_all({"ticker": "X"})  # type: ignore[arg-type]

    def test_run_all_list_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_all(["not", "a", "context"])  # type: ignore[arg-type]

    def test_run_all_str_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_all("not a context")  # type: ignore[arg-type]

    def test_run_all_non_context_object_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_all(object())  # type: ignore[arg-type]

    def test_run_for_event_type_none_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_for_event_type(None, "EVT")  # type: ignore[arg-type]

    def test_run_for_event_type_dict_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must be a DetectionContext"):
            orch.run_for_event_type({"ticker": "X"}, "EVT")  # type: ignore[arg-type]

    def test_bad_context_does_not_trigger_detect(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", results=[_res()])
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError):
            orch.run_all(None)  # type: ignore[arg-type]
        assert detector._call_count == 0

    def test_bad_context_does_not_mutate_registry(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", results=[_res()])
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError):
            orch.run_all(None)  # type: ignore[arg-type]
        assert len(registry) == 1


# ==============================================================================
# event_type validation tests
# ==============================================================================


class TestEventTypeValidation:
    """Tests confirming event_type validation for run_for_event_type()."""

    def test_none_event_type_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="event_type must be str"):
            orch.run_for_event_type(_ctx(), None)  # type: ignore[arg-type]

    def test_int_event_type_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="event_type must be str"):
            orch.run_for_event_type(_ctx(), 42)  # type: ignore[arg-type]

    def test_empty_event_type_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(ValueError, match="event_type must not be empty"):
            orch.run_for_event_type(_ctx(), "")

    def test_whitespace_event_type_rejected(self) -> None:
        registry = DetectorRegistry()
        orch = DetectorOrchestrator(registry)
        with pytest.raises(ValueError, match="event_type must not be empty"):
            orch.run_for_event_type(_ctx(), "   ")

    def test_bad_event_type_does_not_trigger_detect(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(
            detector_id="d1", event_types=("EVT",), results=[_res()]
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError):
            orch.run_for_event_type(_ctx(), None)  # type: ignore[arg-type]
        assert detector._call_count == 0


# ==============================================================================
# Invalid detect() result tests
# ==============================================================================


class TestInvalidDetectResult:
    """Tests confirming orchestrator validates detect() return values."""

    def test_none_result_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad")
        detector._results = None  # type: ignore[assignment]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must return list"):
            orch.run_all(_ctx())

    def test_tuple_result_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad", results=(_res(),))  # type: ignore[arg-type]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must return list"):
            orch.run_all(_ctx())

    def test_generator_result_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad", results=iter([_res()]))  # type: ignore[arg-type]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must return list"):
            orch.run_all(_ctx())

    def test_set_result_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad", results={_res()})  # type: ignore[arg-type]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must return list"):
            orch.run_all(_ctx())

    def test_single_detection_result_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad", results=_res())  # type: ignore[arg-type]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="must return list"):
            orch.run_all(_ctx())

    def test_list_containing_none_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad", results=[None])  # type: ignore[list-item]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="non-DetectionResult"):
            orch.run_all(_ctx())

    def test_list_containing_string_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="bad", results=["not_a_result"])  # type: ignore[list-item]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="non-DetectionResult"):
            orch.run_all(_ctx())

    def test_list_with_valid_and_invalid_element_rejected(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(
            detector_id="bad", results=[_res(), "bad_element"]  # type: ignore[list-item]
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="non-DetectionResult"):
            orch.run_all(_ctx())

    def test_error_message_contains_detector_id(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="my_bad_detector")
        detector._results = None  # type: ignore[assignment]
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError, match="my_bad_detector"):
            orch.run_all(_ctx())

    def test_subsequent_detectors_not_called_after_bad_result(self) -> None:
        registry = DetectorRegistry()
        bad = StubDetector(detector_id="bad")
        bad._results = None  # type: ignore[assignment]
        good = StubDetector(detector_id="good")
        registry.register(bad)
        registry.register(good)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError):
            orch.run_all(_ctx())
        assert good._call_count == 0

    def test_no_partial_results_returned(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1")
        bad = StubDetector(detector_id="bad")
        bad._results = None  # type: ignore[assignment]
        registry.register(d1)
        registry.register(bad)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TypeError):
            orch.run_all(_ctx())


# ==============================================================================
# Exception propagation tests
# ==============================================================================


class TestExceptionPropagation:
    """Tests confirming exceptions from detect() propagate unchanged."""

    class _TestException(Exception):
        """Custom exception for testing (not collected by pytest)."""
        pass

    def test_exception_from_first_detector_propagates(self) -> None:
        registry = DetectorRegistry()
        exc = TestExceptionPropagation._TestException("detector failure")
        detector = StubDetector(detector_id="bad", raise_exc=exc)
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TestExceptionPropagation._TestException, match="detector failure"):
            orch.run_all(_ctx())

    def test_exception_from_later_detector_propagates(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", results=[_res()])
        exc = TestExceptionPropagation._TestException("later failure")
        d2 = StubDetector(detector_id="d2", raise_exc=exc)
        registry.register(d1)
        registry.register(d2)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TestExceptionPropagation._TestException, match="later failure"):
            orch.run_all(_ctx())

    def test_subsequent_detectors_not_called_after_exception(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", results=[_res()])
        exc = TestExceptionPropagation._TestException("stop here")
        d2 = StubDetector(detector_id="d2", raise_exc=exc)
        d3 = StubDetector(detector_id="d3", results=[_res()])
        registry.register(d1)
        registry.register(d2)
        registry.register(d3)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TestExceptionPropagation._TestException):
            orch.run_all(_ctx())
        assert d1._call_count == 1
        assert d2._call_count == 1
        assert d3._call_count == 0

    def test_exception_not_converted_to_typeerror(self) -> None:
        """Confirm that an exception from detect() is not wrapped in TypeError."""
        registry = DetectorRegistry()
        exc = ValueError("real detect error")
        detector = StubDetector(detector_id="d1", raise_exc=exc)
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(ValueError, match="real detect error"):
            orch.run_all(_ctx())

    def test_orchestrator_does_not_retry(self) -> None:
        registry = DetectorRegistry()
        exc = TestExceptionPropagation._TestException("no retry")
        detector = StubDetector(detector_id="d1", raise_exc=exc)
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TestExceptionPropagation._TestException):
            orch.run_all(_ctx())
        assert detector._call_count == 1

    def test_run_for_event_type_also_propagates_exception(self) -> None:
        registry = DetectorRegistry()
        exc = TestExceptionPropagation._TestException("event type failure")
        detector = StubDetector(
            detector_id="d1", event_types=("EVT",), raise_exc=exc
        )
        registry.register(detector)
        orch = DetectorOrchestrator(registry)
        with pytest.raises(TestExceptionPropagation._TestException):
            orch.run_for_event_type(_ctx(), "EVT")


# ==============================================================================
# Forbidden responsibility tests
# ==============================================================================


class TestForbiddenMethods:
    """Confirm DetectorOrchestrator does not implement forbidden methods."""

    _FORBIDDEN = frozenset({
        "register",
        "unregister",
        "discover",
        "reload",
        "dispatch",
        "execute",
        "detect_all",
        "run_parallel",
        "run_async",
        "retry",
        "filter_results",
        "sort_results",
        "deduplicate",
    })

    def test_no_forbidden_methods_on_class(self) -> None:
        public_methods = {
            name for name in dir(DetectorOrchestrator)
            if not name.startswith("_")
            and callable(getattr(DetectorOrchestrator, name))
        }
        found = public_methods & self._FORBIDDEN
        assert not found, f"Forbidden methods found: {found}"

    def test_no_any_in_source(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "Any" not in source, "DetectorOrchestrator must not contain Any"

    def test_no_args_kwargs_in_init(self) -> None:
        sig = inspect.signature(DetectorOrchestrator.__init__)
        params = list(sig.parameters.values())[1:]  # skip self
        for p in params:
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ), "__init__ must not accept *args or **kwargs"

    def test_no_async_methods(self) -> None:
        for name in dir(DetectorOrchestrator):
            if name.startswith("_"):
                continue
            attr = getattr(DetectorOrchestrator, name)
            if callable(attr):
                assert not inspect.iscoroutinefunction(
                    attr
                ), f"Method {name} is async — not allowed"

    def test_no_asyncio_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "asyncio" not in source

    def test_no_concurrent_futures_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "concurrent" not in source
        assert "futures" not in source

    def test_no_multiprocessing_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "multiprocessing" not in source

    def test_no_threading_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "threading" not in source

    def test_no_copy_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "copy" not in source
        assert "deepcopy" not in source

    def test_no_master_engine_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "MasterEngine" not in source

    def test_no_runtime_service_import(self) -> None:
        source = inspect.getsource(DetectorOrchestrator)
        assert "RuntimeService" not in source


# ==============================================================================
# Integration test — import via Public API
# ==============================================================================


class TestPublicApiIntegration:
    """Verify DetectorOrchestrator is accessible via Public API."""

    def test_import_from_engines_detectors(self) -> None:
        from engines.detectors import DetectorOrchestrator as DO
        assert DO is DetectorOrchestrator

    def test_all_exports_includes_orchestrator(self) -> None:
        from engines.detectors import __all__
        assert "DetectorOrchestrator" in __all__

    def test_all_imports_work(self) -> None:
        from engines.detectors import (
            BaseDetector,
            DetectionContext,
            DetectionResult,
            DetectorOrchestrator,
            DetectorRegistry,
        )
        assert DetectorOrchestrator is not None
        assert BaseDetector is not None
        assert DetectionContext is not None
        assert DetectionResult is not None
        assert DetectorRegistry is not None