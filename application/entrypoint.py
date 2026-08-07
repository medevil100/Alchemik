"""
Minimal production entry point for ALCHEMIK RuntimeService with SQLite persistence.

Creates a fully wired RuntimeService using SQLiteHistoryRepository as the
persistent storage backend. This is the composition root for production use.

Usage:
    python -m application.entrypoint

Note: Requires environment variables for secrets (OpenAI API key, Telegram token).
      Without them, AI and Telegram features will be gracefully disabled.
"""
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from application.runtime import RuntimeService
from application.market_scanner import MarketScanner
from application.universe import PennyStockUniverse
from application.alert_dispatcher import AlertDispatcher
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.sources.static_instrument_source import StaticInstrumentSource
from application.providers.yahoo_scan_provider import YahooScanProvider
from data.yahoo.yahoo_fetcher import YahooFetcher
from application.opportunity_deduplicator import OpportunityDeduplicator
from application.alert_builder import AlertBuilder

from engines.hunter.engine import HunterEngine
from engines.master.engine import MasterEngine
from engines.technical.engine import TechnicalEngine
from engines.news.pipeline import NewsPipeline
from engines.news.filter import NewsFilterConfig
from engines.ai.decision_engine import DecisionEngine
from engines.ranking.engine import RankingEngine
from engines.risk.engine import RiskEngine
from engines.analyst.engine import AnalystEngine

from engines.outcome.engine import OutcomeComputer
from engines.outcome.calendar import TradingCalendar
from config.outcome import OutcomeConfig

logger = logging.getLogger(__name__)


def build_runtime_service(persist_path: Path = None) -> RuntimeService:
    """
    Build and wire a production RuntimeService with SQLite persistence.

    Args:
        persist_path: Path to SQLite database. If None, uses default from
                      config.RuntimeConfig.

    Returns:
        A fully wired RuntimeService instance.
    """
    # --- Persistence ---
    history_repository = SQLiteHistoryRepository(
        db_path=persist_path if persist_path else None
    )

    # --- Data sources ---
    instrument_source = StaticInstrumentSource()
    universe = PennyStockUniverse(instrument_source)
    yahoo_fetcher = YahooFetcher()
    scan_provider = YahooScanProvider(yahoo_fetcher)
    market_scanner = MarketScanner(universe, scan_provider)

    # --- Deduplication ---
    deduplicator = OpportunityDeduplicator(deduplication_window_seconds=3600)

    # --- Alert components ---
    alert_builder = AlertBuilder()
    alert_dispatcher = AlertDispatcher()  # No channels by default

    # --- Engines ---
    hunter_config = {
        "ranking_weight": 0.4,
        "risk_weight": 0.3,
        "confidence_weight": 0.3,
        "min_ranking_score": 0.5,
        "max_risk_score": 0.7,
        "min_confidence": 0.6,
        "max_results": 10,
        "priority_thresholds": [0.9, 0.7, 0.5],
    }
    hunter_engine = HunterEngine(hunter_config)
    technical_engine = TechnicalEngine()
    news_filter_config = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
    news_pipeline = NewsPipeline(news_filter_config)
    decision_engine = DecisionEngine()
    ranking_engine = RankingEngine()
    risk_engine = RiskEngine()
    analyst_engine = AnalystEngine()

    master_engine = MasterEngine(
        technical_engine=technical_engine,
        news_engine=news_pipeline,
        ai_engine=decision_engine,
        hunter_engine=hunter_engine,
        ranking_engine=ranking_engine,
        risk_engine=risk_engine,
        analyst_engine=analyst_engine,
    )

    # --- Outcome Computer ---
    outcome_computer = OutcomeComputer(
        repository=history_repository,
        yahoo_fetcher=yahoo_fetcher,
        calendar=TradingCalendar(),
        config=OutcomeConfig(),
    )

    runtime = RuntimeService(
        hunter_engine=hunter_engine,
        master_engine=master_engine,
        history_repository=history_repository,
        market_scanner=market_scanner,
        deduplicator=deduplicator,
        alert_builder=alert_builder,
        alert_dispatcher=alert_dispatcher,
        outcome_computer=outcome_computer,
    )

    return runtime


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("ALCHEMIK RuntimeService starting")

    runtime = build_runtime_service()
    report = runtime.run_cycle()

    logger.info("Cycle complete: %d candidates, %d success, %d errors",
                report.candidates_count, report.success_count, report.error_count)

    if report.errors:
        for err in report.errors:
            logger.warning("  Error: [%s] %s: %s",
                           err.stage, err.candidate_id, err.message)

    summary = runtime.history_repository.get_storage_summary()
    logger.info("Storage: %d cycles, %d MarketEvents in %s",
                summary["cycle_count"], summary["event_count"], summary["db_path"])


if __name__ == "__main__":
    main()