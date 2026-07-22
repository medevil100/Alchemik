"""
DetectionResult — lightweight container for a single detection outcome.

A DetectionResult carries only the data that the detector itself computes.
Classification fields (event_category, event_subcategory, priority_raw,
EventFamily) are derived from ``event_type`` by the orchestration layer
using the catalogue — they are NOT duplicated here.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11.5
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from data.models.price_data import PriceData
from data.models.volume_data import VolumeData


@dataclass(frozen=True)
class DetectionResult:
    """
    Immutable, minimal result of a single detection.

    Fields
    ------
    event_type: str
        Catalogue identifier (e.g. ``"PRICE_SURGE"``).  Must be non-empty.
    confidence_level: float
        Detector's confidence in the range ``[0.0, 1.0]``.
        ``NaN``, ``inf``, and ``bool`` are rejected.
    price_data: PriceData | None
        OHLCV snapshot for price/volume/technical families; ``None`` for others.
    volume_data: VolumeData | None
        Volume snapshot for volume-family detectors; ``None`` for others.
    """

    event_type: str
    confidence_level: float
    price_data: PriceData | None = None
    volume_data: VolumeData | None = None

    def __post_init__(self) -> None:
        # -- event_type -------------------------------------------------------
        if not isinstance(self.event_type, str):
            raise TypeError(
                f"event_type must be str, got {type(self.event_type).__name__}"
            )
        if not self.event_type.strip():
            raise ValueError("event_type must not be empty or whitespace-only")

        # -- confidence_level -------------------------------------------------
        # bool is a subclass of int (and int is a subclass of float via Number),
        # but the contract explicitly forbids bool values.
        if isinstance(self.confidence_level, bool):
            raise TypeError(
                "confidence_level must be a real number (float), got bool"
            )
        if not isinstance(self.confidence_level, (int, float)):
            raise TypeError(
                "confidence_level must be a real number (float), "
                f"got {type(self.confidence_level).__name__}"
            )
        # Reject NaN and infinities via math.isfinite
        if not math.isfinite(self.confidence_level):
            raise ValueError(
                f"confidence_level must be finite, got {self.confidence_level}"
            )
        if not (0.0 <= self.confidence_level <= 1.0):
            raise ValueError(
                "confidence_level must be in [0.0, 1.0], "
                f"got {self.confidence_level}"
            )

        # -- price_data -------------------------------------------------------
        if self.price_data is not None and not isinstance(self.price_data, PriceData):
            raise TypeError(
                "price_data must be None or a PriceData instance, "
                f"got {type(self.price_data).__name__}"
            )

        # -- volume_data ------------------------------------------------------
        if self.volume_data is not None and not isinstance(self.volume_data, VolumeData):
            raise TypeError(
                "volume_data must be None or a VolumeData instance, "
                f"got {type(self.volume_data).__name__}"
            )