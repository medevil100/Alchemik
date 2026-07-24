"""
Configuration for the Sentiment & News Event Detector.

All thresholds and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

Source references are provided for every parameter.

Note: the Sentiment & News Event Detector requires external data sources
(social media APIs, Tavily search results, VIX data, news feeds).  None
of these sources are available in the current DetectionContext
(OHLCV-only contract).  All parameters are declared for future
activation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentEventsConfig:
    """
    Configuration for sentiment & news event detection.

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # Social Media Spike (37.x)
    # Source: Katalog §37, Hierarchia §4.10
    # ------------------------------------------------------------------
    social_media_mention_multiplier: float = 3.0
    """[Future] Multiplier of average mentions to trigger SOCIAL_MEDIA_SPIKE."""

    social_media_lookback_days: int = 7
    """[Future] Days to average mention count over."""

    # ------------------------------------------------------------------
    # Sentiment Shift (38.x)
    # Source: Katalog §38, Hierarchia §4.10
    # ------------------------------------------------------------------
    sentiment_shift_threshold: float = 0.3
    """[Future] Absolute change in sentiment score [-1.0, 1.0] to trigger
    SENTIMENT_SHIFT."""

    # ------------------------------------------------------------------
    # VIX Change (39.x)
    # Source: Katalog §39, Hierarchia §4.10
    # ------------------------------------------------------------------
    vix_change_threshold_pct: float = 15.0
    """[Future] Daily VIX percentage change threshold."""

    # ------------------------------------------------------------------
    # Breaking News (40.x)
    # Source: Katalog §40, Hierarchia §4.10
    # ------------------------------------------------------------------
    breaking_news_relevance_threshold: float = 0.8
    """[Future] Minimum relevance score [0.0, 1.0] to trigger BREAKING_NEWS."""

    # ------------------------------------------------------------------
    # Tavily Results (41.x)
    # Source: Katalog §41, Hierarchia §4.10
    # ------------------------------------------------------------------
    tavily_result_count_threshold: int = 50
    """[Future] Minimum search result count to trigger TAVILY_SPIKE."""

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------
    confidence_scale_factor: float = 2.0
    """Divide signal strength by this factor to cap confidence at 1.0."""


DEFAULT_SENTIMENT_CONFIG = SentimentEventsConfig()