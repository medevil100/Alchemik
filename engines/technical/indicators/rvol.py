from typing import List, Optional
from data.models.market_data import MarketData
from config.indicators import IndicatorsConfig

def calculate_relative_volume(data: List[MarketData], period: Optional[int] = None) -> List[float]:
    """
    Calculate Relative Volume (RVOL) for the given market data.
    
    Args:
        data (List[MarketData]): List of market data points.
        period (Optional[int]): Period for calculating the average volume.
            If not provided, the value from IndicatorsConfig will be used.
        
    Returns:
        List[float]: List of RVOL values for each data point.
    
    Raises:
        ValueError: If the input data is empty or period is invalid.
    """
    if not data:
        raise ValueError("Input data cannot be empty.")
    
    if period is None:
        period = IndicatorsConfig.relative_volume_period
        if period is None:
            raise ValueError("Relative Volume period is not configured.")
    
    if period <= 0:
        raise ValueError("Period must be a positive integer.")
    
    rvol_values = []
    
    for i in range(len(data)):
        if i < period - 1:
            rvol_values.append(0.0)
        else:
            avg_volume = sum(point.volume for point in data[i - period + 1:i + 1]) / period
            if avg_volume == 0:
                rvol_values.append(0.0)
            else:
                rvol_values.append(data[i].volume / avg_volume)
    
    return rvol_values