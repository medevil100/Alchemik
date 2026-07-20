#!/usr/bin/env python
"""
Diagnostic script to read stored data from SQLite runtime database.

Usage:
    python scripts/read_stored_data.py [--db PATH] [--cycles N] [--events N]

Shows recent cycles and MarketEvents from the persistent storage.
Default path: data/runtime/alchemik_runtime.db
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from application.sqlite_history_repository import SQLiteHistoryRepository


def main():
    parser = argparse.ArgumentParser(description="Read stored ALCHEMIK runtime data")
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to SQLite database (default: data/runtime/alchemik_runtime.db)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=10,
        help="Number of recent cycles to show (default: 10)",
    )
    parser.add_argument(
        "--events",
        type=int,
        default=20,
        help="Number of recent MarketEvents to show (default: 20)",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Filter MarketEvents by ticker (optional)",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else None
    repo = SQLiteHistoryRepository(db_path)

    # Storage summary
    summary = repo.get_storage_summary()
    print("=" * 60)
    print("ALCHEMIK — STORAGE SUMMARY")
    print("=" * 60)
    print(f"  Database path:  {summary['db_path']}")
    print(f"  Journal mode:    {summary['journal_mode']}")
    print(f"  Schema version:  {summary['schema_version']}")
    print(f"  Total cycles:    {summary['cycle_count']}")
    print(f"  Total events:    {summary['event_count']}")
    print()

    # Recent cycles
    print("=" * 60)
    print(f"RECENT CYCLES (last {args.cycles})")
    print("=" * 60)
    cycles = repo.list_cycle_summaries(limit=args.cycles)
    if not cycles:
        print("  (no cycles recorded)")
    else:
        for c in cycles:
            print(f"  Cycle:    {c['cycle_id']}")
            print(f"    Created: {c['created_at']}")
            print(f"    Status:  {c.get('status', 'completed')}")
            print(f"    Time:    {c.get('execution_time', 'N/A'):.3f}s")
            print(f"    Cand:    {c.get('candidates_count', 0)}")
            print(f"    Ok/Err:  {c.get('success_count', 0)}/{c.get('error_count', 0)}")
            if c.get('error_message'):
                print(f"    Error:   {c['error_message']}")
            print()

    # Recent MarketEvents
    print("=" * 60)
    if args.ticker:
        print(f"MARKET EVENTS FOR TICKER: {args.ticker} (last {args.events})")
        print("=" * 60)
        events = repo.get_market_events_by_ticker(args.ticker, limit=args.events)
    else:
        print(f"RECENT MARKET EVENTS (last {args.events})")
        print("=" * 60)
        events = repo.get_latest_market_events(limit=args.events)

    if not events:
        print("  (no market events recorded)")
    else:
        for ev in events:
            print(f"  EventID:   {ev.get('event_id', 'N/A')}")
            print(f"    Ticker:    {ev.get('ticker', 'N/A')}")
            print(f"    Type:      {ev.get('event_type', 'N/A')}")
            print(f"    Family:    {ev.get('event_family', 'N/A')}")
            print(f"    Market:    {ev.get('market', 'N/A')}")
            print(f"    Priority:  {ev.get('priority_raw', 'N/A')}")
            print(f"    Conf:      {ev.get('confidence_level', 0.0):.2f}")
            print(f"    Source:    {ev.get('detection_source', 'N/A')}")
            print(f"    CycleID:   {ev.get('_cycle_id', 'N/A')}")
            print(f"    SavedAt:   {ev.get('_saved_at', 'N/A')}")
            print()


if __name__ == "__main__":
    main()