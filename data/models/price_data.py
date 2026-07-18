from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PriceData:
    """
    Price data related to a market event.

    Contains OHLCV values from current and previous candles
    relevant to the event, as specified in the Kontrakt Zdarzen Rynkowych.

    Fields:
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        prev_close: Previous closing price
        change_pct: Percentage change
        change_abs: Absolute change
    """

    open: float
    high: float
    low: float
    close: float
    prev_close: float
    change_pct: float
    change_abs: float

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "prev_close": self.prev_close,
            "change_pct": self.change_pct,
            "change_abs": self.change_abs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PriceData":
        """Deserialize from a dictionary."""
        return cls(
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            prev_close=data["prev_close"],
            change_pct=data["change_pct"],
            change_abs=data["change_abs"],
        )