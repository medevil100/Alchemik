from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class OutcomeConfig:
    """Konfiguracja OutcomeComputer."""

    horizons: Tuple[str, ...] = ("+1", "+2", "+3", "+5")
    max_retry_attempts: int = 5
    fetch_timeout_seconds: int = 30
    rule_version: str = "1.0.0"