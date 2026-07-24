"""
Configuration for the Fundamental Event Detector.

All thresholds, windows, and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

Source references are provided for every parameter.

Note: the Fundamental Event Detector currently operates on OHLCV-derived
signals only. Events requiring ``ticker.info``, ``ticker.quarterly_financials``,
``ticker.calendar``, ESPI, or EBI data cannot be detected within the
``DetectionContext`` contract and are documented as such.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FundamentalEventsConfig:
    """
    Configuration for fundamental event detection.

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # P/E Ratio Change (9.1)
    # Source: Katalog §9.1, Hierarchia §4.4
    # ------------------------------------------------------------------
    pe_change_threshold_pct: float = 20.0
    """Percentage change in P/E ratio required to trigger PE_RATIO_CHANGE."""

    # ------------------------------------------------------------------
    # Revenue Change (9.5)
    # Source: Katalog §9.5, Hierarchia §4.4
    # ------------------------------------------------------------------
    revenue_change_threshold_pct: float = 15.0
    """Percentage change in revenue required to trigger REVENUE_CHANGE."""

    # ------------------------------------------------------------------
    # Net Income Change (9.6)
    # Source: Katalog §9.6, Hierarchia §4.4
    # ------------------------------------------------------------------
    net_income_change_threshold_pct: float = 20.0
    """Percentage change in net income required to trigger NET_INCOME_CHANGE."""

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------
    confidence_scale_factor: float = 2.0
    """Divide signal strength by this factor to cap confidence at 1.0."""

    # ------------------------------------------------------------------
    # Future parameters — not yet active
    # ------------------------------------------------------------------
    pbv_change_threshold_pct: float = 20.0
    """[Future] P/BV ratio change threshold (9.2)."""

    market_cap_change_threshold_pct: float = 25.0
    """[Future] Market cap change threshold (9.3)."""

    debt_change_threshold_pct: float = 30.0
    """[Future] Debt/Equity change threshold (9.4)."""

    dividend_change_threshold_pct: float = 50.0
    """[Future] Dividend change threshold (14.x)."""


DEFAULT_FUNDAMENTAL_CONFIG = FundamentalEventsConfig()