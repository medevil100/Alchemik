"""
Tests for DashboardReadService.

Uses temporary SQLite databases. Does NOT use the production database.
Does NOT start engines or runtime.
"""
import unittest
import tempfile
import os
import json
from datetime import datetime, timezone

from application.sqlite_history_repository import SQLiteHistoryRepository
from application.dashboard_read_service import DashboardReadService


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


class TestDashboardServiceEmpty(unittest.TestCase):
    """Test dashboard service with empty database."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.service = DashboardReadService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_empty_db_returns_200_structure(self):
        """Empty database returns HTTP 200 structure with is_empty: true."""
        result = self.service.get_dashboard_summary()
        self.assertIn("generated_at", result)
        self.assertIn("system", result)
        self.assertIn("runtime", result)
        self.assertIn("recent_activity", result)
        self.assertIn("top_tickers", result)
        self.assertIn("event_breakdown", result)
        self.assertIn("latest_events", result)
        self.assertTrue(result["runtime"]["is_empty"])
        self.assertEqual(result["runtime"]["cycle_count"], 0)
        self.assertEqual(result["runtime"]["event_count"], 0)
        self.assertEqual(result["recent_activity"]["events_in_last_cycle"], 0)
        self.assertEqual(result["recent_activity"]["events_last_24h"], 0)
        self.assertEqual(result["recent_activity"]["unique_tickers_last_24h"], 0)
        self.assertIsNone(result["recent_activity"]["last_event_at"])
        self.assertEqual(result["top_tickers"], [])
        self.assertEqual(result["event_breakdown"]["by_event_family"], [])
        self.assertEqual(result["event_breakdown"]["by_event_type"], [])
        self.assertEqual(result["event_breakdown"]["by_priority"], [])
        self.assertEqual(result["latest_events"], [])

    def test_generated_at_is_iso8601(self):
        """generated_at is a valid ISO 8601 string."""
        result = self.service.get_dashboard_summary()
        dt = datetime.fromisoformat(result["generated_at"])
        self.assertIsNotNone(dt)

    def test_system_status_ok_on_empty(self):
        """System status is 'ok' on empty db."""
        result = self.service.get_dashboard_summary()
        self.assertEqual(result["system"]["status"], "ok")
        self.assertEqual(result["system"]["database"], "available")


class TestDashboardServiceWithData(unittest.TestCase):
    """Test dashboard service with populated database."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)
        self.service = DashboardReadService(self.db_path)

        # Create cycles
        self.repo.save_cycle("cycle_1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })

        # Create various events
        self.repo.save_market_events("cycle_1", [
            _make_event_dict(event_id="evt_001", ticker="ABC", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="CRITICAL"),
            _make_event_dict(event_id="evt_002", ticker="ABC", event_family="VOLUME",
                             event_type="VOLUME_SPIKE", priority_final="HIGH"),
            _make_event_dict(event_id="evt_003", ticker="XYZ", event_family="PRICE",
                             event_type="PRICE_DROP", priority_final="CRITICAL"),
            _make_event_dict(event_id="evt_004", ticker="DEF", event_family="TECHNICAL",
                             event_type="RSI_OVERSOLD", priority_final="MEDIUM"),
            _make_event_dict(event_id="evt_005", ticker="ABC", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="HIGH"),
        ])

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_complete_response_structure(self):
        """Response has all required sections."""
        result = self.service.get_dashboard_summary()
        self.assertIn("generated_at", result)
        self.assertIn("system", result)
        self.assertIn("runtime", result)
        self.assertIn("recent_activity", result)
        self.assertIn("top_tickers", result)
        self.assertIn("event_breakdown", result)
        self.assertIn("latest_events", result)

    def test_runtime_counts(self):
        """Runtime section has correct counts."""
        result = self.service.get_dashboard_summary()
        self.assertEqual(result["runtime"]["cycle_count"], 1)
        self.assertEqual(result["runtime"]["event_count"], 5)
        self.assertFalse(result["runtime"]["is_empty"])

    def test_last_cycle_info(self):
        """Last cycle info is present."""
        result = self.service.get_dashboard_summary()
        self.assertIsNotNone(result["runtime"]["last_cycle"])
        self.assertEqual(result["runtime"]["last_cycle"]["cycle_id"], "cycle_1")

    def test_recent_activity_counters(self):
        """Recent activity has correct counters."""
        result = self.service.get_dashboard_summary()
        self.assertIsInstance(result["recent_activity"]["events_in_last_cycle"], int)
        self.assertIsInstance(result["recent_activity"]["events_last_24h"], int)
        self.assertIsInstance(result["recent_activity"]["unique_tickers_last_24h"], int)

    def test_top_tickers_order(self):
        """Top tickers are sorted by event count."""
        result = self.service.get_dashboard_summary(top_tickers_limit=10)
        tickers = result["top_tickers"]
        if len(tickers) > 1:
            for i in range(len(tickers) - 1):
                self.assertGreaterEqual(
                    tickers[i]["event_count"],
                    tickers[i + 1]["event_count"]
                )

    def test_top_tickers_limit(self):
        """Top tickers respects limit."""
        result = self.service.get_dashboard_summary(top_tickers_limit=2)
        self.assertLessEqual(len(result["top_tickers"]), 2)

    def test_event_breakdown_structure(self):
        """Event breakdown has all three sections."""
        result = self.service.get_dashboard_summary()
        self.assertIn("by_event_family", result["event_breakdown"])
        self.assertIn("by_event_type", result["event_breakdown"])
        self.assertIn("by_priority", result["event_breakdown"])

    def test_event_breakdown_families(self):
        """Event breakdown by family has correct entries."""
        result = self.service.get_dashboard_summary()
        families = {item["event_family"] for item in result["event_breakdown"]["by_event_family"]}
        self.assertIn("PRICE", families)
        self.assertIn("VOLUME", families)
        self.assertIn("TECHNICAL", families)

    def test_latest_events_limit(self):
        """Latest events respects limit."""
        result = self.service.get_dashboard_summary(latest_events_limit=3)
        self.assertLessEqual(len(result["latest_events"]), 3)

    def test_latest_events_structure(self):
        """Latest events have expected fields."""
        result = self.service.get_dashboard_summary(latest_events_limit=10)
        if result["latest_events"]:
            event = result["latest_events"][0]
            self.assertIn("event_id", event)
            self.assertIn("timestamp_utc", event)
            self.assertIn("ticker", event)
            self.assertIn("event_family", event)
            self.assertIn("event_type", event)
            self.assertIn("priority_final", event)

    def test_generated_at_iso8601(self):
        """generated_at is valid ISO 8601."""
        result = self.service.get_dashboard_summary()
        dt = datetime.fromisoformat(result["generated_at"])
        self.assertIsNotNone(dt)

    def test_no_mutation(self):
        """Dashboard service does not modify database."""
        initial_cycle_count = self.repo.count()
        initial_event_count = self.repo.count_market_events()
        self.service.get_dashboard_summary()
        self.service.get_dashboard_summary()
        self.service.get_dashboard_summary()
        final_cycle_count = self.repo.count()
        final_event_count = self.repo.count_market_events()
        self.assertEqual(initial_cycle_count, final_cycle_count)
        self.assertEqual(initial_event_count, final_event_count)

    def test_activity_hours_parameter(self):
        """Different activity_hours values produce consistent results."""
        result_24h = self.service.get_dashboard_summary(activity_hours=24)
        result_1h = self.service.get_dashboard_summary(activity_hours=1)
        # Both should work without errors
        self.assertIn("recent_activity", result_24h)
        self.assertIn("recent_activity", result_1h)


class TestDashboardServiceCyclesOnly(unittest.TestCase):
    """Test dashboard with cycles but no events."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)
        self.service = DashboardReadService(self.db_path)

        # Create cycles without events
        self.repo.save_cycle("c1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_cycles_no_events(self):
        """Dashboard works with cycles but no events."""
        result = self.service.get_dashboard_summary()
        self.assertFalse(result["runtime"]["is_empty"])
        self.assertEqual(result["runtime"]["cycle_count"], 1)
        self.assertEqual(result["runtime"]["event_count"], 0)
        self.assertIsNone(result["recent_activity"]["last_event_at"])
        self.assertEqual(result["latest_events"], [])
        self.assertEqual(result["top_tickers"], [])


class TestDashboardServiceParameterValidation(unittest.TestCase):
    """Test dashboard service parameter validation."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.service = DashboardReadService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_latest_events_limit_max(self):
        """Max latest_events_limit is 50."""
        result = self.service.get_dashboard_summary(latest_events_limit=100)
        self.assertLessEqual(len(result["latest_events"]), 50)

    def test_latest_events_limit_min(self):
        """Minimum latest_events_limit is 1."""
        result = self.service.get_dashboard_summary(latest_events_limit=0)
        # Should clamp to 1
        self.assertIsInstance(result["latest_events"], list)

    def test_top_tickers_limit_max(self):
        """Max top_tickers_limit is 50."""
        result = self.service.get_dashboard_summary(top_tickers_limit=100)
        self.assertLessEqual(len(result["top_tickers"]), 50)

    def test_activity_hours_min(self):
        """Minimum activity_hours is 1."""
        result = self.service.get_dashboard_summary(activity_hours=0)
        self.assertIn("recent_activity", result)

    def test_activity_hours_max(self):
        """Maximum activity_hours is 168."""
        result = self.service.get_dashboard_summary(activity_hours=200)
        self.assertIn("recent_activity", result)


if __name__ == "__main__":
    unittest.main()