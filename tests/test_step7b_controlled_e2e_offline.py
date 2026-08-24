"""
Step 7B/8 — full-system controlled E2E offline (RED).

Weryfikuje kompletny kontrakt trybu CONTROLLED_VALIDATION_ONLY działający
w całości offline, z prawdziwymi komponentami wewnętrznymi ALCHEMIKA
(RuntimeService, SQLiteHistoryRepository na tmp_path, Hunter/Master/Technical/
Ranking/Risk/Analyst/AlertBuilder/AlertDispatcher) i wyłącznie delegującymi
doubles na granicach zewnętrznych (Yahoo, Tavily, OpenAI, Telegram).

Testy NIE podmieniają mockami komponentów wewnętrznych.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from application.controlled_validation import (
    BudgetExceededError,
    ControlledYahooSession,
    GuardedTelegramChannel,
    TelegramBudgetGuard,
    TELEGRAM_CONTROLLED_PREFIX,
    select_symbol,
)
from application.cycle_trace import (
    EXECUTED,
    BLOCKED_BY_BUDGET,
    NATURAL_PIPELINE_STOP,
)

T0 = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers: budowa prawdziwej izolowanej bazy (tmp SQLite)
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.isoformat()


def insert_active_reading(conn: sqlite3.Connection, *, instrument_id: str,
                          market_ts: datetime, revision: int = 1,
                          volume: float = 1000.0, close: float = 5.0,
                          obs_id: str | None = None):
    obs_id = obs_id or f"obs_{instrument_id}"
    conn.execute(
        "INSERT INTO instrument_observations "
        "(observation_id, instrument_id, state, created_at) VALUES (?,?,?,?)",
        (obs_id, instrument_id, "ACTIVE", _iso(T0)),
    )
    conn.execute(
        "INSERT INTO instrument_readings "
        "(reading_id, observation_id, instrument_id, market_data_timestamp, "
        " scan_timestamp, open, high, low, close, volume, source, "
        " prev_reading_id, data_completeness, revision_number, supersedes_reading_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            f"rdg_{instrument_id}_{revision}",
            obs_id,
            instrument_id,
            _iso(market_ts),
            _iso(T0),
            close * 0.99, close * 1.01, close * 0.98, close,
            volume, "YahooFinance", None, "COMPLETE", revision, None,
        ),
    )


@pytest.fixture
def isolated_db(tmp_path: Path) -> Path:
    """Prawdziwa izolowana baza z ACTIVE Observationami i Readingami."""
    db_path = tmp_path / "isolated" / "alchemik_runtime.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE instrument_observations (
                observation_id TEXT PRIMARY KEY,
                instrument_id TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                terminated_at TEXT,
                termination_reason TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_observation
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
            CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_identity
                ON instrument_readings(instrument_id, market_data_timestamp, revision_number);
            """
        )
        # AAA.WA: najnowszy efektywny Reading (t1, rev2) ma niski wolumen,
        # ale historyczny Reading (t0, rev1) ma wysoki wolumen — selektor musi
        # wybrać według wolumenu najnowszego efektywnego Readingu, nie historii.
        insert_active_reading(conn, instrument_id="AAA.WA", market_ts=T0, volume=9000.0, close=9.0)
        # rewizja 2 tego samego timestampu = efektywna (wolumen 100)
        conn.execute(
            "INSERT INTO instrument_readings "
            "(reading_id, observation_id, instrument_id, market_data_timestamp, "
            " scan_timestamp, open, high, low, close, volume, source, "
            " prev_reading_id, data_completeness, revision_number, supersedes_reading_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "rdg_AAA_rev2", "obs_AAA.WA", "AAA.WA", _iso(T0), _iso(T0),
                8.5, 9.2, 8.4, 9.0, 100.0, "YahooFinance",
                "rdg_AAA.WA_1", "COMPLETE", 2, "rdg_AAA.WA_1",
            ),
        )
        # BBB.WA: najnowszy timestamp (t1) wolumen 500 — wyższy niż AAA rev2 (100),
        # więc BBB.WA wygrywa przy sortowaniu volume DESC.
        insert_active_reading(conn, instrument_id="BBB.WA",
                              market_ts=T0 + timedelta(days=1), volume=500.0, close=4.0)
        # CCC.WA: ACTIVE ale brak w discovery — nie może być wybrany.
        insert_active_reading(conn, instrument_id="CCC.WA",
                              market_ts=T0 + timedelta(days=2), volume=9999.0, close=3.0)
        # DDD.WA: tylko terminalna Observation — odrzucona.
        conn.execute(
            "INSERT INTO instrument_observations "
            "(observation_id, instrument_id, state, created_at) VALUES (?,?,?,?)",
            ("obs_DDD", "DDD.WA", "TERMINATED_DOMAIN", _iso(T0)),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Selektor
# ---------------------------------------------------------------------------

class TestSymbolSelection:
    def test_picks_effective_latest_reading_not_historical_volume(
        self, isolated_db: Path
    ):
        """Historyczny wysoki wolumen nie wygrywa; liczy się najnowszy
        efektywny Reading (najnowszy timestamp, najwyższa rewizja)."""
        discovery = ["AAA.WA", "BBB.WA"]
        selected = select_symbol(isolated_db, discovery)
        assert selected is not None
        symbol, snapshot = selected
        assert symbol == "BBB.WA"  # BBB rev1 (t1) wolumen 500 > AAA rev2 (t0) wolumen 100

    def test_picks_highest_volume_then_symbol_asc(self, isolated_db: Path):
        selected = select_symbol(isolated_db, ["AAA.WA", "BBB.WA"])
        assert selected is not None
        assert selected[0] == "BBB.WA"

    def test_instrument_without_active_observation_not_selected(
        self, isolated_db: Path
    ):
        selected = select_symbol(isolated_db, ["CCC.WA", "DDD.WA"])
        # CCC ma ACTIVE (wygrywa wolumenem), ale DDD ma tylko terminalną
        # Observation — nie może zostać wybrany, gdy discovery zawiera wyłącznie DDD.
        only_ddd = select_symbol(isolated_db, ["DDD.WA"])
        assert only_ddd is None
        assert selected is not None
        assert selected[0] == "CCC.WA"

    def test_no_manual_ticker_parameter(self):
        import inspect
        from application.controlled_validation import select_symbol as fn
        params = inspect.signature(fn).parameters
        assert "ticker" not in params and "symbol" not in params


# ---------------------------------------------------------------------------
# Overlay
# ---------------------------------------------------------------------------

class TestOverlay:
    def _raw_intraday(self) -> dict:
        # surowe dane Yale zgodne z formatem YahooSession.fetch_chart(intraday)
        return {
            "variant": "intraday",
            "meta": {"symbol": "BBB.WA", "instrumentType": "EQUITY",
                     "currency": "PLN", "exchangeName": "WSE"},
            "timestamp": [1, 2, 3],
            "open": [4.0, 4.1, 4.2],
            "high": [4.1, 4.2, 4.3],
            "low": [3.9, 4.0, 4.05],
            "close": [4.0, 4.1, 4.2],
            "volume": [100, 200, 300],
            "events": {},
        }

    def test_close_plus_4_pct_high_minimal(self):
        raw = self._raw_intraday()
        effective_previous_close = 4.0  # close_prev z efektywnego Readingu
        overlay = ControlledYahooSession.overlay_intraday(
            raw, effective_previous_close=effective_previous_close
        )
        controlled_close = 4.0 * 1.04
        assert overlay["close"][-1] == pytest.approx(controlled_close)
        assert overlay["high"][-1] == pytest.approx(max(4.3, controlled_close))
        # open/low/volume/timestamp bez zmian
        assert overlay["open"] == raw["open"]
        assert overlay["low"] == raw["low"]
        assert overlay["volume"] == raw["volume"]
        assert overlay["timestamp"] == raw["timestamp"]
        # OHLC po overlayu: high >= open/low/close; low <= open/high/close
        o, h, l, c = (overlay[k][-1] for k in ("open", "high", "low", "close"))
        assert h >= o and h >= l and h >= c
        assert l <= o and l <= h and l <= c

    def test_overlay_is_recorded_in_metadata(self):
        raw = self._raw_intraday()
        overlay = ControlledYahooSession.overlay_intraday(raw, effective_previous_close=4.0)
        meta = overlay["meta"]
        assert meta["CONTROLLED_VALIDATION_ONLY"] is True
        assert meta["overlay"] == {
            "symbol": "BBB.WA",
            "timestamp": raw["timestamp"][-1],
            "close_before": pytest.approx(4.2),
            "close_after": pytest.approx(4.0 * 1.04),
            "high_before": pytest.approx(4.3),
            "high_after": pytest.approx(max(4.3, 4.0 * 1.04)),
            "open": pytest.approx(4.2),
            "low": pytest.approx(4.05),
            "volume": pytest.approx(300),
        }


class TestGuardedTelegramChannelLabels:
    """Pełna etykieta CONTROLLED_VALIDATION_ONLY na granicy Telegram."""

    @staticmethod
    def _send(message_text):
        sent = []

        class _RecordingTelegramBoundary:
            """Recording double wyłącznie zewnętrznej granicy Telegrama."""

            def send(self, alert_message):
                sent.append(alert_message)
                return "sent"

        guard = TelegramBudgetGuard()
        channel = GuardedTelegramChannel(_RecordingTelegramBoundary(), guard)
        message = SimpleNamespace(formatted_message=message_text)
        channel.send(message)
        return sent[0].formatted_message, len(sent)

    def test_emoji_message_gets_both_labels(self):
        text, sends = self._send("🚨 ALCHEMIK ALERT\n\nTicker: AAA.WA")
        assert text.startswith(TELEGRAM_CONTROLLED_PREFIX)
        assert text.count("ALCHEMIK — CONTROLLED_VALIDATION_ONLY") == 1
        assert text.count("TO NIE JEST SYGNAŁ INWESTYCYJNY.") == 1
        assert sends == 1

    def test_plain_alchemik_message_gets_both_labels(self):
        text, sends = self._send("ALCHEMIK ALERT\n\nTicker: AAA.WA")
        assert text.startswith(TELEGRAM_CONTROLLED_PREFIX)
        assert text.count("ALCHEMIK — CONTROLLED_VALIDATION_ONLY") == 1
        assert text.count("TO NIE JEST SYGNAŁ INWESTYCYJNY.") == 1
        assert sends == 1

    def test_full_prefix_not_duplicated(self):
        body = "Treść właściwa kontrolowanego alertu."
        text, sends = self._send(TELEGRAM_CONTROLLED_PREFIX + body)
        assert text.startswith(TELEGRAM_CONTROLLED_PREFIX)
        assert text.count("ALCHEMIK — CONTROLLED_VALIDATION_ONLY") == 1
        assert text.count("TO NIE JEST SYGNAŁ INWESTYCYJNY.") == 1
        assert text == TELEGRAM_CONTROLLED_PREFIX + body
        assert sends == 1


class TestBudgetGuards:
    def test_second_tavily_call_blocked_before_delegation(self):
        from application.controlled_validation import TavilyBudgetGuard
        calls = []
        guard = TavilyBudgetGuard()
        guard.guard("ev1", lambda event: calls.append(event) or "ok")
        with pytest.raises(BudgetExceededError):
            guard.guard("ev2", lambda event: calls.append(event) or "ok")
        assert len(calls) == 1

    def test_second_openai_call_blocked_before_delegation(self):
        from application.controlled_validation import OpenAIBudgetGuard
        calls = []
        guard = OpenAIBudgetGuard()
        guard.guard({"p": 1}, lambda payload: calls.append(payload) or "ok")
        with pytest.raises(BudgetExceededError):
            guard.guard({"p": 2}, lambda payload: calls.append(payload) or "ok")
        assert len(calls) == 1

    def test_second_telegram_call_blocked_before_delegation(self):
        from application.controlled_validation import TelegramBudgetGuard
        calls = []
        guard = TelegramBudgetGuard()
        guard.guard("m1", lambda message: calls.append(message) or "ok")
        with pytest.raises(BudgetExceededError):
            guard.guard("m2", lambda message: calls.append(message) or "ok")
        assert len(calls) == 1


class TestControlledTrace:
    def test_controlled_stage_statuses_exist_in_cycle_trace(self):
        # Dozwolone statusy kontrolne istnieją w cycle_trace (addytywnie).
        from application import cycle_trace as ct
        assert EXECUTED in ct.DIAGNOSTIC_STATUSES  # po implementacji

    def test_stage_list_contains_controlled_stages(self):
        from application.controlled_validation import CONTROLLED_STAGE_ORDER
        required = {
            "preflight", "discovery", "symbol_selection", "daily", "intraday",
            "controlled_overlay", "chart_validation", "reading_persistence",
            "baseline_comparison", "hunter", "technical", "master",
            "market_event", "tavily", "openai", "ai_result", "ranking",
            "risk", "analyst", "final_analysis", "alert_builder",
            "alert_dispatcher", "telegram", "cycle_persistence",
            "final_database_check",
        }
        assert required <= set(CONTROLLED_STAGE_ORDER)


# ---------------------------------------------------------------------------
# Krok 7B — pełnosystemowy dowód wykonaniowy jednego RuntimeService.run_cycle()
# ---------------------------------------------------------------------------

# Recording Yahoo boundary — deterministyczny double na granicy Yahoo.
# Zwraca dokładnie: jedno discovery (1 symbol), jedno daily, jedno intraday.
class RecordingYahooBoundary:
    """
    Recording/delegating double wyłącznie granicy Yahoo. Nie zastępuje
    żadnego komponentu wewnętrznego ALCHEMIKA. Zwraca realny-formatowo
    poprawne payloady YahooSession i zlicza wywołania, aby udowodnić
    wykonaniowo brak drugiego discovery wewnątrz RuntimeService.
    """

    SYMBOL = "AAA.WA"

    def __init__(self, intraday_timestamp=None, intraday_close=4.2):
        from data.yahoo.yahoo_session import (
            FetchResult,
            OutcomeKind,
            ScreenerPage,
            ScreenerPagination,
        )
        self.FetchResult = FetchResult
        self.OutcomeKind = OutcomeKind
        self.ScreenerPage = ScreenerPage
        self.ScreenerPagination = ScreenerPagination
        self._intraday_ts = intraday_timestamp
        self._intraday_close = intraday_close
        self.discovery_calls = 0
        self.daily_calls = 0
        self.intraday_calls = 0

    def paginate_screener(self, size: int = 250):
        self.discovery_calls += 1
        page = self.ScreenerPage(
            total=1,
            start=0,
            count=1,
            quotes=[{
                "symbol": self.SYMBOL,
                "quoteType": "EQUITY",
                "currency": "PLN",
                "exchange": "WSE",
            }],
        )
        return self.FetchResult(
            kind=self.OutcomeKind.SUCCESS_WITH_DATA,
            data=self.ScreenerPagination(total=1, pages=[page]),
            message=None,
        )

    def fetch_chart(self, symbol: str, variant: str = "daily"):
        if variant == "daily":
            self.daily_calls += 1
            return self.FetchResult(
                kind=self.OutcomeKind.SUCCESS_WITH_DATA,
                data={
                    "variant": "daily",
                    "http_status": 200,
                    "captured_at": T0.isoformat(),
                    "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                             "currency": "PLN", "exchangeName": "WSE"},
                    "timestamp": [1, 2, 3],
                    "open": [4.0, 4.1, 4.2],
                    "high": [4.1, 4.2, 4.3],
                    "low": [3.9, 4.0, 4.05],
                    "close": [4.0, 4.1, 4.2],
                    "volume": [100, 200, 300],
                    "events": {},
                },
                message=None,
            )
        if variant == "intraday":
            self.intraday_calls += 1
            base_ts = int(T0.timestamp())
            ts = self._intraday_ts if self._intraday_ts is not None else base_ts + 3600
            close = self._intraday_close
            # 7F: anchor overlayu wymaga poprzedniej CLOSED 1h w payloadzie —
            # zwracamy CLOSED (T0) przed OPEN (T0+1h), aby kontrakt testu
            # jednoznacznie odzwierciedlał nową regułę.
            closed_ts = base_ts
            open_ts = ts
            return self.FetchResult(
                kind=self.OutcomeKind.SUCCESS_WITH_DATA,
                data={
                    "variant": "intraday",
                    "http_status": 200,
                    "captured_at": T0.isoformat(),
                    "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                             "currency": "PLN", "exchangeName": "WSE"},
                    "timestamp": [closed_ts, open_ts],
                    "open": [4.0, 4.2],
                    "high": [4.1, 4.3],
                    "low": [3.9, 4.05],
                    "close": [4.0, close],
                    "volume": [200, 300],
                    "events": {},
                },
                message=None,
            )
        raise AssertionError(f"nieznany variant {variant} — poza granicą kontraktu")


@pytest.fixture
def controlled_full_db(tmp_path: Path) -> Path:
    """
    Prawdziwa baza SUBSEQUENT_CYCLE: pełny schemat repository, jeden
    wcześniejszy snapshot, jeden ACTIVE instrument/Observation, jeden
    baseline Reading (revision 1).
    """
    from application.sqlite_history_repository import SQLiteHistoryRepository
    from data.models.instrument_reading import InstrumentReading
    from data.models.instrument_observation import InstrumentObservation

    db_path = tmp_path / "controlled_full" / "alchemik_runtime.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SQLiteHistoryRepository(db_path=db_path)

    # 1. Wcześniejszy snapshot (konieczny dla SUBSEQUENT_CYCLE).
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO universe_snapshots (snapshot_id, sequence, created_at, "
            "total_records, unique_symbols) VALUES (?,?,?,?,?)",
            ("snap_prev", 1, _iso(T0), 1, 1),
        )
        conn.execute(
            "INSERT INTO universe_snapshot_members (snapshot_id, symbol, present, "
            "status, first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?)",
            ("snap_prev", RecordingYahooBoundary.SYMBOL, 1, "ACTIVE", _iso(T0), _iso(T0)),
        )
        conn.commit()
    finally:
        conn.close()

    # 2. ACTIVE Observation + baseline Reading przez prawdziwy repository.
    obs = InstrumentObservation(
        observation_id="obs_aaa",
        instrument_id=RecordingYahooBoundary.SYMBOL,
        timeframe="1h",
    )
    reading = InstrumentReading(
        reading_id="rdg_baseline",
        observation_id=obs.observation_id,
        instrument_id=RecordingYahooBoundary.SYMBOL,
        market_data_timestamp=T0 - timedelta(days=1),
        scan_timestamp=T0,
        open=4.0,
        high=4.1,
        low=3.9,
        close=4.0,
        volume=500,
        data_completeness="COMPLETE",
        timeframe="1h",
        candle_state="CLOSED",
    )
    result = repo.save_reading(obs, reading)
    assert result == "ACCEPTED"
    repo.restore_active_observations()
    return db_path


class TestControlledFullPipelineExecution:
    def test_executes_exactly_one_real_run_cycle(
        self, tmp_path: Path, controlled_full_db: Path
    ):
        """Pełnosystemowy dowód wykonaniowy na prawdziwym RuntimeService.

        Uruchamia prawdziwy ControlledValidationController z prawdziwym
        composition root (entrypoint.build_runtime_service + _build_runtime_guarded)
        i prawdziwą tymczasową SQLite. Recording Yahoo boundary potwierdza
        discovery=1, daily=1, intraday=1 i brak drugiego discovery.
        """
        from application.controlled_validation import (
            ControlledValidationConfig,
            ControlledValidationController,
        )
        from application.controlled_validation_cli import PROD_DB

        artifacts = tmp_path / "artifacts"
        boundary = RecordingYahooBoundary()
        cfg = ControlledValidationConfig(
            isolated_db_path=controlled_full_db,
            artifacts_dir=artifacts,
            production_db_path=PROD_DB,
            allow_network=False,
            confirm_step7=True,
        )

        # Liczniki przed wykonaniem.
        conn = sqlite3.connect(str(controlled_full_db))
        try:
            cycles_before = conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
            snapshots_before = conn.execute(
                "SELECT COUNT(*) FROM universe_snapshots"
            ).fetchone()[0]
            obs_before = conn.execute(
                "SELECT COUNT(*) FROM instrument_observations"
            ).fetchone()[0]
            readings_before = conn.execute(
                "SELECT COUNT(*) FROM instrument_readings"
            ).fetchone()[0]
            events_before = conn.execute(
                "SELECT COUNT(*) FROM market_events"
            ).fetchone()[0]
        finally:
            conn.close()

        # Kontroler z prawdziwym composition root; run() wykona discovery,
        # zbuduje jednoelementowe źródło i wykona dokładnie jedno run_cycle().
        controller = ControlledValidationController(
            cfg=cfg,
            runtime_factory=lambda: None,  # nieużywany — runtime buduje kontroler
            real_yahoo_session=boundary,
            clock=_FakeClock([T0 + timedelta(hours=1, minutes=15)]),
        )
        # Marker jednokrotności — kontroler wymaga markera PRZED siecią.
        from application.controlled_validation import ensure_once_marker
        ensure_once_marker(artifacts)

        result = controller.run()

        # Wynik kontrolera — jeden raport, nie kolekcja.
        assert result["status"] in ("COMPLETE_E2E", "NO_NATURAL_E2E_CANDIDATE")
        # Dowód wykonaniowy (1 cykl, 1 snapshot) pozostaje ważny także przy
        # naturalnym stopie pipeline'u (NATURAL_PIPELINE_STOP), gdy zmiana nie
        # zostanie naturalnie zakwalifikowana do MasterEngine.
        assert result["trace"]["overall_status"] in (
            "SUCCESS", "PARTIAL", "NATURAL_PIPELINE_STOP",
        )

        # Dowód wykonaniowy w prawdziwej bazie.
        conn = sqlite3.connect(str(controlled_full_db))
        try:
            cycles_after = conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
            snapshots_after = conn.execute(
                "SELECT COUNT(*) FROM universe_snapshots"
            ).fetchone()[0]
            obs_after = conn.execute(
                "SELECT COUNT(*) FROM instrument_observations"
            ).fetchone()[0]
            readings_after = conn.execute(
                "SELECT COUNT(*) FROM instrument_readings"
            ).fetchone()[0]
            events_after = conn.execute(
                "SELECT COUNT(*) FROM market_events"
            ).fetchone()[0]

            # Dokładnie jeden nowy rekord cyklu.
            assert cycles_after - cycles_before == 1
            # Dokładnie jeden nowy snapshot kontrolnego cyklu.
            assert snapshots_after - snapshots_before == 1
            # Ta sama ACTIVE Observation (prawdziwe repository ładuje istniejącą
            # przez load_observation() i NIE tworzy duplikatu).
            assert obs_after == obs_before
            # Reading wzrósł o dokładnie 2: nowa CLOSED 1h + nowy OPEN 1h
            # z overlayem (anchor CLOSED 1h z tego samego payloadu intraday).
            assert readings_after - readings_before == 2
            # Brak nowych MarketEvent (przy naturalnym braku alertów nie
            # wymuszamy zdarzeń).
            assert events_after == events_before

            # Dokładnie jeden nowy snapshot zawiera przygotowany instrument.
            latest_snap = conn.execute(
                "SELECT snapshot_id FROM universe_snapshots "
                "ORDER BY rowid DESC LIMIT 1"
            ).fetchone()[0]
            member = conn.execute(
                "SELECT symbol FROM universe_snapshot_members "
                "WHERE snapshot_id = ? AND symbol = ?",
                (latest_snap, boundary.SYMBOL),
            ).fetchone()
            assert member is not None and member[0] == boundary.SYMBOL

            # Brak drugiego raportu / drugiego identyfikatora cyklu.
            rows = conn.execute(
                "SELECT cycle_id FROM cycles ORDER BY rowid DESC LIMIT 2"
            ).fetchall()
            assert len(rows) == 1

            # cycle_kind w zapisanym raporcie = SUBSEQUENT_CYCLE (enum zapisany
            # przez json.dumps(default=str) — akceptujemy ciąg znaków).
            cycle_row = conn.execute(
                "SELECT report_json FROM cycles WHERE cycle_id = ?",
                (rows[0][0],),
            ).fetchone()
            report = json.loads(cycle_row[0])
            assert "SUBSEQUENT_CYCLE" in str(report["diagnostics"]["cycle_kind"])
        finally:
            conn.close()

        # Granica Yahoo: dokładnie 1 discovery, 1 daily, 1 intraday.
        assert boundary.discovery_calls == 1
        assert boundary.daily_calls == 1
        assert boundary.intraday_calls == 1

        # Kontrolny trace zawiera dokładnie jedno wykonanie runtime.run_cycle
        # (etap cycle_persistence w stage order + brak drugiego).
        stages = result["trace"]["stages"]
        exec_cycle = [name for name, st in stages.items()
                      if st.get("status") == EXECUTED and "cycle" in name]
        assert len(exec_cycle) == 1


class _FakeClock:
    def __init__(self, times):
        self._times = list(times)
        self._idx = 0

    def __call__(self):
        value = self._times[min(self._idx, len(self._times) - 1)]
        self._idx += 1
        return value


class _OpenBoundary:
    SYMBOL = "AAA.WA"

    def __init__(self, candles):
        self.candles = candles

    def fetch_chart(self, symbol, variant="daily"):
        from data.yahoo.yahoo_session import FetchResult, OutcomeKind
        rows = self.candles if variant == "intraday" else self.candles
        return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA, data={
            "variant": variant, "http_status": 200,
            "captured_at": "2026-08-17T12:15:00+00:00",
            "meta": {"symbol": self.SYMBOL, "instrumentType": "EQUITY",
                     "currency": "PLN", "exchangeName": "WSE"},
            "timestamp": [int(ts.timestamp()) for ts in rows],
            "open": [4.0] * len(rows),
            "high": [4.1] * len(rows),
            "low": [3.9] * len(rows),
            "close": [4.0] * len(rows),
            "volume": [100] * len(rows),
            "events": {},
        }, message=None)


class TestControlledOverlayOpen1h:
    def test_injectable_clock(self):
        from application.controlled_validation import (
            ControlledYahooSession, YahooBudgetGuard,
        )
        boundary = _OpenBoundary([T0 - timedelta(hours=2)])
        session = ControlledYahooSession(
            boundary, YahooBudgetGuard(),
            previous_close=4.0, symbol="AAA.WA",
            clock=_FakeClock([T0 + timedelta(minutes=15)]),
        )
        assert session._clock is not None

    def test_no_open_candle_returns_no_data(self):
        from application.controlled_validation import (
            ControlledYahooSession, YahooBudgetGuard,
        )
        import copy as _copy

        class _RecordingRawBoundary:
            """Recording double of the external Yahoo boundary only:
            stores the raw intraday payload returned by the real boundary
            BEFORE adapter handling (proof close/high were not changed)."""
            def __init__(self, inner):
                self._inner = inner
                self.returned_raw = None

            def fetch_chart(self, symbol, variant="daily"):
                res = self._inner.fetch_chart(symbol, variant=variant)
                if variant == "intraday" and res.data is not None:
                    self.returned_raw = _copy.deepcopy(res.data)
                return res

        observed = T0 + timedelta(minutes=15)  # 12:15
        candles = [T0 - timedelta(hours=2), T0 - timedelta(hours=1)]  # CLOSED
        inner_boundary = _OpenBoundary(candles)
        recording = _RecordingRawBoundary(inner_boundary)
        session = ControlledYahooSession(
            recording, YahooBudgetGuard(), previous_close=4.0,
            symbol="AAA.WA", clock=_FakeClock([observed]),
        )
        result = session.fetch_chart("AAA.WA", variant="intraday")
        from data.yahoo.yahoo_session import OutcomeKind
        assert result.kind == OutcomeKind.SUCCESS_NO_DATA
        assert result.data is None
        assert session.overlay_applied is False
        assert session.overlay_state["status"] == "NO_OPEN_CANDIDATE"
        assert session.overlay_state["applied"] is False
        assert session.overlay_state["raw_preserved"] is True
        # Raw payload of the recording boundary stayed identical before and after
        # delegation - close/high prices were NOT changed.
        assert recording.returned_raw["close"] == [4.0, 4.0]

        assert recording.returned_raw["high"] == [4.1, 4.1]



class _TwoCandleBoundaryFull:
    """Recording double externalnej granicy Yahoo z CLOSED 1h + OPEN 1h.

    Deterministic APPLIED overlay: daily close=8.244, intraday CLOSED 1h
    (closed_ts) close=8.244 + OPEN 1h (open_ts) close=8.24. Obserwacja musi
    być po starcie OPEN, aby cykl zakwalifikował się jako COMPLETE_E2E.
    """

    SYMBOL = RecordingYahooBoundary.SYMBOL

    def __init__(self, closed_ts, open_ts):
        self.closed_ts = closed_ts
        self.open_ts = open_ts
        self.discovery_calls = 0
        self.daily_calls = 0
        self.intraday_calls = 0

    def paginate_screener(self, size=250):
        from data.yahoo.yahoo_session import (
            FetchResult, OutcomeKind, ScreenerPage, ScreenerPagination,
        )
        self.discovery_calls += 1
        page = ScreenerPage(total=1, start=0, count=1, quotes=[{
            "symbol": self.SYMBOL,
            "quoteType": "EQUITY", "currency": "PLN", "exchange": "WSE",
        }])
        return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA,
                           data=ScreenerPagination(total=1, pages=[page]),
                           message=None)

    def fetch_chart(self, symbol, variant="daily"):
        from data.yahoo.yahoo_session import FetchResult, OutcomeKind
        if variant == "daily":
            self.daily_calls += 1
            return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA, data={
                "variant": "daily", "http_status": 200,
                "captured_at": T0.isoformat(),
                "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                         "currency": "PLN", "exchangeName": "WSE"},
                "timestamp": [int(self.closed_ts.timestamp())],
                "open": [8.25], "high": [8.30], "low": [8.20],
                "close": [8.244], "volume": [100.0], "events": {},
            }, message=None)
        if variant == "intraday":
            self.intraday_calls += 1
            payload = {
                "variant": "intraday", "http_status": 200,
                "captured_at": T0.isoformat(),
                "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                         "currency": "PLN", "exchangeName": "WSE"},
                "timestamp": [int(self.closed_ts.timestamp()),
                              int(self.open_ts.timestamp())],
                "open": [8.25, 8.24], "high": [8.30, 8.26],
                "low": [8.20, 8.22], "close": [8.244, 8.24],
                "volume": [100.0, 150.0], "events": {},
            }
            return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA,
                               data=payload, message=None)
        raise AssertionError(f"unknown variant {variant}")


class _ClosedOnlyYahooBoundary:
    """Recording double of the external Yahoo boundary.

    Returns exactly one CLOSED intraday candle with close=5.0, deterministically
    earlier than candle_start + 1h so the controlled session classifies it as
    CLOSED and hard-stops as NO_OPEN_CANDIDATE (no OPEN candle in payload)."""

    SYMBOL = RecordingYahooBoundary.SYMBOL

    def __init__(self, intraday_ts):
        from data.yahoo.yahoo_session import (
            FetchResult,
            OutcomeKind,
            ScreenerPage,
            ScreenerPagination,
        )
        self.FetchResult = FetchResult
        self.OutcomeKind = OutcomeKind
        self.ScreenerPage = ScreenerPage
        self.ScreenerPagination = ScreenerPagination
        self.intraday_ts = intraday_ts
        self.discovery_calls = 0
        self.daily_calls = 0
        self.intraday_calls = 0
        self.raw_intraday_payload = None

    def paginate_screener(self, size: int = 250):
        self.discovery_calls += 1
        page = self.ScreenerPage(
            total=1, start=0, count=1, quotes=[{
                "symbol": self.SYMBOL, "quoteType": "EQUITY",
                "currency": "PLN", "exchange": "WSE",
            }],
        )
        return self.FetchResult(
            kind=self.OutcomeKind.SUCCESS_WITH_DATA,
            data=self.ScreenerPagination(total=1, pages=[page]),
            message=None,
        )

    def fetch_chart(self, symbol: str, variant: str = "daily"):
        import copy as _copy
        if variant == "daily":
            self.daily_calls += 1
            return self.FetchResult(
                kind=self.OutcomeKind.SUCCESS_WITH_DATA,
                data={
                    "variant": "daily", "http_status": 200,
                    "captured_at": T0.isoformat(),
                    "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                             "currency": "PLN", "exchangeName": "WSE"},
                    "timestamp": [int(self.intraday_ts.timestamp())],
                    "open": [5.0], "high": [5.1], "low": [4.9], "close": [5.0],
                    "volume": [100], "events": {},
                },
                message=None,
            )
        if variant == "intraday":
            self.intraday_calls += 1
            payload = {
                "variant": "intraday", "http_status": 200,
                "captured_at": T0.isoformat(),
                "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                         "currency": "PLN", "exchangeName": "WSE"},
                "timestamp": [int(self.intraday_ts.timestamp())],
                "open": [5.0], "high": [5.1], "low": [4.9], "close": [5.0],
                "volume": [100], "events": {},
            }
            # Keep the exact raw payload for the immutability proof.
            self.raw_intraday_payload = _copy.deepcopy(payload)
            return self.FetchResult(
                kind=self.OutcomeKind.SUCCESS_WITH_DATA,
                data=payload,
                message=None,
            )
        raise AssertionError("unknown variant {} - outside the contract".format(variant))


class TestOverlayAnchorClosed1h:
    """7F: anchor overlayu pochodzi WYŁĄCZNIE z payloadu intraday 1h
    (najnowsza OPEN + najbliższa wcześniejsza CLOSED 1h). Reading 5m
    (trwały historyczny close 8.75) NIE MOŻE być źródłem previous_close."""

    @staticmethod
    def _session(boundary, observed, previous_close=8.75):
        from application.controlled_validation import (
            ControlledYahooSession, YahooBudgetGuard,
        )
        return ControlledYahooSession(
            boundary, YahooBudgetGuard(), previous_close=previous_close,
            symbol="AAA.WA", clock=_FakeClock([observed]),
        )

    def test_close_is_8_57376_not_9_1_with_historical_5m_8_75(self):
        """Payload Yahoo: CLOSED 1h close=8.244 (11:00) + OPEN 1h (12:00).
        Trwały Reading 5m close=8.75 istnieje, ale anchor musi pochodzić
        z CLOSED 1h: controlled_close = 8.244*1.04 = 8.57376."""
        import copy as _copy
        from data.yahoo.yahoo_session import FetchResult, OutcomeKind

        class _TwoCandleBoundary:
            def __init__(self, closed_ts, open_ts):
                self.closed_ts = closed_ts
                self.open_ts = open_ts
                self.returned_raw = None

            def fetch_chart(self, symbol, variant="daily"):
                if variant != "intraday":
                    raise AssertionError(f"unexpected variant {variant}")
                payload = {
                    "variant": "intraday", "http_status": 200,
                    "captured_at": T0.isoformat(),
                    "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                             "currency": "PLN", "exchangeName": "WSE"},
                    "timestamp": [int(self.closed_ts.timestamp()),
                                  int(self.open_ts.timestamp())],
                    "open": [8.25, 8.24],
                    "high": [8.30, 8.26],
                    "low": [8.20, 8.22],
                    "close": [8.244, 8.24],
                    "volume": [100.0, 150.0],
                    "events": {},
                }
                self.returned_raw = _copy.deepcopy(payload)
                return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA,
                                   data=payload, message=None)

        observed = T0 + timedelta(minutes=15)      # 12:15
        closed_ts = T0 - timedelta(hours=1)        # 11:00 CLOSED
        open_ts = T0                               # 12:00 OPEN
        boundary = _TwoCandleBoundary(closed_ts, open_ts)
        session = self._session(boundary, observed, previous_close=8.75)
        result = session.fetch_chart("AAA.WA", variant="intraday")

        from data.yahoo.yahoo_session import OutcomeKind
        assert result.kind == OutcomeKind.SUCCESS_WITH_DATA
        assert session.overlay_applied is True
        data = result.data
        expected = 8.244 * 1.04
        assert expected == pytest.approx(8.57376)
        assert data["close"][-1] == pytest.approx(expected)
        assert data["close"][-1] != pytest.approx(8.75 * 1.04)
        assert data["high"][-1] == pytest.approx(max(8.26, expected))
        # Niezmienność open/low/volume/timestamp na świecy OPEN.
        assert data["open"][-1] == pytest.approx(8.24)
        assert data["low"][-1] == pytest.approx(8.22)
        assert data["volume"][-1] == pytest.approx(150.0)
        assert data["timestamp"][-1] == int(open_ts.timestamp())
        # Reading 5m (8.75) nie jest źródłem anchoru.
        assert session.overlay_state["effective_previous_close"] == pytest.approx(8.244)
        assert session.overlay_state["anchor_source"] == "YAHOO_PREVIOUS_CLOSED_1H"
        assert session.overlay_state["anchor_index"] == 0
        assert session.overlay_state["anchor_candle_state"] == "CLOSED"
        assert session.overlay_state["interval"] == "1h"
        assert session.overlay_state["open_index"] == 1
        assert session.overlay_state["status"] == "APPLIED"

    def test_open_without_previous_closed_1h_returns_no_data(self):
        """Payload zawiera wyłącznie OPEN 1h (brak wcześniejszej CLOSED 1h):
        overlay NIE jest wykonywany; status NO_PREVIOUS_CLOSED_1H_ANCHOR
        i naturalny stop przez SUCCESS_NO_DATA."""
        import copy as _copy
        from data.yahoo.yahoo_session import FetchResult, OutcomeKind

        class _OpenOnlyBoundary:
            def __init__(self, open_ts):
                self.open_ts = open_ts
                self.returned_raw = None

            def fetch_chart(self, symbol, variant="daily"):
                if variant != "intraday":
                    raise AssertionError(f"unexpected variant {variant}")
                payload = {
                    "variant": "intraday", "http_status": 200,
                    "captured_at": T0.isoformat(),
                    "meta": {"symbol": symbol, "instrumentType": "EQUITY",
                             "currency": "PLN", "exchangeName": "WSE"},
                    "timestamp": [int(self.open_ts.timestamp())],
                    "open": [8.24], "high": [8.26], "low": [8.22],
                    "close": [8.24], "volume": [150.0], "events": {},
                }
                self.returned_raw = _copy.deepcopy(payload)
                return FetchResult(kind=OutcomeKind.SUCCESS_WITH_DATA,
                                   data=payload, message=None)

        observed = T0 + timedelta(minutes=15)      # 12:15
        boundary = _OpenOnlyBoundary(T0)           # jedyna świeca = OPEN 12:00
        session = self._session(boundary, observed, previous_close=8.75)
        result = session.fetch_chart("AAA.WA", variant="intraday")

        from data.yahoo.yahoo_session import OutcomeKind
        assert result.kind == OutcomeKind.SUCCESS_NO_DATA
        assert result.data is None
        assert session.overlay_applied is False
        assert session.overlay_state["status"] == "NO_PREVIOUS_CLOSED_1H_ANCHOR"
        assert session.overlay_state["applied"] is False
        assert session.overlay_state["raw_preserved"] is True
        # Surowe dane granicy pozostały niezmienione.
        assert boundary.returned_raw["close"] == [8.24]
        assert boundary.returned_raw["high"] == [8.26]

    def test_overlay_trace_fields_persisted(self, tmp_path, controlled_full_db):
        """Pełny kontrolowany trace zawiera trwale wymagane pola overlayu:
        symbol, interval=1h, status, applied, open_index, open_candle_start,
        expected_close, observed_at, anchor_source, anchor_index,
        anchor_candle_start, anchor_candle_state=CLOSED,
        effective_previous_close, close_before, close_after, high_before,
        high_after oraz niezmienność open/low/volume/timestamp."""
        import copy as _copy
        from application.controlled_validation import (
            ControlledValidationConfig,
            ControlledValidationController,
            ensure_once_marker,
        )
        from application.controlled_validation_cli import PROD_DB
        from data.yahoo.yahoo_session import FetchResult, OutcomeKind

        artifacts = tmp_path / "artifacts"
        observed = T0 + timedelta(minutes=15)
        closed_ts = T0 - timedelta(hours=1)
        open_ts = T0
        boundary = _TwoCandleBoundaryFull(closed_ts, open_ts)
        # Trwały Reading 5m close=8.75 w izolowanej bazie — nie może być anchorem.
        conn = sqlite3.connect(str(controlled_full_db))
        try:
            conn.execute(
                "INSERT INTO instrument_readings "
                "(reading_id, observation_id, instrument_id, market_data_timestamp, "
                " scan_timestamp, open, high, low, close, volume, source, "
                " prev_reading_id, data_completeness, revision_number, "
                " supersedes_reading_id, timeframe, candle_state) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "rdg_5m_8_75", "obs_aaa", RecordingYahooBoundary.SYMBOL,
                    _iso(T0 - timedelta(days=2)), _iso(T0),
                    8.75, 8.75, 8.75, 8.75, 580360.0, "YahooFinance",
                    None, "COMPLETE", 1, None, "5m", "LEGACY_UNKNOWN",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        cfg = ControlledValidationConfig(
            isolated_db_path=controlled_full_db,
            artifacts_dir=artifacts,
            production_db_path=PROD_DB,
            allow_network=False,
            confirm_step7=True,
        )
        controller = ControlledValidationController(
            cfg=cfg, runtime_factory=lambda: None,
            real_yahoo_session=boundary, clock=_FakeClock([observed]),
        )
        ensure_once_marker(artifacts)
        result = controller.run()
        assert result["status"] == "COMPLETE_E2E"

        # Trace kontrolny — wymagane pola w stages.controlled_overlay.details.
        stage = result["trace"]["stages"]["controlled_overlay"]
        assert stage["status"] == EXECUTED
        details = stage.get("details", {})
        assert details["symbol"] == RecordingYahooBoundary.SYMBOL
        assert details["interval"] == "1h"
        assert details["status"] == "APPLIED"
        assert details["applied"] is True
        assert details["open_index"] == 1
        assert details["open_candle_start"] == _iso(open_ts)
        # 7F semantyka: expected_close = czas zamknięcia świecy OPEN 1h,
        # controlled_close = cena kontrolna = effective_previous_close * 1.04.
        assert details["expected_close"] == _iso(open_ts + timedelta(hours=1))
        assert details["controlled_close"] == pytest.approx(8.244 * 1.04)
        assert details["controlled_close"] == pytest.approx(8.57376)
        assert details["observed_at"] == _iso(observed)
        assert details["anchor_source"] == "YAHOO_PREVIOUS_CLOSED_1H"
        assert details["anchor_index"] == 0
        assert details["anchor_candle_start"] == _iso(closed_ts)
        assert details["anchor_candle_state"] == "CLOSED"
        assert details["effective_previous_close"] == pytest.approx(8.244)
        assert details["close_before"] == pytest.approx(8.24)
        assert details["close_after"] == pytest.approx(8.244 * 1.04)
        assert details["close_after"] == details["controlled_close"]
        assert details["high_before"] == pytest.approx(8.26)
        assert details["high_after"] == pytest.approx(max(8.26, 8.244 * 1.04))
        assert details["open_unchanged"] is True
        assert details["low_unchanged"] is True
        assert details["volume_unchanged"] is True
        assert details["timestamp_unchanged"] is True

        # Dokładnie jeden cykl, żadnego drugiego przebiegu.
        assert boundary.discovery_calls == 1
        assert boundary.daily_calls == 1
        assert boundary.intraday_calls == 1
        conn = sqlite3.connect(str(controlled_full_db))
        try:
            rows = conn.execute("SELECT cycle_id FROM cycles ORDER BY rowid DESC LIMIT 2").fetchall()
            assert len(rows) == 1
            # Anchor w bazie == CLOSED 1h (nie 5m): prev_reading_id otwartej 1h
            # wskazuje Reading CLOSED 1h, nie 5m 8.75.
            open_reading = conn.execute(
                "SELECT prev_reading_id, close, timeframe FROM instrument_readings "
                "WHERE instrument_id=? AND timeframe='1h' AND candle_state='OPEN'",
                (RecordingYahooBoundary.SYMBOL,),
            ).fetchone()
            assert open_reading is not None
            assert open_reading[1] == pytest.approx(8.244 * 1.04)
            anchor = conn.execute(
                "SELECT close, timeframe, candle_state FROM instrument_readings "
                "WHERE reading_id=?",
                (open_reading[0],),
            ).fetchone()
            assert anchor is not None
            assert anchor[1] == "1h" and anchor[2] == "CLOSED"
            assert anchor[0] == pytest.approx(8.244)
        finally:
            conn.close()


class TestControlledTraceJsonExport:
    """Trwały eksport kontrolowanego trace do artefaktu (Krok 7G/7H).

    Po pojedynczym przebiegu kontrolera CLI musi utworzyć
    ``<artifacts-dir>/controlled_validation_trace.json`` zawierający
    finalny sanitized wynik kontrolera, w tym
    ``stages.controlled_overlay.details`` z pełnym zestawem pól 7F.
    Plik nie może zawierać wartości sekretów.
    """

    @staticmethod
    def _normalized_secret_fingerprints(payload: dict):
        """Stałe know-bad fingerprints testowe (nie prawdziwe sekrety)."""
        secrets = [
            "sk-test-0000000000000000",
            "sk-11111111111111111111",
            "123456:AAbbCCddEEffGGhhIIjjKKll",
            "your-chat-id",
        ]
        return [s for s in secrets if s in json.dumps(payload)]

    def _run_controller_once(self, tmp_path, controlled_full_db, boundary, observed):
        from application.controlled_validation import (
            ControlledValidationConfig,
            ControlledValidationController,
            ensure_once_marker,
        )
        from application.controlled_validation_cli import PROD_DB

        artifacts = tmp_path / "artifacts"
        cfg = ControlledValidationConfig(
            isolated_db_path=controlled_full_db,
            artifacts_dir=artifacts,
            production_db_path=PROD_DB,
            allow_network=False,
            confirm_step7=True,
        )
        controller = ControlledValidationController(
            cfg=cfg, runtime_factory=lambda: None,
            real_yahoo_session=boundary, clock=_FakeClock([observed]),
        )
        # Marker przed pierwszym requestem — jak w CLI main().
        ensure_once_marker(artifacts)
        result = controller.run()

        # Krok 7G: pojedynczy zapis trace do artefaktów przez publiczną funkcję
        # CLI (RED: funkcja nie istnieje przed implementacją).
        from application.controlled_validation_cli import write_controlled_trace_json
        write_controlled_trace_json(result, artifacts)
        return result, artifacts

    @pytest.mark.parametrize("variant", ["applied", "natural_stop"])
    def test_trace_json_written_after_single_run(
        self, tmp_path: Path, controlled_full_db: Path, variant: str
    ):
        """Po pojedynczym run() kontrolera (dla APPLIED oraz NO_OPEN_CANDIDATE
        naturalnego stopu) istnieje plik controlled_validation_trace.json
        z finalnym sanitized wynikiem."""
        if variant == "applied":
            observed = T0 + timedelta(minutes=15)
            closed_ts = T0 - timedelta(hours=1)
            open_ts = T0
            boundary = _TwoCandleBoundaryFull(closed_ts, open_ts)
        else:
            observed = T0 + timedelta(hours=1, minutes=15)
            boundary = _ClosedOnlyYahooBoundary(
                intraday_ts=T0 - timedelta(hours=2)
            )

        result, artifacts = self._run_controller_once(
            tmp_path, controlled_full_db, boundary, observed
        )
        if variant == "applied":
            assert result["status"] == "COMPLETE_E2E"
        else:
            assert result["status"] == "NO_NATURAL_E2E_CANDIDATE"

        # W tym teście RED wymagamy pliku artefaktu (przed implementacją
        # zapisu trace przez CLI plik NIE istnieje — to punkt RED).
        trace_path = artifacts / "controlled_validation_trace.json"
        assert trace_path.exists(), (
            "CLI/main musi wyeksportować controlled_validation_trace.json "
            "do katalogu artefaktów po pojedynczym run()"
        )
        data = json.loads(trace_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        # Finalny wyniki kontrolera - status i trace.
        assert data["status"] == result["status"]
        assert data["trace"]["overall_status"] == result["trace"]["overall_status"]

        # Krok 7G: dla APPLIED plik trace musi zawierać pola overlayu 7F.
        # Dla naturalnego stopu (NO_OPEN_CANDIDATE) nie istnieją — weryfikujemy
        # wyłącznie utworzenie pliku, status i brak sekretów.
        if variant == "applied":
            stage = data["trace"]["stages"]["controlled_overlay"]
            details = stage.get("details", {})
            for key in (
                "symbol", "interval", "status", "applied",
                "anchor_source", "effective_previous_close",
                "expected_close", "controlled_close",
                "close_before", "close_after", "high_before", "high_after",
            ):
                assert key in details
            assert data["status"] == "COMPLETE_E2E"

        # Brak sekretów: know-bad fingerprints NIE występują w żadnym polu.
        # "telegram"/"chat_id" to nazwy pól liczników w trace, nie wartości
        # sekretów — weryfikujemy wyłącznie wzorce wartości sekretów.
        payload_str = json.dumps(data)
        for secret in ("sk-", "tvly-", "your-chat-id", "123456:AAbbCCddEEffGG"):
            assert secret not in payload_str


class TestNoOpenHardStop:
    def test_no_open_hard_stop_different_closed(
        self, tmp_path: Path, controlled_full_db: Path
    ):
        """Full-system hard natural stop for a payload with only CLOSED 1h.

        Real controller, real RuntimeService, real composition root on a real
        temp SQLite. Only the external Yahoo boundary is a recording double;
        existing recording guards remain untouched. Baseline 1h CLOSED has
        close 4.0; Yahoo intraday contains ONLY a CLOSED candle with close 5.0;
        observed_at is clearly later than candle_start + 1h. Different 4.0/5.0
        values are mandatory so the test cannot pass thanks to an accidentally
        identical fingerprint."""
        from application.controlled_validation import (
           ControlledValidationConfig,
           ControlledValidationController,
           ensure_once_marker,
        )
        from application.controlled_validation_cli import PROD_DB

        artifacts = tmp_path / "artifacts"
        observed = T0 + timedelta(hours=1, minutes=15)
        boundary = _ClosedOnlyYahooBoundary(
           intraday_ts=T0 - timedelta(hours=2)
        )
        cfg = ControlledValidationConfig(
           isolated_db_path=controlled_full_db,
           artifacts_dir=artifacts,
           production_db_path=PROD_DB,
           allow_network=False,
           confirm_step7=True,
        )

        conn = sqlite3.connect(str(controlled_full_db))
        try:
           cycles_before = conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
           readings_before = conn.execute(
               "SELECT COUNT(*) FROM instrument_readings"
           ).fetchone()[0]
           events_before = conn.execute(
               "SELECT COUNT(*) FROM market_events"
           ).fetchone()[0]
        finally:
           conn.close()

        controller = ControlledValidationController(
           cfg=cfg,
           runtime_factory=lambda: None,
           real_yahoo_session=boundary,
           clock=_FakeClock([observed]),
        )
        ensure_once_marker(artifacts)
        result = controller.run()

        assert result["status"] == "NO_NATURAL_E2E_CANDIDATE"
        assert result["trace"]["overall_status"] == NATURAL_PIPELINE_STOP

        assert boundary.discovery_calls == 1
        assert boundary.daily_calls == 1
        assert boundary.intraday_calls == 1

        session = controller.controlled_session
        assert session is not None
        assert session.overlay_state["status"] == "NO_OPEN_CANDIDATE"
        assert session.overlay_state["applied"] is False
        assert session.overlay_state["raw_preserved"] is True

        assert boundary.raw_intraday_payload["close"] == [5.0]
        assert boundary.raw_intraday_payload["high"] == [5.1]

        conn = sqlite3.connect(str(controlled_full_db))
        try:
           cycles_after = conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
           readings_after = conn.execute(
               "SELECT COUNT(*) FROM instrument_readings"
           ).fetchone()[0]
           events_after = conn.execute(
               "SELECT COUNT(*) FROM market_events"
           ).fetchone()[0]
           assert cycles_after - cycles_before == 1
           assert readings_after == readings_before
           assert events_after == events_before

           rows = conn.execute(
               "SELECT cycle_id FROM cycles ORDER BY rowid DESC LIMIT 2"
           ).fetchall()
           assert len(rows) == 1
        finally:
           conn.close()

        assert result["trace"]["external_calls"]["openai_attempts"] == 0
        assert result["trace"]["external_calls"]["tavily_attempts"] == 0
        assert result["trace"]["external_calls"]["telegram_attempts"] == 0

        # OpenAI/Tavily/Telegram pozostaja potwierdzone jako 0 wywolan przez

        stages = result["trace"]["stages"]
        exec_cycle = [name for name, st in stages.items()
                     if st.get("status") == EXECUTED and "cycle" in name]
        assert len(exec_cycle) == 1
