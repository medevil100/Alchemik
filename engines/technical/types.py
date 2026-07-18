"""Type definitions and interfaces for technical analysis."""

from typing import Protocol, List
from data.models.market_data import MarketData
from data.models.analysis_result import AnalysisResult


class Indicator(Protocol):
    """Protocol for technical analysis indicators."""

    def calculate(self, data: List[MarketData]) -> AnalysisResult:
        """Calculate the indicator value for the given data.

        Args:
            data: List of MarketData objects to analyze.

        Returns:
            AnalysisResult: The result of the indicator calculation.
        """
        ...