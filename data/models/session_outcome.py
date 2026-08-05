"""SessionOutcome — model domenowy wyniku pojedynczego horyzontu sesyjnego."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionOutcomeState(str, Enum):
    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class SessionOutcome:
    """Model opisujący wynik pojedynczego horyzontu sesyjnego."""

    session_outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_outcome_id: str = ""
    horizon_id: str = ""

    state: SessionOutcomeState = SessionOutcomeState.PENDING
    attempt_count: int = 0

    # Metryki cenowe
    close_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    price_change_abs: Optional[float] = None

    # Metryki wolumenowe
    volume: Optional[float] = None
    volume_change_pct: Optional[float] = None

    # Metryki wewnątrz-horyzontalne
    high_price: Optional[float] = None
    low_price: Optional[float] = None

    # Błędy
    failure_reason: Optional[str] = None
    skip_reason: Optional[str] = None

    # Metadane
    computed_at: Optional[datetime] = None
    rule_version: Optional[str] = None
    data_source: Optional[str] = None