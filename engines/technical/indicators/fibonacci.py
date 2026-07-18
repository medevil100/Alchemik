from typing import List, Tuple, Optional
from data.models.market_data import MarketData

def calculate_fibonacci_levels(high: float, low: float) -> List[float]:
    """
    Calculate Fibonacci retracement levels based on the given high and low prices.

    Args:
        high (float): The highest price in the period.
        low (float): The lowest price in the period.

    Returns:
        List[float]: A list of Fibonacci levels: [0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%].
    """
    diff = high - low
    return [
        high,
        high - 0.236 * diff,
        high - 0.382 * diff,
        high - 0.5 * diff,
        high - 0.618 * diff,
        high - 0.786 * diff,
        low
    ]

def find_nearest_fibonacci_level(price: float, levels: List[float]) -> Tuple[int, float, str]:
    """
    Find the nearest Fibonacci level to the current price.

    Args:
        price (float): The current price.
        levels (List[float]): List of Fibonacci levels.

    Returns:
        Tuple[int, float, str]: Index of the nearest level, distance from the level, and direction ("above" or "below").
    """
    nearest_idx = 0
    min_distance = abs(price - levels[0])
    for i, level in enumerate(levels[1:], 1):
        distance = abs(price - level)
        if distance < min_distance:
            min_distance = distance
            nearest_idx = i
    
    direction = "above" if price > levels[nearest_idx] else "below"
    return nearest_idx, min_distance, direction

def get_fibonacci_analysis(price: float, high: float, low: float, tolerance: Optional[float] = None) -> dict:
    """
    Perform a Fibonacci analysis for the given price, high, and low values.

    Args:
        price (float): The current price.
        high (float): The highest price in the period.
        low (float): The lowest price in the period.
        tolerance (Optional[float]): Tolerance for determining if the price is exactly on a level.

    Returns:
        dict: A dictionary containing:
            - levels: List of Fibonacci levels.
            - nearest_level: Index of the nearest Fibonacci level.
            - distance: Distance from the nearest level.
            - between_levels: Tuple of indices of the levels between which the price lies.
            - direction: Direction relative to the nearest level ("above" or "below").
            - is_exact: Whether the price is exactly on a level (within tolerance).
    """
    levels = calculate_fibonacci_levels(high, low)
    nearest_idx, distance, direction = find_nearest_fibonacci_level(price, levels)
    
    # Determine between which levels the price lies
    between_levels = (0, 0)
    for i in range(len(levels) - 1):
        if (price >= levels[i+1] and price <= levels[i]) or (price <= levels[i+1] and price >= levels[i]):
            between_levels = (i, i+1)
            break
    
    # Check if price is exactly on a level (within tolerance)
    is_exact = False
    if tolerance is not None:
        for level in levels:
            if abs(price - level) <= tolerance:
                is_exact = True
                nearest_idx = levels.index(level)
                distance = 0
                direction = "on"
                break
    
    return {
        "levels": levels,
        "nearest_level": nearest_idx,
        "distance": distance,
        "between_levels": between_levels,
        "direction": direction,
        "is_exact": is_exact
    }