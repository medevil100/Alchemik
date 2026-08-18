"""Exponential Moving Average (EMA) indicator implementation."""

from typing import List
from data.models.market_data import MarketData
from engines.technical.errors import InsufficientDataError


def calculate_ema(data: List[MarketData], window: int = 20) -> List[float]:
    """Calculate Exponential Moving Average for given market data.
    
    Args:
        data: List of MarketData objects
        window: Number of periods to average (default: 20)
        
    Returns:
        List of EMA values (same length as input data)
    """
    if len(data) < window:
        raise InsufficientDataError(
            f"Not enough data points for window size {window}"
        )
        
    closes = [d.close for d in data]
    ema_values = []
    multiplier = 2 / (window + 1)
    
    # Calculate first EMA as SMA
    sma = sum(closes[:window]) / window
    ema_values.append(sma)
    
    # Calculate subsequent EMAs
    for i in range(window, len(closes)):
        ema = (closes[i] - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema)
    
    # Pad beginning with None values for alignment
    return [None] * (window - 1) + ema_values