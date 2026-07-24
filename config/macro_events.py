"""
Configuration for the Macro Event Detector.

All thresholds and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

Source references are provided for every parameter.

Note: the Macro Event Detector requires external data sources
(GDP reports, central bank announcements, CPI/PPI releases, currency
and commodity prices).  None of these sources are available in the
current DetectionContext (OHLCV-only contract).  All parameters are
declared for future activation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MacroEventsConfig:
    """
    Configuration for macro event detection.

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # GDP (27.x)
    # Source: Katalog §27, Hierarchia §4.7
    # ------------------------------------------------------------------
    gdp_change_threshold_pct: float = 0.5
    """[Future] GDP change quarter-over-quarter to trigger detection (abs)."""

    # ------------------------------------------------------------------
    # Interest Rates (28.x)
    # Source: Katalog §28, Hierarchia §4.7
    # ------------------------------------------------------------------
    rate_change_threshold_bps: int = 25
    """[Future] Minimum basis point change to trigger INTEREST_RATE_CHANGE."""

    # ------------------------------------------------------------------
    # Inflation (29.x)
    # Source: Katalog §29, Hierarchia §4.7
    # ------------------------------------------------------------------
    cpi_change_threshold_pct: float = 0.3
    """[Future] CPI MoM change threshold to trigger INFLATION_CHANGE (abs)."""

    ppi_change_threshold_pct: float = 0.5
    """[Future] PPI MoM change threshold (abs)."""

    # ------------------------------------------------------------------
    # Currency / Commodity / Geopolitics (30.x, 31.x, 32.x)
    # Source: Katalog §30-32, Hierarchia §4.7
    # ------------------------------------------------------------------
    currency_move_threshold_pct: float = 2.0
    """[Future] Daily currency move threshold (abs) to trigger CURRENCY_MOVE."""

    commodity_move_threshold_pct: float = 3.0
    """[Future] Daily commodity price move threshold (abs)."""

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------
    confidence_scale_factor: float = 2.0
    """Divide signal strength by this factor to cap confidence at 1.0."""


DEFAULT_MACRO_CONFIG = MacroEventsConfig()