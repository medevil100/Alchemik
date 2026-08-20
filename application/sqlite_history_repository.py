import sqlite3
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
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

    SCHEMA_VERSION = 2

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
            signal_timing TEXT,
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
        CREATE UNIQUE INDEX IF NOT EXISTS idx_market_events_event_id ON market_events(event_id);

        CREATE TABLE IF NOT EXISTS event_outcomes (
            event_outcome_id TEXT PRIMARY KEY,
            market_event_id TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL DEFAULT 'PENDING',
            ticker TEXT NOT NULL,
            market TEXT NOT NULL DEFAULT '',
            detection_timestamp TEXT NOT NULL,
            base_price REAL,
            base_volume REAL,
            event_family TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL DEFAULT '',
            quality_level TEXT NOT NULL DEFAULT '',
            expected_horizons INTEGER NOT NULL DEFAULT 4,
            horizons_calculated INTEGER NOT NULL DEFAULT 0,
            horizons_failed INTEGER NOT NULL DEFAULT 0,
            horizons_skipped INTEGER NOT NULL DEFAULT 0,
            missing_horizons_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            rule_version TEXT NOT NULL DEFAULT '1.0.0',
            failure_reason TEXT,
            invalid_reason TEXT,
            FOREIGN KEY (market_event_id) REFERENCES market_events(event_id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_event_outcomes_market_event_id ON event_outcomes(market_event_id);
        CREATE INDEX IF NOT EXISTS idx_event_outcomes_state ON event_outcomes(state);
        CREATE INDEX IF NOT EXISTS idx_event_outcomes_ticker ON event_outcomes(ticker);

        CREATE TABLE IF NOT EXISTS session_outcomes (
            session_outcome_id TEXT PRIMARY KEY,
            event_outcome_id TEXT NOT NULL,
            horizon_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'PENDING',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            close_price REAL,
            price_change_pct REAL,
            price_change_abs REAL,
            volume REAL,
            volume_change_pct REAL,
            high_price REAL,
            low_price REAL,
            failure_reason TEXT,
            skip_reason TEXT,
            computed_at TEXT,
            rule_version TEXT,
            data_source TEXT,
            FOREIGN KEY (event_outcome_id) REFERENCES event_outcomes(event_outcome_id) ON DELETE RESTRICT,
            UNIQUE(event_outcome_id, horizon_id)
        );

        CREATE INDEX IF NOT EXISTS idx_session_outcomes_event_outcome_id ON session_outcomes(event_outcome_id);
        CREATE INDEX IF NOT EXISTS idx_session_outcomes_state ON session_outcomes(state);

        CREATE TABLE IF NOT EXISTS instrument_observations (
            observation_id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            terminated_at TEXT,
            termination_reason TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_obs_instrument_state
            ON instrument_observations(instrument_id, state);

        CREATE TABLE IF NOT EXISTS instrument_readings (
            reading_id TEXT PRIMARY KEY,
            observation_id TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            market_data_timestamp TEXT NOT NULL,
            scan_timestamp TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            source TEXT NOT NULL DEFAULT 'YahooFinance',
            prev_reading_id TEXT,
            data_completeness TEXT NOT NULL DEFAULT 'COMPLETE',
            revision_number INTEGER NOT NULL DEFAULT 1,
            supersedes_reading_id TEXT,
            FOREIGN KEY (observation_id) REFERENCES instrument_observations(observation_id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_identity
            ON instrument_readings(instrument_id, market_data_timestamp, revision_number);

        CREATE INDEX IF NOT EXISTS idx_readings_observation
            ON instrument_readings(observation_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_observation
            ON instrument_observations(instrument_id)
            WHERE state = 'ACTIVE';

        CREATE TABLE IF NOT EXISTS universe_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            sequence INTEGER NOT NULL UNIQUE,
            created_at TEXT,
            total_records INTEGER NOT NULL DEFAULT 0,
            unique_symbols INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS universe_instruments (
            symbol TEXT PRIMARY KEY,
            quote_type TEXT,
            exchange TEXT,
            market TEXT,
            currency TEXT,
            regular_market_price REAL,
            first_seen_at TEXT,
            last_seen_at TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            chart_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
            candles_received INTEGER NOT NULL DEFAULT 0,
            candles_valid INTEGER NOT NULL DEFAULT 0,
            candles_rejected INTEGER NOT NULL DEFAULT 0,
            rejection_reasons_json TEXT NOT NULL DEFAULT '{}',
            daily_status TEXT,
            daily_candles_received INTEGER NOT NULL DEFAULT 0,
            daily_candles_valid INTEGER NOT NULL DEFAULT 0,
            daily_candles_rejected INTEGER NOT NULL DEFAULT 0,
            daily_rejection_reasons_json TEXT NOT NULL DEFAULT '{}',
            intraday_status TEXT,
            intraday_candles_received INTEGER NOT NULL DEFAULT 0,
            intraday_candles_valid INTEGER NOT NULL DEFAULT 0,
            intraday_candles_rejected INTEGER NOT NULL DEFAULT 0,
            intraday_rejection_reasons_json TEXT NOT NULL DEFAULT '{}',
            baseline_status TEXT,
            last_reading_id TEXT
        );

        CREATE TABLE IF NOT EXISTS universe_snapshot_members (
            snapshot_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            present INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            first_seen_at TEXT,
            last_seen_at TEXT,
            chart_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
            candles_received INTEGER NOT NULL DEFAULT 0,
            candles_valid INTEGER NOT NULL DEFAULT 0,
            candles_rejected INTEGER NOT NULL DEFAULT 0,
            rejection_reasons_json TEXT NOT NULL DEFAULT '{}',
            daily_status TEXT,
            daily_candles_received INTEGER NOT NULL DEFAULT 0,
            daily_candles_valid INTEGER NOT NULL DEFAULT 0,
            daily_candles_rejected INTEGER NOT NULL DEFAULT 0,
            daily_rejection_reasons_json TEXT NOT NULL DEFAULT '{}',
            intraday_status TEXT,
            intraday_candles_received INTEGER NOT NULL DEFAULT 0,
            intraday_candles_valid INTEGER NOT NULL DEFAULT 0,
            intraday_candles_rejected INTEGER NOT NULL DEFAULT 0,
            intraday_rejection_reasons_json TEXT NOT NULL DEFAULT '{}',
            baseline_status TEXT,
            last_reading_id TEXT,
            PRIMARY KEY (snapshot_id, symbol),
            FOREIGN KEY (snapshot_id) REFERENCES universe_snapshots(snapshot_id)
        );

        CREATE INDEX IF NOT EXISTS idx_universe_members_snapshot
            ON universe_snapshot_members(snapshot_id);
    """

    SQL_WAL_PRAGMAS = """
        PRAGMA journal_mode=WAL;
        PRAGMA busy_timeout=5000;
        PRAGMA foreign_keys=ON;
    """

    SQL_MIGRATE_ADD_SIGNAL_TIMING = """
        ALTER TABLE market_events ADD COLUMN signal_timing TEXT
    """

    SQL_SELECT_EVENTS_WITHOUT_TIMING = """
        SELECT id, event_json FROM market_events
        WHERE signal_timing IS NULL OR signal_timing = ''
    """

    SQL_UPDATE_SIGNAL_TIMING = """
        UPDATE market_events SET signal_timing = ? WHERE id = ?
    """

    def _initialize_database(self):
        """Create schema and apply WAL pragmas idempotently."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Enable WAL and safety pragmas
            conn.executescript(self.SQL_WAL_PRAGMAS)
            # Create all tables, indexes, and triggers
            conn.executescript(self.SQL_CREATE_TABLES)

            # Set schema version if not already set
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM schema_version")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )
            conn.commit()
        finally:
            conn.close()

        # Run migration to add signal_timing column (idempotent)
        self._migrate_signal_timing()
        self._migrate_universe_registry()
        self._migrate_reading_revisions()
        self._migrate_event_outcome_fk()

    def _column_exists(self, cursor, table: str, column: str) -> bool:
        """Check whether *column* already exists in *table*."""
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

    def _migrate_universe_registry(self) -> None:
        """Idempotentna migracja rejestru uniwersum.

        Dodaje sequence do universe_snapshots oraz status/first_seen_at/
        last_seen_at do universe_snapshot_members. Dla starej bazy odtwarza
        historyczny status memberów deterministycznie z chronologii snapshotów
        (pierwszy -> NEW_IN_CURRENT_SCAN, kolejny -> ACTIVE, nieobecny ->
        MISSING_IN_CURRENT_SCAN) bez używania universe_instruments.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            for col, ddl in (
                ("status", "ALTER TABLE universe_snapshot_members ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE'"),
                ("first_seen_at", "ALTER TABLE universe_snapshot_members ADD COLUMN first_seen_at TEXT"),
                ("last_seen_at", "ALTER TABLE universe_snapshot_members ADD COLUMN last_seen_at TEXT"),
            ):
                if not self._column_exists(cursor, "universe_snapshot_members", col):
                    cursor.execute(ddl)
            # Krok 4/8 — migracja daily/intraday (idempotentna)
            for table in ("universe_instruments", "universe_snapshot_members"):
                for col, ddl in (
                    ("daily_status", f"ALTER TABLE {table} ADD COLUMN daily_status TEXT"),
                    ("daily_candles_received", f"ALTER TABLE {table} ADD COLUMN daily_candles_received INTEGER NOT NULL DEFAULT 0"),
                    ("daily_candles_valid", f"ALTER TABLE {table} ADD COLUMN daily_candles_valid INTEGER NOT NULL DEFAULT 0"),
                    ("daily_candles_rejected", f"ALTER TABLE {table} ADD COLUMN daily_candles_rejected INTEGER NOT NULL DEFAULT 0"),
                    ("daily_rejection_reasons_json", f"ALTER TABLE {table} ADD COLUMN daily_rejection_reasons_json TEXT NOT NULL DEFAULT '{{}}'"),
                    ("intraday_status", f"ALTER TABLE {table} ADD COLUMN intraday_status TEXT"),
                    ("intraday_candles_received", f"ALTER TABLE {table} ADD COLUMN intraday_candles_received INTEGER NOT NULL DEFAULT 0"),
                    ("intraday_candles_valid", f"ALTER TABLE {table} ADD COLUMN intraday_candles_valid INTEGER NOT NULL DEFAULT 0"),
                    ("intraday_candles_rejected", f"ALTER TABLE {table} ADD COLUMN intraday_candles_rejected INTEGER NOT NULL DEFAULT 0"),
                    ("intraday_rejection_reasons_json", f"ALTER TABLE {table} ADD COLUMN intraday_rejection_reasons_json TEXT NOT NULL DEFAULT '{{}}'"),
                ):
                    if not self._column_exists(cursor, table, col):
                        cursor.execute(ddl)
            if not self._column_exists(cursor, "universe_snapshots", "sequence"):
                cursor.execute("ALTER TABLE universe_snapshots ADD COLUMN sequence INTEGER")
                cursor.execute(
                    """UPDATE universe_snapshots
                       SET sequence = (SELECT COUNT(*) FROM universe_snapshots s2
                                       WHERE (s2.created_at, s2.snapshot_id) <=
                                             (universe_snapshots.created_at, universe_snapshots.snapshot_id))"""
                )
            cursor.execute("SELECT COUNT(*) FROM universe_snapshot_members WHERE status != 'ACTIVE' AND status != 'NEW_IN_CURRENT_SCAN' AND status != 'MISSING_IN_CURRENT_SCAN'")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """SELECT snapshot_id, symbol, present FROM universe_snapshot_members
                       ORDER BY (SELECT COALESCE(sequence, 0) FROM universe_snapshots
                                 WHERE universe_snapshots.snapshot_id = universe_snapshot_members.snapshot_id),
                                symbol"""
                )
                rows = cursor.fetchall()
                if rows:
                    first_seen = {}
                    for snapshot_id, symbol, present in rows:
                        if symbol not in first_seen:
                            first_seen[symbol] = snapshot_id
                    for snapshot_id, symbol, present in rows:
                        if present == 0:
                            status = "MISSING_IN_CURRENT_SCAN"
                        elif snapshot_id == first_seen.get(symbol):
                            status = "NEW_IN_CURRENT_SCAN"
                        else:
                            status = "ACTIVE"
                        cursor.execute(
                            """UPDATE universe_snapshot_members
                               SET status = ?,
                                   first_seen_at = COALESCE(first_seen_at, (SELECT MIN(created_at) FROM universe_snapshots WHERE universe_snapshots.snapshot_id = universe_snapshot_members.snapshot_id)),
                                   last_seen_at = COALESCE(last_seen_at, (SELECT MAX(created_at) FROM universe_snapshots WHERE universe_snapshots.snapshot_id = universe_snapshot_members.snapshot_id))
                               WHERE snapshot_id = ? AND symbol = ?""",
                            (status, snapshot_id, symbol),
                        )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_reading_revisions(self) -> None:
        """Transakcyjna, idempotentna migracja instrument_readings do modelu rewizji.

        - dodaje revision_number (INTEGER NOT NULL DEFAULT 1) oraz
          supersedes_reading_id (TEXT);
        - istniejące rekordy otrzymują revision 1 oraz supersedes NULL;
        - przebudowuje unikalny indeks idx_readings_identity na
          (instrument_id, market_data_timestamp, revision_number);
        - rollback przy błędzie; żadnego DELETE ani nadpisywania wersji.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            if not self._column_exists(cursor, "instrument_readings", "revision_number"):
                cursor.execute(
                    "ALTER TABLE instrument_readings ADD COLUMN "
                    "revision_number INTEGER NOT NULL DEFAULT 1"
                )
            if not self._column_exists(cursor, "instrument_readings", "supersedes_reading_id"):
                cursor.execute(
                    "ALTER TABLE instrument_readings ADD COLUMN "
                    "supersedes_reading_id TEXT"
                )

            # Istniejące rekordy -> revision 1, supersedes NULL
            cursor.execute(
                "UPDATE instrument_readings "
                "SET revision_number = 1, supersedes_reading_id = NULL "
                "WHERE revision_number IS NULL OR revision_number < 1"
            )

            # Przebudowa unikalnego indeksu tożsamości na identity + revision
            cursor.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'index' AND name = 'idx_readings_identity'"
            )
            row = cursor.fetchone()
            if row is not None and "revision_number" not in (row[0] or ""):
                cursor.execute("DROP INDEX idx_readings_identity")
            cursor.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_identity
                   ON instrument_readings(instrument_id, market_data_timestamp, revision_number)"""
            )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_event_outcome_fk(self) -> None:
        """Idempotentna migracja FK EventOutcome -> MarketEvent.

        - zapewnia jednoznaczny UNIQUE na market_events.event_id (wymagany
          przez FK event_outcomes.market_event_id REFERENCES
          market_events(event_id));
        - przed utworzeniem UNIQUE sprawdza duplikaty event_id — jeżeli
          istnieją, przerywa migrację jawnym błędem (RuntimeError) i wykonuje
          rollback, nie zmieniając danych;
        - ewentualny stary nieunikalny indeks idx_market_events_event_id jest
          bezpiecznie zastępowany indeksem UNIQUE o tej samej nazwie;
        - nie usuwa, nie łączy i nie zmienia wartości event_id;
        - ponowne otwarcie jest idempotentne.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            # 1. Czy istnieje już UNIQUE na event_id?
            cursor.execute("PRAGMA index_list(market_events)")
            unique_exists = False
            old_index_exists = False
            for row in cursor.fetchall():
                index_name = row[1]
                is_unique = bool(row[2])
                cursor.execute(f"PRAGMA index_info({index_name})")
                columns = [info[2] for info in cursor.fetchall()]
                if "event_id" in columns:
                    if is_unique:
                        unique_exists = True
                    if index_name == "idx_market_events_event_id":
                        old_index_exists = True

            if unique_exists:
                conn.commit()
                return

            # 2. Sprawdź duplikaty event_id
            cursor.execute(
                """SELECT event_id, COUNT(*)
                   FROM market_events
                   GROUP BY event_id
                   HAVING COUNT(*) > 1"""
            )
            duplicates = cursor.fetchall()
            if duplicates:
                duplicate_list = ", ".join(repr(row[0]) for row in duplicates)
                raise RuntimeError(
                    "Migration FK event_outcomes -> market_events: duplicate "
                    f"market_events.event_id found ({duplicate_list}); cannot "
                    "create UNIQUE index. Migration aborted, no data changed."
                )

            # 3. Zastąp stary nieunikalny indeks indeksem UNIQUE
            if old_index_exists:
                cursor.execute("DROP INDEX idx_market_events_event_id")
            cursor.execute(
                """CREATE UNIQUE INDEX idx_market_events_event_id
                   ON market_events(event_id)"""
            )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_signal_timing(self) -> None:
        """
        Migrate: add ``signal_timing`` column + backfill existing rows.

        This is idempotent — calling it multiple times is safe.
        Existing rows are classified using the canonical
        ``config.signal_timing.lookup_signal_timing()`` mapping
        based on the stored ``event_type`` from ``event_json``.
        """
        from config.signal_timing import lookup_signal_timing

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            # 1. Add column if it doesn't exist
            if not self._column_exists(cursor, "market_events", "signal_timing"):
                cursor.execute(self.SQL_MIGRATE_ADD_SIGNAL_TIMING)
                logger.info("Migration: added signal_timing column to market_events")

            # 2. Backfill existing rows
            cursor.execute(self.SQL_SELECT_EVENTS_WITHOUT_TIMING)
            rows = cursor.fetchall()

            if rows:
                updated = 0
                for row_id, event_json_str in rows:
                    event_data = json.loads(event_json_str)
                    event_type = event_data.get("event_type")
                    if not event_type:
                        raise ValueError(
                            f"Migration error: row id={row_id} has no event_type "
                            f"in event_json. Cannot classify signal_timing."
                        )
                    timing = lookup_signal_timing(event_type)
                    cursor.execute(
                        self.SQL_UPDATE_SIGNAL_TIMING,
                        (timing.value, row_id),
                    )
                    updated += 1

                logger.info(
                    "Migration: backfilled signal_timing for %d existing rows",
                    updated,
                )

            conn.commit()
        except Exception:
            logger.exception("Migration signal_timing failed")
            conn.rollback()
            raise
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
        # If report is a CycleReport dataclass, convert to dict so that the
        # full report (including diagnostics["trace"]) persists as JSON,
        # not as a flattened str(dataclass).
        if hasattr(report, "start_time") and is_dataclass(report):
            report_json = json.dumps(asdict(report), default=str, indent=2)
        else:
            report_json = json.dumps(report, default=str, indent=2)

        created_at = datetime.now(timezone.utc).isoformat()
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
        created_at = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO market_events (
                    cycle_id, event_id, ticker, market,
                    instrument_type, event_family, event_category,
                    event_type, event_subcategory, signal_timing,
                    priority_raw, priority_final, confidence_level,
                    detection_source, event_owner, event_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    event_data.get("signal_timing"),
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

        created_at = datetime.now(timezone.utc).isoformat()

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
                        event_type, event_subcategory, signal_timing,
                        priority_raw, priority_final, confidence_level,
                        detection_source, event_owner, event_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        event_data.get("signal_timing"),
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
    # Dashboard aggregation queries
    # ------------------------------------------------------------------

    def _suffix_hours(self, hours: int) -> str:
        """
        Return a SQLite time modifier string for the given number of hours.

        Args:
            hours: Number of hours (may be negative for future times).

        Returns:
            String like '-24 hours' or '1 hours' that SQLite datetime() understands.
        """
        if hours >= 0:
            return f"-{hours} hours"
        else:
            return f"{abs(hours)} hours"

    def count_market_events_since(self, hours: int) -> int:
        """
        Count MarketEvents created within the last N hours.

        Uses datetime(created_at) to normalize timestamps regardless of
        ISO 8601 format variations (T separator, +00:00 offset, microseconds).

        Args:
            hours: Number of hours to look back.

        Returns:
            Count of market events since the given time.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM market_events
                WHERE datetime(created_at) >= datetime('now', ?)
                """,
                (self._suffix_hours(hours),),
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def count_unique_tickers_since(self, hours: int) -> int:
        """
        Count unique tickers that have events within the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            Count of unique tickers.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(DISTINCT ticker) FROM market_events
                WHERE datetime(created_at) >= datetime('now', ?)
                """,
                (self._suffix_hours(hours),),
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_last_market_event_time(self) -> Optional[str]:
        """
        Get the timestamp of the most recent MarketEvent.

        Returns:
            ISO 8601 datetime string or None if no events exist.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT created_at FROM market_events
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def count_events_for_latest_cycle(self) -> int:
        """
        Count the number of MarketEvents for the most recent cycle.

        Uses datetime(created_at) for comparison with fallback to rowid for
        deterministic ordering when timestamps are identical.

        Returns:
            Count of events in the latest cycle, or 0 if no cycles exist.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM market_events
                WHERE cycle_id = (
                    SELECT cycle_id FROM cycles
                    ORDER BY datetime(created_at) DESC, rowid DESC
                    LIMIT 1
                )
                """
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def count_events_for_cycle(self, cycle_id: str) -> int:
        """
        Count the number of MarketEvents for a specific cycle.

        Args:
            cycle_id: The cycle identifier.

        Returns:
            Count of events for that cycle.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM market_events
                WHERE cycle_id = ?
                """,
                (cycle_id,),
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_top_tickers_since(
        self, limit: int, hours: int
    ) -> List[Dict[str, Any]]:
        """
        Get the most active tickers within the last N hours.

        Priority_final is taken from the most recent event for each ticker
        (determined by datetime(created_at) within the group), ensuring a
        deterministic and semantically meaningful value.

        Tie-breaker: for events with identical created_at, the last inserted
        record (highest id) wins.

        Args:
            limit: Maximum number of tickers to return.
            hours: Number of hours to look back.

        Returns:
            List of dicts with ticker, event_count, last_event_at, priority_final.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    m.ticker,
                    m.event_count,
                    m.last_event_at,
                    COALESCE(
                        (SELECT me.priority_final
                         FROM market_events me
                         WHERE me.ticker = m.ticker
                           AND datetime(me.created_at) >= datetime('now', ?)
                         ORDER BY datetime(me.created_at) DESC, me.id DESC
                         LIMIT 1),
                        ''
                    ) AS priority_final
                FROM (
                    SELECT
                        ticker,
                        COUNT(*) AS event_count,
                        datetime(MAX(created_at)) AS last_event_at
                    FROM market_events
                    WHERE datetime(created_at) >= datetime('now', ?)
                    GROUP BY ticker
                ) m
                ORDER BY m.event_count DESC, m.last_event_at DESC
                LIMIT ?
                """,
                (self._suffix_hours(hours), self._suffix_hours(hours), limit),
            )
            return [
                {
                    "ticker": row[0],
                    "event_count": row[1],
                    "last_event_at": row[2],
                    "priority_final": row[3],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_event_family_breakdown_since(
        self, hours: int
    ) -> List[Dict[str, Any]]:
        """
        Aggregate event counts by event_family within the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of dicts with event_family and count.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    event_family,
                    COUNT(*) AS count
                FROM market_events
                WHERE datetime(created_at) >= datetime('now', ?)
                GROUP BY event_family
                ORDER BY count DESC
                """,
                (self._suffix_hours(hours),),
            )
            return [
                {"event_family": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_event_type_breakdown_since(
        self, hours: int
    ) -> List[Dict[str, Any]]:
        """
        Aggregate event counts by event_type within the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of dicts with event_type and count.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    event_type,
                    COUNT(*) AS count
                FROM market_events
                WHERE datetime(created_at) >= datetime('now', ?)
                GROUP BY event_type
                ORDER BY count DESC
                """,
                (self._suffix_hours(hours),),
            )
            return [
                {"event_type": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_priority_breakdown_since(
        self, hours: int
    ) -> List[Dict[str, Any]]:
        """
        Aggregate event counts by priority_final within the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of dicts with priority and count.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    priority_final,
                    COUNT(*) AS count
                FROM market_events
                WHERE datetime(created_at) >= datetime('now', ?)
                GROUP BY priority_final
                ORDER BY count DESC
                """,
                (self._suffix_hours(hours),),
            )
            return [
                {"priority": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # OutcomeRepository contract methods (KROK 3E)
    # ------------------------------------------------------------------

    def get_all_market_event_ids(self) -> set[str]:
        """Return all MarketEvent.event_id values stored in the database."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id FROM market_events")
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_market_event_by_id(self, event_id: str):
        """
        Return a real MarketEvent object for the given event_id, or None.

        Reconstructs the MarketEvent from its JSON representation stored
        in the database. Uses MarketEvent.from_dict() if available,
        otherwise returns the raw dict (for duck-typing compatibility
        with OutcomeComputer which accesses attributes like .ticker,
        .market, .timestamp_utc, .price_data, .volume_data, etc.).

        Returns:
            MarketEvent object if found, None otherwise.
        """
        from data.models.market_event import MarketEvent

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_json FROM market_events
                WHERE event_id = ?
                LIMIT 1
                """,
                (event_id,),
            )
            row = cursor.fetchone()
            if row:
                event_dict = json.loads(row[0])
                # Reconstruct MarketEvent from dict
                if hasattr(MarketEvent, "from_dict"):
                    return MarketEvent.from_dict(event_dict)
                else:
                    # Fallback: construct directly from fields
                    from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel
                    from data.models.price_data import PriceData
                    from data.models.volume_data import VolumeData
                    ts = event_dict.get("timestamp_utc")
                    if ts:
                        ts = datetime.fromisoformat(ts)
                    else:
                        ts = datetime.now(timezone.utc)

                    instrument_type = event_dict.get("instrument_type", "STOCK_GPW")
                    if isinstance(instrument_type, str):
                        try:
                            instrument_type = InstrumentType(instrument_type)
                        except (ValueError, TypeError):
                            instrument_type = InstrumentType.STOCK_GPW

                    event_family = event_dict.get("event_family", "TECHNICAL")
                    if isinstance(event_family, str):
                        try:
                            event_family = EventFamily(event_family)
                        except (ValueError, TypeError):
                            event_family = EventFamily.TECHNICAL

                    priority_raw = event_dict.get("priority_raw", "MEDIUM")
                    if isinstance(priority_raw, str):
                        try:
                            priority_raw = PriorityLevel(priority_raw)
                        except (ValueError, TypeError):
                            priority_raw = PriorityLevel.MEDIUM

                    price_data = None
                    pd_dict = event_dict.get("price_data")
                    if pd_dict and isinstance(pd_dict, dict):
                        price_data = PriceData(
                            open=pd_dict.get("open", 0.0),
                            high=pd_dict.get("high", 0.0),
                            low=pd_dict.get("low", 0.0),
                            close=pd_dict.get("close", 0.0),
                            prev_close=pd_dict.get("prev_close", 0.0),
                            change_pct=pd_dict.get("change_pct", 0.0),
                            change_abs=pd_dict.get("change_abs", 0.0),
                        )

                    volume_data = None
                    vd_dict = event_dict.get("volume_data")
                    if vd_dict and isinstance(vd_dict, dict):
                        volume_data = VolumeData(
                            current_volume=vd_dict.get("current_volume", 0.0),
                            avg_volume=vd_dict.get("avg_volume", 0.0),
                            volume_ratio=vd_dict.get("volume_ratio", 1.0),
                            direction=vd_dict.get("direction", ""),
                        )

                    event = MarketEvent(
                        event_id=event_dict.get("event_id", event_id),
                        timestamp_utc=ts,
                        ticker=event_dict.get("ticker", ""),
                        market=event_dict.get("market", ""),
                        instrument_type=instrument_type,
                        event_family=event_family,
                        event_category=event_dict.get("event_category", ""),
                        event_type=event_dict.get("event_type", ""),
                        priority_raw=priority_raw,
                        confidence_level=event_dict.get("confidence_level", 0.0),
                        detection_source=event_dict.get("detection_source", ""),
                        event_owner=EventOwner.TechnicalEngine,
                        price_data=price_data,
                        volume_data=volume_data,
                    )
                    # Restore quality_level if present
                    ql = event_dict.get("quality_level")
                    if ql:
                        try:
                            event.quality_level = PriorityLevel(ql) if isinstance(ql, str) else ql
                        except (ValueError, TypeError):
                            pass
                    return event
            return None
        finally:
            conn.close()

    def get_all_event_outcome_ids(self) -> set[str]:
        """Return all market_event_id values that already have an EventOutcome."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT market_event_id FROM event_outcomes")
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    def save_event_outcome(self, event_outcome) -> None:
        """
        Save or update an EventOutcome object to the database.

        Args:
            event_outcome: EventOutcome dataclass instance.
        """
        import json
        from datetime import datetime

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(
                """
                INSERT INTO event_outcomes (
                    event_outcome_id, market_event_id, state, ticker, market,
                    detection_timestamp, base_price, base_volume,
                    event_family, event_type, quality_level,
                    expected_horizons, horizons_calculated, horizons_failed,
                    horizons_skipped, missing_horizons_json, created_at,
                    rule_version, failure_reason, invalid_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_outcome_id) DO UPDATE SET
                    market_event_id = excluded.market_event_id,
                    state = excluded.state,
                    ticker = excluded.ticker,
                    market = excluded.market,
                    detection_timestamp = excluded.detection_timestamp,
                    base_price = excluded.base_price,
                    base_volume = excluded.base_volume,
                    event_family = excluded.event_family,
                    event_type = excluded.event_type,
                    quality_level = excluded.quality_level,
                    expected_horizons = excluded.expected_horizons,
                    horizons_calculated = excluded.horizons_calculated,
                    horizons_failed = excluded.horizons_failed,
                    horizons_skipped = excluded.horizons_skipped,
                    missing_horizons_json = excluded.missing_horizons_json,
                    created_at = excluded.created_at,
                    rule_version = excluded.rule_version,
                    failure_reason = excluded.failure_reason,
                    invalid_reason = excluded.invalid_reason
                """,
                (
                    event_outcome.event_outcome_id,
                    event_outcome.market_event_id,
                    event_outcome.state.value if hasattr(event_outcome.state, "value") else str(event_outcome.state),
                    event_outcome.ticker,
                    event_outcome.market,
                    event_outcome.detection_timestamp.isoformat() if hasattr(event_outcome.detection_timestamp, "isoformat") else str(event_outcome.detection_timestamp),
                    event_outcome.base_price,
                    event_outcome.base_volume,
                    event_outcome.event_family,
                    event_outcome.event_type,
                    event_outcome.quality_level,
                    event_outcome.expected_horizons,
                    event_outcome.horizons_calculated,
                    event_outcome.horizons_failed,
                    event_outcome.horizons_skipped,
                    json.dumps(event_outcome.missing_horizons),
                    event_outcome.created_at.isoformat() if hasattr(event_outcome.created_at, "isoformat") else str(event_outcome.created_at),
                    event_outcome.rule_version,
                    event_outcome.failure_reason,
                    event_outcome.invalid_reason,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_event_outcome_by_id(self, event_outcome_id: str):
        """
        Retrieve an EventOutcome by its own ID.

        Returns:
            EventOutcome object if found, None otherwise.
        """
        from data.models.event_outcome import EventOutcome, EventOutcomeState

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT event_outcome_id, market_event_id, state, ticker, market,
                   detection_timestamp, base_price, base_volume,
                   event_family, event_type, quality_level,
                   expected_horizons, horizons_calculated, horizons_failed,
                   horizons_skipped, missing_horizons_json, created_at,
                   rule_version, failure_reason, invalid_reason
                   FROM event_outcomes WHERE event_outcome_id = ?""",
                (event_outcome_id,),
            )
            row = cursor.fetchone()
            if row:
                return EventOutcome(
                    event_outcome_id=row[0],
                    market_event_id=row[1],
                    state=EventOutcomeState(row[2]) if row[2] else EventOutcomeState.PENDING,
                    ticker=row[3],
                    market=row[4],
                    detection_timestamp=datetime.fromisoformat(row[5]),
                    base_price=row[6],
                    base_volume=row[7],
                    event_family=row[8],
                    event_type=row[9],
                    quality_level=row[10],
                    expected_horizons=row[11],
                    horizons_calculated=row[12],
                    horizons_failed=row[13],
                    horizons_skipped=row[14],
                    missing_horizons=json.loads(row[15]) if row[15] else [],
                    created_at=datetime.fromisoformat(row[16]),
                    rule_version=row[17],
                    failure_reason=row[18],
                    invalid_reason=row[19],
                )
            return None
        finally:
            conn.close()

    def get_event_outcome_by_market_event_id(self, market_event_id: str):
        """
        Retrieve an EventOutcome by its source MarketEvent ID.

        Returns:
            EventOutcome object if found, None otherwise.
        """
        from data.models.event_outcome import EventOutcome, EventOutcomeState

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT event_outcome_id, market_event_id, state, ticker, market,
                   detection_timestamp, base_price, base_volume,
                   event_family, event_type, quality_level,
                   expected_horizons, horizons_calculated, horizons_failed,
                   horizons_skipped, missing_horizons_json, created_at,
                   rule_version, failure_reason, invalid_reason
                   FROM event_outcomes WHERE market_event_id = ?""",
                (market_event_id,),
            )
            row = cursor.fetchone()
            if row:
                return EventOutcome(
                    event_outcome_id=row[0],
                    market_event_id=row[1],
                    state=EventOutcomeState(row[2]) if row[2] else EventOutcomeState.PENDING,
                    ticker=row[3],
                    market=row[4],
                    detection_timestamp=datetime.fromisoformat(row[5]),
                    base_price=row[6],
                    base_volume=row[7],
                    event_family=row[8],
                    event_type=row[9],
                    quality_level=row[10],
                    expected_horizons=row[11],
                    horizons_calculated=row[12],
                    horizons_failed=row[13],
                    horizons_skipped=row[14],
                    missing_horizons=json.loads(row[15]) if row[15] else [],
                    created_at=datetime.fromisoformat(row[16]),
                    rule_version=row[17],
                    failure_reason=row[18],
                    invalid_reason=row[19],
                )
            return None
        finally:
            conn.close()

    def get_pending_session_outcomes(self) -> list:
        """
        Return all SessionOutcome objects in PENDING state.

        Returns:
            List of SessionOutcome dataclass instances.
        """
        from data.models.session_outcome import SessionOutcome, SessionOutcomeState

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_outcome_id, event_outcome_id, horizon_id,
                   state, attempt_count,
                   close_price, price_change_pct, price_change_abs,
                   volume, volume_change_pct,
                   high_price, low_price,
                   failure_reason, skip_reason,
                   computed_at, rule_version, data_source
                   FROM session_outcomes WHERE state = 'PENDING'"""
            )
            results = []
            for row in cursor.fetchall():
                results.append(SessionOutcome(
                    session_outcome_id=row[0],
                    event_outcome_id=row[1],
                    horizon_id=row[2],
                    state=SessionOutcomeState(row[3]) if row[3] else SessionOutcomeState.PENDING,
                    attempt_count=row[4],
                    close_price=row[5],
                    price_change_pct=row[6],
                    price_change_abs=row[7],
                    volume=row[8],
                    volume_change_pct=row[9],
                    high_price=row[10],
                    low_price=row[11],
                    failure_reason=row[12],
                    skip_reason=row[13],
                    computed_at=datetime.fromisoformat(row[14]) if row[14] else None,
                    rule_version=row[15],
                    data_source=row[16],
                ))
            return results
        finally:
            conn.close()

    def get_session_outcomes_for_event(self, event_outcome_id: str) -> list:
        """
        Return all SessionOutcome objects for a given EventOutcome.

        Args:
            event_outcome_id: The EventOutcome ID.

        Returns:
            List of SessionOutcome dataclass instances.
        """
        from data.models.session_outcome import SessionOutcome, SessionOutcomeState

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT session_outcome_id, event_outcome_id, horizon_id,
                   state, attempt_count,
                   close_price, price_change_pct, price_change_abs,
                   volume, volume_change_pct,
                   high_price, low_price,
                   failure_reason, skip_reason,
                   computed_at, rule_version, data_source
                   FROM session_outcomes WHERE event_outcome_id = ?""",
                (event_outcome_id,),
            )
            results = []
            for row in cursor.fetchall():
                results.append(SessionOutcome(
                    session_outcome_id=row[0],
                    event_outcome_id=row[1],
                    horizon_id=row[2],
                    state=SessionOutcomeState(row[3]) if row[3] else SessionOutcomeState.PENDING,
                    attempt_count=row[4],
                    close_price=row[5],
                    price_change_pct=row[6],
                    price_change_abs=row[7],
                    volume=row[8],
                    volume_change_pct=row[9],
                    high_price=row[10],
                    low_price=row[11],
                    failure_reason=row[12],
                    skip_reason=row[13],
                    computed_at=datetime.fromisoformat(row[14]) if row[14] else None,
                    rule_version=row[15],
                    data_source=row[16],
                ))
            return results
        finally:
            conn.close()

    def save_session_outcome(self, session) -> None:
        """
        Save or update a SessionOutcome object to the database.

        Args:
            session: SessionOutcome dataclass instance.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO session_outcomes (
                    session_outcome_id, event_outcome_id, horizon_id,
                    state, attempt_count,
                    close_price, price_change_pct, price_change_abs,
                    volume, volume_change_pct,
                    high_price, low_price,
                    failure_reason, skip_reason,
                    computed_at, rule_version, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_outcome_id,
                    session.event_outcome_id,
                    session.horizon_id,
                    session.state.value if hasattr(session.state, "value") else str(session.state),
                    session.attempt_count,
                    session.close_price,
                    session.price_change_pct,
                    session.price_change_abs,
                    session.volume,
                    session.volume_change_pct,
                    session.high_price,
                    session.low_price,
                    session.failure_reason,
                    session.skip_reason,
                    session.computed_at.isoformat() if session.computed_at and hasattr(session.computed_at, "isoformat") else str(session.computed_at) if session.computed_at else None,
                    session.rule_version,
                    session.data_source,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_event_outcomes_by_state(self, state) -> list:
        """
        Return all EventOutcome objects in the given state.

        Args:
            state: EventOutcomeState enum value.

        Returns:
            List of EventOutcome dataclass instances.
        """
        from data.models.event_outcome import EventOutcome, EventOutcomeState

        state_str = state.value if hasattr(state, "value") else str(state)
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT event_outcome_id, market_event_id, state, ticker, market,
                   detection_timestamp, base_price, base_volume,
                   event_family, event_type, quality_level,
                   expected_horizons, horizons_calculated, horizons_failed,
                   horizons_skipped, missing_horizons_json, created_at,
                   rule_version, failure_reason, invalid_reason
                   FROM event_outcomes WHERE state = ?""",
                (state_str,),
            )
            results = []
            for row in cursor.fetchall():
                results.append(EventOutcome(
                    event_outcome_id=row[0],
                    market_event_id=row[1],
                    state=EventOutcomeState(row[2]) if row[2] else EventOutcomeState.PENDING,
                    ticker=row[3],
                    market=row[4],
                    detection_timestamp=datetime.fromisoformat(row[5]),
                    base_price=row[6],
                    base_volume=row[7],
                    event_family=row[8],
                    event_type=row[9],
                    quality_level=row[10],
                    expected_horizons=row[11],
                    horizons_calculated=row[12],
                    horizons_failed=row[13],
                    horizons_skipped=row[14],
                    missing_horizons=json.loads(row[15]) if row[15] else [],
                    created_at=datetime.fromisoformat(row[16]),
                    rule_version=row[17],
                    failure_reason=row[18],
                    invalid_reason=row[19],
                ))
            return results
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # InstrumentReading / InstrumentObservation persistence (KROK 5)
    # ------------------------------------------------------------------

    def save_reading(self, observation, reading) -> str:
        """
        Atomowo zapisz InstrumentObservation i InstrumentReading z obsługą rewizji.

        Wyniki:
          * ACCEPTED                 — nowy timestamp, revision 1, supersedes NULL;
          * DUPLICATE_NO_OP          — identyczny timestamp i treść (bez zmian);
          * SOURCE_REVISION_ACCEPTED — ta sama tożsamość/źródło/Observation przy
                                       zmienionej treści → nowa rewizja
                                       (revision_number = najwyższa + 1,
                                        supersedes_reading_id = zastępowana wersja);
          * CONFLICT                 — obca tożsamość, uszkodzone supersedes albo
                                       prawdziwy konflikt treści
                                       (Observation → INTEGRITY_BREACHED);
          * STALE_TIMESTAMP          — starszy timestamp, odrzucony bez naruszenia.
        """
        instrument_id = observation.instrument_id
        observation_id = observation.observation_id
        market_ts = reading.market_data_timestamp
        market_ts_iso = market_ts.isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Obca tożsamość instrumentu → CONFLICT (nie jest rewizją)
        if reading.instrument_id != instrument_id:
            return "CONFLICT"

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            # 0. Terminalna Observation → ValueError (dotychczasowe zachowanie)
            cursor.execute(
                "SELECT state FROM instrument_observations WHERE observation_id=?",
                (observation_id,),
            )
            obs_row = cursor.fetchone()
            if obs_row is not None and obs_row[0] in (
                "INTEGRITY_BREACHED", "TERMINATED_DOMAIN", "TERMINATED_TECHNICAL",
            ):
                raise ValueError(
                    f"Cannot add reading to terminal observation {observation_id}"
                )

            # 1. Istniejąca najnowsza wersja dla tej tożsamości
            cursor.execute(
                """SELECT reading_id, open, high, low, close, volume,
                          data_completeness, source, observation_id, revision_number,
                          supersedes_reading_id
                   FROM instrument_readings
                   WHERE instrument_id = ? AND market_data_timestamp = ?
                   ORDER BY revision_number DESC
                   LIMIT 1""",
                (instrument_id, market_ts_iso),
            )
            existing = cursor.fetchone()

            if existing is not None:
                (ex_rdg_id, ex_open, ex_high, ex_low, ex_close, ex_volume,
                 ex_completeness, ex_source, ex_obs_id, ex_revision,
                 ex_supersedes) = existing

                same_content = (
                    (reading.open == ex_open) and
                    (reading.high == ex_high) and
                    (reading.low == ex_low) and
                    (reading.close == ex_close) and
                    (reading.volume == ex_volume) and
                    (reading.data_completeness == ex_completeness) and
                    (reading.source == ex_source)
                )

                reference = reading.supersedes_reading_id
                valid_ref = (
                    reference is None
                    or reference == ex_rdg_id
                )

                if same_content:
                    # Identyczna treść — rewizja niepotrzebna; uszkodzone
                    # supersedes przy identycznej treści = CONFLICT.
                    return "DUPLICATE_NO_OP" if valid_ref else "CONFLICT"

                # Zmieniona treść tego samego timestampu.
                if (reading.observation_id != ex_obs_id) or (reading.source != ex_source):
                    # Obca Observation albo obce źródło → prawdziwy CONFLICT.
                    self._terminate_observation_on_conflict(
                        cursor, instrument_id, market_ts_iso, now_iso,
                    )
                    conn.commit()
                    return "CONFLICT"

                if not valid_ref:
                    # Uszkodzone supersedes przy zmienionej treści → CONFLICT.
                    return "CONFLICT"

                # Poprawna rewizja źródła: ta sama tożsamość, Observation i źródło.
                new_revision = ex_revision + 1
                cursor.execute(
                    """INSERT INTO instrument_readings
                       (reading_id, observation_id, instrument_id,
                        market_data_timestamp, scan_timestamp,
                        open, high, low, close, volume,
                        source, prev_reading_id, data_completeness,
                        revision_number, supersedes_reading_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        reading.reading_id,
                        observation_id,
                        instrument_id,
                        market_ts_iso,
                        reading.scan_timestamp.isoformat(),
                        reading.open,
                        reading.high,
                        reading.low,
                        reading.close,
                        reading.volume,
                        reading.source,
                        ex_rdg_id,
                        reading.data_completeness,
                        new_revision,
                        ex_rdg_id,
                    ),
                )
                conn.commit()
                return "SOURCE_REVISION_ACCEPTED"

            # 2. STALE_TIMESTAMP check
            cursor.execute(
                """SELECT market_data_timestamp FROM instrument_readings
                   WHERE instrument_id = ?
                   ORDER BY market_data_timestamp DESC
                   LIMIT 1""",
                (instrument_id,),
            )
            last_row = cursor.fetchone()
            if last_row is not None and market_ts_iso < last_row[0]:
                return "STALE_TIMESTAMP"

            # 3. prev_reading_id — najnowsza rewizja najnowszego timestampu
            #    wyłącznie w obrębie bieżącej Observation (kontrakt KROK 5).
            prev_reading_id = None
            cursor.execute(
                """SELECT reading_id FROM instrument_readings
                   WHERE instrument_id = ? AND observation_id = ?
                   ORDER BY market_data_timestamp DESC, revision_number DESC
                   LIMIT 1""",
                (instrument_id, observation_id),
            )
            last_rdg = cursor.fetchone()
            if last_rdg is not None:
                prev_reading_id = last_rdg[0]

            # 4. Observation (non-destructive)
            cursor.execute(
                "SELECT observation_id, instrument_id, state "
                "FROM instrument_observations WHERE observation_id=?",
                (observation_id,),
            )
            existing_obs = cursor.fetchone()
            if existing_obs is None:
                self._insert_observation(cursor, observation, now_iso)
            else:
                ex_obs_id, ex_instr_id, ex_state = existing_obs
                if ex_state in ("INTEGRITY_BREACHED", "TERMINATED_DOMAIN", "TERMINATED_TECHNICAL"):
                    return "CONFLICT"
                if ex_instr_id != instrument_id:
                    return "CONFLICT"

            # 5. Nowy fakt — revision 1, supersedes NULL
            cursor.execute(
                """INSERT INTO instrument_readings
                   (reading_id, observation_id, instrument_id,
                    market_data_timestamp, scan_timestamp,
                    open, high, low, close, volume,
                    source, prev_reading_id, data_completeness,
                    revision_number, supersedes_reading_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    reading.reading_id,
                    observation_id,
                    instrument_id,
                    market_ts_iso,
                    reading.scan_timestamp.isoformat(),
                    reading.open,
                    reading.high,
                    reading.low,
                    reading.close,
                    reading.volume,
                    reading.source,
                    prev_reading_id,
                    reading.data_completeness,
                    1,
                    None,
                ),
            )

            conn.commit()
            return "ACCEPTED"

        except sqlite3.IntegrityError as exc:
            err_msg = str(exc).lower()
            # Partial UNIQUE index violation = second ACTIVE observation
            if "idx_one_active_observation" in err_msg:
                conn.rollback()
                raise ValueError(
                    f"Cannot create second ACTIVE observation for instrument {instrument_id}"
                )
            # UNIQUE constraint on reading identity → classify (wyścig)
            if "idx_readings_identity" in err_msg:
                conn.rollback()
                return self._handle_identity_conflict(
                    instrument_id, market_ts_iso, reading, observation_id, exc,
                )
            # All other integrity errors propagate as technical errors
            conn.rollback()
            raise
        finally:
            conn.close()

    def _terminate_observation_on_conflict(self, cursor, instrument_id, market_ts_iso, now_iso):
        """Atomowo zakończ ACTIVE Observation instrumentu w CONFLICT."""
        cursor.execute(
            """UPDATE instrument_observations
               SET state = 'INTEGRITY_BREACHED',
                   terminated_at = ?,
                   termination_reason = ?
               WHERE instrument_id = ? AND state = 'ACTIVE'""",
            (now_iso, f"Content conflict at {market_ts_iso}", instrument_id),
        )

    def _insert_observation(self, cursor, observation, now_iso):
        """Insert a new observation. Raises ValueError if INSERT fails
        due to partial UNIQUE index (second ACTIVE observation)."""
        try:
            cursor.execute(
                """INSERT INTO instrument_observations
                   (observation_id, instrument_id, state, created_at,
                    terminated_at, termination_reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    observation.observation_id,
                    observation.instrument_id,
                    observation.state,
                    observation.created_at.isoformat() if observation.created_at else now_iso,
                    observation.terminated_at.isoformat() if observation.terminated_at else None,
                    observation.termination_reason,
                ),
            )
        except sqlite3.IntegrityError:
            raise ValueError(
                f"Cannot create second ACTIVE observation "
                f"for instrument {observation.instrument_id}"
            )

    def _handle_identity_conflict(self, instrument_id, market_ts_iso, reading, observation_id, original_error):
        """When UNIQUE constraint on (instrument_id, market_data_timestamp)
        is violated, re-read the existing row and classify.
        If the row disappeared, re-raise the original error."""
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT r.open, r.high, r.low, r.close, r.volume,
                          r.data_completeness, r.source
                   FROM instrument_readings r
                   WHERE r.instrument_id = ? AND r.market_data_timestamp = ?
                   LIMIT 1""",
                (instrument_id, market_ts_iso),
            )
            ex = cursor.fetchone()
            if ex is None:
                raise original_error  # Row disappeared — propagate
            ex_open, ex_high, ex_low, ex_close, ex_volume, ex_completeness, ex_source = ex
            same_content = (
                (reading.open == ex_open) and
                (reading.high == ex_high) and
                (reading.low == ex_low) and
                (reading.close == ex_close) and
                (reading.volume == ex_volume) and
                (reading.data_completeness == ex_completeness) and
                (reading.source == ex_source)
            )
            if same_content:
                return "DUPLICATE_NO_OP"
            else:
                now_iso = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    """UPDATE instrument_observations
                       SET state = 'INTEGRITY_BREACHED',
                           terminated_at = ?,
                           termination_reason = ?
                       WHERE instrument_id = ? AND state = 'ACTIVE'""",
                    (now_iso, f"Content conflict at {market_ts_iso}", instrument_id),
                )
                conn.commit()
                return "CONFLICT"
        finally:
            conn.close()

    def load_observation(self, instrument_id: str):
        """
        Wczytaj ACTIVE InstrumentObservation po instrument_id.

        Zwraca InstrumentObservation lub None, jeżeli nie ma ACTIVE.
        """
        from data.models.instrument_observation import InstrumentObservation

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT observation_id, instrument_id, state, created_at,
                          terminated_at, termination_reason
                   FROM instrument_observations
                   WHERE instrument_id = ? AND state = 'ACTIVE'
                   LIMIT 1""",
                (instrument_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return InstrumentObservation(
                observation_id=row[0],
                instrument_id=row[1],
                state=row[2],
                created_at=datetime.fromisoformat(row[3]),
                terminated_at=datetime.fromisoformat(row[4]) if row[4] else None,
                termination_reason=row[5],
            )
        finally:
            conn.close()

    def restore_active_observations(self) -> list:
        """
        Restore all ACTIVE Observations with their last accepted Reading
        (by greatest market_data_timestamp).

        Returns a list of (InstrumentObservation, InstrumentReading) tuples.
        """
        from data.models.instrument_observation import InstrumentObservation
        from data.models.instrument_reading import InstrumentReading

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT o.observation_id, o.instrument_id, o.state,
                          o.created_at, o.terminated_at, o.termination_reason,
                          r.reading_id, r.instrument_id, r.market_data_timestamp,
                          r.scan_timestamp, r.open, r.high, r.low, r.close,
                          r.volume, r.source, r.prev_reading_id,
                          r.data_completeness, r.revision_number,
                          r.supersedes_reading_id
                   FROM instrument_observations o
                   JOIN instrument_readings r ON r.observation_id = o.observation_id
                   WHERE o.state = 'ACTIVE'
                     AND r.market_data_timestamp = (
                         SELECT MAX(r2.market_data_timestamp)
                         FROM instrument_readings r2
                         WHERE r2.observation_id = o.observation_id
                     )
                     AND r.revision_number = (
                         SELECT MAX(r3.revision_number)
                         FROM instrument_readings r3
                         WHERE r3.observation_id = o.observation_id
                           AND r3.market_data_timestamp = r.market_data_timestamp
                     )
                   ORDER BY o.instrument_id""",
            )

            results = []
            for row in cursor.fetchall():
                obs = InstrumentObservation(
                    observation_id=row[0],
                    instrument_id=row[1],
                    state=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    terminated_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    termination_reason=row[5],
                )

                reading = InstrumentReading(
                    reading_id=row[6],
                    observation_id=row[0],
                    instrument_id=row[7],
                    market_data_timestamp=datetime.fromisoformat(row[8]),
                    scan_timestamp=datetime.fromisoformat(row[9]),
                    open=row[10],
                    high=row[11],
                    low=row[12],
                    close=row[13],
                    volume=row[14],
                    source=row[15],
                    prev_reading_id=row[16],
                    data_completeness=row[17],
                    revision_number=row[18],
                    supersedes_reading_id=row[19],
                )

                results.append((obs, reading))

            return results
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Trwały rejestr uniwersum (Krok 3/8)
    # ------------------------------------------------------------------

    def save_universe_snapshot(self, snapshot) -> None:
        """Atomowo zapisz jeden snapshot uniwersum (snapshot + członków +
        instrumenty). Błąd któregokolwiek elementu wycofuje cały zapis."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            # 1. Snapshot główny — sequence nadawana w tej samej transakcji
            cursor.execute("SELECT COALESCE(MAX(sequence), 0) + 1 FROM universe_snapshots")
            seq = cursor.fetchone()[0]
            cursor.execute(
                """INSERT OR REPLACE INTO universe_snapshots
                   (snapshot_id, sequence, created_at, total_records, unique_symbols)
                   VALUES (?, ?, ?, ?, ?)""",
                (snapshot.snapshot_id, seq, snapshot.created_at,
                 snapshot.total_records, snapshot.unique_symbols),
            )

            # 2. Członkowie + instrumenty (atomowo w tej samej transakcji)
            seen = set()
            for member in snapshot.members:
                if member.symbol in seen:
                    continue
                seen.add(member.symbol)
                # Insert instrumentu, jeżeli nie istnieje (zachowaj first_seen_at)
                cursor.execute(
                    """INSERT OR IGNORE INTO universe_instruments
                       (symbol, quote_type, exchange, market, currency,
                        regular_market_price, first_seen_at, last_seen_at,
                        status, chart_status, candles_received, candles_valid,
                        candles_rejected, rejection_reasons_json,
                        daily_status, daily_candles_received, daily_candles_valid,
                        daily_candles_rejected, daily_rejection_reasons_json,
                        intraday_status, intraday_candles_received,
                        intraday_candles_valid, intraday_candles_rejected,
                        intraday_rejection_reasons_json,
                        baseline_status, last_reading_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (member.symbol, None, None, None, None, None,
                     member.first_seen_at if hasattr(member, "first_seen_at") else None,
                     member.last_seen_at if hasattr(member, "last_seen_at") else None,
                     "ACTIVE", "NOT_STARTED", 0, 0, 0, "{}",
                     None, 0, 0, 0, "{}",
                     None, 0, 0, 0, "{}",
                     None, None),
                )
                cursor.execute(
                    """UPDATE universe_instruments
                       SET last_seen_at = COALESCE(?, last_seen_at),
                           status = CASE WHEN ? IS NOT NULL THEN ? ELSE status END,
                           chart_status = CASE WHEN ? IS NOT NULL THEN ? ELSE chart_status END,
                           candles_valid = COALESCE(?, candles_valid),
                           candles_rejected = COALESCE(?, candles_rejected),
                           rejection_reasons_json = COALESCE(?, rejection_reasons_json),
                           daily_status = COALESCE(?, daily_status),
                           daily_candles_received = COALESCE(?, daily_candles_received),
                           daily_candles_valid = COALESCE(?, daily_candles_valid),
                           daily_candles_rejected = COALESCE(?, daily_candles_rejected),
                           daily_rejection_reasons_json = COALESCE(?, daily_rejection_reasons_json),
                           intraday_status = COALESCE(?, intraday_status),
                           intraday_candles_received = COALESCE(?, intraday_candles_received),
                           intraday_candles_valid = COALESCE(?, intraday_candles_valid),
                           intraday_candles_rejected = COALESCE(?, intraday_candles_rejected),
                           intraday_rejection_reasons_json = COALESCE(?, intraday_rejection_reasons_json),
                           baseline_status = COALESCE(?, baseline_status),
                           last_reading_id = COALESCE(?, last_reading_id)
                       WHERE symbol = ?""",
                    (member.last_seen_at if hasattr(member, "last_seen_at") else None,
                     member.status if hasattr(member, "status") else None,
                     member.status if hasattr(member, "status") else None,
                     member.chart_status, member.chart_status,
                     member.candles_valid if member.candles_valid >= 0 else None,
                     member.candles_rejected if member.candles_rejected >= 0 else None,
                     json.dumps(member.rejection_reasons or {}, default=str),
                     getattr(member, "daily_status", None),
                     getattr(member, "daily_candles_received", 0),
                     getattr(member, "daily_candles_valid", 0),
                     getattr(member, "daily_candles_rejected", 0),
                     json.dumps(getattr(member, "daily_rejection_reasons", None) or {}, default=str),
                     getattr(member, "intraday_status", None),
                     getattr(member, "intraday_candles_received", 0),
                     getattr(member, "intraday_candles_valid", 0),
                     getattr(member, "intraday_candles_rejected", 0),
                     json.dumps(getattr(member, "intraday_rejection_reasons", None) or {}, default=str),
                     member.baseline_status, member.last_reading_id,
                     member.symbol),
                )
                cursor.execute(
                    """INSERT OR REPLACE INTO universe_snapshot_members
                       (snapshot_id, symbol, present, status, first_seen_at,
                        last_seen_at, chart_status,
                        candles_received, candles_valid, candles_rejected,
                        rejection_reasons_json,
                        daily_status, daily_candles_received, daily_candles_valid,
                        daily_candles_rejected, daily_rejection_reasons_json,
                        intraday_status, intraday_candles_received,
                        intraday_candles_valid, intraday_candles_rejected,
                        intraday_rejection_reasons_json,
                        baseline_status, last_reading_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (snapshot.snapshot_id, member.symbol,
                     1 if member.present else 0,
                     member.status, member.first_seen_at, member.last_seen_at,
                     member.chart_status, member.candles_received,
                     member.candles_valid, member.candles_rejected,
                     json.dumps(member.rejection_reasons or {}, default=str),
                     getattr(member, "daily_status", None),
                     getattr(member, "daily_candles_received", 0),
                     getattr(member, "daily_candles_valid", 0),
                     getattr(member, "daily_candles_rejected", 0),
                     json.dumps(getattr(member, "daily_rejection_reasons", None) or {}, default=str),
                     getattr(member, "intraday_status", None),
                     getattr(member, "intraday_candles_received", 0),
                     getattr(member, "intraday_candles_valid", 0),
                     getattr(member, "intraday_candles_rejected", 0),
                     json.dumps(getattr(member, "intraday_rejection_reasons", None) or {}, default=str),
                     member.baseline_status, member.last_reading_id),
                )

            # 3. Dodaj nieobecnych jako członków present=0 (pełna matryca)
            cursor.execute("SELECT symbol FROM universe_instruments")
            known = {r[0] for r in cursor.fetchall()}
            for sym in sorted(known - seen):
                cursor.execute(
                    """INSERT OR REPLACE INTO universe_snapshot_members
                       (snapshot_id, symbol, present, status, chart_status)
                       VALUES (?, ?, 0, 'MISSING_IN_CURRENT_SCAN', 'NOT_STARTED')""",
                    (snapshot.snapshot_id, sym),
                )

            # 4. Oznacz wcześniej znane, nieobecne jako MISSING_IN_CURRENT_SCAN
            if seen:
                placeholders = ",".join("?" * len(seen))
                cursor.execute(
                    f"""UPDATE universe_instruments
                        SET status = 'MISSING_IN_CURRENT_SCAN'
                        WHERE symbol NOT IN ({placeholders})""",
                    tuple(sorted(seen)),
                )
            else:
                cursor.execute(
                    "UPDATE universe_instruments SET status = 'MISSING_IN_CURRENT_SCAN'"
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_current_universe(self) -> list:
        """Zwróć aktualne uniwersum (wszystkie instrumenty z rejestru)."""
        from data.models.universe_instrument import UniverseInstrument
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT symbol, quote_type, exchange, market, currency,
                          regular_market_price, first_seen_at, last_seen_at,
                          status, chart_status, candles_received, candles_valid,
                          candles_rejected, rejection_reasons_json,
                          daily_status, daily_candles_received,
                          daily_candles_valid, daily_candles_rejected,
                          daily_rejection_reasons_json,
                          intraday_status, intraday_candles_received,
                          intraday_candles_valid, intraday_candles_rejected,
                          intraday_rejection_reasons_json,
                          baseline_status, last_reading_id
                   FROM universe_instruments
                   ORDER BY symbol""",
            )
            return [
                UniverseInstrument(
                    symbol=r[0], quote_type=r[1], exchange=r[2], market=r[3],
                    currency=r[4], regular_market_price=r[5],
                    first_seen_at=r[6], last_seen_at=r[7],
                    status=r[8], chart_status=r[9],
                    candles_received=r[10], candles_valid=r[11],
                    candles_rejected=r[12],
                    rejection_reasons=json.loads(r[13]) if r[13] else {},
                    daily_status=r[14],
                    daily_candles_received=r[15],
                    daily_candles_valid=r[16],
                    daily_candles_rejected=r[17],
                    daily_rejection_reasons=json.loads(r[18]) if r[18] else {},
                    intraday_status=r[19],
                    intraday_candles_received=r[20],
                    intraday_candles_valid=r[21],
                    intraday_candles_rejected=r[22],
                    intraday_rejection_reasons=json.loads(r[23]) if r[23] else {},
                    baseline_status=r[24], last_reading_id=r[25],
                )
                for r in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_snapshot(self, snapshot_id: str):
        """Zwróć konkretny snapshot wraz z członkami lub None."""
        from data.models.universe_snapshot import (
            UniverseSnapshot,
            UniverseSnapshotMember,
        )
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT snapshot_id, created_at, total_records, unique_symbols
                   FROM universe_snapshots WHERE snapshot_id = ?""",
                (snapshot_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                """SELECT symbol, present, status, first_seen_at, last_seen_at,
                          chart_status, candles_received,
                          candles_valid, candles_rejected, rejection_reasons_json,
                          daily_status, daily_candles_received,
                          daily_candles_valid, daily_candles_rejected,
                          daily_rejection_reasons_json,
                          intraday_status, intraday_candles_received,
                          intraday_candles_valid, intraday_candles_rejected,
                          intraday_rejection_reasons_json,
                          baseline_status, last_reading_id
                   FROM universe_snapshot_members
                   WHERE snapshot_id = ? ORDER BY symbol""",
                (snapshot_id,),
            )
            members = [
                UniverseSnapshotMember(
                    snapshot_id=snapshot_id, symbol=r[0],
                    present=bool(r[1]), status=r[2],
                    first_seen_at=r[3], last_seen_at=r[4],
                    chart_status=r[5],
                    candles_received=r[6], candles_valid=r[7],
                    candles_rejected=r[8],
                    rejection_reasons=json.loads(r[9]) if r[9] else {},
                    daily_status=r[10],
                    daily_candles_received=r[11],
                    daily_candles_valid=r[12],
                    daily_candles_rejected=r[13],
                    daily_rejection_reasons=json.loads(r[14]) if r[14] else {},
                    intraday_status=r[15],
                    intraday_candles_received=r[16],
                    intraday_candles_valid=r[17],
                    intraday_candles_rejected=r[18],
                    intraday_rejection_reasons=json.loads(r[19]) if r[19] else {},
                    baseline_status=r[20], last_reading_id=r[21],
                )
                for r in cursor.fetchall()
            ]
            return UniverseSnapshot(
                snapshot_id=row[0], created_at=row[1],
                total_records=row[2], unique_symbols=row[3],
                members=members,
            )
        finally:
            conn.close()

    def get_latest_snapshot(self):
        """Zwróć ostatni snapshot (wg created_at) lub None."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT snapshot_id FROM universe_snapshots
                   ORDER BY sequence DESC LIMIT 1""",
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self.get_snapshot(row[0])
        finally:
            conn.close()

    def restore_universe(self) -> list:
        """Jawne odtworzenie pełnego uniwersum po restarcie."""
        return self.get_current_universe()

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
                "journal_mode": journal_mode,
                "schema_version": self.SCHEMA_VERSION,
            }
        finally:
            conn.close()