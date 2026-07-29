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
from engines.composer.engine import ComposerEngine
from engines.quality.engine import QualityEngine
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
from data.models.pipeline_decision import PipelineDecision
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
    # ------------------------------------------------------------------
    # FUNDAMENTAL (FundamentalEventDetector — 5 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.4
    # ------------------------------------------------------------------
    "PE_RATIO_CHANGE": (EventFamily.FUNDAMENTAL, "Wskaźniki finansowe", None, PriorityLevel.HIGH),
    "REVENUE_CHANGE": (EventFamily.FUNDAMENTAL, "Wskaźniki finansowe", None, PriorityLevel.HIGH),
    "NET_INCOME_CHANGE": (EventFamily.FUNDAMENTAL, "Wskaźniki finansowe", None, PriorityLevel.HIGH),
    "EARNINGS_RELEASE": (EventFamily.FUNDAMENTAL, "Wyniki finansowe", None, PriorityLevel.CRITICAL),
    "GUIDANCE_UPDATE": (EventFamily.FUNDAMENTAL, "Wyniki finansowe", None, PriorityLevel.CRITICAL),
    # ------------------------------------------------------------------
    # CORPORATE (CorporateEventDetector — 34 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.5
    # ------------------------------------------------------------------
    # Insider Trading
    "INSIDER_BUY": (EventFamily.CORPORATE, "Insider Trading", None, PriorityLevel.CRITICAL),
    "INSIDER_SELL": (EventFamily.CORPORATE, "Insider Trading", None, PriorityLevel.CRITICAL),
    "INSIDER_CLUSTER_BUY": (EventFamily.CORPORATE, "Insider Trading", None, PriorityLevel.HIGH),
    "INSIDER_CLUSTER_SELL": (EventFamily.CORPORATE, "Insider Trading", None, PriorityLevel.HIGH),
    # Zmiany akcjonariatu
    "SHAREHOLDER_INCREASE": (EventFamily.CORPORATE, "Zmiany akcjonariatu", None, PriorityLevel.CRITICAL),
    "SHAREHOLDER_DECREASE": (EventFamily.CORPORATE, "Zmiany akcjonariatu", None, PriorityLevel.CRITICAL),
    "SIGNIFICANT_HOLDER_CHANGE": (EventFamily.CORPORATE, "Zmiany akcjonariatu", None, PriorityLevel.HIGH),
    # Rekomendacje
    "ANALYST_UPGRADE": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    "ANALYST_DOWNGRADE": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    "PRICE_TARGET_INCREASE": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    "PRICE_TARGET_DECREASE": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    "NEW_COVERAGE": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    "COVERAGE_DROPPED": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    "RATING_CHANGE": (EventFamily.CORPORATE, "Rekomendacje", None, PriorityLevel.HIGH),
    # Ratingi
    "CREDIT_RATING_UPGRADE": (EventFamily.CORPORATE, "Ratingi", None, PriorityLevel.CRITICAL),
    "CREDIT_RATING_DOWNGRADE": (EventFamily.CORPORATE, "Ratingi", None, PriorityLevel.CRITICAL),
    "CREDIT_WATCH_POSITIVE": (EventFamily.CORPORATE, "Ratingi", None, PriorityLevel.HIGH),
    "CREDIT_WATCH_NEGATIVE": (EventFamily.CORPORATE, "Ratingi", None, PriorityLevel.HIGH),
    # Fuzje i przejęcia
    "MERGER_ANNOUNCEMENT": (EventFamily.CORPORATE, "Fuzje i przejęcia", None, PriorityLevel.CRITICAL),
    "ACQUISITION_ANNOUNCEMENT": (EventFamily.CORPORATE, "Fuzje i przejęcia", None, PriorityLevel.CRITICAL),
    "TAKEOVER_BID": (EventFamily.CORPORATE, "Fuzje i przejęcia", None, PriorityLevel.CRITICAL),
    "MERGER_COMPLETION": (EventFamily.CORPORATE, "Fuzje i przejęcia", None, PriorityLevel.CRITICAL),
    "ACQUISITION_COMPLETION": (EventFamily.CORPORATE, "Fuzje i przejęcia", None, PriorityLevel.CRITICAL),
    # Kontrakty
    "MAJOR_CONTRACT_WIN": (EventFamily.CORPORATE, "Kontrakty", None, PriorityLevel.CRITICAL),
    "MAJOR_CONTRACT_LOSS": (EventFamily.CORPORATE, "Kontrakty", None, PriorityLevel.CRITICAL),
    # Pozwy
    "LAWSUIT_FILED": (EventFamily.CORPORATE, "Pozwy", None, PriorityLevel.HIGH),
    "SETTLEMENT_ANNOUNCED": (EventFamily.CORPORATE, "Pozwy", None, PriorityLevel.MEDIUM),
    # Problemy prawne
    "REGULATORY_INVESTIGATION": (EventFamily.CORPORATE, "Problemy prawne", None, PriorityLevel.CRITICAL),
    # Upadłości
    "BANKRUPTCY_FILING": (EventFamily.CORPORATE, "Upadłości", None, PriorityLevel.CRITICAL),
    "RESTRUCTURING_PLAN": (EventFamily.CORPORATE, "Upadłości", None, PriorityLevel.HIGH),
    # Zmiany zarządu
    "CEO_CHANGE": (EventFamily.CORPORATE, "Zmiany zarządu", None, PriorityLevel.CRITICAL),
    "CFO_CHANGE": (EventFamily.CORPORATE, "Zmiany zarządu", None, PriorityLevel.HIGH),
    "BOARD_CHANGE": (EventFamily.CORPORATE, "Zmiany zarządu", None, PriorityLevel.MEDIUM),
    "MANAGEMENT_SHAKEUP": (EventFamily.CORPORATE, "Zmiany zarządu", None, PriorityLevel.MEDIUM),
    # ------------------------------------------------------------------
    # REGULATORY (RegulatoryEventDetector — 3 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.6
    # ------------------------------------------------------------------
    "ESPI_FILING": (EventFamily.REGULATORY, "ESPI", None, PriorityLevel.CRITICAL),
    "EBI_FILING": (EventFamily.REGULATORY, "EBI", None, PriorityLevel.CRITICAL),
    "FILING_DELAY": (EventFamily.REGULATORY, "ESPI", None, PriorityLevel.HIGH),
    # ------------------------------------------------------------------
    # MACRO (MacroEventDetector — 16 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.7
    # ------------------------------------------------------------------
    # Makroekonomia
    "GDP_BEAT": (EventFamily.MACRO, "Makroekonomia", None, PriorityLevel.HIGH),
    "GDP_MISS": (EventFamily.MACRO, "Makroekonomia", None, PriorityLevel.HIGH),
    "GDP_REVISION": (EventFamily.MACRO, "Makroekonomia", None, PriorityLevel.MEDIUM),
    # Stopy procentowe
    "INTEREST_RATE_HIKE": (EventFamily.MACRO, "Stopy procentowe", None, PriorityLevel.CRITICAL),
    "INTEREST_RATE_CUT": (EventFamily.MACRO, "Stopy procentowe", None, PriorityLevel.CRITICAL),
    "RATE_DECISION_SURPRISE": (EventFamily.MACRO, "Stopy procentowe", None, PriorityLevel.CRITICAL),
    # Inflacja
    "CPI_BEAT": (EventFamily.MACRO, "Inflacja", None, PriorityLevel.HIGH),
    "CPI_MISS": (EventFamily.MACRO, "Inflacja", None, PriorityLevel.HIGH),
    "PPI_SURGE": (EventFamily.MACRO, "Inflacja", None, PriorityLevel.HIGH),
    "INFLATION_TREND_CHANGE": (EventFamily.MACRO, "Inflacja", None, PriorityLevel.HIGH),
    # Waluty
    "CURRENCY_SURGE": (EventFamily.MACRO, "Waluty", None, PriorityLevel.HIGH),
    "CURRENCY_PLUMMET": (EventFamily.MACRO, "Waluty", None, PriorityLevel.HIGH),
    "CURRENCY_VOLATILITY_SPIKE": (EventFamily.MACRO, "Waluty", None, PriorityLevel.MEDIUM),
    # Surowce
    "COMMODITY_PRICE_SPIKE": (EventFamily.MACRO, "Surowce", None, PriorityLevel.HIGH),
    "COMMODITY_PRICE_DROP": (EventFamily.MACRO, "Surowce", None, PriorityLevel.HIGH),
    # Geopolityka
    "GEOPOLITICAL_ESCALATION": (EventFamily.MACRO, "Geopolityka", None, PriorityLevel.CRITICAL),
    # ------------------------------------------------------------------
    # ETF (ETFEventDetector — 4 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.8
    # ------------------------------------------------------------------
    "ETF_COMPOSITION_CHANGE": (EventFamily.ETF, "ETF", None, PriorityLevel.HIGH),
    "ETF_FLOW_SPIKE": (EventFamily.ETF, "ETF", None, PriorityLevel.HIGH),
    "ETF_PREMIUM_DISCOUNT": (EventFamily.ETF, "ETF", None, PriorityLevel.MEDIUM),
    "ETF_CLOSURE_ANNOUNCEMENT": (EventFamily.ETF, "ETF", None, PriorityLevel.CRITICAL),
    # ------------------------------------------------------------------
    # DERIVATIVES (DerivativesEventDetector — 9 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.9
    # ------------------------------------------------------------------
    # Opcje
    "UNUSUAL_OPTIONS_VOLUME": (EventFamily.DERIVATIVES, "Opcje", None, PriorityLevel.HIGH),
    "OPTIONS_PUT_CALL_RATIO": (EventFamily.DERIVATIVES, "Opcje", None, PriorityLevel.MEDIUM),
    "OPTIONS_VOLATILITY_SKEW": (EventFamily.DERIVATIVES, "Opcje", None, PriorityLevel.HIGH),
    # Short Interest
    "SHORT_INTEREST_SPIKE": (EventFamily.DERIVATIVES, "Short Interest", None, PriorityLevel.HIGH),
    "SHORT_INTEREST_SQUEEZE": (EventFamily.DERIVATIVES, "Short Interest", None, PriorityLevel.CRITICAL),
    # Dark Pool
    "DARK_POOL_PRINT": (EventFamily.DERIVATIVES, "Dark Pool", None, PriorityLevel.MEDIUM),
    "DARK_POOL_SPIKE": (EventFamily.DERIVATIVES, "Dark Pool", None, PriorityLevel.MEDIUM),
    # Nietypowe transakcje
    "UNUSUAL_BLOCK_TRADE": (EventFamily.DERIVATIVES, "Nietypowe transakcje", None, PriorityLevel.HIGH),
    "BLOCK_TRADE_CLUSTER": (EventFamily.DERIVATIVES, "Nietypowe transakcje", None, PriorityLevel.HIGH),
    # ------------------------------------------------------------------
    # SENTIMENT (SentimentNewsEventDetector — 11 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.10
    # ------------------------------------------------------------------
    # Media społecznościowe
    "SOCIAL_MEDIA_SPIKE": (EventFamily.SENTIMENT, "Media społecznościowe", None, PriorityLevel.HIGH),
    "SOCIAL_MEDIA_SENTIMENT_SHIFT": (EventFamily.SENTIMENT, "Media społecznościowe", None, PriorityLevel.HIGH),
    # Sentyment rynku
    "VIX_SPIKE": (EventFamily.SENTIMENT, "Sentyment rynku", None, PriorityLevel.CRITICAL),
    "VIX_COLLAPSE": (EventFamily.SENTIMENT, "Sentyment rynku", None, PriorityLevel.HIGH),
    # News
    "BREAKING_NEWS": (EventFamily.SENTIMENT, "News", None, PriorityLevel.CRITICAL),
    "ANALYST_REPORT": (EventFamily.SENTIMENT, "News", None, PriorityLevel.HIGH),
    "EXECUTIVE_INTERVIEW": (EventFamily.SENTIMENT, "News", None, PriorityLevel.MEDIUM),
    # Tavily
    "TAVILY_RESULT_SPIKE": (EventFamily.SENTIMENT, "Tavily", None, PriorityLevel.HIGH),
    "TAVILY_SENTIMENT_SHIFT": (EventFamily.SENTIMENT, "Tavily", None, PriorityLevel.HIGH),
    # Pozostałe
    "NEWS_SENTIMENT_SHIFT": (EventFamily.SENTIMENT, "Sentyment rynku", None, PriorityLevel.HIGH),
    "EARNINGS_WHISPER": (EventFamily.SENTIMENT, "News", None, PriorityLevel.HIGH),
    # ------------------------------------------------------------------
    # SYSTEM (SystemEventDetector — 12 event types)
    # Source: docs/Hierarchia_Zdarzen_Rynkowych.md §4.11
    # ------------------------------------------------------------------
    # Alerty własne
    "COMPOSITE_EVENT": (EventFamily.SYSTEM, "Alerty własne", None, PriorityLevel.CRITICAL),
    "INSTRUMENT_STATE_CHANGE": (EventFamily.SYSTEM, "Alerty własne", None, PriorityLevel.CRITICAL),
    "RECURRING_PATTERN": (EventFamily.SYSTEM, "Alerty własne", None, PriorityLevel.HIGH),
    # Międzyinstrumentowe
    "CROSS_INSTRUMENT_CORRELATION": (EventFamily.SYSTEM, "Międzyinstrumentowe", None, PriorityLevel.MEDIUM),
    # Sektor
    "SECTOR_ROTATION": (EventFamily.SYSTEM, "Sektor", None, PriorityLevel.HIGH),
    # Sezonowe
    "SEASONAL_PATTERN": (EventFamily.SYSTEM, "Sezonowe", None, PriorityLevel.LOW),
    # Korelacje
    "CORRELATION_BREAKDOWN": (EventFamily.SYSTEM, "Korelacje", None, PriorityLevel.HIGH),
    # Pozostałe alerty własne
    "VOLUME_ANOMALY_CLUSTER": (EventFamily.SYSTEM, "Alerty własne", None, PriorityLevel.MEDIUM),
    "PRICE_VOLUME_DIVERGENCE": (EventFamily.SYSTEM, "Międzyinstrumentowe", None, PriorityLevel.MEDIUM),
    "MULTIPLE_DETECTOR_CONFIRMATION": (EventFamily.SYSTEM, "Alerty własne", None, PriorityLevel.HIGH),
    # Sektor (pozostałe)
    "ADVANCED_DECLINE_RATIO": (EventFamily.SYSTEM, "Sektor", None, PriorityLevel.MEDIUM),
    "MARKET_BREADTH_CHANGE": (EventFamily.SYSTEM, "Sektor", None, PriorityLevel.MEDIUM),
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
                 detector_registry=None,
                 composer_engine=None,
                 quality_engine=None,
                 tavily_adapter=None):
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
        self._composer_engine = composer_engine or ComposerEngine()
        self._quality_engine = quality_engine or QualityEngine()
        self._tavily_adapter = tavily_adapter

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

        # Step 2a: Compose — merge related MarketEvents into Composite Events
        # (ETAP 7.3 / KROK 2A)
        if market_events:
            market_events = self._composer_engine.compose(market_events)

        # Step 2b: Quality Assessment — assign quality_level to each event
        # (ETAP 7.2 / KROK 2B)
        if market_events:
            for i, ev in enumerate(market_events):
                market_events[i] = self._quality_engine.assess(ev)

        # Step 2c: Pipeline Decision — decide which stages to run per event
        # (ETAP 7.4 / KROK 2C)
        pipeline_decisions: List[PipelineDecision] = []
        if market_events:
            decisions_map = {}  # event_id → PipelineDecision (used in AI loop)
            for ev in market_events:
                decision = self.ai_engine.decide_pipeline(ev)
                pipeline_decisions.append(decision)
                decisions_map[ev.event_id] = decision
            run_news = any(d.run_news for d in pipeline_decisions)
            run_ai_for_any = any(d.run_ai for d in pipeline_decisions)
        else:
            run_news = False
            run_ai_for_any = False
            decisions_map = {}

        # Pass events to caller via the optional output list
        if events_out is not None and market_events:
            events_out.extend(market_events)

        # Step 3: News Engine (conditional on pipeline decision)
        if run_news:
            news_result = self.news_engine.process([symbol])
        else:
            news_result = []

        # Step 3b: Tavily Search (conditional on pipeline decision)
        # Runs BEFORE AI so that tavily_context is available during AI analysis.
        if market_events and self._tavily_adapter is not None:
            for ev in market_events:
                ev_decision = decisions_map.get(ev.event_id)
                if ev_decision is None or not ev_decision.run_tavily:
                    continue

                try:
                    ctx = self._tavily_adapter.search_for_event(ev)
                    ev.tavily_context = {
                        "query": ctx.query,
                        "results_count": ctx.results_count,
                        "top_results": [
                            {
                                "title": r.title,
                                "url": r.url,
                                "content": r.content,
                                "published_date": (
                                    r.published_date.isoformat()
                                    if r.published_date else None
                                ),
                                "score": r.score,
                            }
                            for r in ctx.top_results
                        ],
                        "sentiment": ctx.sentiment,
                    }
                except Exception as exc:
                    logger.warning(
                        "Tavily search failed for %s (%s): %s",
                        symbol,
                        ev.event_type,
                        exc,
                    )
        elif market_events and self._tavily_adapter is None:
            any_tavily = any(d.run_tavily for d in pipeline_decisions)
            if any_tavily:
                logger.warning(
                    "Tavily requested for %s but no TavilyEventAdapter provided",
                    symbol,
                )

        # Step 4: AI Engine (conditional on pipeline decision)
        if market_events and run_ai_for_any:
            ai_results: List = []
            for ev in market_events:
                ev_decision = decisions_map.get(ev.event_id)
                if ev_decision is None or not ev_decision.run_ai:
                    continue  # skip AI for this event

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
                # Enrich ai_context with Tavily data if available
                if ev.tavily_context is not None:
                    ev.ai_context["tavily_context"] = ev.tavily_context

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