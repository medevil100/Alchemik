"""
RegulatoryEventDetector — detects regulatory market events.

Implements the scaffold for events from the REGULATORY family (~3 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data.  Regulatory events require external data sources (ESPI, EBI,
regulatory filings) which are not present in the current contract.

All 3 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended or external regulatory
data sources (ESPI/EBI API) are integrated.

Events declared (3 / 3 total — all [Future])
----------------------------------------------
    ESPI_FILING, EBI_FILING, FILING_DELAY

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Regulatory Event Detector
"""

from __future__ import annotations

from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    "ESPI_FILING",
    "EBI_FILING",
    "FILING_DELAY",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class RegulatoryEventDetector(BaseDetector):
    """
    Detector for the REGULATORY event family (3 declared events).

    All 3 events require ESPI/EBI regulatory filing data not present in
    the current DetectionContext.  The detector's ``detect()`` returns
    ``[]`` — correct analysis, no detection — until the context or
    external data sources are extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when ESPI/EBI data is available.
    """

    def __init__(self) -> None:
        pass

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "regulatory"

    @property
    def name(self) -> str:
        return "Regulatory Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run regulatory detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        regulatory data (ESPI, EBI filings) is not available in
        DetectionContext.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        return []