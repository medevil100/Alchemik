"""EventOutcome — model domenowy rezultatu zdarzenia rynkowego."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class EventOutcomeState(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    INVALID = "INVALID"


@dataclass
class EventOutcome:
    """Model opisujący rezultat zdarzenia rynkowego."""

    event_outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    market_event_id: str = ""

    state: EventOutcomeState = EventOutcomeState.PENDING

    # Wartości bazowe — kontrolowana kopia z MarketEvent
    ticker: str = ""
    market: str = ""
    detection_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    base_price: Optional[float] = None
    base_volume: Optional[float] = None
    event_family: str = ""
    event_type: str = ""
    quality_level: str = ""

    # Informacje zbiorcze
    expected_horizons: int = 4
    horizons_calculated: int = 0
    horizons_failed: int = 0
    horizons_skipped: int = 0
    missing_horizons: list[str] = field(default_factory=list)

    # Metadane
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rule_version: str = "1.0.0"

    # Przyczyny
    failure_reason: Optional[str] = None
    invalid_reason: Optional[str] = None