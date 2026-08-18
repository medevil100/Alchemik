from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from typing import Optional, List
from data.models.final_analysis_result import FinalAnalysisResult
from data.models.market_event import MarketEvent

TELEGRAM_MESSAGE_LIMIT = 4096


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

        # final_rating and confidence_level are domain values in [0.0, 1.0]
        # (decyzja właściciela Punkt 7). No scaling is applied here.
        final_score = result.final_rating
        confidence = result.confidence_level

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
        price_data = None
        volume_data = None
        technical_context = None
        timestamp_utc = None

        if event is not None:
            event_type = getattr(event, 'event_type', None)
            ef = getattr(event, 'event_family', None)
            event_family = getattr(ef, 'value', str(ef)) if ef is not None else None
            pf = getattr(event, 'priority_final', None)
            priority_final = getattr(pf, 'value', str(pf)) if pf is not None else None
            ql = getattr(event, 'quality_level', None)
            quality_level = getattr(ql, 'value', str(ql)) if ql is not None else None
            is_composite = bool(getattr(event, 'is_composite', False))
            composite_events = getattr(event, 'composite_events', None)
            composite_count = len(composite_events) if isinstance(composite_events, list) else 0
            market = getattr(event, 'market', None)
            price_data = getattr(event, 'price_data', None)
            volume_data = getattr(event, 'volume_data', None)
            technical_context = getattr(event, 'technical_context', None)
            timestamp_utc = getattr(event, 'timestamp_utc', None)

            # Extract AI summary from ai_context
            ai_ctx = getattr(event, 'ai_context', None)
            if isinstance(ai_ctx, dict):
                ai_summary = (
                    ai_ctx.get('summary')
                    or ai_ctx.get('reasoning')
                    or ai_ctx.get('justification')
                )
                ai_rating = ai_ctx.get('signal_type')

        # Format priority string (fallback to result recommendation context)
        priority_str = priority_final or result.recommendation or "UNKNOWN"

        # Build formatted message
        lines = ["🚨 ALCHEMIK ALERT", ""]
        lines.append(f"Ticker: {symbol}")

        if timestamp_utc is not None:
            try:
                data_time = timestamp_utc.isoformat()
            except AttributeError:
                data_time = str(timestamp_utc)
            lines.append(f"Data time: {data_time}")

        if price_data is not None and getattr(price_data, 'close', None) is not None:
            lines.append(f"Price: {price_data.close}")

        if volume_data is not None and getattr(volume_data, 'current_volume', None) is not None:
            lines.append(f"Volume: {volume_data.current_volume}")

        change_pct = getattr(price_data, 'change_pct', None) if price_data is not None else None
        if change_pct is not None:
            lines.append(f"Change vs baseline: {change_pct}%")

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

        lines.append(f"Score: {result.final_rating:.2f}")
        lines.append(f"Confidence: {result.confidence_level:.0%}")

        if technical_context:
            try:
                tech_str = json.dumps(
                    technical_context, ensure_ascii=False, default=str
                )
            except TypeError:
                tech_str = str(technical_context)
            lines.append(f"Technical: {tech_str}")

        if ai_summary:
            lines.append("")
            lines.append(f"AI Summary: {ai_summary}")

        lines.append("")
        lines.append(
            "Zastrzeżenie: wiadomość nie jest automatyczną rekomendacją BUY/SELL."
        )

        formatted_msg = _fit_telegram_limit("\n".join(lines))

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
            final_score=result.final_rating,
            confidence_level=result.confidence_level,
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


def _fit_telegram_limit(message: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    """Return a single message that fits Telegram's per-message limit."""
    if len(message) <= limit:
        return message
    return message[: limit - 1] + "…"