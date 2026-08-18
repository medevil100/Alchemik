"""UniverseInstrument — trwała tożsamość instrumentu z uniwersum Yahoo."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UniverseInstrument:
    """Trwała tożsamość instrumentu zwróconego przez Yahoo discovery.

    Reprezentuje instrument niezależnie od pojedynczego snapshotu. Instrument
    nigdy nie jest usuwany z rejestru; zmienia się tylko jego status.
    """

    symbol: str
    quote_type: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None
    currency: Optional[str] = None
    regular_market_price: Optional[float] = None

    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None

    # Status obecności w ostatnim snapshotcie i status chart (daily).
    status: str = "ACTIVE"
    chart_status: str = "NOT_STARTED"

    candles_received: int = 0
    candles_valid: int = 0
    candles_rejected: int = 0
    rejection_reasons: dict = field(default_factory=dict)

    # Krok 4/8 — jawna diagnostyka daily (1y/1d) i intraday (5d/5m).
    # Pola daily są dodane obok istniejącego wspólnego chart_status, który
    # pozostaje aliasem daily dla kompatybilności ze starszymi odczytami.
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

    # Status baseline — PENDING_BASELINE / BASELINE_READY / None.
    baseline_status: Optional[str] = None

    # Identyfikator ostatniego poprawnego Reading (jeśli istnieje).
    last_reading_id: Optional[str] = None

    def to_row(self) -> dict:
        return {
            "symbol": self.symbol,
            "quote_type": self.quote_type,
            "exchange": self.exchange,
            "market": self.market,
            "currency": self.currency,
            "regular_market_price": self.regular_market_price,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "status": self.status,
            "chart_status": self.chart_status,
            "candles_received": self.candles_received,
            "candles_valid": self.candles_valid,
            "candles_rejected": self.candles_rejected,
            "rejection_reasons": dict(self.rejection_reasons or {}),
            "daily_status": self.daily_status,
            "daily_candles_received": self.daily_candles_received,
            "daily_candles_valid": self.daily_candles_valid,
            "daily_candles_rejected": self.daily_candles_rejected,
            "daily_rejection_reasons": dict(self.daily_rejection_reasons or {}),
            "intraday_status": self.intraday_status,
            "intraday_candles_received": self.intraday_candles_received,
            "intraday_candles_valid": self.intraday_candles_valid,
            "intraday_candles_rejected": self.intraday_candles_rejected,
            "intraday_rejection_reasons": dict(self.intraday_rejection_reasons or {}),
            "baseline_status": self.baseline_status,
            "last_reading_id": self.last_reading_id,
        }