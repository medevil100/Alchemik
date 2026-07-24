import logging
from typing import List, Optional

from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.ai import DecisionEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.hunter import HunterEngine
from engines.analyst import AnalystEngine
from engines.price_detector import PriceDetector
from engines.volume_detector import VolumeDetector
from engines.detectors import (
    BaseDetector,
    CorporateEventDetector,
    DerivativesEventDetector,
    DetectionContext,
    DetectionResult,
    DetectorOrchestrator,
    DetectorRegistry,
    ETFEventDetector,
    FundamentalEventDetector,
    MacroEventDetector,
    RegulatoryEventDetector,
    SentimentNewsEventDetector,
    SystemEventDetector,
    TechnicalEventDetector,
)
from data.models import FinalAnalysisResult, MarketData, MarketEvent, InstrumentType
from data.models.analysis_result import AnalysisResult
from data.models.event_enums import EventFamily, EventOwner, PriorityLevel
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Event catalogue — maps event_type → classification metadata.
#
# Source of truth: docs/Hierarchia_Zdarzen_Rynkowych.md §4 and
# docs/Katalog_Zdarzen_Rynkowych.md.
#
# Each entry:
#   (EventFamily, event_category, event_subcategory | None, PriorityLevel)
#
# The catalogue is used by _result_to_market_event() to convert
# DetectionResult into MarketEvent (ETAP_6_ARCHITEKTURA.md §11.8).
# ------------------------------------------------------------------

_CATALOGUE: dict[str, tuple[EventFamily, str, Optional[str], PriorityLevel]] = {
    # ------------------------------------------------------------------
    # TECHNICAL — Zmienność (Volatility)
    # ------------------------------------------------------------------
    "VOLATILITY_SPIKE": (EventFamily.TECHNICAL, "Zmienność", "Odchylenie ATR", PriorityLevel.CRITICAL),
    "VOLATILITY_CONTRACTION": (EventFamily.TECHNICAL, "Zmienność", "Odchylenie ATR", PriorityLevel.MEDIUM),
    "BB_EXPANSION": (EventFamily.TECHNICAL, "Zmienność", "Bollinger Bands", PriorityLevel.HIGH),
    "BB_SQUEEZE": (EventFamily.TECHNICAL, "Zmienność", "Bollinger Bands", PriorityLevel.MEDIUM),
    # ------------------------------------------------------------------
    # TECHNICAL — Wybicia (Breakouts)
    # ------------------------------------------------------------------
    "RESISTANCE_BREAKOUT": (EventFamily.TECHNICAL, "Wybicia", "Poziomy S/R", PriorityLevel.HIGH),
    "SUPPORT_BREAKDOWN": (EventFamily.TECHNICAL, "Wybicia", "Poziomy S/R", PriorityLevel.HIGH),
    # ------------------------------------------------------------------
    # TECHNICAL — Formacje świecowe (Candlestick patterns)
    # ------------------------------------------------------------------
    "HAMMER_HANGING_MAN": (EventFamily.TECHNICAL, "Formacje świecowe", "Jednoświecowe", PriorityLevel.MEDIUM),
    "SHOOTING_STAR_INV_HAMMER": (EventFamily.TECHNICAL, "Formacje świecowe", "Jednoświecowe", PriorityLevel.MEDIUM),
    "BULLISH_ENGULFING": (EventFamily.TECHNICAL, "Formacje świecowe", "Wieloświecowe", PriorityLevel.HIGH),
    "BEARISH_ENGULFING": (EventFamily.TECHNICAL, "Formacje świecowe", "Wieloświecowe", PriorityLevel.HIGH),
    "DOJI": (EventFamily.TECHNICAL, "Formacje świecowe", "Jednoświecowe", PriorityLevel.LOW),
    "MORNING_EVENING_STAR": (EventFamily.TECHNICAL, "Formacje świecowe", "Wieloświecowe", PriorityLevel.HIGH),
    "THREE_WHITE_SOLDIERS": (EventFamily.TECHNICAL, "Formacje świecowe", "Wieloświecowe", PriorityLevel.HIGH),
    "THREE_BLACK_CROWS": (EventFamily.TECHNICAL, "Formacje świecowe", "Wieloświecowe", PriorityLevel.HIGH),
    "MARUBOZU": (EventFamily.TECHNICAL, "Formacje świecowe", "Jednoświecowe", PriorityLevel.MEDIUM),
    "HARAMI": (EventFamily.TECHNICAL, "Formacje świecowe", "Wieloświecowe", PriorityLevel.LOW),
    # ------------------------------------------------------------------
    # TECHNICAL — Trend
    # ------------------------------------------------------------------
    "MA_CROSSOVER": (EventFamily.TECHNICAL, "Trend", "Średnie kroczące", PriorityLevel.HIGH),
    "MA_SLOPE_CHANGE": (EventFamily.TECHNICAL, "Trend", "Średnie kroczące", PriorityLevel.MEDIUM),
    "PRICE_VS_MA": (EventFamily.TECHNICAL, "Trend", "Średnie kroczące", PriorityLevel.MEDIUM),
    "CONSECUTIVE_CANDLES": (EventFamily.TECHNICAL, "Trend", "Struktura trendu", PriorityLevel.MEDIUM),
    "TREND_STRUCTURE_CHANGE": (EventFamily.TECHNICAL, "Trend", "Struktura trendu", PriorityLevel.HIGH),
    # ------------------------------------------------------------------
    # TECHNICAL — Momentum
    # ------------------------------------------------------------------
    "RSI_OVERBOUGHT": (EventFamily.TECHNICAL, "Momentum", "RSI", PriorityLevel.MEDIUM),
    "RSI_OVERSOLD": (EventFamily.TECHNICAL, "Momentum", "RSI", PriorityLevel.MEDIUM),
    "RSI_DIVERGENCE": (EventFamily.TECHNICAL, "Momentum", "RSI", PriorityLevel.HIGH),
    "MACD_LINE_CROSSOVER": (EventFamily.TECHNICAL, "Momentum", "MACD", PriorityLevel.HIGH),
    "MACD_ZERO_CROSS": (EventFamily.TECHNICAL, "Momentum", "MACD", PriorityLevel.MEDIUM),
    # ------------------------------------------------------------------
    # TECHNICAL — Wskaźniki techniczne (Technical indicators)
    # ------------------------------------------------------------------
    "OBV_DIVERGENCE": (EventFamily.TECHNICAL, "Wskaźniki techniczne", "OBV", PriorityLevel.MEDIUM),
    "ATR_EXPANSION": (EventFamily.TECHNICAL, "Wskaźniki techniczne", "ATR", PriorityLevel.MEDIUM),
    "FIBONACCI_HIT": (EventFamily.TECHNICAL, "Wskaźniki techniczne", "Fibonacci", PriorityLevel.MEDIUM),
}


def _lookup_catalogue(event_type: str) -> tuple[EventFamily, str, Optional[str], PriorityLevel]:
    """Return catalogue entry for *event_type* or a safe default if missing."""
    if event_type in _CATALOGUE:
        return _CATALOGUE[event_type]
    return (EventFamily.SYSTEM, "System", None, PriorityLevel.LOW)


def _result_to_market_event(
    result: DetectionResult,
    ticker: str,
    market: str,
    instrument_type: InstrumentType,
    detector_name: str,
    detector_family: EventFamily,
) -> MarketEvent:
    """Convert a DetectionResult to a fully-formed MarketEvent.

    Implements the conversion protocol from ETAP_6_ARCHITEKTURA.md §11.8:
      1. Lookup classification from catalogue using event_type.
      2. Create MarketEvent via create_new().
      3. Call set_detection() with catalogue values.
    """
    event_family, event_category, event_subcategory, priority_raw = _lookup_catalogue(
        result.event_type
    )
    # Override family with the detector's declared family
    event_family = detector_family

    confidence = max(0.0, min(1.0, result.confidence_level))

    event = MarketEvent.create_new(
        ticker=ticker,
        market=market,
        instrument_type=instrument_type,
        timestamp_utc=datetime.now(timezone.utc),
    )
    event.set_detection(
        event_family=event_family,
        event_category=event_category,
        event_type=result.event_type,
        priority_raw=priority_raw,
        confidence_level=confidence,
        detection_source=f"{detector_name} (DetectorOrchestrator)",
        event_owner=EventOwner.TechnicalEngine,
        event_subcategory=event_subcategory,
        price_data=result.price_data,
        volume_data=result.volume_data,
    )
    return event


def _build_default_registry() -> DetectorRegistry:
    """Build a DetectorRegistry with all available BaseDetector-based detectors."""
    registry = DetectorRegistry()
    registry.register(TechnicalEventDetector())
    registry.register(FundamentalEventDetector())
    registry.register(CorporateEventDetector())
    registry.register(RegulatoryEventDetector())
    registry.register(MacroEventDetector())
    registry.register(ETFEventDetector())
    registry.register(DerivativesEventDetector())
    registry.register(SentimentNewsEventDetector())
    registry.register(SystemEventDetector())
    return registry


class MasterEngine:
    def __init__(self, 
                 technical_engine=None, 
                 news_engine=None, 
                 ai_engine=None, 
                 ranking_engine=None, 
                 risk_engine=None, 
                 hunter_engine=None, 
                 analyst_engine=None,
                 price_detector=None,
                 volume_detector=None,
                 detector_registry=None):
        self.technical_engine = technical_engine or TechnicalEngine()
        self.news_engine = news_engine or NewsPipeline()
        self.ai_engine = ai_engine or DecisionEngine()
        self.ranking_engine = ranking_engine or RankingEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.hunter_engine = hunter_engine or HunterEngine()
        self.analyst_engine = analyst_engine or AnalystEngine()
        self.price_detector = price_detector or PriceDetector()
        self.volume_detector = volume_detector or VolumeDetector()
        self.detector_registry = detector_registry or _build_default_registry()
        self._orchestrator = DetectorOrchestrator(self.detector_registry)

    def _run_base_detectors(
        self,
        ticker: str,
        market: str,
        instrument_type: InstrumentType,
        ohlcv_data: List[MarketData],
    ) -> List[MarketEvent]:
        """Run all BaseDetector detectors and convert results to MarketEvents.

        Creates a DetectionContext, runs all registered detectors through
        DetectorOrchestrator.run_all(), and converts each DetectionResult
        to a MarketEvent using the event catalogue.

        Returns:
            list[MarketEvent] — events from BaseDetector-based detectors.
            Empty list if no events detected or data insufficient.
        """
        if not ohlcv_data:
            return []

        try:
            context = DetectionContext(
                ticker=ticker,
                market=market,
                instrument_type=instrument_type,
                ohlcv_data=tuple(ohlcv_data),
            )
            results: tuple[DetectionResult, ...] = self._orchestrator.run_all(context)
        except (TypeError, ValueError) as exc:
            logger.debug(
                "Skipping BaseDetector orchestration for %s: %s", ticker, exc
            )
            return []

        events: List[MarketEvent] = []
        if not results:
            return events

        # Map detector_id → EventFamily for catalogue lookup
        # Each BaseDetector corresponds to exactly one EventFamily.
        _DETECTOR_FAMILY: dict[str, EventFamily] = {
            "technical": EventFamily.TECHNICAL,
            "fundamental": EventFamily.FUNDAMENTAL,
            "corporate": EventFamily.CORPORATE,
            "regulatory": EventFamily.REGULATORY,
            "macro": EventFamily.MACRO,
            "etf": EventFamily.ETF,
            "derivatives": EventFamily.DERIVATIVES,
            "sentiment": EventFamily.SENTIMENT,
            "system": EventFamily.SYSTEM,
        }

        for result in results:
            # Determine which detector produced this result
            # We look it up via registry: find the first detector that can handle this event_type
            matching = self.detector_registry.get_for_event_type(result.event_type)
            if not matching:
                logger.debug("No detector registered for event_type %s", result.event_type)
                continue
            detector = matching[0]
            family = _DETECTOR_FAMILY.get(detector.detector_id, EventFamily.SYSTEM)

            try:
                event = _result_to_market_event(
                    result=result,
                    ticker=ticker,
                    market=market,
                    instrument_type=instrument_type,
                    detector_name=detector.name,
                    detector_family=family,
                )
                events.append(event)
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "Failed to convert DetectionResult(%s) to MarketEvent: %s",
                    result.event_type, exc,
                )

        if events:
            logger.info(
                "BaseDetectors produced %d MarketEvent(s) for %s: %s",
                len(events), ticker,
                [e.event_type for e in events],
            )

        return events

    def run_detectors(
        self,
        ticker: str,
        market: str,
        instrument_type: InstrumentType,
        ohlcv_data: List[MarketData],
    ) -> List[MarketEvent]:
        """Run all detectors and return combined MarketEvent list.

        Combines:
          - Frozen PriceDetector / VolumeDetector results (existing)
          - BaseDetector-based detector results (new, via _run_base_detectors)

        Returns:
            Combined list of MarketEvent objects from all detectors.
        """
        events: List[MarketEvent] = []

        # Run frozen PriceDetector
        price_events = self.price_detector.detect(
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            ohlcv_data=ohlcv_data,
        )
        events.extend(price_events)

        # Run frozen VolumeDetector
        volume_events = self.volume_detector.detect(
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            ohlcv_data=ohlcv_data,
        )
        events.extend(volume_events)

        # Run BaseDetector-based detectors via DetectorOrchestrator
        base_events = self._run_base_detectors(
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            ohlcv_data=ohlcv_data,
        )
        events.extend(base_events)

        return events

    def run_analysis(
        self,
        symbol: str,
        market: str = "UNKNOWN",
        instrument_type: InstrumentType = InstrumentType.STOCK_USA,
        events_out: Optional[List[MarketEvent]] = None,
        ohlcv_data: Optional[List[MarketData]] = None,
    ) -> FinalAnalysisResult:
        """
        Execute the full analysis pipeline for a single instrument.

        Detectors (PriceDetector, VolumeDetector, BaseDetector-based) are
        run EXACTLY ONCE inside this method.
        """
        # Validate symbol
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Invalid symbol. Symbol must be a non-empty string.")

        # Step 1: Technical Engine
        if ohlcv_data:
            technical_result = self.technical_engine.analyze(ohlcv_data)
        else:
            technical_result = AnalysisResult(
                company=None,
                market_data=[],
                news=[],
                signals=[],
                generated_at=datetime.now()
            )
            technical_result.indicators = {}

        # Step 2: Run detectors on market data
        market_events: List[MarketEvent] = []
        if hasattr(technical_result, 'market_data') and technical_result.market_data:
            market_events = self.run_detectors(
                ticker=symbol,
                market=market,
                instrument_type=instrument_type,
                ohlcv_data=technical_result.market_data,
            )

        # Pass events to caller via the optional output list
        if events_out is not None and market_events:
            events_out.extend(market_events)

        # Step 3: News Engine
        news_result = self.news_engine.process([symbol])

        # Step 4: AI Engine
        if market_events:
            ai_results: List = []
            for ev in market_events:
                if hasattr(technical_result, 'indicators') and technical_result.indicators:
                    ev.technical_context = technical_result.indicators

                ai_signal = self.ai_engine.process_event(ev)
                ai_results.append(ai_signal)

                ev.ai_context = {
                    "signal_type": ai_signal.signal_type,
                    "confidence": ai_signal.confidence,
                    "reasoning": ai_signal.reasoning,
                    "generated_at": ai_signal.generated_at.isoformat(),
                }

            ai_result = ai_results[0] if ai_results else self.ai_engine.process_data({
                "symbol": symbol, "technical": technical_result, "news": news_result
            })
        else:
            ai_result = self.ai_engine.process_data({
                "symbol": symbol, "technical": technical_result, "news": news_result
            })

        # Step 5: Ranking Engine
        ranking_result = self.ranking_engine.calculate_ranking([ai_result])

        # Step 6: Risk Engine
        risk_result = self.risk_engine.assess_risk(ai_result, ranking_result)

        # Step 7: Hunter Engine
        hunter_result = self.hunter_engine.scan([{"symbol": symbol, "risk": risk_result, "ranking": ranking_result}])

        # Step 8: Analyst Engine
        analyst_result = self.analyst_engine.generate_analysis(hunter_result)

        return FinalAnalysisResult(
            symbol=symbol,
            final_rating=analyst_result.final_rating,
            confidence_level=analyst_result.confidence_level,
            recommendation=analyst_result.recommendation,
            positive_factors=analyst_result.positive_factors,
            risk_factors=analyst_result.risk_factors,
            warnings=analyst_result.warnings,
            summary=analyst_result.summary,
            generated_at=datetime.now()
        )