import logging
from typing import List, Optional

from engines.technical import TechnicalEngine
from application.cycle_trace import SUCCESS as _TRACE_SUCCESS
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
from config.signal_timing import lookup_signal_timing
from data.models import FinalAnalysisResult, MarketData, MarketEvent, InstrumentType, AISignal
from data.models.company_info import CompanyInfo
from data.models.hunter_result import HunterResult
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
        event_type=result.event_type,
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
                 tavily_adapter=None,
                 openai_provider=None):
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
        self.openai_provider = openai_provider

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

    # ------------------------------------------------------------------
    # AI payload construction (Punkt 4 — real AI boundary)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_ai_payload(
        symbol: str,
        market: str,
        instrument_type: InstrumentType,
        technical_result: AnalysisResult,
        market_events: List[MarketEvent],
        decisions_map: dict,
    ) -> dict:
        """Build the redacted, instrument-scoped payload for GPT-4o.

        ONLY data belonging to this instrument is included. No secrets,
        cookies, crumb, API keys, foreign-symbol data, or raw exceptions.

        Returns a JSON-serialisable dict with at minimum: symbol, current
        price, volume (preserving zero), data timestamp, baseline, change vs
        baseline, deterministic history summary, technical indicators,
        detected events (with quality + pipeline decision), Tavily context,
        and data-completeness status.
        """
        market_data = list(getattr(technical_result, "market_data", []) or [])

        current_price = None
        current_volume = None
        data_timestamp = None
        baseline = None
        change_vs_baseline = None

        if market_data:
            latest = market_data[-1]
            current_price = latest.close
            current_volume = latest.volume
            data_timestamp = latest.timestamp.isoformat()
            baseline = market_data[0].close
            if baseline is not None and baseline != 0:
                change_vs_baseline = round(
                    (current_price - baseline) / baseline * 100.0, 4
                )

        history = [
            {
                "timestamp": m.timestamp.isoformat(),
                "open": m.open,
                "high": m.high,
                "low": m.low,
                "close": m.close,
                "volume": m.volume,
            }
            for m in market_data
        ]

        technical_indicators = getattr(technical_result, "indicators", {}) or {}

        has_complete_ohlcv = all(
            m.open is not None
            and m.high is not None
            and m.low is not None
            and m.close is not None
            for m in market_data
        )
        data_completeness = "COMPLETE" if has_complete_ohlcv else "PARTIAL"

        events_out = []
        for ev in market_events:
            decision = decisions_map.get(ev.event_id)
            events_out.append({
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "event_category": ev.event_category,
                "event_subcategory": ev.event_subcategory,
                "quality_level": ev.quality_level.value,
                "priority_raw": ev.priority_raw.value,
                "priority_final": ev.priority_final.value,
                "confidence_level": ev.confidence_level,
                "signal_timing": ev.signal_timing.value,
                "pipeline_decision": (
                    {
                        "run_news": decision.run_news,
                        "run_tavily": decision.run_tavily,
                        "run_ai": decision.run_ai,
                        "reason": decision.reason,
                    }
                    if decision is not None
                    else None
                ),
                "tavily_context": ev.tavily_context,
                "price_data": ev.price_data.to_dict() if ev.price_data else None,
                "volume_data": ev.volume_data.to_dict() if ev.volume_data else None,
            })

        return {
            "symbol": symbol,
            "market": market,
            "instrument_type": instrument_type.value,
            "current_price": current_price,
            "volume": current_volume,
            "data_timestamp": data_timestamp,
            "baseline_close": baseline,
            "change_vs_baseline_pct": change_vs_baseline,
            "history": history,
            "technical_indicators": technical_indicators,
            "detected_events": events_out,
            "data_completeness": data_completeness,
        }

    # ------------------------------------------------------------------
    # AI result conversion (Punkt 4 — real AI boundary)
    # ------------------------------------------------------------------

    @staticmethod
    def _provider_result_to_aisignal(provider_result) -> AISignal:
        """Convert a validated provider result to an ``AISignal``.

        ``confidence`` comes from the real model response, never from the
        ``DecisionEngine`` placeholder. A refusal or a missing structured
        output is preserved explicitly with ``confidence=0.0`` and a
        non-``combined_analysis`` signal type so it is never presented as
        a successful model output.
        """
        if provider_result is None:
            return AISignal(
                signal_type="ai_error",
                confidence=0.0,
                generated_at=datetime.now(timezone.utc),
                reasoning="AI provider returned no result",
            )

        if getattr(provider_result, "refusal", None) is not None:
            return AISignal(
                signal_type="refusal",
                confidence=0.0,
                generated_at=datetime.now(timezone.utc),
                reasoning=provider_result.refusal,
            )

        result = getattr(provider_result, "result", None)
        if result is None:
            return AISignal(
                signal_type="ai_error",
                confidence=0.0,
                generated_at=datetime.now(timezone.utc),
                reasoning="AI provider returned no structured output",
            )

        parts = []
        if result.facts:
            parts.append("Fakty: " + " | ".join(result.facts))
        if result.hypotheses:
            parts.append("Hipotezy: " + " | ".join(result.hypotheses))
        if result.alternatives:
            parts.append("Alternatywy: " + " | ".join(result.alternatives))
        if result.risks:
            parts.append("Ryzyka: " + " | ".join(result.risks))
        if result.data_limitations:
            parts.append("Ograniczenia: " + " | ".join(result.data_limitations))
        if result.justification:
            parts.append("Uzasadnienie: " + result.justification)

        return AISignal(
            signal_type="combined_analysis",
            confidence=result.confidence,
            generated_at=datetime.now(timezone.utc),
            reasoning=" ".join(parts),
        )

    def run_analysis(
        self,
        symbol: str,
        market: str = "UNKNOWN",
        instrument_type: InstrumentType = InstrumentType.STOCK_USA,
        events_out: Optional[List[MarketEvent]] = None,
        ohlcv_data: Optional[List[MarketData]] = None,
        trace=None,
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
        # TechnicalEngine.analyze() raises ValueError when the supplied history
        # is too short for its indicators (SMA(20), RSI(14), EMA(26), MACD
        # signal EMA(9)). That error must propagate to the caller as a
        # per-instrument failure rather than being converted into a
        # fake-looking empty AnalysisResult.
        if trace is not None:
            trace.stage_start("technical")
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

        if trace is not None:
            indicators_count = len(getattr(technical_result, "indicators", {}) or {})
            trace.stage_end("technical", _TRACE_SUCCESS, output_count=indicators_count)
            trace.instrument_update(
                symbol,
                technical_status=_TRACE_SUCCESS,
                indicators_count=indicators_count,
            )

        # Step 2: Run detectors on market data
        market_events: List[MarketEvent] = []
        if hasattr(technical_result, 'market_data') and technical_result.market_data:
            market_events = self.run_detectors(
                ticker=symbol,
                market=market,
                instrument_type=instrument_type,
                ohlcv_data=technical_result.market_data,
            )

        if trace is not None:
            trace.instrument_update(
                symbol,
                events_count=len(market_events),
                hunter_status=_TRACE_SUCCESS,
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
        # NewsPipeline.process() expects List[NewsItem]; there is no
        # NewsItem source wired into MasterEngine at this stage, so pass an
        # empty list instead of a list of symbol strings.
        if trace is not None:
            trace.stage_start("news")
        if run_news:
            news_result = self.news_engine.process([])
        else:
            news_result = []
        if trace is not None:
            trace.stage_end(
                "news",
                _TRACE_SUCCESS if news_result else "EXECUTED_EMPTY",
                input_count=1 if run_news else 0,
                output_count=len(news_result) if news_result else 0,
                reason=(
                    "NewsPipeline executed with empty NewsItem list"
                    if run_news and not news_result else None
                ),
            )

        # Step 3b: Tavily Search (conditional on pipeline decision)
        # Runs BEFORE AI so that tavily_context is available during AI analysis.
        if trace is not None:
            trace.stage_start("tavily")
        tavily_attempted = 0
        tavily_success = 0
        if market_events and self._tavily_adapter is not None:
            for ev in market_events:
                ev_decision = decisions_map.get(ev.event_id)
                if ev_decision is None or not ev_decision.run_tavily:
                    continue

                tavily_attempted += 1
                try:
                    ctx = self._tavily_adapter.search_for_event(ev)
                    tavily_success += 1
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

        if trace is not None:
            trace.stage_end(
                "tavily",
                _TRACE_SUCCESS if tavily_success else "EXECUTED_EMPTY",
                input_count=tavily_attempted,
                output_count=tavily_success,
            )
            if tavily_attempted:
                trace.bump_external("tavily_attempts", tavily_attempted)
            trace.instrument_update(
                symbol,
                tavily_attempted=tavily_attempted,
                tavily_sent=tavily_attempted,
                tavily_success=tavily_success,
            )

        # Step 4: AI Engine (conditional on pipeline decision)
        if trace is not None:
            trace.stage_start("ai")
        # When a real OpenAI provider is wired in, qualified events trigger
        # exactly one provider call per instrument. Its validated output
        # becomes the AISignal with real model confidence; provider metadata
        # (response id / request id) is retained for provenance. When no
        # provider is configured, the DecisionEngine placeholder is kept for
        # offline/backward-compatible runs.
        ai_provider_metadata = {}
        ai_attempted = 1 if (market_events and run_ai_for_any) else 0
        ai_sent = 1 if (ai_attempted and self.openai_provider is not None) else 0
        ai_validated = 0
        ai_refusal = 0
        ai_signal_created = False

        if trace is not None and ai_sent:
            trace.bump_external("openai_attempts", 1)

        if market_events and run_ai_for_any and self.openai_provider is not None:
            for ev in market_events:
                if hasattr(technical_result, 'indicators') and technical_result.indicators:
                    ev.technical_context = technical_result.indicators

            payload = self._build_ai_payload(
                symbol=symbol,
                market=market,
                instrument_type=instrument_type,
                technical_result=technical_result,
                market_events=market_events,
                decisions_map=decisions_map,
            )

            try:
                provider_result = self.openai_provider.analyze(payload)
                ai_result = self._provider_result_to_aisignal(provider_result)
                ai_provider_metadata = {
                    "response_id": getattr(provider_result, "response_id", ""),
                    "request_id": getattr(provider_result, "request_id", None),
                    "refusal": getattr(provider_result, "refusal", None),
                }
            except Exception as exc:  # noqa: BLE001 — provider boundary
                logger.warning("OpenAI provider failed for %s: %s", symbol, exc)
                ai_result = AISignal(
                    signal_type="ai_error",
                    confidence=0.0,
                    generated_at=datetime.now(timezone.utc),
                    reasoning="AI provider error",
                )
                ai_provider_metadata = {"error": "provider_error"}
        elif market_events and run_ai_for_any:
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

        # Attach provider metadata to the first qualified event for provenance
        # (no secrets; only provider ids and the model-declared confidence).
        if ai_provider_metadata and market_events:
            for ev in market_events:
                decision = decisions_map.get(ev.event_id)
                if decision is not None and decision.run_ai:
                    ev.ai_context = dict(ai_provider_metadata)
                    ev.ai_context["confidence"] = ai_result.confidence
                    ev.ai_context["signal_type"] = ai_result.signal_type
                    ev.ai_context["reasoning"] = ai_result.reasoning
                    if ev.tavily_context is not None:
                        ev.ai_context["tavily_context"] = ev.tavily_context
                    break

        if ai_result is not None:
            signal_type = getattr(ai_result, "signal_type", None)
            if signal_type == "combined_analysis":
                ai_validated = 1
                ai_signal_created = True
            elif signal_type == "refusal":
                ai_refusal = 1

        if trace is not None:
            trace.stage_end(
                "ai",
                _TRACE_SUCCESS if ai_signal_created else (
                    "EXECUTED_EMPTY" if not ai_attempted else _TRACE_SUCCESS
                ),
                input_count=ai_sent,
                output_count=ai_validated,
            )
            trace.instrument_update(
                symbol,
                ai_attempted=ai_attempted,
                ai_sent=ai_sent,
                ai_validated=ai_validated,
                ai_refusal=ai_refusal,
                ai_signal_created=bool(ai_signal_created),
            )

        # Build a complete AnalysisResult for RankingEngine and RiskEngine.
        # technical_result carries market_data and (dynamically) indicators;
        # company is filled from the symbol/metadata available in run_analysis();
        # AISignal is appended to signals so that RiskEngine has access.
        analysis_result = technical_result
        if analysis_result.company is None:
            analysis_result.company = CompanyInfo(
                name=symbol,
                symbol=symbol,
            )
        analysis_result.signals.append(ai_result)

        # Step 5: Ranking Engine
        if trace is not None:
            trace.stage_start("ranking")
        ranking_result = self.ranking_engine.calculate_ranking([analysis_result])
        if trace is not None:
            trace.stage_end("ranking", _TRACE_SUCCESS, output_count=len(ranking_result.results))

        # Step 6: Risk Engine
        if trace is not None:
            trace.stage_start("risk")
        risk_result = self.risk_engine.assess_risk(analysis_result, ranking_result)
        if trace is not None:
            trace.stage_end("risk", _TRACE_SUCCESS, output_count=1)

        # Step 7: Hunter Engine
        # Map to HunterEngine's expected dict keys: instrument_id, ranking_score,
        # risk_score, confidence (not symbol/risk/ranking objects).
        hunter_scan = self.hunter_engine.scan([
            {
                "instrument_id": symbol,
                "ranking_score": ranking_result.results[0].score if ranking_result.results else 0,
                "risk_score": risk_result.risk_score,
                "confidence": analysis_result.signals[0].confidence if analysis_result.signals else 0,
            }
        ])

        # Extract the single HunterResult for this ticker (or provide a neutral fallback).
        if hunter_scan.qualified > 0:
            single_hunter = hunter_scan.opportunities[0]
        else:
            single_hunter = HunterResult(
                instrument_id=symbol,
                hunter_score=0.0,
                priority=3,
                ranking_score=0.0,
                risk_score=0.0,
                risk_level="",
                confidence=0.0,
                reasons=[],
                warnings=[],
                timestamp=datetime.now(timezone.utc),
            )

        # Step 8: Analyst Engine
        # AnalystEngine expects RankingResult (single), not FullRanking.
        # MasterEngine processes one symbol at a time — extract the first (and only) result.
        analyst_result = self.analyst_engine.generate_analysis(
            symbol=symbol,
            analysis_result=analysis_result,
            ranking_result=ranking_result.results[0] if ranking_result.results else None,
            risk_result=risk_result,
            hunter_result=single_hunter,
        )

        if trace is not None:
            trace.stage_start("final_result")
            trace.instrument_update(
                symbol,
                master_status=_TRACE_SUCCESS,
                final_result_created=True,
                final_status=_TRACE_SUCCESS,
            )

        final_result = FinalAnalysisResult(
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
        if trace is not None:
            trace.stage_end("final_result", _TRACE_SUCCESS, output_count=1)
        return final_result
