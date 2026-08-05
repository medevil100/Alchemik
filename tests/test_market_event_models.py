"""
Tests for the MarketEvent model and its supporting models.

Covers:
1. Correct creation of a complete MarketEvent
2. Rejection of data without required fields
3. Correct enum behavior
4. Correct addition of HistoryEntry
5. Correct lifecycle stage transitions
6. Correct serialization to JSON
7. Correct reconstruction of object from JSON
8. Preservation of optional values
9. Preservation of contract version
10. No dependency of models on engines/
"""

import json
import uuid
from datetime import datetime, timezone

import pytest

from config.signal_timing import lookup_signal_timing
from data.models.event_enums import (
    EventFamily,
    EventOwner,
    InstrumentType,
    PriorityLevel,
    SignalTiming,
)
from data.models.history_entry import HistoryEntry
from data.models.market_event import CURRENT_SCHEMA_VERSION, MarketEvent
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def sample_price_data():
    return PriceData(
        open=100.0,
        high=112.5,
        low=98.0,
        close=112.3,
        prev_close=100.0,
        change_pct=12.3,
        change_abs=12.3,
    )


@pytest.fixture
def sample_volume_data():
    return VolumeData(
        current_volume=420000.0,
        avg_volume=100000.0,
        volume_ratio=4.2,
        direction="up",
    )


@pytest.fixture
def timestamp_now():
    return datetime(2026, 7, 18, 14, 32, 5, tzinfo=timezone.utc)


# ------------------------------------------------------------------
# 1. Correct creation of a complete MarketEvent
# ------------------------------------------------------------------


class TestMarketEventCreation:
    """Tests for correct MarketEvent creation."""

    def test_create_new_with_factory(self, timestamp_now):
        """MarketEvent.create_new() creates a valid event with Stage 1 fields."""
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        assert isinstance(event.event_id, str)
        assert len(event.event_id) == 36  # UUID v4
        assert event.timestamp_utc == timestamp_now
        assert event.ticker == "XYZ.WA"
        assert event.market == "GPW"
        assert event.instrument_type == InstrumentType.STOCK_GPW
        assert event.schema_version == CURRENT_SCHEMA_VERSION
        assert len(event.history) == 1
        assert event.history[0].module == "MarketScanner"

    def test_create_new_without_timestamp_generates_now(self):
        """create_new without timestamp_utc uses current UTC time."""
        before = datetime.now(timezone.utc)
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        after = datetime.now(timezone.utc)
        assert before <= event.timestamp_utc <= after

    def test_complete_event_with_all_context_fields(self, timestamp_now, sample_price_data, sample_volume_data):
        """A fully populated MarketEvent has all required fields."""
        event = MarketEvent(
            event_id=str(uuid.uuid4()),
            timestamp_utc=timestamp_now,
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            signal_timing=SignalTiming.LEADING,
            event_subcategory="Ruchy gwałtowne",
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            price_data=sample_price_data,
            volume_data=sample_volume_data,
            technical_context={"RSI": 28.5, "MACD_line": -0.32},
            fundamental_context={"PE_ratio": 12.5},
            news_context=[{"headline": "Test news"}],
            ai_context={"summary": "Test AI summary"},
            tavily_context={"results_count": 3},
            metadata={"key": "value"},
            composite_events=[],
            is_composite=False,
            quality_level=PriorityLevel.CRITICAL,
            history=[],
            schema_version=CURRENT_SCHEMA_VERSION,
        )
        # Verify all 27 fields are present
        assert event.event_id is not None
        assert event.timestamp_utc == timestamp_now
        assert event.ticker == "XYZ.WA"
        assert event.market == "GPW"
        assert event.instrument_type == InstrumentType.STOCK_GPW
        assert event.event_family == EventFamily.PRICE
        assert event.event_category == "Cenowe"
        assert event.event_subcategory == "Ruchy gwałtowne"
        assert event.event_type == "PRICE_SURGE"
        assert event.priority_raw == PriorityLevel.CRITICAL
        assert event.priority_final == PriorityLevel.CRITICAL
        assert event.confidence_level == 0.95
        assert event.detection_source == "Price Event Detector"
        assert event.event_owner == EventOwner.TechnicalEngine
        assert event.price_data == sample_price_data
        assert event.volume_data == sample_volume_data
        assert event.technical_context == {"RSI": 28.5, "MACD_line": -0.32}
        assert event.fundamental_context == {"PE_ratio": 12.5}
        assert event.news_context == [{"headline": "Test news"}]
        assert event.ai_context == {"summary": "Test AI summary"}
        assert event.tavily_context == {"results_count": 3}
        assert event.metadata == {"key": "value"}
        assert event.composite_events == []
        assert event.is_composite is False
        assert event.quality_level == PriorityLevel.CRITICAL
        assert event.history == []
        assert event.schema_version == CURRENT_SCHEMA_VERSION


# ------------------------------------------------------------------
# 2. Rejection of data without required fields
# ------------------------------------------------------------------


class TestMarketEventValidation:
    """Tests that MarketEvent rejects invalid data."""

    def test_empty_event_id_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="event_id"):
            MarketEvent(
                event_id="",
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_empty_ticker_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="ticker"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_empty_market_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="market"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_empty_event_category_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="event_category"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_empty_event_type_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="event_type"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_detection_source_empty_allowed_at_creation(self, timestamp_now):
        """detection_source may be empty at creation; it's filled in Stage 2 (Detekcja)."""
        event = MarketEvent(
            event_id=str(uuid.uuid4()),
            timestamp_utc=timestamp_now,
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            signal_timing=SignalTiming.LEADING,
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            confidence_level=0.8,
            detection_source="",
            event_owner=EventOwner.TechnicalEngine,
            quality_level=PriorityLevel.HIGH,
        )

    def test_signal_timing_required(self):
        """signal_timing is required at construction."""
        with pytest.raises(TypeError):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=datetime.now(timezone.utc),
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
            )

    def test_set_detection_requires_detection_source(self, timestamp_now):
        """After set_detection, detection_source must be non-empty."""
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
        )
        assert event.detection_source == "Price Event Detector"

    def test_confidence_level_below_zero_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="confidence_level"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=-0.1,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_confidence_level_above_one_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="confidence_level"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=1.5,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )

    def test_empty_schema_version_raises(self, timestamp_now):
        with pytest.raises(ValueError, match="schema_version"):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=timestamp_now,
                ticker="XYZ.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                signal_timing=SignalTiming.LEADING,
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="Test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
                schema_version="",
            )

    def test_missing_signal_timing_fails(self):
        """MarketEvent without signal_timing fails at construction."""
        with pytest.raises(TypeError):
            MarketEvent(
                event_id=str(uuid.uuid4()),
                timestamp_utc=datetime.now(timezone.utc),
                ticker="TEST",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                event_family=EventFamily.PRICE,
                event_category="Cenowe",
                event_type="PRICE_SURGE",
                priority_raw=PriorityLevel.HIGH,
                priority_final=PriorityLevel.HIGH,
                confidence_level=0.8,
                detection_source="test",
                event_owner=EventOwner.TechnicalEngine,
                quality_level=PriorityLevel.HIGH,
            )


# ------------------------------------------------------------------
# 3. Correct enum behavior
# ------------------------------------------------------------------


class TestEnums:
    """Tests for enum definitions."""

    def test_instrument_type_values(self):
        assert InstrumentType.STOCK_GPW.value == "STOCK_GPW"
        assert InstrumentType.STOCK_USA.value == "STOCK_USA"
        assert InstrumentType.ETF.value == "ETF"
        assert len(InstrumentType) == 3

    def test_event_family_values(self):
        families = {
            EventFamily.PRICE,
            EventFamily.VOLUME,
            EventFamily.TECHNICAL,
            EventFamily.FUNDAMENTAL,
            EventFamily.CORPORATE,
            EventFamily.REGULATORY,
            EventFamily.MACRO,
            EventFamily.ETF,
            EventFamily.DERIVATIVES,
            EventFamily.SENTIMENT,
            EventFamily.SYSTEM,
        }
        assert len(families) == 11

    def test_priority_level_values(self):
        levels = {
            PriorityLevel.CRITICAL,
            PriorityLevel.HIGH,
            PriorityLevel.MEDIUM,
            PriorityLevel.LOW,
            PriorityLevel.IGNORE,
        }
        assert len(levels) == 5

    def test_event_owner_values(self):
        owners = {
            EventOwner.TechnicalEngine,
            EventOwner.AnalystEngine,
            EventOwner.NewsEngine,
            EventOwner.AIEngine,
            EventOwner.Multi_Engine,
        }
        assert len(owners) == 5

    def test_signal_timing_values(self):
        """SignalTiming enum has exactly four values."""
        values = {SignalTiming.LEADING, SignalTiming.CONFIRMING, SignalTiming.WARNING, SignalTiming.CONTEXT}
        assert len(values) == 4

    def test_enums_are_string_backed(self):
        """All enums inherit from str, so they compare with strings."""
        assert InstrumentType.STOCK_GPW == "STOCK_GPW"
        assert PriorityLevel.CRITICAL == "CRITICAL"
        assert EventFamily.PRICE == "PRICE"

    def test_enum_from_string_construction(self):
        assert InstrumentType("STOCK_GPW") == InstrumentType.STOCK_GPW
        assert PriorityLevel("HIGH") == PriorityLevel.HIGH
        assert EventFamily("VOLUME") == EventFamily.VOLUME
        assert EventOwner("NewsEngine") == EventOwner.NewsEngine


# ------------------------------------------------------------------
# 4. Correct addition of HistoryEntry
# ------------------------------------------------------------------


class TestHistoryEntry:
    """Tests for HistoryEntry model."""

    def test_create_history_entry(self):
        ts = datetime(2026, 7, 18, 14, 32, 5, tzinfo=timezone.utc)
        entry = HistoryEntry(
            timestamp=ts,
            module="MarketScanner",
            action="Utworzenie zdarzenia dla instrumentu XYZ.WA",
            fields_changed=["event_id", "timestamp_utc", "ticker"],
        )
        assert entry.timestamp == ts
        assert entry.module == "MarketScanner"
        assert entry.action == "Utworzenie zdarzenia dla instrumentu XYZ.WA"
        assert "event_id" in entry.fields_changed
        assert entry.details is None

    def test_history_entry_with_details(self):
        ts = datetime(2026, 7, 18, 14, 32, 5, tzinfo=timezone.utc)
        entry = HistoryEntry(
            timestamp=ts,
            module="TechnicalEngine",
            action="Wykrycie zdarzenia",
            fields_changed=["event_type"],
            details={"old_value": "EVENT_CREATED", "new_value": "PRICE_SURGE"},
        )
        assert entry.details == {"old_value": "EVENT_CREATED", "new_value": "PRICE_SURGE"}

    def test_history_entry_serialization(self):
        ts = datetime(2026, 7, 18, 14, 32, 5, tzinfo=timezone.utc)
        entry = HistoryEntry(
            timestamp=ts,
            module="MarketScanner",
            action="Utworzenie zdarzenia",
            fields_changed=["event_id", "ticker"],
            details={"note": "test"},
        )
        d = entry.to_dict()
        assert d["timestamp"] == "2026-07-18T14:32:05+00:00"
        assert d["module"] == "MarketScanner"
        assert d["action"] == "Utworzenie zdarzenia"
        assert d["fields_changed"] == ["event_id", "ticker"]
        assert d["details"] == {"note": "test"}

    def test_history_entry_deserialization(self):
        data = {
            "timestamp": "2026-07-18T14:32:05+00:00",
            "module": "MarketScanner",
            "action": "Utworzenie zdarzenia",
            "fields_changed": ["event_id", "ticker"],
            "details": {"note": "test"},
        }
        entry = HistoryEntry.from_dict(data)
        assert entry.timestamp == datetime(2026, 7, 18, 14, 32, 5, tzinfo=timezone.utc)
        assert entry.module == "MarketScanner"
        assert entry.action == "Utworzenie zdarzenia"
        assert entry.fields_changed == ["event_id", "ticker"]
        assert entry.details == {"note": "test"}

    def test_history_entry_deserialization_without_details(self):
        data = {
            "timestamp": "2026-07-18T14:32:05+00:00",
            "module": "MarketScanner",
            "action": "Utworzenie zdarzenia",
            "fields_changed": [],
        }
        entry = HistoryEntry.from_dict(data)
        assert entry.details is None

    def test_add_history_entry_to_event(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        initial_count = len(event.history)
        event.add_history_entry(
            module="TechnicalEngine",
            action="Wykrycie zdarzenia: PRICE_SURGE",
            fields_changed=["event_family", "event_type"],
        )
        assert len(event.history) == initial_count + 1
        last_entry = event.history[-1]
        assert last_entry.module == "TechnicalEngine"
        assert last_entry.action == "Wykrycie zdarzenia: PRICE_SURGE"
        assert "event_family" in last_entry.fields_changed


# ------------------------------------------------------------------
# 5. Correct lifecycle stage transitions
# ------------------------------------------------------------------


class TestLifecycleTransitions:
    """Tests for lifecycle stage transitions."""

    def test_set_detection(self, timestamp_now, sample_price_data, sample_volume_data):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        initial_history_count = len(event.history)
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            event_subcategory="Ruchy gwałtowne",
            price_data=sample_price_data,
            volume_data=sample_volume_data,
            technical_context={"RSI": 28.5},
            fundamental_context={"PE_ratio": 12.5},
        )
        assert event.event_family == EventFamily.PRICE
        assert event.event_type == "PRICE_SURGE"
        assert event.priority_raw == PriorityLevel.CRITICAL
        assert event.confidence_level == 0.95
        assert event.detection_source == "Price Event Detector"
        assert event.event_owner == EventOwner.TechnicalEngine
        assert event.event_subcategory == "Ruchy gwałtowne"
        assert event.price_data == sample_price_data
        assert event.volume_data == sample_volume_data
        assert event.technical_context == {"RSI": 28.5}
        assert event.fundamental_context == {"PE_ratio": 12.5}
        assert len(event.history) == initial_history_count + 1

    def test_set_detection_immutable_fields(self, timestamp_now):
        """Fields set at creation must not be changed by set_detection."""
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        original_id = event.event_id
        original_ticker = event.ticker
        original_market = event.market
        original_instrument = event.instrument_type
        original_timestamp = event.timestamp_utc

        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
        )
        assert event.event_id == original_id
        assert event.ticker == original_ticker
        assert event.market == original_market
        assert event.instrument_type == original_instrument
        assert event.timestamp_utc == original_timestamp

    def test_set_detection_optional_subcategory(self, timestamp_now):
        """event_subcategory can remain None."""
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
        )
        assert event.event_subcategory is None

    def test_set_normalization(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
        )
        initial_history_count = len(event.history)
        event.set_normalization(
            priority_final=PriorityLevel.CRITICAL,
            is_composite=True,
            composite_events=[str(uuid.uuid4()), str(uuid.uuid4())],
        )
        assert event.priority_final == PriorityLevel.CRITICAL
        assert event.is_composite is True
        assert len(event.composite_events) == 2
        # priority_raw must remain unchanged (invariant N6)
        assert event.priority_raw == PriorityLevel.CRITICAL
        assert len(event.history) == initial_history_count + 1

    def test_set_quality_assessment(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_quality_assessment(PriorityLevel.CRITICAL)
        assert event.quality_level == PriorityLevel.CRITICAL
        assert event.history[-1].action == "Ocena jakości — poziom: CRITICAL"

    def test_set_quality_assessment_ignore_stops_processing(self, timestamp_now):
        """quality_level IGNORE means processing should stop."""
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_quality_assessment(PriorityLevel.IGNORE)
        assert event.quality_level == PriorityLevel.IGNORE

    def test_set_archive(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_archive()
        assert "archived_at" in event.metadata
        assert event.history[-1].module == "HistoryRepository"


# ------------------------------------------------------------------
# 6. Correct serialization to JSON
# ------------------------------------------------------------------


class TestSerialization:
    """Tests for serialization to JSON-compatible dicts."""

    def test_to_dict_roundtrip(self, timestamp_now, sample_price_data, sample_volume_data):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            event_subcategory="Ruchy gwałtowne",
            price_data=sample_price_data,
            volume_data=sample_volume_data,
            technical_context={"RSI": 28.5},
        )
        event.set_normalization(
            priority_final=PriorityLevel.CRITICAL,
            is_composite=False,
        )
        event.set_quality_assessment(PriorityLevel.CRITICAL)
        event.metadata["dedup_hash"] = "abc123"

        d = event.to_dict()

        assert d["event_id"] == event.event_id
        assert d["ticker"] == "XYZ.WA"
        assert d["market"] == "GPW"
        assert d["instrument_type"] == "STOCK_GPW"
        assert d["event_family"] == "PRICE"
        assert d["signal_timing"] == "leading"
        assert d["priority_raw"] == "CRITICAL"
        assert d["priority_final"] == "CRITICAL"
        assert d["quality_level"] == "CRITICAL"
        assert d["confidence_level"] == 0.95
        assert d["schema_version"] == CURRENT_SCHEMA_VERSION
        assert d["price_data"]["open"] == 100.0
        assert d["volume_data"]["volume_ratio"] == 4.2
        assert d["technical_context"] == {"RSI": 28.5}
        assert d["metadata"]["dedup_hash"] == "abc123"
        assert isinstance(d["history"], list)
        assert len(d["history"]) >= 1

        # Verify JSON serialization
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        assert "XYZ.WA" in json_str

    def test_serialization_with_null_optionals(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        d = event.to_dict()
        assert d["event_subcategory"] is None
        assert d["price_data"] is None
        assert d["volume_data"] is None
        assert d["technical_context"] is None
        assert d["fundamental_context"] is None
        assert d["news_context"] is None
        assert d["ai_context"] is None
        assert d["tavily_context"] is None


# ------------------------------------------------------------------
# 7. Correct reconstruction of object from JSON
# ------------------------------------------------------------------


class TestDeserialization:
    """Tests for deserialization from dicts."""

    def test_from_dict_reconstructs_full_event(self, timestamp_now, sample_price_data, sample_volume_data):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            event_subcategory="Ruchy gwałtowne",
            price_data=sample_price_data,
            volume_data=sample_volume_data,
            technical_context={"RSI": 28.5},
        )
        event.set_normalization(
            priority_final=PriorityLevel.CRITICAL,
            is_composite=False,
        )
        event.set_quality_assessment(PriorityLevel.CRITICAL)
        event.metadata["dedup_hash"] = "abc123"

        d = event.to_dict()
        restored = MarketEvent.from_dict(d)

        assert restored.event_id == event.event_id
        assert restored.ticker == event.ticker
        assert restored.market == event.market
        assert restored.instrument_type == event.instrument_type
        assert restored.event_family == event.event_family
        assert restored.event_category == event.event_category
        assert restored.event_subcategory == event.event_subcategory
        assert restored.event_type == event.event_type
        assert restored.signal_timing == event.signal_timing
        assert restored.priority_raw == event.priority_raw
        assert restored.priority_final == event.priority_final
        assert restored.confidence_level == event.confidence_level
        assert restored.detection_source == event.detection_source
        assert restored.event_owner == event.event_owner
        assert restored.quality_level == event.quality_level
        assert restored.schema_version == event.schema_version
        assert restored.is_composite == event.is_composite
        assert restored.metadata == event.metadata

        # Nested objects
        assert restored.price_data is not None
        assert restored.price_data.open == 100.0
        assert restored.price_data.close == 112.3
        assert restored.volume_data is not None
        assert restored.volume_data.volume_ratio == 4.2
        assert restored.technical_context == {"RSI": 28.5}

        # History
        assert len(restored.history) == len(event.history)
        for original, restored_entry in zip(event.history, restored.history):
            assert restored_entry.module == original.module
            assert restored_entry.action == original.action

    def test_from_dict_with_minimal_event(self, timestamp_now):
        """Reconstruct from a minimal event created by create_new."""
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        d = event.to_dict()
        restored = MarketEvent.from_dict(d)
        assert restored.event_id == event.event_id
        assert restored.ticker == "XYZ.WA"
        assert restored.market == "GPW"
        assert restored.instrument_type == InstrumentType.STOCK_GPW
        assert restored.price_data is None
        assert restored.volume_data is None
        assert len(restored.history) == 1

    def test_from_dict_requires_signal_timing(self):
        """from_dict raises KeyError when signal_timing is missing."""
        data = {
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": "2026-07-18T14:32:05+00:00",
            "ticker": "XYZ.WA",
            "market": "GPW",
            "instrument_type": "STOCK_GPW",
            "event_family": "PRICE",
            "event_category": "Cenowe",
            "event_type": "PRICE_SURGE",
            "priority_raw": "HIGH",
            "priority_final": "HIGH",
            "confidence_level": 0.8,
            "detection_source": "Test",
            "event_owner": "TechnicalEngine",
            "quality_level": "HIGH",
            "schema_version": "1.0",
        }
        with pytest.raises(KeyError):
            MarketEvent.from_dict(data)

    def test_from_dict_with_signal_timing_succeeds(self):
        """from_dict with signal_timing reconstructs correctly."""
        data = {
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": "2026-07-18T14:32:05+00:00",
            "ticker": "XYZ.WA",
            "market": "GPW",
            "instrument_type": "STOCK_GPW",
            "event_family": "PRICE",
            "event_category": "Cenowe",
            "event_type": "PRICE_SURGE",
            "signal_timing": "leading",
            "priority_raw": "HIGH",
            "priority_final": "HIGH",
            "confidence_level": 0.8,
            "detection_source": "Test",
            "event_owner": "TechnicalEngine",
            "quality_level": "HIGH",
            "schema_version": "1.0",
        }
        event = MarketEvent.from_dict(data)
        assert event.signal_timing == SignalTiming.LEADING


# ------------------------------------------------------------------
# 8. Preservation of optional values
# ------------------------------------------------------------------


class TestOptionalValues:
    """Tests that optional values are correctly preserved."""

    def test_event_subcategory_preserved(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.TECHNICAL,
            event_category="Formacje świecowe",
            event_type="HAMMER",
            priority_raw=PriorityLevel.MEDIUM,
            confidence_level=0.7,
            detection_source="Technical Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            event_subcategory="Świece pojedyncze",
        )
        d = event.to_dict()
        restored = MarketEvent.from_dict(d)
        assert restored.event_subcategory == "Świece pojedyncze"

    def test_context_dictionaries_preserved(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.news_context = [
            {"headline": "News 1", "source": "Source A"},
            {"headline": "News 2", "source": "Source B"},
        ]
        event.ai_context = {"summary": "AI analysis", "sentiment": "positive"}
        event.tavily_context = {"query": "test", "results_count": 5}

        d = event.to_dict()
        restored = MarketEvent.from_dict(d)

        assert restored.news_context == event.news_context
        assert len(restored.news_context) == 2
        assert restored.ai_context == event.ai_context
        assert restored.tavily_context == event.tavily_context

    def test_fundamental_context_preserved(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.fundamental_context = {
            "PE_ratio": 12.5,
            "market_cap": 1_200_000_000,
            "revenue": 500_000_000,
        }
        d = event.to_dict()
        restored = MarketEvent.from_dict(d)
        assert restored.fundamental_context == event.fundamental_context


# ------------------------------------------------------------------
# 9. Preservation of contract version
# ------------------------------------------------------------------


class TestContractVersion:
    """Tests that the contract version is correctly preserved."""

    def test_schema_version_is_current(self):
        assert CURRENT_SCHEMA_VERSION == "1.0"

    def test_create_new_uses_current_version(self):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        assert event.schema_version == CURRENT_SCHEMA_VERSION

    def test_version_preserved_in_serialization(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        d = event.to_dict()
        assert d["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_version_preserved_in_deserialization(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        d = event.to_dict()
        restored = MarketEvent.from_dict(d)
        assert restored.schema_version == CURRENT_SCHEMA_VERSION

    def test_version_preserved_through_lifecycle(self, timestamp_now):
        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            timestamp_utc=timestamp_now,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.95,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
        )
        event.set_normalization(priority_final=PriorityLevel.CRITICAL)
        event.set_quality_assessment(PriorityLevel.CRITICAL)
        event.set_archive()
        assert event.schema_version == CURRENT_SCHEMA_VERSION


# ------------------------------------------------------------------
# 10. No dependency of models on engines/
# ------------------------------------------------------------------


class TestNoEngineDependency:
    """Tests that models have no dependency on engines/."""

    def test_models_do_not_import_engines(self):
        """Verify that the new models don't import anything from engines/."""
        import ast
        import inspect

        from data.models import event_enums, history_entry, market_event, price_data, volume_data

        modules = [event_enums, history_entry, price_data, volume_data, market_event]

        for mod in modules:
            source = inspect.getsource(mod)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.ImportFrom):
                        module_name = node.module or ""
                    else:
                        module_name = node.names[0].name if node.names else ""
                    assert not module_name.startswith(
                        "engines"
                    ), f"{mod.__name__} imports from engines/: {module_name}"


# ------------------------------------------------------------------
# PriceData and VolumeData serialization
# ------------------------------------------------------------------


class TestPriceData:
    """Tests for PriceData model."""

    def test_create_price_data(self):
        pd = PriceData(
            open=100.0,
            high=110.0,
            low=95.0,
            close=108.0,
            prev_close=100.0,
            change_pct=8.0,
            change_abs=8.0,
        )
        assert pd.open == 100.0
        assert pd.close == 108.0
        assert pd.change_pct == 8.0

    def test_price_data_serialization_roundtrip(self):
        pd = PriceData(
            open=100.0,
            high=110.0,
            low=95.0,
            close=108.0,
            prev_close=100.0,
            change_pct=8.0,
            change_abs=8.0,
        )
        d = pd.to_dict()
        restored = PriceData.from_dict(d)
        assert restored.open == pd.open
        assert restored.high == pd.high
        assert restored.low == pd.low
        assert restored.close == pd.close
        assert restored.prev_close == pd.prev_close
        assert restored.change_pct == pd.change_pct
        assert restored.change_abs == pd.change_abs


class TestVolumeData:
    """Tests for VolumeData model."""

    def test_create_volume_data(self):
        vd = VolumeData(
            current_volume=500000.0,
            avg_volume=100000.0,
            volume_ratio=5.0,
            direction="up",
        )
        assert vd.current_volume == 500000.0
        assert vd.volume_ratio == 5.0
        assert vd.direction == "up"

    def test_volume_data_serialization_roundtrip(self):
        vd = VolumeData(
            current_volume=500000.0,
            avg_volume=100000.0,
            volume_ratio=5.0,
            direction="down",
        )
        d = vd.to_dict()
        restored = VolumeData.from_dict(d)
        assert restored.current_volume == vd.current_volume
        assert restored.avg_volume == vd.avg_volume
        assert restored.volume_ratio == vd.volume_ratio
        assert restored.direction == vd.direction