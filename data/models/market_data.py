from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MarketData:
    """
    Represents OHLCV (Open, High, Low, Close, Volume) market data for a financial instrument.
    
    Attributes:
        open (float): Opening price of the period
        high (float): Highest price during the period
        low (float): Lowest price during the period
        close (float): Closing price of the period
        volume (float): Trading volume during the period
        timestamp (datetime): Date and time of the data point
        timeframe (Optional[str]): Krok 7C — kanoniczny interwał (np. "1h").
        candle_state (Optional[str]): Krok 7C — "OPEN" albo "CLOSED".
        observed_at (Optional[datetime]): Krok 7C — jeden wspólny czas obserwacji
            użyty do klasyfikacji stanu świecy.
    """
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    timeframe: Optional[str] = None
    candle_state: Optional[str] = None
    observed_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict):
        """Create MarketData from a dictionary (for potential API responses)."""
        return cls(
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )