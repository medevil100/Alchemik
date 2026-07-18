"""
Decision Engine for the AI Engine.

This module is responsible for combining data from the Technical Analyzer and News Analyzer
into a unified format for the Prompt Builder. It does not interpret the data or make
investment decisions.
"""

import datetime
from typing import Dict, Any, List
from data.models.ai_signal import AISignal
from data.models.analysis_result import AnalysisResult
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline


class DecisionEngine:
    """Combines technical and news analysis results for the AI Engine."""

    def __init__(self):
        """Initialize the DecisionEngine with instances of TechnicalEngine and NewsPipeline."""
        self.technical_engine = TechnicalEngine()
        self.news_pipeline = NewsPipeline(filter_config=None)

    def process_data(self, market_data: Dict[str, Any]) -> AISignal:
        """
        Process market data by combining results from Technical and News Analyzers.

        Args:
            market_data: Raw market data to be analyzed.

        Returns:
            AISignal: Combined data for the Prompt Builder.

        Raises:
            RuntimeError: If processing fails.
        """
        try:
            # Create an AISignal object
            return AISignal(
                signal_type="combined_analysis",
                confidence=0.0,  # Placeholder - actual confidence should be calculated
                generated_at=datetime.datetime.now(),
                reasoning=f"Technical: {market_data['technical_analysis']}, News: {market_data['news_analysis']}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to process data: {e}")

    def __repr__(self) -> str:
        return "<DecisionEngine>"