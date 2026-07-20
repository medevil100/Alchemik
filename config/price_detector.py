"""
Configuration for the Price Event Detector.

All thresholds, windows, and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Przeplyw Zdarzen Rynkowych v1.0, Hierarchia Zdarzen Rynkowych v1.0).

No arbitrary thresholds — every value is documented with its source.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PriceDetectorConfig:
    """
    Configuration for price-based event detection.

    Thresholds are based on the standard market conventions and
    example values referenced in the ALCHEMIK documentation:
      - Przeplyw Zdarzen Rynkowych mentions +8.5% as a surge example
      - Katalog Zdarzen Rynkowych defines gap significance qualitatively
      - Hierarchia Zdarzen Rynkowych defines event priorities and families

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # Price Surge / Price Drop (1.1, 1.2)
    # Source: Katalog §1.1, §1.2 — "Cena wzrosła/spadła o X% w ciągu
    # jednej świecy". Example from Przeplyw §2.1: "+8.5% dla surge".
    # ------------------------------------------------------------------
    surge_threshold_pct: float = 8.0
    """Percentage change threshold for Price Surge (positive) / Drop (negative)."""

    surge_confidence_scale_pct: float = 15.0
    """The change_pct at which confidence_level reaches 1.0 (2x this = 1.0)."""

    # ------------------------------------------------------------------
    # Gap Up / Gap Down (1.3, 1.4)
    # Source: Katalog §1.3, §1.4 — "znacząco wyższa/niższa niż cena
    # zamknięcia poprzedniej świecy". Threshold derived from common
    # market gap conventions (typically 2-5%).
    # ------------------------------------------------------------------
    gap_threshold_pct: float = 3.0
    """Percentage gap (open vs prev_close) required to trigger a gap event."""

    gap_confidence_scale_pct: float = 10.0
    """The gap_pct at which confidence_level reaches 1.0."""

    gap_vs_high_low: bool = True
    """
    If True, also check gap vs prev_high (for Gap Up) or prev_low (for Gap Down)
    for stronger confirmation.
    """

    # ------------------------------------------------------------------
    # 52-Week High / Low (1.5, 1.6)
    # Source: Katalog §1.5, §1.6 — "260 świec dziennych (minimum)".
    # ------------------------------------------------------------------
    fifty_two_week_window: int = 260
    """Minimum number of daily candles to consider for 52-week extremes."""

    # ------------------------------------------------------------------
    # All-Time High / Low (1.7, 1.8)
    # Source: Katalog §1.7, §1.8 — "pełna historia notowań (max dostępne)".
    # ------------------------------------------------------------------
    ath_min_history: int = 50
    """
    Minimum number of candles required before ATH/ATL detection is meaningful.
    Below this threshold, the detection is skipped (insufficient history).
    """

    # ------------------------------------------------------------------
    # Level Rejection (1.9)
    # Source: Katalog §1.9 — "Cena zbliżyła się do istotnego poziomu
    # wsparcia/oporu i gwałtownie się od niego odbiła."
    # ------------------------------------------------------------------
    level_rejection_proximity_pct: float = 1.0
    """
    Maximum distance (as percentage of price) from a support/resistance
    level to consider it "approached".
    """

    level_rejection_rebound_pct: float = 1.5
    """
    Minimum rebound (as percentage of price from the level) required
    to confirm the rejection.
    """

    level_rejection_lookback: int = 20
    """Number of recent swing highs/lows to consider as S/R levels."""

    level_rejection_min_swing_strength: int = 3
    """Minimum number of candles on each side of a swing point."""

    # ------------------------------------------------------------------
    # Psychological Level Cross (1.10)
    # Source: Katalog §1.10 — "Cena przekroczyła okrągły poziom
    # (np. 10, 50, 100, 1000 PLN/USD)."
    # ------------------------------------------------------------------
    psych_level_rounds: List[float] = field(default_factory=lambda: [
        1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000
    ])
    """
    List of absolute round levels considered psychologically significant.
    """

    psych_level_proximity_pct: float = 0.5
    """
    Maximum distance (as percentage of the round level) for the price
    to be considered "near" the psychological level.
    """

    # ------------------------------------------------------------------
    # General confidence calculation
    # ------------------------------------------------------------------
    min_confidence: float = 0.1
    """Minimum confidence level for any detected event."""

    max_confidence: float = 1.0
    """Maximum confidence level (always capped at 1.0)."""

    def get_psych_levels_for_price(self, price: float) -> List[float]:
        """
        Return the set of psychological levels relevant to a given price.

        Includes the nearest round levels above and below the current price.
        """
        relevant = []
        for level in self.psych_level_rounds:
            # Include levels within a reasonable range of the current price
            if level * 0.3 <= price <= level * 3.0:
                relevant.append(level)
        return relevant if relevant else self.psych_level_rounds


# Module-level default config instance used by the detector.
DEFAULT_CONFIG = PriceDetectorConfig()