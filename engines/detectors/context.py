"""
DetectionContext — immutable input container for all market event detectors.

Every detector receives a fully validated DetectionContext.  A context
without OHLCV data cannot be created; an empty OHLCV tuple is a contract
error, not a missing-detection signal.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — §11.4
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from data.models.event_enums import InstrumentType
from data.models.market_data import MarketData


@dataclass(frozen=True)
class DetectionContext:
    """
    Immutable container with the data required by every detector.

    Fields
    ------
    ticker: str
        Instrument symbol (e.g. ``"PKN.ORLEN.WA"``).  Must be non-empty.
    market: str
        Trading venue (e.g. ``"GPW"``, ``"NYSE"``).  Must be non-empty.
    instrument_type: InstrumentType
        Classification of the instrument.
    ohlcv_data: tuple[MarketData, ...]
        Non-empty tuple of OHLCV candles ordered chronologically
        (oldest first).  Every element must be a ``MarketData`` instance;
        duplicate or mis-ordered timestamps are rejected.
    """

    ticker: str
    market: str
    instrument_type: InstrumentType
    ohlcv_data: tuple[MarketData, ...]

    def __post_init__(self) -> None:
        # -- ticker -----------------------------------------------------------
        if not isinstance(self.ticker, str):
            raise TypeError(
                f"ticker must be str, got {type(self.ticker).__name__}"
            )
        if not self.ticker.strip():
            raise ValueError("ticker must not be empty or whitespace-only")

        # -- market -----------------------------------------------------------
        if not isinstance(self.market, str):
            raise TypeError(
                f"market must be str, got {type(self.market).__name__}"
            )
        if not self.market.strip():
            raise ValueError("market must not be empty or whitespace-only")

        # -- instrument_type --------------------------------------------------
        if not isinstance(self.instrument_type, InstrumentType):
            raise TypeError(
                "instrument_type must be an InstrumentType instance, "
                f"got {type(self.instrument_type).__name__}"
            )

        # -- ohlcv_data -------------------------------------------------------
        if not isinstance(self.ohlcv_data, tuple):
            raise TypeError(
                "ohlcv_data must be a tuple, "
                f"got {type(self.ohlcv_data).__name__}"
            )
        if len(self.ohlcv_data) == 0:
            raise ValueError("ohlcv_data must contain at least one MarketData item")

        prev_ts: datetime | None = None
        for idx, item in enumerate(self.ohlcv_data):
            if not isinstance(item, MarketData):
                raise TypeError(
                    f"ohlcv_data[{idx}] must be MarketData, "
                    f"got {type(item).__name__}"
                )
            ts = item.timestamp
            if not isinstance(ts, datetime):
                raise TypeError(
                    f"ohlcv_data[{idx}].timestamp must be datetime, "
                    f"got {type(ts).__name__}"
                )
            if prev_ts is not None:
                if ts <= prev_ts:
                    raise ValueError(
                        f"ohlcv_data is not in strict chronological order: "
                        f"timestamp at index {idx} ({ts.isoformat()}) "
                        f"is not greater than timestamp at index {idx - 1} "
                        f"({prev_ts.isoformat()})"
                    )
            prev_ts = ts