"""
Tests for RuntimeReadService and the HTTP API endpoints.

Uses temporary SQLite databases. Does NOT use the production database.
"""
import unittest
import tempfile
import os
import json
from datetime import datetime, timezone
from pathlib import Path

from application.read_service import RuntimeReadService
from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models import MarketEvent, InstrumentType, EventFamily, EventOwner, PriorityLevel


# ------------------------------------------------------------------
# Helper: create sample MarketEvent dicts directly (not via constructor)
# to avoid enum validation issues when overriding fields for testing.
# ------------------------------------------------------------------

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
    """Create a MarketEvent dict for testing (skips MarketEvent constructor)."""
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
        "signal_timing": "leading",
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


# ======================================================================
# RuntimeReadService tests
# ======================================================================

class TestReadServiceHealth(unittest.TestCase):
    """Test storage health and statistics."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)
        self.service = RuntimeReadService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_health_ok_on_empty_db(self):
        """Health returns ok on empty database."""
        health = self.service.get_storage_health()
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["db_available"])
        self.assertEqual(health["cycle_count"], 0)
        self.assertEqual(health["event_count"], 0)

    def test_health_with_data(self):
        """Health returns correct counts with data."""
        self.repo.save_cycle("cycle_1", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })
        self.repo.save_market_event("cycle_1", _make_event_dict())
        health = self.service.get_storage_health()
        self.assertEqual(health["cycle_count"], 1)
        self.assertEqual(health["event_count"], 1)

    def test_statistics_empty(self):
        """Statistics work on empty database."""
        stats = self.service.get_runtime_statistics()
        self.assertEqual(stats["cycle_count"], 0)
        self.assertEqual(stats["event_count"], 0)
        self.assertIsNone(stats["latest_cycle"])

    def test_statistics_with_latest_cycle(self):
        """Statistics include latest cycle info."""
        self.repo.save_cycle("cycle_x", {
            "execution_time": 2.5, "candidates_count": 10,
            "success_count": 8, "error_count": 1, "report": {}
        })
        stats = self.service.get_runtime_statistics()
        self.assertEqual(stats["cycle_count"], 1)
        self.assertEqual(stats["event_count"], 0)
        self.assertIsNotNone(stats["latest_cycle"])
        self.assertEqual(stats["latest_cycle"]["cycle_id"], "cycle_x")


class TestReadServiceCycles(unittest.TestCase):
    """Test cycle reading operations."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)
        self.service = RuntimeReadService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_get_cycle_found(self):
        """Get existing cycle returns data."""
        self.repo.save_cycle("cycle_42", {
            "execution_time": 1.5, "candidates_count": 7,
            "success_count": 6, "error_count": 0, "report": {"key": "val"}
        })
        cycle = self.service.get_cycle("cycle_42")
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle["cycle_id"], "cycle_42")
        self.assertEqual(cycle["execution_time"], 1.5)

    def test_get_cycle_not_found(self):
        """Get non-existent cycle returns None."""
        cycle = self.service.get_cycle("nonexistent")
        self.assertIsNone(cycle)

    def test_get_latest_cycles_empty(self):
        """Latest cycles returns empty list on empty db."""
        result = self.service.get_latest_cycles(limit=10)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["returned"], 0)

    def test_get_latest_cycles_with_data(self):
        """Latest cycles returns correct summaries."""
        for i in range(5):
            self.repo.save_cycle(f"cycle_{i}", {
                "execution_time": 1.0, "candidates_count": i,
                "success_count": i, "error_count": 0, "report": {}
            })
        result = self.service.get_latest_cycles(limit=10)
        self.assertEqual(result["returned"], 5)

    def test_get_latest_cycles_limit(self):
        """Latest cycles respects limit."""
        for i in range(10):
            self.repo.save_cycle(f"cycle_{i}", {
                "execution_time": 1.0, "candidates_count": i,
                "success_count": i, "error_count": 0, "report": {}
            })
        result = self.service.get_latest_cycles(limit=3)
        self.assertEqual(result["returned"], 3)

    def test_get_latest_cycles_offset(self):
        """Latest cycles respects offset."""
        for i in range(5):
            self.repo.save_cycle(f"cycle_{i}", {
                "execution_time": 1.0, "candidates_count": i,
                "success_count": i, "error_count": 0, "report": {}
            })
        result = self.service.get_latest_cycles(limit=10, offset=3)
        self.assertEqual(result["returned"], 2)


class TestReadServiceMarketEvents(unittest.TestCase):
    """Test MarketEvent reading operations."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = SQLiteHistoryRepository(self.db_path)
        self.service = RuntimeReadService(self.db_path)

        # Add a test cycle
        self.cycle_id = "cycle_test"
        self.repo.save_cycle(self.cycle_id, {
            "execution_time": 1.0, "candidates_count": 4,
            "success_count": 4, "error_count": 0, "report": {}
        })

        # Create test events with specific attributes
        self.events_data = [
            _make_event_dict(event_id="evt_001", ticker="TST", market="NYSE",
                             event_family="VOLUME", event_type="VOLUME_SPIKE",
                             priority_final="HIGH"),
            _make_event_dict(event_id="evt_002", ticker="TST", market="NYSE",
                             event_family="PRICE", event_type="PRICE_SURGE",
                             priority_final="CRITICAL"),
            _make_event_dict(event_id="evt_003", ticker="OTH", market="GPW",
                              event_family="VOLUME", event_type="PRICE_DROP",
                             priority_final="MEDIUM"),
            _make_event_dict(event_id="evt_004", ticker="TST", market="NYSE",
                             event_family="TECHNICAL", event_type="RSI_OVERSOLD",
                             priority_final="LOW"),
        ]
        self.repo.save_market_events(self.cycle_id, self.events_data)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_get_latest_market_events_all(self):
        """Get all market events works."""
        result = self.service.get_latest_market_events(limit=10)
        self.assertEqual(result["returned"], 4)
        self.assertEqual(len(result["items"]), 4)

    def test_get_latest_market_events_limit(self):
        """Get latest respects limit."""
        result = self.service.get_latest_market_events(limit=2)
        self.assertEqual(result["returned"], 2)

    def test_get_latest_market_events_offset(self):
        """Get latest respects offset."""
        result = self.service.get_latest_market_events(limit=10, offset=2)
        self.assertEqual(result["returned"], 2)

    def test_get_market_events_by_ticker(self):
        """Get events by ticker works."""
        result = self.service.get_market_events_by_ticker("TST")
        self.assertEqual(result["returned"], 3)

    def test_get_market_events_by_ticker_offset(self):
        """Get events by ticker respects offset."""
        result = self.service.get_market_events_by_ticker("TST", limit=10, offset=1)
        self.assertEqual(result["returned"], 2)

    def test_get_market_event_by_id_found(self):
        """Get event by ID returns correct event."""
        event = self.service.get_market_event_by_id("evt_001")
        self.assertIsNotNone(event)
        self.assertEqual(event["event_id"], "evt_001")

    def test_get_market_event_by_id_not_found(self):
        """Get event by non-existent ID returns None."""
        event = self.service.get_market_event_by_id("nonexistent")
        self.assertIsNone(event)

    # ------------------------------------------------------------------
    # Filtering tests
    # ------------------------------------------------------------------

    def test_filter_by_ticker(self):
        """Filter by ticker returns only matching events."""
        result = self.service.query_market_events(ticker="TST")
        self.assertEqual(result["returned"], 3)
        for item in result["items"]:
            self.assertEqual(item["ticker"], "TST")

    def test_filter_by_market(self):
        """Filter by market returns only matching events."""
        result = self.service.query_market_events(market="GPW")
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["items"][0]["market"], "GPW")

    def test_filter_by_event_type(self):
        """Filter by event_type returns only matching events."""
        result = self.service.query_market_events(event_type="VOLUME_SPIKE")
        self.assertEqual(result["returned"], 1)

    def test_filter_by_event_family(self):
        """Filter by event_family returns only matching events."""
        result = self.service.query_market_events(event_family="VOLUME")
        self.assertEqual(result["returned"], 2)

    def test_filter_by_priority_final(self):
        """Filter by priority_final returns only matching events."""
        result = self.service.query_market_events(priority_final="CRITICAL")
        self.assertEqual(result["returned"], 1)

    def test_filter_by_instrument_type(self):
        """Filter by instrument_type works."""
        result = self.service.query_market_events(instrument_type="STOCK_USA")
        self.assertEqual(result["returned"], 4)

    def test_filter_multiple_filters(self):
        """Multiple filters combined work correctly."""
        result = self.service.query_market_events(
            ticker="TST",
            event_family="VOLUME",
        )
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["items"][0]["event_id"], "evt_001")

    def test_filter_no_filters_uses_limit(self):
        """No filters just returns latest respecting limit."""
        result = self.service.query_market_events(limit=2)
        self.assertEqual(result["returned"], 2)

    def test_filter_empty_result(self):
        """Filter that matches nothing returns empty list."""
        result = self.service.query_market_events(ticker="NONEXISTENT")
        self.assertEqual(result["returned"], 0)

    # ------------------------------------------------------------------
    # Pagination validation
    # ------------------------------------------------------------------

    def test_default_limit(self):
        """Default limit is 50."""
        result = self.service.get_latest_market_events()
        self.assertEqual(result["limit"], 50)

    def test_max_limit_clamped(self):
        """Limit above max is clamped to 200."""
        result = self.service.get_latest_market_events(limit=999)
        self.assertEqual(result["limit"], 200)

    def test_negative_offset_clamped(self):
        """Negative offset is clamped to 0."""
        result = self.service.get_latest_market_events(offset=-5)
        self.assertEqual(result["offset"], 0)

    def test_negative_limit_uses_default(self):
        """Negative limit uses default."""
        result = self.service.get_latest_market_events(limit=-1)
        self.assertEqual(result["limit"], 50)

    # ------------------------------------------------------------------
    # Internal fields not exposed
    # ------------------------------------------------------------------

    def test_internal_fields_stripped(self):
        """Internal fields (prefixed with _) are not in API responses."""
        result = self.service.get_latest_market_events(limit=1)
        if result["items"]:
            for key in result["items"][0]:
                self.assertFalse(key.startswith("_"),
                                 f"Found internal field: {key}")

    def test_api_does_not_expose_db_path(self):
        """DB path is not exposed in API responses."""
        result = self.service.get_latest_market_events(limit=1)
        for item in result["items"]:
            self.assertNotIn("db_path", json.dumps(item))

    # ------------------------------------------------------------------
    # Persistence across service instances
    # ------------------------------------------------------------------

    def test_persistence_across_service_instances(self):
        """Data remains accessible after creating new service instances."""
        service2 = RuntimeReadService(self.db_path)
        result = service2.get_latest_market_events(limit=10)
        self.assertEqual(result["returned"], 4)

        service3 = RuntimeReadService(self.db_path)
        result = service3.get_latest_market_events(limit=10)
        self.assertEqual(result["returned"], 4)


# Suppress Starlette 1.x deprecation warning emitted during import of
# fastapi.testclient.  The project does not depend on starlette/testclient
# directly; the warning fires when starlette detects httpx v1 on the path.
import warnings
from starlette.exceptions import StarletteDeprecationWarning

warnings.filterwarnings(
    "ignore",
    message=r"Using .*httpx.* with .*starlette\.testclient.* is deprecated",
    category=StarletteDeprecationWarning,
)

# ======================================================================
# HTTP API tests (using TestClient)
# ======================================================================

try:
    from fastapi.testclient import TestClient  # noqa: E402
    from application.api_entrypoint import app  # noqa: E402
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestAPIHealth(unittest.TestCase):
    """Test health endpoint."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.service = RuntimeReadService(self.db_path)

        import application.api_entrypoint as api
        api._read_service = self.service

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_health_returns_200(self):
        """Health endpoint returns 200 with proper fields."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["api"], "running")
        self.assertEqual(data["database"], "available")


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestAPICycles(unittest.TestCase):
    """Test cycle endpoints."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.repo = SQLiteHistoryRepository(self.db_path)
        self.service = RuntimeReadService(self.db_path)

        import application.api_entrypoint as api
        api._read_service = self.service

        self.client = TestClient(app)

        # Add test cycles
        for i in range(3):
            self.repo.save_cycle(f"cycle_{i}", {
                "execution_time": 1.0 * i,
                "candidates_count": 5,
                "success_count": 4,
                "error_count": 0,
                "report": {"idx": i},
            })

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_list_cycles(self):
        """GET /api/v1/cycles returns list."""
        response = self.client.get("/api/v1/cycles")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertTrue(len(data["items"]) >= 1)

    def test_list_cycles_pagination(self):
        """List cycles respects pagination parameters."""
        response = self.client.get("/api/v1/cycles?limit=2")
        data = response.json()
        self.assertEqual(data["returned"], 2)

    def test_get_cycle_found(self):
        """GET /api/v1/cycles/{id} returns 200 for existing cycle."""
        response = self.client.get("/api/v1/cycles/cycle_0")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["cycle_id"], "cycle_0")

    def test_get_cycle_not_found(self):
        """GET /api/v1/cycles/{id} returns 404 for non-existing."""
        response = self.client.get("/api/v1/cycles/nonexistent")
        self.assertEqual(response.status_code, 404)


@unittest.skipIf(not HAS_FASTAPI, "FastAPI not available")
class TestAPIMarketEvents(unittest.TestCase):
    """Test market event endpoints."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.repo = SQLiteHistoryRepository(self.db_path)
        self.repo.save_cycle("test_cycle", {
            "execution_time": 1.0, "candidates_count": 5,
            "success_count": 3, "error_count": 0, "report": {}
        })

        self.events = [
            _make_event_dict(event_id="evt_001", ticker="TST", market="NYSE",
                             event_family="VOLUME", event_type="VOLUME_SPIKE",
                             priority_final="HIGH"),
            _make_event_dict(event_id="evt_002", ticker="OTH", market="GPW",
                             event_family="PRICE", event_type="PRICE_SURGE",
                             priority_final="CRITICAL"),
        ]
        self.repo.save_market_events("test_cycle", self.events)

        self.service = RuntimeReadService(self.db_path)

        import application.api_entrypoint as api
        api._read_service = self.service

        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_list_market_events(self):
        """GET /api/v1/market-events returns list."""
        response = self.client.get("/api/v1/market-events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertEqual(data["returned"], 2)

    def test_list_market_events_filter_ticker(self):
        """Filter by ticker works."""
        response = self.client.get("/api/v1/market-events?ticker=TST")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["returned"], 1)

    def test_list_market_events_filter_market(self):
        """Filter by market works."""
        response = self.client.get("/api/v1/market-events?market=GPW")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["returned"], 1)

    def test_list_market_events_filter_event_type(self):
        """Filter by event_type works."""
        response = self.client.get("/api/v1/market-events?event_type=PRICE_SURGE")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["returned"], 1)

    def test_list_market_events_filter_multiple(self):
        """Multiple filters work together."""
        response = self.client.get(
            "/api/v1/market-events?ticker=OTH&event_family=PRICE"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["returned"], 1)

    def test_get_market_event_found(self):
        """GET /api/v1/market-events/{id} returns 200."""
        response = self.client.get("/api/v1/market-events/evt_001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], "evt_001")

    def test_get_market_event_not_found(self):
        """GET /api/v1/market-events/{id} returns 404."""
        response = self.client.get("/api/v1/market-events/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_ticker_events(self):
        """GET /api/v1/tickers/{ticker}/market-events works."""
        response = self.client.get("/api/v1/tickers/TST/market-events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["returned"], 1)

    def test_ticker_events_normalization(self):
        """Ticker normalization (uppercase) works."""
        response = self.client.get("/api/v1/tickers/tst/market-events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["returned"], 1)

    def test_default_limit(self):
        """Default limit is 50."""
        response = self.client.get("/api/v1/market-events")
        data = response.json()
        self.assertEqual(data["limit"], 50)

    def test_max_limit(self):
        """Limit of 200 is accepted."""
        response = self.client.get("/api/v1/market-events?limit=200")
        self.assertEqual(response.status_code, 200)

    def test_negative_limit_rejected(self):
        """Negative limit returns 422 (FastAPI validation)."""
        response = self.client.get("/api/v1/market-events?limit=-1")
        self.assertEqual(response.status_code, 422)

    def test_excessive_limit_rejected(self):
        """Limit > 200 returns 422."""
        response = self.client.get("/api/v1/market-events?limit=999")
        self.assertEqual(response.status_code, 422)

    def test_negative_offset(self):
        """Negative offset returns 422."""
        response = self.client.get("/api/v1/market-events?offset=-5")
        self.assertEqual(response.status_code, 422)

    def test_no_db_path_in_error(self):
        """Error responses don't contain system paths."""
        response = self.client.get("/api/v1/market-events/nonexistent")
        body_str = response.text.lower()
        self.assertNotIn("c:\\", body_str)
        self.assertNotIn("/home/", body_str)


# ======================================================================
# Smoke test
# ======================================================================

class TestSmokeReadService(unittest.TestCase):
    """Smoke test: create data, read it, verify no writes."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Create data using the repository (write path)
        self.repo = SQLiteHistoryRepository(self.db_path)
        self.repo.save_cycle("smoke_cycle", {
            "execution_time": 10.0,
            "candidates_count": 5,
            "success_count": 3,
            "error_count": 2,
            "report": {"test": True},
        })
        self.repo.save_market_event("smoke_cycle",
                                     _make_event_dict(event_id="smoke_evt_001",
                                                       ticker="SMK",
                                                       event_type="SMOKE_TEST"))

        # Get initial counts
        self.initial_counts = self.repo.get_storage_summary()

        self.service = RuntimeReadService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_smoke_read_does_not_modify_db(self):
        """Reading via ReadService does not change database."""
        # Read various endpoints
        self.service.get_storage_health()
        self.service.get_runtime_statistics()
        self.service.get_cycle("smoke_cycle")
        self.service.get_latest_cycles(limit=10)
        self.service.get_latest_market_events(limit=10)
        self.service.get_market_events_by_ticker("SMK")
        self.service.get_market_event_by_id("smoke_evt_001")

        # Verify counts haven't changed
        final_counts = self.repo.get_storage_summary()
        self.assertEqual(final_counts["cycle_count"], self.initial_counts["cycle_count"])
        self.assertEqual(final_counts["event_count"], self.initial_counts["event_count"])


if __name__ == "__main__":
    unittest.main()