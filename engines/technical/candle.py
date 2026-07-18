"""
Candle Engine Module

This module analyzes single candle parameters without interpreting market conditions.
It provides raw data about the candle's direction, body size, wick lengths, and their percentages.
"""
from typing import Tuple, Dict, Optional
from dataclasses import dataclass
from data.models.market_data import MarketData


@dataclass
class CandleAnalysisResult:
    """
    Data class to store the results of candle analysis.
    """
    direction: str  # "up", "down", or "neutral"
    body_size: float
    upper_wick_length: float
    lower_wick_length: float
    body_percentage: float
    upper_wick_percentage: float
    lower_wick_percentage: float
    total_range: float
    body_to_wicks_ratio: float
    is_body_dominant: bool
    are_wicks_dominant: bool


def analyze_candle(candle: MarketData) -> Optional[CandleAnalysisResult]:
    """
    Analyze a single candle and return its parameters.

    Args:
        candle: The candle data to analyze.

    Returns:
        CandleAnalysisResult: The analysis result or None if analysis fails.
    """
    try:
        open_price = candle.open
        close_price = candle.close
        high_price = candle.high
        low_price = candle.low

        # Determine candle direction
        if close_price > open_price:
            direction = "up"
        elif close_price < open_price:
            direction = "down"
        else:
            direction = "neutral"

        # Calculate candle parameters
        body_size = abs(close_price - open_price)
        upper_wick_length = high_price - max(open_price, close_price)
        lower_wick_length = min(open_price, close_price) - low_price
        total_range = high_price - low_price

        # Calculate percentages
        if total_range > 0:
            body_percentage = (body_size / total_range) * 100
            upper_wick_percentage = (upper_wick_length / total_range) * 100
            lower_wick_percentage = (lower_wick_length / total_range) * 100
        else:
            body_percentage = 0.0
            upper_wick_percentage = 0.0
            lower_wick_percentage = 0.0

        # Calculate body-to-wicks ratio and dominance
        body_to_wicks_ratio = body_size / (upper_wick_length + lower_wick_length) if (upper_wick_length + lower_wick_length) > 0 else 0.0
        is_body_dominant = body_percentage > 50
        are_wicks_dominant = (upper_wick_percentage + lower_wick_percentage) > 50

        return CandleAnalysisResult(
            direction=direction,
            body_size=body_size,
            upper_wick_length=upper_wick_length,
            lower_wick_length=lower_wick_length,
            body_percentage=body_percentage,
            upper_wick_percentage=upper_wick_percentage,
            lower_wick_percentage=lower_wick_percentage,
            total_range=total_range,
            body_to_wicks_ratio=body_to_wicks_ratio,
            is_body_dominant=is_body_dominant,
            are_wicks_dominant=are_wicks_dominant
        )
    except Exception as e:
        print(f"Error analyzing candle: {e}")
        return None