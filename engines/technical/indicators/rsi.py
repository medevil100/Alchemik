"""Relative Strength Index (RSI) indicator implementation."""

from typing import List
from data.models.market_data import MarketData


def calculate_rsi(data: List[MarketData], window: int = 14) -> List[float]:
    """Calculate Relative Strength Index for given market data.
    
    Args:
        data: List of MarketData objects
        window: Number of periods to calculate RSI (default: 14)
        
    Returns:
        List of RSI values (same length as input data)
    """
    if len(data) < window + 1:
        raise ValueError(f"Not enough data points for window size {window}")
    
    closes = [d.close for d in data]
    rsi_values = []
    gains = []
    losses = []
    
    # Calculate initial average gains and losses
    for i in range(1, window + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    
    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window
    
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    rsi_values.append(rsi)
    
    # Calculate subsequent RSI values
    for i in range(window + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        current_gain = max(change, 0)
        current_loss = max(-change, 0)
        
        avg_gain = (avg_gain * (window - 1) + current_gain) / window
        avg_loss = (avg_loss * (window - 1) + current_loss) / window
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
    
    # Pad beginning with None values for alignment
    return [None] * window + rsi_values