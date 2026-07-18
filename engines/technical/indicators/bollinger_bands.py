from typing import List, Tuple
from data.models.market_data import MarketData
from engines.technical.indicators.sma import calculate_sma

def calculate_bollinger_bands(data: List[MarketData], window: int = 20, num_std_dev: int = 2) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate the Bollinger Bands (upper, middle, lower) for a given list of MarketData.
    
    Args:
        data (List[MarketData]): List of MarketData objects containing OHLCV data.
        window (int, optional): The window size for the moving average. Defaults to 20.
        num_std_dev (int, optional): The number of standard deviations for the bands. Defaults to 2.
    
    Returns:
        Tuple[List[float], List[float], List[float]]: A tuple containing the upper, middle, and lower bands.
    
    Raises:
        ValueError: If the window size is invalid or data is insufficient.
    """
    if window <= 0:
        raise ValueError("Window size must be a positive integer.")
    if len(data) < window:
        raise ValueError("Insufficient data points for the specified window size.")
    
    middle_band = calculate_sma(data, window)
    
    # Calculate standard deviation of closing prices
    std_devs = []
    for i in range(window - 1, len(data)):
        window_data = data[i - window + 1:i + 1]
        closes = [d.close for d in window_data]
        mean = sum(closes) / window
        variance = sum((x - mean) ** 2 for x in closes) / window
        std_dev = variance ** 0.5
        std_devs.append(std_dev)
    
    # Pad std_devs to match input data length
    std_devs_padded = [None] * (window - 1) + std_devs
    
    upper_band = []
    lower_band = []
    
    for i in range(len(middle_band)):
        if middle_band[i] is None:
            upper_band.append(None)
            lower_band.append(None)
        else:
            upper_band.append(middle_band[i] + num_std_dev * std_devs_padded[i])
            lower_band.append(middle_band[i] - num_std_dev * std_devs_padded[i])
    
    return upper_band, middle_band, lower_band
