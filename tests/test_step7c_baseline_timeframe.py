"""Test-first RED — baseline per timeframe używany przez RuntimeService (7C/8)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from application.history_repository import HistoryRepository
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.runtime import RuntimeService
from data.models.instrument_observation import InstrumentObservation
from data.models.instrument_reading import InstrumentReading
from data.models.market_data import MarketData


def _obs(instrument_id, timeframe):
    return InstrumentObservation(
        observation_id=f"obs_{instrument_id}_{timeframe}",
        instrument_id=instrument_id,
        timeframe=timeframe,
    )


def _reading(instrument_id, timeframe, ts, candle_state, reading_id, close=100.0):
    return InstrumentReading(
        reading_id=reading_id,
        observation_id=f"obs_{instrument_id}_{timeframe}",
        instrument_id=instrument_id,
        market_data_timestamp=ts,
        scan_timestamp=ts,
        open=100.0,
        high=110.0,
        low=90.0,
        close=close,
        volume=1000.0,
        timeframe=timeframe,
        candle_state=candle_state,
    )


class TestBaselineApiParity:
    def _seed_reading(self, repo, instrument_id, timeframe, reading_id, ts=None):
        ts = ts or datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        obs = _obs(instrument_id, timeframe)
        rdg = _reading(instrument_id, timeframe, ts, "CLOSED", reading_id)
        assert repo.save_reading(obs, rdg) == "ACCEPTED"
        return rdg

    def test_first_baseline_persist_and_read(self):
        repos = [HistoryRepository(), SQLiteHistoryRepository("/tmp/dummy")] if False else None

    def test_sqlite_first_baseline_persistent(self, tmp_path):
        repo = SQLiteHistoryRepository(tmp_path / "b.db")
        rdg = self._seed_reading(repo, "PAR-X", "1h", "r-anchor")

        assert repo.save_baseline("PAR-X", "1h", rdg.reading_id) == "BASELINE_ACCEPTED"
        assert repo.get_baseline("PAR-X", "1h") == rdg.reading_id
        # Restart SQLite — ten sam baseline.
        repo2 = SQLiteHistoryRepository(tmp_path / "b.db")
        assert repo2.get_baseline("PAR-X", "1h") == rdg.reading_id

    def test_in_memory_first_baseline(self):
        repo = HistoryRepository()
        rdg = self._seed_reading(repo, "PAR-X", "1h", "r-anchor")

        assert repo.save_baseline("PAR-X", "1h", rdg.reading_id) == "BASELINE_ACCEPTED"
        assert repo.get_baseline("PAR-X", "1h") == rdg.reading_id

    def test_same_baseline_idempotent(self):
        repo = HistoryRepository()
        rdg = self._seed_reading(repo, "PAR-X", "1h", "r-anchor")
        assert repo.save_baseline("PAR-X", "1h", rdg.reading_id) == "BASELINE_ACCEPTED"
        assert repo.save_baseline("PAR-X", "1h", rdg.reading_id) == "BASELINE_UNCHANGED"

    def test_replacing_baseline_rejected(self):
        repo = SQLiteHistoryRepository
        in_mem = HistoryRepository()
        anchor = self._seed_reading(in_mem, "PAR-X", "1h", "r-anchor")
        other = self._seed_reading(
            in_mem, "PAR-X", "1h", "r-other",
            ts=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
        )
        assert in_mem.save_baseline("PAR-X", "1h", anchor.reading_id) == "BASELINE_ACCEPTED"
        assert in_mem.save_baseline("PAR-X", "1h", other.reading_id) == "BASELINE_CONFLICT"

    def test_timeframes_not_mixed(self):
        repo = HistoryRepository()
        rdg_5m = self._seed_reading(repo, "PAR-X", "5m", "r-5m")
        rdg_1h = self._seed_reading(
            repo, "PAR-X", "1h", "r-1h",
            ts=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
        )
        repo.save_baseline("PAR-X", "5m", rdg_5m.reading_id)
        repo.save_baseline("PAR-X", "1h", rdg_1h.reading_id)
        assert repo.get_baseline("PAR-X", "5m") == rdg_5m.reading_id
        assert repo.get_baseline("PAR-X", "1h") == rdg_1h.reading_id


def _market(ts, timeframe, candle_state, close):
    return MarketData(
        timestamp=ts,
        open=100.0,
        high=110.0,
        low=90.0,
        close=close,
        volume=1000.0,
        timeframe=timeframe,
        candle_state=candle_state,
    )


class TestRuntimeFirst1hCycleBaseline:
    def _make_runtime(self, tmp_path):
        repo = SQLiteHistoryRepository(tmp_path / "rt.db")
        runtime = RuntimeService(
            hunter_engine=None,
            master_engine=None,
            history_repository=repo,
        )
        return repo, runtime

    def test_first_1h_cycle_persists_closed_anchor_and_open(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)
        anchor_ts = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        open_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        data = [
            _market(anchor_ts, "1h", "CLOSED", 100.0),
            _market(open_ts, "1h", "OPEN", 101.0),
        ]

        result, reading, observation = runtime._persist_observation_and_reading_full("AAA.WA", data)

        # Ostatni (bieżący) Reading to OPEN.
        assert result == "ACCEPTED"
        assert reading.candle_state == "OPEN"
        assert reading.timeframe == "1h"

        conn = sqlite3.connect(str(repo.db_path))
        try:
            rows = conn.execute(
                """SELECT reading_id, candle_state, revision_number, prev_reading_id, timeframe
                   FROM instrument_readings WHERE instrument_id='AAA.WA'
                   ORDER BY market_data_timestamp"""
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) == 2
        anchor = rows[0]
        open_row = rows[1]
        assert anchor[1] == "CLOSED"
        assert anchor[2] == 1
        assert anchor[3] is None
        assert anchor[4] == "1h"
        assert open_row[1] == "OPEN"
        assert open_row[2] == 1
        assert open_row[3] == anchor[0]
        assert open_row[4] == "1h"

        # Baseline 1h wskazuje CLOSED kotwicę.
        assert repo.get_baseline("AAA.WA", "1h") == anchor[0]

    def test_next_open_update_keeps_baseline(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)
        anchor_ts = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        open_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        data = [
            _market(anchor_ts, "1h", "CLOSED", 100.0),
            _market(open_ts, "1h", "OPEN", 101.0),
        ]
        runtime._persist_observation_and_reading_full("AAA.WA", data)
        baseline_before = repo.get_baseline("AAA.WA", "1h")

        # Kolejny stan tej samej OPEN świecy.
        updated = [
            _market(anchor_ts, "1h", "CLOSED", 100.0),
            _market(open_ts, "1h", "OPEN", 102.0),
        ]
        result, reading, _obs = runtime._persist_observation_and_reading_full("AAA.WA", updated)

        assert result == "CANDLE_PROGRESS_ACCEPTED"
        assert repo.get_baseline("AAA.WA", "1h") == baseline_before

    def test_transition_to_next_1h_candle(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)

        # Cykl 1: 11:00 CLOSED + 12:00 OPEN.
        c11 = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        c12 = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        runtime._persist_observation_and_reading_full("AAA.WA", [
            _market(c11, "1h", "CLOSED", 100.0),
            _market(c12, "1h", "OPEN", 101.0),
        ])

        baseline_after_cycle1 = repo.get_baseline("AAA.WA", "1h")

        conn = sqlite3.connect(str(repo.db_path))
        try:
            rows1 = conn.execute(
                """SELECT reading_id, candle_state, revision_number, prev_reading_id,
                          market_data_timestamp
                   FROM instrument_readings WHERE instrument_id='AAA.WA'
                   ORDER BY market_data_timestamp"""
            ).fetchall()
        finally:
            conn.close()

        assert len(rows1) == 2
        anchor_11 = rows1[0]
        open_12 = rows1[1]
        assert anchor_11[3] is None
        assert open_12[3] == anchor_11[0]
        assert baseline_after_cycle1 == anchor_11[0]

        # Cykl 2: starsza historia + 12:00 CLOSED + 13:00 OPEN.
        older = [
            datetime(2026, 8, 20, h, 0, tzinfo=timezone.utc) for h in (9, 10, 11, 12)
        ]
        c13 = datetime(2026, 8, 21, 13, 0, tzinfo=timezone.utc)
        payload2 = [_market(t, "1h", "CLOSED", 100.0) for t in older]
        payload2.append(_market(c12, "1h", "CLOSED", 102.0))
        payload2.append(_market(c13, "1h", "OPEN", 103.0))
        runtime._persist_observation_and_reading_full("AAA.WA", payload2)

        conn = sqlite3.connect(str(repo.db_path))
        try:
            rows2 = conn.execute(
                """SELECT reading_id, candle_state, revision_number, prev_reading_id,
                          supersedes_reading_id, market_data_timestamp
                   FROM instrument_readings WHERE instrument_id='AAA.WA'
                   ORDER BY market_data_timestamp, revision_number"""
            ).fetchall()
            obs_rows = conn.execute(
                """SELECT observation_id, state, timeframe, COUNT(*)
                   FROM instrument_observations
                   WHERE instrument_id='AAA.WA' GROUP BY observation_id, state, timeframe"""
            ).fetchall()
        finally:
            conn.close()

        # Starsza historia nie zostaje zapisana. Zachowane pozostają obie wersje
        # świecy 12:00 (OPEN rev1 i CLOSED rev2), więc łącznie 4 Readingi:
        # 11:00 CLOSED rev1, 12:00 OPEN rev1, 12:00 CLOSED rev2, 13:00 OPEN rev1.
        assert len(rows2) == 4
        open_12_kept = next(
            r for r in rows2
            if r[5] == c12.isoformat() and r[1] == "OPEN"
        )
        assert open_12_kept[2] == 1

        anchor_11_final = next(r for r in rows2 if r[5] == c11.isoformat())
        closed_12_final = next(
            r for r in rows2
            if r[5] == c12.isoformat() and r[1] == "CLOSED"
        )
        open_13 = next(r for r in rows2 if r[5] == c13.isoformat())

        # 12:00 OPEN został zamknięty do CLOSED tej samej świecy (rewizja 2).
        assert closed_12_final[1] == "CLOSED"
        assert closed_12_final[2] == 2
        assert closed_12_final[4] == open_12[0]

        # 13:00 OPEN to nowa świeca revision 1; prev = końcowa wersja 12:00 CLOSED.
        assert open_13[1] == "OPEN"
        assert open_13[2] == 1
        assert open_13[3] == closed_12_final[0]
        # prev nie wskazuje baseline 11:00.
        assert open_13[3] != anchor_11_final[0]

        # Baseline 1h niezmienny (11:00), Observation jedna i ACTIVE.
        assert repo.get_baseline("AAA.WA", "1h") == baseline_after_cycle1
        assert len(obs_rows) == 1
        assert obs_rows[0][1] == "ACTIVE"
        assert obs_rows[0][2] == "1h"

    def test_realistic_5d_1h_payload_saves_only_closed_open_pair(self, tmp_path):
        repo, runtime = self._make_runtime(tmp_path)
        # Pełny payload 5d/1h: cztery starsze świece CLOSED z poprzedniego dnia,
        # jedna CLOSED bezpośrednio poprzedzająca i jedna bieżąca OPEN.
        older_closed = [
            datetime(2026, 8, 20, h, 0, tzinfo=timezone.utc) for h in (9, 10, 11, 12)
        ]
        prev_closed = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        cur_open = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

        data = [_market(t, "1h", "CLOSED", 100.0) for t in older_closed]
        data.append(_market(prev_closed, "1h", "CLOSED", 100.0))
        data.append(_market(cur_open, "1h", "OPEN", 101.0))

        result, reading, _obs = runtime._persist_observation_and_reading_full("AAA.WA", data)

        assert result == "ACCEPTED"
        assert reading.candle_state == "OPEN"

        conn = sqlite3.connect(str(repo.db_path))
        try:
            rows = conn.execute(
                """SELECT reading_id, candle_state, market_data_timestamp, prev_reading_id
                   FROM instrument_readings WHERE instrument_id='AAA.WA'
                   ORDER BY market_data_timestamp"""
            ).fetchall()
        finally:
            conn.close()

        # Dokładnie dwa nowe Readingi 1h: bezpośrednio poprzednia CLOSED i bieżąca OPEN.
        assert len(rows) == 2
        anchor = rows[0]
        open_row = rows[1]
        assert anchor[1] == "CLOSED"
        assert anchor[2] == prev_closed.isoformat()
        assert open_row[1] == "OPEN"
        assert open_row[2] == cur_open.isoformat()
        assert open_row[3] == anchor[0]

        # Baseline 1h = bezpośrednio poprzednia CLOSED (nie najstarsza świeca).
        assert repo.get_baseline("AAA.WA", "1h") == anchor[0]
        # Starsza historia nie została zapisana i nie jest baseline.
        for old_ts in older_closed:
            assert old_ts.isoformat() not in {r[2] for r in rows}
