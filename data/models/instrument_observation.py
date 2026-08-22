"""
InstrumentObservation — model domenowy trwałej obserwacji jednego instrumentu.

Reprezentuje obserwację instrumentu z własną niezmienną tożsamością observation_id,
cyklem życia opartym na stanach (ACTIVE, TERMINATED_DOMAIN, TERMINATED_TECHNICAL,
INTEGRITY_BREACHED, RETIRED_TIMEFRAME) i jawnymi przejściami terminalnymi.

KROK 4 — implementacja po Test First RED.
KROK 7C.4B — dodanie timeframe i statusu RETIRED_TIMEFRAME (decyzja właściciela 2026-08-21).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

_ALLOWED_STATES = frozenset({
    "ACTIVE",
    "TERMINATED_DOMAIN",
    "TERMINATED_TECHNICAL",
    "INTEGRITY_BREACHED",
    "RETIRED_TIMEFRAME",
})
_TERMINAL_STATES = frozenset({
    "TERMINATED_DOMAIN",
    "TERMINATED_TECHNICAL",
    "INTEGRITY_BREACHED",
    "RETIRED_TIMEFRAME",
})


@dataclass
class InstrumentObservation:
    """Trwała obserwacja jednego instrumentu z własną tożsamością."""

    observation_id: str
    instrument_id: str

    state: str = "ACTIVE"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    terminated_at: Optional[datetime] = None
    termination_reason: Optional[str] = None

    # Krok 7C.4B — timeframe Observation.
    # Domyślna wartość LEGACY_UNKNOWN zapewnia kompatybilność istniejących
    # konstruktorów bez nowych argumentów.
    timeframe: str = "LEGACY_UNKNOWN"

    _initialized: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        """Validate state and timeframe on creation."""
        if self.state not in _ALLOWED_STATES:
            raise ValueError(
                f"Invalid state: {self.state!r}. "
                f"Allowed: {', '.join(sorted(_ALLOWED_STATES))}"
            )
        if not isinstance(self.timeframe, str) or not self.timeframe.strip():
            raise ValueError("timeframe must be a non-empty canonical string")
        self._initialized = True

    def __setattr__(self, name, value):
        """Guard: prevent mutation of identity fields and validate state transitions."""
        # Allow mutation during __init__ (before _initialized is set)
        if name == "_initialized":
            object.__setattr__(self, name, value)
            return

        is_init_phase = not getattr(self, "_initialized", False)

        if is_init_phase:
            object.__setattr__(self, name, value)
            return

        # Identity fields are immutable after creation
        if name in ("observation_id", "instrument_id", "timeframe"):
            raise AttributeError(f"{name} is immutable")

        # State validation on set
        if name == "state":
            if value not in _ALLOWED_STATES:
                raise ValueError(
                    f"Invalid state: {value!r}. "
                    f"Allowed: {', '.join(sorted(_ALLOWED_STATES))}"
                )
            # Block transition from terminal states
            if self.state in _TERMINAL_STATES:
                raise ValueError(
                    f"Cannot transition from terminal state {self.state!r} to {value!r}"
                )
            object.__setattr__(self, name, value)
            return

        object.__setattr__(self, name, value)

    def terminate(self, target_state: str, reason: str) -> None:
        """
        Execute a terminal transition with an explicit reason.

        Allowed transitions:
        - ACTIVE → TERMINATED_DOMAIN
        - ACTIVE → TERMINATED_TECHNICAL
        - ACTIVE → INTEGRITY_BREACHED
        - ACTIVE → RETIRED_TIMEFRAME (Krok 7C.4B)

        Requires a non-empty *reason*.  Fails with ValueError if:
        - *target_state* is not a valid terminal state
        - *reason* is empty
        - already in a terminal state
        """
        if target_state not in _ALLOWED_STATES:
            raise ValueError(
                f"Invalid state: {target_state!r}. "
                f"Allowed: {', '.join(sorted(_ALLOWED_STATES))}"
            )

        if target_state == "ACTIVE":
            raise ValueError("terminate() requires a terminal state, got ACTIVE")

        if not reason or not reason.strip():
            raise ValueError("Terminal transition requires a non-empty reason")

        if self.state in _TERMINAL_STATES:
            raise ValueError(
                f"Cannot transition from terminal state {self.state!r} to {target_state!r}"
            )

        self.state = target_state
        self.termination_reason = reason
        self.terminated_at = datetime.now(timezone.utc)