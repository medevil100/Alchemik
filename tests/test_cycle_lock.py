"""ALCHEMIK — Krok 1/8 — kontraktowe testy blokady pojedynczego cyklu.

Testy uzywaja wylacznie rzeczywistych plikowych blokad w systemowym katalogu
tymczasowym. Zakazane jest tu: unittest.mock, Mock, MagicMock, patch, fake lock
i fake RuntimeService jako dowod dzialania blokady.

Test dwoch niezaleznych procesow nalezy do Kroku 2/8 i NIE jest wykonywany
w tym zadaniu.
"""
from __future__ import annotations

import inspect
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from application.cycle_lock import (
    CycleAlreadyRunningError,
    CycleLock,
    lock_identity_for_db,
    lock_path_for_db,
)


def _temp_lock_path(name: str) -> Path:
    base = Path(tempfile.gettempdir()) / "alchemik_step1_lock_test"
    base.mkdir(parents=True, exist_ok=True)
    return base / name


# ---------------------------------------------------------------------------
# 1. Pierwsza blokada dla sciezki bazy zostaje uzyskana.
# ---------------------------------------------------------------------------

def test_first_lock_acquired_for_db_path():
    db_path = _temp_lock_path("first_acquire.sqlite")
    lock = CycleLock(db_path)
    lock.acquire()
    try:
        assert lock.held
    finally:
        lock.release()
    assert not lock.held


# ---------------------------------------------------------------------------
# 2. Druga blokada dla tej samej sciezki natychmiast zglasza
#    CycleAlreadyRunningError.
# ---------------------------------------------------------------------------

def test_second_lock_same_path_raises_immediately():
    db_path = _temp_lock_path("second_raises.sqlite")
    lock1 = CycleLock(db_path)
    lock1.acquire()
    try:
        lock2 = CycleLock(db_path)
        with pytest.raises(CycleAlreadyRunningError):
            lock2.acquire()
    finally:
        lock1.release()


# ---------------------------------------------------------------------------
# 3. Po release() blokade mozna uzyskac ponownie.
# ---------------------------------------------------------------------------

def test_reacquire_after_release():
    db_path = _temp_lock_path("reacquire.sqlite")
    lock = CycleLock(db_path)
    lock.acquire()
    lock.release()
    lock2 = CycleLock(db_path)
    lock2.acquire()
    lock2.release()


# ---------------------------------------------------------------------------
# 4. Wyjatek wewnatrz context managera zwalnia blokade.
# ---------------------------------------------------------------------------

def test_exception_inside_context_manager_releases():
    db_path = _temp_lock_path("exception_release.sqlite")
    with pytest.raises(RuntimeError):
        with CycleLock(db_path):
            raise RuntimeError("boom")
    lock = CycleLock(db_path)
    lock.acquire()
    lock.release()


# ---------------------------------------------------------------------------
# 5. Dwa rozne pliki baz maja niezalezne blokady.
# ---------------------------------------------------------------------------

def test_two_different_db_paths_independent():
    db_a = _temp_lock_path("db_a.sqlite")
    db_b = _temp_lock_path("db_b.sqlite")
    lock_a = CycleLock(db_a)
    lock_b = CycleLock(db_b)
    lock_a.acquire()
    try:
        lock_b.acquire()
        lock_b.release()
    finally:
        lock_a.release()


# ---------------------------------------------------------------------------
# 6. Rownowazne reprezentacje tej samej sciezki tworza ta sama tozsamosc.
# ---------------------------------------------------------------------------

def test_equivalent_path_representations_same_identity():
    db = _temp_lock_path("equiv.sqlite")
    db_alt = _temp_lock_path("equiv.sqlite")
    db_other_dir = _temp_lock_path("other/equiv.sqlite")
    db_other_dir.parent.mkdir(parents=True, exist_ok=True)

    assert lock_identity_for_db(db) == lock_identity_for_db(db_alt)
    assert lock_identity_for_db(db) != lock_identity_for_db(db_other_dir)
    assert lock_path_for_db(db) == lock_path_for_db(db_alt)
    assert lock_path_for_db(db) != lock_path_for_db(db_other_dir)

    # Wariant z "." — resolve() usuwa segment.
    dotted = db.parent / "." / db.name
    assert lock_identity_for_db(dotted) == lock_identity_for_db(db)

    # Wariant z inna wielkoscia liter — na Windows sciezka jest normalizowana
    # bez rozrozniania wielkosci liter.
    uppercase = db.parent / db.name.upper()
    assert lock_identity_for_db(uppercase) == lock_identity_for_db(db)


# ---------------------------------------------------------------------------
# 7. Pozostajacy plik .lock bez blokady systemowej nie blokuje kolejnego cyklu.
# ---------------------------------------------------------------------------

def test_orphan_lock_file_without_system_lock_does_not_block():
    db_path = _temp_lock_path("orphan.sqlite")
    lock_path = lock_path_for_db(db_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(b"\x00")  # pozostajacy plik .lock bez blokady systemowej

    lock = CycleLock(db_path)
    lock.acquire()
    try:
        assert lock.held
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# 8. Produkcyjny composition root przekazuje rzeczywista blokade do
#    RuntimeService.
# ---------------------------------------------------------------------------

def test_production_composition_root_passes_real_lock():
    from application.entrypoint import build_runtime_service
    from application.cycle_lock import CycleLock as _CycleLock

    db_path = _temp_lock_path("composition_root.sqlite")

    class _FakeSession:
        """Test double wylacznie na zewnetrznej granicy Yahoo."""

        def paginate_screener(self, size=250):
            from data.yahoo.yahoo_session import (
                FetchResult,
                OutcomeKind,
                ScreenerPagination,
            )
            return FetchResult(
                kind=OutcomeKind.SUCCESS_WITH_DATA,
                data=ScreenerPagination(total=0, pages=[]),
                message=None,
            )

        def fetch_chart(self, symbol, variant="daily"):
            from data.yahoo.yahoo_session import FetchResult, OutcomeKind
            return FetchResult(
                kind=OutcomeKind.SUCCESS_NO_DATA,
                data=None,
                message=None,
            )

    runtime = build_runtime_service(persist_path=db_path, yahoo_session=_FakeSession())
    lock = getattr(runtime, "_cycle_lock", None)
    assert isinstance(lock, _CycleLock)
    assert lock.lock_path == lock_path_for_db(db_path)
    assert not lock.held


# ---------------------------------------------------------------------------
# 9. Recznie zbudowany RuntimeService bez blokady zachowuje kompatybilnosc.
# ---------------------------------------------------------------------------

def test_manual_runtime_without_lock_remains_compatible():
    from application.runtime import RuntimeService
    from application.history_repository import HistoryRepository
    from application.models import CycleReport
    from engines.hunter.engine import HunterEngine
    from engines.master.engine import MasterEngine
    from engines.news.filter import NewsFilterConfig
    from engines.news.pipeline import NewsPipeline
    from engines.ai.decision_engine import DecisionEngine
    from engines.ranking.engine import RankingEngine
    from engines.risk.engine import RiskEngine

    hunter_config = {
        "ranking_weight": 0.4,
        "risk_weight": 0.3,
        "confidence_weight": 0.3,
        "min_ranking_score": 0.5,
        "max_risk_score": 0.7,
        "min_confidence": 0.6,
        "max_results": 10,
        "priority_thresholds": [0.9, 0.7, 0.5],
    }
    hunter = HunterEngine(hunter_config)
    master = MasterEngine(
        news_engine=NewsPipeline(
            NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        ),
        hunter_engine=hunter,
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
    )
    runtime = RuntimeService(
        hunter_engine=hunter,
        master_engine=master,
        history_repository=HistoryRepository(),
    )
    # Rzeczywisty RuntimeService bez blokady — brak zaleznosci blokady.
    assert getattr(runtime, "_cycle_lock", None) is None
    report = runtime.run_cycle({})
    assert isinstance(report, CycleReport)


# ---------------------------------------------------------------------------
# 10. Statyczna kontrola: uzyskanie blokady nastepuje przed scanner.scan(),
#     repository cycle start i innymi efektami cyklu.
# ---------------------------------------------------------------------------

def test_static_control_lock_acquired_before_cycle_effects():
    from application import runtime as runtime_module

    module_src = inspect.getsource(runtime_module)

    # Dekorator @_cycle_lock_guard musi bezposrednio poprzedzac def run_cycle.
    deco_pos = module_src.find("@_cycle_lock_guard")
    run_cycle_def_pos = module_src.find("def run_cycle(self")
    assert deco_pos != -1, "Brak @_cycle_lock_guard w runtime.py"
    assert run_cycle_def_pos != -1, "Brak def run_cycle w runtime.py"
    assert deco_pos < run_cycle_def_pos, (
        "@_cycle_lock_guard musi wystepowac przed def run_cycle"
    )

    # Wrapper guarda: acquire, try, finally-release (zwolnienie takze po wyjatku).
    wrapper_marker = "def wrapper(self, *args, **kwargs)"
    w_start = module_src.find(wrapper_marker)
    assert w_start != -1, "Brak wrappera w _cycle_lock_guard"
    w_chunk = module_src[w_start:w_start + 700]
    assert "lock.acquire()" in w_chunk, "Brak lock.acquire() we wrapperze"
    assert "try:" in w_chunk, "Brak try we wrapperze"
    assert "finally:" in w_chunk, "Brak finally we wrapperze"
    assert "lock.release()" in w_chunk, "Brak lock.release() we wrapperze"

    # Efekty cyklu znajduja sie w ciele run_cycle (dekorowanej metody),
    # a zatem wykonywane sa PO pozyskaniu blokady przez wrapper.
    next_def = module_src.find("\n    def ", run_cycle_def_pos + 10)
    run_cycle_end = next_def if next_def != -1 else len(module_src)
    run_cycle_chunk = module_src[run_cycle_def_pos:run_cycle_end]
    for needle in (
        "self.market_scanner.scan()",
        "self._run_production_cycle(start_time, recorder, cycle_id)",
        "self.history_repository.save_cycle",
        "CycleTraceRecorder()",
    ):
        assert needle in run_cycle_chunk, f"Brak efektu cyklu w run_cycle: {needle}"

    # _run_production_cycle (wywolywany z run_cycle po acquire) uruchamia
    # scanner.scan() i fetch_intraday() oraz zapisuje cykl.
    prod_def_pos = module_src.find("def _run_production_cycle")
    assert prod_def_pos != -1, "Brak _run_production_cycle w runtime.py"
    next_prod_def = module_src.find("\n    def ", prod_def_pos + 10)
    prod_end = next_prod_def if next_prod_def != -1 else len(module_src)
    prod_chunk = module_src[prod_def_pos:prod_end]
    for needle in (
        "candidates = scanner.scan()",
        "intraday_result = provider.fetch_intraday(symbols)",
        "self.history_repository.save_cycle",
    ):
        assert needle in prod_chunk, (
            f"Brak efektu cyklu w _run_production_cycle: {needle}"
        )


# ---------------------------------------------------------------------------
# 11. Zwolnienie nastepuje rowniez po wyjatku (context manager).
# ---------------------------------------------------------------------------

def test_release_happens_after_exception():
    db_path = _temp_lock_path("release_after_exception.sqlite")

    def _raise_inside(lock: CycleLock) -> None:
        with lock:
            raise ValueError("cycle failure")

    with pytest.raises(ValueError):
        _raise_inside(CycleLock(db_path))

    lock = CycleLock(db_path)
    lock.acquire()
    lock.release()


# ---------------------------------------------------------------------------
# 12. Nie powstaja pliki blokady w repozytorium.
# ---------------------------------------------------------------------------

def test_no_lock_files_in_repository():
    repo_root = Path(__file__).resolve().parent.parent
    db_path = repo_root / "data" / "runtime" / "alchemik_runtime.db"
    lock_path = lock_path_for_db(db_path)
    # Sciezka locka zawsze lezy w systemowym katalogu tymczasowym.
    assert str(lock_path).startswith(str(Path(tempfile.gettempdir())))
    assert str(repo_root) not in str(lock_path)


# =============================================================================
# KROK 2/8 — rzeczywisty test dwoch niezaleznych procesow blokady cyklu.
# =============================================================================
# Oba procesy uzywaja prawdziwego RuntimeService i prawdziwego CycleLock na
# prawdziwej bazie SQLite w swiezym katalogu tymczasowym. Jedyna kontrolowana
# granica to hermetyczny skaner bez sieci. Synchronizacja: pliki sygnalowe
# z jawnym timeoutem (bez stalego sleep).

_STEP2_WORKER = r"""
import sys
import time
from pathlib import Path


def _main():
    db_path = Path(sys.argv[1])
    role = sys.argv[2]
    work_dir = Path(sys.argv[3])

    from application.cycle_lock import CycleAlreadyRunningError, CycleLock
    from application.runtime import RuntimeService
    from application.sqlite_history_repository import SQLiteHistoryRepository
    from engines.hunter.engine import HunterEngine
    from engines.master.engine import MasterEngine
    from engines.news.filter import NewsFilterConfig
    from engines.news.pipeline import NewsPipeline
    from engines.ai.decision_engine import DecisionEngine
    from engines.ranking.engine import RankingEngine
    from engines.risk.engine import RiskEngine

    class ControlledScannerBoundary:
        def __init__(self):
            self.network_calls = 0

        def scan(self):
            self.network_calls += 1
            if role == "A":
                (work_dir / "A_SCANNER_REACHED").write_text("1")
                print("LOCK_HELD", flush=True)
                deadline = time.monotonic() + 30.0
                while not (work_dir / "release_a.flag").exists():
                    if time.monotonic() > deadline:
                        raise TimeoutError("A release timeout")
                    time.sleep(0.05)
                raise RuntimeError("SCANNER_GATE_RELEASED")
            (work_dir / "B_SCANNER_REACHED").write_text("1")
            raise RuntimeError("UNEXPECTED_SCANNER")

    hunter_config = {
        "ranking_weight": 0.4,
        "risk_weight": 0.3,
        "confidence_weight": 0.3,
        "min_ranking_score": 0.5,
        "max_risk_score": 0.7,
        "min_confidence": 0.6,
        "max_results": 10,
        "priority_thresholds": [0.9, 0.7, 0.5],
    }
    hunter = HunterEngine(hunter_config)
    master = MasterEngine(
        news_engine=NewsPipeline(
            NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        ),
        hunter_engine=hunter,
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
    )
    boundary = ControlledScannerBoundary()
    repo = SQLiteHistoryRepository(db_path)
    runtime = RuntimeService(
        hunter_engine=hunter,
        master_engine=master,
        history_repository=repo,
        market_scanner=boundary,
        cycle_lock=CycleLock(db_path),
    )
    try:
        runtime.run_cycle()
        print("RUN_CYCLE_RETURNED", flush=True)
    except Exception as exc:
        if role == "B" and isinstance(exc, CycleAlreadyRunningError):
            print("CYCLE_ALREADY_RUNNING", flush=True)
            print("B_CYCLE_COUNT", repo.count(), flush=True)
            print("B_SCANNER_REACHED_EXISTS",
                  (work_dir / "B_SCANNER_REACHED").exists(), flush=True)
            print("B_NETWORK_CALLS", boundary.network_calls, flush=True)
            sys.exit(0)
        print("UNEXPECTED_ERROR", type(exc).__name__, flush=True)
        sys.exit(3)


if __name__ == "__main__":
    _main()
"""


def _wait_for_file(path: Path, timeout: float) -> None:
    """Czekaj na plik sygnalowy z jawnym timeoutem (polling deterministyczny)."""
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(f"Timeout waiting for {path.name}")
        time.sleep(0.05)


def _close_stdio(proc) -> None:
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass


def _terminate_or_kill(proc, timeout: float = 5.0) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


def test_two_real_processes_second_runtime_rejected_before_scanner():
    """Krok 2/8 — rzeczywisty test dwoch niezaleznych procesow.

    Proces A utrzymuje blokade na tymczasowej bazie (bez sieci). Proces B
    dla tej samej bazy zostaje natychmiast odrzucony przez prawdziwy
    RuntimeService.run_cycle() jawnym CycleAlreadyRunningError, zanim
    zostanie osiagniety skaner, siec lub zapis cyklu do SQLite.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="alchemik_step2_lock_"))
    db_path = work_dir / "step2_runtime.db"
    proc_a = None
    proc_b = None
    out_a = ""
    out_b = ""
    try:
        # Identycznosc blokady dla tej samej bazy (kanoniczna sciezka).
        identity = lock_identity_for_db(db_path)
        lock_path = lock_path_for_db(db_path)
        assert lock_path == lock_path_for_db(work_dir / "step2_runtime.db")

        # Proces A: prawdziwy RuntimeService + CycleLock, utrzymuje blokade.
        proc_a = subprocess.Popen(
            [sys.executable, "-c", _STEP2_WORKER, str(db_path), "A", str(work_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        try:
            _wait_for_file(work_dir / "A_SCANNER_REACHED", timeout=30.0)
        except TimeoutError:
            if proc_a.poll() is None:
                _terminate_or_kill(proc_a)
            raise
        assert proc_a.poll() is None, "Proces A zakonczyl sie przed utrzymaniem blokady"

        # A utrzymuje blokade — proba zdobycia z rodzica konczy sie bledem.
        probe = CycleLock(db_path)
        with pytest.raises(CycleAlreadyRunningError):
            probe.acquire()

        # Proces B: ta sama baza, prawdziwy RuntimeService + CycleLock.
        start_b = time.monotonic()
        proc_b = subprocess.Popen(
            [sys.executable, "-c", _STEP2_WORKER, str(db_path), "B", str(work_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        out_b, err_b = proc_b.communicate(timeout=30.0)
        elapsed_b = time.monotonic() - start_b

        assert proc_b.returncode == 0, (
            f"Proces B rc={proc_b.returncode}: {out_b} {err_b}"
        )
        assert "CYCLE_ALREADY_RUNNING" in out_b
        # Brak jakiegokolwiek zapisu domenowego cyklu w procesie B.
        assert "B_CYCLE_COUNT 0" in out_b
        # Skaner procesu B nie zostal osiagniety.
        assert "B_SCANNER_REACHED_EXISTS False" in out_b
        assert "B_NETWORK_CALLS 0" in out_b
        # Odrzucenie bez retry i bez oczekiwania na zwolnienie blokady przez A.
        assert elapsed_b < 15.0, (
            f"Proces B czekal na zwolnienie blokady: {elapsed_b:.2f}s"
        )
    finally:
        # Determinystyczne zwolnienie procesu A po zakonczeniu procesu B.
        if proc_a is not None and proc_a.poll() is None:
            (work_dir / "release_a.flag").write_text("go")
            try:
                out_a, err_a = proc_a.communicate(timeout=30.0)
            except subprocess.TimeoutExpired:
                _terminate_or_kill(proc_a)
                out_a = ""
            finally:
                _close_stdio(proc_a)
        if proc_a is not None and proc_a.poll() is None:
            _terminate_or_kill(proc_a)
        if proc_b is not None and proc_b.poll() is None:
            _terminate_or_kill(proc_b)
        _close_stdio(proc_b) if proc_b is not None else None
        shutil.rmtree(work_dir, ignore_errors=True)

    # Proces A zakonczyl sie poprawnie: utrzymal blokade i zwolnił po sygnale.
    assert proc_a is not None and proc_a.poll() is not None
    assert "LOCK_HELD" in out_a, f"Brak LOCK_HELD w procesie A: {out_a!r}"
    assert "RUN_CYCLE_RETURNED" in out_a, f"Brak poprawnego zakonczenia A: {out_a!r}"

    # PID procesow sa rozne.
    assert proc_a.pid != proc_b.pid, "Procesy A i B maja ten sam PID"

    # Po zakonczeniu A blokade mozna ponownie uzyskac i zwolnic,
    # a pozostajacy plik .lock bez blokady systemowej nie blokuje.
    assert lock_path.exists(), "Plik .lock powinien pozostac po procesach"
    lock1 = CycleLock(db_path)
    lock1.acquire()
    lock1.release()
    lock2 = CycleLock(db_path)
    lock2.acquire()
    lock2.release()

    # Brak markera skanera procesu B — skaner B nigdy nie zostal osiagniety.
    assert not (work_dir / "B_SCANNER_REACHED").exists()
    # Wszystkie procesy potomne zostaly zakonczone.
    assert proc_a.poll() is not None and proc_b.poll() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])