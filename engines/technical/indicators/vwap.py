from typing import List
from data.models.market_data import MarketData

def calculate_vwap(data: List[MarketData]) -> List[float]:
    """
    Calculate Volume Weighted Average Price (VWAP) for the given market data.
    
    Args:
        data (List[MarketData]): List of market data points.
        
    Returns:
        List[float]: List of VWAP values for each data point.
    
    Raises:
        ValueError: If the input data is empty.
    """
    if not data:
        raise ValueError("Input data cannot be empty.")
    
    vwap_values = []
    cumulative_volume = 0.0
    cumulative_price_volume = 0.0
    
    for point in data:
        typical_price = (point.high + point.low + point.close) / 3
        cumulative_price_volume += typical_price * point.volume
        cumulative_volume += point.volume
        
        if cumulative_volume == 0:
            vwap_values.append(0.0)
        else:
            vwap_values.append(cumulative_price_volume / cumulative_volume)
    
    return vwap_values