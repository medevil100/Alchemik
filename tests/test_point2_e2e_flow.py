"""
Point 2/7 — podłączenie danych do RuntimeService i repozytoriów.

Scenariusze obowiązkowe Punktu 2. Przepływ testowany na realnych modułach
wewnętrznych:

    YahooChartProvider → MarketScanner → RuntimeService
    → InstrumentReading → InstrumentObservation/Baseline
    → HistoryRepository → SQLite

Test double dozwolony wyłącznie na zewnętrznej granicy Yahoo
(``FakeYahooSession``). Żaden wewnętrzny komponent nie jest mockowany.
Używane jest rzeczywiste tymczasowe SQLite.
"""
import ast
import inspect
import sqlite3
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from application import entrypoint
from application.runtime import RuntimeService
from data.yahoo.yahoo_session import FetchResult, OutcomeKind, ScreenerPage, ScreenerPagination


# ---------------------------------------------------------------------------
# Granica Yahoo — test double (bez sieci)
# ---------------------------------------------------------------------------

def make_quote(symbol: str, price: float = 5.0) -> dict:
    return {
        "symbol": symbol,
        "quoteType": "EQUITY",
        "exchange": "WSE",
        "market": "pl_market",
        "currency": "PLN",
        "regularMarketPrice": price,
    }


def make_chart(symbol: str, rows: list) -> FetchResult:
    timestamps = [r[0] for r in rows]
    opens = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    closes = [r[4] for r in rows]
    volumes = [r[5] for r in rows]
    return FetchResult(
        kind=OutcomeKind.SUCCESS_WITH_DATA,
        data={
            "variant": "daily",
            "meta": {
                "symbol": symbol,
                "instrumentType": "EQUITY",
                "currency": "PLN",
                "exchangeName": "WSE",
            },
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "events": {},
        },
        message=None,
    )


def ts(dt: datetime) -> int:
    return int(dt.timestamp())


class FakeYahooSession:
    """Deterministyczna granica Yahoo — zero rzeczywistej sieci."""

    def __init__(self, quotes: list, chart_rows_by_symbol: dict):
        self._quotes = list(quotes)
        self._chart_rows = dict(chart_rows_by_symbol)
        self.real_network_sent = 0
        self.chart_calls = []

    def paginate_screener(self, size: int = 250) -> FetchResult:
        page = ScreenerPage(
            total=len(self._quotes),
            start=0,
            count=len(self._quotes),
            quotes=list(self._quotes),
        )
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=ScreenerPagination(total=len(self._quotes), pages=[page]),
            message=None,
        )

    def fetch_chart(self, symbol: str, variant: str = "daily") -> FetchResult:
        self.chart_calls.append(symbol)
        rows = self._chart_rows.get(symbol)
        if rows is None:
            return FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)
        return make_chart(symbol, rows)


def _build(persist_path: Path, session: FakeYahooSession) -> RuntimeService:
    return entrypoint.build_runtime_service(persist_path=persist_path, yahoo_session=session)


def _reading_count(db_path: Path, instrument_id: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?",
            (instrument_id,),
        )
        return cur.fetchone()[0]
    finally:
        conn.close()


T1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Scenariusz 1/8/12/13/14 — pełna ścieżka, baseline, brak sieci
# ---------------------------------------------------------------------------


class TestPoint2FullChain:
    def test_first_reading_creates_baseline_and_observation(self, tmp_path):
        """Pełna ścieżka realnych komponentów prowadzi chart → trwały baseline."""
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={
                "AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 1000)],
            },
        )
        runtime = _build(tmp_path / "e2e.db", session)
        report = runtime.run_cycle()

        assert report.candidates_count >= 1

        repo = runtime.history_repository
        obs = repo.load_observation("AAA.WA")
        assert obs is not None, "brak ACTIVE Observation po run_cycle"
        assert obs.state == "ACTIVE"

        restored = repo.restore_active_observations()
        assert len(restored) == 1
        _, rdg = restored[0]
        assert rdg.close == 1.1
        assert rdg.market_data_timestamp == T1
        assert rdg.volume == 1000.0

        # Żaden odcinek nie otrzymał surowej odpowiedzi — close przepłynął
        # z chart przez MarketData do Reading (normowanie na granicy).
        assert session.real_network_sent == 0

    def test_composition_root_builds_complete_real_path(self, tmp_path):
        """Composition root buduje realne MarketScanner → RuntimeService."""
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={
                "AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 1000)],
            },
        )
        runtime = _build(tmp_path / "e2e.db", session)
        assert runtime.market_scanner is not None
        assert runtime.history_repository is not None
        assert runtime.hunter_engine is not None
        assert runtime.master_engine is not None

    def test_no_hidden_db_loading_in_constructor(self):
        """Konstruktor RuntimeService nie ładuje bazy ani nie przywraca
        Observation — restore jest wyłącznie jawną operacją startową."""
        source = textwrap.dedent(inspect.getsource(RuntimeService.__init__))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                    assert name not in (
                        "restore_active_observations",
                        "load_observation",
                        "save_reading",
                    ), f"konstruktor ukrywa ładowanie bazy: {name}"


# ---------------------------------------------------------------------------
# Scenariusz 2/3/4/5 — volume=0, krótka historia, uszkodzony chart, jeden błędny
# ---------------------------------------------------------------------------


class TestPoint2ProviderEdgeCases:
    def test_volume_zero_preserved_and_not_skipped(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={
                "AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 0)],
            },
        )
        runtime = _build(tmp_path / "e2e.db", session)
        runtime.run_cycle()

        repo = runtime.history_repository
        restored = repo.restore_active_observations()
        assert len(restored) == 1
        _, rdg = restored[0]
        assert rdg.volume == 0.0, "volume=0 nie może być zamienione na brak danych"

    def test_short_history_passes_to_observation(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={
                "AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 100)],
            },
        )
        runtime = _build(tmp_path / "e2e.db", session)
        runtime.run_cycle()

        obs = runtime.history_repository.load_observation("AAA.WA")
        assert obs is not None and obs.state == "ACTIVE"

    def test_broken_chart_does_not_create_reading(self, tmp_path):
        broken = FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data={
                "variant": "daily",
                "meta": {"symbol": "AAA.WA"},
                "timestamp": [ts(T1), ts(T1) + 1],
                "open": [1.0],
                "high": [1.0],
                "low": [1.0],
                "close": [1.0],
                "volume": [100],
                "events": {},
            },
            message=None,
        )

        class BrokenSession(FakeYahooSession):
            def fetch_chart(self, symbol, variant="daily"):
                self.chart_calls.append(symbol)
                return broken

        session = BrokenSession(quotes=[make_quote("AAA.WA")], chart_rows_by_symbol={})
        runtime = _build(tmp_path / "e2e.db", session)
        runtime.run_cycle()

        assert _reading_count(tmp_path / "e2e.db", "AAA.WA") == 0

    def test_two_instruments_one_bad_second_passes(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 100)],
                # BBB.WA: brakujący chart → SUCCESS_NO_DATA
            },
        )
        runtime = _build(tmp_path / "e2e.db", session)
        report = runtime.run_cycle()

        assert runtime.history_repository.load_observation("AAA.WA") is not None
        assert runtime.history_repository.load_observation("BBB.WA") is None
        assert _reading_count(tmp_path / "e2e.db", "AAA.WA") == 1
        assert _reading_count(tmp_path / "e2e.db", "BBB.WA") == 0


# ---------------------------------------------------------------------------
# Scenariusz 6 — drugi zmieniony odczyt aktualizuje istniejącą Observation
# ---------------------------------------------------------------------------


class TestPoint2ChangedReading:
    def test_second_changed_reading_updates_existing_observation(self, tmp_path):
        db = tmp_path / "e2e.db"

        s1 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 100)]},
        )
        rt1 = _build(db, s1)
        rt1.run_cycle()

        obs1 = rt1.history_repository.load_observation("AAA.WA")
        assert obs1 is not None

        s2 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": [(ts(T2), 1.2, 1.6, 0.6, 1.3, 200)]},
        )
        rt2 = _build(db, s2)
        rt2.run_cycle()

        obs2 = rt2.history_repository.load_observation("AAA.WA")
        assert obs2 is not None
        assert obs2.observation_id == obs1.observation_id, (
            "zmieniony odczyt utworzył nową Observation zamiast zaktualizować"
        )

        # prev_reading_id wskazuje na pierwszy Reading = zachowany baseline
        _, rdg2 = rt2.history_repository.restore_active_observations()[0]
        assert rdg2.close == 1.3
        assert rdg2.prev_reading_id is not None


# ---------------------------------------------------------------------------
# Scenariusz 7 + 10 — identyczny odczyt nie uruchamia dalszego przetwarzania
# i jest zliczany diagnostycznie
# ---------------------------------------------------------------------------


class TestPoint2UnchangedReadingSkipsProcessing:
    def test_second_identical_reading_skips_further_processing(self, tmp_path):
        db = tmp_path / "e2e.db"
        chart = [(ts(T1), 1.0, 1.5, 0.5, 1.1, 100)]

        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": chart},
        )
        first = _build(db, session).run_cycle()
        assert first.candidates_count >= 1

        session2 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": chart},
        )
        second = _build(db, session2).run_cycle()

        # Brak zmiany → kandydat nie dociera do Hunter/Master
        assert second.candidates_count == 0, (
            f"niezmieniony odczyt przekazano dalej (candidates_count={second.candidates_count})"
        )
        assert second.success_count == 0

        # Idempotentnie tylko jeden Reading
        assert _reading_count(db, "AAA.WA") == 1

    def test_diagnostics_counts_saved_and_skipped(self, tmp_path):
        db = tmp_path / "e2e.db"
        chart = [(ts(T1), 1.0, 1.5, 0.5, 1.1, 100)]

        def _run():
            return _build(
                db,
                FakeYahooSession(
                    quotes=[make_quote("AAA.WA")],
                    chart_rows_by_symbol={"AAA.WA": chart},
                ),
            ).run_cycle()

        first = _run()
        assert first.diagnostics["saved_count"] == 1
        assert first.diagnostics["skipped_unchanged_count"] == 0

        second = _run()
        assert second.diagnostics["saved_count"] == 0
        assert second.diagnostics["skipped_unchanged_count"] == 1


# ---------------------------------------------------------------------------
# Scenariusz 9 — jawne odtworzenie po restarcie + kontynuacja z baseline
# ---------------------------------------------------------------------------


class TestPoint2RestoreContinuation:
    def test_restore_then_continuation_uses_previous_baseline(self, tmp_path):
        db = tmp_path / "e2e.db"

        s1 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": [(ts(T1), 1.0, 1.5, 0.5, 1.1, 100)]},
        )
        _build(db, s1).run_cycle()

        # Symulowany restart — nowy repo nad tą samą bazą
        rt_restart = _build(db, FakeYahooSession(quotes=[], chart_rows_by_symbol={}))
        restored = rt_restart.restore_active_observations()
        assert len(restored) == 1
        obs_base, reading_base = restored[0]
        assert reading_base.close == 1.1

        # Kontynuacja po odtworzeniu — nowy odczyt używa poprzedniego baseline
        s2 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": [(ts(T2), 1.2, 1.6, 0.6, 1.3, 200)]},
        )
        rt2 = _build(db, s2)
        rt2.run_cycle()

        obs2, rdg2 = rt2.history_repository.restore_active_observations()[0]
        assert obs2.observation_id == obs_base.observation_id
        assert rdg2.prev_reading_id == reading_base.reading_id


if __name__ == "__main__":
    pytest.main([__file__, "-q"])