"""
Tests for the Dashboard API endpoint (GET /api/v1/dashboard).

Uses temporary SQLite databases. Does NOT use the production database.
Does NOT start engines or runtime.
"""
import unittest
import tempfile
import os
from datetime import datetime, timezone

from application.sqlite_history_repository import SQLiteHistoryRepository
from application.read_service import RuntimeReadService
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


# Check if FastAPI TestClient is available
try:
    from fastapi.testclient import TestClient
    from application.api_entrypoint import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestDashboardAPIEmpty(unittest.TestCase):
    """Test dashboard endpoint with empty database."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.dashboard_service = DashboardReadService(self.db_path)
        self.read_service = RuntimeReadService(self.db_path)

        import application.api_entrypoint as api
        api._read_service = self.read_service
        api._dashboard_service = self.dashboard_service

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_dashboard_empty_returns_200(self):
        """Dashboard returns 200 for empty database."""
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_empty_has_all_sections(self):
        """Empty dashboard has all required sections."""
        response = self.client.get("/api/v1/dashboard")
        data = response.json()
        self.assertIn("generated_at", data)
        self.assertIn("system", data)
        self.assertIn("runtime", data)
        self.assertIn("recent_activity", data)
        self.assertIn("top_tickers", data)
        self.assertIn("event_breakdown", data)
        self.assertIn("latest_events", data)

    def test_dashboard_empty_is_empty_true(self):
        """Empty database has is_empty: true."""
        response = self.client.get("/api/v1/dashboard")
        data = response.json()
        self.assertTrue(data["runtime"]["is_empty"])

    def test_dashboard_empty_counters_zero(self):
        """Empty database has zero counters."""
        response = self.client.get("/api/v1/dashboard")
        data = response.json()
        self.assertEqual(data["runtime"]["cycle_count"], 0)
        self.assertEqual(data["runtime"]["event_count"], 0)
        self.assertEqual(data["recent_activity"]["events_in_last_cycle"], 0)
        self.assertEqual(data["recent_activity"]["events_last_24h"], 0)
        self.assertEqual(data["recent_activity"]["unique_tickers_last_24h"], 0)

    def test_dashboard_empty_lists_empty(self):
        """Empty database has empty lists."""
        response = self.client.get("/api/v1/dashboard")
        data = response.json()
        self.assertEqual(data["top_tickers"], [])
        self.assertEqual(data["latest_events"], [])
        self.assertEqual(data["event_breakdown"]["by_event_family"], [])
        self.assertEqual(data["event_breakdown"]["by_event_type"], [])
        self.assertEqual(data["event_breakdown"]["by_priority"], [])


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestDashboardAPIWithData(unittest.TestCase):
    """Test dashboard endpoint with populated database."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.repo = SQLiteHistoryRepository(self.db_path)
        self.dashboard_service = DashboardReadService(self.db_path)
        self.read_service = RuntimeReadService(self.db_path)

        # Create test data
        self.repo.save_cycle("cycle_1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })
        self.repo.save_market_events("cycle_1", [
            _make_event_dict(event_id="evt_001", ticker="ABC", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="CRITICAL"),
            _make_event_dict(event_id="evt_002", ticker="ABC", event_family="VOLUME",
                             event_type="VOLUME_SPIKE", priority_final="HIGH"),
            _make_event_dict(event_id="evt_003", ticker="XYZ", event_family="PRICE",
                             event_type="PRICE_DROP", priority_final="CRITICAL"),
        ])

        import application.api_entrypoint as api
        api._read_service = self.read_service
        api._dashboard_service = self.dashboard_service

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_dashboard_returns_200(self):
        """Dashboard returns 200 with data."""
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["runtime"]["is_empty"])

    def test_dashboard_runtime_counts(self):
        """Runtime counts are correct."""
        response = self.client.get("/api/v1/dashboard")
        data = response.json()
        self.assertEqual(data["runtime"]["cycle_count"], 1)
        self.assertEqual(data["runtime"]["event_count"], 3)

    def test_dashboard_latest_events_limit(self):
        """Latest events limit works."""
        response = self.client.get("/api/v1/dashboard?latest_events_limit=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["latest_events"]), 2)

    def test_dashboard_top_tickers_limit(self):
        """Top tickers limit works."""
        response = self.client.get("/api/v1/dashboard?top_tickers_limit=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["top_tickers"]), 1)

    def test_dashboard_activity_hours(self):
        """Activity hours parameter works."""
        response = self.client.get("/api/v1/dashboard?activity_hours=48")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recent_activity", data)

    def test_dashboard_event_breakdown(self):
        """Event breakdown contains expected data."""
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        families = {item["event_family"] for item in data["event_breakdown"]["by_event_family"]}
        self.assertIn("PRICE", families)
        self.assertIn("VOLUME", families)

    def test_dashboard_top_tickers_content(self):
        """Top tickers have expected fields."""
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if data["top_tickers"]:
            ticker = data["top_tickers"][0]
            self.assertIn("ticker", ticker)
            self.assertIn("event_count", ticker)
            self.assertIn("last_event_at", ticker)
            self.assertIn("priority_final", ticker)

    def test_dashboard_latest_events_content(self):
        """Latest events have expected fields."""
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if data["latest_events"]:
            event = data["latest_events"][0]
            self.assertIn("event_id", event)
            self.assertIn("ticker", event)
            self.assertIn("event_family", event)
            self.assertIn("event_type", event)


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestDashboardAPIParameters(unittest.TestCase):
    """Test dashboard endpoint parameter validation."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.dashboard_service = DashboardReadService(self.db_path)
        self.read_service = RuntimeReadService(self.db_path)

        import application.api_entrypoint as api
        api._read_service = self.read_service
        api._dashboard_service = self.dashboard_service

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_negative_latest_events_limit_rejected(self):
        """Negative latest_events_limit returns 422."""
        response = self.client.get("/api/v1/dashboard?latest_events_limit=-1")
        self.assertEqual(response.status_code, 422)

    def test_excessive_latest_events_limit_rejected(self):
        """latest_events_limit > 50 returns 422."""
        response = self.client.get("/api/v1/dashboard?latest_events_limit=51")
        self.assertEqual(response.status_code, 422)

    def test_negative_top_tickers_limit_rejected(self):
        """Negative top_tickers_limit returns 422."""
        response = self.client.get("/api/v1/dashboard?top_tickers_limit=-1")
        self.assertEqual(response.status_code, 422)

    def test_excessive_top_tickers_limit_rejected(self):
        """top_tickers_limit > 50 returns 422."""
        response = self.client.get("/api/v1/dashboard?top_tickers_limit=51")
        self.assertEqual(response.status_code, 422)

    def test_activity_hours_zero_rejected(self):
        """activity_hours = 0 returns 422."""
        response = self.client.get("/api/v1/dashboard?activity_hours=0")
        self.assertEqual(response.status_code, 422)

    def test_activity_hours_excessive_rejected(self):
        """activity_hours > 168 returns 422."""
        response = self.client.get("/api/v1/dashboard?activity_hours=169")
        self.assertEqual(response.status_code, 422)

    def test_no_db_path_in_response(self):
        """Error responses don't contain system paths."""
        response = self.client.get("/api/v1/dashboard")
        body_str = response.text.lower()
        self.assertNotIn("c:\\", body_str)
        self.assertNotIn("/home/", body_str)


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestDashboardAPINoMutation(unittest.TestCase):
    """Test that dashboard endpoint does not mutate data."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.repo = SQLiteHistoryRepository(self.db_path)
        self.dashboard_service = DashboardReadService(self.db_path)
        self.read_service = RuntimeReadService(self.db_path)

        # Create test data
        self.repo.save_cycle("cycle_1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })
        self.repo.save_market_events("cycle_1", [
            _make_event_dict(event_id="evt_001", ticker="ABC", event_family="PRICE",
                             event_type="PRICE_SURGE", priority_final="CRITICAL"),
        ])

        self.initial_cycle_count = self.repo.count()
        self.initial_event_count = self.repo.count_market_events()

        import application.api_entrypoint as api
        api._read_service = self.read_service
        api._dashboard_service = self.dashboard_service

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_dashboard_does_not_change_cycle_count(self):
        """Dashboard does not change cycle count."""
        for _ in range(5):
            self.client.get("/api/v1/dashboard")
        final_count = self.repo.count()
        self.assertEqual(self.initial_cycle_count, final_count)

    def test_dashboard_does_not_change_event_count(self):
        """Dashboard does not change event count."""
        for _ in range(5):
            self.client.get("/api/v1/dashboard")
        final_count = self.repo.count_market_events()
        self.assertEqual(self.initial_event_count, final_count)


if __name__ == "__main__":
    unittest.main()