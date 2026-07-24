"""
Configuration for the ETF Event Detector.

All thresholds and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

Source references are provided for every parameter.

Note: the ETF Event Detector requires external data sources
(ETF composition data, flow data, NAV/market price data).  None of
these sources are available in the current DetectionContext
(OHLCV-only contract).  All parameters are declared for future
activation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ETFEventsConfig:
    """
    Configuration for ETF event detection.

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # ETF Composition Change (33.x)
    # Source: Katalog §33, Hierarchia §4.8
    # ------------------------------------------------------------------
    etf_composition_change_threshold_pct: float = 10.0
    """[Future] Percentage of holdings changed to trigger detection."""

    # ------------------------------------------------------------------
    # ETF Flows (34.x)
    # Source: Katalog §34, Hierarchia §4.8
    # ------------------------------------------------------------------
    etf_flow_threshold_pct: float = 5.0
    """[Future] Daily flow as percentage of AUM to trigger detection."""

    # ------------------------------------------------------------------
    # ETF Premium / Discount (35.x)
    # Source: Katalog §35, Hierarchia §4.8
    # ------------------------------------------------------------------
    etf_premium_discount_threshold_pct: float = 2.0
    """[Future] NAV vs market price divergence threshold."""

    # ------------------------------------------------------------------
    # ETF Closure (36.x)
    # Source: Katalog §36, Hierarchia §4.8
    # ------------------------------------------------------------------
    # No numeric threshold — binary event (ETF closure announcement).

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------
    confidence_scale_factor: float = 2.0
    """Divide signal strength by this factor to cap confidence at 1.0."""


DEFAULT_ETF_CONFIG = ETFEventsConfig()