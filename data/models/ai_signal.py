from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class AISignal:
    """
    Represents a single AI-generated analysis signal for a financial instrument.
    
    Attributes:
        signal_type (str): Type of signal (e.g., 'buy', 'sell', 'hold')
        confidence (float): Confidence score (0-1)
        generated_at (datetime): When the signal was generated
        reasoning (Optional[str]): Brief explanation of the signal
        model_version (Optional[str]): AI model version that generated this
    """
    signal_type: str
    confidence: float
    generated_at: datetime
    reasoning: Optional[str] = None
    model_version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        """Create AISignal from a dictionary (for potential API responses)."""
        return cls(
            signal_type=data['signal_type'],
            confidence=data['confidence'],
            generated_at=datetime.fromisoformat(data['generated_at']),
            reasoning=data.get('reasoning'),
            model_version=data.get('model_version')
        )