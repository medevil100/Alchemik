"""
SentimentNewsEventDetector — detects sentiment and news market events.

Implements the scaffold for events from the SENTIMENT family (~11 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Current limitations
-------------------
DetectionContext (as per docs/ETAP_6_ARCHITEKTURA.md §11.4) carries only
OHLCV data.  Sentiment & news events require external data sources
(social media APIs, Tavily search results, VIX data, news feeds) which
are not present in the current contract.

All 11 event types are declared in ``event_types`` for registration and
routing, but ``detect()`` returns ``[]`` (correct analysis with
insufficient data).  This detector is structurally complete and ready
to activate once the DetectionContext is extended.

Events declared (11 / 11 total — all [Future])
-----------------------------------------------
    SOCIAL_MEDIA_SPIKE, SOCIAL_MEDIA_SENTIMENT_SHIFT,
    VIX_SPIKE, VIX_COLLAPSE, BREAKING_NEWS, ANALYST_REPORT,
    EXECUTIVE_INTERVIEW, TAVILY_RESULT_SPIKE, TAVILY_SENTIMENT_SHIFT,
    NEWS_SENTIMENT_SHIFT, EARNINGS_WHISPER

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Sentiment & News Event Detector
"""

from __future__ import annotations

from config.sentiment_events import DEFAULT_SENTIMENT_CONFIG, SentimentEventsConfig
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult


_EVENT_TYPES: tuple[str, ...] = (
    "SOCIAL_MEDIA_SPIKE",
    "SOCIAL_MEDIA_SENTIMENT_SHIFT",
    "VIX_SPIKE",
    "VIX_COLLAPSE",
    "BREAKING_NEWS",
    "ANALYST_REPORT",
    "EXECUTIVE_INTERVIEW",
    "TAVILY_RESULT_SPIKE",
    "TAVILY_SENTIMENT_SHIFT",
    "NEWS_SENTIMENT_SHIFT",
    "EARNINGS_WHISPER",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


class SentimentNewsEventDetector(BaseDetector):
    """
    Detector for the SENTIMENT event family (11 declared events).

    All 11 events require sentiment/news data not present in the current
    DetectionContext (social media, Tavily, VIX, news feeds).  The
    detector's ``detect()`` returns ``[]`` — correct analysis, no
    detection — until the context is extended.

    The detector is structurally complete:
        - Implements all BaseDetector abstract members.
        - Can be registered, routed, and invoked without errors.
        - Ready for activation when sentiment data sources are available.
    """

    def __init__(self, config: SentimentEventsConfig | None = None) -> None:
        self._config = config or DEFAULT_SENTIMENT_CONFIG

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "sentiment"

    @property
    def name(self) -> str:
        return "Sentiment & News Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run sentiment & news detection logic on the given context.

        Current behaviour: returns ``[]`` (no detection) because
        sentiment/news data (social media, Tavily, VIX, news feeds)
        is not available in DetectionContext.

        Args:
            context: A fully-validated DetectionContext.

        Returns:
            ``[]`` — correct analysis, no detection possible with OHLCV
            data alone.
        """
        return []