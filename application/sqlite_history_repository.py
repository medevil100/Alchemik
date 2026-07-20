import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from config import RuntimeConfig

logger = logging.getLogger(__name__)


class SQLiteHistoryRepository:
    """
    Persistent repository for runtime cycle data and MarketEvents using SQLite.

    Uses WAL journal mode for safe concurrent access (RuntimeService + future readers).
    Schema is created idempotently on init. Short transactions, no long-held locks.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the SQLite repository.

        Args:
            db_path: Path to the SQLite database file.
                     If None, uses RuntimeConfig.get_db_path().
                     Accepts str or pathlib.Path.
        """
        if db_path is None:
            self.db_path: Path = RuntimeConfig.get_db_path()
        else:
            self.db_path: Path = Path(db_path) if not isinstance(db_path, Path) else db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    SCHEMA_VERSION = 1

    SQL_CREATE_TABLES = """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS cycles (
            cycle_id TEXT PRIMARY KEY,
            execution_time REAL,
            candidates_count INTEGER,
            success_count INTEGER,
            error_count INTEGER,
            status TEXT,
            error_message TEXT,
            report_json TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS market_events (
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
            created_at TEXT,
            FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
        );

        CREATE INDEX IF NOT EXISTS idx_market_events_cycle_id ON market_events(cycle_id);
        CREATE INDEX IF NOT EXISTS idx_market_events_ticker ON market_events(ticker);
        CREATE INDEX IF NOT EXISTS idx_market_events_created ON market_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_market_events_event_id ON market_events(event_id);
    """

    SQL_WAL_PRAGMAS = """
        PRAGMA journal_mode=WAL;
        PRAGMA busy_timeout=5000;
        PRAGMA foreign_keys=ON;
    """

    def _initialize_database(self):
        """Create schema and apply WAL pragmas idempotently."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            # Enable WAL and safety pragmas
            for pragma in self.SQL_WAL_PRAGMAS.strip().split(";"):
                pragma = pragma.strip()
                if pragma:
                    cursor.execute(pragma)

            # Create tables
            for stmt in self.SQL_CREATE_TABLES.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cursor.execute(stmt)

            # Set schema version if not already set
            cursor.execute("SELECT COUNT(*) FROM schema_version")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )

            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Cycles
    # ------------------------------------------------------------------

    def save_cycle(
        self,
        cycle_id: str,
        cycle_data: Dict[str, Any],
    ) -> None:
        """
        Save a cycle report to the database.

        Args:
            cycle_id: Unique identifier for the cycle.
            cycle_data: Data dictionary with keys:
                execution_time, candidates_count, success_count,
                error_count, report (CycleReport or dict).
        """
        report = cycle_data.get("report", {})
        # If report is a CycleReport or similar, convert to dict for JSON
        if hasattr(report, "start_time"):
            report_json = json.dumps(report, default=str, indent=2)
        else:
            report_json = json.dumps(report, default=str, indent=2)

        created_at = datetime.now().isoformat()
        status = cycle_data.get("status", "completed")
        error_message = cycle_data.get("error_message")

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cycles (
                    cycle_id, execution_time, candidates_count,
                    success_count, error_count, status, error_message,
                    report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    cycle_data.get("execution_time"),
                    cycle_data.get("candidates_count"),
                    cycle_data.get("success_count"),
                    cycle_data.get("error_count"),
                    status,
                    error_message,
                    report_json,
                    created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_cycle(self, cycle_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cycle report by its ID.

        Args:
            cycle_id: Unique identifier for the cycle.

        Returns:
            Dict with cycle data if found, None otherwise.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    cycle_id, execution_time, candidates_count,
                    success_count, error_count, status, error_message,
                    report_json, created_at
                FROM cycles
                WHERE cycle_id = ?
                """,
                (cycle_id,),
            )
            row = cursor.fetchone()

            if row:
                return {
                    "cycle_id": row[0],
                    "execution_time": row[1],
                    "candidates_count": row[2],
                    "success_count": row[3],
                    "error_count": row[4],
                    "status": row[5],
                    "error_message": row[6],
                    "report": json.loads(row[7]) if row[7] else {},
                    "created_at": row[8],
                }
            return None
        finally:
            conn.close()

    def list_cycles(self, limit: int = 50, offset: int = 0) -> List[str]:
        """
        List stored cycle IDs, newest first.

        Args:
            limit: Maximum number of IDs to return.
            offset: Number of records to skip.

        Returns:
            List of cycle IDs.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cycle_id FROM cycles ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_cycle_summaries(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Return recent cycle summaries (no full report JSON).

        Args:
            limit: Maximum number of summaries.
            offset: Number of records to skip.

        Returns:
            List of dicts with cycle metadata.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    cycle_id, execution_time, candidates_count,
                    success_count, error_count, status, error_message,
                    created_at
                FROM cycles
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
                """,
                (limit, offset),
            )
            return [
                {
                    "cycle_id": row[0],
                    "execution_time": row[1],
                    "candidates_count": row[2],
                    "success_count": row[3],
                    "error_count": row[4],
                    "status": row[5],
                    "error_message": row[6],
                    "created_at": row[7],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def delete_cycle(self, cycle_id: str) -> None:
        """
        Delete a cycle report and its associated MarketEvents.

        Args:
            cycle_id: Unique identifier for the cycle.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM market_events WHERE cycle_id = ?", (cycle_id,))
            cursor.execute("DELETE FROM cycles WHERE cycle_id = ?", (cycle_id,))
            conn.commit()
        finally:
            conn.close()

    def count(self) -> int:
        """
        Count the number of stored cycle reports.

        Returns:
            The number of cycles stored.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cycles")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # MarketEvents
    # ------------------------------------------------------------------

    def save_market_event(self, cycle_id: str, event_data: Dict[str, Any]) -> None:
        """
        Save a single MarketEvent to the database.

        Args:
            cycle_id: The cycle that produced this event.
            event_data: Dictionary representation of a MarketEvent
                        (as returned by MarketEvent.to_dict()).
        """
        event_json = json.dumps(event_data, default=str, indent=2)
        created_at = datetime.now().isoformat()

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO market_events (
                    cycle_id, event_id, ticker, market,
                    instrument_type, event_family, event_category,
                    event_type, event_subcategory, priority_raw,
                    priority_final, confidence_level, detection_source,
                    event_owner, event_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id,
                    event_data.get("event_id"),
                    event_data.get("ticker"),
                    event_data.get("market"),
                    event_data.get("instrument_type"),
                    event_data.get("event_family"),
                    event_data.get("event_category"),
                    event_data.get("event_type"),
                    event_data.get("event_subcategory"),
                    event_data.get("priority_raw"),
                    event_data.get("priority_final"),
                    event_data.get("confidence_level", 0.0),
                    event_data.get("detection_source"),
                    event_data.get("event_owner"),
                    event_json,
                    created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def save_market_events(
        self,
        cycle_id: str,
        events_data: List[Dict[str, Any]],
    ) -> None:
        """
        Save multiple MarketEvents in a single transaction.

        Args:
            cycle_id: The cycle that produced these events.
            events_data: List of MarketEvent dicts.
        """
        if not events_data:
            return

        created_at = datetime.now().isoformat()

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            for event_data in events_data:
                event_json = json.dumps(event_data, default=str, indent=2)
                cursor.execute(
                    """
                    INSERT INTO market_events (
                        cycle_id, event_id, ticker, market,
                        instrument_type, event_family, event_category,
                        event_type, event_subcategory, priority_raw,
                        priority_final, confidence_level, detection_source,
                        event_owner, event_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cycle_id,
                        event_data.get("event_id"),
                        event_data.get("ticker"),
                        event_data.get("market"),
                        event_data.get("instrument_type"),
                        event_data.get("event_family"),
                        event_data.get("event_category"),
                        event_data.get("event_type"),
                        event_data.get("event_subcategory"),
                        event_data.get("priority_raw"),
                        event_data.get("priority_final"),
                        event_data.get("confidence_level", 0.0),
                        event_data.get("detection_source"),
                        event_data.get("event_owner"),
                        event_json,
                        created_at,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def get_market_events_for_cycle(
        self,
        cycle_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all MarketEvents for a given cycle.

        Args:
            cycle_id: The cycle identifier.
            limit: Maximum number of events to return.
            offset: Number of records to skip.

        Returns:
            List of MarketEvent dicts.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_json FROM market_events
                WHERE cycle_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
                """,
                (cycle_id, limit, offset),
            )
            return [json.loads(row[0]) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_latest_market_events(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent MarketEvents across all cycles.

        Args:
            limit: Maximum number of events to return.
            offset: Number of records to skip.

        Returns:
            List of MarketEvent dicts.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_json, cycle_id, created_at
                FROM market_events
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
                """,
                (limit, offset),
            )
            results = []
            for row in cursor.fetchall():
                event = json.loads(row[0])
                event["_cycle_id"] = row[1]
                event["_saved_at"] = row[2]
                results.append(event)
            return results
        finally:
            conn.close()

    def get_market_events_by_ticker(
        self,
        ticker: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve MarketEvents for a specific ticker.

        Args:
            ticker: Instrument ticker symbol.
            limit: Maximum number of events to return.
            offset: Number of records to skip.

        Returns:
            List of MarketEvent dicts.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_json, cycle_id, created_at
                FROM market_events
                WHERE ticker = ?
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
                """,
                (ticker, limit, offset),
            )
            results = []
            for row in cursor.fetchall():
                event = json.loads(row[0])
                event["_cycle_id"] = row[1]
                event["_saved_at"] = row[2]
                results.append(event)
            return results
        finally:
            conn.close()

    def get_market_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single MarketEvent by its event_id.

        Args:
            event_id: The unique event identifier.

        Returns:
            Dict with event data if found, None otherwise.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_json, cycle_id, created_at
                FROM market_events
                WHERE event_id = ?
                LIMIT 1
                """,
                (event_id,),
            )
            row = cursor.fetchone()
            if row:
                event = json.loads(row[0])
                event["_cycle_id"] = row[1]
                event["_saved_at"] = row[2]
                return event
            return None
        finally:
            conn.close()

    def query_market_events(
        self,
        limit: int = 50,
        offset: int = 0,
        ticker: Optional[str] = None,
        market: Optional[str] = None,
        instrument_type: Optional[str] = None,
        event_family: Optional[str] = None,
        event_type: Optional[str] = None,
        priority_final: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query MarketEvents with optional filters. All filters are optional.
        Filters are applied via parameterized WHERE clauses. No dynamic SQL
        with string concatenation of user values.

        Args:
            limit: Maximum number of events to return.
            offset: Number of records to skip.
            ticker: Filter by ticker (exact match).
            market: Filter by market (exact match).
            instrument_type: Filter by instrument_type (exact match).
            event_family: Filter by event_family (exact match).
            event_type: Filter by event_type (exact match).
            priority_final: Filter by priority_final (exact match).
            date_from: Filter by created_at >= this ISO datetime.
            date_to: Filter by created_at <= this ISO datetime.

        Returns:
            List of MarketEvent dicts.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            where_clauses: List[str] = []
            params: List[Any] = []

            if ticker is not None:
                where_clauses.append("ticker = ?")
                params.append(ticker)
            if market is not None:
                where_clauses.append("market = ?")
                params.append(market)
            if instrument_type is not None:
                where_clauses.append("instrument_type = ?")
                params.append(instrument_type)
            if event_family is not None:
                where_clauses.append("event_family = ?")
                params.append(event_family)
            if event_type is not None:
                where_clauses.append("event_type = ?")
                params.append(event_type)
            if priority_final is not None:
                where_clauses.append("priority_final = ?")
                params.append(priority_final)
            if date_from is not None:
                where_clauses.append("created_at >= ?")
                params.append(date_from)
            if date_to is not None:
                where_clauses.append("created_at <= ?")
                params.append(date_to)

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            sql = f"""
                SELECT event_json, cycle_id, created_at
                FROM market_events
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
            """
            params.append(limit)
            params.append(offset)

            cursor.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                event = json.loads(row[0])
                event["_cycle_id"] = row[1]
                event["_saved_at"] = row[2]
                results.append(event)
            return results
        finally:
            conn.close()

    def count_market_events(self) -> int:
        """
        Count all stored MarketEvents.

        Returns:
            Total number of market events.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM market_events")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_storage_summary(self) -> Dict[str, Any]:
        """
        Return a summary of stored data.

        Returns:
            Dict with cycle_count, event_count, db_path, wal_mode.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM cycles")
            cycle_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM market_events")
            event_count = cursor.fetchone()[0]

            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]

            return {
                "cycle_count": cycle_count,
                "event_count": event_count,
                "db_path": str(self.db_path),
                "journal_mode": journal_mode,
                "schema_version": self.SCHEMA_VERSION,
            }
        finally:
            conn.close()