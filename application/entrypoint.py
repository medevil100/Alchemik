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


def build_runtime_service(
    persist_path: Path = None,
    *,
    yahoo_session=None,
    source_kind: str = None,
    static_tickers=None,
    controlled_source=None,
) -> RuntimeService:
    """
    Build and wire a production RuntimeService with SQLite persistence.

    Args:
        persist_path: Path to SQLite database. If None, uses default from
                      config.RuntimeConfig.
        yahoo_session: Optional injected YahooSession for tests. When omitted,
                       a production session over CurlCffiTransport is built.
        source_kind: Explicit instrument source kind. Defaults to dynamic
                     Yahoo discovery. The static source is an explicit fallback
                     and is never selected automatically.
        static_tickers: Approved list of exact Yahoo symbols, required only
                        when source_kind == "static".

    Returns:
        A fully wired RuntimeService instance.
    """
    # --- Data sources ---
    # Production source is dynamic Yahoo discovery. The static list is an
    # explicit emergency variant selected only by configuration.
    # Walidacja źródła następuje PRZED konstrukcją repozytorium SQLite, aby
    # błędna konfiguracja nigdy nie otwierała żadnej bazy (produkcyjna
    # alchemik_runtime.db jest otwierana wyłącznie przez jawną decyzję
    # o budowie produkcyjnej persystencji, nigdy przez błędne argumenty).
    from config.instrument_source import (
        SOURCE_KIND_STATIC,
        resolve_source_kind,
        validate_static_tickers,
    )

    effective_kind = resolve_source_kind(source_kind)
    if effective_kind == SOURCE_KIND_STATIC:
        validated_tickers = validate_static_tickers(static_tickers)
    else:
        validated_tickers = None

    # --- Persistence ---
    history_repository = SQLiteHistoryRepository(
        db_path=persist_path if persist_path else None
    )

    # --- Krok 1/8: międzyprocesowa blokada pojedynczego cyklu ---
    # Produkcyjny composition root zawsze tworzy rzeczywistą blokadę na
    # podstawie dokładnej produkcyjnej ścieżki bazy SQLite. W środowiskach,
    # gdzie repo jest podmienione (testy), blokada pozostaje None.
    cycle_lock = None
    _db_path_for_lock = getattr(history_repository, "db_path", None)
    if isinstance(_db_path_for_lock, Path):
        from application.cycle_lock import CycleLock

        cycle_lock = CycleLock(_db_path_for_lock)

    if yahoo_session is None:
        from data.yahoo.yahoo_transport import CurlCffiTransport
        from data.yahoo.yahoo_session import YahooSession
        yahoo_session = YahooSession(CurlCffiTransport())

    # Addytywny tryb CONTROLLED_VALIDATION_ONLY (Krok 7B/8): gdy przekazano
    # kontrolne jednoelementowe źródło, jest ono używane zamiast domyślnego
    # YahooDiscoverySource. Normalny composition root (controlled_source=None)
    # pozostaje bez zmian.
    if controlled_source is not None:
        instrument_source = controlled_source
    elif effective_kind == SOURCE_KIND_STATIC:
        from application.sources.static_instrument_source import StaticInstrumentSource
        instrument_source = StaticInstrumentSource(validated_tickers)
    else:
        from application.sources.yahoo_discovery_source import YahooDiscoverySource
        instrument_source = YahooDiscoverySource(yahoo_session)

    universe = PennyStockUniverse(instrument_source)

    from application.providers.yahoo_chart_provider import YahooChartProvider
    scan_provider = YahooChartProvider(yahoo_session, discovery_source=instrument_source)
    market_scanner = MarketScanner(universe, scan_provider)

    # Keep YahooFetcher for OutcomeComputer's existing contract.
    yahoo_fetcher = YahooFetcher()

    # --- Deduplication ---
    deduplicator = OpportunityDeduplicator(deduplication_window_seconds=3600)

    # --- Alert components ---
    alert_builder = AlertBuilder()
    alert_dispatcher = AlertDispatcher()  # No channels by default

    # --- Telegram (real, when configured; gracefully disabled otherwise) ---
    telegram_channel = None
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if telegram_bot_token.strip() and telegram_chat_id.strip():
        from application.channels.telegram_channel import TelegramChannel

        telegram_channel = TelegramChannel(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
        )

    # --- Tavily (real, when configured; gracefully disabled otherwise) ---
    tavily_adapter = None
    try:
        from data.tavily.config import TavilyConfig
        from data.tavily.service import TavilyService
        from data.tavily.event_adapter import TavilyEventAdapter

        tavily_config = TavilyConfig.from_env()
        if tavily_config.enabled:
            tavily_adapter = TavilyEventAdapter(TavilyService(tavily_config))
    except Exception:
        # No Tavily key / disabled / invalid config — the flow continues
        # without the Tavily context (Plan B: skip, do not fabricate news).
        tavily_adapter = None

    # --- OpenAI GPT-4o (real, only when a key is present) ---
    openai_provider = None
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_api_key.strip():
        from engines.ai.openai_provider import OpenAIProvider

        openai_provider = OpenAIProvider(
            api_key=openai_api_key,
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            timeout=float(os.environ.get("OPENAI_TIMEOUT", "30")),
            max_retries=0,  # Punkt 4: exactly one attempt per application call
        )

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
        tavily_adapter=tavily_adapter,
        openai_provider=openai_provider,
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
        telegram_channel=telegram_channel,
        outcome_computer=outcome_computer,
        cycle_lock=cycle_lock,
    )

    return runtime


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("ALCHEMIK RuntimeService starting")

    runtime = build_runtime_service()
    runtime.restore_active_observations()
    # Krok 4/8: produkcyjny cykl matrycy jest jawnie włączany w głównym
    # entrypoincie. Testy używające build_runtime_service() bez tej flagi
    # zachowują niezmienione istniejące zachowanie run_cycle().
    runtime.production_matrix_cycle = True
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