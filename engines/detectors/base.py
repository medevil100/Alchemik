"""
BaseDetector — abstract interface for all market event detectors.

All concrete detector implementations must inherit from BaseDetector
and implement its abstract methods.  This ensures a uniform API
across all detector types in the ALCHEMIK system.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11.6
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


class BaseDetector(ABC):
    """
    Abstract base class for all market event detectors.

    Subclasses must implement:
        - detector_id  (property → str)
        - name         (property → str)
        - event_types  (property → tuple[str, ...])
        - detect()     (method  → list[DetectionResult])

    ``can_handle()`` is a concrete utility that checks membership in
    ``event_types``.
    """

    # ------------------------------------------------------------------
    # Abstract properties
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def detector_id(self) -> str:
        """
        Unique identifier for this detector.

        Returns:
            A string key used by DetectorRegistry for lookup.
            Example: ``"technical_volatility"``
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable name of this detector.

        Returns:
            A display-friendly name such as ``"Technical Volatility Detector"``.
        """
        ...

    @property
    @abstractmethod
    def event_types(self) -> tuple[str, ...]:
        """
        Immutable tuple of event type identifiers this detector can emit.

        Every value must exist in ``docs/Katalog_Zdarzen_Rynkowych.md``.

        Returns:
            A tuple of event type strings, e.g.
            ``("VOLATILITY_SPIKE", "BB_SQUEEZE")``.
        """
        ...

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run detection logic on the given context.

        Preconditions:
            - ``context.ohlcv_data`` is non-empty.
            - ``context`` passes all structural validations from
              ``DetectionContext.__post_init__``.

        The orchestrator must not call ``detect()`` without a valid context.

        Args:
            context: A fully-validated ``DetectionContext``.

        Returns:
            ``list[DetectionResult]`` — an empty list ``[]`` means the
            analysis completed successfully but no events were detected.
        """
        ...

    # ------------------------------------------------------------------
    # Concrete utility methods
    # ------------------------------------------------------------------

    def can_handle(self, event_type: str) -> bool:
        """
        Check whether this detector can handle the given event type.

        Args:
            event_type: An event type string from the event catalogue.

        Returns:
            ``True`` if ``event_type`` is in ``self.event_types``,
            ``False`` otherwise.
        """
        return event_type in self.event_types