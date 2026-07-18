import hashlib
import time
from typing import Dict, Optional, Union


class OpportunityDeduplicator:
    """
    A deduplication layer for financial opportunities, ensuring no duplicate alerts are processed
    within a configurable time window.
    """

    def __init__(self, deduplication_window_seconds: int, clock=time.time):
        """
        Initialize the deduplicator with a configurable time window.

        Args:
            deduplication_window_seconds: Time window (in seconds) for deduplication.
            clock: Optional function to override the default time source (for testing).
        """
        if deduplication_window_seconds <= 0:
            raise ValueError("Deduplication window must be positive.")

        self.deduplication_window_seconds = deduplication_window_seconds
        self.clock = clock
        self.processed_opportunities: Dict[str, float] = {}

    def _generate_opportunity_id(
        self,
        symbol: str,
        recommendation_type: str,
        detection_time: Optional[Union[int, float]] = None,
        key_elements: Optional[str] = None,
    ) -> str:
        """
        Generate a deterministic identifier for an opportunity.

        Args:
            symbol: Financial instrument symbol.
            recommendation_type: Type of recommendation or signal.
            detection_time: Time when the opportunity was detected (defaults to current time).
            key_elements: Optional additional elements to include in the identifier.

        Returns:
            A deterministic SHA-256 hash of the opportunity attributes.
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string.")
        if not recommendation_type or not isinstance(recommendation_type, str):
            raise ValueError("Recommendation type must be a non-empty string.")

        timestamp = detection_time if detection_time is not None else self.clock()
        identifier_data = f"{symbol}:{recommendation_type}:{timestamp}"
        if key_elements:
            identifier_data += f":{key_elements}"

        return hashlib.sha256(identifier_data.encode()).hexdigest()

    def is_duplicate(self, opportunity_id: str) -> bool:
        """
        Check if an opportunity has already been processed within the deduplication window.

        Args:
            opportunity_id: The identifier of the opportunity.

        Returns:
            True if the opportunity is a duplicate, False otherwise.
        """
        if not opportunity_id or not isinstance(opportunity_id, str):
            raise ValueError("Opportunity ID must be a non-empty string.")

        processed_time = self.processed_opportunities.get(opportunity_id)
        if processed_time is None:
            return False

        return (self.clock() - processed_time) <= self.deduplication_window_seconds

    def mark_processed(self, opportunity_id: str) -> None:
        """
        Mark an opportunity as processed.

        Args:
            opportunity_id: The identifier of the opportunity.
        """
        if not opportunity_id or not isinstance(opportunity_id, str):
            raise ValueError("Opportunity ID must be a non-empty string.")

        self.processed_opportunities[opportunity_id] = self.clock()

    def should_process(self, opportunity_id: str) -> bool:
        """
        Determine if an opportunity should be processed (i.e., not a duplicate).

        Args:
            opportunity_id: The identifier of the opportunity.

        Returns:
            True if the opportunity should be processed, False otherwise.
        """
        return not self.is_duplicate(opportunity_id)

    def clear_expired(self) -> None:
        """
        Clear expired entries from the deduplication storage.
        """
        current_time = self.clock()
        expired_ids = [
            opp_id
            for opp_id, processed_time in self.processed_opportunities.items()
            if (current_time - processed_time) > self.deduplication_window_seconds
        ]
        for opp_id in expired_ids:
            del self.processed_opportunities[opp_id]