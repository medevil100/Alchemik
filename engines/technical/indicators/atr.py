from typing import List
from data.models.market_data import MarketData

def calculate_atr(data: List[MarketData], window: int = 14) -> List[float]:
    """
    Calculate the Average True Range (ATR) for a given list of MarketData.
    
    Args:
        data (List[MarketData]): List of MarketData objects containing OHLCV data.
        window (int, optional): The window size for the ATR calculation. Defaults to 14.
    
    Returns:
        List[float]: A list of ATR values.
    
    Raises:
        ValueError: If the window size is invalid or data is insufficient.
    """
    if window <= 0:
        raise ValueError("Window size must be a positive integer.")
    if len(data) < window:
        raise ValueError("Insufficient data points for the specified window size.")
    
    true_ranges = []
    for i in range(1, len(data)):
        high = data[i].high
        low = data[i].low
        previous_close = data[i - 1].close
        
        tr1 = high - low
        tr2 = abs(high - previous_close)
        tr3 = abs(low - previous_close)
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    atr_values = []
    for i in range(window - 1, len(true_ranges)):
        atr = sum(true_ranges[i - window + 1:i + 1]) / window
        atr_values.append(atr)
    
    return atr_values