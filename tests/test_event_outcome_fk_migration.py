"""
Testy migracji FK EventOutcome -> MarketEvent (Phase B).

Scenariusze na prawdziwym tymczasowym SQLite:
  * stary schemat: market_events.event_id nie jest UNIQUE;
  * stary schemat: FK market_event_id -> market_events(event_id) nie jest
    egzekwowany (foreign key mismatch);
  * nowa pusta baza po naprawie ma UNIQUE na market_events.event_id;
  * migracja starej bazy tworzy UNIQUE;
  * drugie otwarcie jest idempotentne;
  * istniejący event_id przyjmuje prawidłowy EventOutcome;
  * nieistniejący event_id jest odrzucany przez SQLite;
  * duplikaty event_id zatrzymują migrację bez utraty danych;
  * PRAGMA foreign_key_check po migracji jest czysty;
  * PRAGMA integrity_check = ok.
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models.event_outcome import EventOutcome


# ----------------------------------------------------------------------
# Stary schemat sprzed naprawy FK (miniatura produkcyjnej bazy).
# market_events.event_id NIE ma UNIQUE, event_outcomes ma FK do event_id.
# ----------------------------------------------------------------------

_OLD_SCHEMA = """
CREATE TABLE cycles (
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

CREATE TABLE market_events (
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

CREATE INDEX idx_market_events_event_id ON market_events(event_id);

CREATE TABLE event_outcomes (
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

CREATE TABLE instrument_observations (
    observation_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    terminated_at TEXT,
    termination_reason TEXT
);

CREATE TABLE instrument_readings (
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

CREATE UNIQUE INDEX idx_readings_identity
    ON instrument_readings(instrument_id, market_data_timestamp, revision_number);

CREATE UNIQUE INDEX idx_one_active_observation
    ON instrument_observations(instrument_id)
    WHERE state = 'ACTIVE';

CREATE TABLE universe_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    created_at TEXT
);

CREATE TABLE universe_instruments (
    symbol TEXT PRIMARY KEY
);

CREATE TABLE universe_snapshot_members (
    snapshot_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    present INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (snapshot_id, symbol),
    FOREIGN KEY (snapshot_id) REFERENCES universe_snapshots(snapshot_id)
);
"""


def _create_old_schema_db(db_path: str) -> None:
    """Tworzy starą bazę ze schematem sprzed naprawy FK."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_OLD_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _insert_market_event(
    db_path: str,
    *,
    event_id: str,
    ticker: str = "AAA",
    signal_timing: str = "EOD",
) -> None:
    """Wstawia wiersz market_events bezpośrednio (stary schemat)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO cycles (cycle_id, created_at) "
            "VALUES ('cycle-1', '2026-08-19T12:00:00+00:00')"
        )
        conn.execute(
            """
            INSERT INTO market_events (
                cycle_id, event_id, ticker, market, instrument_type,
                event_family, event_category, event_type, event_subcategory,
                signal_timing, priority_raw, priority_final, confidence_level,
                detection_source, event_owner, event_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cycle-1",
                event_id,
                ticker,
                "GPW",
                "STOCK_GPW",
                "TECHNICAL",
                "MOMENTUM",
                "RSI_OVERSOLD",
                "",
                signal_timing,
                "MEDIUM",
                "MEDIUM",
                0.5,
                "technical",
                "TechnicalEngine",
                '{"event_id": "' + event_id + '", "event_type": "RSI_OVERSOLD"}',
                "2026-08-19T12:00:00+00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _has_unique_index_on_event_id(db_path: str) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA index_list(market_events)").fetchall()
        for name, unique in [(r[1], r[2]) for r in rows]:
            if unique:
                info = conn.execute(f"PRAGMA index_info({name})").fetchall()
                cols = [r[2] for r in info]
                if "event_id" in cols:
                    return True
        return False
    finally:
        conn.close()


def _make_event_outcome(market_event_id: str, event_outcome_id: str) -> EventOutcome:
    ts = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
    return EventOutcome(
        event_outcome_id=event_outcome_id,
        market_event_id=market_event_id,
        ticker="AAA",
        market="GPW",
        detection_timestamp=ts,
        created_at=ts,
        event_family="TECHNICAL",
        event_type="RSI_OVERSOLD",
    )


class TestEventOutcomeFkMigration(unittest.TestCase):
    def setUp(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = temp.name
        temp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def _new_repo(self, db_path: str) -> SQLiteHistoryRepository:
        return SQLiteHistoryRepository(db_path)

    # ------------------------------------------------------------------
    # Dowody defektu w starym schemacie (przed implementacją)
    # ------------------------------------------------------------------

    def test_stary_parent_event_id_nie_jest_unique(self):
        """Stary schemat: market_events.event_id nie jest UNIQUE."""
        _create_old_schema_db(self.db_path)
        self.assertFalse(_has_unique_index_on_event_id(self.db_path))

    def test_stary_schemat_powoduje_fk_mismatch(self):
        """Stary schemat: FK event_outcomes.market_event_id -> market_events.event_id
        nie jest egzekwowany — foreign_key_check zgłasza błąd."""
        _create_old_schema_db(self.db_path)
        _insert_market_event(self.db_path, event_id="evt-1")
        ts = "2026-08-19T12:00:00+00:00"
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO event_outcomes (
                    event_outcome_id, market_event_id, state, ticker, market,
                    detection_timestamp, event_family, event_type, created_at
                ) VALUES (?, ?, 'PENDING', 'AAA', 'GPW', ?, 'TECHNICAL',
                          'RSI_OVERSOLD', ?)
                """,
                ("eo-mismatch", "missing-event", ts, ts),
            )
            conn.commit()
            try:
                violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            except sqlite3.OperationalError as exc:
                # Stary schemat: FK market_event_id -> market_events(event_id)
                # nie jest egzekwowany, bo event_id nie jest UNIQUE — SQLite
                # zgłasza "foreign key mismatch" jako błąd operacyjny.
                violations = [("OPERATIONAL_ERROR", str(exc))]
        finally:
            conn.close()
        self.assertTrue(
            violations,
            "Stary schemat powinien mieć niespójność FK dla nieistniejącego "
            "market_event_id (foreign key mismatch).",
        )

    def test_eventoutcome_nie_ma_egzekwowanego_fk(self):
        """EventOutcome z nieistniejącym market_event_id NIE jest odrzucany
        przez repozytorium — FK nie działa (wymagany IntegrityError)."""
        repo = self._new_repo(self.db_path)
        repo.save_market_event(
            "cycle-1",
            {
                "event_id": "evt-1",
                "ticker": "AAA",
                "market": "GPW",
                "instrument_type": "STOCK_GPW",
                "event_family": "TECHNICAL",
                "event_category": "MOMENTUM",
                "event_type": "RSI_OVERSOLD",
                "event_subcategory": "",
                "signal_timing": "EOD",
                "priority_raw": "MEDIUM",
                "priority_final": "MEDIUM",
                "confidence_level": 0.5,
                "detection_source": "technical",
                "event_owner": "TechnicalEngine",
            },
        )
        outcome = _make_event_outcome("missing-event", "eo-1")
        with self.assertRaises(sqlite3.IntegrityError):
            repo.save_event_outcome(outcome)

    # ------------------------------------------------------------------
    # Testy naprawy (RED przed implementacją, GREEN po)
    # ------------------------------------------------------------------

    def test_nowa_baza_ma_unique_event_id(self):
        """Nowa pusta baza ma UNIQUE na market_events.event_id."""
        repo = self._new_repo(self.db_path)
        self.assertIsNotNone(repo)
        self.assertTrue(_has_unique_index_on_event_id(self.db_path))

    def test_migracja_starej_bazy_tworzy_unique(self):
        """Otwarcie starej bazy przez repozytorium tworzy UNIQUE."""
        _create_old_schema_db(self.db_path)
        _insert_market_event(self.db_path, event_id="evt-1")
        repo = self._new_repo(self.db_path)
        self.assertIsNotNone(repo)
        self.assertTrue(_has_unique_index_on_event_id(self.db_path))

    def test_drugie_otwarcie_jest_idempotentne(self):
        """Ponowne otwarcie po migracji niczego nie zmienia i nie psuje."""
        _create_old_schema_db(self.db_path)
        _insert_market_event(self.db_path, event_id="evt-1")
        self._new_repo(self.db_path)
        self._new_repo(self.db_path)
        self.assertTrue(_has_unique_index_on_event_id(self.db_path))

    def test_istniejacy_event_id_przyjmuje_event_outcome(self):
        """Istniejący event_id przyjmuje prawidłowy EventOutcome."""
        repo = self._new_repo(self.db_path)
        repo.save_market_event(
            "cycle-1",
            {
                "event_id": "evt-1",
                "ticker": "AAA",
                "market": "GPW",
                "instrument_type": "STOCK_GPW",
                "event_family": "TECHNICAL",
                "event_category": "MOMENTUM",
                "event_type": "RSI_OVERSOLD",
                "event_subcategory": "",
                "signal_timing": "EOD",
                "priority_raw": "MEDIUM",
                "priority_final": "MEDIUM",
                "confidence_level": 0.5,
                "detection_source": "technical",
                "event_owner": "TechnicalEngine",
            },
        )
        outcome = _make_event_outcome("evt-1", "eo-1")
        repo.save_event_outcome(outcome)
        loaded = repo.get_event_outcome_by_id("eo-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.market_event_id, "evt-1")

    def test_nieistniejacy_event_id_odrzucany_przez_sqlite(self):
        """Nieistniejący event_id jest odrzucany przez SQLite (IntegrityError)."""
        _create_old_schema_db(self.db_path)
        repo = self._new_repo(self.db_path)
        self.assertIsNotNone(repo)
        outcome = _make_event_outcome("missing-event", "eo-1")
        with self.assertRaises(sqlite3.IntegrityError):
            repo.save_event_outcome(outcome)

    def test_duplikaty_event_id_zatrzymuja_migracje_bez_utraty_danych(self):
        """Duplikaty event_id zatrzymują migrację jawnym błędem; dane zostają."""
        _create_old_schema_db(self.db_path)
        _insert_market_event(self.db_path, event_id="dup-1", ticker="AAA")
        _insert_market_event(self.db_path, event_id="dup-1", ticker="BBB")
        with self.assertRaises(RuntimeError):
            self._new_repo(self.db_path)
        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM market_events WHERE event_id = 'dup-1'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 2)

    def test_fk_check_czysty_po_migracji(self):
        """PRAGMA foreign_key_check po migracji jest czysty."""
        _create_old_schema_db(self.db_path)
        _insert_market_event(self.db_path, event_id="evt-1")
        repo = self._new_repo(self.db_path)
        outcome = _make_event_outcome("evt-1", "eo-1")
        repo.save_event_outcome(outcome)
        conn = sqlite3.connect(self.db_path)
        try:
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        finally:
            conn.close()
        self.assertEqual(violations, [])

    def test_integrity_check_ok(self):
        """PRAGMA integrity_check = ok."""
        _create_old_schema_db(self.db_path)
        _insert_market_event(self.db_path, event_id="evt-1")
        self._new_repo(self.db_path)
        conn = sqlite3.connect(self.db_path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()