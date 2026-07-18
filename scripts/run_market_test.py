import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

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
from application.channels.telegram_channel import TelegramChannel

from engines.hunter.engine import HunterEngine
from engines.master.engine import MasterEngine
from engines.technical.engine import TechnicalEngine
from engines.news.pipeline import NewsPipeline
from engines.news.filter import NewsFilterConfig
from engines.ai.decision_engine import DecisionEngine
from engines.ranking.engine import RankingEngine
from engines.risk.engine import RiskEngine
from engines.analyst.engine import AnalystEngine

def main():
    # 1. Configure test parameters
    test_tickers = ["CDR.WA", "11B.WA", "AAPL", "MSFT"]  # 2 GPW + 2 USA tickers
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sqlite_path = str(PROJECT_ROOT / "data" / "runtime" / "market_test.db")
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    # 2. Create dependencies with dependency injection
    instrument_source = StaticInstrumentSource(test_tickers)
    universe = PennyStockUniverse(instrument_source)
    yahoo_fetcher = YahooFetcher()
    scan_provider = YahooScanProvider(yahoo_fetcher)
    market_scanner = MarketScanner(universe, scan_provider)
    history_repository = SQLiteHistoryRepository(db_path=sqlite_path)
    deduplicator = OpportunityDeduplicator(deduplication_window_seconds=3600)
    alert_builder = AlertBuilder()
    
    # Configure Telegram if environment variables are set
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if telegram_token and telegram_chat_id:
        telegram_channel = TelegramChannel(telegram_token, telegram_chat_id)
        alert_dispatcher = AlertDispatcher(channels=[telegram_channel])
    else:
        alert_dispatcher = AlertDispatcher()

    # 3. Create all required engines with configurations
    # Hunter Engine
    hunter_config = {
        "ranking_weight": 0.4,
        "risk_weight": 0.3,
        "confidence_weight": 0.3,
        "min_ranking_score": 0.5,
        "max_risk_score": 0.7,
        "min_confidence": 0.6,
        "max_results": 10,
        "priority_thresholds": [0.9, 0.7, 0.5]
    }
    hunter_engine = HunterEngine(hunter_config)
    
    # Technical Engine (no config needed)
    technical_engine = TechnicalEngine()
    
    # News Pipeline with Filter Config
    news_filter_config = NewsFilterConfig(
        min_content_length=50,
        min_quality_score=0.5
    )
    news_pipeline = NewsPipeline(news_filter_config)
    
    # Decision Engine (no config needed)
    decision_engine = DecisionEngine()
    
    # Ranking Engine with default config
    ranking_engine = RankingEngine()
    
    # Risk Engine with default config
    risk_engine = RiskEngine()
    
    # Analyst Engine (no config needed)
    analyst_engine = AnalystEngine()
    
    # 4. Create MasterEngine with all dependencies
    master_engine = MasterEngine(
        technical_engine=technical_engine,
        news_engine=news_pipeline,
        ai_engine=decision_engine,
        hunter_engine=hunter_engine,
        ranking_engine=ranking_engine,
        risk_engine=risk_engine,
        analyst_engine=analyst_engine
    )
    
    # 5. Create RuntimeService and inject dependencies
    runtime = RuntimeService(
        hunter_engine=hunter_engine,
        master_engine=master_engine,
        history_repository=history_repository,
        market_scanner=market_scanner,
        deduplicator=deduplicator,
        alert_builder=alert_builder,
        alert_dispatcher=alert_dispatcher
    )

    # 6. Execute single test cycle
    start_time = time.time()
    report = runtime.run_cycle()
    end_time = time.time()

    # 7. Print cycle report
    print(f"Input tickers: {test_tickers}")
    print(f"Candidates count: {report.candidates_count}")
    print(f"Success count: {report.success_count}")
    print(f"Error count: {report.error_count}")
    print(f"Errors: {report.errors}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    print(f"Database path: {sqlite_path}")
    print(f"Alerts count: {report.alerts_count}")

if __name__ == "__main__":
    main()