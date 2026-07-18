from typing import List
from data.models.market_data import MarketData

def calculate_obv(data: List[MarketData]) -> List[float]:
    """
    Calculate On Balance Volume (OBV) for the given market data.
    
    Args:
        data (List[MarketData]): List of market data points.
        
    Returns:
        List[float]: List of OBV values for each data point.
    
    Raises:
        ValueError: If the input data is empty.
    """
    if not data:
        raise ValueError("Input data cannot be empty.")
    
    obv_values = []
    obv = 0.0
    
    for i in range(len(data)):
        if i == 0:
            obv = data[i].volume
        else:
            if data[i].close > data[i - 1].close:
                obv += data[i].volume
            elif data[i].close < data[i - 1].close:
                obv -= data[i].volume
            # No change if close price is equal
        
        obv_values.append(obv)
    
    return obv_values