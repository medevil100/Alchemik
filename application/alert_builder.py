from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from typing import Optional, List
from data.models.final_analysis_result import FinalAnalysisResult
from data.models.market_event import MarketEvent


@dataclass
class AlertMessage:
    """
    Model for alert messages to be formatted and sent.

    Contains data from both MarketEvent and FinalAnalysisResult.
    """
    alert_id: str
    symbol: str
    market: Optional[str]
    event_type: Optional[str]
    event_family: Optional[str]
    priority_final: Optional[str]
    quality_level: Optional[str]
    is_composite: bool
    composite_count: int
    recommendation: str
    ai_rating: Optional[str]
    final_score: float
    confidence_level: float
    risk_level: Optional[str]
    ai_summary: Optional[str]
    created_at: datetime
    formatted_message: str


class AlertBuilder:
    """
    Builds alerts from MarketEvent and FinalAnalysisResult objects.
    """

    def __init__(self,
                 min_final_score: float = 0.7,
                 min_confidence: float = 0.7,
                 allowed_recommendations: Optional[List[str]] = None):
        """
        Initialize with configurable thresholds.

        Args:
            min_final_score: Minimum final_score to trigger alert (0.0-1.0)
            min_confidence: Minimum confidence_level to trigger alert (0.0-1.0)
            allowed_recommendations: List of recommendation values that qualify for alerts
        """
        self.min_final_score = min_final_score
        self.min_confidence = min_confidence
        self.allowed_recommendations = (
            allowed_recommendations or ["STRONG_BUY", "BUY"]
        )

    # ------------------------------------------------------------------
    # Public API — MarketEvent + FinalAnalysisResult (ETAP 7.5)
    # ------------------------------------------------------------------

    def should_alert(self, result: FinalAnalysisResult,
                     event: Optional[MarketEvent] = None) -> bool:
        """
        Determine if a result qualifies for an alert.

        Accepts FinalAnalysisResult with an optional MarketEvent for
        extended criteria (quality_level, priority_final).

        Args:
            result: FinalAnalysisResult to evaluate.
            event: Optional MarketEvent providing quality/priority context.

        Returns:
            bool: True if result meets alert criteria.
        """
        if not result or not isinstance(result, FinalAnalysisResult):
            raise ValueError("Invalid FinalAnalysisResult provided")

        if not result.symbol:
            raise ValueError("Symbol cannot be empty")

        # Convert 0-100 scale to 0-1 for comparison
        final_score = result.final_rating / 100
        confidence = result.confidence_level / 100

        # Base criteria — final_score, confidence, recommendation
        base_ok = (
            final_score >= self.min_final_score
            and confidence >= self.min_confidence
            and result.recommendation in self.allowed_recommendations
        )
        if not base_ok:
            return False

        # Extended criteria from MarketEvent (when available)
        if event is not None:
            if hasattr(event, 'quality_level') and event.quality_level is not None:
                ql = getattr(event.quality_level, 'value', str(event.quality_level))
                if ql in ("IGNORE", "LOW", "ignore", "low"):
                    return False

        return True

    def build_alert(self, result: FinalAnalysisResult,
                    event: Optional[MarketEvent] = None) -> AlertMessage:
        """
        Create an AlertMessage from a qualifying FinalAnalysisResult
        and optional MarketEvent.

        Args:
            result: FinalAnalysisResult that qualifies for alert.
            event: Optional MarketEvent providing rich context.

        Returns:
            AlertMessage: Standardized alert object with rich formatting.
        """
        if not self.should_alert(result, event):
            raise ValueError("Result does not qualify for alert")

        # Create deterministic alert_id
        symbol = result.symbol
        hash_input = f"{symbol}:{result.recommendation}:{result.generated_at.isoformat()}"
        alert_id = hashlib.sha256(hash_input.encode()).hexdigest()

        # Extract rich context from MarketEvent
        event_type = None
        event_family = None
        priority_final = None
        quality_level = None
        is_composite = False
        composite_count = 0
        ai_summary = None
        market = None
        ai_rating = None

        if event is not None:
            event_type = event.event_type if hasattr(event, 'event_type') else None
            ef = event.event_family if hasattr(event, 'event_family') else None
            event_family = getattr(ef, 'value', str(ef)) if ef is not None else None
            pf = event.priority_final if hasattr(event, 'priority_final') else None
            priority_final = getattr(pf, 'value', str(pf)) if pf is not None else None
            ql = event.quality_level if hasattr(event, 'quality_level') else None
            quality_level = getattr(ql, 'value', str(ql)) if ql is not None else None
            is_composite = bool(event.is_composite) if hasattr(event, 'is_composite') else False
            composite_events = (
                event.composite_events if hasattr(event, 'composite_events') else None
            )
            composite_count = len(composite_events) if isinstance(composite_events, list) else 0
            market = event.market if hasattr(event, 'market') else None

            # Extract AI summary from ai_context
            ai_ctx = event.ai_context if hasattr(event, 'ai_context') else None
            if isinstance(ai_ctx, dict):
                ai_summary = ai_ctx.get('summary') or ai_ctx.get('reasoning')
                ai_rating = ai_ctx.get('signal_type')

        # Format priority string (fallback to result recommendation context)
        priority_str = priority_final or result.recommendation or "UNKNOWN"

        # Build formatted message
        lines = ["🚨 ALCHEMIK ALERT", ""]
        lines.append(f"Ticker: {symbol}")
        if event_type:
            lines.append(f"Event Type: {event_type}")
        if event_family:
            lines.append(f"Event Family: {event_family}")
        lines.append(f"Priority: {priority_str}")
        if quality_level:
            lines.append(f"Quality: {quality_level}")

        # AI Rating — informational only, NOT an investment recommendation
        if ai_rating:
            lines.append(f"AI Rating: {ai_rating}")

        lines.append(f"Score: {result.final_rating:.1f}")
        lines.append(f"Confidence: {result.confidence_level:.1f}%")

        if ai_summary:
            lines.append("")
            lines.append(f"AI Summary: {ai_summary}")

        formatted_msg = "\n".join(lines)

        return AlertMessage(
            alert_id=alert_id,
            symbol=symbol,
            market=market,
            event_type=event_type,
            event_family=event_family,
            priority_final=priority_final,
            quality_level=quality_level,
            is_composite=is_composite,
            composite_count=composite_count,
            recommendation=result.recommendation,
            ai_rating=ai_rating,
            final_score=result.final_rating / 100,
            confidence_level=result.confidence_level / 100,
            risk_level=None,
            ai_summary=ai_summary,
            created_at=datetime.now(),
            formatted_message=formatted_msg,
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