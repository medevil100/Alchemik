"""
DetectorOrchestrator — minimal orchestration layer for the detector framework.

The orchestrator receives a populated ``DetectorRegistry`` and a validated
``DetectionContext``, iterates over the selected detectors, calls their
``detect()`` method, validates the returned collections, and returns
all results as a single flat tuple.

This orchestrator does **not**:
- create or modify ``DetectionContext``,
- modify detectors or their results,
- classify, sort, filter, or deduplicate results,
- create ``MarketEvent`` instances,
- map ``EventFamily``, ``event_category``, ``event_subcategory``,
- fetch market data,
- communicate with the database,
- send alerts,
- perform retries,
- execute detectors in parallel,
- use async.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11 (Detector Framework)
"""

from __future__ import annotations

from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.registry import DetectorRegistry
from engines.detectors.result import DetectionResult


class DetectorOrchestrator:
    """
    Minimal orchestrator that runs detectors from a ``DetectorRegistry``.

    The orchestrator receives a fully constructed registry and calls
    ``detect()`` on selected detectors, collecting and flattening their
    results into a single immutable tuple.

    Usage::

        registry = DetectorRegistry()
        registry.register(my_detector)
        orchestrator = DetectorOrchestrator(registry)
        results = orchestrator.run_all(context)
        # or:
        results = orchestrator.run_for_event_type(context, "PRICE_SURGE")
    """

    def __init__(self, registry: DetectorRegistry) -> None:
        """
        Initialize the orchestrator with an existing ``DetectorRegistry``.

        Args:
            registry: A fully constructed ``DetectorRegistry`` instance.
                Must not be ``None``.

        Raises:
            TypeError: If ``registry`` is not a ``DetectorRegistry`` instance.
        """
        if not isinstance(registry, DetectorRegistry):
            raise TypeError(
                "registry must be a DetectorRegistry instance, "
                f"got {type(registry).__name__}"
            )
        self._registry: DetectorRegistry = registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(
        self,
        context: DetectionContext,
    ) -> tuple[DetectionResult, ...]:
        """
        Run all registered detectors against the given context.

        Detectors are executed in registration order.  The results of each
        detector are concatenated in order, producing a single flat tuple.

        Args:
            context: A fully validated ``DetectionContext``.

        Returns:
            ``tuple[DetectionResult, ...]`` — an empty tuple if no detectors
            are registered or all detectors return ``[]``.

        Raises:
            TypeError: If ``context`` is not a ``DetectionContext``, or if
                a detector returns an invalid collection or invalid elements.
            Exception: Exceptions raised by ``detector.detect()`` propagate
                unchanged.
        """
        self._validate_context(context)
        detectors = self._registry.get_all()
        return self._run(detectors, context)

    def run_for_event_type(
        self,
        context: DetectionContext,
        event_type: str,
    ) -> tuple[DetectionResult, ...]:
        """
        Run only the detectors that can handle the given ``event_type``.

        Detectors are selected by ``registry.get_for_event_type(event_type)``
        and executed in registration order.

        Args:
            context: A fully validated ``DetectionContext``.
            event_type: The event type identifier (e.g. ``"PRICE_SURGE"``).

        Returns:
            ``tuple[DetectionResult, ...]`` — an empty tuple if no detector
            matches ``event_type`` or all matching detectors return ``[]``.

        Raises:
            TypeError: If ``context`` is not a ``DetectionContext``,
                if ``event_type`` is invalid (validated by the registry),
                or if a detector returns an invalid collection or elements.
            RuntimeError: Exceptions raised by ``detector.detect()``
                propagate unchanged.
        """
        self._validate_context(context)
        detectors = self._registry.get_for_event_type(event_type)
        return self._run(detectors, context)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_context(context: object) -> None:
        """Validate that *context* is a ``DetectionContext`` instance."""
        if not isinstance(context, DetectionContext):
            raise TypeError(
                "context must be a DetectionContext instance, "
                f"got {type(context).__name__}"
            )

    @staticmethod
    def _validate_detector_result(
        results: object,
        detector_id: str,
    ) -> list[DetectionResult]:
        """
        Validate the return value of ``detector.detect()``.

        The validated ``list[DetectionResult]`` is returned unchanged
        (the same list object, not a duplicate).

        Args:
            results: The value returned by ``detect()``.
            detector_id: The ``detector_id`` of the detector (used in error
                messages).

        Returns:
            The validated ``list[DetectionResult]`` (same object).

        Raises:
            TypeError: If *results* is not a ``list``, or if some element
                is not a ``DetectionResult`` instance.
        """
        if not isinstance(results, list):
            raise TypeError(
                f"Detector {detector_id!r} must return list[DetectionResult], "
                f"got {type(results).__name__}"
            )

        for idx, item in enumerate(results):
            if not isinstance(item, DetectionResult):
                raise TypeError(
                    f"Detector {detector_id!r} returned a non-DetectionResult "
                    f"at position {idx}: got {type(item).__name__}"
                )

        return results

    @staticmethod
    def _run(
        detectors: tuple[BaseDetector, ...],
        context: DetectionContext,
    ) -> tuple[DetectionResult, ...]:
        """
        Execute *detectors* in order and flatten their results.

        Args:
            detectors: Ordered tuple of ``BaseDetector`` instances.
            context: The validated ``DetectionContext`` to pass to each.

        Returns:
            ``tuple[DetectionResult, ...]`` — flat tuple of all results.

        Raises:
            TypeError: If a detector returns invalid output.
            Exceptions from ``detect()`` propagate unchanged.
        """
        all_results: list[DetectionResult] = []
        for detector in detectors:
            raw = detector.detect(context)
            validated = DetectorOrchestrator._validate_detector_result(
                raw, detector.detector_id
            )
            all_results.extend(validated)
        return tuple(all_results)