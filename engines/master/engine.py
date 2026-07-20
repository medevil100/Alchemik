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
from data.models import FinalAnalysisResult, MarketData, MarketEvent, InstrumentType
from datetime import datetime

logger = logging.getLogger(__name__)


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
                 volume_detector=None):
        self.technical_engine = technical_engine or TechnicalEngine()
        self.news_engine = news_engine or NewsPipeline()
        self.ai_engine = ai_engine or DecisionEngine()
        self.ranking_engine = ranking_engine or RankingEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.hunter_engine = hunter_engine or HunterEngine()
        self.analyst_engine = analyst_engine or AnalystEngine()
        self.price_detector = price_detector or PriceDetector()
        self.volume_detector = volume_detector or VolumeDetector()

    def run_detectors(
        self,
        ticker: str,
        market: str,
        instrument_type: InstrumentType,
        ohlcv_data: List[MarketData],
    ) -> List[MarketEvent]:
        """
        Run PriceDetector and VolumeDetector on the given OHLCV data.

        This method orchestrates the detection phase of the MarketEvent lifecycle.
        It does NOT modify AnalysisResult, AISignal, or FinalAnalysisResult.

        Args:
            ticker: Instrument symbol (e.g., "XYZ.WA")
            market: Market identifier (e.g., "GPW", "NYSE")
            instrument_type: Type of instrument (STOCK_GPW, STOCK_USA, ETF)
            ohlcv_data: List of MarketData candles sorted chronologically.

        Returns:
            Combined list of MarketEvent objects from all detectors.
            Empty list if no events detected or data insufficient.
        """
        events: List[MarketEvent] = []

        # Run PriceDetector
        price_events = self.price_detector.detect(
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            ohlcv_data=ohlcv_data,
        )
        events.extend(price_events)

        # Run VolumeDetector
        volume_events = self.volume_detector.detect(
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            ohlcv_data=ohlcv_data,
        )
        events.extend(volume_events)

        return events

    def run_analysis(
        self,
        symbol: str,
        market: str = "UNKNOWN",
        instrument_type: InstrumentType = InstrumentType.STOCK_USA,
        events_out: Optional[List[MarketEvent]] = None,
    ) -> FinalAnalysisResult:
        """
        Execute the full analysis pipeline for a single instrument.

        Detectors (PriceDetector, VolumeDetector) are run EXACTLY ONCE
        inside this method, when market data is available from the
        TechnicalEngine result.

        Args:
            symbol: Instrument ticker.
            market: Market identifier (e.g., "GPW", "NYSE", "NASDAQ").
            instrument_type: Type of instrument (STOCK_GPW, STOCK_USA, ETF).
            events_out: Optional mutable list to receive detected MarketEvents.
                        If provided, detected events are appended to this list
                        for consumption by the caller (RuntimeService).
                        This avoids changing the return type or storing
                        state on the instance.

        Returns:
            FinalAnalysisResult (unchanged old pipeline result).

        Raises:
            ValueError: If symbol is empty or not a string.
        """
        # Validate symbol
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Invalid symbol. Symbol must be a non-empty string.")

        # Step 1: Technical Engine
        technical_result = self.technical_engine.analyze([symbol])

        # Step 2: Run detectors on market data (if available from technical result)
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
        ai_result = self.ai_engine.process_data({"symbol": symbol, "technical": technical_result, "news": news_result})

        # Step 5: Ranking Engine
        ranking_result = self.ranking_engine.calculate_ranking([ai_result])

        # Step 6: Risk Engine
        risk_result = self.risk_engine.assess_risk(ai_result, ranking_result)

        # Step 7: Hunter Engine
        hunter_result = self.hunter_engine.scan([{"symbol": symbol, "risk": risk_result, "ranking": ranking_result}])

        # Step 8: Analyst Engine
        analyst_result = self.analyst_engine.generate_analysis(hunter_result)

        # Return Final Analysis Result (unchanged)
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
