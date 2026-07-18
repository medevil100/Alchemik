from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class RiskResult:
    """
    Model representing the output of the Risk Engine.
    """
    instrument_id: str
    risk_score: float
    risk_level: str
    confidence: float
    risk_factors: List[str]
    max_position_size: float
    stop_loss: float
    take_profit: float
    timestamp: datetime