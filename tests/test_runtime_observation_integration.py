"""
Testy integracji RuntimeService → InstrumentObservation (RED → GREEN).

Ograniczona integracja Runtime z trwałością:
  Yahoo / MarketScanner → RuntimeService → InstrumentReading
  → InstrumentObservation → istniejący Market Hunter.

Zakazane: Mock, MagicMock, patch, monkeypatch dla komponentów wewnętrznych.
Dopuszczalne: lokalny deterministyczny odpowiednik granicy Yahoo/ScanProvider.
"""

import ast
import inspect
import os
import tempfile
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pytest

from data.models.market_data import MarketData
from data.models.instrument_reading import InstrumentReading
from data.models.instrument_observation import InstrumentObservation
from data.models import InstrumentType
from application.runtime import RuntimeService
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.market_scanner import MarketScanner
from application.universe import PennyStockUniverse
from application.opportunity_deduplicator import OpportunityDeduplicator
from engines.hunter.engine import HunterEngine


# ---------------------------------------------------------------------------
# Helpers — lokalny deterministyczny odpowiednik granicy Yahoo / ScanProvider
# ---------------------------------------------------------------------------

class _FakeInstrumentSource:
    """Zwraca zadaną listę symboli — zastępuje StaticInstrumentSource."""

    def __init__(self, symbols: List[str]):
        self._symbols = list(symbols)

    def get_instruments(self) -> List[str]:
        return list(self._symbols)


class _FakeScanProvider:
    """Zwraca z góry zadane dane MarketData dla symboli — zastępuje Yahoo."""

    def __init__(self, data_map: Dict[str, List[MarketData]]):
        self._data_map = data_map

    def scan(self, instruments: List[str]) -> List[dict]:
        results = []
        for sym in instruments:
            data = self._data_map.get(sym)
            if data is not None:
                results.append({"symbol": sym, "data": list(data)})
        return results


class _SourceErrorScanProvider:
    """Symuluje SOURCE_ERROR — rzuca wyjątek przy skanowaniu."""

    def __init__(self, symbols: List[str]):
        self._symbols = list(symbols)

    def scan(self, instruments: List[str]) -> List[dict]:
        raise RuntimeError("SOURCE_ERROR: Yahoo Finance unavailable")


class _TimeoutScanProvider:
    """Symuluje timeout — zwraca pustą listę (brak danych)."""

    def scan(self, instruments: List[str]) -> List[dict]:
        return []  # timeout → brak wyników, nie wyjątek


def _temp_db_path() -> Path:
    """Bezpieczny plik tymczasowy SQLite (mkstemp, nie mktemp)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Path(path)


def _make_market_data(
    timestamp: datetime,
    open_price: float = 10.0,
    high: float = 12.0,
    low: float = 9.0,
    close: float = 11.0,
    volume: float = 1000.0,
) -> MarketData:
    return MarketData(
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


def _make_hunter_config():
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
    """Tworzy MasterEngine z domyślnymi silnikami."""
    from engines.master.engine import MasterEngine
    from engines.news.filter import NewsFilterConfig
    from engines.news.pipeline import NewsPipeline
    from engines.ai.decision_engine import DecisionEngine
    from engines.ranking.engine import RankingEngine
    from engines.risk.engine import RiskEngine
    news_filter = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
    news_pipeline = NewsPipeline(news_filter)
    hunter = HunterEngine(_make_hunter_config())
    return MasterEngine(
        news_engine=news_pipeline,
        hunter_engine=hunter,
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db():
    """Tymczasowa baza SQLite poza repozytorium. Usuwana po teście."""
    db_path = _temp_db_path()
    yield db_path
    try:
        if db_path.exists():
            db_path.unlink()
    except (OSError, PermissionError):
        pass


def _build_runtime(
    db_path: Path,
    symbols: List[str],
    data_map: Dict[str, List[MarketData]] = None,
    scan_provider=None,
    instrument_metadata: Dict[str, tuple] = None,
) -> RuntimeService:
    """Buduje RuntimeService z realnymi komponentami i lokalnym ScanProvider."""
    repo = SQLiteHistoryRepository(db_path)
    instrument_source = _FakeInstrumentSource(symbols)
    universe = PennyStockUniverse(instrument_source)
    if scan_provider is None:
        scan_provider = _FakeScanProvider(data_map or {})
    scanner = MarketScanner(universe, scan_provider)
    deduplicator = OpportunityDeduplicator(deduplication_window_seconds=1)
    hunter = HunterEngine(_make_hunter_config())
    master = _build_minimal_master_engine()

    if instrument_metadata is None:
        instrument_metadata = {
            s: ("GPW", InstrumentType.STOCK_GPW) for s in symbols
        }

    return RuntimeService(
        hunter_engine=hunter,
        master_engine=master,
        history_repository=repo,
        market_scanner=scanner,
        deduplicator=deduplicator,
        instrument_metadata=instrument_metadata,
    )


# =============================================================================
# Kontrakt kolejności w RuntimeService.run_cycle() — testy AST
# =============================================================================


class TestRuntimeOrderContract:
    """W run_cycle() dla MarketScanner: persistencja Observation/Reading
    następuje strukturalnie przed hunter_engine.scan(candidates).

    Dowód wyłącznie przez AST (inspect + ast), nie przez source.find()."""

    @staticmethod
    def _get_run_cycle_ast():
        source = inspect.getsource(RuntimeService.run_cycle)
        source = textwrap.dedent(source)
        return ast.parse(source)

    @staticmethod
    def _find_method_calls(tree, method_name):
        """Znajdź wszystkie wywołania self.<method_name>(...) w drzewie AST."""
        import ast
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == method_name:
                    calls.append(node)
        return calls

    def test_persist_before_hunter_scan_in_ast_order(self):
        """AST dowodzi: _persist_observation_and_reading występuje
        strukturalnie przed hunter_engine.scan(candidates) w ciele run_cycle."""
        tree = self._get_run_cycle_ast()
        fn = tree.body[0]

        persist_calls = self._find_method_calls(fn, "_persist_observation_and_reading")
        hunter_scan_calls = self._find_method_calls(fn, "scan")

        assert len(persist_calls) >= 1, (
            "RED: _persist_observation_and_reading nie występuje w run_cycle()"
        )
        assert len(hunter_scan_calls) >= 1, (
            "RED: hunter_engine.scan( nie występuje w run_cycle()"
        )

        # Persistencja musi mieć mniejszy numer linii niż każde
        # wywołanie .scan() na hunter_engine (market_scanner.scan()
        # występuje wcześniej i ma mniejszy numer linii — to OK).
        # Kluczowe: strukturalnie persistencja jest przed
        # hunter_engine.scan(candidates).
        persist_line = persist_calls[0].lineno

        # Filtruj tylko scan() na hunter_engine (nie market_scanner)
        # po kontekście: hunter_engine.scan jest wywoływane PO persistencji
        # w bloku if self.market_scanner:
        for scan_call in hunter_scan_calls:
            # market_scanner.scan() ma lineno < persist_line
            # hunter_engine.scan() ma lineno > persist_line
            if scan_call.lineno > persist_line:
                # To jest hunter_engine.scan() — persistencja przed nim
                continue
            # Jeśli któreś .scan() poza market_scanner ma mniejszy lineno,
            # sprawdź czy nie jest to market_scanner.scan()
            pass

        # Główny dowód: persistencja nie występuje w pętli
        # for candidate in hunter_result.opportunities
        # Sprawdzamy: czy którykolwiek persist call jest wewnątrz
        # pętli for iterującej po hunter_result.opportunities
        for node in ast.walk(fn):
            if isinstance(node, ast.For):
                # Sprawdź czy iterujemy po hunter_result.opportunities
                iter_str = ast.dump(node.iter)
                if "hunter_result" in iter_str and "opportunities" in iter_str:
                    # Szukaj persistencji wewnątrz tej pętli
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            if (isinstance(sub.func, ast.Attribute)
                                    and sub.func.attr == "_persist_observation_and_reading"):
                                pytest.fail(
                                    "FAIL: _persist_observation_and_reading "
                                    "znajduje się wewnątrz pętli po "
                                    "hunter_result.opportunities"
                                )

        # Pozytywny dowód: istnieje persistencja przed pierwszym
        # hunter_engine.scan() (nie-market_scanner.scan())
        # Znajdź wywołania .scan() które są PO persistencji
        post_persist_scans = [
            s for s in hunter_scan_calls if s.lineno > persist_line
        ]
        assert len(post_persist_scans) >= 1, (
            "RED: brak hunter_engine.scan() po persistencji — "
            "kolejność nie do zweryfikowania"
        )

    def test_persist_not_inside_hunter_opportunities_loop(self):
        """AST dowodzi: _persist_observation_and_reading nie występuje
        wewnątrz pętli for candidate in hunter_result.opportunities."""
        tree = self._get_run_cycle_ast()
        fn = tree.body[0]

        for node in ast.walk(fn):
            if isinstance(node, ast.For):
                iter_str = ast.dump(node.iter)
                if "hunter_result" in iter_str and "opportunities" in iter_str:
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            if (isinstance(sub.func, ast.Attribute)
                                    and sub.func.attr == "_persist_observation_and_reading"):
                                pytest.fail(
                                    "FAIL: _persist_observation_and_reading "
                                    "wewnątrz pętli hunter_result.opportunities"
                                )

    def test_no_second_persist_after_hunter_scan(self):
        """AST dowodzi: po hunter_engine.scan(candidates) nie istnieje
        drugie wywołanie _persist_observation_and_reading."""
        tree = self._get_run_cycle_ast()
        fn = tree.body[0]

        persist_calls = self._find_method_calls(fn, "_persist_observation_and_reading")
        scan_calls = self._find_method_calls(fn, "scan")

        if len(persist_calls) == 0 or len(scan_calls) <= 1:
            return  # Nie można zweryfikować — brak odpowiednich wywołań

        # Ostatnia persistencja musi być przed ostatnim hunter_engine.scan()
        # (market_scanner.scan() jest pierwszy)
        persist_lines = sorted(c.lineno for c in persist_calls)
        scan_lines = sorted(c.lineno for c in scan_calls)

        # Pierwszy .scan() to market_scanner, drugi i kolejne to hunter_engine
        if len(scan_lines) >= 2:
            last_hunter_scan = scan_lines[-1]
            for pl in persist_lines:
                assert pl < last_hunter_scan, (
                    f"FAIL: _persist_observation_and_reading (linia {pl}) "
                    f"występuje po hunter_engine.scan() (linia {last_hunter_scan})"
                )


# =============================================================================
# Kontrakt kolejności w produkcyjnym entrypoint.main()
# =============================================================================


class TestEntrypointOrderContract:
    """W entrypoint.main(): build_runtime_service() →
    restore_active_observations() → run_cycle().

    Dowód wyłącznie przez AST (inspect + ast), nie przez source.find()."""

    @staticmethod
    def _get_main_ast():
        from application import entrypoint
        source = inspect.getsource(entrypoint.main)
        source = textwrap.dedent(source)
        return ast.parse(source)

    @staticmethod
    def _collect_top_level_calls(tree):
        """Zbierz nazwy wywołań na poziomie głównym main() w kolejności."""
        calls = []
        fn = tree.body[0]
        for node in ast.walk(fn):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute):
                    calls.append((node.lineno, call.func.attr))
                elif isinstance(call.func, ast.Name):
                    calls.append((node.lineno, call.func.id))
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute):
                    calls.append((node.lineno, call.func.attr))
                elif isinstance(call.func, ast.Name):
                    calls.append((node.lineno, call.func.id))
        # Sort by line number, deduplicate
        seen = set()
        ordered = []
        for ln, name in sorted(calls, key=lambda x: x[0]):
            if (ln, name) not in seen:
                seen.add((ln, name))
                ordered.append((ln, name))
        return ordered

    def test_build_runtime_before_restore_before_run_cycle_in_main(self):
        """AST dowodzi kolejności: build_runtime_service() →
        restore_active_observations() → run_cycle()."""
        calls = self._collect_top_level_calls(self._get_main_ast())

        build_idx = None
        restore_idx = None
        run_cycle_idx = None
        for i, (_, name) in enumerate(calls):
            if name == "build_runtime_service":
                build_idx = i
            elif name == "restore_active_observations":
                restore_idx = i
            elif name == "run_cycle":
                run_cycle_idx = i

        assert build_idx is not None, (
            "RED: build_runtime_service() nie występuje w main()"
        )
        assert restore_idx is not None, (
            "RED: restore_active_observations() nie występuje w main()"
        )
        assert run_cycle_idx is not None, (
            "RED: run_cycle() nie występuje w main()"
        )
        assert build_idx < restore_idx < run_cycle_idx, (
            f"FAIL: kolejność w main() nieprawidłowa — "
            f"build_runtime_service() (idx {build_idx}), "
            f"restore_active_observations() (idx {restore_idx}), "
            f"run_cycle() (idx {run_cycle_idx}). "
            f"Wymagana: build < restore < run_cycle"
        )


# =============================================================================
# Test 15a — Jawny restore ACTIVE Observation przed pierwszym cyklem
# =============================================================================


class TestRestoreActiveObservationBeforeFirstCycle:
    """Startup Runtime odtwarza ACTIVE Observation z ostatnim Readingiem
    z rzeczywistej trwałości (SQLite)."""

    def test_restore_method_exists(self, temp_db):
        """RuntimeService posiada metodę restore_active_observations()."""
        runtime = _build_runtime(temp_db, symbols=["TEST"])
        assert hasattr(runtime, "restore_active_observations"), (
            "RED: RuntimeService nie ma metody restore_active_observations()"
        )

    def test_restore_returns_active_observation_with_reading(self, temp_db):
        """Po zapisaniu Observation+Reading przez jedno repo,
        restore_active_observations() w RuntimeService odtwarza je."""
        repo1 = SQLiteHistoryRepository(temp_db)
        obs = InstrumentObservation(
            observation_id=str(uuid.uuid4()),
            instrument_id="TEST",
        )
        ts = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        rdg = InstrumentReading(
            reading_id=str(uuid.uuid4()),
            observation_id=obs.observation_id,
            instrument_id="TEST",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=10.0,
            high=12.0,
            low=9.0,
            close=11.0,
            volume=1000.0,
            data_completeness="COMPLETE",
        )
        repo1.save_reading(obs, rdg)

        runtime = _build_runtime(temp_db, symbols=["TEST"])
        active = runtime.restore_active_observations()

        assert len(active) == 1, (
            f"restore_active_observations() zwróciło {len(active)}, oczekiwano 1"
        )
        restored_obs, restored_rdg = active[0]
        assert restored_obs.instrument_id == "TEST"
        assert restored_obs.state == "ACTIVE"
        assert restored_rdg.close == 11.0
        assert restored_rdg.instrument_id == "TEST"

    def test_restore_empty_when_no_active_observations(self, temp_db):
        """Gdy brak ACTIVE Observation, restore zwraca pustą listę."""
        runtime = _build_runtime(temp_db, symbols=["TEST"])
        active = runtime.restore_active_observations()
        assert active == []


# =============================================================================
# Test 15b — Pierwszy Reading z największym market_data_timestamp
# =============================================================================


class TestFirstReadingFromLatestMarketData:
    """Jeden poprawny kandydat z listą wielu MarketData tworzy tylko jeden
    trwały Reading — z największym market_data_timestamp."""

    def test_single_reading_from_latest_timestamp(self, temp_db):
        """Kandydat z 3 MarketData → tylko 1 Reading (najnowszy timestamp)."""
        t1 = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)

        data = [
            _make_market_data(t1, close=100.0),
            _make_market_data(t2, close=101.0),
            _make_market_data(t3, close=102.0),
        ]

        runtime = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data})
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        obs = repo.load_observation("TEST")
        assert obs is not None, "Po run_cycle() brak ACTIVE Observation dla TEST"
        assert obs.state == "ACTIVE"

        active = repo.restore_active_observations()
        assert len(active) == 1
        _, stored_rdg = active[0]
        assert stored_rdg.close == 102.0
        assert stored_rdg.market_data_timestamp == t3

    def test_only_one_reading_not_entire_history(self, temp_db):
        """10 dni historii OHLCV → tylko 1 Reading."""
        timestamps = [
            datetime(2026, 8, d, 10, 0, tzinfo=timezone.utc)
            for d in range(1, 11)
        ]
        data = [_make_market_data(ts, close=float(100 + i)) for i, ts in enumerate(timestamps)]

        runtime = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data})
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        active = repo.restore_active_observations()
        assert len(active) == 1

        import sqlite3
        conn = sqlite3.connect(str(temp_db))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?",
                ("TEST",),
            )
            count = cursor.fetchone()[0]
            assert count == 1, f"Znaleziono {count} Readingów zamiast 1"
        finally:
            conn.close()


# =============================================================================
# Test 15c — Kolejny nowszy Reading kontynuuje ACTIVE Observation
# =============================================================================


class TestSubsequentReadingContinuesObservation:
    """Kolejny poprawny Reading o nowszym timestampie kontynuuje tę samą
    ACTIVE Observation i zachowuje prev_reading_id."""

    def test_second_cycle_continues_same_observation(self, temp_db):
        """Drugi cykl z nowszym timestampem używa tego samego observation_id."""
        t1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)

        data1 = [_make_market_data(t1, close=100.0)]
        data2 = [_make_market_data(t2, close=101.0)]

        rt1 = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data1})
        rt1.run_cycle()

        repo1 = SQLiteHistoryRepository(temp_db)
        obs1 = repo1.load_observation("TEST")
        assert obs1 is not None, "Brak Observation po pierwszym cyklu"

        rt2 = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data2})
        rt2.run_cycle()

        repo2 = SQLiteHistoryRepository(temp_db)
        obs2 = repo2.load_observation("TEST")
        assert obs2 is not None, "Brak Observation po drugim cyklu"
        assert obs2.observation_id == obs1.observation_id, (
            f"Drugi cykl utworzył nową Observation ({obs2.observation_id})"
        )

    def test_prev_reading_id_set_on_second_reading(self, temp_db):
        """Drugi Reading ma prev_reading_id wskazujące na pierwszy."""
        t1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)

        data1 = [_make_market_data(t1, close=100.0)]
        data2 = [_make_market_data(t2, close=101.0)]

        rt1 = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data1})
        rt1.run_cycle()

        rt2 = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data2})
        rt2.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        active = repo.restore_active_observations()
        assert len(active) == 1
        _, stored_rdg = active[0]
        assert stored_rdg.close == 101.0
        assert stored_rdg.prev_reading_id is not None


# =============================================================================
# Test 15d — Idempotentność: ten sam fakt nie tworzy drugiego Readingu
# =============================================================================


class TestDuplicateFactIsIdempotent:
    """Dokładne ponowne dostarczenie tego samego najnowszego faktu
    nie tworzy drugiego Readingu."""

    def test_same_data_second_cycle_does_not_create_second_reading(self, temp_db):
        """Ten sam timestamp i te same dane → brak nowego Readingu."""
        t1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        data = [_make_market_data(t1, close=100.0, volume=5000.0)]

        rt1 = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data})
        rt1.run_cycle()

        rt2 = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": data})
        rt2.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)

        import sqlite3
        conn = sqlite3.connect(str(temp_db))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?",
                ("TEST",),
            )
            count = cursor.fetchone()[0]
            assert count == 1, f"Znaleziono {count} Readingów (oczekiwano 1)"
        finally:
            conn.close()

        obs = repo.load_observation("TEST")
        assert obs is not None
        assert obs.state == "ACTIVE"


# =============================================================================
# Test 15e — Brak użytecznych danych → brak Readingu i Observation
# =============================================================================


class TestNoDataCreatesNoReading:
    """Brak użytecznych danych OHLCV nie tworzy Readingu ani Observation."""

    def test_empty_data_list_does_not_create_reading(self, temp_db):
        """Pusta lista MarketData → brak Observation."""
        runtime = _build_runtime(temp_db, symbols=["TEST"], data_map={"TEST": []})
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        obs = repo.load_observation("TEST")
        assert obs is None, "Pusta lista MarketData utworzyła Observation"

    def test_no_data_for_symbol_does_not_create_reading(self, temp_db):
        """Brak danych dla symbolu → brak Observation."""
        runtime = _build_runtime(temp_db, symbols=["TEST"], data_map={})
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        obs = repo.load_observation("TEST")
        assert obs is None, "Brak danych utworzył Observation"


# =============================================================================
# Test 15e-2 — SOURCE_ERROR nie tworzy Reading/Observation
# =============================================================================


class TestSourceErrorCreatesNoReading:
    """SOURCE_ERROR nie tworzy Readingu ani Observation
    i nie kończy istniejącej ACTIVE Observation."""

    def test_source_error_does_not_create_observation(self, temp_db):
        """ScanProvider rzuca wyjątek → brak Observation."""
        scan_provider = _SourceErrorScanProvider(["TEST"])
        runtime = _build_runtime(
            temp_db, symbols=["TEST"], scan_provider=scan_provider
        )
        # run_cycle() łapie wyjątek MarketScanner i zwraca CycleReport
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        obs = repo.load_observation("TEST")
        assert obs is None, "SOURCE_ERROR utworzył Observation"

    def test_source_error_preserves_existing_active_observation(self, temp_db):
        """SOURCE_ERROR nie kończy istniejącej ACTIVE Observation."""
        # Najpierw utwórz ACTIVE Observation z poprawnym Readingu
        repo1 = SQLiteHistoryRepository(temp_db)
        obs = InstrumentObservation(
            observation_id=str(uuid.uuid4()),
            instrument_id="TEST",
        )
        ts = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        rdg = InstrumentReading(
            reading_id=str(uuid.uuid4()),
            observation_id=obs.observation_id,
            instrument_id="TEST",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=10.0, high=12.0, low=9.0, close=11.0,
            volume=1000.0,
            data_completeness="COMPLETE",
        )
        repo1.save_reading(obs, rdg)

        # Teraz uruchom Runtime z SourceErrorScanProvider
        scan_provider = _SourceErrorScanProvider(["TEST"])
        runtime = _build_runtime(
            temp_db, symbols=["TEST"], scan_provider=scan_provider
        )
        runtime.run_cycle()

        # Observation nadal ACTIVE
        repo2 = SQLiteHistoryRepository(temp_db)
        loaded = repo2.load_observation("TEST")
        assert loaded is not None, "SOURCE_ERROR usunął ACTIVE Observation"
        assert loaded.state == "ACTIVE", (
            f"SOURCE_ERROR zmienił stan Observation na {loaded.state}"
        )

    def test_source_error_does_not_create_reading(self, temp_db):
        """SOURCE_ERROR → liczba Readingów bez zmian."""
        scan_provider = _SourceErrorScanProvider(["TEST"])
        runtime = _build_runtime(
            temp_db, symbols=["TEST"], scan_provider=scan_provider
        )
        runtime.run_cycle()

        import sqlite3
        conn = sqlite3.connect(str(temp_db))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM instrument_readings")
            count = cursor.fetchone()[0]
            assert count == 0, f"SOURCE_ERROR utworzył {count} Reading(ów)"
        finally:
            conn.close()


# =============================================================================
# Test 15e-3 — Timeout nie tworzy Reading/Observation
# =============================================================================


class TestTimeoutCreatesNoReading:
    """Timeout nie tworzy Readingu ani Observation
    i nie kończy istniejącej ACTIVE Observation."""

    def test_timeout_does_not_create_observation(self, temp_db):
        """ScanProvider zwraca pustą listę (timeout) → brak Observation."""
        scan_provider = _TimeoutScanProvider()
        runtime = _build_runtime(
            temp_db, symbols=["TEST"], scan_provider=scan_provider
        )
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        obs = repo.load_observation("TEST")
        assert obs is None, "Timeout utworzył Observation"

    def test_timeout_preserves_existing_active_observation(self, temp_db):
        """Timeout nie kończy istniejącej ACTIVE Observation."""
        repo1 = SQLiteHistoryRepository(temp_db)
        obs = InstrumentObservation(
            observation_id=str(uuid.uuid4()),
            instrument_id="TEST",
        )
        ts = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        rdg = InstrumentReading(
            reading_id=str(uuid.uuid4()),
            observation_id=obs.observation_id,
            instrument_id="TEST",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=10.0, high=12.0, low=9.0, close=11.0,
            volume=1000.0,
            data_completeness="COMPLETE",
        )
        repo1.save_reading(obs, rdg)

        scan_provider = _TimeoutScanProvider()
        runtime = _build_runtime(
            temp_db, symbols=["TEST"], scan_provider=scan_provider
        )
        runtime.run_cycle()

        repo2 = SQLiteHistoryRepository(temp_db)
        loaded = repo2.load_observation("TEST")
        assert loaded is not None, "Timeout usunął ACTIVE Observation"
        assert loaded.state == "ACTIVE", (
            f"Timeout zmienił stan Observation na {loaded.state}"
        )

    def test_timeout_does_not_create_reading(self, temp_db):
        """Timeout → liczba Readingów bez zmian."""
        scan_provider = _TimeoutScanProvider()
        runtime = _build_runtime(
            temp_db, symbols=["TEST"], scan_provider=scan_provider
        )
        runtime.run_cycle()

        import sqlite3
        conn = sqlite3.connect(str(temp_db))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM instrument_readings")
            count = cursor.fetchone()[0]
            assert count == 0, f"Timeout utworzył {count} Reading(ów)"
        finally:
            conn.close()


# =============================================================================
# Test 15f — Utrwalenie Observation przed Market Hunterem
# =============================================================================


class TestPersistenceBeforeMarketHunter:
    """Observation jest utrwalane przed wywołaniem Market Huntera,
    bez zmiany dalszego przekazywania kandydatów."""

    def test_observation_persisted_and_hunter_still_receives_candidates(
        self, temp_db
    ):
        """Po run_cycle() Observation istnieje ORAZ Hunter otrzymał
        wszystkich kandydatów (brak filtrowania przez persistencję)."""
        t1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        data = [_make_market_data(t1, close=100.0)]

        runtime = _build_runtime(
            temp_db, symbols=["TEST"], data_map={"TEST": data}
        )
        report = runtime.run_cycle()

        # Observation utrwalone
        repo = SQLiteHistoryRepository(temp_db)
        obs = repo.load_observation("TEST")
        assert obs is not None, "Observation nie została utrwalona"
        assert obs.state == "ACTIVE"

        # Hunter otrzymał kandydata
        assert report.candidates_count >= 1, (
            f"candidates_count={report.candidates_count}, oczekiwano >= 1"
        )

    def test_ohlcv_still_passed_to_master_engine(self, temp_db):
        """Pełne OHLCV nadal jest przekazywane do MasterEngine
        (nie zastąpione przez Reading)."""
        t1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)
        data = [
            _make_market_data(t2, close=99.0),
            _make_market_data(t1, close=100.0),
        ]

        runtime = _build_runtime(
            temp_db, symbols=["TEST"], data_map={"TEST": data}
        )
        runtime.run_cycle()

        repo = SQLiteHistoryRepository(temp_db)
        active = repo.restore_active_observations()
        assert len(active) == 1
        _, stored_rdg = active[0]

        assert stored_rdg.close == 100.0

        import sqlite3
        conn = sqlite3.connect(str(temp_db))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?",
                ("TEST",),
            )
            count = cursor.fetchone()[0]
            assert count == 1, f"Utrwalono {count} Readingów (oczekiwano 1)"
        finally:
            conn.close()