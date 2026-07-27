"""
Unit tests for the CompositeEvent model (ETAP 7.3 — Krok 1).

Tests cover:
- Correct object creation via constructor and factory
- Field validation (required fields, confidence range, component consistency)
- Serialization (to_dict / from_dict round-trip)
- Equality and inequality
- Hashing
- Edge cases (empty component list, duplicate IDs, boundary values)
"""

import unittest
from datetime import datetime, timezone
from data.models.composite_event import CompositeEvent
from data.models.event_enums import EventFamily, PriorityLevel


class TestCompositeEventCreation(unittest.TestCase):
    """Tests for creating CompositeEvent instances."""

    def test_create_with_minimal_fields(self):
        """CompositeEvent should be creatable with all required fields."""
        now = datetime.now(timezone.utc)
        event_ids = ["evt-001", "evt-002"]
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=event_ids,
            priority_final=PriorityLevel.HIGH,
            event_family=EventFamily.PRICE,
            component_count=2,
        )
        self.assertEqual(ce.composite_id, "comp-001")
        self.assertEqual(ce.ticker, "XYZ.WA")
        self.assertEqual(ce.priority_final, PriorityLevel.HIGH)
        self.assertEqual(ce.event_family, EventFamily.PRICE)
        self.assertTrue(ce.is_composite)
        self.assertEqual(ce.component_count, 2)

    def test_create_with_all_fields(self):
        """CompositeEvent should accept all optional fields."""
        now = datetime.now(timezone.utc)
        event_ids = ["evt-001", "evt-002", "evt-003"]
        ce = CompositeEvent(
            composite_id="comp-002",
            timestamp_utc=now,
            ticker="ABC.NY",
            component_event_ids=event_ids,
            priority_final=PriorityLevel.CRITICAL,
            event_family=EventFamily.VOLUME,
            event_type="COMPOSITE_MULTI_EVENT",
            confidence_level=0.85,
            component_count=3,
            is_composite=True,
            metadata={"source": "composer"},
        )
        self.assertEqual(ce.confidence_level, 0.85)
        self.assertEqual(ce.metadata["source"], "composer")
        self.assertEqual(ce.event_type, "COMPOSITE_MULTI_EVENT")

    def test_factory_method_create(self):
        """The create() factory should produce a valid CompositeEvent."""
        event_ids = ["evt-001", "evt-002", "evt-003"]
        now = datetime.now(timezone.utc)
        ce = CompositeEvent.create(
            ticker="XYZ.WA",
            component_event_ids=event_ids,
            priority_final=PriorityLevel.HIGH,
            event_family=EventFamily.PRICE,
            confidence_level=0.75,
            timestamp_utc=now,
        )
        self.assertTrue(ce.is_composite)
        self.assertEqual(ce.ticker, "XYZ.WA")
        self.assertEqual(ce.component_count, 3)
        self.assertEqual(ce.component_event_ids, event_ids)
        self.assertEqual(ce.priority_final, PriorityLevel.HIGH)
        self.assertEqual(ce.event_family, EventFamily.PRICE)
        self.assertEqual(ce.confidence_level, 0.75)
        self.assertEqual(ce.timestamp_utc, now)

    def test_factory_less_than_two_components_raises(self):
        """create() should raise ValueError when fewer than 2 component IDs."""
        with self.assertRaises(ValueError) as ctx:
            CompositeEvent.create(
                ticker="XYZ.WA",
                component_event_ids=["evt-001"],
                priority_final=PriorityLevel.HIGH,
                event_family=EventFamily.PRICE,
            )
        self.assertIn("at least 2", str(ctx.exception))

    def test_factory_empty_components_raises(self):
        """create() should raise ValueError when component list is empty."""
        with self.assertRaises(ValueError) as ctx:
            CompositeEvent.create(
                ticker="XYZ.WA",
                component_event_ids=[],
                priority_final=PriorityLevel.HIGH,
                event_family=EventFamily.PRICE,
            )
        self.assertIn("at least 2", str(ctx.exception))


class TestCompositeEventValidation(unittest.TestCase):
    """Tests for field validation."""

    def test_empty_composite_id_raises(self):
        """Empty composite_id should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                component_count=2,
            )

    def test_empty_ticker_raises(self):
        """Empty ticker should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="",
                component_event_ids=["a", "b"],
                component_count=2,
            )

    def test_none_timestamp_raises(self):
        """None timestamp should raise ValueError."""
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=None,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                component_count=2,
            )

    def test_none_priority_raises(self):
        """None priority_final should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                priority_final=None,
                component_count=2,
            )

    def test_none_event_family_raises(self):
        """None event_family should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                event_family=None,
                component_count=2,
            )

    def test_empty_event_type_raises(self):
        """Empty event_type should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                event_type="",
                component_count=2,
            )

    def test_confidence_below_zero_raises(self):
        """confidence_level < 0.0 should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                confidence_level=-0.1,
                component_count=2,
            )

    def test_confidence_above_one_raises(self):
        """confidence_level > 1.0 should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                confidence_level=1.01,
                component_count=2,
            )

    def test_confidence_boundary_zero(self):
        """confidence_level = 0.0 should be accepted."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            confidence_level=0.0,
            component_count=2,
        )
        self.assertEqual(ce.confidence_level, 0.0)

    def test_confidence_boundary_one(self):
        """confidence_level = 1.0 should be accepted."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            confidence_level=1.0,
            component_count=2,
        )
        self.assertEqual(ce.confidence_level, 1.0)

    def test_component_count_mismatch_raises(self):
        """component_count not matching len(component_event_ids) should raise."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b", "c"],
                component_count=2,
            )

    def test_duplicate_component_ids_raises(self):
        """Duplicate component_event_ids should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "a"],
                component_count=2,
            )

    def test_is_composite_false_raises(self):
        """is_composite=False should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", "b"],
                component_count=2,
                is_composite=False,
            )

    def test_component_ids_not_list_raises(self):
        """Non-list component_event_ids should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids="not-a-list",
                component_count=2,
            )

    def test_component_ids_contain_empty_string_raises(self):
        """Component ID being an empty string should raise ValueError."""
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            CompositeEvent(
                composite_id="comp-001",
                timestamp_utc=now,
                ticker="XYZ.WA",
                component_event_ids=["a", ""],
                component_count=2,
            )


class TestCompositeEventSerialization(unittest.TestCase):
    """Tests for to_dict() and from_dict() round-trip."""

    def test_round_trip_minimal(self):
        """Minimal CompositeEvent should survive to_dict → from_dict."""
        now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["evt-001", "evt-002"],
            priority_final=PriorityLevel.HIGH,
            event_family=EventFamily.PRICE,
            component_count=2,
        )
        data = ce.to_dict()
        restored = CompositeEvent.from_dict(data)
        self.assertEqual(ce, restored)

    def test_round_trip_full(self):
        """Full CompositeEvent should survive to_dict → from_dict."""
        now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-002",
            timestamp_utc=now,
            ticker="ABC.NY",
            component_event_ids=["evt-001", "evt-002", "evt-003"],
            priority_final=PriorityLevel.CRITICAL,
            event_family=EventFamily.VOLUME,
            event_type="COMPOSITE_MULTI_EVENT",
            confidence_level=0.95,
            component_count=3,
            is_composite=True,
            metadata={"source": "test"},
        )
        data = ce.to_dict()
        restored = CompositeEvent.from_dict(data)
        self.assertEqual(ce, restored)

    def test_to_dict_types(self):
        """to_dict() should return appropriate types."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-003",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["evt-001", "evt-002"],
            priority_final=PriorityLevel.MEDIUM,
            event_family=EventFamily.TECHNICAL,
            confidence_level=0.5,
            component_count=2,
        )
        data = ce.to_dict()
        self.assertIsInstance(data["composite_id"], str)
        self.assertIsInstance(data["timestamp_utc"], str)
        self.assertIsInstance(data["ticker"], str)
        self.assertIsInstance(data["component_event_ids"], list)
        self.assertIsInstance(data["priority_final"], str)
        self.assertIsInstance(data["event_family"], str)
        self.assertIsInstance(data["confidence_level"], float)
        self.assertIsInstance(data["component_count"], int)
        self.assertIsInstance(data["is_composite"], bool)

    def test_to_dict_enum_values_are_strings(self):
        """Enum fields should serialize as their string values."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-004",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["evt-001", "evt-002"],
            priority_final=PriorityLevel.CRITICAL,
            event_family=EventFamily.CORPORATE,
            component_count=2,
        )
        data = ce.to_dict()
        self.assertEqual(data["priority_final"], "CRITICAL")
        self.assertEqual(data["event_family"], "CORPORATE")

    def test_from_dict_restores_enum_values(self):
        """from_dict() should restore enums from string values."""
        now_iso = "2026-07-24T12:00:00+00:00"
        data = {
            "composite_id": "comp-005",
            "timestamp_utc": now_iso,
            "ticker": "XYZ.WA",
            "component_event_ids": ["evt-001", "evt-002"],
            "priority_final": "CRITICAL",
            "event_family": "CORPORATE",
            "event_type": "COMPOSITE_MULTI_EVENT",
            "confidence_level": 0.8,
            "component_count": 2,
            "is_composite": True,
            "metadata": {},
        }
        ce = CompositeEvent.from_dict(data)
        self.assertEqual(ce.priority_final, PriorityLevel.CRITICAL)
        self.assertEqual(ce.event_family, EventFamily.CORPORATE)

    def test_from_dict_defaults(self):
        """from_dict() should apply defaults for missing optional fields."""
        now_iso = "2026-07-24T12:00:00+00:00"
        data = {
            "composite_id": "comp-006",
            "timestamp_utc": now_iso,
            "ticker": "XYZ.WA",
            "component_event_ids": ["evt-001", "evt-002"],
            "priority_final": "HIGH",
            "event_family": "PRICE",
        }
        ce = CompositeEvent.from_dict(data)
        self.assertEqual(ce.event_type, "COMPOSITE_MULTI_EVENT")
        self.assertEqual(ce.confidence_level, 0.0)
        self.assertTrue(ce.is_composite)
        self.assertEqual(ce.metadata, {})


class TestCompositeEventEquality(unittest.TestCase):
    """Tests for equality and hashing."""

    def test_equal_objects(self):
        """Two CompositeEvents with identical fields should be equal."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertEqual(ce1, ce2)

    def test_different_id_not_equal(self):
        """Different composite_id should make objects unequal."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-002",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertNotEqual(ce1, ce2)

    def test_different_ticker_not_equal(self):
        """Different ticker should make objects unequal."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="ABC.NY",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertNotEqual(ce1, ce2)

    def test_different_priority_not_equal(self):
        """Different priority_final should make objects unequal."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            priority_final=PriorityLevel.HIGH,
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            priority_final=PriorityLevel.LOW,
            component_count=2,
        )
        self.assertNotEqual(ce1, ce2)

    def test_different_components_not_equal(self):
        """Different component lists should make objects unequal."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "c"],
            component_count=2,
        )
        self.assertNotEqual(ce1, ce2)

    def test_equality_against_non_composite(self):
        """Equality check with non-CompositeEvent should return NotImplemented."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertNotEqual(ce, "not-a-composite-event")

    def test_hash_same_id_equal(self):
        """Objects with the same composite_id should have the same hash."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="ABC.NY",
            component_event_ids=["x", "y"],
            priority_final=PriorityLevel.CRITICAL,
            component_count=2,
        )
        self.assertEqual(hash(ce1), hash(ce2))

    def test_hash_different_id_different(self):
        """Objects with different composite_ids should (likely) have different hash."""
        now = datetime.now(timezone.utc)
        ce1 = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        ce2 = CompositeEvent(
            composite_id="comp-002",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertNotEqual(hash(ce1), hash(ce2))


class TestCompositeEventEdgeCases(unittest.TestCase):
    """Tests for edge cases."""

    def test_many_components(self):
        """CompositeEvent with many component IDs should be valid."""
        now = datetime.now(timezone.utc)
        ids = [f"evt-{i:03d}" for i in range(100)]
        ce = CompositeEvent(
            composite_id="comp-large",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=ids,
            component_count=100,
        )
        self.assertEqual(ce.component_count, 100)

    def test_default_metadata_is_empty_dict(self):
        """Default metadata should be an empty dict."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertEqual(ce.metadata, {})

    def test_default_is_composite_true(self):
        """Default is_composite should be True."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b"],
            component_count=2,
        )
        self.assertTrue(ce.is_composite)

    def test_factory_defaults_timestamp(self):
        """Factory create() with no timestamp should generate current UTC time."""
        before = datetime.now(timezone.utc)
        ce = CompositeEvent.create(
            ticker="XYZ.WA",
            component_event_ids=["evt-001", "evt-002"],
            priority_final=PriorityLevel.HIGH,
            event_family=EventFamily.PRICE,
        )
        after = datetime.now(timezone.utc)
        self.assertIsNotNone(ce.timestamp_utc)
        self.assertLessEqual(before, ce.timestamp_utc)
        self.assertLessEqual(ce.timestamp_utc, after)

    def test_repr(self):
        """__repr__ should include key fields."""
        now = datetime.now(timezone.utc)
        ce = CompositeEvent(
            composite_id="comp-001",
            timestamp_utc=now,
            ticker="XYZ.WA",
            component_event_ids=["a", "b", "c"],
            priority_final=PriorityLevel.HIGH,
            event_family=EventFamily.PRICE,
            component_count=3,
        )
        rep = repr(ce)
        self.assertIn("CompositeEvent", rep)
        self.assertIn("composite_id='comp-001'", rep)
        self.assertIn("ticker='XYZ.WA'", rep)
        self.assertIn("components=3", rep)
        self.assertIn("priority_final=HIGH", rep)


if __name__ == "__main__":
    unittest.main()