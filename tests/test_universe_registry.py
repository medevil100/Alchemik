# -*- coding: utf-8 -*-
"""ALCHEMIK — Krok 3/8 — RED: trwały rejestr pełnego uniwersum Yahoo."""
from __future__ import annotations

import json
import pathlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from application.sqlite_history_repository import SQLiteHistoryRepository
from data.models.universe_instrument import UniverseInstrument
from data.models.universe_snapshot import UniverseSnapshot


def _utc():
    return datetime.now(timezone.utc).isoformat()


def inst(symbol, **kw):
    d = {"quote_type": "EQUITY", "exchange": "WSE", "market": "pl_market",
         "currency": "PLN", "regular_market_price": 1.0,
         "first_seen_at": _utc(), "last_seen_at": _utc(), "status": "ACTIVE"}
    d.update(kw)
    return UniverseInstrument(symbol=symbol, **d)


def snap(sid, instruments, created_at=None):
    return UniverseSnapshot.from_discovery(sid, created_at or _utc(), instruments)


class Base(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix="alchemik_u3_")
        self.db_path = Path(d) / "universe.db"
        self.repo = SQLiteHistoryRepository(db_path=self.db_path)


class TestRegistryPart1(Base):
    def test_first_snapshot_saves_all_instruments(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA"), inst("CCC.WA")]))
        universe = self.repo.get_current_universe()
        self.assertEqual({i.symbol for i in universe},
                         {"AAA.WA", "BBB.WA", "CCC.WA"})

    def test_symbol_count_equals_unique_discovery_symbols(self):
        s = snap("s1", [inst("AAA.WA"), inst("BBB.WA"), inst("BBB.WA")])
        self.repo.save_universe_snapshot(s)
        universe = self.repo.get_current_universe()
        self.assertEqual(len(universe), 2)
        self.assertEqual(s.unique_symbols, 2)

    def test_exact_symbol_preserved_without_suffix(self):
        self.repo.save_universe_snapshot(snap("s1", [inst("IFR.WA")]))
        self.assertEqual(self.repo.get_current_universe()[0].symbol, "IFR.WA")

    def test_instrument_with_valid_chart_saved(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("AAA.WA", chart_status="SUCCESS", candles_received=250,
                 candles_valid=249, candles_rejected=1)]))
        self.assertEqual(self.repo.get_current_universe()[0].candles_valid, 249)

    def test_instrument_with_chart_error_saved(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("BBB.WA", chart_status="FAILED", candles_received=250,
                 candles_valid=0)]))
        u = self.repo.get_current_universe()[0]
        self.assertEqual(u.symbol, "BBB.WA")
        self.assertEqual(u.chart_status, "FAILED")

    def test_zero_valid_candles_remains_in_registry(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("CCC.WA", chart_status="FAILED", candles_received=250,
                 candles_valid=0)]))
        u = self.repo.get_current_universe()[0]
        self.assertEqual(u.candles_valid, 0)

    def test_volume_zero_does_not_make_status_error(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("DDD.WA", chart_status="SUCCESS", candles_received=3,
                 candles_valid=3)]))
        u = self.repo.get_current_universe()[0]
        self.assertEqual(u.status, "ACTIVE")
        self.assertEqual(u.chart_status, "SUCCESS")

    def test_short_valid_history_allows_baseline_status(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("AAA.WA", chart_status="SUCCESS", candles_received=5,
                 candles_valid=5, baseline_status="BASELINE_READY")]))
        self.assertIn(self.repo.get_current_universe()[0].baseline_status,
                      ("PENDING_BASELINE", "BASELINE_READY"))

    def test_second_snapshot_updates_last_seen_at(self):
        self.repo.save_universe_snapshot(snap("s1", [inst("AAA.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [
            inst("AAA.WA", last_seen_at="2099-01-01T00:00:00+00:00")]))
        self.assertEqual(self.repo.get_current_universe()[0].last_seen_at,
                         "2099-01-01T00:00:00+00:00")

    def test_second_snapshot_does_not_change_first_seen_at(self):
        first_seen = "2026-01-01T00:00:00+00:00"
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA", first_seen_at=first_seen)]))
        self.repo.save_universe_snapshot(snap("s2", [
            inst("AAA.WA", first_seen_at="2099-01-01T00:00:00+00:00")]))
        self.assertEqual(self.repo.get_current_universe()[0].first_seen_at,
                         first_seen)

    def test_missing_instrument_gets_missing_in_current_scan(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [inst("AAA.WA")]))
        by_sym = {i.symbol: i for i in self.repo.get_current_universe()}
        self.assertEqual(by_sym["BBB.WA"].status, "MISSING_IN_CURRENT_SCAN")

    def test_missing_instrument_not_removed(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [inst("AAA.WA")]))
        self.assertEqual({i.symbol for i in self.repo.get_current_universe()},
                         {"AAA.WA", "BBB.WA"})

    def test_new_instrument_added(self):
        self.repo.save_universe_snapshot(snap("s1", [inst("AAA.WA")]))
        self.repo.save_universe_snapshot(
            snap("s2", [inst("AAA.WA"), inst("CCC.WA", status="NEW_IN_CURRENT_SCAN")]))
        by_sym = {i.symbol: i for i in self.repo.get_current_universe()}
        self.assertEqual(by_sym["CCC.WA"].status, "NEW_IN_CURRENT_SCAN")

    def test_reappearing_instrument_returns_to_active(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [inst("AAA.WA")]))
        self.repo.save_universe_snapshot(
            snap("s3", [inst("AAA.WA"), inst("BBB.WA")]))
        by_sym = {i.symbol: i for i in self.repo.get_current_universe()}
        self.assertEqual(by_sym["BBB.WA"].status, "ACTIVE")

    def test_chart_error_does_not_clear_last_reading_id(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA", last_reading_id="rdg_1")]))
        self.repo.save_universe_snapshot(snap("s2", [
            inst("AAA.WA", chart_status="FAILED", last_reading_id=None)]))
        self.assertEqual(self.repo.get_current_universe()[0].last_reading_id,
                         "rdg_1")

    def test_repeated_symbol_does_not_create_two_instruments(self):
        self.repo.save_universe_snapshot(snap("s1", [inst("AAA.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [inst("AAA.WA")]))
        self.assertEqual(len(self.repo.get_current_universe()), 1)


class TestRegistryPart2(Base):
    def test_snapshot_keeps_record_count_and_unique_count(self):
        s = snap("s1", [inst("AAA.WA"), inst("BBB.WA"), inst("AAA.WA")])
        self.repo.save_universe_snapshot(s)
        loaded = self.repo.get_snapshot("s1")
        self.assertEqual(loaded.total_records, 3)
        self.assertEqual(loaded.unique_symbols, 2)

    def test_snapshot_save_is_atomic(self):
        self.repo.save_universe_snapshot(snap(
            "s1", [inst("AAA.WA"), inst("BBB.WA"), inst("CCC.WA")]))
        conn = sqlite3.connect(str(self.db_path))
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM universe_snapshots")
            sc = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM universe_snapshot_members")
            mc = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM universe_instruments")
            ic = c.fetchone()[0]
        finally:
            conn.close()
        self.assertEqual((sc, mc, ic), (1, 3, 3))

    def test_error_mid_save_rolls_back(self):
        bad = UniverseInstrument(symbol=None, quote_type="EQUITY")
        s = snap("s1", [inst("AAA.WA"), bad])
        with self.assertRaises(Exception):
            self.repo.save_universe_snapshot(s)
        conn = sqlite3.connect(str(self.db_path))
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM universe_snapshots")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT COUNT(*) FROM universe_instruments")
            self.assertEqual(c.fetchone()[0], 0)
        finally:
            conn.close()

    def test_latest_snapshot_returns_correct_members(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(
            snap("s2", [inst("AAA.WA"), inst("CCC.WA")]))
        latest = self.repo.get_latest_snapshot()
        self.assertEqual(latest.snapshot_id, "s2")
        by_sym = {m.symbol: m for m in latest.members}
        self.assertEqual(set(by_sym), {"AAA.WA", "BBB.WA", "CCC.WA"})
        self.assertTrue(by_sym["AAA.WA"].present)
        self.assertTrue(by_sym["CCC.WA"].present)
        self.assertFalse(by_sym["BBB.WA"].present)

    def test_restore_after_restart_returns_full_universe(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        repo2 = SQLiteHistoryRepository(db_path=self.db_path)
        universe = repo2.restore_universe()
        self.assertEqual({i.symbol for i in universe},
                         {"AAA.WA", "BBB.WA"})

    def test_existing_observation_and_reading_remain_after_migration(self):
        from data.models.instrument_observation import InstrumentObservation
        from data.models.instrument_reading import InstrumentReading
        obs = InstrumentObservation("obs_1", "AAA.WA")
        rdg = InstrumentReading(
            reading_id="rdg_1", observation_id="obs_1", instrument_id="AAA.WA",
            market_data_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
            scan_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
            open=1.0, high=1.5, low=0.5, close=1.1, volume=100)
        self.assertEqual(self.repo.save_reading(obs, rdg), "ACCEPTED")
        repo2 = SQLiteHistoryRepository(db_path=self.db_path)
        restored = repo2.restore_active_observations()
        self.assertEqual(restored[0][0].observation_id, "obs_1")
        self.assertEqual(restored[0][1].reading_id, "rdg_1")

    def test_migration_can_run_again_without_error(self):
        self.repo.save_universe_snapshot(snap("s1", [inst("AAA.WA")]))
        SQLiteHistoryRepository(db_path=self.db_path)
        SQLiteHistoryRepository(db_path=self.db_path)
        self.assertEqual(len(self.repo.get_current_universe()), 1)

    def test_empty_snapshot_does_not_clear_registry(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(snap("s2", []))
        self.assertEqual({i.symbol for i in self.repo.get_current_universe()},
                         {"AAA.WA", "BBB.WA"})

    def test_diagnostics_have_no_secrets(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("AAA.WA", chart_status="FAILED", candles_received=250,
                 candles_valid=0, rejection_reasons={"no_complete_rows": 250})]))
        s = json.dumps([i.to_row() for i in self.repo.get_current_universe()],
                       default=str).lower()
        for f in ("bot_token", "chat_id", "api_key", "authorization",
                  "bearer", "cookie", "crumb", "sk-", "tvly-"):
            self.assertNotIn(f, s)

    def test_no_test_runs_engines_ai_or_telegram(self):
        import pathlib
        source = pathlib.Path(__file__).read_text(encoding="utf-8")
        for f in ("engines" + ".master", "engines" + ".hunter",
                  "openai" + "_provider", "telegram" + "_channel",
                  "tav" + "ily"):
            self.assertNotIn(f, source)


class TestRegistryCorrections(Base):
    def test_fresh_db_has_member_status_columns_and_snapshot_sequence(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            c = conn.cursor()
            c.execute("PRAGMA table_info(universe_snapshot_members)")
            cols = {r[1] for r in c.fetchall()}
            c.execute("PRAGMA table_info(universe_snapshots)")
            snap_cols = {r[1] for r in c.fetchall()}
        finally:
            conn.close()
        self.assertTrue({"status", "first_seen_at", "last_seen_at"} <= cols)
        self.assertIn("sequence", snap_cols)

    def test_roundtrip_member_status_and_timestamps(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("NEW.WA", status="NEW_IN_CURRENT_SCAN",
                 first_seen_at="2026-01-01T00:00:00+00:00",
                 last_seen_at="2026-01-02T00:00:00+00:00")]))
        m = self.repo.get_snapshot("s1").members[0]
        self.assertEqual(m.status, "NEW_IN_CURRENT_SCAN")
        self.assertEqual(m.first_seen_at, "2026-01-01T00:00:00+00:00")
        self.assertEqual(m.last_seen_at, "2026-01-02T00:00:00+00:00")

    def test_two_snapshots_keep_distinct_historical_statuses(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("AAA.WA", status="NEW_IN_CURRENT_SCAN")]))
        self.repo.save_universe_snapshot(snap("s2", [
            inst("AAA.WA", status="ACTIVE")]))
        self.assertEqual(self.repo.get_snapshot("s1").members[0].status,
                         "NEW_IN_CURRENT_SCAN")
        self.assertEqual(self.repo.get_snapshot("s2").members[0].status,
                         "ACTIVE")

    def test_current_instrument_status_does_not_override_old_snapshot(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("AAA.WA", status="NEW_IN_CURRENT_SCAN",
                 last_reading_id="rdg_1")]))
        self.repo.save_universe_snapshot(snap("s2", [
            inst("AAA.WA", status="ACTIVE", last_reading_id="rdg_2")]))
        s1 = self.repo.get_snapshot("s1").members[0]
        self.assertEqual(s1.status, "NEW_IN_CURRENT_SCAN")
        self.assertEqual(s1.last_reading_id, "rdg_1")

    def test_missing_instrument_member_present_false(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [inst("AAA.WA")]))
        m = {m.symbol: m for m in self.repo.get_snapshot("s2").members}
        self.assertFalse(m["BBB.WA"].present)
        self.assertEqual(m["BBB.WA"].status, "MISSING_IN_CURRENT_SCAN")

    def test_reappearing_instrument_member_present_true(self):
        self.repo.save_universe_snapshot(
            snap("s1", [inst("AAA.WA"), inst("BBB.WA")]))
        self.repo.save_universe_snapshot(snap("s2", [inst("AAA.WA")]))
        self.repo.save_universe_snapshot(
            snap("s3", [inst("AAA.WA"), inst("BBB.WA")]))
        m3 = {m.symbol: m for m in self.repo.get_snapshot("s3").members}
        self.assertTrue(m3["BBB.WA"].present)
        self.assertEqual(m3["BBB.WA"].status, "ACTIVE")
        m2 = {m.symbol: m for m in self.repo.get_snapshot("s2").members}
        self.assertFalse(m2["BBB.WA"].present)

    def test_latest_snapshot_respects_write_order(self):
        t = "2099-01-01T00:00:00+00:00"
        self.repo.save_universe_snapshot(
            UniverseSnapshot.from_discovery("B", t, [inst("B.WA")]))
        self.repo.save_universe_snapshot(
            UniverseSnapshot.from_discovery("A", t, [inst("A.WA")]))
        self.assertEqual(self.repo.get_latest_snapshot().snapshot_id, "A")

    def test_latest_snapshot_stable_after_reopen(self):
        t = "2099-01-01T00:00:00+00:00"
        self.repo.save_universe_snapshot(
            UniverseSnapshot.from_discovery("B", t, [inst("B.WA")]))
        self.repo.save_universe_snapshot(
            UniverseSnapshot.from_discovery("A", t, [inst("A.WA")]))
        repo2 = SQLiteHistoryRepository(db_path=self.db_path)
        self.assertEqual(repo2.get_latest_snapshot().snapshot_id, "A")

    def test_sequence_monotonic_unique(self):
        for sid in ("s1", "s2", "s3"):
            self.repo.save_universe_snapshot(snap(sid, [inst(sid + ".WA")]))
        conn = sqlite3.connect(str(self.db_path))
        try:
            c = conn.cursor()
            c.execute("SELECT sequence FROM universe_snapshots ORDER BY sequence")
            seqs = [r[0] for r in c.fetchall()]
        finally:
            conn.close()
        self.assertEqual(seqs, [1, 2, 3])
        self.assertEqual(len(set(seqs)), 3)

    def test_migration_idempotent_fresh(self):
        SQLiteHistoryRepository(db_path=self.db_path)
        SQLiteHistoryRepository(db_path=self.db_path)
        self.repo.save_universe_snapshot(snap("s1", [inst("AAA.WA")]))
        self.assertEqual(len(self.repo.get_current_universe()), 1)

    def test_migration_empty_old_db_adds_columns(self):
        import tempfile as _tf
        old = pathlib.Path(_tf.mkdtemp(prefix="alchemik_u3m_")) / "old.db"
        conn = sqlite3.connect(str(old))
        try:
            c = conn.cursor()
            c.execute("CREATE TABLE universe_snapshots (snapshot_id TEXT PRIMARY KEY, created_at TEXT, total_records INTEGER NOT NULL DEFAULT 0, unique_symbols INTEGER NOT NULL DEFAULT 0)")
            c.execute("CREATE TABLE universe_snapshot_members (snapshot_id TEXT NOT NULL, symbol TEXT NOT NULL, present INTEGER NOT NULL DEFAULT 1, chart_status TEXT NOT NULL DEFAULT 'NOT_STARTED', candles_received INTEGER NOT NULL DEFAULT 0, candles_valid INTEGER NOT NULL DEFAULT 0, candles_rejected INTEGER NOT NULL DEFAULT 0, rejection_reasons_json TEXT NOT NULL DEFAULT '{}', baseline_status TEXT, last_reading_id TEXT, PRIMARY KEY (snapshot_id, symbol))")
            conn.commit()
        finally:
            conn.close()
        SQLiteHistoryRepository(db_path=old)
        conn = sqlite3.connect(str(old))
        try:
            c = conn.cursor()
            c.execute("PRAGMA table_info(universe_snapshot_members)")
            mc = {r[1] for r in c.fetchall()}
            c.execute("PRAGMA table_info(universe_snapshots)")
            sc = {r[1] for r in c.fetchall()}
        finally:
            conn.close()
        self.assertTrue({"status", "first_seen_at", "last_seen_at"} <= mc)
        self.assertIn("sequence", sc)

    def test_migration_old_db_reconstructs_history_without_data_loss(self):
        import tempfile as _tf
        old = pathlib.Path(_tf.mkdtemp(prefix="alchemik_u3m_")) / "old.db"
        conn = sqlite3.connect(str(old))
        try:
            c = conn.cursor()
            c.execute("CREATE TABLE universe_snapshots (snapshot_id TEXT PRIMARY KEY, created_at TEXT, total_records INTEGER NOT NULL DEFAULT 0, unique_symbols INTEGER NOT NULL DEFAULT 0)")
            c.execute("CREATE TABLE universe_snapshot_members (snapshot_id TEXT NOT NULL, symbol TEXT NOT NULL, present INTEGER NOT NULL DEFAULT 1, chart_status TEXT NOT NULL DEFAULT 'NOT_STARTED', candles_received INTEGER NOT NULL DEFAULT 0, candles_valid INTEGER NOT NULL DEFAULT 0, candles_rejected INTEGER NOT NULL DEFAULT 0, rejection_reasons_json TEXT NOT NULL DEFAULT '{}', baseline_status TEXT, last_reading_id TEXT, PRIMARY KEY (snapshot_id, symbol))")
            c.execute("INSERT INTO universe_snapshots VALUES ('s1','2026-01-01T00:00:00+00:00',1,1)")
            c.execute("INSERT INTO universe_snapshots VALUES ('s2','2026-01-02T00:00:00+00:00',1,1)")
            c.execute("INSERT INTO universe_snapshot_members (snapshot_id, symbol, present) VALUES ('s1','AAA.WA',1)")
            c.execute("INSERT INTO universe_snapshot_members (snapshot_id, symbol, present) VALUES ('s2','AAA.WA',1)")
            conn.commit()
        finally:
            conn.close()
        repo = SQLiteHistoryRepository(db_path=old)
        s1 = repo.get_snapshot("s1")
        self.assertEqual(s1.members[0].status, "NEW_IN_CURRENT_SCAN")
        self.assertEqual(s1.members[0].first_seen_at,
                         "2026-01-01T00:00:00+00:00")
        s2 = repo.get_snapshot("s2")
        self.assertEqual(s2.members[0].status, "ACTIVE")
        self.assertEqual(s2.members[0].last_seen_at,
                         "2026-01-02T00:00:00+00:00")
        self.assertEqual(len(repo.get_current_universe()), 0)
        SQLiteHistoryRepository(db_path=old)

    def test_observations_readings_snapshots_preserved_and_fks_ok(self):
        from data.models.instrument_observation import InstrumentObservation
        from data.models.instrument_reading import InstrumentReading
        self.repo.save_universe_snapshot(snap("s1", [inst("AAA.WA")]))
        obs = InstrumentObservation("obs_1", "AAA.WA")
        rdg = InstrumentReading(
            reading_id="rdg_1", observation_id="obs_1", instrument_id="AAA.WA",
            market_data_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
            scan_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
            open=1.0, high=1.5, low=0.5, close=1.1, volume=100)
        self.assertEqual(self.repo.save_reading(obs, rdg), "ACCEPTED")
        SQLiteHistoryRepository(db_path=self.db_path)
        self.assertEqual(len(self.repo.get_snapshot("s1").members), 1)
        restored = self.repo.restore_active_observations()
        self.assertEqual(restored[0][1].reading_id, "rdg_1")

    def test_get_snapshot_member_complete_no_defaults(self):
        self.repo.save_universe_snapshot(snap("s1", [
            inst("AAA.WA", status="BASELINE_READY", chart_status="SUCCESS",
                 candles_valid=5, rejection_reasons={"x": 1})]))
        m = self.repo.get_snapshot("s1").members[0]
        self.assertEqual(m.status, "BASELINE_READY")
        self.assertEqual(m.chart_status, "SUCCESS")
        self.assertEqual(m.candles_valid, 5)
        self.assertEqual(m.rejection_reasons, {"x": 1})


if __name__ == "__main__":
    unittest.main()
