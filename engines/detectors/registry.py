"""
DetectorRegistry — central registry for market event detector instances.

The registry stores instances of ``BaseDetector``, enforces uniqueness on
``detector_id``, validates detector attributes on registration, and provides
lookup methods for finding detectors by id or supported event type.

This registry does **not**:
- execute ``detect()``,
- create ``DetectionContext``,
- process ``DetectionResult``,
- perform orchestration,
- load modules dynamically,
- discover detectors from the filesystem,
- assign priorities or rankings.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11 (Detector Registry)
"""

from __future__ import annotations

from engines.detectors.base import BaseDetector


class DetectorRegistry:
    """
    Central registry for ``BaseDetector`` instances.

    The registry accepts already-instantiated detectors via ``register()``
    and provides lookup methods keyed by ``detector_id`` or supported
    ``event_type``.

    Usage::

        registry = DetectorRegistry()
        registry.register(detector)
        assert registry.get(detector.detector_id) is detector
        for d in registry.get_for_event_type("PRICE_SURGE"):
            ...
    """

    def __init__(self) -> None:
        self._detectors: dict[str, BaseDetector] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, detector: BaseDetector) -> None:
        """
        Register a detector instance.

        Args:
            detector: A fully constructed `BaseDetector` instance.

        Raises:
            TypeError: If ``detector`` is not a ``BaseDetector`` instance,
                or if ``detector.detector_id`` is not a ``str``,
                or if ``detector.name`` is not a ``str``,
                or if ``detector.event_types`` is not a ``tuple``.
            ValueError: If ``detector_id`` is empty or whitespace-only,
                or if ``name`` is empty or whitespace-only,
                or if ``event_types`` is an empty tuple,
                or if any element of ``event_types`` is not a non-empty
                ``str`` with at least one non-whitespace character,
                or if ``event_types`` contains duplicate entries.
            KeyError: If a detector with the same ``detector_id`` is already
                registered.
        """
        # -- Type check -------------------------------------------------------
        if not isinstance(detector, BaseDetector):
            raise TypeError(
                "detector must be an instance of BaseDetector, "
                f"got {type(detector).__name__}"
            )

        # -- detector_id ------------------------------------------------------
        did = detector.detector_id
        if not isinstance(did, str):
            raise TypeError(
                f"detector.detector_id must be str, got {type(did).__name__}"
            )
        if not did.strip():
            raise ValueError("detector.detector_id must not be empty or whitespace-only")

        # -- name -------------------------------------------------------------
        dname = detector.name
        if not isinstance(dname, str):
            raise TypeError(
                f"detector.name must be str, got {type(dname).__name__}"
            )
        if not dname.strip():
            raise ValueError("detector.name must not be empty or whitespace-only")

        # -- event_types ------------------------------------------------------
        ets = detector.event_types
        if not isinstance(ets, tuple):
            raise TypeError(
                f"detector.event_types must be tuple[str, ...], "
                f"got {type(ets).__name__}"
            )
        if len(ets) == 0:
            raise ValueError(
                "detector.event_types must not be empty; "
                "a detector must declare at least one supported event type"
            )

        seen: set[str] = set()
        for idx, et in enumerate(ets):
            if not isinstance(et, str):
                raise TypeError(
                    f"detector.event_types[{idx}] must be str, "
                    f"got {type(et).__name__}"
                )
            if not et.strip():
                raise ValueError(
                    f"detector.event_types[{idx}] must not be empty "
                    f"or whitespace-only"
                )
            if et in seen:
                raise ValueError(
                    f"detector.event_types contains duplicate: {et!r}"
                )
            seen.add(et)

        # -- duplicate check --------------------------------------------------
        if did in self._detectors:
            raise KeyError(
                f"Detector with detector_id={did!r} is already registered"
            )

        self._detectors[did] = detector

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, detector_id: str) -> BaseDetector:
        """
        Retrieve a detector by its unique ``detector_id``.

        Args:
            detector_id: The unique identifier of the desired detector.

        Returns:
            The registered ``BaseDetector`` instance.

        Raises:
            TypeError: If ``detector_id`` is not a ``str``.
            ValueError: If ``detector_id`` is empty or whitespace-only.
            KeyError: If no detector with the given ``detector_id`` is
                registered.
        """
        if not isinstance(detector_id, str):
            raise TypeError(
                f"detector_id must be str, got {type(detector_id).__name__}"
            )
        if not detector_id.strip():
            raise ValueError("detector_id must not be empty or whitespace-only")

        if detector_id not in self._detectors:
            raise KeyError(
                f"No detector registered with detector_id={detector_id!r}"
            )
        return self._detectors[detector_id]

    def contains(self, detector_id: str) -> bool:
        """
        Check whether a detector with the given ``detector_id`` is registered.

        Args:
            detector_id: The unique identifier to check.

        Returns:
            ``True`` if a detector with that id is registered, ``False``
            otherwise.

        Raises:
            TypeError: If ``detector_id`` is not a ``str``.
            ValueError: If ``detector_id`` is empty or whitespace-only.
        """
        if not isinstance(detector_id, str):
            raise TypeError(
                f"detector_id must be str, got {type(detector_id).__name__}"
            )
        if not detector_id.strip():
            raise ValueError("detector_id must not be empty or whitespace-only")

        return detector_id in self._detectors

    # ------------------------------------------------------------------
    # Bulk access
    # ------------------------------------------------------------------

    def get_all(self) -> tuple[BaseDetector, ...]:
        """
        Return all registered detectors as an immutable tuple.

        The order matches registration order (Python 3.7+ dict insertion
        order is preserved).

        Returns:
            ``tuple[BaseDetector, ...]`` — may be empty if no detectors
            are registered.
        """
        return tuple(self._detectors.values())

    def get_for_event_type(self, event_type: str) -> tuple[BaseDetector, ...]:
        """
        Return all registered detectors that can handle the given event type.

        Uses ``detector.can_handle(event_type)`` to determine eligibility.

        Args:
            event_type: An event type string (e.g. ``"PRICE_SURGE"``).

        Returns:
            ``tuple[BaseDetector, ...]`` — detectors in registration order.
            An empty tuple means no registered detector handles this type
            (this is not an error).

        Raises:
            TypeError: If ``event_type`` is not a ``str``.
            ValueError: If ``event_type`` is empty or whitespace-only.
        """
        if not isinstance(event_type, str):
            raise TypeError(
                f"event_type must be str, got {type(event_type).__name__}"
            )
        if not event_type.strip():
            raise ValueError("event_type must not be empty or whitespace-only")

        return tuple(
            d for d in self._detectors.values() if d.can_handle(event_type)
        )

    def __len__(self) -> int:
        """Return the number of registered detectors."""
        return len(self._detectors)