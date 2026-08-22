# -*- coding: utf-8 -*-
"""Test-first RED/GREEN — pełne naturalne połączenie: decyzja AI →
prawdziwy AlertBuilder → prawdziwy AlertDispatcher →
GuardedTelegramChannel → zewnętrzna granica Telegram (recording double).

Dokładnie jeden ``RuntimeService.run_cycle()`` na scenariusz.
Prawdziwe komponenty: RuntimeService, MasterEngine, DecisionEngine,
RankingEngine, RiskEngine, AnalystEngine, AlertBuilder, AlertDispatcher,
GuardedTelegramChannel, tymczasowe SQLite.
Doubles wyłącznie na zewnętrznych granicach: Yahoo, OpenAI, Telegram.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from application.alert_builder import AlertBuilder
from application.alert_dispatcher import AlertDispatcher
from application.channels.telegram_channel import TelegramChannel
from application.controlled_validation import (
    GuardedTelegramChannel,
    TelegramBudgetGuard,
)
from application.market_scanner import MarketScanner
from application.opportunity_deduplicator import OpportunityDeduplicator
from application.providers.yahoo_chart_provider import YahooChartProvider
from application.runtime import RuntimeService
from application.sources.yahoo_discovery_source import YahooDiscoverySource
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.universe import PennyStockUniverse
from data.models import InstrumentType
from data.models.instrument_observation import InstrumentObservation
from data.models.instrument_reading import InstrumentReading
from data.models.market_data import MarketData
from data.yahoo.yahoo_session import (
    FetchResult,
    OutcomeKind,
    ScreenerPage,
    ScreenerPagination,
)
from engines.analyst import AnalystEngine
from engines.ai import DecisionEngine
from engines.hunter import HunterEngine
from engines.master.engine import MasterEngine
from engines.news.filter import NewsFilterConfig
from engines.news.pipeline import NewsPipeline
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.technical import TechnicalEngine

ANCHOR_TS = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
CUR_TS = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


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


def _make_quote(symbol: str, price: float = 5.0) -> dict:
    return {
        "symbol": symbol,
        "quoteType": "EQUITY",
        "exchange": "WSE",
        "market": "pl_market",
        "currency": "PLN",
        "regularMarketPrice": price,
    }


def _chart_payload(symbol: str, market_data: list, variant: str) -> dict:
    ts = [int(md.timestamp.timestamp()) for md in market_data]
    return {
        "variant": variant,
        "http_status": 200,
        "captured_at": "2026-08-21T12:30:00+00:00",
        "meta": {
            "symbol": symbol,
            "instrumentType": "EQUITY",
            "currency": "PLN",
            "exchangeName": "WSE",
        },
        "timestamp": ts,
        "open": [md.open for md in market_data],
        "high": [md.high for md in market_data],
        "low": [md.low for md in market_data],
        "close": [md.close for md in market_data],
        "volume": [md.volume for md in market_data],
        "events": {},
    }


class FakeYahooSession:
    """Granica Yahoo — screener + daily + intraday (1h). Zero sieci."""

    def __init__(self, symbols, daily_by_symbol, intraday_by_symbol):
        self._symbols = list(symbols)
        self._daily = dict(daily_by_symbol)
        self._intraday = dict(intraday_by_symbol)

    def paginate_screener(self, size=250):
        page = ScreenerPage(
            total=len(self._symbols),
            start=0,
            count=len(self._symbols),
            quotes=[_make_quote(s) for s in self._symbols],
        )
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=ScreenerPagination(total=len(self._symbols), pages=[page]),
            message=None,
        )

    def fetch_chart(self, symbol, variant="daily"):
        if variant == "daily":
            data = self._daily.get(symbol)
        elif variant == "intraday":
            data = self._intraday.get(symbol)
        else:
            return FetchResult(
                kind=OutcomeKind.MISSING_FIELDS, data=None, message="unknown variant"
            )
        if data is None:
            return FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message="404")
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=_chart_payload(symbol, data, variant=variant),
            message=None,
        )


def _rising_daily(n=60) -> list:
    """Rosnąca daily — naturalnie produkuje eventy (run_ai=True)."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        MarketData(
            open=100.0 + d * 0.1,
            high=101.0 + d * 0.1,
            low=99.5 + d * 0.1,
            close=100.5 + d * 0.1,
            volume=500000.0,
            timestamp=base + timedelta(days=d),
        )
        for d in range(n)
    ]


class RecordingOpenAI:
    """Recording double granicy OpenAI — zapisuje dokładny payload."""

    def __init__(self, confidence: float = 0.8, order_log=None):
        self.confidence = confidence
        self.order_log = order_log
        self.calls = []

    def analyze(self, payload):
        self.calls.append(payload)
        if self.order_log is not None:
            self.order_log.append("openai")
        from engines.ai.openai_provider import AIAnalysisResult, OpenAIProviderResult

        return OpenAIProviderResult(
            result=AIAnalysisResult(
                facts=["Fakt"], hypotheses=["Hipoteza"], alternatives=["Alt"],
                risks=["Ryzyko"], data_limitations=["Limit"], justification="Ok",
                confidence=self.confidence,
            ),
            response_id="resp-step7c",
            request_id="req-step7c",
        )


class RecordingTelegramHTTP:
    """Recording zewnętrznej granicy Telegrama: url + payload + kolejność."""

    def __init__(self, order_log=None):
        self.calls = []
        self.order_log = order_log

    def __call__(self, url, json, timeout):
        self.calls.append((url, dict(json), timeout))
        if self.order_log is not None:
            self.order_log.append("telegram")
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "ok": True,
                "result": {"message_id": 7, "chat": {"id": "12345"}},
            },
        )


# ---------------------------------------------------------------------------
# Budowa prawdziwych komponentów
# ---------------------------------------------------------------------------

def _build_master(openai_provider):
    news_filter = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
    return MasterEngine(
        technical_engine=TechnicalEngine(),
        news_engine=NewsPipeline(news_filter),
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
        hunter_engine=HunterEngine(_hunter_config()),
        analyst_engine=AnalystEngine(),
        openai_provider=openai_provider,
    )


def _seed_subsequent_cycle_db(
    db_path: Path, *, symbol: str = "AAA.WA",
    anchor_ts=ANCHOR_TS, cur_ts=CUR_TS,
) -> None:
    """Przygotowanie SUBSEQUENT_CYCLE + OPEN rev1 istniejące.

    Stan początkowy (zgodnie z decyzją właściciela):
      * poprzednia świeca 11:00 CLOSED jako baseline 1h;
      * istniejąca bieżąca świeca 12:00 OPEN rev1 (close=101).
    Payload jedynego cyklu zawiera zmieniony stan tej samej świecy
    12:00 OPEN (close=103) i naturalnie zwróci CANDLE_PROGRESS_ACCEPTED,
    tworząc OPEN rev2; trajektoria do AI = OPEN rev1 + OPEN rev2
    z previous_closed 11:00.
    """
    repo = SQLiteHistoryRepository(db_path)
    t0 = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO universe_snapshots (snapshot_id, sequence, created_at, "
            "total_records, unique_symbols) VALUES (?,?,?,?,?)",
            ("snap_prev", 1, t0.isoformat(), 1, 1),
        )
        conn.execute(
            "INSERT INTO universe_snapshot_members (snapshot_id, symbol, present, "
            "status, first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?)",
            ("snap_prev", symbol, 1, "ACTIVE", t0.isoformat(), t0.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    obs = InstrumentObservation(
        observation_id="obs_aaa", instrument_id=symbol, timeframe="1h",
    )
    r_closed = InstrumentReading(
        reading_id="rdg_closed",
        observation_id=obs.observation_id,
        instrument_id=symbol,
        market_data_timestamp=anchor_ts,
        scan_timestamp=t0,
        open=100.0, high=101.0, low=99.0, close=100.0,
        volume=1000.0, data_completeness="COMPLETE",
        timeframe="1h", candle_state="CLOSED",
    )
    result = repo.save_reading(obs, r_closed)
    assert result == "ACCEPTED", f"baseline CLOSED seed: {result}"
    assert repo.save_baseline(symbol, "1h", r_closed.reading_id) == "BASELINE_ACCEPTED"

    r_open1 = InstrumentReading(
        reading_id="rdg_open1",
        observation_id=obs.observation_id,
        instrument_id=symbol,
        market_data_timestamp=cur_ts,
        scan_timestamp=t0,
        open=101.0, high=105.0, low=95.0, close=101.0,
        volume=1000.0, data_completeness="COMPLETE",
        timeframe="1h", candle_state="OPEN",
    )
    result = repo.save_reading(obs, r_open1)
    assert result == "ACCEPTED", f"OPEN rev1 seed: {result}"


def _build_runtime(db_path, session, openai_provider, telegram_channel, observed_at):
    provider = YahooChartProvider(session, clock=lambda: observed_at)
    discovery_source = YahooDiscoverySource(session)
    universe = PennyStockUniverse(discovery_source)
    scanner = MarketScanner(universe, provider)
    repo = SQLiteHistoryRepository(db_path)
    deduplicator = OpportunityDeduplicator(deduplication_window_seconds=1)
    master = _build_master(openai_provider)
    hunter = HunterEngine(_hunter_config())
    instrument_metadata = {"AAA.WA": ("GPW", InstrumentType.STOCK_GPW)}
    return RuntimeService(
        hunter_engine=hunter,
        master_engine=master,
        history_repository=repo,
        market_scanner=scanner,
        deduplicator=deduplicator,
        alert_builder=AlertBuilder(),
        alert_dispatcher=AlertDispatcher(),
        telegram_channel=telegram_channel,
        instrument_metadata=instrument_metadata,
        production_matrix_cycle=True,
    )


def _intraday_candles(current_close: float) -> list:
    """11:00 CLOSED + 12:00 OPEN — zmieniony stan bieżącej świecy 1h."""
    return [
        MarketData(
            timestamp=ANCHOR_TS, open=100.0, high=101.0, low=99.0,
            close=100.0, volume=1000.0,
        ),
        MarketData(
            timestamp=CUR_TS, open=101.0, high=105.0, low=95.0,
            close=current_close, volume=1000.0,
        ),
    ]


def _count_cycles(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Scenariusz pozytywny — AI + naturalne bramki + alert → dokładnie 1 Telegram
# ---------------------------------------------------------------------------

def test_ai_decision_reaches_controlled_telegram_once(tmp_path):
    db = tmp_path / "positive" / "e2e.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    _seed_subsequent_cycle_db(db)

    order_log: list = []
    openai = RecordingOpenAI(confidence=0.8, order_log=order_log)
    telegram_http = RecordingTelegramHTTP(order_log=order_log)
    telegram_channel = TelegramChannel(
        bot_token="test-token",
        chat_id="12345",
        http_client=telegram_http,
    )
    guarded = GuardedTelegramChannel(telegram_channel, TelegramBudgetGuard())

    session = FakeYahooSession(
        ["AAA.WA"],
        daily_by_symbol={"AAA.WA": _rising_daily(60)},
        intraday_by_symbol={"AAA.WA": _intraday_candles(current_close=103.0)},
    )
    rt = _build_runtime(
        db, session, openai, guarded,
        observed_at=datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc),
    )

    report = rt.run_cycle()

    assert report.diagnostics["cycle_kind"] == "SUBSEQUENT_CYCLE"
    assert report.diagnostics["candle_progress_saved"] == 1

    assert len(openai.calls) == 1
    payload = openai.calls[0]
    assert "candle_trajectory_1h" in payload
    traj = payload["candle_trajectory_1h"]
    assert traj["timeframe"] == "1h"
    assert traj["instrument_id"] == "AAA.WA"
    assert traj["candle_start"] == CUR_TS.isoformat()
    assert traj["previous_closed_close"] == 100.0
    assert [s["candle_state"] for s in traj["states"]] == ["OPEN", "OPEN"]
    assert [s["revision_number"] for s in traj["states"]] == [1, 2]
    assert traj["states"][0]["close"] == 101.0
    assert traj["states"][1]["close"] == 103.0

    assert len(telegram_http.calls) == 1
    url, tg_payload, _timeout = telegram_http.calls[0]
    assert "api.telegram.org" in url
    msg = tg_payload["text"]
    assert msg.count("ALCHEMIK — CONTROLLED_VALIDATION_ONLY") == 1
    assert msg.count("TO NIE JEST SYGNAŁ INWESTYCYJNY.") == 1
    assert len(msg) <= 4096

    assert order_log.count("openai") == 1
    assert order_log.count("telegram") == 1
    assert order_log.index("openai") < order_log.index("telegram")
    assert _count_cycles(db) == 1


# ---------------------------------------------------------------------------
# Scenariusz negatywny — AI osiągnięte, ale naturalna bramka zatrzymuje alert
# ---------------------------------------------------------------------------

def test_ai_call_alone_does_not_send_telegram(tmp_path):
    db = tmp_path / "negative" / "e2e.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    _seed_subsequent_cycle_db(db)

    order_log: list = []
    openai = RecordingOpenAI(confidence=0.4, order_log=order_log)
    telegram_http = RecordingTelegramHTTP(order_log=order_log)
    telegram_channel = TelegramChannel(
        bot_token="test-token",
        chat_id="12345",
        http_client=telegram_http,
    )
    guarded = GuardedTelegramChannel(telegram_channel, TelegramBudgetGuard())

    session = FakeYahooSession(
        ["AAA.WA"],
        daily_by_symbol={"AAA.WA": _rising_daily(60)},
        intraday_by_symbol={"AAA.WA": _intraday_candles(current_close=103.0)},
    )
    rt = _build_runtime(
        db, session, openai, guarded,
        observed_at=datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc),
    )

    rt.run_cycle()

    assert len(openai.calls) == 1
    assert "candle_trajectory_1h" in openai.calls[0]
    assert telegram_http.calls == []
    assert order_log.count("openai") == 1
    assert order_log.count("telegram") == 0
    assert _count_cycles(db) == 1
