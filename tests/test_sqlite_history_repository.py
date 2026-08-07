import unittest
import tempfile
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models import SignalTiming, MarketEvent, InstrumentType, EventFamily, EventOwner, PriorityLevel


class TestSQLiteHistoryRepository(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for the database
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db_file.name
        self.temp_db_file.close()

        # Initialize the repository with the temporary database
        self.repo = SQLiteHistoryRepository(self.db_path)

        # Sample cycle data
        self.cycle_id = "test_cycle_1"
        self.cycle_data = {
            "execution_time": 123.45,
            "candidates_count": 10,
            "success_count": 8,
            "error_count": 2,
            "report": {"key": "value"}
        }

    def tearDown(self):
        # Ensure all connections are closed
        if hasattr(self, 'repo'):
            pass  # SQLiteHistoryRepository uses short-lived connections
        # Clean up the temporary file
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass  # Skip if file is still locked

    # ------------------------------------------------------------------
    # Original cycle tests
    # ------------------------------------------------------------------

    def test_save_and_get_cycle(self):
        """Test saving and retrieving a cycle."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        retrieved_data = self.repo.get_cycle(self.cycle_id)

        self.assertEqual(retrieved_data["cycle_id"], self.cycle_id)
        self.assertEqual(retrieved_data["execution_time"], self.cycle_data["execution_time"])
        self.assertEqual(retrieved_data["candidates_count"], self.cycle_data["candidates_count"])
        self.assertEqual(retrieved_data["success_count"], self.cycle_data["success_count"])
        self.assertEqual(retrieved_data["error_count"], self.cycle_data["error_count"])
        self.assertEqual(retrieved_data["report"], self.cycle_data["report"])
        self.assertIsNotNone(retrieved_data["created_at"])

    def test_list_cycles(self):
        """Test listing all cycles (newest first, with limit)."""
        cycle_ids = ["cycle_1", "cycle_2"]
        for cycle_id in cycle_ids:
            self.repo.save_cycle(cycle_id, self.cycle_data)

        listed_cycles = self.repo.list_cycles(limit=10)
        # Should contain both but in reverse order
        self.assertIn("cycle_1", listed_cycles)
        self.assertIn("cycle_2", listed_cycles)
        self.assertEqual(len(listed_cycles), 2)

    def test_delete_cycle(self):
        """Test deleting a cycle."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        self.repo.delete_cycle(self.cycle_id)
        self.assertIsNone(self.repo.get_cycle(self.cycle_id))

    def test_count(self):
        """Test counting cycles."""
        self.assertEqual(self.repo.count(), 0)
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        self.assertEqual(self.repo.count(), 1)

    def test_empty_repository(self):
        """Test operations on an empty repository."""
        self.assertEqual(self.repo.count(), 0)
        self.assertEqual(self.repo.list_cycles(), [])
        self.assertIsNone(self.repo.get_cycle("nonexistent_cycle"))

    def test_overwrite_cycle(self):
        """Test overwriting a cycle with the same ID."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)

        updated_data = {
            "execution_time": 678.90,
            "candidates_count": 20,
            "success_count": 15,
            "error_count": 5,
            "report": {"key": "updated_value"}
        }
        self.repo.save_cycle(self.cycle_id, updated_data)

        retrieved_data = self.repo.get_cycle(self.cycle_id)
        self.assertEqual(retrieved_data["execution_time"], updated_data["execution_time"])
        self.assertEqual(retrieved_data["report"], updated_data["report"])

    def test_persistence(self):
        """Test data persistence after repository reinitialization."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)

        new_repo = SQLiteHistoryRepository(self.db_path)
        retrieved_data = new_repo.get_cycle(self.cycle_id)
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data["cycle_id"], self.cycle_id)

    def test_datetime_serialization(self):
        """Test datetime serialization and deserialization."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        retrieved_data = self.repo.get_cycle(self.cycle_id)

        try:
            datetime.fromisoformat(retrieved_data["created_at"])
        except ValueError:
            self.fail("created_at is not a valid ISO 8601 datetime string")

    # ------------------------------------------------------------------
    # NEW: WAL mode test
    # ------------------------------------------------------------------

    def test_wal_mode_enabled(self):
        """Test that WAL journal mode is active."""
        summary = self.repo.get_storage_summary()
        self.assertEqual(summary["journal_mode"], "wal")

    # ------------------------------------------------------------------
    # NEW: MarketEvent persistence tests
    # ------------------------------------------------------------------

    def _make_sample_market_event(self, ticker="TEST", event_type="VOLUME_SPIKE") -> MarketEvent:
        """Helper to create a deterministic MarketEvent."""
        return MarketEvent(
            event_id=f"evt_{ticker}_{event_type}",
            timestamp_utc=datetime.now(timezone.utc),
            ticker=ticker,
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            event_family=EventFamily.VOLUME,
            event_category="VolumeAnomaly",
            event_type=event_type,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.85,
            detection_source="VolumeDetector",
            event_owner=EventOwner.TechnicalEngine,
            signal_timing=SignalTiming.LEADING,
            schema_version="1.0",
        )

    def test_save_and_get_market_events(self):
        """Test saving and retrieving MarketEvents."""
        event = self._make_sample_market_event()
        event_dict = event.to_dict()

        # Save
        self.repo.save_market_event(self.cycle_id, event_dict)

        # Count
        self.assertEqual(self.repo.count_market_events(), 1)

        # Retrieve for cycle
        events = self.repo.get_market_events_for_cycle(self.cycle_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], event.event_id)
        self.assertEqual(events[0]["ticker"], event.ticker)
        self.assertEqual(events[0]["event_type"], event.event_type)

    def test_save_market_events_batch(self):
        """Test saving multiple MarketEvents in batch."""
        events = [
            self._make_sample_market_event("TEST", "VOLUME_SPIKE"),
            self._make_sample_market_event("XYZ.WA", "PRICE_SURGE"),
        ]
        events_data = [ev.to_dict() for ev in events]

        self.repo.save_market_events(self.cycle_id, events_data)
        self.assertEqual(self.repo.count_market_events(), 2)

        # Retrieve latest
        latest = self.repo.get_latest_market_events(limit=5)
        self.assertEqual(len(latest), 2)

    def test_get_market_events_by_ticker(self):
        """Test retrieving MarketEvents by ticker."""
        events = [
            self._make_sample_market_event("AAPL", "VOLUME_SPIKE"),
            self._make_sample_market_event("MSFT", "PRICE_SURGE"),
            self._make_sample_market_event("AAPL", "PRICE_DROP"),
        ]
        events_data = [ev.to_dict() for ev in events]

        self.repo.save_market_events(self.cycle_id, events_data)

        aapl_events = self.repo.get_market_events_by_ticker("AAPL")
        self.assertEqual(len(aapl_events), 2)

        msft_events = self.repo.get_market_events_by_ticker("MSFT")
        self.assertEqual(len(msft_events), 1)

    def test_market_events_deleted_with_cycle(self):
        """Test that MarketEvents are deleted when their cycle is deleted."""
        event = self._make_sample_market_event()
        self.repo.save_market_event(self.cycle_id, event.to_dict())
        self.assertEqual(self.repo.count_market_events(), 1)

        self.repo.delete_cycle(self.cycle_id)
        self.assertEqual(self.repo.count_market_events(), 0)

    def test_market_event_persistence_after_restart(self):
        """Test that MarketEvents survive repository reinitialization."""
        event = self._make_sample_market_event()
        self.repo.save_market_event(self.cycle_id, event.to_dict())

        # Reinitialize
        new_repo = SQLiteHistoryRepository(self.db_path)
        self.assertEqual(new_repo.count_market_events(), 1)

        events = new_repo.get_market_events_for_cycle(self.cycle_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], event.event_id)

    def test_latest_market_events_limit(self):
        """Test that get_latest_market_events respects the limit."""
        events = [
            self._make_sample_market_event(f"TICKER{i}", "EVENT")
            for i in range(10)
        ]
        events_data = [ev.to_dict() for ev in events]
        self.repo.save_market_events(self.cycle_id, events_data)

        latest = self.repo.get_latest_market_events(limit=3)
        self.assertLessEqual(len(latest), 3)

    def test_latest_market_events_with_offset(self):
        """Test that get_latest_market_events respects offset."""
        events = [
            self._make_sample_market_event(f"TICK{i}", "EVENT")
            for i in range(5)
        ]
        events_data = [ev.to_dict() for ev in events]
        self.repo.save_market_events(self.cycle_id, events_data)

        all_events = self.repo.get_latest_market_events(limit=10, offset=0)
        self.assertEqual(len(all_events), 5)

        some_events = self.repo.get_latest_market_events(limit=10, offset=2)
        self.assertEqual(len(some_events), 3)

        no_events = self.repo.get_latest_market_events(limit=10, offset=10)
        self.assertEqual(len(no_events), 0)

    def test_get_market_event_by_id(self):
        """Test retrieving a single MarketEvent by event_id — returns MarketEvent object."""
        event = self._make_sample_market_event("TICK_X", "EVENT_ID_TEST")
        self.repo.save_market_event(self.cycle_id, event.to_dict())

        retrieved = self.repo.get_market_event_by_id(event.event_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.event_id, event.event_id)
        self.assertEqual(retrieved.ticker, event.ticker)
        self.assertEqual(retrieved.event_type, event.event_type)

    def test_get_market_event_by_id_not_found(self):
        """Test that get_market_event_by_id returns None for non-existent ID."""
        result = self.repo.get_market_event_by_id("nonexistent_event_id")
        self.assertIsNone(result)

    def test_get_market_events_by_ticker_with_offset(self):
        """Test retrieving MarketEvents by ticker with offset."""
        events = [
            self._make_sample_market_event("TICK_A", "EVENT_1"),
            self._make_sample_market_event("TICK_A", "EVENT_2"),
            self._make_sample_market_event("TICK_A", "EVENT_3"),
        ]
        events_data = [ev.to_dict() for ev in events]
        self.repo.save_market_events(self.cycle_id, events_data)

        all_events = self.repo.get_market_events_by_ticker("TICK_A", limit=10, offset=0)
        self.assertEqual(len(all_events), 3)

        some_events = self.repo.get_market_events_by_ticker("TICK_A", limit=10, offset=1)
        self.assertEqual(len(some_events), 2)

    def test_market_events_empty_cycle(self):
        """Test that non-existent cycle returns empty list."""
        events = self.repo.get_market_events_for_cycle("nonexistent")
        self.assertEqual(events, [])

    # ------------------------------------------------------------------
    # NEW: Cycle list with limit
    # ------------------------------------------------------------------

    def test_list_cycles_with_limit(self):
        """Test that list_cycles respects limit and offset."""
        for i in range(10):
            self.repo.save_cycle(f"cycle_{i}", self.cycle_data)

        all_ids = self.repo.list_cycles(limit=100)
        self.assertEqual(len(all_ids), 10)

        limited = self.repo.list_cycles(limit=3)
        self.assertEqual(len(limited), 3)

    def test_list_cycle_summaries(self):
        """Test that list_cycle_summaries returns metadata without full report."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)

        summaries = self.repo.list_cycle_summaries(limit=5)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["cycle_id"], self.cycle_id)
        self.assertIn("execution_time", summaries[0])
        self.assertNotIn("report_json", summaries[0])

    def test_list_cycle_summaries_with_offset(self):
        """Test that list_cycle_summaries respects offset."""
        for i in range(5):
            self.repo.save_cycle(f"cycle_{i}", self.cycle_data)

        all_summaries = self.repo.list_cycle_summaries(limit=10, offset=0)
        self.assertEqual(len(all_summaries), 5)

        some_summaries = self.repo.list_cycle_summaries(limit=10, offset=3)
        self.assertEqual(len(some_summaries), 2)

        no_summaries = self.repo.list_cycle_summaries(limit=10, offset=10)
        self.assertEqual(len(no_summaries), 0)

    # ------------------------------------------------------------------
    # NEW: Storage summary
    # ------------------------------------------------------------------

    def test_storage_summary(self):
        """Test that storage summary returns correct metadata."""
        # Empty repo
        summary = self.repo.get_storage_summary()
        self.assertEqual(summary["cycle_count"], 0)
        self.assertEqual(summary["event_count"], 0)
        self.assertEqual(summary["journal_mode"], "wal")
        self.assertEqual(summary["schema_version"], 2)

        # With data
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        event = self._make_sample_market_event()
        self.repo.save_market_event(self.cycle_id, event.to_dict())

        summary = self.repo.get_storage_summary()
        self.assertEqual(summary["cycle_count"], 1)
        self.assertEqual(summary["event_count"], 1)

    # ------------------------------------------------------------------
    # NEW: Schema version idempotency
    # ------------------------------------------------------------------

    def test_reinitialization_idempotent(self):
        """Test that creating a second instance on same DB does not break schema."""
        self.repo.save_cycle(self.cycle_id, self.cycle_data)

        # Second instance
        repo2 = SQLiteHistoryRepository(self.db_path)
        # Should still read data
        data = repo2.get_cycle(self.cycle_id)
        self.assertIsNotNone(data)

        # Third instance
        repo3 = SQLiteHistoryRepository(self.db_path)
        data = repo3.get_cycle(self.cycle_id)
        self.assertIsNotNone(data)


if __name__ == "__main__":
    unittest.main()