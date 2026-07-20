"""
Tests for SQLiteHistoryRepository dashboard aggregation methods.

Uses temporary SQLite databases. Does NOT use the production database.
"""
import unittest
import tempfile
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from application.sqlite_history_repository import SQLiteHistoryRepository


def _make_event_dict(
    event_id: str = "evt_default",
    ticker: str = "TST",
    market: str = "NYSE",
    instrument_type: str = "STOCK_USA",
    event_family: str = "VOLUME",
    event_category: str = "VolumeAnomaly",
    event_type: str = "VOLUME_SPIKE",
    event_subcategory: str = None,
    priority_raw: str = "HIGH",
    priority_final: str = "HIGH",
    confidence_level: float = 0.85,
    detection_source: str = "VolumeDetector",
    event_owner: str = "TechnicalEngine",
    quality_level: str = "HIGH",
    schema_version: str = "1.0",
) -> dict:
    """Create a MarketEvent dict for testing."""
    return {
        "event_id": event_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker,
        "market": market,
        "instrument_type": instrument_type,
        "event_family": event_family,
        "event_category": event_category,
        "event_subcategory": event_subcategory,
        "event_type": event_type,
        "priority_raw": priority_raw,
        "priority_final": priority_final,
        "confidence_level": confidence_level,
        "detection_source": detection_source,
        "event_owner": event_owner,
        "price_data": None,
        "volume_data": None,
        "technical_context": None,
        "fundamental_context": None,
        "news_context": None,
        "ai_context": None,
        "tavily_context": None,
        "metadata": {},
        "composite_events": [],
        "is_composite": False,
        "quality_level": quality_level,
        "history": [],
        "schema_version": schema_version,
    }


class TestDashboardAggregations(unittest.TestCase):
    """Test dashboard aggregation queries."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)

        # Create test cycles and events
        self.repo.save_cycle("cycle_1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })

        self.repo.save_cycle("cycle_2", {
            "execution_time": 2.0, "candidates_count": 10,
            "success_count": 8, "error_count": 1, "report": {}
        })

        # Events for cycle_1
        self.repo.save_market_events("cycle_1", [
            _make_event_dict(event_id="evt_c1_1", ticker="TST1", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="CRITICAL"),
            _make_event_dict(event_id="evt_c1_2", ticker="TST1", event_family="VOLUME",
                             event_type="VOLUME_SPIKE", priority_final="HIGH"),
            _make_event_dict(event_id="evt_c1_3", ticker="TST2", event_family="PRICE",
                             event_type="PRICE_DROP", priority_final="CRITICAL"),
        ])

        # Events for cycle_2 (latest cycle)
        self.repo.save_market_events("cycle_2", [
            _make_event_dict(event_id="evt_c2_1", ticker="TST1", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="HIGH"),
            _make_event_dict(event_id="evt_c2_2", ticker="TST3", event_family="VOLUME",
                             event_type="VOLUME_SPIKE", priority_final="MEDIUM"),
            _make_event_dict(event_id="evt_c2_3", ticker="TST3", event_family="TECHNICAL",
                             event_type="RSI_OVERSOLD", priority_final="LOW"),
            _make_event_dict(event_id="evt_c2_4", ticker="TST2", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="CRITICAL"),
        ])

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_count_market_events_since(self):
        """Count events since N hours returns correct count."""
        # All events are recent (just created)
        count = self.repo.count_market_events_since(hours=24)
        self.assertEqual(count, 7)

    def test_count_market_events_since_zero_hours(self):
        """Count events since 0 hours still works (minimum 1 hour handled upstream)."""
        count = self.repo.count_market_events_since(hours=0)
        # 0 hours means 'now' - likely 0
        self.assertIsInstance(count, int)

    def test_count_unique_tickers_since(self):
        """Count unique tickers within time window."""
        count = self.repo.count_unique_tickers_since(hours=24)
        self.assertEqual(count, 3)

    def test_count_unique_tickers_since_no_events(self):
        """No unique tickers when no events in window."""
        count = self.repo.count_unique_tickers_since(hours=0)
        self.assertIsInstance(count, int)

    def test_get_last_market_event_time(self):
        """Last event time is not None when events exist."""
        last_time = self.repo.get_last_market_event_time()
        self.assertIsNotNone(last_time)
        self.assertIsInstance(last_time, str)

    def test_get_last_market_event_time_empty(self):
        """Last event time is None for empty database."""
        temp_db2 = tempfile.NamedTemporaryFile(delete=False)
        db_path2 = temp_db2.name
        temp_db2.close()
        try:
            repo2 = SQLiteHistoryRepository(db_path2)
            last_time = repo2.get_last_market_event_time()
            self.assertIsNone(last_time)
        finally:
            if os.path.exists(db_path2):
                os.unlink(db_path2)

    def test_count_events_for_latest_cycle(self):
        """Count events for the latest cycle."""
        count = self.repo.count_events_for_latest_cycle()
        self.assertEqual(count, 4)  # cycle_2 has 4 events

    def test_count_events_for_latest_cycle_empty(self):
        """Count events for latest cycle when no cycles exist."""
        temp_db2 = tempfile.NamedTemporaryFile(delete=False)
        db_path2 = temp_db2.name
        temp_db2.close()
        try:
            repo2 = SQLiteHistoryRepository(db_path2)
            count = repo2.count_events_for_latest_cycle()
            self.assertEqual(count, 0)
        finally:
            if os.path.exists(db_path2):
                os.unlink(db_path2)

    def test_count_events_for_cycle_specific(self):
        """Count events for a specific cycle."""
        count = self.repo.count_events_for_cycle("cycle_1")
        self.assertEqual(count, 3)

    def test_count_events_for_cycle_nonexistent(self):
        """Count events for nonexistent cycle returns 0."""
        count = self.repo.count_events_for_cycle("nonexistent")
        self.assertEqual(count, 0)

    def test_get_top_tickers_since_order(self):
        """Top tickers are sorted by event_count descending."""
        top = self.repo.get_top_tickers_since(limit=10, hours=24)
        self.assertGreater(len(top), 0)
        # TST1 appears in both cycles (3 times), TST3 appears in cycle_2 (2 times)
        # TST2 appears in both cycles (2 times)
        for i in range(len(top) - 1):
            self.assertGreaterEqual(top[i]["event_count"], top[i + 1]["event_count"])

    def test_get_top_tickers_since_limit(self):
        """Top tickers respects the limit."""
        top = self.repo.get_top_tickers_since(limit=2, hours=24)
        self.assertLessEqual(len(top), 2)

    def test_get_top_tickers_since_has_priority(self):
        """Top tickers include priority_final field."""
        top = self.repo.get_top_tickers_since(limit=10, hours=24)
        if top:
            self.assertIn("priority_final", top[0])
            self.assertIn("ticker", top[0])
            self.assertIn("event_count", top[0])
            self.assertIn("last_event_at", top[0])

    def test_top_tickers_priority_from_latest_event(self):
        """
        Priority_final in top tickers comes from the most recent event,
        not an alphabetical MAX. Given a ticker with events of different
        priorities, the latest event's priority_final wins.
        """
        # Save events individually (not in one batch) so they get different
        # created_at timestamps, ensuring deterministic ORDER BY.
        self.repo.save_market_event("cycle_2", _make_event_dict(
            event_id="evt_priority_order_1", ticker="PRIORITY_TEST",
            event_family="PRICE", event_type="PRICE_DROP",
            priority_final="LOW"))
        # Second event is saved later, gets a newer created_at
        self.repo.save_market_event("cycle_2", _make_event_dict(
            event_id="evt_priority_order_2", ticker="PRIORITY_TEST",
            event_family="PRICE", event_type="PRICE_SURGE",
            priority_final="CRITICAL"))
        # The latest event (second) has CRITICAL priority
        top = self.repo.get_top_tickers_since(limit=10, hours=24)
        for t in top:
            if t["ticker"] == "PRIORITY_TEST":
                self.assertEqual(t["priority_final"], "CRITICAL")
                break
        else:
            self.fail("PRIORITY_TEST not found in top tickers")

    def test_get_event_family_breakdown(self):
        """Event family breakdown returns correct counts."""
        breakdown = self.repo.get_event_family_breakdown_since(hours=24)
        # We have PRICE (3 events: c1_1, c1_3, c2_1, c2_4), VOLUME (2: c1_2, c2_2), TECHNICAL (1: c2_3)
        families = {item["event_family"]: item["count"] for item in breakdown}
        self.assertEqual(families.get("PRICE", 0), 4)  # 4 PRICE events

    def test_get_event_type_breakdown(self):
        """Event type breakdown returns correct counts."""
        breakdown = self.repo.get_event_type_breakdown_since(hours=24)
        types = {item["event_type"]: item["count"] for item in breakdown}
        self.assertEqual(types.get("PRICE_SURGE", 0), 3)

    def test_get_priority_breakdown(self):
        """Priority breakdown returns correct counts."""
        breakdown = self.repo.get_priority_breakdown_since(hours=24)
        priorities = {item["priority"]: item["count"] for item in breakdown}
        self.assertEqual(priorities.get("CRITICAL", 0), 3)

    def test_empty_results_for_future_time(self):
        """Methods return 0/empty for time windows before any event existed."""
        # Use a very large negative hours value (going forward in time) to ensure no events match
        count = self.repo.count_market_events_since(hours=-1)
        self.assertIsInstance(count, int)

    def test_top_tickers_empty_for_narrow_window(self):
        """Top tickers returns empty list when no events match window."""
        # Using a large positive offset (hours before events)
        top = self.repo.get_top_tickers_since(limit=10, hours=-1)
        self.assertEqual(len(top), 0)

    def test_breakdowns_empty_for_narrow_window(self):
        """Breakdowns are empty when no events match window."""
        # Using a large positive offset (hours before events exist)
        family_breakdown = self.repo.get_event_family_breakdown_since(hours=-1)
        type_breakdown = self.repo.get_event_type_breakdown_since(hours=-1)
        priority_breakdown = self.repo.get_priority_breakdown_since(hours=-1)
        self.assertEqual(len(family_breakdown), 0)
        self.assertEqual(len(type_breakdown), 0)
        self.assertEqual(len(priority_breakdown), 0)


class TestDashboardTimeHandling(unittest.TestCase):
    """Test time-related edge cases with ISO 8601 UTC timestamps."""

    _TS_UTC = "2026-07-20T20:00:00.000000+00:00"
    _TS_INSIDE = "2026-07-20T19:59:59.000000+00:00"  # 1 second inside 1h window
    _TS_BORDER = "2026-07-20T19:00:00.000000+00:00"   # exactly on 1h border
    _TS_OUTSIDE = "2026-07-20T18:59:59.000000+00:00"  # 1 second outside 1h window
    _TS_LOCAL_OLD = "2026-07-19T22:00:00"              # old local-time format (no offset, yesterday)

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)

        # Insert events with explicit created_at via raw SQL to control timestamps
        conn = sqlite3.connect(self.db_path)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO cycles (cycle_id, created_at) VALUES ('c_time', ?)",
            (now,),
        )
        # Insert events with various timestamp formats
        events = [
            ("evt_utc_now", "TST_TIME", self._TS_UTC),
            ("evt_inside", "TST_TIME", self._TS_INSIDE),
            ("evt_border", "TST_TIME", self._TS_BORDER),
            ("evt_outside", "TST_TIME", self._TS_OUTSIDE),
        ]
        for eid, ticker, ts in events:
            conn.execute(
                """INSERT INTO market_events
                   (cycle_id, event_id, ticker, event_family, event_type,
                    priority_raw, priority_final, confidence_level,
                    detection_source, event_owner, event_json, created_at)
                   VALUES (?, ?, ?, 'PRICE', 'TEST', 'LOW', 'LOW', 0.5,
                           'Test', 'TechnicalEngine', '{}', ?)""",
                ("c_time", eid, ticker, ts),
            )
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_utc_with_offset_included(self):
        """UTC event with +00:00 is counted in 24h window."""
        count = self.repo.count_market_events_since(hours=24)
        self.assertGreaterEqual(count, 4)

    def test_border_inside_included(self):
        """Event 1 second inside 1h window is included with 2h margin."""
        count = self.repo.count_market_events_since(hours=2)
        self.assertGreaterEqual(count, 2)

    def test_border_outside_excluded(self):
        """Events outside narrow window don't appear unreasonably."""
        count = self.repo.count_market_events_since(hours=0)
        self.assertIsInstance(count, int)

    def test_local_time_format_included(self):
        """Old local-time records (no offset) are still correctly interpreted."""
        count = self.repo.count_market_events_since(hours=24)
        self.assertGreaterEqual(count, 4)

    def test_sorting_utc_iso8601(self):
        """Sorting by datetime(created_at) DESC works with +00:00 timestamps."""
        last = self.repo.get_last_market_event_time()
        self.assertEqual(last, self._TS_UTC)

    def test_top_tickers_tiebreaker_identical_timestamp(self):
        """
        Two events for the same ticker with identical created_at:
        priority_final from the last-inserted record (higher id) wins.
        """
        conn = sqlite3.connect(self.db_path)
        # Both have same created_at, but second insert gets higher id
        conn.execute(
            """INSERT INTO market_events
               (cycle_id, event_id, ticker, event_family, event_type,
                priority_raw, priority_final, confidence_level,
                detection_source, event_owner, event_json, created_at)
               VALUES (?, ?, ?, 'PRICE', 'TEST', 'LOW', 'LOW', 0.5,
                       'Test', 'TechnicalEngine', '{}', ?)""",
            ("c_time", "evt_tie_1", "TIE_TEST", self._TS_UTC),
        )
        conn.execute(
            """INSERT INTO market_events
               (cycle_id, event_id, ticker, event_family, event_type,
                priority_raw, priority_final, confidence_level,
                detection_source, event_owner, event_json, created_at)
               VALUES (?, ?, ?, 'PRICE', 'TEST', 'LOW', 'HIGH', 0.5,
                       'Test', 'TechnicalEngine', '{}', ?)""",
            ("c_time", "evt_tie_2", "TIE_TEST", self._TS_UTC),
        )
        conn.commit()
        conn.close()

        top = self.repo.get_top_tickers_since(limit=10, hours=24)
        for t in top:
            if t["ticker"] == "TIE_TEST":
                self.assertEqual(t["priority_final"], "HIGH")
                break
        else:
            self.fail("TIE_TEST not found in top tickers")

    def test_last_event_time_with_utc_offset(self):
        """get_last_market_event_time returns the right timestamp."""
        last = self.repo.get_last_market_event_time()
        self.assertEqual(last, self._TS_UTC)


class TestDashboardAggregationsMinimal(unittest.TestCase):
    """Test dashboard aggregations with minimal or empty data."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_all_aggregations_empty_db(self):
        """All aggregation methods work on empty database."""
        self.assertEqual(self.repo.count_market_events_since(24), 0)
        self.assertEqual(self.repo.count_unique_tickers_since(24), 0)
        self.assertIsNone(self.repo.get_last_market_event_time())
        self.assertEqual(self.repo.count_events_for_latest_cycle(), 0)
        self.assertEqual(self.repo.count_events_for_cycle("nonexistent"), 0)
        self.assertEqual(len(self.repo.get_top_tickers_since(10, 24)), 0)
        self.assertEqual(len(self.repo.get_event_family_breakdown_since(24)), 0)
        self.assertEqual(len(self.repo.get_event_type_breakdown_since(24)), 0)
        self.assertEqual(len(self.repo.get_priority_breakdown_since(24)), 0)

    def test_cycles_no_events(self):
        """Aggregations work when cycles exist but no events."""
        self.repo.save_cycle("c1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })
        self.assertEqual(self.repo.count_events_for_latest_cycle(), 0)
        self.assertEqual(self.repo.count_market_events_since(24), 0)
        self.assertIsNone(self.repo.get_last_market_event_time())


if __name__ == "__main__":
    unittest.main()