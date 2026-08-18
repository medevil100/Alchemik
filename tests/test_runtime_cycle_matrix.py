# -*- coding: utf-8 -*-
"""ALCHEMIK — Krok 4/8 — TEST-FIRST RED: pierwszy cykl matrycy i kolejne cykle porównawcze Runtime.

Kontrakt zatwierdzonego cyklu:
- Pierwszy poprawny cykl (brak wcześniejszego UniverseSnapshot) tworzy trwałą matrycę rynku,
  Observation, Reading i baseline, ale NIE uruchamia HunterEngine, MasterEngine, Tavily,
  OpenAI, AlertBuilder, AlertDispatcher ani TelegramChannel.
- Kolejne cykle porównują nowe dane z ostatnim trwałym Readingiem tego samego symbolu.
  Brak rzeczywistej zmiany nie uruchamia dalszych modułów. Instrument ze zmianą może
  przejść do istniejących silników zgodnie z ich obecnymi kontraktami.
- Nic nie jest usuwane z rejestru tylko dlatego, że w bieżącym cyklu nie ma danych,
  zmiany albo sygnału.

Zakazane: Mock, MagicMock, patch, monkeypatch dla komponentów wewnętrznych ALCHEMIKA
(RuntimeService, MarketScanner, HistoryRepository, SQLite, HunterEngine, MasterEngine,
pozostałe wewnętrzne moduły). Dozwolony wyłącznie deterministyczny test double
na zewnętrznej granicy Yahoo (session: paginate_screener + fetch_chart).
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from data.models.market_data import MarketData
from data.models import InstrumentType
from application.runtime import RuntimeService
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.market_scanner import MarketScanner
from application.universe import PennyStockUniverse
from application.sources.yahoo_discovery_source import YahooDiscoverySource
from application.providers.yahoo_chart_provider import YahooChartProvider
from application.opportunity_deduplicator import OpportunityDeduplicator
from data.yahoo.yahoo_session import FetchResult, OutcomeKind, ScreenerPage, ScreenerPagination
from engines.hunter.engine import HunterEngine


# ---------------------------------------------------------------------------
# Deterministyczny test double — wyłącznie zewnętrzna granica Yahoo
# ---------------------------------------------------------------------------

def _make_quote(symbol: str, price: float = 1.0) -> dict:
    return {
        "symbol": symbol,
        "quoteType": "EQUITY",
        "exchange": "WSE",
        "market": "pl_market",
        "currency": "PLN",
        "regularMarketPrice": price,
    }


class _FakeYahooSession:
    """Zastępuje tylko transport Yahoo (screener + chart). Nie zastępuje
    żadnego wewnętrznego komponentu ALCHEMIKA."""

    def __init__(self, discovery_symbols, chart_map, screener_error=False, intraday_map=None):
        self._discovery_symbols = list(discovery_symbols)
        self._chart_map = dict(chart_map)   # symbol -> list[MarketData] | None (błąd chart)
        self._screener_error = screener_error
        # Warianty intraday (5d/5m) — domyślnie takie same jak daily.
        # Brak/ pusty wpis dla symbolu oznacza NO_INTRADAY (brak zamkniętej świecy 5m).
        self._intraday_map = {}
        if intraday_map is not None:
            self._intraday_map = dict(intraday_map)
        else:
            for sym, data in self._chart_map.items():
                if isinstance(data, list) and data:
                    self._intraday_map[sym] = data
                else:
                    self._intraday_map[sym] = None

    def paginate_screener(self, size=250):
        if self._screener_error:
            return FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message="HTTP 503")
        page = ScreenerPage(
            total=len(self._discovery_symbols),
            start=0,
            count=len(self._discovery_symbols),
            quotes=[_make_quote(s) for s in self._discovery_symbols],
        )
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=ScreenerPagination(total=len(self._discovery_symbols), pages=[page]),
            message=None,
        )

    def fetch_chart(self, symbol, variant="daily"):
        if variant == "daily":
            data = self._chart_map.get(symbol)
        elif variant == "intraday":
            data = self._intraday_map.get(symbol)
        else:
            return FetchResult(kind=OutcomeKind.MISSING_FIELDS, data=None, message=f"unknown variant {variant}")
        if data is None:
            return FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message=f"HTTP 404 for {symbol}")
        if isinstance(data, list) and not data:
            return FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=_chart_payload(symbol, data, variant=variant),
            message=None,
        )


def _chart_payload(symbol: str, market_data: list, variant: str = "daily") -> dict:
    ts = [int(md.timestamp.timestamp()) for md in market_data]
    return {
        "variant": variant,
        "http_status": 200,
        "captured_at": "2026-08-18T00:00:00+00:00",
        "meta": {
            "symbol": symbol,
            "instrumentType": "EQUITY",
            "currency": "PLN",
            "exchangeName": "WSE",
            "gmtoffset": 7200,
            "timezone": "Europe/Warsaw",
        },
        "timestamp": ts,
        "open": [md.open for md in market_data],
        "high": [md.high for md in market_data],
        "low": [md.low for md in market_data],
        "close": [md.close for md in market_data],
        "volume": [md.volume for md in market_data],
        "events": {},
    }


def _make_market_data(
    timestamp: datetime,
    open_price: float = None,
    high: float = None,
    low: float = None,
    close: float = 11.0,
    volume: float = 1000.0,
) -> MarketData:
    """Utwórz poprawną świecę — OHLC zawsze spójne z close (gdy nie podane)."""
    open_price = close if open_price is None else open_price
    high = close + 1.0 if high is None else high
    low = close - 1.0 if low is None else low
    return MarketData(
        open=open_price, high=high, low=low, close=close, volume=volume, timestamp=timestamp,
    )


def _utc_ts(year, month, day, hour=10, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _temp_db_path() -> Path:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Path(path)


def _hunter_config():
    return {
        "ranking_weight": 0.4,
        "risk_weight": 0.3,
        "confidence_weight": 0.3,
        "min_ranking_score": 0.5,
        "max_risk_score": 0.7,
        "min_confidence": 0.6,
        "max_results": 10,
        "priority_thresholds": [0.9, 0.7, 0.5],
    }


def _build_minimal_master_engine():
    from engines.master.engine import MasterEngine
    from engines.news.filter import NewsFilterConfig
    from engines.news.pipeline import NewsPipeline
    from engines.ai.decision_engine import DecisionEngine
    from engines.ranking.engine import RankingEngine
    from engines.risk.engine import RiskEngine
    news_filter = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
    news_pipeline = NewsPipeline(news_filter)
    hunter = HunterEngine(_hunter_config())
    return MasterEngine(
        news_engine=news_pipeline,
        hunter_engine=hunter,
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
    )


def _build_runtime(db_path, symbols, chart_map, screener_error=False, instrument_metadata=None,
                   intraday_map=None):
    """Buduje prawdziwy RuntimeService z prawdziwymi wewnętrznymi komponentami.
    Jedynym test double jest granica Yahoo (session)."""
    session = _FakeYahooSession(
        symbols, chart_map, screener_error=screener_error, intraday_map=intraday_map,
    )
    discovery_source = YahooDiscoverySource(session)
    universe = PennyStockUniverse(discovery_source)
    provider = YahooChartProvider(session, discovery_source=discovery_source)
    scanner = MarketScanner(universe, provider)
    repo = SQLiteHistoryRepository(db_path)
    deduplicator = OpportunityDeduplicator(deduplication_window_seconds=1)
    hunter = HunterEngine(_hunter_config())
    master = _build_minimal_master_engine()

    if instrument_metadata is None:
        instrument_metadata = {s: ("GPW", InstrumentType.STOCK_GPW) for s in symbols}

    return RuntimeService(
        hunter_engine=hunter,
        master_engine=master,
        history_repository=repo,
        market_scanner=scanner,
        deduplicator=deduplicator,
        instrument_metadata=instrument_metadata,
        production_matrix_cycle=True,
    )


@pytest.fixture
def temp_db():
    db_path = _temp_db_path()
    yield db_path
    try:
        if db_path.exists():
            db_path.unlink()
    except (OSError, PermissionError):
        pass


def _trace_stage(trace, name):
    return trace.get("stages", {}).get(name, {})


# =============================================================================
# 1. Pierwszy cykl z jednym poprawnym instrumentem tworzy snapshot,
#    Observation, Reading i baseline.
# =============================================================================

class TestFirstCycleSingleInstrument:
    def test_first_cycle_creates_snapshot_observation_reading_baseline(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data = [_make_market_data(t1, close=11.0)]
        rt = _build_runtime(temp_db, symbols=["TST.WA"], chart_map={"TST.WA": data})
        report = rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)

        # Snapshot
        snap = repo.get_latest_snapshot()
        assert snap is not None, "Brak UniverseSnapshot po pierwszym cyklu"
        assert snap.unique_symbols == 1
        assert snap.members[0].symbol == "TST.WA"
        assert snap.members[0].present is True

        # Observation + Reading
        obs = repo.load_observation("TST.WA")
        assert obs is not None
        assert obs.state == "ACTIVE"
        active = repo.restore_active_observations()
        assert len(active) == 1
        _, stored = active[0]
        assert stored.instrument_id == "TST.WA"
        assert stored.close == 11.0

        # Baseline
        u = {i.symbol: i for i in repo.get_current_universe()}
        assert u["TST.WA"].baseline_status in ("PENDING_BASELINE", "BASELINE_READY")
        assert u["TST.WA"].last_reading_id == stored.reading_id


# =============================================================================
# 2. Pierwszy cykl nie uruchamia Huntera, MasterEngine, Tavily, AI ani Telegrama.
# =============================================================================

class TestFirstCycleNoEngines:
    def test_first_cycle_does_not_run_hunter_master_tavily_ai_telegram(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data = [_make_market_data(t1, close=11.0)]
        rt = _build_runtime(temp_db, symbols=["TST.WA"], chart_map={"TST.WA": data})
        report = rt.run_cycle()

        trace = report.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"
        assert _trace_stage(trace, "master").get("status") == "SKIPPED"
        assert _trace_stage(trace, "tavily").get("status") == "SKIPPED"
        assert _trace_stage(trace, "ai").get("status") == "SKIPPED"
        assert _trace_stage(trace, "telegram").get("status") == "SKIPPED"
        assert _trace_stage(trace, "alert_build").get("status") == "SKIPPED"
        assert _trace_stage(trace, "alert_dispatch").get("status") == "SKIPPED"

        # Brak FinalAnalysisResult i sygnału
        assert report.results == []
        assert report.success_count == 0
        # Jawny niebłędny wynik matrycy
        assert report.diagnostics.get("cycle_kind") == "BASELINE_INITIALIZED"
        assert report.diagnostics.get("baseline_created", 0) == 1


# =============================================================================
# 3. Pierwszy cykl z wieloma poprawnymi instrumentami zapisuje pełną matrycę.
# =============================================================================

class TestFirstCycleMultipleInstruments:
    def test_first_cycle_full_matrix(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map = {
            "AAA.WA": [_make_market_data(t1, close=10.0)],
            "BBB.WA": [_make_market_data(t1, close=20.0)],
            "CCC.WA": [_make_market_data(t1, close=30.0)],
        }
        rt = _build_runtime(temp_db, symbols=list(chart_map), chart_map=chart_map)
        report = rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        snap = repo.get_latest_snapshot()
        assert snap is not None
        assert snap.unique_symbols == 3
        members = {m.symbol: m for m in snap.members}
        assert set(members) == {"AAA.WA", "BBB.WA", "CCC.WA"}
        for m in members.values():
            assert m.present is True
            assert m.chart_status == "SUCCESS"

        ready = repo.restore_active_observations()
        assert len(ready) == 3
        by_sym = {r.instrument_id: r for _, r in ready}
        assert set(by_sym) == {"AAA.WA", "BBB.WA", "CCC.WA"}
        assert report.diagnostics.get("readings_saved", 0) == 3
        assert report.diagnostics.get("baseline_created", 0) == 3


# =============================================================================
# 4. Jeden błędny chart nie usuwa pozostałych instrumentów.
# =============================================================================

class TestBadChartDoesNotRemoveOthers:
    def test_one_bad_chart_keeps_other_instruments(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        # Daily poprawne dla OK1/OK2, intraday BRAK (NO_INTRADAY — brak zamkniętej
        # świecy 5m). BAD.WA nie ma daily ani intraday. Wszyscy pozostają w matrycy.
        chart_map = {
            "BAD.WA": None,  # błąd chart (HTTP 404)
            "OK1.WA": [_make_market_data(t1, close=10.0)],
            "OK2.WA": [_make_market_data(t1, close=20.0)],
        }
        intraday_map = {
            "BAD.WA": None,
            "OK1.WA": None,  # brak zamkniętej świecy intraday → NO_INTRADAY
            "OK2.WA": None,
        }
        rt = _build_runtime(temp_db, symbols=list(chart_map), chart_map=chart_map,
                            intraday_map=intraday_map)
        report = rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        universe = {i.symbol: i for i in repo.get_current_universe()}
        assert set(universe) == {"BAD.WA", "OK1.WA", "OK2.WA"}

        # Daily jest zachowane diagnostycznie (SUCCESS dla poprawnych).
        assert universe["OK1.WA"].daily_status == "SUCCESS"
        assert universe["OK2.WA"].daily_status == "SUCCESS"
        # Brak intraday → NO_INTRADAY: NIE powstaje Reading ani fałszywy baseline.
        assert universe["OK1.WA"].intraday_status == "FAILED"
        assert universe["OK2.WA"].intraday_status == "FAILED"
        assert universe["BAD.WA"].baseline_status in (None, "PENDING_BASELINE")
        # Brak baseline dla wszystkich — Reading nie powstał z daily.
        assert universe["OK1.WA"].last_reading_id in (None, "")
        assert universe["OK2.WA"].last_reading_id in (None, "")
        assert universe["BAD.WA"].last_reading_id in (None, "")
        # Żadne Obserwacje nie powstały (brak Readingu z intraday).
        assert repo.restore_active_observations() == []

        # Instrumenty pozostają w snapshotcie z jawną diagnostyką.
        snap = repo.get_latest_snapshot()
        assert snap is not None
        members = {m.symbol: m for m in snap.members}
        assert members["OK1.WA"].present is True
        assert members["OK2.WA"].present is True
        assert members["BAD.WA"].present is True

        # Hunter i dalsze moduły nie zostały uruchomione.
        trace = report.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"
        assert report.results == []
        assert report.success_count == 0

        # Cykl nie jest błędem globalnym i nie udaje pełnego sukcesu danych.
        assert report.diagnostics.get("cycle_kind") == "BASELINE_INITIALIZED"
        assert report.error_count == 0
        assert report.diagnostics.get("readings_saved", 0) == 0
        assert report.diagnostics.get("baseline_created", 0) == 0
        assert report.diagnostics.get("intraday_error", 0) == 3


# =============================================================================
# 5. Instrument z błędnym chart pozostaje w snapshotcie z diagnostyką.
# =============================================================================

class TestBadChartInSnapshotWithDiagnostics:
    def test_bad_chart_member_has_diagnostics(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map = {
            "BAD.WA": None,
            "OK.WA": [_make_market_data(t1, close=10.0)],
        }
        rt = _build_runtime(temp_db, symbols=list(chart_map), chart_map=chart_map)
        rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        snap = repo.get_latest_snapshot()
        assert snap is not None
        by_sym = {m.symbol: m for m in snap.members}
        assert "BAD.WA" in by_sym
        bad = by_sym["BAD.WA"]
        assert bad.chart_status == "FAILED"
        assert bad.candles_received == 0
        assert bad.candles_valid == 0


# =============================================================================
# 6. volume=0 przechodzi do Reading bez zmiany wartości.
# =============================================================================

class TestVolumeZeroPreserved:
    def test_volume_zero_stored_exactly(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data = [_make_market_data(t1, close=11.0, volume=0)]
        rt = _build_runtime(temp_db, symbols=["VOL.WA"], chart_map={"VOL.WA": data})
        rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        _, stored = repo.restore_active_observations()[0]
        assert stored.volume == 0

        import sqlite3 as _s
        conn = _s.connect(str(temp_db))
        try:
            cur = conn.cursor()
            cur.execute("SELECT volume FROM instrument_readings WHERE instrument_id=?", ("VOL.WA",))
            row = cur.fetchone()
            assert row is not None
            assert row[0] == 0
        finally:
            conn.close()


# =============================================================================
# 7. Krótka poprawna historia tworzy baseline, ale nie jest automatycznie
#    kwalifikowana do Technical Engine.
# =============================================================================

class TestShortHistoryBaselineNoTechnical:
    def test_short_history_creates_baseline_not_technical(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        t2 = _utc_ts(2026, 8, 16)
        data = [
            _make_market_data(t2, close=10.0),
            _make_market_data(t1, close=10.5),
        ]
        rt = _build_runtime(temp_db, symbols=["SHORT.WA"], chart_map={"SHORT.WA": data})
        report = rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        u = {i.symbol: i for i in repo.get_current_universe()}
        assert u["SHORT.WA"].baseline_status in ("PENDING_BASELINE", "BASELINE_READY")
        u_inst = u["SHORT.WA"]
        # Krótka historia nie jest automatycznie gotowa dla Technical Engine:
        # chart jest poprawny, ale NIE ma sygnału ani przekazania do silników.
        assert report.diagnostics.get("cycle_kind") == "BASELINE_INITIALIZED"
        assert u_inst.chart_status == "SUCCESS"


# =============================================================================
# 8. Drugi identyczny odczyt nie uruchamia dalszych modułów.
# =============================================================================

class TestSecondIdenticalReadingNoDownstream:
    def test_identical_reading_no_downstream(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data = [_make_market_data(t1, close=11.0, volume=500)]
        rt1 = _build_runtime(temp_db, symbols=["ID.WA"], chart_map={"ID.WA": data})
        rt1.run_cycle()

        # Drugi cykl: identyczne dane (ten sam timestamp, te same wartości)
        rt2 = _build_runtime(temp_db, symbols=["ID.WA"], chart_map={"ID.WA": data})
        report2 = rt2.run_cycle()

        trace = report2.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"
        assert _trace_stage(trace, "master").get("status") == "SKIPPED"
        assert report2.results == []
        assert report2.success_count == 0
        assert report2.diagnostics.get("unchanged", 0) >= 1

        # Tylko jeden trwały Reading
        repo = SQLiteHistoryRepository(temp_db)
        conn = sqlite3.connect(str(temp_db))
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?", ("ID.WA",))
            assert cur.fetchone()[0] == 1
        finally:
            conn.close()


# =============================================================================
# 9. Drugi odczyt z nowym timestampem, ale bez zmiany wartości rynkowych,
#    nie uruchamia dalszych modułów.
# =============================================================================

class TestSecondNewTimestampNoMarketChange:
    def test_new_timestamp_same_values_no_downstream(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        t2 = _utc_ts(2026, 8, 18)
        data1 = [_make_market_data(t1, close=11.0, volume=500)]
        data2 = [_make_market_data(t2, close=11.0, volume=500)]

        rt1 = _build_runtime(temp_db, symbols=["NTS.WA"], chart_map={"NTS.WA": data1})
        rt1.run_cycle()

        rt2 = _build_runtime(temp_db, symbols=["NTS.WA"], chart_map={"NTS.WA": data2})
        report2 = rt2.run_cycle()

        trace = report2.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"
        assert _trace_stage(trace, "master").get("status") == "SKIPPED"
        assert report2.results == []
        assert report2.diagnostics.get("unchanged", 0) >= 1

        # Nowy timestamp zapisany historycznie (2 Readingi)
        repo = SQLiteHistoryRepository(temp_db)
        active = repo.restore_active_observations()
        _, latest = active[0]
        assert latest.market_data_timestamp == t2


# =============================================================================
# 10. Drugi zmieniony odczyt dotyczy wyłącznie właściwego symbolu.
# =============================================================================

class TestSecondChangedReadingOnlyCorrectSymbol:
    def test_changed_symbol_routed_unchanged_not(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data_a1 = [_make_market_data(t1, close=10.0)]
        data_b1 = [_make_market_data(t1, close=20.0)]
        chart_map1 = {"CHG.WA": data_a1, "UNCH.WA": data_b1}
        rt1 = _build_runtime(temp_db, symbols=list(chart_map1), chart_map=chart_map1)
        rt1.run_cycle()

        # Drugi cykl: CHG.WA zmienia close, UNCH.WA bez zmian (nowy timestamp, te same wartości)
        t2 = _utc_ts(2026, 8, 18)
        data_a2 = [_make_market_data(t2, close=15.0)]
        data_b2 = [_make_market_data(t2, close=20.0)]
        chart_map2 = {"CHG.WA": data_a2, "UNCH.WA": data_b2}
        rt2 = _build_runtime(temp_db, symbols=list(chart_map2), chart_map=chart_map2)
        report2 = rt2.run_cycle()

        trace = report2.diagnostics.get("trace", {})
        # Hunter uruchomiony (jest zmiana), master może być wykonany (prawdziwe silniki)
        assert _trace_stage(trace, "hunter").get("status") in ("SUCCESS", "PARTIAL")
        # Niezmieniony symbol nie przeszedł dalej
        assert report2.diagnostics.get("changed", 0) == 1
        assert report2.diagnostics.get("unchanged", 0) == 1
        inst = trace.get("instruments", {})
        assert inst["UNCH.WA"].get("final_status") in ("SKIPPED", "NOT_STARTED")
        assert inst["CHG.WA"].get("final_status") in ("SUCCESS", "PARTIAL", "FAILED", "NOT_STARTED")


# =============================================================================
# 11. Niezmieniony drugi symbol nie przechodzi dalej.
# =============================================================================

class TestUnchangedSymbolNotRouted:
    def test_unchanged_symbol_stays(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        t2 = _utc_ts(2026, 8, 18)
        data1 = [_make_market_data(t1, close=7.0)]
        data2 = [_make_market_data(t2, close=7.0)]

        rt1 = _build_runtime(temp_db, symbols=["STAY.WA"], chart_map={"STAY.WA": data1})
        rt1.run_cycle()

        rt2 = _build_runtime(temp_db, symbols=["STAY.WA"], chart_map={"STAY.WA": data2})
        report2 = rt2.run_cycle()

        assert report2.diagnostics.get("changed", 0) == 0
        assert report2.diagnostics.get("unchanged", 0) == 1
        trace = report2.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"


# =============================================================================
# 12. Instrument nieobecny w drugim discovery otrzymuje present=false,
#     ale nie jest usuwany.
# =============================================================================

class TestMissingInstrumentPresentFalse:
    def test_missing_in_second_discovery_present_false_and_kept(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map1 = {"AAA.WA": [_make_market_data(t1, close=10.0)],
                       "BBB.WA": [_make_market_data(t1, close=20.0)]}
        rt1 = _build_runtime(temp_db, symbols=list(chart_map1), chart_map=chart_map1)
        rt1.run_cycle()

        # Drugi discovery: tylko AAA.WA
        t2 = _utc_ts(2026, 8, 18)
        chart_map2 = {"AAA.WA": [_make_market_data(t2, close=10.0)]}
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map=chart_map2)
        rt2.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        snap2 = repo.get_latest_snapshot()
        members = {m.symbol: m for m in snap2.members}
        assert "BBB.WA" in members
        assert members["BBB.WA"].present is False
        assert members["BBB.WA"].status == "MISSING_IN_CURRENT_SCAN"

        universe = {i.symbol: i for i in repo.get_current_universe()}
        assert "BBB.WA" in universe  # nie usunięty
        # Wcześniejszy baseline zachowany
        assert universe["BBB.WA"].baseline_status in ("PENDING_BASELINE", "BASELINE_READY")


# =============================================================================
# 13. Powracający instrument zachowuje wcześniejszy baseline i ciągłość historii.
# =============================================================================

class TestReappearingInstrument:
    def test_reappearing_keeps_baseline_and_history(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map1 = {"AAA.WA": [_make_market_data(t1, close=10.0)],
                       "BBB.WA": [_make_market_data(t1, close=20.0)]}
        rt1 = _build_runtime(temp_db, symbols=list(chart_map1), chart_map=chart_map1)
        rt1.run_cycle()

        repo1 = SQLiteHistoryRepository(temp_db)
        _, rdg1 = repo1.restore_active_observations()[0]

        # Drugi: tylko AAA.WA
        t2 = _utc_ts(2026, 8, 18)
        chart_map2 = {"AAA.WA": [_make_market_data(t2, close=10.0)]}
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map=chart_map2)
        rt2.run_cycle()

        # Trzeci: BBB.WA powraca
        t3 = _utc_ts(2026, 8, 19)
        chart_map3 = {"AAA.WA": [_make_market_data(t3, close=10.0)],
                       "BBB.WA": [_make_market_data(t3, close=21.0)]}
        rt3 = _build_runtime(temp_db, symbols=list(chart_map3), chart_map=chart_map3)
        rt3.run_cycle()

        repo3 = SQLiteHistoryRepository(temp_db)
        universe = {i.symbol: i for i in repo3.get_current_universe()}
        assert universe["BBB.WA"].status == "ACTIVE"
        assert universe["BBB.WA"].baseline_status in ("PENDING_BASELINE", "BASELINE_READY")
        # Ciągłość historii: pierwszy Reading BBB.WA nadal istnieje
        conn = sqlite3.connect(str(temp_db))
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?", ("BBB.WA",))
            assert cur.fetchone()[0] >= 1
        finally:
            conn.close()


# =============================================================================
# 14. Błąd całego discovery nie tworzy fałszywego pustego snapshotu.
# =============================================================================

class TestDiscoveryErrorNoFalseEmptySnapshot:
    def test_discovery_error_preserves_previous_matrix(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map1 = {"AAA.WA": [_make_market_data(t1, close=10.0)],
                       "BBB.WA": [_make_market_data(t1, close=20.0)]}
        rt1 = _build_runtime(temp_db, symbols=list(chart_map1), chart_map=chart_map1)
        rt1.run_cycle()

        # Drugi cykl: błąd całego discovery (screener HTTP 503)
        rt2 = _build_runtime(
            temp_db, symbols=["AAA.WA", "BBB.WA"],
            chart_map={}, screener_error=True,
        )
        report2 = rt2.run_cycle()

        repo2 = SQLiteHistoryRepository(temp_db)
        snap2 = repo2.get_latest_snapshot()
        assert snap2 is not None
        assert snap2.unique_symbols == 2  # poprzednia matryca zachowana
        assert report2.diagnostics.get("cycle_kind") == "SOURCE_ERROR"
        universe = {i.symbol: i for i in repo2.get_current_universe()}
        assert set(universe) == {"AAA.WA", "BBB.WA"}
        # Żaden wcześniejszy instrument nie jest oznaczony jako MISSING z powodu błędu źródła
        assert all(i.status != "MISSING_IN_CURRENT_SCAN" for i in universe.values())

    def test_discovery_error_first_cycle_no_snapshot(self, temp_db):
        rt = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={}, screener_error=True)
        report = rt.run_cycle()
        assert report.diagnostics.get("cycle_kind") == "SOURCE_ERROR"
        repo = SQLiteHistoryRepository(temp_db)
        assert repo.get_latest_snapshot() is None
        assert repo.get_current_universe() == []


# =============================================================================
# 15. Restart SQLite odtwarza ostatni snapshot i baseline przed kolejnym cyklem.
# =============================================================================

class TestRestartRestoresSnapshotAndBaseline:
    def test_restart_restores_snapshot_and_baseline(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data1 = [_make_market_data(t1, close=10.0)]
        rt1 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data1})
        rt1.run_cycle()

        # Restart: nowa instancja repo na tej samej bazie
        repo2 = SQLiteHistoryRepository(temp_db)
        snap = repo2.get_latest_snapshot()
        assert snap is not None
        assert snap.members[0].symbol == "AAA.WA"
        assert snap.members[0].baseline_status in ("PENDING_BASELINE", "BASELINE_READY")

        universe = repo2.restore_universe()
        assert len(universe) == 1
        assert universe[0].baseline_status in ("PENDING_BASELINE", "BASELINE_READY")

        # Kolejny cykl po restarcie: nowy timestamp, te same wartości → bez Huntera
        t2 = _utc_ts(2026, 8, 18)
        data2 = [_make_market_data(t2, close=10.0)]
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data2})
        report2 = rt2.run_cycle()
        trace = report2.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"


# =============================================================================
# 16. Nie powstaje fałszywy FinalAnalysisResult przy braku zmiany.
# =============================================================================

class TestNoFalseFinalAnalysisResult:
    def test_no_final_result_on_no_change(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data1 = [_make_market_data(t1, close=10.0)]
        rt1 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data1})
        rt1.run_cycle()

        t2 = _utc_ts(2026, 8, 18)
        data2 = [_make_market_data(t2, close=10.0)]
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data2})
        report2 = rt2.run_cycle()

        assert report2.results == []
        assert report2.success_count == 0
        trace = report2.diagnostics.get("trace", {})
        inst = trace.get("instruments", {}).get("AAA.WA", {})
        assert inst.get("final_result_created") in (False, None)


# =============================================================================
# 17. Nie jest wysyłany Telegram przy pierwszym baseline ani przy braku zmiany.
# =============================================================================

class TestNoTelegramOnBaselineOrNoChange:
    def test_no_telegram_on_first_baseline(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data = [_make_market_data(t1, close=10.0)]
        rt = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data})
        report = rt.run_cycle()
        trace = report.diagnostics.get("trace", {})
        assert _trace_stage(trace, "telegram").get("status") == "SKIPPED"
        assert trace.get("external_calls", {}).get("telegram_attempts") == 0

    def test_no_telegram_on_no_change(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data1 = [_make_market_data(t1, close=10.0)]
        rt1 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data1})
        rt1.run_cycle()

        t2 = _utc_ts(2026, 8, 18)
        data2 = [_make_market_data(t2, close=10.0)]
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data2})
        report2 = rt2.run_cycle()
        trace = report2.diagnostics.get("trace", {})
        assert _trace_stage(trace, "telegram").get("status") == "SKIPPED"
        assert trace.get("external_calls", {}).get("telegram_attempts") == 0


# =============================================================================
# 18. Liczniki cyklu rozróżniają: discovered, chart_ok, chart_error,
#     baseline_created, readings_saved, unchanged, changed, skipped_downstream
#     i errors.
# =============================================================================

class TestCycleCounters:
    def test_counters_distinguish_all_states(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map1 = {
            "BAD.WA": None,
            "OK1.WA": [_make_market_data(t1, close=10.0)],
            "OK2.WA": [_make_market_data(t1, close=20.0)],
        }
        rt1 = _build_runtime(temp_db, symbols=list(chart_map1), chart_map=chart_map1)
        report1 = rt1.run_cycle()
        d1 = report1.diagnostics
        assert d1.get("discovered", 0) == 3
        assert d1.get("chart_ok", 0) == 2
        assert d1.get("chart_error", 0) == 1
        assert d1.get("baseline_created", 0) == 2
        assert d1.get("readings_saved", 0) == 2
        assert d1.get("errors", 0) == 0
        assert d1.get("cycle_kind") == "BASELINE_INITIALIZED"

        # Drugi cykl: OK1 zmienia się, OK2 bez zmian (nowy timestamp, te same wartości)
        t2 = _utc_ts(2026, 8, 18)
        chart_map2 = {
            "OK1.WA": [_make_market_data(t2, close=15.0)],
            "OK2.WA": [_make_market_data(t2, close=20.0)],
        }
        rt2 = _build_runtime(temp_db, symbols=["OK1.WA", "OK2.WA"], chart_map=chart_map2)
        report2 = rt2.run_cycle()
        d2 = report2.diagnostics
        assert d2.get("discovered", 0) == 2
        assert d2.get("chart_ok", 0) == 2
        assert d2.get("changed", 0) == 1
        assert d2.get("unchanged", 0) == 1
        assert d2.get("skipped_downstream", 0) == 1
        # Instrument ze zmianą przechodzi do prawdziwych silników; dla historii
        # 1 świecy Technical Engine zwraca InsufficientDataError (zgodnie z
        # obecnym kontraktem). Nie jest to fałszywy błąd cyklu — jest to
        # rzeczywista decyzja silnika.
        assert d2.get("errors", 0) in (0, 1)
        assert d2.get("cycle_kind") == "SUBSEQUENT_CYCLE"


# =============================================================================
# 19. Snapshot zachowuje wszystkie historyczne statusy po ponownym odczycie.
# =============================================================================

class TestSnapshotPreservesHistoricalStatuses:
    def test_snapshots_keep_historical_statuses(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map1 = {"AAA.WA": [_make_market_data(t1, close=10.0)],
                       "BBB.WA": [_make_market_data(t1, close=20.0)]}
        rt1 = _build_runtime(temp_db, symbols=list(chart_map1), chart_map=chart_map1)
        rt1.run_cycle()

        t2 = _utc_ts(2026, 8, 18)
        chart_map2 = {"AAA.WA": [_make_market_data(t2, close=10.0)]}
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map=chart_map2)
        rt2.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        snap1 = repo.get_snapshot(repo.get_latest_snapshot().snapshot_id)
        # BBB.WA w drugim snapshotcie: present=False
        members2 = {m.symbol: m for m in snap1.members}
        assert members2["BBB.WA"].present is False
        assert members2["BBB.WA"].status == "MISSING_IN_CURRENT_SCAN"


# =============================================================================
# 20. Jeden problem instrumentu nie zatrzymuje pełnego cyklu.
# =============================================================================

class TestOneInstrumentProblemDoesNotStopCycle:
    def test_bad_chart_does_not_stop_cycle(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map = {
            "BAD.WA": None,
            "OK1.WA": [_make_market_data(t1, close=10.0)],
            "OK2.WA": [_make_market_data(t1, close=20.0)],
        }
        rt = _build_runtime(temp_db, symbols=list(chart_map), chart_map=chart_map)
        report = rt.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        ok_ready = repo.restore_active_observations()
        assert len(ok_ready) == 2  # OK1 i OK2 zapisane mimo błędu BAD
        assert report.error_count == 0


# =============================================================================
# 21. CycleReport/CycleTrace pozwala jednoznacznie stwierdzić charakter cyklu.
# =============================================================================

class TestCycleTraceAnswerability:
    def test_trace_answers_all_questions(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        chart_map = {"AAA.WA": [_make_market_data(t1, close=10.0)]}
        rt = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map=chart_map)
        report = rt.run_cycle()
        trace = report.diagnostics.get("trace", {})
        d = report.diagnostics

        # czy był to pierwszy cykl
        assert d.get("cycle_kind") == "BASELINE_INITIALIZED"
        # czy utworzono baseline
        assert d.get("baseline_created", 0) == 1
        # ile instrumentów odkryto
        assert d.get("discovered", 0) == 1
        # ile zapisano w snapshotcie
        snap_count = d.get("snapshot_symbols", 0)
        assert snap_count >= 1
        # ile miało poprawny chart
        assert d.get("chart_ok", 0) == 1
        # ile miało błąd chart
        assert d.get("chart_error", 0) == 0
        # ile Reading zapisano
        assert d.get("readings_saved", 0) == 1
        # ile odczytów było niezmienionych
        assert d.get("unchanged", 0) == 0
        # ile instrumentów miało zmianę
        assert d.get("changed", 0) == 0
        # ile skierowano do dalszego przetwarzania
        assert d.get("skipped_downstream", 0) == 0

        # dlaczego dany instrument nie przeszedł dalej — jawnie w trace
        inst = trace.get("instruments", {}).get("AAA.WA", {})
        assert inst.get("final_status") == "NOT_STARTED"

    def test_subsequent_trace_answers_why_not_routed(self, temp_db):
        t1 = _utc_ts(2026, 8, 17)
        data1 = [_make_market_data(t1, close=10.0)]
        rt1 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data1})
        rt1.run_cycle()

        t2 = _utc_ts(2026, 8, 18)
        data2 = [_make_market_data(t2, close=10.0)]
        rt2 = _build_runtime(temp_db, symbols=["AAA.WA"], chart_map={"AAA.WA": data2})
        report2 = rt2.run_cycle()
        d = report2.diagnostics
        assert d.get("cycle_kind") == "SUBSEQUENT_CYCLE"
        assert d.get("unchanged", 0) == 1
        trace = report2.diagnostics.get("trace", {})
        assert _trace_stage(trace, "hunter").get("status") == "SKIPPED"
        inst = trace.get("instruments", {}).get("AAA.WA", {})
        assert inst.get("final_status") in ("SKIPPED", "NOT_STARTED")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])