"""
ETFEventDetector — detects ETF-related market events.

Implements the scaffold for events from the ETF family (~4 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data.  ETF events require external data sources (ETF composition
data, flow data, NAV/market price data) which are not present in the
current contract.

All 4 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (4 / 4 total — all [Future])
----------------------------------------------
    ETF_COMPOSITION_CHANGE, ETF_FLOW_SPIKE, ETF_PREMIUM_DISCOUNT,
    ETF_CLOSURE_ANNOUNCEMENT

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § ETF Event Detector
"""

from __future__ import annotations

from config.etf_events import DEFAULT_ETF_CONFIG, ETFEventsConfig
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    "ETF_COMPOSITION_CHANGE",
    "ETF_FLOW_SPIKE",
    "ETF_PREMIUM_DISCOUNT",
    "ETF_CLOSURE_ANNOUNCEMENT",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class ETFEventDetector(BaseDetector):
    """
    Detector for the ETF event family (4 declared events).

    All 4 events require ETF-specific data not present in the current
    DetectionContext (composition, flows, NAV vs market price).  The
    detector's ``detect()`` returns ``[]`` — correct analysis, no
    detection — until the context is extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when ETF data sources are available.
    """

    def __init__(self, config: ETFEventsConfig | None = None) -> None:
        self._config = config or DEFAULT_ETF_CONFIG

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "etf"

    @property
    def name(self) -> str:
        return "ETF Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run ETF detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        ETF data (composition, flows, NAV/market price) is not available
        in DetectionContext.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        return []