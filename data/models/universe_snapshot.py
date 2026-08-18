"""UniverseSnapshot — jeden wynik discovery Yahoo w konkretnym cyklu."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .universe_instrument import UniverseInstrument


@dataclass
class UniverseSnapshotMember:
    """Wiąże instrument ze snapshotem i zachowuje wynik tego skanu."""

    snapshot_id: str
    symbol: str
    present: bool = True
    status: str = "ACTIVE"
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    chart_status: str = "NOT_STARTED"
    candles_received: int = 0
    candles_valid: int = 0
    candles_rejected: int = 0
    rejection_reasons: dict = field(default_factory=dict)

    # Krok 4/8 — jawna diagnostyka daily i intraday (rozdzielona).
    daily_status: Optional[str] = None
    daily_candles_received: int = 0
    daily_candles_valid: int = 0
    daily_candles_rejected: int = 0
    daily_rejection_reasons: dict = field(default_factory=dict)

    intraday_status: Optional[str] = None
    intraday_candles_received: int = 0
    intraday_candles_valid: int = 0
    intraday_candles_rejected: int = 0
    intraday_rejection_reasons: dict = field(default_factory=dict)

    baseline_status: Optional[str] = None
    last_reading_id: Optional[str] = None


@dataclass
class UniverseSnapshot:
    """Jeden wynik discovery w konkretnym cyklu (atomowy zapis zbiorczy)."""

    snapshot_id: str
    created_at: Optional[str] = None
    total_records: int = 0
    unique_symbols: int = 0

    instruments: List[UniverseInstrument] = field(default_factory=list)
    members: List[UniverseSnapshotMember] = field(default_factory=list)

    @classmethod
    def from_discovery(cls, snapshot_id: str, created_at: str,
                       instruments: List[UniverseInstrument]) -> "UniverseSnapshot":
        """Zbuduj snapshot z listy instrumentów; members pochodzą z całości."""
        members = [
            UniverseSnapshotMember(
                snapshot_id=snapshot_id,
                symbol=inst.symbol,
                present=True,
                status=inst.status,
                first_seen_at=inst.first_seen_at,
                last_seen_at=inst.last_seen_at,
                chart_status=inst.chart_status,
                candles_received=inst.candles_received,
                candles_valid=inst.candles_valid,
                candles_rejected=inst.candles_rejected,
                rejection_reasons=dict(inst.rejection_reasons or {}),
                daily_status=inst.daily_status,
                daily_candles_received=inst.daily_candles_received,
                daily_candles_valid=inst.daily_candles_valid,
                daily_candles_rejected=inst.daily_candles_rejected,
                daily_rejection_reasons=dict(inst.daily_rejection_reasons or {}),
                intraday_status=inst.intraday_status,
                intraday_candles_received=inst.intraday_candles_received,
                intraday_candles_valid=inst.intraday_candles_valid,
                intraday_candles_rejected=inst.intraday_candles_rejected,
                intraday_rejection_reasons=dict(inst.intraday_rejection_reasons or {}),
                baseline_status=inst.baseline_status,
                last_reading_id=inst.last_reading_id,
            )
            for inst in instruments
        ]
        return cls(
            snapshot_id=snapshot_id,
            created_at=created_at,
            total_records=len(instruments),
            unique_symbols=len({inst.symbol for inst in instruments}),
            instruments=list(instruments),
            members=members,
        )