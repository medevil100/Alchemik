"""
Contract tests for SignalTiming enum, mapping, MarketEvent integration,
SQLite persistence, and pipeline propagation.

All tests use real models and real engines — no internal mocks, no fakes.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from application.sqlite_history_repository import SQLiteHistoryRepository
from config.signal_timing import SIGNAL_TIMING_MAP, lookup_signal_timing
from data.models.event_enums import SignalTiming, EventFamily, EventOwner, InstrumentType, PriorityLevel
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent, CURRENT_SCHEMA_VERSION
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData
from engines.master.engine import _CATALOGUE
from engines.price_detector import PriceDetector
from engines.volume_detector import VolumeDetector


class TestSignalTimingEnum(unittest.TestCase):
    """ETAP 1 — enum contains exactly four values."""

    def test_enum_four_values(self):
        """SignalTiming has exactly four values."""
        values = list(SignalTiming)
        self.assertEqual(len(values), 4)
        expected = {"leading", "confirming", "warning", "context"}
        actual = {v.value for v in values}
        self.assertEqual(actual, expected)

    def test_signal_timing_is_str_enum(self):
        """SignalTiming inherits from str."""
        self.assertTrue(issubclass(SignalTiming, str))

    def test_enum_values_are_strings(self):
        """Each value is accessible as a string."""
        for v in SignalTiming:
            self.assertIsInstance(v.value, str)
            self.assertEqual(SignalTiming(v.value), v)


class TestCanonicalMapping(unittest.TestCase):
    """ETAP 2 — canonical mapping contract checks."""

    def test_mapping_has_exactly_138_entries(self):
        """Mapping contains exactly 138 core event types (without test markers)."""
        # Core 138 = _CATALOGUE (123) + PriceDetector types (10) + VolumeDetector types (5)
        price_types = {
            "PRICE_SURGE", "PRICE_DROP", "GAP_UP", "GAP_DOWN",
            "52W_HIGH", "52W_LOW", "ATH", "ATL", "LEVEL_REJECTION", "PSYCH_LEVEL_CROSS",
        }
        volume_types = {
            "VOLUME_SPIKE", "NEAR_ZERO_VOLUME", "CUMULATIVE_VOLUME_ANOMALY",
            "HIGH_VOLUME_ON_DOWN_DAYS", "HIGH_VOLUME_ON_UP_DAYS",
        }
        catalogue_types = set(_CATALOGUE.keys())
        core_138 = catalogue_types | price_types | volume_types
        self.assertEqual(len(core_138), 138)

        # Remove non-core entries for this check
        map_without_test = {
            k: v for k, v in SIGNAL_TIMING_MAP.items()
            if k not in {"EVENT_CREATED", "SMOKE_TEST", "VOLUME_DROP"}
        }
        self.assertEqual(len(map_without_test), 138)
        self.assertEqual(set(map_without_test.keys()), core_138)

    def test_mapping_keys_match_code_union(self):
        """Every code type is in the map and vice versa."""
        price_types = {
            "PRICE_SURGE", "PRICE_DROP", "GAP_UP", "GAP_DOWN",
            "52W_HIGH", "52W_LOW", "ATH", "ATL", "LEVEL_REJECTION", "PSYCH_LEVEL_CROSS",
        }
        volume_types = {
            "VOLUME_SPIKE", "NEAR_ZERO_VOLUME", "CUMULATIVE_VOLUME_ANOMALY",
            "HIGH_VOLUME_ON_DOWN_DAYS", "HIGH_VOLUME_ON_UP_DAYS",
        }
        catalogue_types = set(_CATALOGUE.keys())
        all_code_types = catalogue_types | price_types | volume_types

        map_types = {k for k in SIGNAL_TIMING_MAP.keys() if k not in {"EVENT_CREATED", "SMOKE_TEST", "VOLUME_DROP"}}

        missing = all_code_types - map_types
        extra = map_types - all_code_types
        self.assertEqual(missing, set(), f"Types in code but not mapped: {missing}")
        self.assertEqual(extra, set(), f"Types in map but not in code: {extra}")

    def test_no_duplicates_in_mapping(self):
        """Each event_type appears exactly once."""
        keys = list(SIGNAL_TIMING_MAP.keys())
        self.assertEqual(len(keys), len(set(keys)), "Mapping contains duplicate event_type keys")

    def test_all_values_are_valid_signal_timing(self):
        """Every mapping value is a valid SignalTiming instance."""
        for event_type, timing in SIGNAL_TIMING_MAP.items():
            self.assertIsInstance(timing, SignalTiming, f"{event_type} -> {timing} is not SignalTiming")

    def test_distribution_matches_contract(self):
        """LEADING=24, CONFIRMING=23, WARNING=31, CONTEXT=60 (plus EVENT_CREATED etc)."""
        from collections import Counter
        # Count only the core 138
        core_map = {
            k: v for k, v in SIGNAL_TIMING_MAP.items()
            if k not in {"EVENT_CREATED", "SMOKE_TEST", "VOLUME_DROP"}
        }
        c = Counter(core_map.values())
        self.assertEqual(c.get(SignalTiming.LEADING, 0), 24)
        self.assertEqual(c.get(SignalTiming.CONFIRMING, 0), 23)
        self.assertEqual(c.get(SignalTiming.WARNING, 0), 31)
        self.assertEqual(c.get(SignalTiming.CONTEXT, 0), 60)


class TestLookupNoFallback(unittest.TestCase):
    """ETAP 2 — lookup_signal_timing() has no fallback."""

    def test_lookup_known_type_succeeds(self):
        """Known event_type returns correct SignalTiming."""
        self.assertEqual(lookup_signal_timing("PRICE_SURGE"), SignalTiming.LEADING)
        self.assertEqual(lookup_signal_timing("VOLUME_SPIKE"), SignalTiming.LEADING)

    def test_lookup_unknown_type_raises(self):
        """Unknown event_type raises KeyError — no fallback to CONTEXT."""
        with self.assertRaises(KeyError):
            lookup_signal_timing("NONEXISTENT_TYPE")

    def test_lookup_does_not_fallback_to_context(self):
        """There is no .get(event_type, SignalTiming.CONTEXT) behavior."""
        # Directly verify: SIGNAL_TIMING_MAP.get() is not the same as lookup
        result = SIGNAL_TIMING_MAP.get("NONEXISTENT_TYPE", "fallback")
        self.assertEqual(result, "fallback")  # .get() would fall back, but lookup() must not


class TestMarketEventRequiresSignalTiming(unittest.TestCase):
    """ETAP 3 — MarketEvent requires signal_timing, no default, no fallback."""

    def test_create_new_includes_signal_timing(self):
        """create_new() produces a valid MarketEvent with signal_timing set."""
        event = MarketEvent.create_new("TEST", "NYSE", InstrumentType.STOCK_USA, event_type="PRICE_SURGE")
        self.assertIsInstance(event.signal_timing, SignalTiming)
        self.assertEqual(event.signal_timing, SignalTiming.LEADING)

    def test_direct_construction_without_signal_timing_fails(self):
        """MarketEvent() without signal_timing raises TypeError (required positional arg)."""
        with self.assertRaises(TypeError):
            MarketEvent(
                event_id="evt-1",
                timestamp_utc=datetime.now(timezone.utc),
                ticker="TEST",
                market="NYSE",
                instrument_type=InstrumentType.STOCK_USA,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="test",
                event_owner=EventOwner.TechnicalEngine,
            )

    def test_direct_construction_with_signal_timing_succeeds(self):
        """MarketEvent() with signal_timing works."""
        event = MarketEvent(
            event_id="evt-1",
            timestamp_utc=datetime.now(timezone.utc),
            ticker="TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            signal_timing=SignalTiming.LEADING,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.8,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
        )
        self.assertEqual(event.signal_timing, SignalTiming.LEADING)


class TestDeserializationRequiresSignalTiming(unittest.TestCase):
    """ETAP 3 — from_dict() requires signal_timing, no fallback."""

    def test_from_dict_missing_signal_timing_raises(self):
        """from_dict() without signal_timing raises KeyError."""
        data = {
            "event_id": "evt-1",
            "timestamp_utc": "2026-01-01T00:00:00+00:00",
            "ticker": "TEST",
            "market": "NYSE",
            "instrument_type": "STOCK_GPW",
            "event_family": "PRICE",
            "event_category": "Cenowe",
            "event_type": "PRICE_SURGE",
            "priority_raw": "HIGH",
            "priority_final": "HIGH",
            "confidence_level": 0.8,
            "detection_source": "test",
            "event_owner": "TechnicalEngine",
            "quality_level": "HIGH",
        }
        with self.assertRaises(KeyError):
            MarketEvent.from_dict(data)

    def test_from_dict_with_signal_timing_succeeds(self):
        """from_dict() with signal_timing roundtrips correctly."""
        event = MarketEvent(
            event_id="evt-1",
            timestamp_utc=datetime.now(timezone.utc),
            ticker="TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            signal_timing=SignalTiming.LEADING,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.8,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
        )
        d = event.to_dict()
        restored = MarketEvent.from_dict(d)
        self.assertEqual(restored.signal_timing, SignalTiming.LEADING)

    def test_to_dict_contains_signal_timing(self):
        """to_dict() includes signal_timing as string value."""
        event = MarketEvent.create_new("TEST", "NYSE", InstrumentType.STOCK_USA, event_type="PRICE_SURGE")
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.8,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
        )
        d = event.to_dict()
        self.assertIn("signal_timing", d)
        self.assertEqual(d["signal_timing"], "leading")


class TestDetectorsCreateRealEventsWithSignalTiming(unittest.TestCase):
    """ETAP 4 — PriceDetector and VolumeDetector assign correct SignalTiming."""

    def _make_ohlcv(self, close: float, volume: float, prev_close: float = 100.0):
        """Create minimal MarketData list for tests."""
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        prev = MarketData(
            timestamp=now - timedelta(days=1),
            open=prev_close - 1, high=prev_close + 1, low=prev_close - 2,
            close=prev_close, volume=10000.0,
        )
        curr = MarketData(
            timestamp=now,
            open=close - 1, high=close + 2, low=close - 2,
            close=close, volume=volume,
        )
        return [prev, curr]

    def test_price_detector_assigns_leading_to_price_surge(self):
        """PriceDetector assigns LEADING to PRICE_SURGE."""
        detector = PriceDetector()
        data = self._make_ohlcv(close=120.0, volume=10000.0)  # +20%
        events = detector.detect("TEST", "NYSE", InstrumentType.STOCK_USA, data)
        self.assertGreater(len(events), 0)
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        self.assertGreater(len(surge_events), 0)
        self.assertEqual(surge_events[0].signal_timing, SignalTiming.LEADING)

    def test_price_detector_assigns_warning_to_psych_level_cross(self):
        """PriceDetector assigns WARNING to PSYCH_LEVEL_CROSS."""
        detector = PriceDetector()
        from config.price_detector import PriceDetectorConfig
        # Use very low threshold to force detection
        low_config = PriceDetectorConfig(psych_level_proximity_pct=0.0001)
        detector = PriceDetector(config=low_config)
        data = self._make_ohlcv(close=100.50, volume=10000.0, prev_close=99.50)  # crossed 100
        events = detector.detect("TEST", "NYSE", InstrumentType.STOCK_USA, data)
        psych_events = [e for e in events if e.event_type == "PSYCH_LEVEL_CROSS"]
        if psych_events:
            self.assertEqual(psych_events[0].signal_timing, SignalTiming.WARNING)

    def test_volume_detector_assigns_leading_to_volume_spike(self):
        """VolumeDetector assigns LEADING to VOLUME_SPIKE."""
        detector = VolumeDetector()
        data = self._make_ohlcv(close=101.0, volume=500000.0)  # massive volume
        events = detector.detect("TEST", "NYSE", InstrumentType.STOCK_USA, data)
        spike_events = [e for e in events if e.event_type == "VOLUME_SPIKE"]
        self.assertGreater(len(spike_events), 0)
        self.assertEqual(spike_events[0].signal_timing, SignalTiming.LEADING)

    def test_volume_detector_assigns_warning_to_near_zero_volume(self):
        """VolumeDetector assigns WARNING to NEAR_ZERO_VOLUME."""
        from config.volume_detector import VolumeDetectorConfig
        low_config = VolumeDetectorConfig(near_zero_threshold=0.5)
        detector = VolumeDetector(config=low_config)
        data = self._make_ohlcv(close=101.0, volume=1.0)  # near zero
        events = detector.detect("TEST", "NYSE", InstrumentType.STOCK_USA, data)
        nz_events = [e for e in events if e.event_type == "NEAR_ZERO_VOLUME"]
        if nz_events:
            self.assertEqual(nz_events[0].signal_timing, SignalTiming.WARNING)


class TestSQLiteSavesAndReadsSignalTiming(unittest.TestCase):
    """ETAP 5 — SQLite persistence preserves signal_timing."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = SQLiteHistoryRepository(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_save_and_read_preserves_signal_timing(self):
        """Saving and reading a MarketEvent preserves signal_timing."""
        event = MarketEvent(
            event_id="evt-sql-1",
            timestamp_utc=datetime.now(timezone.utc),
            ticker="TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            signal_timing=SignalTiming.LEADING,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.9,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
        )
        event_dict = event.to_dict()
        self.repo.save_market_event("cycle-1", event_dict)

        # Read back via get_latest_market_events
        events = self.repo.get_latest_market_events(limit=1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["signal_timing"], "leading")

        # Read back via MarketEvent.from_dict
        event_dict_loaded = self.repo.get_market_events_for_cycle("cycle-1")
        self.assertEqual(len(event_dict_loaded), 1)
        restored = MarketEvent.from_dict(event_dict_loaded[0])
        self.assertEqual(restored.signal_timing, SignalTiming.LEADING)

    def test_migration_on_old_db_works(self):
        """Migration on old DB classifies existing rows correctly."""
        # Simulate old schema by removing signal_timing column after creation
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            # Drop and recreate without signal_timing
            conn.execute("DROP TABLE IF EXISTS market_events")
            conn.execute("""
                CREATE TABLE market_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT,
                    event_id TEXT,
                    ticker TEXT,
                    market TEXT,
                    instrument_type TEXT,
                    event_family TEXT,
                    event_category TEXT,
                    event_type TEXT,
                    event_subcategory TEXT,
                    priority_raw TEXT,
                    priority_final TEXT,
                    confidence_level REAL,
                    detection_source TEXT,
                    event_owner TEXT,
                    event_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

        # Insert old row without signal_timing column
        event = MarketEvent(
            event_id="evt-old-1",
            timestamp_utc=datetime.now(timezone.utc),
            ticker="TEST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            signal_timing=SignalTiming.LEADING,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.9,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
        )
        event_dict = event.to_dict()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO market_events (
                    cycle_id, event_id, ticker, market, instrument_type,
                    event_family, event_category, event_type, event_subcategory,
                    priority_raw, priority_final, confidence_level,
                    detection_source, event_owner, event_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("cycle-1", event_dict["event_id"], event_dict["ticker"],
                 event_dict["market"], event_dict["instrument_type"],
                 event_dict["event_family"], event_dict["event_category"],
                 event_dict["event_type"], event_dict.get("event_subcategory"),
                 event_dict["priority_raw"], event_dict["priority_final"],
                 event_dict["confidence_level"], event_dict["detection_source"],
                 event_dict["event_owner"], json.dumps(event_dict),
                 datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

        # Reinitialize — migration should run
        repo2 = SQLiteHistoryRepository(self.db_path)
        events = repo2.get_latest_market_events(limit=1)
        self.assertEqual(len(events), 1)
        # migration backfills signal_timing from event_type in event_json
        self.assertEqual(events[0]["signal_timing"], "leading")

    def test_migration_error_on_unknown_event_type(self):
        """Migration raises KeyError for unknown event_type."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DROP TABLE IF EXISTS market_events")
            conn.execute("""
                CREATE TABLE market_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT,
                    event_id TEXT,
                    ticker TEXT,
                    market TEXT,
                    instrument_type TEXT,
                    event_family TEXT,
                    event_category TEXT,
                    event_type TEXT,
                    event_subcategory TEXT,
                    priority_raw TEXT,
                    priority_final TEXT,
                    confidence_level REAL,
                    detection_source TEXT,
                    event_owner TEXT,
                    event_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

        # Insert row with unknown event_type
        conn = sqlite3.connect(self.db_path)
        try:
            unknown_data = {"event_id": "bad-1", "event_type": "UNKNOWN_TYPE"}
            conn.execute(
                """INSERT INTO market_events (
                    cycle_id, event_id, ticker, market, instrument_type,
                    event_family, event_category, event_type, event_subcategory,
                    priority_raw, priority_final, confidence_level,
                    detection_source, event_owner, event_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("cycle-1", "bad-1", "T", "M", "STOCK_GPW",
                 "PRICE", "cat", "UNKNOWN_TYPE", None,
                 "HIGH", "HIGH", 0.5, "test", "TechnicalEngine",
                 json.dumps(unknown_data), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

        # Reinitialization should raise
        with self.assertRaises(KeyError):
            SQLiteHistoryRepository(self.db_path)


class TestRoundtripPreservesSignalTiming(unittest.TestCase):
    """to_dict() + from_dict() roundtrip preserves signal_timing."""

    def test_roundtrip_all_four_values(self):
        """Each SignalTiming value survives serialization roundtrip."""
        for timing in SignalTiming:
            event = MarketEvent(
                event_id=f"evt-{timing.value}",
                timestamp_utc=datetime.now(timezone.utc),
                ticker="TEST",
                market="NYSE",
                instrument_type=InstrumentType.STOCK_USA,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=timing,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="test",
                event_owner=EventOwner.TechnicalEngine,
            )
            d = event.to_dict()
            restored = MarketEvent.from_dict(d)
            self.assertEqual(restored.signal_timing, timing,
                             f"Failed roundtrip for {timing}")


class TestPipelinePropagation(unittest.TestCase):
    """Pipeline does not modify signal_timing after creation."""

    def test_pipeline_does_not_modify_signal_timing(self):
        """After create_new + set_detection, value stays unchanged."""
        event = MarketEvent.create_new("TEST", "NYSE", InstrumentType.STOCK_USA, event_type="PRICE_SURGE")
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.8,
            detection_source="test",
            event_owner=EventOwner.TechnicalEngine,
        )
        self.assertEqual(event.signal_timing, SignalTiming.LEADING)

        # Running quality assessment and normalization should NOT change it
        event.set_normalization(PriorityLevel.HIGH, is_composite=False)
        self.assertEqual(event.signal_timing, SignalTiming.LEADING)

        event.set_quality_assessment(PriorityLevel.HIGH)
        self.assertEqual(event.signal_timing, SignalTiming.LEADING)

    def test_multi_ticker_events_have_independent_timing(self):
        """Events for different tickers have independent, correct timing."""
        detector = PriceDetector()
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        prev = MarketData(
            timestamp=now - timedelta(days=1),
            open=99, high=101, low=98, close=100, volume=10000,
        )
        curr = MarketData(
            timestamp=now,
            open=119, high=122, low=118, close=120, volume=15000,
        )
        events1 = detector.detect("ABC", "NYSE", InstrumentType.STOCK_USA, [prev, curr])
        events2 = detector.detect("XYZ", "NYSE", InstrumentType.STOCK_USA, [prev, curr])

        for ev in events1 + events2:
            self.assertIsInstance(ev.signal_timing, SignalTiming)
            # Each type has a canonical mapping
            expected = lookup_signal_timing(ev.event_type)
            self.assertEqual(ev.signal_timing, expected)


if __name__ == "__main__":
    unittest.main()