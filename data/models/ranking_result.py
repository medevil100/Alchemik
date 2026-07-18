"""
Model representing a single ranked result for the Ranking Engine.
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RankingResult:
    """
    Data class representing a single ranked instrument.
    
    Attributes:
        instrument_id: Unique identifier for the instrument
        score: Calculated ranking score (higher is better)
        details: Dictionary containing all scoring components
    """
    instrument_id: str
    score: float
    details: Dict[str, Any]