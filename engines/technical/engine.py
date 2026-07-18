"""Core engine for technical analysis.

This module implements the main logic for processing financial data
and generating technical analysis results.
"""

from typing import List, Dict, Any
from datetime import datetime
from data.models.market_data import MarketData
from data.models.analysis_result import AnalysisResult
from .indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd_line,
    calculate_signal_line,
    calculate_macd_histogram,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_vwap,
    calculate_obv,
    calculate_relative_volume,
    get_fibonacci_analysis
)


class TechnicalEngine:
    """Engine for performing technical analysis on financial data."""

    def __init__(self):
        """Initialize the TechnicalEngine."""
        pass

    def analyze(self, data: List[MarketData]) -> AnalysisResult:
        """Analyze the given market data and return the analysis result.

        Args:
            data: List of MarketData objects to analyze.

        Returns:
            AnalysisResult: The result of the technical analysis.
        """
        # Create AnalysisResult with required fields
        result = AnalysisResult(
            company=None,
            market_data=data,
            news=[],
            signals=[],
            generated_at=datetime.now()
        )
        
        # Calculate all indicators and store them in a separate dict
        indicators = {}
        indicators["sma"] = calculate_sma(data)
        indicators["ema"] = calculate_ema(data)
        indicators["rsi"] = calculate_rsi(data)
        
        macd_line = calculate_macd_line(data)
        signal_line = calculate_signal_line(macd_line)
        indicators["macd"] = {
            "line": macd_line,
            "signal": signal_line,
            "histogram": calculate_macd_histogram(macd_line, signal_line)
        }
        
        indicators["atr"] = calculate_atr(data)
        
        upper, middle, lower = calculate_bollinger_bands(data)
        indicators["bollinger_bands"] = {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
        
        indicators["vwap"] = calculate_vwap(data)
        indicators["obv"] = calculate_obv(data)
        indicators["rvol"] = calculate_relative_volume(data)
        
        # Fibonacci analysis requires high/low prices
        if len(data) > 0:
            high = max(d.high for d in data)
            low = min(d.low for d in data)
            indicators["fibonacci"] = get_fibonacci_analysis(data[-1].close, high, low)
        
        # Store indicators in the result for compatibility
        result.indicators = indicators
        
        return result
