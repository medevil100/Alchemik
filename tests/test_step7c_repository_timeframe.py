"""Test-first RED — kontrakt repository per timeframe i candle_state (7C).

Zakres:
  * unikalność ACTIVE Observation per (instrument_id, timeframe);
  * osobny baseline 5m i 1h;
  * brak połączenia prev/latest/restore między 5m i 1h;
  * pierwsza kotwica CLOSED 1h i pierwszy OPEN Reading;
  * OPEN rev1 -> OPEN rev2 -> OPEN rev3 -> CLOSED rev4;
  * następny timestamp 1h jako revision 1;
  * SOURCE_REVISION_ACCEPTED dopiero po CLOSED;
  * CANDLE_PROGRESS_ACCEPTED dla postępu OPEN oraz przejścia OPEN -> CLOSED.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from application.history_repository import HistoryRepository
from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models.instrument_observation import InstrumentObservation
from data.models.instrument_reading import InstrumentReading


def _make_observation(instrument_id="SYN-1H", observation_id="obs-1h", timeframe="1h"):
    return InstrumentObservation(
        observation_id=observation_id,
        instrument_id=instrument_id,
        timeframe=timeframe,
    )


def _make_reading(
    instrument_id="SYN-1H",
    observation_id="obs-1h",
    market_ts=None,
    timeframe="1h",
    candle_state="OPEN",
    reading_id="rdg-1",
    close=102.0,
    scan_hour=12,
    scan_minute=15,
):
    if market_ts is None:
        market_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    return InstrumentReading(
        reading_id=reading_id,
        observation_id=observation_id,
        instrument_id=instrument_id,
        market_data_timestamp=market_ts,
        scan_timestamp=datetime(2026, 8, 21, scan_hour, scan_minute, tzinfo=timezone.utc),
        open=100.0,
        high=105.0,
        low=99.0,
        close=close,
        volume=1000.0,
        timeframe=timeframe,
        candle_state=candle_state,
    )


@pytest.fixture()
def repo(tmp_path: Path):
    return SQLiteHistoryRepository(tmp_path / "test_7c.db")


class TestActiveObservationUniquePerTimeframe:
    def test_second_active_same_instrument_same_timeframe_rejected(self, repo):
        obs1 = _make_observation(instrument_id="SYN-1H", observation_id="obs-a", timeframe="1h")
        rdg1 = _make_reading(instrument_id="SYN-1H", observation_id="obs-a", timeframe="1h",
                             reading_id="r-a", market_ts=datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc))
        repo.save_reading(obs1, rdg1)

        obs2 = _make_observation(instrument_id="SYN-1H", observation_id="obs-b", timeframe="1h")
        rdg2 = _make_reading(instrument_id="SYN-1H", observation_id="obs-b", timeframe="1h",
                             reading_id="r-b", market_ts=datetime(2026, 8, 21, 13, 0, tzinfo=timezone.utc))
        with pytest.raises(ValueError):
            repo.save_reading(obs2, rdg2)

    def test_second_active_same_instrument_different_timeframe_allowed(self, repo):
        obs5 = _make_observation(instrument_id="SYN-X", observation_id="obs-5m", timeframe="5m")
        rdg5 = _make_reading(instrument_id="SYN-X", observation_id="obs-5m", timeframe="5m",
                             reading_id="r-5m", market_ts=datetime(2026, 8, 21, 11, 55, tzinfo=timezone.utc))
        repo.save_reading(obs5, rdg5)

        obs1h = _make_observation(instrument_id="SYN-X", observation_id="obs-1h", timeframe="1h")
        rdg1h = _make_reading(instrument_id="SYN-X", observation_id="obs-1h", timeframe="1h",
                              reading_id="r-1h", market_ts=datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc))
        result = repo.save_reading(obs1h, rdg1h)
        assert result == "ACCEPTED"


class TestSeparatedBaselinesAndHistory:
    def test_baseline_5m_cannot_be_prev_for_1h(self, repo):
        obs5 = _make_observation(instrument_id="SYN-Y", observation_id="obs-5m", timeframe="5m")
        rdg5 = _make_reading(instrument_id="SYN-Y", observation_id="obs-5m", timeframe="5m",
                             reading_id="r-5m", market_ts=datetime(2026, 8, 21, 11, 55, tzinfo=timezone.utc))
        repo.save_reading(obs5, rdg5)

        restored_at_start = repo.restore_active_observations()
        assert len(restored_at_start) == 1
        assert restored_at_start[0][1].timeframe == "5m"

        obs1h = _make_observation(instrument_id="SYN-Y", observation_id="obs-1h", timeframe="1h")
        rdg1h_first = _make_reading(instrument_id="SYN-Y", observation_id="obs-1h", timeframe="1h",
                                    reading_id="r-1h-1", market_ts=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
                                    candle_state="OPEN")
        repo.save_reading(obs1h, rdg1h_first)

        restored = repo.restore_active_observations()
        by_tf = {r.timeframe: (o, r) for o, r in restored}
        assert "5m" in by_tf
        assert "1h" in by_tf
        assert by_tf["5m"][1].reading_id == "r-5m"
        assert by_tf["1h"][1].reading_id == "r-1h-1"
        assert by_tf["1h"][1].prev_reading_id is None

    def test_latest_1h_does_not_see_5m_history(self, repo):
        obs5 = _make_observation(instrument_id="SYN-Z", observation_id="obs-5m", timeframe="5m")
        repo.save_reading(obs5, _make_reading(
            instrument_id="SYN-Z", observation_id="obs-5m", timeframe="5m",
            reading_id="r-5m", market_ts=datetime(2026, 8, 21, 11, 55, tzinfo=timezone.utc),
        ))

        obs1h = _make_observation(instrument_id="SYN-Z", observation_id="obs-1h", timeframe="1h")
        repo.save_reading(obs1h, _make_reading(
            instrument_id="SYN-Z", observation_id="obs-1h", timeframe="1h",
            reading_id="r-1h-1", market_ts=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
            candle_state="OPEN",
        ))

        read_conn = sqlite3.connect(str(repo.db_path))
        try:
            row = read_conn.execute(
                "SELECT market_data_timestamp, prev_reading_id FROM instrument_readings WHERE reading_id='r-1h-1'"
            ).fetchone()
        finally:
            read_conn.close()
        assert row[0] == "2026-08-21T12:00:00+00:00"
        assert row[1] is None


class TestCandleLifecycle:
    def test_first_1h_cycle_creates_closed_anchor_and_open(self, repo):
        obs = _make_observation()
        anchor = _make_reading(
            reading_id="rdg-anchor", market_ts=datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc),
            candle_state="CLOSED", close=110.0, scan_hour=11, scan_minute=15,
        )
        assert repo.save_reading(obs, anchor) == "ACCEPTED"

        current = _make_reading(
            reading_id="rdg-open", market_ts=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
            candle_state="OPEN", close=112.0, scan_hour=12, scan_minute=15,
        )
        assert repo.save_reading(obs, current) == "ACCEPTED"

        restored = repo.restore_active_observations()
        assert len(restored) == 1
        obs_r, rdg = restored[0]
        assert rdg.reading_id == "rdg-open"
        assert rdg.candle_state == "OPEN"
        assert rdg.prev_reading_id == "rdg-anchor"

    def test_open_progress_revisions_then_closed(self, repo):
        obs = _make_observation()
        candle_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

        r1 = _make_reading(reading_id="rdg-1", market_ts=candle_ts, candle_state="OPEN",
                           close=101.0, scan_hour=12, scan_minute=15)
        assert repo.save_reading(obs, r1) == "ACCEPTED"

        r2 = _make_reading(reading_id="rdg-2", market_ts=candle_ts, candle_state="OPEN",
                           close=102.0, scan_hour=12, scan_minute=30)
        assert repo.save_reading(obs, r2) == "CANDLE_PROGRESS_ACCEPTED"

        r3 = _make_reading(reading_id="rdg-3", market_ts=candle_ts, candle_state="OPEN",
                           close=103.0, scan_hour=12, scan_minute=45)
        assert repo.save_reading(obs, r3) == "CANDLE_PROGRESS_ACCEPTED"

        r4 = _make_reading(reading_id="rdg-4", market_ts=candle_ts, candle_state="CLOSED",
                           close=104.0, scan_hour=13, scan_minute=0)
        assert repo.save_reading(obs, r4) == "CANDLE_PROGRESS_ACCEPTED"

        conn = sqlite3.connect(str(repo.db_path))
        try:
            rows = conn.execute(
                "SELECT reading_id, candle_state, revision_number, supersedes_reading_id "
                "FROM instrument_readings WHERE market_data_timestamp=? ORDER BY revision_number",
                (candle_ts.isoformat(),),
            ).fetchall()
        finally:
            conn.close()

        assert [r[2] for r in rows] == [1, 2, 3, 4]
        assert [r[1] for r in rows] == ["OPEN", "OPEN", "OPEN", "CLOSED"]
        assert rows[1][0] == "rdg-2" and rows[1][3] == "rdg-1"
        assert rows[2][0] == "rdg-3" and rows[2][3] == "rdg-2"
        assert rows[3][0] == "rdg-4" and rows[3][3] == "rdg-3"

    def test_next_1h_timestamp_starts_revision_1(self, repo):
        obs = _make_observation()
        candle1 = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        repo.save_reading(obs, _make_reading(reading_id="rdg-1", market_ts=candle1,
                                             candle_state="OPEN", close=101.0,
                                             scan_hour=12, scan_minute=15))
        repo.save_reading(obs, _make_reading(reading_id="rdg-2", market_ts=candle1,
                                             candle_state="CLOSED", close=102.0,
                                             scan_hour=13, scan_minute=0))

        candle2 = datetime(2026, 8, 21, 13, 0, tzinfo=timezone.utc)
        result = repo.save_reading(obs, _make_reading(reading_id="rdg-3", market_ts=candle2,
                                                      candle_state="OPEN", close=103.0,
                                                      scan_hour=13, scan_minute=15))
        assert result == "ACCEPTED"

        conn = sqlite3.connect(str(repo.db_path))
        try:
            nxt = conn.execute(
                "SELECT revision_number, supersedes_reading_id FROM instrument_readings WHERE reading_id='rdg-3'"
            ).fetchone()
        finally:
            conn.close()
        assert nxt[0] == 1
        assert nxt[1] is None

    def test_source_revision_accepted_only_after_closed(self, repo):
        obs = _make_observation()
        candle_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

        repo.save_reading(obs, _make_reading(reading_id="rdg-1", market_ts=candle_ts,
                                             candle_state="OPEN", close=101.0,
                                             scan_hour=12, scan_minute=15))

        # korekta świecy OPEN jest traktowana jako postęp, nie SOURCE_REVISION
        corr_open = _make_reading(reading_id="rdg-2", market_ts=candle_ts,
                                  candle_state="OPEN", close=101.5,
                                  scan_hour=12, scan_minute=30)
        assert repo.save_reading(obs, corr_open) == "CANDLE_PROGRESS_ACCEPTED"

        # świeca CLOSED
        repo.save_reading(obs, _make_reading(reading_id="rdg-3", market_ts=candle_ts,
                                             candle_state="CLOSED", close=102.0,
                                             scan_hour=13, scan_minute=0))

        # korekta CLOSED => SOURCE_REVISION_ACCEPTED
        corr_closed = _make_reading(reading_id="rdg-4", market_ts=candle_ts,
                                    candle_state="CLOSED", close=102.5,
                                    scan_hour=13, scan_minute=5)
        assert repo.save_reading(obs, corr_closed) == "SOURCE_REVISION_ACCEPTED"


@pytest.fixture()
def in_memory_repo():
    return HistoryRepository()


class TestRepositoryTimeframeParity:
    """Ten sam scenariusz na HistoryRepository (in-memory) i
    SQLiteHistoryRepository (tymczasowa baza) musi dać identyczne wyniki."""

    def _trace_1h_lifecycle(self, repo):
        obs = _make_observation(instrument_id="PAR-1H", observation_id="obs-par-1h",
                                timeframe="1h")
        ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)

        def rdg(reading_id, candle_state, close, scan_hour, scan_minute):
            return _make_reading(
                instrument_id="PAR-1H", observation_id="obs-par-1h", timeframe="1h",
                reading_id=reading_id, market_ts=ts, candle_state=candle_state,
                close=close, scan_hour=scan_hour, scan_minute=scan_minute,
            )

        return [
            repo.save_reading(obs, rdg("p1", "OPEN", 101.0, 12, 15)),
            repo.save_reading(obs, rdg("p2", "OPEN", 102.0, 12, 30)),
            repo.save_reading(obs, rdg("p3", "CLOSED", 103.0, 13, 0)),
            repo.save_reading(obs, rdg("p3b", "CLOSED", 103.0, 13, 1)),
            repo.save_reading(obs, rdg("p4", "CLOSED", 104.0, 13, 5)),
            repo.save_reading(obs, rdg("p5", "OPEN", 104.0, 13, 10)),
        ]

    def test_1h_lifecycle_parity(self, in_memory_repo, repo):
        expected = [
            "ACCEPTED",
            "CANDLE_PROGRESS_ACCEPTED",
            "CANDLE_PROGRESS_ACCEPTED",
            "DUPLICATE_NO_OP",
            "SOURCE_REVISION_ACCEPTED",
            "CONFLICT",
        ]
        mem = self._trace_1h_lifecycle(in_memory_repo)
        sql = self._trace_1h_lifecycle(repo)
        assert mem == sql
        assert mem == expected

    def _trace_5m_then_1h(self, repo):
        ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        obs5m = _make_observation(instrument_id="PAR-X", observation_id="obs-5m",
                                  timeframe="5m")
        obs1h = _make_observation(instrument_id="PAR-X", observation_id="obs-1h",
                                  timeframe="1h")

        r5m = repo.save_reading(obs5m, _make_reading(
            instrument_id="PAR-X", observation_id="obs-5m", timeframe="5m",
            reading_id="x5m", market_ts=ts, candle_state="LEGACY_UNKNOWN",
            close=200.0, scan_hour=11, scan_minute=55))
        r1h = repo.save_reading(obs1h, _make_reading(
            instrument_id="PAR-X", observation_id="obs-1h", timeframe="1h",
            reading_id="x1h", market_ts=ts, candle_state="OPEN",
            close=101.0, scan_hour=12, scan_minute=15))

        restored = repo.restore_active_observations()
        summary = sorted(
            (o.instrument_id, o.timeframe, r.reading_id, r.prev_reading_id)
            for o, r in restored
        )
        return (r5m, r1h, summary)

    def test_5m_and_1h_independent_and_not_mixed(self, in_memory_repo, repo):
        mem = self._trace_5m_then_1h(in_memory_repo)
        sql = self._trace_5m_then_1h(repo)
        assert mem == sql
        assert mem[0] == "ACCEPTED"
        assert mem[1] == "ACCEPTED"
        by_tf = {(iid, tf): prev for iid, tf, rid, prev in mem[2]}
        # historia 5m nie może zostać poprzednikiem 1h
        assert by_tf[("PAR-X", "1h")] is None


class TestTrajectoryReadAPI:
    """Wierny odczyt trajektorii świecy 1h z repozytorium (parytet API)."""

    def _seed(self, repo):
        ts5m = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        ts11 = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
        ts12 = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        ts13 = datetime(2026, 8, 21, 13, 0, tzinfo=timezone.utc)

        # Kolidujący 5m — musi zostać wykluczony.
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-5m", timeframe="5m"),
            _make_reading(instrument_id="TRJ", observation_id="obs-5m", timeframe="5m",
                          reading_id="t-5m", market_ts=ts5m, candle_state="LEGACY_UNKNOWN",
                          close=200.0, scan_hour=11, scan_minute=55),
        )
        # 11:00 CLOSED 1h.
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h"),
            _make_reading(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h",
                          reading_id="t-11", market_ts=ts11, candle_state="CLOSED",
                          close=100.0, scan_hour=11, scan_minute=10),
        )
        # 12:00 OPEN rev1..3 i CLOSED rev4.
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h"),
            _make_reading(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h",
                          reading_id="t-12-1", market_ts=ts12, candle_state="OPEN",
                          close=101.0, scan_hour=12, scan_minute=15),
        )
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h"),
            _make_reading(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h",
                          reading_id="t-12-2", market_ts=ts12, candle_state="OPEN",
                          close=102.0, scan_hour=12, scan_minute=30),
        )
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h"),
            _make_reading(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h",
                          reading_id="t-12-3", market_ts=ts12, candle_state="OPEN",
                          close=103.0, scan_hour=12, scan_minute=45),
        )
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h"),
            _make_reading(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h",
                          reading_id="t-12-4", market_ts=ts12, candle_state="CLOSED",
                          close=104.0, scan_hour=13, scan_minute=0),
        )
        # 13:00 OPEN rev1.
        repo.save_reading(
            _make_observation(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h"),
            _make_reading(instrument_id="TRJ", observation_id="obs-1h", timeframe="1h",
                          reading_id="t-13-1", market_ts=ts13, candle_state="OPEN",
                          close=105.0, scan_hour=13, scan_minute=15),
        )
        return ts11, ts12, ts13

    def test_previous_closed_and_trajectory_in_memory(self, in_memory_repo):
        ts11, ts12, ts13 = self._seed(in_memory_repo)

        prev_for_12 = in_memory_repo.get_previous_closed("TRJ", "1h", ts12)
        assert prev_for_12 is not None
        assert prev_for_12.market_data_timestamp == ts11
        assert prev_for_12.candle_state == "CLOSED"

        traj_12 = in_memory_repo.get_current_trajectory("TRJ", "1h", ts12)
        assert [r.revision_number for r in traj_12] == [1, 2, 3, 4]
        assert [r.candle_state for r in traj_12] == ["OPEN", "OPEN", "OPEN", "CLOSED"]

        prev_for_13 = in_memory_repo.get_previous_closed("TRJ", "1h", ts13)
        assert prev_for_13.market_data_timestamp == ts12
        assert prev_for_13.candle_state == "CLOSED"
        assert prev_for_13.revision_number == 4

        traj_13 = in_memory_repo.get_current_trajectory("TRJ", "1h", ts13)
        assert [r.revision_number for r in traj_13] == [1]
        assert traj_13[0].candle_state == "OPEN"

    def test_previous_closed_and_trajectory_sqlite(self, repo):
        ts11, ts12, ts13 = self._seed(repo)

        prev_for_12 = repo.get_previous_closed("TRJ", "1h", ts12)
        assert prev_for_12.market_data_timestamp == ts11
        assert prev_for_12.candle_state == "CLOSED"

        traj_12 = repo.get_current_trajectory("TRJ", "1h", ts12)
        assert [r.revision_number for r in traj_12] == [1, 2, 3, 4]
        assert [r.candle_state for r in traj_12] == ["OPEN", "OPEN", "OPEN", "CLOSED"]

        prev_for_13 = repo.get_previous_closed("TRJ", "1h", ts13)
        assert prev_for_13.market_data_timestamp == ts12
        assert prev_for_13.revision_number == 4
        assert prev_for_13.candle_state == "CLOSED"

        traj_13 = repo.get_current_trajectory("TRJ", "1h", ts13)
        assert [r.revision_number for r in traj_13] == [1]

    def test_sqlite_restart_same_trajectory(self, tmp_path):
        repo = SQLiteHistoryRepository(tmp_path / "traj.db")
        ts11, ts12, ts13 = self._seed(repo)

        repo2 = SQLiteHistoryRepository(tmp_path / "traj.db")
        prev = repo2.get_previous_closed("TRJ", "1h", ts13)
        traj = repo2.get_current_trajectory("TRJ", "1h", ts12)
        assert prev.market_data_timestamp == ts12
        assert prev.revision_number == 4
        assert [r.revision_number for r in traj] == [1, 2, 3, 4]

    def test_5m_excluded_from_trajectory(self, repo):
        self._seed(repo)
        ts12 = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        traj = repo.get_current_trajectory("TRJ", "1h", ts12)
        assert all(r.timeframe == "1h" for r in traj)
        assert len(traj) == 4
