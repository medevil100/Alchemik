"""
MarketEvent — the central data model for market events in ALCHEMIK.

Represents a single market event detected by the system. This object is the sole
carrier of event information across all modules. Each module reads from it and
writes to it only within its own responsibility, as defined in the
Kontrakt Zdarzen Rynkowych.

Contract version: 1.0
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel
from .history_entry import HistoryEntry
from .price_data import PriceData
from .volume_data import VolumeData

# Current schema version as defined in the contract.
CURRENT_SCHEMA_VERSION = "1.0"


@dataclass
class MarketEvent:
    """
    A single market event — the unified data object flowing through all modules.

    The event progresses through 13 lifecycle stages: creation, detection,
    normalization, deduplication, quality assessment, news enrichment, Tavily
    search, orchestration, AI decision, risk assessment, alert decision,
    alert dispatch, and archiving. Each stage adds or modifies specific fields
    and records a HistoryEntry.
    """

    # --- Identification & classification (fields 1-9) ---
    event_id: str
    timestamp_utc: datetime
    ticker: str
    market: str
    instrument_type: InstrumentType
    event_family: EventFamily
    event_category: str
    event_type: str
    event_subcategory: Optional[str] = None

    # --- Priority & confidence (fields 10-12) ---
    priority_raw: PriorityLevel = PriorityLevel.LOW
    priority_final: PriorityLevel = PriorityLevel.LOW
    confidence_level: float = 0.0

    # --- Source & ownership (fields 13-14) ---
    detection_source: str = ""
    event_owner: EventOwner = EventOwner.TechnicalEngine

    # --- Context data (fields 15-22) ---
    price_data: Optional[PriceData] = None
    volume_data: Optional[VolumeData] = None
    technical_context: Optional[dict] = None
    fundamental_context: Optional[dict] = None
    news_context: Optional[list] = None
    ai_context: Optional[dict] = None
    tavily_context: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    # --- Aggregation (fields 23-24) ---
    composite_events: list = field(default_factory=list)
    is_composite: bool = False

    # --- Quality & history (fields 25-26) ---
    quality_level: PriorityLevel = PriorityLevel.LOW
    history: list = field(default_factory=list)

    # --- Versioning (field 27) ---
    schema_version: str = CURRENT_SCHEMA_VERSION

    def __post_init__(self):
        """Validate required fields and invariants after initialization."""
        self._validate_required_fields()
        self._validate_confidence_level()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_required_fields(self):
        """Ensure all required fields are present and non-empty."""
        if not self.event_id or not isinstance(self.event_id, str):
            raise ValueError("event_id must be a non-empty string")
        if self.timestamp_utc is None:
            raise ValueError("timestamp_utc is required")
        if not self.ticker or not isinstance(self.ticker, str):
            raise ValueError("ticker must be a non-empty string")
        if not self.market or not isinstance(self.market, str):
            raise ValueError("market must be a non-empty string")
        if self.instrument_type is None:
            raise ValueError("instrument_type is required")
        if self.event_family is None:
            raise ValueError("event_family is required")
        if not self.event_category or not isinstance(self.event_category, str):
            raise ValueError("event_category must be a non-empty string")
        if not self.event_type or not isinstance(self.event_type, str):
            raise ValueError("event_type must be a non-empty string")
        if self.priority_raw is None:
            raise ValueError("priority_raw is required")
        if self.priority_final is None:
            raise ValueError("priority_final is required")
        if self.confidence_level is None:
            raise ValueError("confidence_level is required")
        if not isinstance(self.detection_source, str):
            raise ValueError("detection_source must be a string")
        if self.event_owner is None:
            raise ValueError("event_owner is required")
        if self.quality_level is None:
            raise ValueError("quality_level is required")
        if not self.schema_version or not isinstance(self.schema_version, str):
            raise ValueError("schema_version must be a non-empty string")

    def _validate_confidence_level(self):
        """Ensure confidence_level is within the valid range [0.0, 1.0]."""
        if not (0.0 <= self.confidence_level <= 1.0):
            raise ValueError(
                f"confidence_level must be between 0.0 and 1.0, got {self.confidence_level}"
            )

    # ------------------------------------------------------------------
    # Factory — minimal creation (Stage 1: MarketScanner / HunterEngine)
    # ------------------------------------------------------------------

    @classmethod
    def create_new(
        cls,
        ticker: str,
        market: str,
        instrument_type: InstrumentType,
        timestamp_utc: Optional[datetime] = None,
    ) -> "MarketEvent":
        """
        Create a new MarketEvent with minimal fields (Stage 1: Utworzenie).

        This corresponds to the first step of the lifecycle where MarketScanner
        or HunterEngine creates the initial event object with identification
        fields only.

        Args:
            ticker: Instrument symbol (e.g., "XYZ.WA")
            market: Market identifier (e.g., "GPW", "NYSE")
            instrument_type: Type of instrument (STOCK_GPW, STOCK_USA, ETF)
            timestamp_utc: Optional timestamp; defaults to current UTC time.

        Returns:
            A new MarketEvent with identification fields set and an initial
            history entry recording the creation.
        """
        if timestamp_utc is None:
            timestamp_utc = datetime.now(timezone.utc)

        event = cls(
            event_id=str(uuid.uuid4()),
            timestamp_utc=timestamp_utc,
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            event_family=EventFamily.SYSTEM,
            event_category="System",
            event_type="EVENT_CREATED",
            priority_raw=PriorityLevel.LOW,
            priority_final=PriorityLevel.LOW,
            confidence_level=0.0,
            detection_source="",
            event_owner=EventOwner.TechnicalEngine,
            schema_version=CURRENT_SCHEMA_VERSION,
            history=[],
        )
        event.add_history_entry(
            module="MarketScanner",
            action=f"Utworzenie zdarzenia dla instrumentu {ticker}",
            fields_changed=[
                "event_id",
                "timestamp_utc",
                "ticker",
                "market",
                "instrument_type",
                "schema_version",
            ],
        )
        return event

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def add_history_entry(
        self,
        module: str,
        action: str,
        fields_changed: list,
        details: Optional[dict] = None,
    ) -> None:
        """
        Append a new HistoryEntry to the event's chronological history.

        This method must be called by every module that modifies the event,
        in accordance with invariant N3 (Historia zmian jest zachowywana).

        Args:
            module: Name of the module making the change (e.g., "TechnicalEngine")
            action: Description of the action performed
            fields_changed: List of field names that were modified
            details: Optional additional details about the change
        """
        entry = HistoryEntry(
            timestamp=datetime.now(timezone.utc),
            module=module,
            action=action,
            fields_changed=fields_changed,
            details=details,
        )
        self.history.append(entry)

    # ------------------------------------------------------------------
    # Lifecycle stage transitions
    # ------------------------------------------------------------------

    def set_detection(
        self,
        event_family: EventFamily,
        event_category: str,
        event_type: str,
        priority_raw: PriorityLevel,
        confidence_level: float,
        detection_source: str,
        event_owner: EventOwner,
        event_subcategory: Optional[str] = None,
        price_data: Optional[PriceData] = None,
        volume_data: Optional[VolumeData] = None,
        technical_context: Optional[dict] = None,
        fundamental_context: Optional[dict] = None,
    ) -> None:
        """
        Transition to Stage 2: Detekcja (Detection).

        Sets all detection-related fields as specified by the detecting module.
        Records the change in history.

        The following fields are immutable after this stage:
        event_id, timestamp_utc, ticker, market, instrument_type.
        """
        changed = []
        self.event_family = event_family
        self.event_category = event_category
        self.event_type = event_type
        self.priority_raw = priority_raw
        self.confidence_level = confidence_level
        self.detection_source = detection_source
        self.event_owner = event_owner
        changed.extend([
            "event_family", "event_category", "event_type",
            "priority_raw", "confidence_level",
            "detection_source", "event_owner",
        ])

        if event_subcategory is not None:
            self.event_subcategory = event_subcategory
            changed.append("event_subcategory")
        if price_data is not None:
            self.price_data = price_data
            changed.append("price_data")
        if volume_data is not None:
            self.volume_data = volume_data
            changed.append("volume_data")
        if technical_context is not None:
            self.technical_context = technical_context
            changed.append("technical_context")
        if fundamental_context is not None:
            self.fundamental_context = fundamental_context
            changed.append("fundamental_context")

        self._validate_confidence_level()

        self.add_history_entry(
            module=detection_source,
            action=f"Wykrycie zdarzenia: {event_type}",
            fields_changed=changed,
        )

    def set_normalization(
        self,
        priority_final: PriorityLevel,
        is_composite: bool = False,
        composite_events: Optional[list] = None,
    ) -> None:
        """
        Transition to Stage 3: Normalizacja i scalanie (Normalization & Merging).

        Sets aggregation fields and computes the final priority.
        Invariant: priority_raw remains unchanged.
        """
        changed = ["priority_final", "is_composite"]
        self.priority_final = priority_final
        self.is_composite = is_composite
        if composite_events is not None:
            self.composite_events = composite_events
            changed.append("composite_events")
        self.add_history_entry(
            module="MasterEngine",
            action="Normalizacja i scalanie"
            + (" — Composite Event" if is_composite else ""),
            fields_changed=changed,
        )

    def set_quality_assessment(self, quality_level: PriorityLevel) -> None:
        """
        Transition to Stage 5: Ocena jakości (Quality Assessment).

        Sets the final quality_level that determines downstream processing.
        quality_level == IGNORE or LOW → processing stops, only archiving.
        """
        self.quality_level = quality_level
        self.add_history_entry(
            module="Ocena jakości",
            action=f"Ocena jakości — poziom: {quality_level.value}",
            fields_changed=["quality_level"],
        )

    def set_archive(self) -> None:
        """
        Transition to Stage 13: Archiwizacja (Archiving).

        Marks the event as archived. No further modifications are expected.
        """
        self.metadata["archived_at"] = datetime.now(timezone.utc).isoformat()
        self.add_history_entry(
            module="HistoryRepository",
            action="Archiwizacja — zapisano w repozytorium",
            fields_changed=["metadata.archived_at"],
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Serialize the MarketEvent to a JSON-compatible dictionary.

        All nested objects (PriceData, VolumeData, HistoryEntry) are
        recursively serialized. Datetime fields are converted to ISO 8601.
        Enum fields are converted to their string values.
        """
        result = {
            "event_id": self.event_id,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "ticker": self.ticker,
            "market": self.market,
            "instrument_type": self.instrument_type.value,
            "event_family": self.event_family.value,
            "event_category": self.event_category,
            "event_subcategory": self.event_subcategory,
            "event_type": self.event_type,
            "priority_raw": self.priority_raw.value,
            "priority_final": self.priority_final.value,
            "confidence_level": self.confidence_level,
            "detection_source": self.detection_source,
            "event_owner": self.event_owner.value,
            "price_data": self.price_data.to_dict() if self.price_data else None,
            "volume_data": self.volume_data.to_dict() if self.volume_data else None,
            "technical_context": self.technical_context,
            "fundamental_context": self.fundamental_context,
            "news_context": self.news_context,
            "ai_context": self.ai_context,
            "tavily_context": self.tavily_context,
            "metadata": self.metadata,
            "composite_events": self.composite_events,
            "is_composite": self.is_composite,
            "quality_level": self.quality_level.value,
            "history": [entry.to_dict() for entry in self.history],
            "schema_version": self.schema_version,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "MarketEvent":
        """
        Deserialize a MarketEvent from a dictionary (e.g., parsed JSON).

        Restores all nested objects, enum values, and datetime fields.
        """
        return cls(
            event_id=data["event_id"],
            timestamp_utc=datetime.fromisoformat(data["timestamp_utc"]),
            ticker=data["ticker"],
            market=data["market"],
            instrument_type=InstrumentType(data["instrument_type"]),
            event_family=EventFamily(data["event_family"]),
            event_category=data["event_category"],
            event_subcategory=data.get("event_subcategory"),
            event_type=data["event_type"],
            priority_raw=PriorityLevel(data["priority_raw"]),
            priority_final=PriorityLevel(data["priority_final"]),
            confidence_level=float(data["confidence_level"]),
            detection_source=data["detection_source"],
            event_owner=EventOwner(data["event_owner"]),
            price_data=(
                PriceData.from_dict(data["price_data"])
                if data.get("price_data") is not None
                else None
            ),
            volume_data=(
                VolumeData.from_dict(data["volume_data"])
                if data.get("volume_data") is not None
                else None
            ),
            technical_context=data.get("technical_context"),
            fundamental_context=data.get("fundamental_context"),
            news_context=data.get("news_context"),
            ai_context=data.get("ai_context"),
            tavily_context=data.get("tavily_context"),
            metadata=data.get("metadata", {}),
            composite_events=data.get("composite_events", []),
            is_composite=bool(data.get("is_composite", False)),
            quality_level=PriorityLevel(data["quality_level"]),
            history=[HistoryEntry.from_dict(entry) for entry in data.get("history", [])],
            schema_version=data.get("schema_version", CURRENT_SCHEMA_VERSION),
        )