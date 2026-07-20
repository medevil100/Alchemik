#!/usr/bin/env python
"""
Smoke test: real ticker through full pipeline → SQLite persistence.

Tests the complete flow:
    YahooFetcher → TechnicalEngine → MasterEngine (detectors) → RuntimeService → SQLite

Uses a temporary database. No Telegram sent. No secrets exposed.
"""
import sys
import tempfile
import os
import gc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from application.sqlite_history_repository import SQLiteHistoryRepository
from application.runtime import RuntimeService
from application.market_scanner import MarketScanner
from application.universe import PennyStockUniverse
from application.sources.static_instrument_source import StaticInstrumentSource
from application.providers.yahoo_scan_provider import YahooScanProvider
from data.yahoo.yahoo_fetcher import YahooFetcher
from application.opportunity_deduplicator import OpportunityDeduplicator

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
    # 1. Create temp database
    tmp = tempfile.NamedTemporaryFile(delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        # 2. Build pipeline with SQLite persistence
        history_repo = SQLiteHistoryRepository(db_path)

        # Use a single real ticker for the smoke test
        universe = PennyStockUniverse(StaticInstrumentSource(["AAPL"]))
        yahoo_fetcher = YahooFetcher()
        scan_provider = YahooScanProvider(yahoo_fetcher)
        market_scanner = MarketScanner(universe, scan_provider)

        deduplicator = OpportunityDeduplicator(deduplication_window_seconds=3600)

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

        runtime = RuntimeService(
            hunter_engine=hunter_engine,
            master_engine=master_engine,
            history_repository=history_repo,
            market_scanner=market_scanner,
            deduplicator=deduplicator,
        )

        # 3. Execute one cycle (real data from Yahoo Finance)
        print("=" * 60)
        print("SMOKE TEST: Full pipeline with SQLite persistence")
        print("=" * 60)
        print(f"Temporary DB: {db_path}")
        print(f"Ticker: AAPL (NASDAQ)")
        print()

        report = runtime.run_cycle()

        print("CYCLE RESULT:")
        print(f"  Candidates: {report.candidates_count}")
        print(f"  Success:    {report.success_count}")
        print(f"  Errors:     {report.error_count}")
        if report.errors:
            for err in report.errors:
                print(f"    [{err.stage}] {err.candidate_id}: {err.message}")
        print(f"  Events:     {len(report.results)}")
        print()

        # 4. Check storage before restart
        s1 = history_repo.get_storage_summary()
        print(f"STORAGE BEFORE RESTART:")
        print(f"  Cycles: {s1['cycle_count']}")
        print(f"  Events: {s1['event_count']}")
        print(f"  Journal: {s1['journal_mode']}")
        print()

        # 5. Simulate restart
        del runtime, history_repo, master_engine
        gc.collect()

        # 6. Reopen database
        repo2 = SQLiteHistoryRepository(db_path)
        s2 = repo2.get_storage_summary()

        print(f"STORAGE AFTER RESTART:")
        print(f"  Cycles:              {s2['cycle_count']}")
        print(f"  Events:              {s2['event_count']}")
        print(f"  Journal:             {s2['journal_mode']}")

        # 7. Verify cycle data
        cycles = repo2.list_cycle_summaries(limit=5)
        print(f"  Cycles retrieved:    {len(cycles)}")
        for c in cycles:
            print(f"    Cycle: {c['cycle_id']}")
            print(f"      Status: {c.get('status', 'completed')}")
            print(f"      Time:   {c.get('execution_time', 'N/A'):.3f}s")
            print(f"      Cand:   {c.get('candidates_count', 0)}")
            print(f"      Ok/Err: {c.get('success_count', 0)}/{c.get('error_count', 0)}")

        # 8. Verify MarketEvents
        events = repo2.get_latest_market_events(limit=20)
        print(f"  MarketEvents:        {len(events)}")
        for ev in events:
            print(f"    {ev.get('event_id', '?'):30s} | {ev.get('ticker', '?'):10s} | "
                  f"{ev.get('event_type', '?'):20s} | priority={ev.get('priority_raw', '?')}")
        print()

        # 9. Summary
        print("=" * 60)
        if s2['cycle_count'] > 0 and s1['cycle_count'] == s2['cycle_count']:
            print("SMOKE TEST PASSED: Cycle persisted and survived restart.")
        else:
            print("SMOKE TEST WARNING: Check cycle count before/after restart.")
        print("=" * 60)

    finally:
        # Cleanup temp database
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    main()