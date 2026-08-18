from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class FinalAnalysisResult:
    """
    Represents the final analysis result from Analyst Engine.
    
    Attributes:
        symbol (str): Instrument symbol
        final_rating (float): Final analysis rating (0.0-1.0)
        confidence_level (float): Confidence level (0.0-1.0)
        recommendation (str): Buy/Hold/Sell recommendation
        positive_factors (List[str]): Key positive arguments
        risk_factors (List[str]): Key risk factors
        warnings (List[str]): Analysis warnings
        summary (str): Textual analysis summary
        generated_at (datetime): When this analysis was performed
    """
    symbol: str
    final_rating: float
    confidence_level: float
    recommendation: str
    positive_factors: List[str]
    risk_factors: List[str]
    warnings: List[str]
    summary: str
    generated_at: datetime

    @classmethod
    def from_dict(cls, data: dict):
        """Create FinalAnalysisResult from a dictionary."""
        return cls(
            symbol=data['symbol'],
            final_rating=data['final_rating'],
            confidence_level=data['confidence_level'],
            recommendation=data['recommendation'],
            positive_factors=data['positive_factors'],
            risk_factors=data['risk_factors'],
            warnings=data['warnings'],
            summary=data['summary'],
            generated_at=datetime.fromisoformat(data['generated_at'])
        )