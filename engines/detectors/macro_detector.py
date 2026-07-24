"""
MacroEventDetector — detects macro-economic market events.

Implements the scaffold for events from the MACRO family (~16 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data.  Macro events require external data sources (GDP reports,
central bank announcements, CPI/PPI releases, currency and commodity
prices, geopolitical event feeds) which are not present in the current
contract.

All 16 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (16 / 16 total — all [Future])
-----------------------------------------------
GDP (27.x):              GDP_BEAT, GDP_MISS, GDP_REVISION
Interest Rates (28.x):   INTEREST_RATE_HIKE, INTEREST_RATE_CUT,
    RATE_DECISION_SURPRISE
Inflation (29.x):        CPI_BEAT, CPI_MISS, PPI_SURGE,
    INFLATION_TREND_CHANGE
Currency (30.x):         CURRENCY_SURGE, CURRENCY_PLUMMET,
    CURRENCY_VOLATILITY_SPIKE
Commodity (31.x):        COMMODITY_PRICE_SPIKE, COMMODITY_PRICE_DROP
Geopolitics (32.x):      GEOPOLITICAL_ESCALATION

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Macro Event Detector
"""

from __future__ import annotations

from config.macro_events import DEFAULT_MACRO_CONFIG, MacroEventsConfig
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    # GDP (27.x)
    "GDP_BEAT",
    "GDP_MISS",
    "GDP_REVISION",
    # Interest Rates (28.x)
    "INTEREST_RATE_HIKE",
    "INTEREST_RATE_CUT",
    "RATE_DECISION_SURPRISE",
    # Inflation (29.x)
    "CPI_BEAT",
    "CPI_MISS",
    "PPI_SURGE",
    "INFLATION_TREND_CHANGE",
    # Currency (30.x)
    "CURRENCY_SURGE",
    "CURRENCY_PLUMMET",
    "CURRENCY_VOLATILITY_SPIKE",
    # Commodity (31.x)
    "COMMODITY_PRICE_SPIKE",
    "COMMODITY_PRICE_DROP",
    # Geopolitics (32.x)
    "GEOPOLITICAL_ESCALATION",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class MacroEventDetector(BaseDetector):
    """
    Detector for the MACRO event family (16 declared events).

    All 16 events require macroeconomic data not present in the current
    DetectionContext (GDP, interest rates, inflation, currency, commodity,
    geopolitical data).  The detector's ``detect()`` returns ``[]`` —
    correct analysis, no detection — until the context is extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when macro data sources are available.
    """

    def __init__(self, config: MacroEventsConfig | None = None) -> None:
        self._config = config or DEFAULT_MACRO_CONFIG

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "macro"

    @property
    def name(self) -> str:
        return "Macro Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run macro detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        macroeconomic data (GDP, interest rates, inflation, currency,
        commodity, geopolitical) is not available in DetectionContext.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        return []