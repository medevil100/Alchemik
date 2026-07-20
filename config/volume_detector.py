"""
Configuration for the Volume Event Detector.

All thresholds, windows, and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

No arbitrary thresholds — every value is documented with its source.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class VolumeDetectorConfig:
    """
    Configuration for volume-based event detection.

    Thresholds are based on the standard market conventions and
    example values referenced in the ALCHEMIK documentation:
      - Katalog Zdarzen Rynkowych §2.1–§2.5
      - Hierarchia Zdarzen Rynkowych §4.2

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # Volume Spike (2.1)
    # Source: Katalog §2.1 — "Wolumen bieżącej świecy przekracza
    # X-krotność średniego wolumenu z ostatnich N świec".
    # ------------------------------------------------------------------
    spike_threshold: float = 3.0
    """
    Volume ratio threshold for Volume Spike.
    Current volume must exceed this multiple of the average volume.
    """

    spike_volume_window: int = 20
    """
    Number of candles to use for average volume calculation in spike detection.
    """

    spike_confidence_scale: float = 5.0
    """
    The volume_ratio at which confidence_level reaches 1.0 for spike.
    """

    # ------------------------------------------------------------------
    # Near-Zero Volume (2.2)
    # Source: Katalog §2.2 — "Wolumen spadł poniżej minimalnego progu
    # (np. <10% średniej)".
    # ------------------------------------------------------------------
    near_zero_threshold: float = 0.1
    """
    Volume ratio threshold for Near-Zero Volume.
    Current volume must be below this fraction of the average volume.
    """

    near_zero_volume_window: int = 20
    """
    Number of candles to use for average volume calculation in near-zero detection.
    """

    near_zero_confidence_scale: float = 0.05
    """
    The volume_ratio at which confidence_level reaches 1.0 for near-zero.
    Lower ratio = higher confidence.
    """

    # ------------------------------------------------------------------
    # Cumulative Volume Anomaly (2.3)
    # Source: Katalog §2.3 — "Suma wolumenu z ostatnich N świec znacząco
    # odbiega od średniej sumy z porównywalnych okresów".
    # ------------------------------------------------------------------
    cumulative_window: int = 20
    """
    Number of candles to sum for cumulative volume detection.
    """

    cumulative_lookback: int = 60
    """
    Number of prior periods to compare against for cumulative volume.
    """

    cumulative_threshold: float = 2.0
    """
    Ratio threshold for cumulative volume anomaly.
    Current cumulative sum must exceed this multiple of the average sum.
    """

    cumulative_confidence_scale: float = 3.0
    """
    The cumulative ratio at which confidence_level reaches 1.0.
    """

    # ------------------------------------------------------------------
    # High Volume on Down Days / Up Days (2.4, 2.5)
    # Source: Katalog §2.4, §2.5 — "Wolumen na świecach spadkowych/
    # wzrostowych jest znacząco wyższy niż na świecach przeciwnych".
    # ------------------------------------------------------------------
    directional_volume_window: int = 20
    """
    Number of candles to analyze for directional volume detection.
    """

    directional_threshold: float = 1.5
    """
    Ratio threshold for directional volume.
    Average volume on dominant direction must exceed this multiple
    of average volume on the opposite direction.
    """

    directional_min_candles: int = 3
    """
    Minimum number of candles in each direction required for meaningful
    directional volume comparison.
    """

    directional_confidence_scale: float = 3.0
    """
    The directional ratio at which confidence_level reaches 1.0.
    """

    # ------------------------------------------------------------------
    # General confidence calculation
    # ------------------------------------------------------------------
    min_confidence: float = 0.1
    """Minimum confidence level for any detected event."""

    max_confidence: float = 1.0
    """Maximum confidence level (always capped at 1.0)."""


# Module-level default config instance used by the detector.
DEFAULT_CONFIG = VolumeDetectorConfig()