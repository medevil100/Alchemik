"""
FundamentalEventDetector — detects fundamental market events.

Implements detection for events from the FUNDAMENTAL family (24 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data (``ticker``, ``market``, ``instrument_type``, ``ohlcv_data``).
Fundamental events require ``ticker.info`` (trailingPE, forwardPE,
priceToBook, marketCap, debtToEquity), ``ticker.quarterly_financials``,
``ticker.calendar``, or external sources (ESPI, EBI) which are not
present in the current contract.

As a result, the 5 v1-eligible event types are declared in ``event_types``
but ``detect()`` returns ``[]`` (no detection — correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (5 v1 / 24 total)
----------------------------------
- PE_RATIO_CHANGE (9.1)        — requires ticker.info (trailingPE/forwardPE)
- REVENUE_CHANGE (9.5)         — requires ticker.quarterly_financials
- NET_INCOME_CHANGE (9.6)      — requires ticker.quarterly_financials
- EARNINGS_RELEASE (10.1)      — requires ticker.calendar
- GUIDANCE_UPDATE (10.4)       — requires ESPI/EBI (no yfinance source)

Future events (19) — declared as [Future] in Katalog
-----------------------------------------------------
- PBV_RATIO_CHANGE (9.2)       - MARKET_CAP_CHANGE (9.3)
- DEBT_CHANGE (9.4)            - EARNINGS_BEAT (10.2)
- EARNINGS_MISS (10.3)         - QUARTERLY_REPORT_FILED (11.1)
- ANNUAL_REPORT_FILED (11.2)   - ACCOUNTING_POLICY_CHANGE (11.3)
- DIVIDEND_ANNOUNCEMENT (14.1) - DIVIDEND_POLICY_CHANGE (14.2)
- SPECIAL_DIVIDEND (14.3)      - EX_DIVIDEND_DATE (14.4)
- SPLIT_ANNOUNCEMENT (15.1)    - SPLIT_EXECUTION (15.2)
- REVERSE_SPLIT (15.3)         - SHARE_ISSUANCE_ANNOUNCEMENT (16.1)
- RIGHTS_OFFERING (16.2)       - PRIVATE_PLACEMENT (16.3)
- BUYBACK_ANNOUNCEMENT (17.1)  - BUYBACK_EXECUTION (17.2)

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Fundamental Event Detector
"""

from __future__ import annotations

from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


# =========================================================================
# Event types — the 5 v1-implementable events from the FUNDAMENTAL family.
#
# Although none of these can be detected with OHLCV-only data today,
# they are declared here so that:
#   - the detector can be registered with the DetectorRegistry,
#   - the orchestrator can route the correct event types to this detector,
#   - future extension of DetectionContext enables immediate activation.
# =========================================================================

_EVENT_TYPES: tuple[str, ...] = (
    "PE_RATIO_CHANGE",
    "REVENUE_CHANGE",
    "NET_INCOME_CHANGE",
    "EARNINGS_RELEASE",
    "GUIDANCE_UPDATE",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class FundamentalEventDetector(BaseDetector):
    """
    Detector for the FUNDAMENTAL event family (5 declared v1 events).

    All 5 events require data not present in the current DetectionContext
    (ticker.info, quarterly_financials, calendar, or ESPI/EBI).  The
    detector's ``detect()`` returns ``[]`` — correct analysis, no
    detection — until the context is extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when DetectionContext is extended.
    """

    def __init__(self) -> None:
        pass  # No configuration needed until data source is available.

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "fundamental"

    @property
    def name(self) -> str:
        return "Fundamental Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run fundamental detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        fundamental data (ticker.info, quarterly_financials, calendar,
        ESPI/EBI) is not available in DetectionContext.

        The context is still validated by the orchestrator before this
        method is called — this method simply reports that no events
        were detected under current data constraints.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        # ------------------------------------------------------------------
        # Future detection logic will be implemented here when
        # DetectionContext is extended to carry fundamental data.
        #
        # Example pseudo-code:
        #
        #   if context.pe_ratio is not None:
        #       if abs(context.pe_ratio - context.prev_pe_ratio) >= threshold:
        #           results.append(DetectionResult(
        #               event_type="PE_RATIO_CHANGE",
        #               confidence_level=...,
        #           ))
        #
        # For now, all 5 v1 events require data not in the context.
        # Returning [] is the correct behaviour — an empty list means
        # "analysis completed, nothing detected".
        # ------------------------------------------------------------------
        return []