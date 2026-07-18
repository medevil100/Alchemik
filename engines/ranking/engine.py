"""
Ranking Engine implementation for the ALCHEMIK project.

This module provides the RankingEngine class which is responsible for:
- Accepting analysis results from other engines
- Calculating weighted ranking scores
- Sorting and returning standardized rankings
"""
from typing import List
from dataclasses import dataclass
from data.models.analysis_result import AnalysisResult

@dataclass
class RankingResult:
    """Model representing a single ranked result."""
    symbol: str
    score: float
    details: dict

@dataclass
class FullRanking:
    """Model representing a complete ranking of instruments."""
    results: List[RankingResult]
    timestamp: str

class RankingEngine:
    """Main Ranking Engine class."""
    
    def __init__(self, config_path: str = None):
        """Initialize with optional path to ranking configuration."""
        self.weights = self._load_weights(config_path)
    
    def _load_weights(self, config_path: str) -> dict:
        """Load ranking weights from configuration."""
        from config.ranking import DEFAULT_WEIGHTS
        return DEFAULT_WEIGHTS
    
    def calculate_ranking(self, analysis_results: List[AnalysisResult]) -> FullRanking:
        """
        Calculate and return a ranked list of instruments.
        
        Args:
            analysis_results: List of analysis results from other engines
            
        Returns:
            FullRanking object with sorted results
        """
        if not analysis_results:
            return FullRanking([], "")
            
        ranked = []
        for result in analysis_results:
            score = self._calculate_score(result)
            ranked.append(RankingResult(
                symbol=result.company.symbol,
                score=score,
                details={
                    "company": result.company.__dict__,
                    "market_data": [d.__dict__ for d in result.market_data],
                    "news": [n.__dict__ for n in result.news] if result.news else [],
                    "signals": [s.__dict__ for s in result.signals] if result.signals else []
                }
            ))
        
        # Sort by score descending
        ranked.sort(key=lambda x: x.score, reverse=True)
        
        from datetime import datetime, timezone
        return FullRanking(ranked, datetime.now(timezone.utc).isoformat())
    
    def _calculate_score(self, result: AnalysisResult) -> float:
        """Calculate weighted score for a single instrument."""
        score = 0.0
        
        # Calculate technical component (from market data)
        if result.market_data:
            technical_score = sum(d.close for d in result.market_data)/len(result.market_data) / 100  # Normalize to 0-1 range
            score += technical_score * self.weights['technical']
        
        # Calculate news component (average sentiment)
        if result.news:
            news_score = sum(n.sentiment for n in result.news)/len(result.news)
            score += news_score * self.weights['news']
        else:
            score += 0.0
        
        # Calculate AI signal component (confidence)
        if result.signals:
            signal_score = sum(s.confidence for s in result.signals)/len(result.signals)
            score += signal_score * self.weights['ai_signal']
        else:
            score += 0.0
            
        return score
