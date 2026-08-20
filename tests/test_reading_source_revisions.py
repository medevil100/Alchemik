"""
Testy rewizji źródła dla InstrumentReading (Phase A).

Scenariusze na prawdziwym tymczasowym SQLite:
  * pierwszy zapis → ACCEPTED / revision 1, supersedes NULL;
  * identyczny timestamp i treść → DUPLICATE_NO_OP;
  * poprawna zmiana tego samego timestampu, instrumentu, Observation i
    źródła → SOURCE_REVISION_ACCEPTED / revision 2;
  * obie wersje pozostają zapisane;
  * Observation pozostaje ACTIVE (baseline nadal jeden);
  * restart wybiera revision 2 jako latest;
  * późniejszy Reading kontynuuje łańcuch od revision 2;
  * obca tożsamość lub uszkodzone supersedes → CONFLICT.
"""

import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timezone

from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models.instrument_observation import InstrumentObservation
from data.models.instrument_reading import InstrumentReading


def _make_observation(instrument_id: str, observation_id: str) -> InstrumentObservation:
    return InstrumentObservation(
        observation_id=observation_id,
        instrument_id=instrument_id,
    )


def _make_reading(
    *,
    instrument_id: str,
    observation_id: str,
    market_ts: datetime,
    close: float,
    reading_id: str | None = None,
    source: str = "YahooFinance",
    supersedes_reading_id: str | None = None,
) -> InstrumentReading:
    return InstrumentReading(
        reading_id=reading_id or str(uuid.uuid4()),
        observation_id=observation_id,
        instrument_id=instrument_id,
        market_data_timestamp=market_ts,
        scan_timestamp=datetime.now(timezone.utc),
        open=100.0,
        high=110.0,
        low=90.0,
        close=close,
        volume=1000,
        source=source,
        supersedes_reading_id=supersedes_reading_id,
    )


class TestReadingSourceRevisions(unittest.TestCase):
    def setUp(self):
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db_file.name
        self.temp_db_file.close()
        self.repo = SQLiteHistoryRepository(self.db_path)

        self.instrument = "AAA"
        self.observation_id = "obs-aaa-1"
        self.ts = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_row(self, reading_id: str):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(
                """SELECT reading_id, observation_id, instrument_id,
                          market_data_timestamp, revision_number,
                          supersedes_reading_id
                   FROM instrument_readings
                   WHERE reading_id = ?""",
                (reading_id,),
            ).fetchone()
        finally:
            conn.close()

    def _read_prev_reading_id(self, reading_id: str):
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT prev_reading_id FROM instrument_readings WHERE reading_id = ?",
                (reading_id,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def _count_versions(self, instrument_id: str, market_ts_iso: str) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(
                """SELECT COUNT(*) FROM instrument_readings
                   WHERE instrument_id = ? AND market_data_timestamp = ?""",
                (instrument_id, market_ts_iso),
            ).fetchone()[0]
        finally:
            conn.close()

    def _count_observations_for_instrument(self, instrument_id: str) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM instrument_observations WHERE instrument_id = ?",
                (instrument_id,),
            ).fetchone()[0]
        finally:
            conn.close()

    def _observation_state(self, observation_id: str) -> str:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT state FROM instrument_observations WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Scenariusze
    # ------------------------------------------------------------------

    def test_pierwszy_zapis_akceptowany_revision_1(self):
        """Pierwszy zapis → ACCEPTED; wiersz ma revision 1 i supersedes NULL."""
        obs = _make_observation(self.instrument, self.observation_id)
        reading = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )

        result = self.repo.save_reading(obs, reading)

        self.assertEqual(result, "ACCEPTED")
        row = self._read_row(reading.reading_id)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], self.instrument)
        self.assertEqual(row[3], self.ts.isoformat())
        self.assertEqual(row[4], 1)
        self.assertIsNone(row[5])

    def test_identyczny_timestamp_i_tresc_duplicate_no_op(self):
        """Identyczny timestamp i treść → DUPLICATE_NO_OP, bez nowej wersji."""
        obs = _make_observation(self.instrument, self.observation_id)
        reading = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, reading)

        duplicate = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        result = self.repo.save_reading(obs, duplicate)

        self.assertEqual(result, "DUPLICATE_NO_OP")
        self.assertEqual(
            self._count_versions(self.instrument, self.ts.isoformat()), 1
        )

    def test_poprawna_zmiana_source_revision_akceptowana_revision_2(self):
        """Zmiana treści tego samego timestampu/instrumentu/Observation/źródła
        → SOURCE_REVISION_ACCEPTED / revision 2 z supersedes rev 1."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        r2 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=150.0,
            supersedes_reading_id=r1.reading_id,
        )
        result = self.repo.save_reading(obs, r2)

        self.assertEqual(result, "SOURCE_REVISION_ACCEPTED")
        row = self._read_row(r2.reading_id)
        self.assertEqual(row[4], 2)
        self.assertEqual(row[5], r1.reading_id)
        self.assertEqual(self._read_prev_reading_id(r2.reading_id), r1.reading_id)

    def test_obie_wersje_pozostaja_zapisane(self):
        """Po rewizji obie wersje pozostają w bazie."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        r2 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=150.0,
        )
        self.repo.save_reading(obs, r2)

        self.assertEqual(
            self._count_versions(self.instrument, self.ts.isoformat()), 2
        )

    def test_observation_pozostaje_active_baseline_jeden(self):
        """Rewizja nie kończy Observation i nie tworzy nowej (baseline jeden)."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        r2 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=150.0,
        )
        self.repo.save_reading(obs, r2)

        loaded = self.repo.load_observation(self.instrument)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.state, "ACTIVE")
        self.assertEqual(loaded.observation_id, self.observation_id)
        self.assertEqual(self._count_observations_for_instrument(self.instrument), 1)

    def test_restart_wybiera_revision_2_jako_latest(self):
        """Po restarcie repozytorium latest dla instrumentu to revision 2."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        r2 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=150.0,
        )
        self.repo.save_reading(obs, r2)

        new_repo = SQLiteHistoryRepository(self.db_path)
        restored = new_repo.restore_active_observations()
        self.assertEqual(len(restored), 1)
        restored_obs, latest = restored[0]
        self.assertEqual(restored_obs.instrument_id, self.instrument)
        self.assertEqual(latest.instrument_id, self.instrument)
        self.assertEqual(latest.reading_id, r2.reading_id)
        self.assertEqual(latest.revision_number, 2)
        self.assertEqual(latest.supersedes_reading_id, r1.reading_id)

    def test_pozniejszy_reading_kontynuuje_od_revision_2(self):
        """Nowy timestamp po rewizji → ACCEPTED rev 1, a jego prev_reading_id
        wskazuje rewizję 2 (kontynuacja łańcucha); kolejna zmiana nowego
        timestampu dostaje revision 2."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        r2 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=150.0,
        )
        self.repo.save_reading(obs, r2)

        ts2 = datetime(2026, 8, 19, 13, 0, 0, tzinfo=timezone.utc)
        r3 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=ts2,
            close=200.0,
        )
        result3 = self.repo.save_reading(obs, r3)

        self.assertEqual(result3, "ACCEPTED")
        row3 = self._read_row(r3.reading_id)
        self.assertEqual(row3[4], 1)
        self.assertIsNone(row3[5])
        self.assertEqual(self._read_prev_reading_id(r3.reading_id), r2.reading_id)

        r4 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=ts2,
            close=250.0,
        )
        result4 = self.repo.save_reading(obs, r4)

        self.assertEqual(result4, "SOURCE_REVISION_ACCEPTED")
        row4 = self._read_row(r4.reading_id)
        self.assertEqual(row4[4], 2)
        self.assertEqual(row4[5], r3.reading_id)
        self.assertEqual(
            self._count_versions(self.instrument, ts2.isoformat()), 2
        )

    def test_obca_tozsamosc_instrumentu_zwraca_conflict(self):
        """Reading o obcym instrument_id niż Observation → CONFLICT."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        foreign = _make_reading(
            instrument_id="BBBB",
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        result = self.repo.save_reading(obs, foreign)

        self.assertEqual(result, "CONFLICT")

    def test_uszkodzone_supersedes_zwraca_conflict(self):
        """supersedes_reading_id wskazujący nieistniejącą wersję → CONFLICT."""
        obs = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs, r1)

        corrupted = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
            supersedes_reading_id="missing-reading",
        )
        result = self.repo.save_reading(obs, corrupted)

        self.assertEqual(result, "CONFLICT")

    def test_prawdziwy_conflict_zachowuje_dotychczasowe_dzialanie(self):
        """Obca Observation z inną treścią → CONFLICT i Observation kończy się
        INTEGRITY_BREACHED (dotychczasowe działanie)."""
        obs1 = _make_observation(self.instrument, self.observation_id)
        r1 = _make_reading(
            instrument_id=self.instrument,
            observation_id=self.observation_id,
            market_ts=self.ts,
            close=100.0,
        )
        self.repo.save_reading(obs1, r1)

        foreign_obs_id = "obs-aaa-foreign"
        obs2 = _make_observation(self.instrument, foreign_obs_id)
        r2 = _make_reading(
            instrument_id=self.instrument,
            observation_id=foreign_obs_id,
            market_ts=self.ts,
            close=300.0,
        )
        result = self.repo.save_reading(obs2, r2)

        self.assertEqual(result, "CONFLICT")
        self.assertIsNone(self.repo.load_observation(self.instrument))
        self.assertEqual(
            self._observation_state(self.observation_id), "INTEGRITY_BREACHED"
        )