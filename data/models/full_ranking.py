"""
Model representing a complete ranking result for the Ranking Engine.
"""
from dataclasses import dataclass
from typing import List
from .ranking_result import RankingResult

@dataclass
class FullRanking:
    """
    Data class representing a complete ranking of instruments.
    
    Attributes:
        results: List of ranked instruments (sorted best to worst)
        timestamp: ISO format timestamp of when ranking was calculated
    """
    results: List[RankingResult]
    timestamp: str