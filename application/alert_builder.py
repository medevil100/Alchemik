from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Optional
from data.models.final_analysis_result import FinalAnalysisResult

@dataclass
class AlertMessage:
    """
    Model for alert messages to be formatted and potentially sent.
    """
    alert_id: str
    symbol: str
    market: Optional[str]
    recommendation: str
    final_score: float
    confidence_level: float
    risk_level: Optional[str]
    summary: str
    created_at: datetime
    formatted_message: str

class AlertBuilder:
    """
    Builds alerts from FinalAnalysisResult objects.
    """
    
    def __init__(self, 
                 min_final_score: float = 0.7, 
                 min_confidence: float = 0.7,
                 allowed_recommendations: list[str] = ["STRONG_BUY", "BUY"]):
        """
        Initialize with configurable thresholds.
        
        Args:
            min_final_score: Minimum final_score to trigger alert (0.0-1.0)
            min_confidence: Minimum confidence_level to trigger alert (0.0-1.0)
            allowed_recommendations: List of recommendation values that qualify for alerts
        """
        self.min_final_score = min_final_score
        self.min_confidence = min_confidence
        self.allowed_recommendations = allowed_recommendations
    
    def should_alert(self, result: FinalAnalysisResult) -> bool:
        """
        Determine if a result qualifies for an alert.
        
        Args:
            result: FinalAnalysisResult to evaluate
            
        Returns:
            bool: True if result meets alert criteria
        """
        if not result or not isinstance(result, FinalAnalysisResult):
            raise ValueError("Invalid FinalAnalysisResult provided")
            
        if not result.symbol:
            raise ValueError("Symbol cannot be empty")
            
        # Convert 0-100 scale to 0-1 for comparison
        final_score = result.final_rating / 100
        confidence = result.confidence_level / 100
        
        return (final_score >= self.min_final_score and 
                confidence >= self.min_confidence and 
                result.recommendation in self.allowed_recommendations)
    
    def build_alert(self, result: FinalAnalysisResult) -> AlertMessage:
        """
        Create an AlertMessage from a qualifying FinalAnalysisResult.
        
        Args:
            result: FinalAnalysisResult that qualifies for alert
            
        Returns:
            AlertMessage: Standardized alert object
        """
        if not self.should_alert(result):
            raise ValueError("Result does not qualify for alert")
            
        # Create deterministic alert_id
        hash_input = f"{result.symbol}:{result.recommendation}:{result.generated_at.isoformat()}"
        alert_id = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Prepare formatted message
        formatted_msg = (
            f"Symbol: {result.symbol}\n"
            f"Recommendation: {result.recommendation}\n"
            f"Score: {result.final_rating:.1f}\n"
            f"Confidence: {result.confidence_level:.1f}%\n"
            f"Summary: {result.summary}"
        )
        
        return AlertMessage(
            alert_id=alert_id,
            symbol=result.symbol,
            market=None,  # Can be enhanced later
            recommendation=result.recommendation,
            final_score=result.final_rating / 100,
            confidence_level=result.confidence_level / 100,
            risk_level=None,  # Can be enhanced later
            summary=result.summary,
            created_at=datetime.now(),
            formatted_message=formatted_msg
        )
    
    def format_message(self, alert: AlertMessage) -> str:
        """
        Format the alert message for display.
        
        Args:
            alert: AlertMessage to format
            
        Returns:
            str: Formatted message text
        """
        return alert.formatted_message