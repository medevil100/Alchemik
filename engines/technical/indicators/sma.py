"""Simple Moving Average (SMA) indicator implementation."""

from typing import List
from data.models.market_data import MarketData


def calculate_sma(data: List[MarketData], window: int = 20) -> List[float]:
    """Calculate Simple Moving Average for given market data.
    
    Args:
        data: List of MarketData objects
        window: Number of periods to average (default: 20)
        
    Returns:
        List of SMA values (same length as input data)
    """
    if len(data) < window:
        raise ValueError(f"Not enough data points for window size {window}")
        
    closes = [d.close for d in data]
    sma_values = []
    
    for i in range(len(closes) - window + 1):
        window_values = closes[i:i + window]
        sma_values.append(sum(window_values) / window)
    
    # Pad beginning with None values for alignment
    return [None] * (window - 1) + sma_values