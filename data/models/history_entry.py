from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class HistoryEntry:
    """
    A single entry in the event's change history.

    Each modification to a MarketEvent object must be recorded as a HistoryEntry.
    The full history is stored chronologically in the event's `history` field.

    Fields:
        timestamp: datetime (ISO 8601, UTC) — moment of modification
        module: string — name of the module making the change
        action: string — description of the action performed
        fields_changed: list of field names that were modified
        details: optional additional details about the change
    """

    timestamp: datetime
    module: str
    action: str
    fields_changed: list = field(default_factory=list)
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "module": self.module,
            "action": self.action,
            "fields_changed": self.fields_changed,
        }
        if self.details is not None:
            result["details"] = self.details
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        """Deserialize from a dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            module=data["module"],
            action=data["action"],
            fields_changed=data.get("fields_changed", []),
            details=data.get("details"),
        )