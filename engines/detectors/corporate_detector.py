"""
CorporateEventDetector — detects corporate market events.

Implements the scaffold for events from the CORPORATE family (~34 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data.  Corporate events require external data sources (ESPI, EBI,
SEC filings, insider trading reports, analyst recommendations, merger
announcements, contract filings, legal filings, bankruptcy announcements,
management change reports) which are not present in the current contract.

All 34 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (34 v1 / 34 total — all [Future])
---------------------------------------------------
Insider Trading (18.x):  INSIDER_BUY, INSIDER_SELL, INSIDER_CLUSTER_BUY,
    INSIDER_CLUSTER_SELL
Shareholder (19.x):      SHAREHOLDER_INCREASE, SHAREHOLDER_DECREASE,
    SIGNIFICANT_HOLDER_CHANGE
Recommendations (20.x):  ANALYST_UPGRADE, ANALYST_DOWNGRADE,
    PRICE_TARGET_INCREASE, PRICE_TARGET_DECREASE, NEW_COVERAGE,
    COVERAGE_DROPPED, RATING_CHANGE
Rating (21.x):           CREDIT_RATING_UPGRADE, CREDIT_RATING_DOWNGRADE,
    CREDIT_WATCH_POSITIVE, CREDIT_WATCH_NEGATIVE
M&A (22.x):              MERGER_ANNOUNCEMENT, ACQUISITION_ANNOUNCEMENT,
    TAKEOVER_BID, MERGER_COMPLETION, ACQUISITION_COMPLETION
Contracts (23.x):        MAJOR_CONTRACT_WIN, MAJOR_CONTRACT_LOSS
Legal (24.x):            LAWSUIT_FILED, SETTLEMENT_ANNOUNCED,
    REGULATORY_INVESTIGATION
Bankruptcy (25.x):       BANKRUPTCY_FILING, RESTRUCTURING_PLAN
Management (26.x):       CEO_CHANGE, CFO_CHANGE, BOARD_CHANGE,
    MANAGEMENT_SHAKEUP

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Corporate Event Detector
"""

from __future__ import annotations

from config.corporate_events import DEFAULT_CORPORATE_CONFIG, CorporateEventsConfig
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    # Insider Trading (18.x)
    "INSIDER_BUY",
    "INSIDER_SELL",
    "INSIDER_CLUSTER_BUY",
    "INSIDER_CLUSTER_SELL",
    # Shareholder Changes (19.x)
    "SHAREHOLDER_INCREASE",
    "SHAREHOLDER_DECREASE",
    "SIGNIFICANT_HOLDER_CHANGE",
    # Recommendations (20.x)
    "ANALYST_UPGRADE",
    "ANALYST_DOWNGRADE",
    "PRICE_TARGET_INCREASE",
    "PRICE_TARGET_DECREASE",
    "NEW_COVERAGE",
    "COVERAGE_DROPPED",
    "RATING_CHANGE",
    # Rating (21.x)
    "CREDIT_RATING_UPGRADE",
    "CREDIT_RATING_DOWNGRADE",
    "CREDIT_WATCH_POSITIVE",
    "CREDIT_WATCH_NEGATIVE",
    # M&A (22.x)
    "MERGER_ANNOUNCEMENT",
    "ACQUISITION_ANNOUNCEMENT",
    "TAKEOVER_BID",
    "MERGER_COMPLETION",
    "ACQUISITION_COMPLETION",
    # Contracts (23.x)
    "MAJOR_CONTRACT_WIN",
    "MAJOR_CONTRACT_LOSS",
    # Legal (24.x)
    "LAWSUIT_FILED",
    "SETTLEMENT_ANNOUNCED",
    "REGULATORY_INVESTIGATION",
    # Bankruptcy (25.x)
    "BANKRUPTCY_FILING",
    "RESTRUCTURING_PLAN",
    # Management (26.x)
    "CEO_CHANGE",
    "CFO_CHANGE",
    "BOARD_CHANGE",
    "MANAGEMENT_SHAKEUP",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class CorporateEventDetector(BaseDetector):
    """
    Detector for the CORPORATE event family (34 declared events).

    All 34 events require data not present in the current DetectionContext
    (ESPI, EBI, SEC filings, insider trading reports, etc.).  The
    detector's ``detect()`` returns ``[]`` — correct analysis, no
    detection — until the context is extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when DetectionContext is extended.
    """

    def __init__(self, config: CorporateEventsConfig | None = None) -> None:
        self._config = config or DEFAULT_CORPORATE_CONFIG

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "corporate"

    @property
    def name(self) -> str:
        return "Corporate Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run corporate detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        corporate data (ESPI, EBI, SEC filings, insider reports,
        recommendations, M&A announcements, contracts, legal filings,
        bankruptcy announcements, management changes) is not available
        in DetectionContext.

        The context is still validated by the orchestrator before this
        method is called — this method simply reports that no events
        were detected under current data constraints.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        return []