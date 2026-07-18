"""
Implementation of the MACD (Moving Average Convergence Divergence) indicator.

This module provides functions to calculate the MACD line, signal line, and MACD histogram.
"""
from typing import List
from data.models.market_data import MarketData
from ..utils import validate_data
from .ema import calculate_ema


def calculate_macd_line(data: List[MarketData], fast_window: int = 12, slow_window: int = 26) -> List[float]:
    """
    Calculate the MACD line (difference between fast and slow EMA).

    Args:
        data: List of MarketData objects containing price information.
        fast_window: The window size for the fast EMA. Default is 12.
        slow_window: The window size for the slow EMA. Default is 26.

    Returns:
        List[float]: The MACD line values.

    Raises:
        ValueError: If the data is empty or windows are invalid.
    """
    validate_data(data)
    if fast_window <= 0 or slow_window <= 0:
        raise ValueError("Window sizes must be positive integers.")
    if fast_window >= slow_window:
        raise ValueError("Fast window must be smaller than slow window.")

    # Calculate fast and slow EMAs
    fast_ema = calculate_ema(data, fast_window)
    slow_ema = calculate_ema(data, slow_window)

    # MACD line is the difference between fast and slow EMA (handle None values)
    macd_line = []
    for fast, slow in zip(fast_ema, slow_ema):
        if fast is None or slow is None:
            macd_line.append(None)
        else:
            macd_line.append(fast - slow)
    return macd_line


def calculate_signal_line(macd_line: List[float], signal_window: int = 9) -> List[float]:
    """
    Calculate the signal line (EMA of the MACD line).

    Args:
        macd_line: List of MACD line values.
        signal_window: The window size for the signal EMA. Default is 9.

    Returns:
        List[float]: The signal line values.

    Raises:
        ValueError: If the MACD line is empty or the window is invalid.
    """
    if not macd_line:
        raise ValueError("MACD line cannot be empty.")
    if signal_window <= 0:
        raise ValueError("Signal window must be a positive integer.")

    # Signal line is the EMA of the MACD line (filter out None values)
    filtered_macd = [x for x in macd_line if x is not None]
    if not filtered_macd:
        return [None] * len(macd_line)
        
    # Calculate EMA on valid values only
    signal_ema = calculate_ema([MarketData(close=x, open=0, high=0, low=0, volume=0, timestamp=0) for x in filtered_macd], signal_window)
    
    # Reconstruct full signal line with None values where original MACD was None
    signal_line = []
    macd_iter = iter(macd_line)
    ema_iter = iter(signal_ema)
    
    for val in macd_line:
        if val is None:
            signal_line.append(None)
        else:
            signal_line.append(next(ema_iter))
    
    return signal_line


def calculate_macd_histogram(macd_line: List[float], signal_line: List[float]) -> List[float]:
    """
    Calculate the MACD histogram (difference between MACD line and signal line).

    Args:
        macd_line: List of MACD line values.
        signal_line: List of signal line values.

    Returns:
        List[float]: The MACD histogram values.

    Raises:
        ValueError: If the lengths of MACD line and signal line do not match.
    """
    if len(macd_line) != len(signal_line):
        raise ValueError("MACD line and signal line must have the same length.")

    histogram = []
    for macd, signal in zip(macd_line, signal_line):
        if macd is None or signal is None:
            histogram.append(None)
        else:
            histogram.append(macd - signal)
    return histogram
