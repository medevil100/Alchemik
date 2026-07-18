from dataclasses import dataclass
from typing import Optional


@dataclass
class VolumeData:
    """
    Volume data related to a market event.

    Contains current volume, average volume, and deviation ratio,
    as specified in the Kontrakt Zdarzen Rynkowych.

    Fields:
        current_volume: Current trading volume
        avg_volume: Average trading volume over the reference period
        volume_ratio: Ratio of current volume to average (krotność odchylenia)
        direction: Direction of the price move (e.g., 'up', 'down', 'neutral')
    """

    current_volume: float
    avg_volume: float
    volume_ratio: float
    direction: str

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "current_volume": self.current_volume,
            "avg_volume": self.avg_volume,
            "volume_ratio": self.volume_ratio,
            "direction": self.direction,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VolumeData":
        """Deserialize from a dictionary."""
        return cls(
            current_volume=data["current_volume"],
            avg_volume=data["avg_volume"],
            volume_ratio=data["volume_ratio"],
            direction=data["direction"],
        )