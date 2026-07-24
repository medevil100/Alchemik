"""
DerivativesEventDetector — detects derivatives-related market events.

Implements the scaffold for events from the DERIVATIVES family (~9 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data.  Derivatives events require external data sources (options
chains, short interest data, dark pool data, block trade reports) which
are not present in the current contract.

All 9 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (9 / 9 total — all [Future])
----------------------------------------------
    UNUSUAL_OPTIONS_VOLUME, OPTIONS_PUT_CALL_RATIO, OPTIONS_VOLATILITY_SKEW,
    SHORT_INTEREST_SPIKE, SHORT_INTEREST_SQUEEZE, DARK_POOL_PRINT,
    DARK_POOL_SPIKE, UNUSUAL_BLOCK_TRADE, BLOCK_TRADE_CLUSTER

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Derivatives Event Detector
"""

from __future__ import annotations

from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    "UNUSUAL_OPTIONS_VOLUME",
    "OPTIONS_PUT_CALL_RATIO",
    "OPTIONS_VOLATILITY_SKEW",
    "SHORT_INTEREST_SPIKE",
    "SHORT_INTEREST_SQUEEZE",
    "DARK_POOL_PRINT",
    "DARK_POOL_SPIKE",
    "UNUSUAL_BLOCK_TRADE",
    "BLOCK_TRADE_CLUSTER",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class DerivativesEventDetector(BaseDetector):
    """
    Detector for the DERIVATIVES event family (9 declared events).

    All 9 events require derivatives data not present in the current
    DetectionContext (options chains, short interest, dark pool data,
    block trade reports).  The detector's ``detect()`` returns ``[]`` —
    correct analysis, no detection — until the context is extended.

    No configuration is needed until data sources are available.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when derivatives data sources are available.
    """

    def __init__(self) -> None:
        pass

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "derivatives"

    @property
    def name(self) -> str:
        return "Derivatives Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run derivatives detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        derivatives data (options, short interest, dark pool, block
        trades) is not available in DetectionContext.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        return []