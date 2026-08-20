"""
InstrumentReading — model domenowy niezmiennego faktu rynkowego.

Reprezentuje niezmienny fakt rynkowy dotyczący jednego instrumentu
w konkretnym market_data_timestamp. Przechowuje dane OHLCV (częściowe
lub kompletne), źródło danych (wyłącznie YahooFinance), relację
do macierzystej InstrumentObservation oraz opcjonalną relację
do poprzedniego odczytu.

KROK 4 — implementacja po Test First RED, z korektami po audycie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple

_ALLOWED_COMPLETENESS = frozenset({"COMPLETE", "PARTIAL"})

# Jedyna dozwolona wartość źródła danych
_ALLOWED_SOURCE = "YahooFinance"


@dataclass
class InstrumentReading:
    """Niezmienny fakt rynkowy dotyczący jednego instrumentu."""

    reading_id: str
    observation_id: str
    instrument_id: str
    market_data_timestamp: datetime
    scan_timestamp: datetime

    # OHLCV — opcjonalne poza close (wymaganym dla PARTIAL; COMPLETE wymaga O+H+L+C)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None

    source: str = _ALLOWED_SOURCE
    prev_reading_id: Optional[str] = None

    data_completeness: str = "COMPLETE"

    revision_number: int = 1
    supersedes_reading_id: Optional[str] = None

    _initialized: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        """Validate source, data_completeness, and OHLCV invariants."""
        # 1. Source validation
        if self.source != _ALLOWED_SOURCE:
            raise ValueError(
                f"source must be {_ALLOWED_SOURCE!r}, got {self.source!r}"
            )

        # 2. data_completeness validation
        if self.data_completeness not in _ALLOWED_COMPLETENESS:
            raise ValueError(
                f"data_completeness must be one of {sorted(_ALLOWED_COMPLETENESS)}, "
                f"got {self.data_completeness!r}"
            )

        # 3. COMPLETE requires open, high, low, close
        if self.data_completeness == "COMPLETE":
            if self.open is None or self.high is None or self.low is None or self.close is None:
                raise ValueError(
                    "data_completeness=COMPLETE requires open, high, low, and close to be non-None"
                )

        # 4. PARTIAL requires close
        if self.data_completeness == "PARTIAL":
            if self.close is None:
                raise ValueError(
                    "data_completeness=PARTIAL requires close to be non-None"
                )

        # 5. volume is always optional — no validation needed

        self._initialized = True

    def __setattr__(self, name, value):
        """Guard: prevent mutation of all data fields after creation."""
        if name == "_initialized":
            object.__setattr__(self, name, value)
            return

        is_init_phase = not getattr(self, "_initialized", False)

        if is_init_phase:
            object.__setattr__(self, name, value)
            return

        # All data fields are immutable after creation
        if name in (
            "reading_id", "observation_id", "instrument_id",
            "market_data_timestamp", "scan_timestamp",
            "open", "high", "low", "close", "volume",
            "source", "prev_reading_id", "data_completeness",
            "revision_number", "supersedes_reading_id",
        ):
            raise AttributeError(f"{name} is immutable")

        object.__setattr__(self, name, value)

    def canonical_identity(self) -> Tuple[str, datetime]:
        """
        Return the canonical domenowa pair: (instrument_id, market_data_timestamp).

        This pair constitutes a jednoznaczny fakt rynkowy within the domen.
        """
        return (self.instrument_id, self.market_data_timestamp)