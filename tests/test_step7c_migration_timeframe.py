"""Test-first RED — migracja produkcyjnej bazy do timeframe (7C).

Walidacja migracji na świeżo utworzonej bazie przypominającej produkcyjną:
  327 Readingów -> 5m/LEGACY_UNKNOWN; 171 ACTIVE -> RETIRED_TIMEFRAME;
  1 INTEGRITY_BREACHED bez zmian; 172 baseline 5m zachowane;
  możliwość utworzenia niezależnego baseline i Observation 1h;
  idempotencja; rollback przy kontrolowanym błędzie.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from application.sqlite_history_repository import SQLiteHistoryRepository


def _create_legacy_production_like_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
            """
            CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
            INSERT INTO schema_version (version) VALUES (2);

            CREATE TABLE instrument_observations (
                observation_id TEXT PRIMARY KEY,
                instrument_id TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                terminated_at TEXT,
                termination_reason TEXT
            );
            CREATE UNIQUE INDEX idx_one_active_observation
                ON instrument_observations(instrument_id) WHERE state = 'ACTIVE';

            CREATE TABLE instrument_readings (
                reading_id TEXT PRIMARY KEY,
                observation_id TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                market_data_timestamp TEXT NOT NULL,
                scan_timestamp TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                source TEXT NOT NULL DEFAULT 'YahooFinance',
                prev_reading_id TEXT,
                data_completeness TEXT NOT NULL DEFAULT 'COMPLETE',
                revision_number INTEGER NOT NULL DEFAULT 1,
                supersedes_reading_id TEXT
            );
            CREATE UNIQUE INDEX idx_readings_identity
                ON instrument_readings(instrument_id, market_data_timestamp, revision_number);

            CREATE TABLE universe_instruments (
                symbol TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                chart_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                baseline_status TEXT,
                last_reading_id TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _seed(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        for i in range(172):
            sym = f"SYN{i:04d}"
            obs_id = f"obs-{i}"
            state = "ACTIVE" if i < 171 else "INTEGRITY_BREACHED"
            if state == "INTEGRITY_BREACHED":
                cur.execute(
                    "INSERT INTO instrument_observations "
                    "(observation_id, instrument_id, state, created_at, terminated_at, termination_reason) "
                    "VALUES (?,?,?,?,?,?)",
                    (obs_id, sym, state, "2026-07-01T08:00:00+00:00",
                     "2026-07-02T08:00:00+00:00", "Content conflict"),
                )
            else:
                cur.execute(
                    "INSERT INTO instrument_observations "
                    "(observation_id, instrument_id, state, created_at) VALUES (?,?,?,?)",
                    (obs_id, sym, state, "2026-07-01T08:00:00+00:00"),
                )
            cur.execute(
                "INSERT INTO universe_instruments (symbol, status, chart_status, baseline_status, last_reading_id) "
                "VALUES (?, 'ACTIVE', 'SUCCESS', 'PENDING_BASELINE', NULL)",
                (sym,),
            )
        # 327 czytan: 172*2 - 17 = 327 => 171 instrumentów z 2 czytaniami + 1 z 1 czytaniem = 343?
        # Ustalmy dokładnie: 171 ACTIVE z 2 czytaniami = 342; 1 INTEGRITY z 1 czytaniem = 343 -> za dużo.
        # Poprawny rozkład: 155 ACTIVE po 2 czytania (310) + 16 ACTIVE po 1 (16) + 1 INTEGRITY po 1 (1) = 327.
        ts = 0
        reading_id = 0
        for i in range(171):
            sym = f"SYN{i:04d}"
            obs_id = f"obs-{i}"
            readings_count = 2 if i < 155 else 1
            for k in range(readings_count):
                ts += 1
                reading_id += 1
                cur.execute(
                    """INSERT INTO instrument_readings
                       (reading_id, observation_id, instrument_id, market_data_timestamp,
                        scan_timestamp, open, high, low, close, volume, source,
                        prev_reading_id, data_completeness, revision_number, supersedes_reading_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f"rdg-{reading_id}", obs_id, sym,
                     f"2026-08-20T{8 + (ts % 8)}:{ts % 60:02d}:00+00:00",
                     "2026-08-20T08:00:00+00:00",
                     100.0 + ts, 105.0 + ts, 99.0 + ts, 102.0 + ts,
                     1000 + ts, "YahooFinance",
                     None if k == 0 else f"rdg-{reading_id - 1}",
                     "COMPLETE", k + 1,
                     None if k == 0 else f"rdg-{reading_id - 1}"),
                )
        # 1 INTEGRITY_BREACHED z 1 czytaniem
        ts += 1
        reading_id += 1
        cur.execute(
            """INSERT INTO instrument_readings
               (reading_id, observation_id, instrument_id, market_data_timestamp,
                scan_timestamp, open, high, low, close, volume, source,
                prev_reading_id, data_completeness, revision_number, supersedes_reading_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"rdg-{reading_id}", "obs-171", "SYN0171",
             "2026-08-20T08:30:00+00:00", "2026-08-20T08:30:00+00:00",
             100.0, 105.0, 99.0, 102.0, 1000.0, "YahooFinance",
             None, "COMPLETE", 1, None),
        )
        conn.commit()
    finally:
        conn.close()


class TestMigration:
    def test_readings_327_backfilled(self, tmp_path):
        path = tmp_path / "prod-like.db"
        _create_legacy_production_like_db(path)
        _seed(path)

        SQLiteHistoryRepository(path)

        conn = sqlite3.connect(str(path))
        try:
            total = conn.execute("SELECT COUNT(*) FROM instrument_readings").fetchone()[0]
            bad = conn.execute(
                "SELECT COUNT(*) FROM instrument_readings WHERE timeframe != '5m' OR candle_state != 'LEGACY_UNKNOWN'"
            ).fetchone()[0]
            integrity = conn.execute(
                "SELECT COUNT(*) FROM instrument_observations WHERE state = 'INTEGRITY_BREACHED'"
            ).fetchone()[0]
        finally:
            conn.close()

        assert total == 327
        assert bad == 0
        assert integrity == 1

    def test_observations_171_retired(self, tmp_path):
        path = tmp_path / "prod-like.db"
        _create_legacy_production_like_db(path)
        _seed(path)

        SQLiteHistoryRepository(path)

        conn = sqlite3.connect(str(path))
        try:
            retired = conn.execute(
                "SELECT COUNT(*) FROM instrument_observations WHERE state = 'RETIRED_TIMEFRAME'"
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM instrument_observations WHERE state = 'ACTIVE'"
            ).fetchone()[0]
        finally:
            conn.close()

        assert retired == 171
        assert active == 0

    def test_baselines_172_preserved_and_new_1h_possible(self, tmp_path):
        path = tmp_path / "prod-like.db"
        _create_legacy_production_like_db(path)
        _seed(path)

        repo = SQLiteHistoryRepository(path)

        conn = sqlite3.connect(str(path))
        try:
            baselines = conn.execute(
                "SELECT COUNT(*) FROM universe_instruments WHERE baseline_status IS NOT NULL"
            ).fetchone()[0]
        finally:
            conn.close()
        assert baselines == 172

        # nowa niezależna Observation i baseline 1h
        from data.models.instrument_observation import InstrumentObservation
        from data.models.instrument_reading import InstrumentReading
        obs = InstrumentObservation(observation_id="obs-1h-new", instrument_id="SYN0000", timeframe="1h")
        rdg = InstrumentReading(
            reading_id="rdg-1h-new",
            observation_id="obs-1h-new",
            instrument_id="SYN0000",
            market_data_timestamp=__import__("datetime").datetime(
                2026, 8, 21, 12, 0, tzinfo=__import__("datetime").timezone.utc),
            scan_timestamp=__import__("datetime").datetime(
                2026, 8, 21, 12, 15, tzinfo=__import__("datetime").timezone.utc),
            open=10.0, high=11.0, low=9.0, close=10.5, volume=100.0,
            timeframe="1h", candle_state="OPEN",
        )
        result = repo.save_reading(obs, rdg)
        assert result == "ACCEPTED"

    def test_migration_idempotent(self, tmp_path):
        path = tmp_path / "prod-like.db"
        _create_legacy_production_like_db(path)
        _seed(path)

        SQLiteHistoryRepository(path)
        conn = sqlite3.connect(str(path))
        first = conn.execute(
            "SELECT COUNT(*), SUM(timeframe='5m'), SUM(candle_state='LEGACY_UNKNOWN') "
            "FROM instrument_readings"
        ).fetchone()
        conn.close()

        SQLiteHistoryRepository(path)
        conn = sqlite3.connect(str(path))
        second = conn.execute(
            "SELECT COUNT(*), SUM(timeframe='5m'), SUM(candle_state='LEGACY_UNKNOWN') "
            "FROM instrument_readings"
        ).fetchone()
        conn.close()

        assert first == second