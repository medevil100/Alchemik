"""News Analyzer module for AI Engine.

This module is responsible for preparing news data from the News Engine
for analysis by the AI Provider. It communicates with the News Engine exclusively
via its Public API and does not interpret results or make investment decisions.
"""

from typing import Dict, Any, List
from data.models.news_item import NewsItem
from data.models.ai_signal import AISignal
from engines.news import NewsPipeline


class NewsAnalyzer:
    """Prepares news data for AI Provider analysis."""

    def __init__(self):
        """Initialize the NewsAnalyzer with a NewsPipeline instance."""
        self.news_pipeline = NewsPipeline(filter_config=None)

    def fetch_news_data(self, market_data: Dict[str, Any]) -> List[AISignal]:
        """Fetch and prepare news data from the News Engine.

        Args:
            market_data: Raw market data to be analyzed.

        Returns:
            List[AISignal]: Structured news analysis results.
        """
        try:
            # Process the market data using the News Engine's Public API
            news_items = self.news_pipeline.process(market_data)
            
            # Prepare the results for AI Provider
            ai_signals = [
                AISignal(
                    news_id=item.news_id,
                    content=item.content,
                    timestamp=item.timestamp
                ) for item in news_items
            ]
            
            return ai_signals
        except Exception as e:
            raise RuntimeError(f"Failed to fetch news data: {e}")

    def __repr__(self) -> str:
        return "<NewsAnalyzer>"