"""
Tests for DetectorRegistry — ETAP 6 — Krok 2.

Covers:
    - Construction (empty registry)
    - Valid registration
    - Invalid registration (all validation branches)
    - get() behaviour
    - contains() behaviour
    - get_all() behaviour
    - get_for_event_type() behaviour
    - Collection protection
    - Forbidden responsibilities
    - Overlapping event_types
    - Registration order preservation

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11
"""

from __future__ import annotations

import inspect

import pytest

from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.registry import DetectorRegistry
from engines.detectors.result import DetectionResult


# ==============================================================================
# Stub detector for testing
# ==============================================================================


class StubDetector(BaseDetector):
    """
    Minimal concrete detector for registry tests.

    Provides explicit detector_id, name, event_types, and a simple detect()
    that does nothing (returns []).
    """

    def __init__(
        self,
        detector_id: str = "stub",
        name: str = "Stub Detector",
        event_types: tuple[str, ...] = ("EVENT_X",),
    ) -> None:
        self._detector_id = detector_id
        self._name = name
        self._event_types = event_types
        self._detect_called = False

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
        self._detect_called = True
        return []


# ==============================================================================
# Construction tests
# ==============================================================================


class TestConstruction:
    """Tests for registry creation and initial state."""

    def test_empty_registry_can_be_created(self) -> None:
        registry = DetectorRegistry()
        assert isinstance(registry, DetectorRegistry)

    def test_empty_registry_len_zero(self) -> None:
        registry = DetectorRegistry()
        assert len(registry) == 0

    def test_empty_registry_get_all_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        result = registry.get_all()
        assert result == ()
        assert isinstance(result, tuple)

    def test_empty_registry_get_for_event_type_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        result = registry.get_for_event_type("ANY_EVENT")
        assert result == ()
        assert isinstance(result, tuple)


# ==============================================================================
# Valid registration tests
# ==============================================================================


class TestValidRegistration:
    """Tests for successful detector registration."""

    def test_valid_detector_can_be_registered(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1")
        registry.register(detector)
        assert len(registry) == 1

    def test_after_registration_len_is_one(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector()
        registry.register(detector)
        assert len(registry) == 1

    def test_contains_returns_true_for_registered(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="my_id")
        registry.register(detector)
        assert registry.contains("my_id") is True

    def test_get_returns_exact_same_instance(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1")
        registry.register(detector)
        assert registry.get("d1") is detector

    def test_get_all_returns_tuple(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector()
        registry.register(detector)
        result = registry.get_all()
        assert isinstance(result, tuple)

    def test_get_all_contains_registered_instance(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector()
        registry.register(detector)
        result = registry.get_all()
        assert result == (detector,)
        assert result[0] is detector

    def test_multiple_detectors_preserve_registration_order(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="first", name="First")
        d2 = StubDetector(detector_id="second", name="Second")
        d3 = StubDetector(detector_id="third", name="Third")
        registry.register(d1)
        registry.register(d2)
        registry.register(d3)
        assert registry.get_all() == (d1, d2, d3)

    def test_register_does_not_call_detect(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector()
        registry.register(detector)
        assert detector._detect_called is False


# ==============================================================================
# Invalid registration tests
# ==============================================================================


class TestInvalidRegistration:
    """Tests for rejected registrations."""

    # -- wrong type -----------------------------------------------------------

    def test_register_none_raises_typeerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="must be an instance of BaseDetector"):
            registry.register(None)  # type: ignore[arg-type]

    def test_register_class_instead_of_instance(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="must be an instance of BaseDetector"):
            registry.register(StubDetector)  # type: ignore[arg-type]

    def test_register_arbitrary_object(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="must be an instance of BaseDetector"):
            registry.register("not_a_detector")  # type: ignore[arg-type]

    # -- detector_id ---------------------------------------------------------

    def test_detector_id_wrong_type_raises_typeerror(self) -> None:
        class BadId(StubDetector):
            @property
            def detector_id(self) -> int:  # type: ignore[override]
                return 42  # type: ignore[return-value]

        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="detector_id must be str"):
            registry.register(BadId(detector_id=42))  # type: ignore[arg-type]

    def test_empty_detector_id_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="")
        with pytest.raises(ValueError, match="detector_id must not be empty"):
            registry.register(detector)

    def test_whitespace_detector_id_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="   ")
        with pytest.raises(ValueError, match="detector_id must not be empty"):
            registry.register(detector)

    # -- name ----------------------------------------------------------------

    def test_name_wrong_type_raises_typeerror(self) -> None:
        class BadName(StubDetector):
            @property
            def name(self) -> int:  # type: ignore[override]
                return 123  # type: ignore[return-value]

        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="detector.name must be str"):
            registry.register(BadName(detector_id="x", name=123))  # type: ignore[arg-type]

    def test_empty_name_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="x", name="")
        with pytest.raises(ValueError, match="detector.name must not be empty"):
            registry.register(detector)

    def test_whitespace_name_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="x", name="  ")
        with pytest.raises(ValueError, match="detector.name must not be empty"):
            registry.register(detector)

    # -- event_types ---------------------------------------------------------

    def test_event_types_list_raises_typeerror(self) -> None:
        class BadETS(StubDetector):
            @property
            def event_types(self) -> tuple[str, ...]:
                return ["A"]  # type: ignore[return-value]

        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="event_types must be tuple"):
            registry.register(BadETS())

    def test_event_types_single_string_raises_typeerror(self) -> None:
        class BadETS(StubDetector):
            @property
            def event_types(self) -> tuple[str, ...]:
                return "EVENT"  # type: ignore[return-value]

        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="event_types must be tuple"):
            registry.register(BadETS())

    def test_event_types_empty_tuple_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(event_types=())
        with pytest.raises(ValueError, match="event_types must not be empty"):
            registry.register(detector)

    def test_event_types_element_wrong_type_raises_typeerror(self) -> None:
        class BadElem(StubDetector):
            @property
            def event_types(self) -> tuple:  # type: ignore[override]
                return (42,)  # type: ignore[return-value]

        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="event_types\\[0\\] must be str"):
            registry.register(BadElem())

    def test_event_types_empty_element_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(event_types=("",))
        with pytest.raises(ValueError, match="event_types\\[0\\] must not be empty"):
            registry.register(detector)

    def test_event_types_whitespace_element_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(event_types=("  ",))
        with pytest.raises(ValueError, match="event_types\\[0\\] must not be empty"):
            registry.register(detector)

    def test_event_types_duplicates_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(event_types=("A", "B", "A"))
        with pytest.raises(ValueError, match="duplicate"):
            registry.register(detector)

    # -- duplicate detector_id -----------------------------------------------

    def test_same_detector_id_twice_raises_keyerror(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="unique")
        registry.register(d1)
        with pytest.raises(KeyError, match="already registered"):
            registry.register(d1)

    def test_different_object_same_detector_id_raises_keyerror(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="dup")
        d2 = StubDetector(detector_id="dup", name="Different")
        registry.register(d1)
        with pytest.raises(KeyError, match="already registered"):
            registry.register(d2)


# ==============================================================================
# get() tests
# ==============================================================================


class TestGet:
    """Tests for DetectorRegistry.get()."""

    def test_get_returns_registered_detector(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="get_me")
        registry.register(detector)
        assert registry.get("get_me") is detector

    def test_get_missing_detector_raises_keyerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(KeyError, match="No detector registered"):
            registry.get("nonexistent")

    def test_get_empty_string_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(ValueError, match="detector_id must not be empty"):
            registry.get("")

    def test_get_whitespace_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(ValueError, match="detector_id must not be empty"):
            registry.get("  ")

    def test_get_wrong_type_raises_typeerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="detector_id must be str"):
            registry.get(123)  # type: ignore[arg-type]

    def test_get_returns_same_instance(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="same")
        registry.register(detector)
        r1 = registry.get("same")
        r2 = registry.get("same")
        assert r1 is r2 is detector


# ==============================================================================
# contains() tests
# ==============================================================================


class TestContains:
    """Tests for DetectorRegistry.contains()."""

    def test_contains_true_for_registered(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="yes")
        registry.register(detector)
        assert registry.contains("yes") is True

    def test_contains_false_for_valid_but_missing(self) -> None:
        registry = DetectorRegistry()
        assert registry.contains("no_such_id") is False

    def test_contains_wrong_type_raises_typeerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="detector_id must be str"):
            registry.contains(None)  # type: ignore[arg-type]

    def test_contains_empty_string_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(ValueError, match="detector_id must not be empty"):
            registry.contains("")

    def test_contains_does_not_modify_registry(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="a")
        registry.register(detector)
        registry.contains("missing")
        assert len(registry) == 1
        assert registry.get("a") is detector


# ==============================================================================
# get_for_event_type() tests
# ==============================================================================


class TestGetForEventType:
    """Tests for DetectorRegistry.get_for_event_type()."""

    def test_empty_registry_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        result = registry.get_for_event_type("EVENT_X")
        assert result == ()
        assert isinstance(result, tuple)

    def test_no_match_returns_empty_tuple(self) -> None:
        registry = DetectorRegistry()
        registry.register(StubDetector(detector_id="d1", event_types=("EVENT_A",)))
        result = registry.get_for_event_type("EVENT_Z")
        assert result == ()

    def test_single_match_returns_single_detector(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", event_types=("EVENT_A", "EVENT_B"))
        registry.register(detector)
        result = registry.get_for_event_type("EVENT_A")
        assert result == (detector,)

    def test_multiple_matches_returns_all(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", event_types=("EVENT_A",))
        d2 = StubDetector(detector_id="d2", event_types=("EVENT_A",))
        registry.register(d1)
        registry.register(d2)
        result = registry.get_for_event_type("EVENT_A")
        assert result == (d1, d2)

    def test_multiple_matches_preserve_registration_order(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="alpha", event_types=("SHARED",))
        d2 = StubDetector(detector_id="beta", event_types=("SHARED",))
        d3 = StubDetector(detector_id="gamma", event_types=("SHARED",))
        registry.register(d1)
        registry.register(d2)
        registry.register(d3)
        result = registry.get_for_event_type("SHARED")
        assert result == (d1, d2, d3)

    def test_can_handle_is_used(self) -> None:
        """
        Verify that get_for_event_type uses can_handle(),
        not direct event_types membership.
        """
        class CustomHandle(StubDetector):
            def can_handle(self, event_type: str) -> bool:
                # Override to always return True regardless of event_types
                return True

        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", event_types=("EVENT_A",))
        d2 = CustomHandle(detector_id="d2", event_types=("EVENT_B",))
        registry.register(d1)
        registry.register(d2)
        # "EVENT_A" should match both: d1 via event_types, d2 via CustomHandle
        result = registry.get_for_event_type("EVENT_A")
        assert d1 in result
        assert d2 in result
        assert result == (d1, d2)

    def test_get_for_event_type_does_not_call_detect(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", event_types=("EVENT_A",))
        registry.register(detector)
        registry.get_for_event_type("EVENT_A")
        assert detector._detect_called is False

    def test_get_for_event_type_wrong_type_raises_typeerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(TypeError, match="event_type must be str"):
            registry.get_for_event_type(123)  # type: ignore[arg-type]

    def test_get_for_event_type_empty_string_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(ValueError, match="event_type must not be empty"):
            registry.get_for_event_type("")

    def test_get_for_event_type_whitespace_raises_valueerror(self) -> None:
        registry = DetectorRegistry()
        with pytest.raises(ValueError, match="event_type must not be empty"):
            registry.get_for_event_type("  ")

    def test_overlapping_event_types_allowed(self) -> None:
        """Two detectors with the same event_type are both returned."""
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1", event_types=("PRICE_SURGE",))
        d2 = StubDetector(detector_id="d2", event_types=("PRICE_SURGE",))
        registry.register(d1)
        registry.register(d2)
        result = registry.get_for_event_type("PRICE_SURGE")
        assert len(result) == 2
        assert d1 in result
        assert d2 in result


# ==============================================================================
# Collection protection tests
# ==============================================================================


class TestCollectionProtection:
    """Tests confirming the registry protects its internal state."""

    def test_get_all_returns_tuple(self) -> None:
        registry = DetectorRegistry()
        assert isinstance(registry.get_all(), tuple)

    def test_get_for_event_type_returns_tuple(self) -> None:
        registry = DetectorRegistry()
        assert isinstance(registry.get_for_event_type("X"), tuple)

    def test_get_all_with_detectors_returns_tuple(self) -> None:
        registry = DetectorRegistry()
        registry.register(StubDetector())
        assert isinstance(registry.get_all(), tuple)

    def test_get_for_event_type_with_match_returns_tuple(self) -> None:
        registry = DetectorRegistry()
        registry.register(StubDetector(event_types=("MATCH_ME",)))
        assert isinstance(registry.get_for_event_type("MATCH_ME"), tuple)

    def test_local_collection_mutation_does_not_affect_registry(self) -> None:
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1")
        d2 = StubDetector(detector_id="d2")
        registry.register(d1)
        registry.register(d2)
        # Try to modify a local copy
        items = list(registry.get_all())
        items.pop()
        assert len(registry) == 2

    def test_internal_dict_is_not_returned(self) -> None:
        """get_all() must return a tuple, not the internal dict."""
        registry = DetectorRegistry()
        registry.register(StubDetector())
        result = registry.get_all()
        assert not isinstance(result, dict)
        assert isinstance(result, tuple)

    def test_registered_instances_are_preserved(self) -> None:
        """The exact registered instances are returned (no copies)."""
        registry = DetectorRegistry()
        d1 = StubDetector(detector_id="d1")
        d2 = StubDetector(detector_id="d2")
        registry.register(d1)
        registry.register(d2)
        all_detectors = registry.get_all()
        assert all_detectors[0] is d1
        assert all_detectors[1] is d2


# ==============================================================================
# Forbidden responsibility tests
# ==============================================================================


class TestForbiddenMethods:
    """Confirm DetectorRegistry does not implement forbidden methods."""

    _FORBIDDEN = frozenset({
        "run_all",
        "detect_all",
        "execute",
        "dispatch",
        "discover",
        "reload",
        "unregister",
        "clear",
        "replace",
    })

    def test_registry_has_no_forbidden_methods(self) -> None:
        public_methods = {
            name for name in dir(DetectorRegistry)
            if not name.startswith("_")
            and callable(getattr(DetectorRegistry, name))
        }
        found = public_methods & self._FORBIDDEN
        assert not found, f"Forbidden methods found: {found}"

    def test_register_does_not_call_detect(self) -> None:
        """Confirm register() never invokes detect() on the detector."""
        registry = DetectorRegistry()
        detector = StubDetector()
        registry.register(detector)
        assert detector._detect_called is False

    def test_get_for_event_type_does_not_call_detect(self) -> None:
        registry = DetectorRegistry()
        detector = StubDetector(detector_id="d1", event_types=("EVENT_A",))
        registry.register(detector)
        registry.get_for_event_type("EVENT_A")
        assert detector._detect_called is False

    def test_no_kwargs_in_init(self) -> None:
        sig = inspect.signature(DetectorRegistry.__init__)
        params = list(sig.parameters.values())[1:]  # skip self
        for p in params:
            assert p.kind not in (
                inspect.Parameter.VAR_KEYWORD,
            ), "__init__ must not accept **kwargs"

    def test_no_any_in_registry_source(self) -> None:
        source = inspect.getsource(DetectorRegistry)
        assert "Any" not in source, "DetectorRegistry must not contain Any"

    def test_public_api_has_no_any(self) -> None:
        """Inspect public method signatures for Any."""
        for name in dir(DetectorRegistry):
            if name.startswith("_"):
                continue
            attr = getattr(DetectorRegistry, name)
            if not callable(attr):
                continue
            try:
                sig = inspect.signature(attr)
            except (ValueError, TypeError):
                continue
            sig_str = str(sig)
            assert "Any" not in sig_str, (
                f"Public method {name}() contains Any in signature: {sig_str}"
            )