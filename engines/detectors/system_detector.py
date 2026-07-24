"""
SystemEventDetector — detects system-level and composite market events.

Implements the scaffold for events from the SYSTEM family (~12 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data for a single instrument.  System events require cross-instrument
data, historical event archives, sector/seasonal data, and correlation
matrices which are not present in the current contract.

All 12 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (12 / 12 total — all [Future])
-----------------------------------------------
    COMPOSITE_EVENT, INSTRUMENT_STATE_CHANGE, RECURRING_PATTERN,
    CROSS_INSTRUMENT_CORRELATION, SECTOR_ROTATION, SEASONAL_PATTERN,
    CORRELATION_BREAKDOWN, VOLUME_ANOMALY_CLUSTER, PRICE_VOLUME_DIVERGENCE,
    MULTIPLE_DETECTOR_CONFIRMATION, ADVANCED_DECLINE_RATIO,
    MARKET_BREADTH_CHANGE

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § System Event Detector
"""

from __future__ import annotations

from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    "COMPOSITE_EVENT",
    "INSTRUMENT_STATE_CHANGE",
    "RECURRING_PATTERN",
    "CROSS_INSTRUMENT_CORRELATION",
    "SECTOR_ROTATION",
    "SEASONAL_PATTERN",
    "CORRELATION_BREAKDOWN",
    "VOLUME_ANOMALY_CLUSTER",
    "PRICE_VOLUME_DIVERGENCE",
    "MULTIPLE_DETECTOR_CONFIRMATION",
    "ADVANCED_DECLINE_RATIO",
    "MARKET_BREADTH_CHANGE",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class SystemEventDetector(BaseDetector):
    """
    Detector for the SYSTEM event family (12 declared events).

    All 12 events require system-level/cross-instrument data not present
    in the current DetectionContext (multi-instrument OHLCV, event
    archives, sector/seasonal data, correlation matrices).  The detector's
    ``detect()`` returns ``[]`` — correct analysis, no detection — until
    the context is extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when system-level data is available.
    """

    def __init__(self) -> None:
        pass

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "system"

    @property
    def name(self) -> str:
        return "System Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run system-level detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        system-level data (multi-instrument OHLCV, event archives,
        sector/seasonal data, correlation matrices) is not available
        in DetectionContext.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with
            single-instrument OHLCV data alone.
        """
        return []