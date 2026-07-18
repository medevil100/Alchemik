"""Utility functions for technical analysis."""

from typing import List
from data.models.market_data import MarketData


def validate_data(data: List[MarketData]) -> bool:
    """Validate the input market data for technical analysis.

    Args:
        data: List of MarketData objects to validate.

    Returns:
        bool: True if data is valid, False otherwise.
    """
    return len(data) > 0