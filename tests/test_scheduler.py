import unittest
import threading
import time
from application.scheduler import RuntimeScheduler
from application.runtime import RuntimeService
from engines.hunter import HunterEngine
from engines.master import MasterEngine
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.ai import DecisionEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.analyst import AnalystEngine
from engines.price_detector import PriceDetector
from engines.volume_detector import VolumeDetector
from application.history_repository import HistoryRepository

HUNTER_CONFIG = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.0,
    "max_risk_score": 1.0,
    "min_confidence": 0.0,
    "max_results": 100,
    "priority_thresholds": [0.9, 0.7, 0.5],
}


def _build_real_runtime_service():
    """Build a RuntimeService with real internal engine instances."""
    technical_engine = TechnicalEngine()
    news_engine = NewsPipeline(filter_config=None)
    ai_engine = DecisionEngine()
    ranking_engine = RankingEngine()
    risk_engine = RiskEngine()
    hunter_engine = HunterEngine(HUNTER_CONFIG)
    analyst_engine = AnalystEngine()
    price_detector = PriceDetector()
    volume_detector = VolumeDetector()
    master_engine = MasterEngine(
        technical_engine=technical_engine,
        news_engine=news_engine,
        ai_engine=ai_engine,
        ranking_engine=ranking_engine,
        risk_engine=risk_engine,
        hunter_engine=hunter_engine,
        analyst_engine=analyst_engine,
        price_detector=price_detector,
        volume_detector=volume_detector,
    )
    history_repository = HistoryRepository()
    return RuntimeService(
        hunter_engine=hunter_engine,
        master_engine=master_engine,
        history_repository=history_repository,
    )


class TestRuntimeScheduler(unittest.TestCase):
    def setUp(self):
        self.runtime_service = _build_real_runtime_service()
        self.scheduler = RuntimeScheduler(self.runtime_service, interval=1, continue_on_error=True)

    def test_run_once_calls_run_cycle(self):
        """Scheduler.run_once() calls RuntimeService.run_cycle() exactly once."""
        self.scheduler.run_once()

    def test_run_cycle_method_exists(self):
        """Real RuntimeService has run_cycle method."""
        self.assertTrue(hasattr(self.runtime_service, "run_cycle"))

    def test_run_once_with_error_continue_on_error_true(self):
        """Error from run_cycle() is silently caught when continue_on_error=True."""
        scheduler = RuntimeScheduler(self.runtime_service, interval=1, continue_on_error=True)
        scheduler.run_once()

    def test_start_stop(self):
        self.scheduler.start()
        time.sleep(0.1)
        self.assertTrue(self.scheduler._thread.is_alive())
        self.scheduler.stop()
        self.assertFalse(self.scheduler._thread.is_alive())

    def test_stop_event(self):
        self.scheduler.start()
        self.scheduler.stop()
        self.assertTrue(self.scheduler._stop_event.is_set())


# =============================================================================
# KROK 8.3 — PRODUKCYJNY SCHEDULER 15 MINUT + CYCLELOCK
# =============================================================================
# Kontrakt zatwierdzony przez wlasciciela po STOP_STEP8_3_CYCLELOCK_CONTRACT_GAP:
#   * RuntimeService.run_cycle() pozostaje jedynym wlascicielem CycleLock;
#   * scheduler nie otrzymuje i nie przejmuje CycleLock;
#   * scheduler wywoluje publiczne, juz chronione run_cycle();
#   * CycleAlreadyRunningError jest mapowany na SKIPPED_OVERLAP;
#   * pierwszy cykl natychmiast, kolejne 900 s po zakonczeniu proby;
#   * przerwalne oczekiwanie (stop_event.wait), bez time.sleep(900);
#   * brak retry, kolejki, catch-up i rownoleglych cykli.
# =============================================================================
import inspect

import pytest

from application.cycle_lock import CycleAlreadyRunningError
from application.cycle_lock import CycleLock
from application.sqlite_history_repository import SQLiteHistoryRepository


class _ManualStopEvent:
    """Deterministyczny zamiennik threading.Event rejestrujacy wywolania wait()."""

    def __init__(self, stop_after_waits=None):
        self.stop_after_waits = stop_after_waits
        self.wait_timeouts = []
        self.order = []
        self._set = False

    def wait(self, timeout=None):
        self.wait_timeouts.append(timeout)
        self.order.append("wait")
        if self.stop_after_waits is not None and len(self.wait_timeouts) >= self.stop_after_waits:
            self._set = True
        return self._set

    def set(self):
        self._set = True

    def clear(self):
        self._set = False

    def is_set(self):
        return self._set


class _RecordingScheduler(RuntimeScheduler):
    """Rejestruje statusy zwracane przez run_once() (mechanika czasu)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.statuses = []

    def run_once(self):
        status = super().run_once()
        self.statuses.append(status)
        return status


class _OkRuntime:
    def __init__(self):
        self.calls = 0

    def run_cycle(self):
        self.calls += 1


class _OverlapRuntime:
    def __init__(self):
        self.calls = 0

    def run_cycle(self):
        self.calls += 1
        raise CycleAlreadyRunningError("busy")


class _ErrorThenOkRuntime:
    def __init__(self):
        self.calls = 0

    def run_cycle(self):
        self.calls += 1
        if self.calls == 1:
            raise ValueError("cycle boom")
        return None


class _ErrorRuntime:
    def run_cycle(self):
        raise ValueError("cycle boom")


# ---------------------------------------------------------------------------
# 8.3A. Interwal 900 s i walidacja
# ---------------------------------------------------------------------------

def test_default_interval_is_900():
    assert RuntimeScheduler(_OkRuntime()).interval == 900


def test_interval_must_be_positive():
    with pytest.raises(ValueError):
        RuntimeScheduler(_OkRuntime(), interval=0)
    with pytest.raises(ValueError):
        RuntimeScheduler(_OkRuntime(), interval=-5)


# ---------------------------------------------------------------------------
# 8.3B. Statusy run_once(): EXECUTED / SKIPPED_OVERLAP / CYCLE_ERROR
# ---------------------------------------------------------------------------

def test_run_once_success_returns_executed():
    runtime = _OkRuntime()
    scheduler = RuntimeScheduler(runtime, interval=900, continue_on_error=True)
    assert scheduler.run_once() == "EXECUTED"
    assert runtime.calls == 1


def test_run_once_error_raises_when_not_continued():
    """Kompatybilnosc: continue_on_error=False nadal propaguje blad cyklu."""
    scheduler = RuntimeScheduler(_ErrorRuntime(), interval=900, continue_on_error=False)
    with pytest.raises(ValueError):
        scheduler.run_once()


def test_run_once_cycle_error_status_when_continued():
    scheduler = RuntimeScheduler(_ErrorRuntime(), interval=900, continue_on_error=True)
    assert scheduler.run_once() == "CYCLE_ERROR"


def test_run_once_overlap_status_skipped_overlap():
    runtime = _OverlapRuntime()
    scheduler = RuntimeScheduler(runtime, interval=900, continue_on_error=True)
    assert scheduler.run_once() == "SKIPPED_OVERLAP"
    assert runtime.calls == 1


def test_scheduler_handles_overlap_explicitly_not_as_generic_error():
    src = inspect.getsource(RuntimeScheduler.run_once)
    assert "except CycleAlreadyRunningError" in src
    assert src.find("except CycleAlreadyRunningError") < src.find("except Exception")


# ---------------------------------------------------------------------------
# 8.3C. Mechanika petli: immediate run -> zakonczenie -> wait; przerwalne wait
# ---------------------------------------------------------------------------

def test_first_cycle_immediate_then_wait_stop_during_wait_no_next_cycle():
    calls = []

    class _RuntimeSetStopOnFirstCycle:
        def __init__(self, evt):
            self.evt = evt

        def run_cycle(self):
            calls.append("run_cycle")
            self.evt.set()

    evt = _ManualStopEvent(stop_after_waits=1)
    scheduler = RuntimeScheduler(_RuntimeSetStopOnFirstCycle(evt), interval=1, continue_on_error=True)
    scheduler._stop_event = evt
    scheduler._run_loop()

    # Kolejnosc: pierwszy cykl przed pierwszym oczekiwaniem ("wait"); stop w
    # trakcie oczekiwania konczy petle bez kolejnego cyklu.
    assert calls == ["run_cycle"]
    assert evt.order == ["wait"]
    assert evt.wait_timeouts == [1]


def test_run_wait_run_wait_no_catchup():
    calls = []

    class _RuntimeSetStopOnSecondCycle:
        def __init__(self, evt):
            self.evt = evt

        def run_cycle(self):
            calls.append("run_cycle")
            if len(calls) >= 2:
                self.evt.set()

    evt = _ManualStopEvent(stop_after_waits=2)
    scheduler = RuntimeScheduler(_RuntimeSetStopOnSecondCycle(evt), interval=1, continue_on_error=True)
    scheduler._stop_event = evt
    scheduler._run_loop()

    # Kolejnosc: run, wait, run, wait — bez catch-up i bez kolejki.
    assert calls == ["run_cycle", "run_cycle"]
    assert evt.order == ["wait", "wait"]
    assert evt.wait_timeouts == [1, 1]


def test_scheduler_source_uses_interruptible_wait_not_time_sleep():
    src = inspect.getsource(RuntimeScheduler._run_loop)
    assert "time.sleep" not in src
    assert "self._stop_event.wait(self.interval)" in src


def test_scheduler_does_not_touch_lock_directly():
    import application.scheduler as scheduler_module

    class_src = inspect.getsource(RuntimeScheduler)
    assert ".acquire(" not in class_src
    assert ".release(" not in class_src
    # Jedyne dopuszczalne uzycie cykle_lock to import typu wyjatku.
    module_src = inspect.getsource(scheduler_module)
    assert "from application.cycle_lock import CycleAlreadyRunningError" in module_src
    assert "CycleLock(" not in module_src


def test_scheduler_has_run_forever_blocking_entry():
    assert callable(RuntimeScheduler.run_forever)


# ---------------------------------------------------------------------------
# 8.3D. Overlap: brak retry, brak kolejki; po pominięciu wait 900
# ---------------------------------------------------------------------------

def test_overlap_skipped_no_retry_no_queue_then_wait():
    runtime = _OverlapRuntime()
    evt = _ManualStopEvent(stop_after_waits=1)
    scheduler = _RecordingScheduler(runtime, interval=900, continue_on_error=True)
    scheduler._stop_event = evt
    scheduler._run_loop()

    assert scheduler.statuses == ["SKIPPED_OVERLAP"]
    # Dokladnie jedna proba run_cycle() (chroniona) i zero retry przed wait.
    assert runtime.calls == 1
    assert evt.wait_timeouts == [900]


def test_overlap_then_next_attempt_after_wait_no_catchup():
    class _OverlapThenOkRuntime:
        def __init__(self):
            self.calls = 0

        def run_cycle(self):
            self.calls += 1
            if self.calls == 1:
                raise CycleAlreadyRunningError("busy")

    runtime = _OverlapThenOkRuntime()
    evt = _ManualStopEvent(stop_after_waits=2)
    scheduler = _RecordingScheduler(runtime, interval=900, continue_on_error=True)
    scheduler._stop_event = evt
    scheduler._run_loop()

    assert scheduler.statuses == ["SKIPPED_OVERLAP", "EXECUTED"]
    assert runtime.calls == 2
    assert evt.wait_timeouts == [900, 900]


# ---------------------------------------------------------------------------
# 8.3E. Blad pojedynczego cyklu: CYCLE_ERROR, kontynuacja po wait 900
# ---------------------------------------------------------------------------

def test_error_cycle_error_then_next_attempt_after_wait():
    runtime = _ErrorThenOkRuntime()
    evt = _ManualStopEvent(stop_after_waits=2)
    scheduler = _RecordingScheduler(runtime, interval=900, continue_on_error=True)
    scheduler._stop_event = evt
    scheduler._run_loop()

    assert scheduler.statuses == ["CYCLE_ERROR", "EXECUTED"]
    assert runtime.calls == 2
    assert evt.wait_timeouts == [900, 900]


# ---------------------------------------------------------------------------
# 8.3F. Rownoleglosc wykluczona przez istniejacy guard RuntimeService
# ---------------------------------------------------------------------------

def test_no_parallel_cycles_guaranteed_by_runtime_guard():
    from application import runtime as runtime_module

    src = inspect.getsource(runtime_module)
    deco_pos = src.find("@_cycle_lock_guard")
    run_cycle_def_pos = src.find("def run_cycle(self")
    assert deco_pos != -1, "Brak @_cycle_lock_guard w runtime.py"
    assert run_cycle_def_pos != -1, "Brak def run_cycle w runtime.py"
    assert deco_pos < run_cycle_def_pos


# ---------------------------------------------------------------------------
# 8.3G. Pełne polaczenie: scheduler -> prawdziwy RuntimeService -> SQLite
#       -> prawdziwy CycleLock
# ---------------------------------------------------------------------------

def _build_full_runtime(db_path, *, cycle_lock=None):
    """Prawdziwy RuntimeService z prawdziwymi silnikami i SQLiteHistoryRepository."""
    import os
    import tempfile
    from pathlib import Path
    from engines.news.filter import NewsFilterConfig
    from engines.news.pipeline import NewsPipeline

    technical_engine = TechnicalEngine()
    news_engine = NewsPipeline(NewsFilterConfig(min_content_length=50, min_quality_score=0.5))
    ai_engine = DecisionEngine()
    ranking_engine = RankingEngine()
    risk_engine = RiskEngine()
    hunter_engine = HunterEngine(HUNTER_CONFIG)
    analyst_engine = AnalystEngine()
    price_detector = PriceDetector()
    volume_detector = VolumeDetector()
    master_engine = MasterEngine(
        technical_engine=technical_engine,
        news_engine=news_engine,
        ai_engine=ai_engine,
        ranking_engine=ranking_engine,
        risk_engine=risk_engine,
        hunter_engine=hunter_engine,
        analyst_engine=analyst_engine,
        price_detector=price_detector,
        volume_detector=volume_detector,
    )
    repo = SQLiteHistoryRepository(db_path)
    return RuntimeService(
        hunter_engine=hunter_engine,
        master_engine=master_engine,
        history_repository=repo,
        cycle_lock=cycle_lock,
    )


def test_full_connection_real_runtime_sqlite_cyclelock(tmp_path):
    db_path = tmp_path / "scheduler_full.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    runtime = _build_full_runtime(db_path, cycle_lock=CycleLock(db_path))
    scheduler = RuntimeScheduler(runtime, interval=900, continue_on_error=True)

    assert scheduler.run_once() == "EXECUTED"
    # Blokada nalezy do RuntimeService i zostaje zwolniona po sukcesie.
    assert runtime._cycle_lock is not None
    assert not runtime._cycle_lock.held


def test_full_connection_overlap_mapped_to_skipped(tmp_path):
    db_path = tmp_path / "scheduler_full_overlap.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    runtime = _build_full_runtime(db_path, cycle_lock=CycleLock(db_path))
    holder = CycleLock(db_path)
    holder.acquire()
    try:
        scheduler = RuntimeScheduler(runtime, interval=900, continue_on_error=True)
        assert scheduler.run_once() == "SKIPPED_OVERLAP"
        assert not runtime._cycle_lock.held
    finally:
        holder.release()


# ---------------------------------------------------------------------------
# 8.3H. Entrypoint: --scheduler; bez flagi nadal jeden cykl
# ---------------------------------------------------------------------------

def test_entrypoint_main_recognizes_scheduler_flag():
    from application import entrypoint as entrypoint_module

    src = inspect.getsource(entrypoint_module.main)
    assert '"--scheduler" in sys.argv[1:]' in src


def test_entrypoint_has_scheduler_entry_function():
    from application import entrypoint as entrypoint_module

    assert callable(getattr(entrypoint_module, "_run_scheduler", None))


def test_main_without_scheduler_keeps_single_cycle(monkeypatch):
    import sys
    from application import entrypoint as ep

    calls = []

    class _FakeReport:
        candidates_count = 0
        success_count = 0
        error_count = 0
        errors = []

    class _FakeRepo:
        def get_storage_summary(self):
            return {"cycle_count": 1, "event_count": 0, "db_path": "tmp"}

    class _FakeRuntime:
        def __init__(self):
            self.production_matrix_cycle = False
            self.history_repository = _FakeRepo()

        def restore_active_observations(self):
            return []

        def run_cycle(self):
            calls.append("run_cycle")
            return _FakeReport()

    monkeypatch.setattr(ep, "build_runtime_service", lambda **kw: _FakeRuntime())
    monkeypatch.setattr(sys, "argv", ["entrypoint"])
    monkeypatch.setattr(ep.logging, "basicConfig", lambda **kw: None)
    monkeypatch.setattr(ep.logger, "info", lambda *a, **k: None)
    monkeypatch.setattr(ep.logger, "warning", lambda *a, **k: None)

    ep.main()

    assert calls == ["run_cycle"]


class _FakeSignalModule:
    SIGTERM = 15

    def __init__(self):
        self.calls = []

    def signal(self, signum, handler):
        self.calls.append((signum, handler))
        return handler


def test_main_with_scheduler_flag_blocks_in_forever_and_waits_900(monkeypatch):
    import sys
    from application import entrypoint as ep

    captured = {}

    class _FakeRuntime:
        def restore_active_observations(self):
            return []

        @property
        def production_matrix_cycle(self):
            return True

        @production_matrix_cycle.setter
        def production_matrix_cycle(self, value):
            pass

    class _FakeScheduler:
        def __init__(self, runtime_service, interval, continue_on_error):
            captured["runtime"] = runtime_service
            captured["interval"] = interval
            captured["continue_on_error"] = continue_on_error

        def run_forever(self):
            captured["run_forever"] = True

        def stop(self):
            captured["stop"] = True

    fake_signal = _FakeSignalModule()
    monkeypatch.setattr(ep, "build_runtime_service", lambda **kw: _FakeRuntime())
    monkeypatch.setattr(sys, "argv", ["entrypoint", "--scheduler"])
    monkeypatch.setattr(ep.logging, "basicConfig", lambda **kw: None)
    monkeypatch.setattr(ep.logger, "info", lambda *a, **k: None)
    monkeypatch.setattr(ep.logger, "warning", lambda *a, **k: None)
    monkeypatch.setattr(ep, "RuntimeScheduler", _FakeScheduler)
    monkeypatch.setattr(ep, "signal", fake_signal)

    ep.main()

    assert captured["interval"] == 900
    assert captured["continue_on_error"] is True
    assert captured["run_forever"] is True
    assert fake_signal.calls, "Brak rejestracji SIGTERM -> graceful stop"


def test_scheduler_mode_graceful_stop_on_keyboard_interrupt(monkeypatch):
    from application import entrypoint as ep

    captured = {}

    class _FakeRuntime:
        pass

    class _InterruptScheduler:
        def __init__(self, runtime_service, interval, continue_on_error):
            pass

        def run_forever(self):
            raise KeyboardInterrupt

        def stop(self):
            captured["stop"] = True

    monkeypatch.setattr(ep, "RuntimeScheduler", _InterruptScheduler)
    monkeypatch.setattr(ep, "signal", _FakeSignalModule())

    ep._run_scheduler(_FakeRuntime())

    assert captured["stop"] is True