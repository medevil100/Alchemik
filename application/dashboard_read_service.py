"""
Dashboard Read Service for ALCHEMIK.

This service provides pre-aggregated dashboard data ready for JSON serialization.
It is a read-only layer that uses SQLiteHistoryRepository or RuntimeReadService
internally and performs all aggregations in SQLite.

It does NOT:
- depend on FastAPI
- know about Request/Response objects
- perform writes to the database
- start RuntimeService or any engines
- contain BUY/SELL logic or investment recommendations
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

from application.sqlite_history_repository import SQLiteHistoryRepository

logger = logging.getLogger(__name__)

# Default limits
DEFAULT_LATEST_EVENTS_LIMIT = 10
MAX_LATEST_EVENTS_LIMIT = 50
DEFAULT_TOP_TICKERS_LIMIT = 10
MAX_TOP_TICKERS_LIMIT = 50
DEFAULT_ACTIVITY_HOURS = 24
MIN_ACTIVITY_HOURS = 1
MAX_ACTIVITY_HOURS = 168


class DashboardReadService:
    """
    Read-only service for dashboard aggregation data.

    All methods return JSON-serializable dictionaries with ISO 8601 datetime strings.
    Queries are performed in SQLite, not by loading full tables into Python.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the dashboard service.

        Args:
            db_path: Path to the SQLite database. If None, uses the default
                     from RuntimeConfig. Accepts str or Path.
        """
        self._repo = SQLiteHistoryRepository(db_path=db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_dashboard_summary(
        self,
        latest_events_limit: int = DEFAULT_LATEST_EVENTS_LIMIT,
        top_tickers_limit: int = DEFAULT_TOP_TICKERS_LIMIT,
        activity_hours: int = DEFAULT_ACTIVITY_HOURS,
    ) -> Dict[str, Any]:
        """
        Return a complete dashboard summary with pre-aggregated data.

        Args:
            latest_events_limit: Max recent events to include (1-50).
            top_tickers_limit: Max top tickers to include (1-50).
            activity_hours: Hours window for activity aggregations (1-168).

        Returns:
            Dict with sections: generated_at, system, runtime,
            recent_activity, top_tickers, event_breakdown, latest_events.
        """
        # Clamp parameters to valid ranges
        latest_events_limit = max(1, min(latest_events_limit, MAX_LATEST_EVENTS_LIMIT))
        top_tickers_limit = max(1, min(top_tickers_limit, MAX_TOP_TICKERS_LIMIT))
        activity_hours = max(MIN_ACTIVITY_HOURS, min(activity_hours, MAX_ACTIVITY_HOURS))

        generated_at = datetime.now(timezone.utc).isoformat()

        try:
            # Gather all data in a single try-except block
            system_info = self._get_system_info()
            runtime_info = self._get_runtime_info()
            is_empty = runtime_info.get("is_empty", True)

            if is_empty:
                # Return minimal structure for empty database
                return self._empty_response(generated_at, system_info)

            recent_activity = self._get_recent_activity(activity_hours)
            top_tickers = self._get_top_tickers(top_tickers_limit, activity_hours)
            event_breakdown = self._get_event_breakdown(activity_hours)
            latest_events = self._get_latest_events(latest_events_limit)

            return {
                "generated_at": generated_at,
                "system": system_info,
                "runtime": runtime_info,
                "recent_activity": recent_activity,
                "top_tickers": top_tickers,
                "event_breakdown": event_breakdown,
                "latest_events": latest_events,
            }

        except Exception as e:
            logger.error("Failed to build dashboard summary: %s", str(e))
            return {
                "generated_at": generated_at,
                "system": {
                    "status": "error",
                    "database": "unavailable",
                    "journal_mode": "unknown",
                    "schema_version": None,
                },
                "runtime": {
                    "cycle_count": 0,
                    "event_count": 0,
                    "last_cycle": None,
                    "last_cycle_at": None,
                    "last_cycle_error_count": None,
                    "is_empty": True,
                },
                "recent_activity": {
                    "events_in_last_cycle": 0,
                    "events_last_24h": 0,
                    "unique_tickers_last_24h": 0,
                    "last_event_at": None,
                },
                "top_tickers": [],
                "event_breakdown": {
                    "by_event_family": [],
                    "by_event_type": [],
                    "by_priority": [],
                },
                "latest_events": [],
            }

    # ------------------------------------------------------------------
    # Internal aggregation methods
    # ------------------------------------------------------------------

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system/database status information."""
        try:
            summary = self._repo.get_storage_summary()
            return {
                "status": "ok",
                "database": "available",
                "journal_mode": summary.get("journal_mode", "unknown"),
                "schema_version": summary.get("schema_version", None),
            }
        except Exception as e:
            logger.error("Failed to get system info: %s", str(e))
            return {
                "status": "error",
                "database": "unavailable",
                "journal_mode": "unknown",
                "schema_version": None,
            }

    def _get_runtime_info(self) -> Dict[str, Any]:
        """Get runtime statistics including last cycle data."""
        try:
            summary = self._repo.get_storage_summary()
            cycle_count = summary.get("cycle_count", 0)
            event_count = summary.get("event_count", 0)

            if cycle_count == 0:
                return {
                    "cycle_count": 0,
                    "event_count": 0,
                    "last_cycle": None,
                    "last_cycle_at": None,
                    "last_cycle_error_count": None,
                    "is_empty": True,
                }

            # Get last cycle
            latest_cycles = self._repo.list_cycle_summaries(limit=1, offset=0)
            last_cycle = latest_cycles[0] if latest_cycles else None

            last_cycle_at = last_cycle.get("created_at") if last_cycle else None
            last_cycle_error_count = last_cycle.get("error_count") if last_cycle else None

            return {
                "cycle_count": cycle_count,
                "event_count": event_count,
                "last_cycle": last_cycle,
                "last_cycle_at": last_cycle_at,
                "last_cycle_error_count": last_cycle_error_count,
                "is_empty": False,
            }
        except Exception as e:
            logger.error("Failed to get runtime info: %s", str(e))
            return {
                "cycle_count": 0,
                "event_count": 0,
                "last_cycle": None,
                "last_cycle_at": None,
                "last_cycle_error_count": None,
                "is_empty": True,
            }

    def _get_recent_activity(self, activity_hours: int) -> Dict[str, Any]:
        """Get recent activity metrics."""
        try:
            events_in_last_cycle = self._repo.count_events_for_latest_cycle()
            events_last_n_hours = self._repo.count_market_events_since(hours=activity_hours)
            unique_tickers = self._repo.count_unique_tickers_since(hours=activity_hours)
            last_event_at = self._repo.get_last_market_event_time()

            return {
                "events_in_last_cycle": events_in_last_cycle,
                "events_last_24h": events_last_n_hours,
                "unique_tickers_last_24h": unique_tickers,
                "last_event_at": last_event_at,
            }
        except Exception as e:
            logger.error("Failed to get recent activity: %s", str(e))
            return {
                "events_in_last_cycle": 0,
                "events_last_24h": 0,
                "unique_tickers_last_24h": 0,
                "last_event_at": None,
            }

    def _get_top_tickers(self, limit: int, activity_hours: int) -> List[Dict[str, Any]]:
        """Get most active tickers with event counts and latest priority."""
        try:
            return self._repo.get_top_tickers_since(limit=limit, hours=activity_hours)
        except Exception as e:
            logger.error("Failed to get top tickers: %s", str(e))
            return []

    def _get_event_breakdown(self, activity_hours: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get event breakdown by family, type, and priority."""
        try:
            return {
                "by_event_family": self._repo.get_event_family_breakdown_since(hours=activity_hours),
                "by_event_type": self._repo.get_event_type_breakdown_since(hours=activity_hours),
                "by_priority": self._repo.get_priority_breakdown_since(hours=activity_hours),
            }
        except Exception as e:
            logger.error("Failed to get event breakdown: %s", str(e))
            return {
                "by_event_family": [],
                "by_event_type": [],
                "by_priority": [],
            }

    def _get_latest_events(self, limit: int) -> List[Dict[str, Any]]:
        """Get the most recent MarketEvents for dashboard display."""
        try:
            events = self._repo.get_latest_market_events(limit=limit, offset=0)
            # Strip internal fields and return minimal event info
            result = []
            for ev in events:
                result.append({
                    "event_id": ev.get("event_id"),
                    "timestamp_utc": ev.get("timestamp_utc"),
                    "ticker": ev.get("ticker"),
                    "market": ev.get("market"),
                    "event_family": ev.get("event_family"),
                    "event_type": ev.get("event_type"),
                    "priority_final": ev.get("priority_final"),
                    "confidence_level": ev.get("confidence_level"),
                })
            return result
        except Exception as e:
            logger.error("Failed to get latest events: %s", str(e))
            return []

    def _empty_response(
        self,
        generated_at: str,
        system_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return a valid dashboard structure for an empty database."""
        return {
            "generated_at": generated_at,
            "system": system_info,
            "runtime": {
                "cycle_count": 0,
                "event_count": 0,
                "last_cycle": None,
                "last_cycle_at": None,
                "last_cycle_error_count": None,
                "is_empty": True,
            },
            "recent_activity": {
                "events_in_last_cycle": 0,
                "events_last_24h": 0,
                "unique_tickers_last_24h": 0,
                "last_event_at": None,
            },
            "top_tickers": [],
            "event_breakdown": {
                "by_event_family": [],
                "by_event_type": [],
                "by_priority": [],
            },
            "latest_events": [],
        }