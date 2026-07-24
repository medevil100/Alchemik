"""
Configuration for the Corporate Event Detector.

All thresholds and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

Source references are provided for every parameter.

Note: the Corporate Event Detector requires external data sources
(ESPI, EBI, SEC filings, insider trading reports, analyst recommendations).
None of these sources are available in the current DetectionContext
(OHLCV-only contract).  All parameters are declared for future activation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CorporateEventsConfig:
    """
    Configuration for corporate event detection.

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # Insider Trading (18.x)
    # Source: Katalog §18, Hierarchia §4.5
    # ------------------------------------------------------------------
    insider_trading_volume_threshold: float = 5.0
    """[Future] Multiplier of average insider volume to trigger detection."""

    insider_trading_value_threshold: float = 100_000.0
    """[Future] Minimum trade value in USD to trigger detection."""

    # ------------------------------------------------------------------
    # Shareholder Change (19.x)
    # Source: Katalog §19, Hierarchia §4.5
    # ------------------------------------------------------------------
    shareholder_change_threshold_pct: float = 5.0
    """[Future] Percentage ownership change to trigger SHAREHOLDER_CHANGE."""

    # ------------------------------------------------------------------
    # Recommendation / Rating Change (20.x)
    # Source: Katalog §20, Hierarchia §4.5
    # ------------------------------------------------------------------
    recommendation_change_min_gap: int = 2
    """[Future] Minimum gap between old and new rating tiers (1-5 scale)."""

    # ------------------------------------------------------------------
    # M&A Events (22.x)
    # Source: Katalog §22, Hierarchia §4.5
    # ------------------------------------------------------------------
    mna_premium_threshold_pct: float = 20.0
    """[Future] Minimum acquisition premium to trigger M&A detection."""

    # ------------------------------------------------------------------
    # Contracts / Legal / Bankruptcy (23.x, 24.x, 25.x)
    # Source: Katalog §23-25, Hierarchia §4.5
    # ------------------------------------------------------------------
    contract_value_threshold: float = 10_000_000.0
    """[Future] Minimum contract value in USD to trigger detection."""

    # ------------------------------------------------------------------
    # Management Change (26.x)
    # Source: Katalog §26, Hierarchia §4.5
    # ------------------------------------------------------------------
    management_change_critical_positions: tuple[str, ...] = (
        "CEO", "CFO", "COO", "CTO", "Chairman",
    )
    """[Future] Positions whose change is considered critical."""

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------
    confidence_scale_factor: float = 2.0
    """Divide signal strength by this factor to cap confidence at 1.0."""


DEFAULT_CORPORATE_CONFIG = CorporateEventsConfig()