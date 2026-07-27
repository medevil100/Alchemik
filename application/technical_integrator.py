"""
TechnicalIntegrator — integration layer connecting MarketEvent → TechnicalEngine.

This module implements the FIRST real connection in the ALCHEMIK pipeline:
after a MarketEvent is created, the system runs existing TechnicalEngine
analysis for the ticker associated with that event.

Key design decisions:
- Resides OUTSIDE frozen engine modules (MasterEngine, TechnicalEngine, etc.)
- Uses ONLY public APIs of TechnicalEngine and YahooFetcher
- Does NOT trigger downstream engines (Ranking, Risk, Analyst, Master, etc.)
- Does NOT write to SQLite
- Does NOT modify MarketEvent contract
- Errors are NOT silenced — they propagate to the caller
"""

from __future__ import annotations

import logging
from typing import List

from data.models.analysis_result import AnalysisResult
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from data.yahoo.yahoo_fetcher import YahooFetcher
from engines.technical import TechnicalEngine

logger = logging.getLogger(__name__)


class TechnicalIntegrator:
    """Connects a MarketEvent to TechnicalEngine analysis.

    Responsibility:
        Given a valid MarketEvent, fetch OHLCV data for event.ticker
        via YahooFetcher, run TechnicalEngine.analyze(), and store
        the resulting indicators in event.technical_context.

    This component does NOT:
        - Run RankingEngine, RiskEngine, AnalystEngine, or MasterEngine
        - Write to SQLite
        - Modify frozen modules
        - Trigger Tavily or Telegram
    """

    def __init__(
        self,
        technical_engine: TechnicalEngine | None = None,
        yahoo_fetcher: YahooFetcher | None = None,
    ) -> None:
        """Initialize the integrator with optional dependency injection.

        Args:
            technical_engine: Optional TechnicalEngine instance.
                              Defaults to a new TechnicalEngine().
            yahoo_fetcher: Optional YahooFetcher instance.
                           Defaults to a new YahooFetcher().
        """
        self._technical_engine = technical_engine or TechnicalEngine()
        self._yahoo_fetcher = yahoo_fetcher or YahooFetcher()

    def integrate(self, event: MarketEvent) -> AnalysisResult:
        """Run technical analysis for the given MarketEvent.

        Workflow:
            1. Validate that *event* is a proper MarketEvent with a ticker.
            2. Fetch OHLCV data via YahooFetcher.fetch_stock_data(event.ticker).
            3. Call TechnicalEngine.analyze(market_data) → AnalysisResult.
            4. Store AnalysisResult.indicators in event.technical_context.
            5. Record a history entry on the event.
            6. Return the AnalysisResult.

        Args:
            event: A MarketEvent whose ticker will be analysed.

        Returns:
            AnalysisResult containing the computed technical indicators.

        Raises:
            ValueError: If *event* is not a MarketEvent or has no ticker.
            YahooFinanceError / InvalidSymbolError / RateLimitExceededError:
                Propagated from YahooFetcher if data fetch fails.
            Any exception from TechnicalEngine.analyze() is NOT caught
            and will propagate to the caller.
        """
        # --- 1. Validation ---
        if not isinstance(event, MarketEvent):
            raise ValueError(
                f"event must be a MarketEvent instance, got {type(event).__name__}"
            )
        if not event.ticker or not isinstance(event.ticker, str) or not event.ticker.strip():
            raise ValueError("MarketEvent.ticker must be a non-empty string")

        ticker = event.ticker.strip()
        logger.info("Integrating MarketEvent %s for ticker %s", event.event_id, ticker)

        # --- 2. Fetch OHLCV data ---
        market_data: List[MarketData] = self._yahoo_fetcher.fetch_stock_data(ticker)
        logger.debug("Fetched %d MarketData points for %s", len(market_data), ticker)

        # --- 3. Run TechnicalEngine analysis ---
        analysis_result: AnalysisResult = self._technical_engine.analyze(market_data)

        # --- 4. Store indicators in MarketEvent.technical_context ---
        if hasattr(analysis_result, "indicators") and analysis_result.indicators:
            event.technical_context = analysis_result.indicators
        else:
            event.technical_context = {}

        # --- 5. Record history entry ---
        event.add_history_entry(
            module="TechnicalIntegrator",
            action=f"Analiza techniczna dla {ticker} — {len(event.technical_context)} wskaźników",
            fields_changed=["technical_context"],
        )

        logger.info(
            "TechnicalIntegrator completed for %s: %d indicators computed",
            ticker,
            len(event.technical_context),
        )

        return analysis_result