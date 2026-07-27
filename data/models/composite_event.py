"""
CompositeEvent — model danych dla zdarzeń złożonych (Composite Events).

Reprezentuje pojedyncze zdarzenie złożone powstałe z połączenia dwóch lub więcej
zdarzeń prostych dotyczących tego samego instrumentu, wykrytych w zbliżonym czasie.

Model jest zgodny z architekturą ETAPU 7 i Kontraktem Zdarzeń Rynkowych:
- ETAP 3 cyklu życia: Normalizacja i scalanie
- Niezmiennik N10: priority_final = max(priorities of component events)

Ten model jest prostym kontenerem danych — nie zawiera logiki wykrywania
ani łączenia zdarzeń. Logika scalania będzie zaimplementowana w ComposerEngine
w kolejnym kroku ETAPU 7.3.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .event_enums import EventFamily, PriorityLevel


@dataclass
class CompositeEvent:
    """
    Pojedyncze zdarzenie złożone — kontener danych dla Composite Event.

    Composite Event powstaje, gdy dwa lub więcej zdarzeń prostych (MarketEvent)
    dotyczących tego samego instrumentu zostanie wykrytych w zbliżonym czasie.
    Zdarzenia składowe są łączone w jedno zdarzenie złożone o wyższym priorytecie.

    Attributes:
        composite_id: Unikalny identyfikator zdarzenia złożonego (UUID v4).
        timestamp_utc: Znacznik czasu utworzenia zdarzenia złożonego w UTC.
        ticker: Symbol instrumentu finansowego, którego dotyczy zdarzenie.
        component_event_ids: Lista identyfikatorów zdarzeń składowych (event_id).
        priority_final: Końcowy priorytet — max z priorytetów zdarzeń składowych
            (zgodnie z niezmiennikiem N10).
        event_family: Rodzina zdarzenia złożonego (określana na podstawie składowych).
        event_type: Typ zdarzenia — dla Composite Events oznaczany jako
            COMPOSITE_MULTI_EVENT.
        confidence_level: Poziom pewności — uśredniony z confidence_level zdarzeń
            składowych.
        component_count: Liczba zdarzeń składowych.
        is_composite: Zawsze True dla CompositeEvent (pole zgodne z kontraktem
            MarketEvent).
        metadata: Dodatkowe metadane (opcjonalne).
    """

    composite_id: str
    timestamp_utc: datetime
    ticker: str
    component_event_ids: list[str] = field(default_factory=list)
    priority_final: PriorityLevel = PriorityLevel.LOW
    event_family: EventFamily = EventFamily.SYSTEM
    event_type: str = "COMPOSITE_MULTI_EVENT"
    confidence_level: float = 0.0
    component_count: int = 0
    is_composite: bool = True
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate_required_fields()
        self._validate_component_ids()
        self._validate_confidence_level()
        self._validate_component_count()
        self._validate_is_composite()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_required_fields(self):
        """Ensure all required fields are present and non-empty."""
        if not self.composite_id or not isinstance(self.composite_id, str):
            raise ValueError("composite_id must be a non-empty string")
        if self.timestamp_utc is None:
            raise ValueError("timestamp_utc is required")
        if not self.ticker or not isinstance(self.ticker, str):
            raise ValueError("ticker must be a non-empty string")
        if self.priority_final is None:
            raise ValueError("priority_final is required")
        if self.event_family is None:
            raise ValueError("event_family is required")
        if not self.event_type or not isinstance(self.event_type, str):
            raise ValueError("event_type must be a non-empty string")

    def _validate_component_ids(self):
        """Ensure component_event_ids is a list of non-empty strings."""
        if not isinstance(self.component_event_ids, list):
            raise ValueError(
                "component_event_ids must be a list"
            )
        for cid in self.component_event_ids:
            if not isinstance(cid, str) or not cid:
                raise ValueError(
                    f"Each component event ID must be a non-empty string, "
                    f"got: {cid!r}"
                )
        # Verify no duplicate component IDs
        if len(self.component_event_ids) != len(set(self.component_event_ids)):
            raise ValueError(
                "component_event_ids must not contain duplicates"
            )

    def _validate_confidence_level(self):
        """Ensure confidence_level is within the valid range [0.0, 1.0]."""
        if not (0.0 <= self.confidence_level <= 1.0):
            raise ValueError(
                f"confidence_level must be between 0.0 and 1.0, "
                f"got {self.confidence_level}"
            )

    def _validate_component_count(self):
        """Ensure component_count is consistent with component_event_ids."""
        expected = len(self.component_event_ids)
        if self.component_count != expected:
            raise ValueError(
                f"component_count ({self.component_count}) does not match "
                f"len(component_event_ids) ({expected})"
            )

    def _validate_is_composite(self):
        """Ensure is_composite is always True for CompositeEvent."""
        if not self.is_composite:
            raise ValueError("is_composite must be True for CompositeEvent")

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        ticker: str,
        component_event_ids: list[str],
        priority_final: PriorityLevel,
        event_family: EventFamily,
        confidence_level: float = 0.0,
        timestamp_utc: Optional[datetime] = None,
        event_type: str = "COMPOSITE_MULTI_EVENT",
        metadata: Optional[dict] = None,
    ) -> "CompositeEvent":
        """
        Create a new CompositeEvent.

        The component_count is derived from the length of component_event_ids.
        is_composite is always set to True.

        Args:
            ticker: Instrument symbol.
            component_event_ids: List of component MarketEvent IDs (must be >= 2).
            priority_final: Final priority — should be max(component priorities).
            event_family: Family derived from component events.
            confidence_level: Average confidence from component events.
            timestamp_utc: Optional timestamp; defaults to current UTC time.
            event_type: Type identifier (default: COMPOSITE_MULTI_EVENT).
            metadata: Optional metadata dictionary.

        Returns:
            A new CompositeEvent instance.

        Raises:
            ValueError: If component_event_ids has fewer than 2 elements.
        """
        if len(component_event_ids) < 2:
            raise ValueError(
                "CompositeEvent requires at least 2 component events, "
                f"got {len(component_event_ids)}"
            )

        if timestamp_utc is None:
            from datetime import timezone
            timestamp_utc = datetime.now(timezone.utc)

        return cls(
            composite_id=str(uuid.uuid4()),
            timestamp_utc=timestamp_utc,
            ticker=ticker,
            component_event_ids=list(component_event_ids),
            priority_final=priority_final,
            event_family=event_family,
            event_type=event_type,
            confidence_level=confidence_level,
            component_count=len(component_event_ids),
            is_composite=True,
            metadata=metadata if metadata is not None else {},
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Serialize the CompositeEvent to a JSON-compatible dictionary.

        All enum fields are converted to their string values.
        Datetime fields are converted to ISO 8601 format.
        """
        return {
            "composite_id": self.composite_id,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "ticker": self.ticker,
            "component_event_ids": self.component_event_ids,
            "priority_final": self.priority_final.value,
            "event_family": self.event_family.value,
            "event_type": self.event_type,
            "confidence_level": self.confidence_level,
            "component_count": self.component_count,
            "is_composite": self.is_composite,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompositeEvent":
        """
        Deserialize a CompositeEvent from a dictionary.

        Restores enum values and datetime fields from their serialized forms.

        Args:
            data: Dictionary with serialized CompositeEvent data.

        Returns:
            A new CompositeEvent instance.
        """
        component_ids = data.get("component_event_ids", [])
        return cls(
            composite_id=data["composite_id"],
            timestamp_utc=datetime.fromisoformat(data["timestamp_utc"]),
            ticker=data["ticker"],
            component_event_ids=component_ids,
            priority_final=PriorityLevel(data["priority_final"]),
            event_family=EventFamily(data["event_family"]),
            event_type=data.get("event_type", "COMPOSITE_MULTI_EVENT"),
            confidence_level=float(data.get("confidence_level", 0.0)),
            component_count=int(data.get("component_count", len(component_ids))),
            is_composite=bool(data.get("is_composite", True)),
            metadata=data.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # Equality
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """
        Compare two CompositeEvent instances for equality.

        Two CompositeEvents are equal if all fields match.
        """
        if not isinstance(other, CompositeEvent):
            return NotImplemented
        return (
            self.composite_id == other.composite_id
            and self.timestamp_utc == other.timestamp_utc
            and self.ticker == other.ticker
            and self.component_event_ids == other.component_event_ids
            and self.priority_final == other.priority_final
            and self.event_family == other.event_family
            and self.event_type == other.event_type
            and self.confidence_level == other.confidence_level
            and self.component_count == other.component_count
            and self.is_composite == other.is_composite
            and self.metadata == other.metadata
        )

    def __hash__(self) -> int:
        """Hash based on composite_id for use in sets and dicts."""
        return hash(self.composite_id)

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"CompositeEvent("
            f"composite_id={self.composite_id!r}, "
            f"ticker={self.ticker!r}, "
            f"components={len(self.component_event_ids)}, "
            f"priority_final={self.priority_final.value}, "
            f"event_family={self.event_family.value}"
            f")"
        )