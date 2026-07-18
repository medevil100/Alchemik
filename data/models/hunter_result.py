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

    Attributes:
        instrument_id (str): Unique identifier for the instrument.
        hunter_score (float): Calculated hunter score (0.0-1.0).
        priority (int): Priority level.
        ranking_score (float): Ranking score from Ranking Engine.
        risk_score (float): Risk score from Risk Engine.
        risk_level (str): Risk level (e.g., 'low', 'medium', 'high').
        confidence (float): Confidence level from AI Engine.
        reasons (List[str]): List of reasons for qualification.
        warnings (List[str]): List of warnings.
        timestamp (datetime): Timestamp of the result.
    """
    instrument_id: str
    hunter_score: float
    priority: int
    ranking_score: float
    risk_score: float
    risk_level: str
    confidence: float
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