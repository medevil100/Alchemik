"""
Read Service (Query Service) for ALCHEMIK runtime data.

This service provides read-only access to stored runtime data (cycles and MarketEvents).
It does NOT:
- start RuntimeService or any engines
- generate MarketEvents
- write to SQLite
- contain BUY/SELL logic
- expose raw SQLite connection objects

All data is returned as JSON-serializable dictionaries.
"""
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from application.sqlite_history_repository import SQLiteHistoryRepository

logger = logging.getLogger(__name__)

# Default pagination limits
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _clamp_limit(limit: int) -> int:
    """Clamp limit to valid range [1, MAX_LIMIT]."""
    if limit < 1:
        return DEFAULT_LIMIT
    if limit > MAX_LIMIT:
        return MAX_LIMIT
    return limit


def _clamp_offset(offset: int) -> int:
    """Ensure offset is non-negative."""
    return max(0, offset)


class RuntimeReadService:
    """
    Read-only service for querying stored runtime data.

    Uses SQLiteHistoryRepository internally. All methods return
    JSON-serializable dicts with ISO 8601 datetime strings.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the read service.

        Args:
            db_path: Path to the SQLite database. If None, uses
                     the default from RuntimeConfig. Accepts str or Path.
        """
        self._repo = SQLiteHistoryRepository(db_path=db_path)

    # ------------------------------------------------------------------
    # Health / metadata
    # ------------------------------------------------------------------

    def get_storage_health(self) -> Dict[str, Any]:
        """
        Return health information about the storage backend.

        Returns:
            Dict with: status, db_path (path only, not full system path exposed),
            journal_mode, schema_version, cycle_count, event_count.
        """
        try:
            summary = self._repo.get_storage_summary()
            return {
                "status": "ok",
                "db_available": True,
                "journal_mode": summary.get("journal_mode", "unknown"),
                "schema_version": summary.get("schema_version", 0),
                "cycle_count": summary.get("cycle_count", 0),
                "event_count": summary.get("event_count", 0),
            }
        except Exception as e:
            logger.error("Storage health check failed: %s", str(e))
            return {
                "status": "error",
                "db_available": False,
                "journal_mode": "unknown",
                "schema_version": 0,
                "cycle_count": 0,
                "event_count": 0,
                "error": "Database unavailable",
            }

    def get_runtime_statistics(self) -> Dict[str, Any]:
        """
        Return runtime statistics.

        Returns:
            Dict with cycle_count, event_count, latest_cycle info,
            storage summary (without full system path).
        """
        try:
            summary = self._repo.get_storage_summary()
            latest_cycles = self._repo.list_cycle_summaries(limit=1, offset=0)
            latest_cycle = latest_cycles[0] if latest_cycles else None

            return {
                "cycle_count": summary.get("cycle_count", 0),
                "event_count": summary.get("event_count", 0),
                "latest_cycle": latest_cycle,
                "storage": {
                    "journal_mode": summary.get("journal_mode", "unknown"),
                    "schema_version": summary.get("schema_version", 0),
                },
            }
        except Exception as e:
            logger.error("Failed to get runtime statistics: %s", str(e))
            return {
                "cycle_count": 0,
                "event_count": 0,
                "latest_cycle": None,
                "storage": None,
                "error": "Failed to retrieve statistics",
            }

    # ------------------------------------------------------------------
    # Cycles
    # ------------------------------------------------------------------

    def get_cycle(self, cycle_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single cycle by its ID.

        Args:
            cycle_id: The cycle identifier.

        Returns:
            Dict with cycle data, or None if not found.
        """
        try:
            return self._repo.get_cycle(cycle_id)
        except Exception as e:
            logger.error("Failed to get cycle %s: %s", cycle_id, str(e))
            return None

    def get_latest_cycles(self, limit: int = DEFAULT_LIMIT, offset: int = 0) -> Dict[str, Any]:
        """
        Return the most recent cycles (without full report JSON for listing).

        Args:
            limit: Maximum number of cycles (clamped to MAX_LIMIT).
            offset: Number of records to skip.

        Returns:
            Dict with items, limit, offset, returned.
        """
        limit = _clamp_limit(limit)
        offset = _clamp_offset(offset)

        try:
            summaries = self._repo.list_cycle_summaries(limit=limit, offset=offset)
            return {
                "items": summaries,
                "limit": limit,
                "offset": offset,
                "returned": len(summaries),
            }
        except Exception as e:
            logger.error("Failed to list cycles: %s", str(e))
            return {
                "items": [],
                "limit": limit,
                "offset": offset,
                "returned": 0,
                "error": "Failed to query cycles",
            }

    # ------------------------------------------------------------------
    # MarketEvents
    # ------------------------------------------------------------------

    def get_latest_market_events(self, limit: int = DEFAULT_LIMIT, offset: int = 0) -> Dict[str, Any]:
        """
        Return the most recent MarketEvents across all cycles.

        Args:
            limit: Maximum number of events (clamped to MAX_LIMIT).
            offset: Number of records to skip.

        Returns:
            Dict with items, limit, offset, returned.
        """
        limit = _clamp_limit(limit)
        offset = _clamp_offset(offset)

        try:
            events = self._repo.get_latest_market_events(limit=limit, offset=offset)
            # Strip internal fields
            items = [_strip_internal_fields(ev) for ev in events]
            return {
                "items": items,
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            }
        except Exception as e:
            logger.error("Failed to get latest market events: %s", str(e))
            return {
                "items": [],
                "limit": limit,
                "offset": offset,
                "returned": 0,
                "error": "Failed to query market events",
            }

    def get_market_events_by_ticker(
        self,
        ticker: str,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Return MarketEvents for a specific ticker.

        Args:
            ticker: Instrument ticker symbol.
            limit: Maximum number of events (clamped to MAX_LIMIT).
            offset: Number of records to skip.

        Returns:
            Dict with items, limit, offset, returned.
        """
        limit = _clamp_limit(limit)
        offset = _clamp_offset(offset)

        try:
            events = self._repo.get_market_events_by_ticker(
                ticker=ticker, limit=limit, offset=offset
            )
            items = [_strip_internal_fields(ev) for ev in events]
            return {
                "items": items,
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            }
        except Exception as e:
            logger.error("Failed to get market events for ticker %s: %s", ticker, str(e))
            return {
                "items": [],
                "limit": limit,
                "offset": offset,
                "returned": 0,
                "error": f"Failed to query market events for {ticker}",
            }

    def get_market_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single MarketEvent by its event_id.

        Args:
            event_id: The unique event identifier.

        Returns:
            Dict with event data, or None if not found.
        """
        try:
            event = self._repo.get_market_event_by_id(event_id)
            if event:
                return _strip_internal_fields(event)
            return None
        except Exception as e:
            logger.error("Failed to get market event %s: %s", event_id, str(e))
            return None

    def query_market_events(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        ticker: Optional[str] = None,
        market: Optional[str] = None,
        instrument_type: Optional[str] = None,
        event_family: Optional[str] = None,
        event_type: Optional[str] = None,
        priority_final: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query MarketEvents with optional filters.

        All filters are optional and applied via parameterized SQL.
        No dynamic SQL with user-value concatenation.

        Args:
            limit: Maximum number of events (clamped to MAX_LIMIT).
            offset: Number of records to skip.
            ticker: Filter by ticker (exact match).
            market: Filter by market (exact match).
            instrument_type: Filter by instrument_type (exact match).
            event_family: Filter by event_family (exact match).
            event_type: Filter by event_type (exact match).
            priority_final: Filter by priority_final (exact match).
            date_from: Filter by created_at >= this ISO datetime string.
            date_to: Filter by created_at <= this ISO datetime string.

        Returns:
            Dict with items, limit, offset, returned.
        """
        limit = _clamp_limit(limit)
        offset = _clamp_offset(offset)

        try:
            events = self._repo.query_market_events(
                limit=limit,
                offset=offset,
                ticker=ticker,
                market=market,
                instrument_type=instrument_type,
                event_family=event_family,
                event_type=event_type,
                priority_final=priority_final,
                date_from=date_from,
                date_to=date_to,
            )
            items = [_strip_internal_fields(ev) for ev in events]
            return {
                "items": items,
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            }
        except Exception as e:
            logger.error("Failed to query market events: %s", str(e))
            return {
                "items": [],
                "limit": limit,
                "offset": offset,
                "returned": 0,
                "error": "Failed to query market events",
            }


def _strip_internal_fields(event: Dict[str, Any]) -> Dict[str, Any]:
    """Remove internal fields (prefixed with _) from event dict."""
    return {k: v for k, v in event.items() if not k.startswith("_")}