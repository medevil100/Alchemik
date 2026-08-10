"""
Model for Hunter Engine results.
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class HunterResult:
    """
    Result for a single opportunity identified by the Hunter Engine.

    Two paths produce this result:

    1. **MarketScanner pass-through** (Krok 6A):
       ``instrument_id`` = ``symbol`` from the candidate.
       All scoring fields (``hunter_score``, ``priority``, ``ranking_score``,
       ``risk_score``, ``confidence``) are ``None`` — they do not exist yet
       at this stage.

    2. **Single-instrument scoring** (Hunter pojedynczego instrumentu):
       All scoring fields carry real values calculated from the input dict.

    Attributes:
        instrument_id (str): Unique identifier for the instrument.
        hunter_score (Optional[float]): Calculated hunter score (0.0-1.0),
            or ``None`` for MarketScanner pass-through.
        priority (Optional[int]): Priority level,
            or ``None`` for MarketScanner pass-through.
        ranking_score (Optional[float]): Ranking score from Ranking Engine,
            or ``None`` for MarketScanner pass-through.
        risk_score (Optional[float]): Risk score from Risk Engine,
            or ``None`` for MarketScanner pass-through.
        risk_level (str): Risk level (e.g., 'low', 'medium', 'high').
        confidence (Optional[float]): Confidence level from AI Engine,
            or ``None`` for MarketScanner pass-through.
        reasons (List[str]): List of reasons for qualification.
        warnings (List[str]): List of warnings.
        timestamp (datetime): Timestamp of the result.
    """
    instrument_id: str
    hunter_score: Optional[float]
    priority: Optional[int]
    ranking_score: Optional[float]
    risk_score: Optional[float]
    risk_level: str
    confidence: Optional[float]
    reasons: List[str]
    warnings: List[str]
    timestamp: datetime

@dataclass
class HunterScanResult:
    """
    Result of a complete scan by the Hunter Engine.

    Attributes:
        opportunities (List[HunterResult]): Sorted list of opportunities.
        analyzed (int): Number of analyzed instruments.
        rejected (int): Number of rejected instruments.
        qualified (int): Number of qualified opportunities.
        timestamp (datetime): Timestamp of the scan.
    """
    opportunities: List[HunterResult]
    analyzed: int
    rejected: int
    qualified: int
    timestamp: datetime