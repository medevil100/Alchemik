# -*- coding: utf-8 -*-
"""Test-first RED/GREEN — trajektoria 1h dociera do payloadu OpenAI.

Pełne połączenie: prawdziwy RuntimeService → prawdziwy MasterEngine →
granica OpenAI (recording double). Test używa rzeczywistej tymczasowej
SQLite i rzeczywistych komponentów wewnętrznych. Test doubles wyłącznie na
granicach zewnętrznych: Yahoo (session) i OpenAI (recording double).

Pierwszy cykl inicjalizuje baseline 1h (nie uruchamia silników). Drugi cykl
rejestruje postęp bieżącej świecy 1h (CANDLE_PROGRESS_ACCEPTED) i — w tym
samym, pojedynczym wywołaniu run_cycle — przekazuje trajektorię do
MasterEngine, a ten umieszcza ją w payloadzie granicy OpenAI jako dokładnie
jeden klucz ``candle_trajectory_1h``.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from application.market_scanner import MarketScanner
from application.opportunity_deduplicator import OpportunityDeduplicator
from application.providers.yahoo_chart_provider import YahooChartProvider
from application.runtime import RuntimeService
from application.sources.yahoo_discovery_source import YahooDiscoverySource
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.universe import PennyStockUniverse
from data.models import InstrumentType
from data.models.market_data import MarketData
from data.yahoo.yahoo_session import (
    FetchResult,
    OutcomeKind,
    ScreenerPage,
    ScreenerPagination,
)
from engines.hunter.engine import HunterEngine


# ---------------------------------------------------------------------------
# Ustalone czasy 1h i świece
# ---------------------------------------------------------------------------

ANCHOR_TS = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)  # CLOSED poprzednia
CUR_TS = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)      # bieżąca świeca 1h


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
        "captured_at": "2026-08-21T12:15:00+00:00",
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
            return FetchResult(kind=OutcomeKind.MISSING_FIELDS, data=None, message="unknown variant")
        if data is None:
            return FetchResult(kind=OutcomeKind.HTTP_ERROR, data=None, message="404")
        if isinstance(data, list) and not data:
            return FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=_chart_payload(symbol, data, variant=variant),
            message=None,
        )


def _rising_daily(n=60) -> list:
    """Rosnąca daily — wytwarza zdarzenie HIGH (run_ai) w detektorach."""
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


def _intraday_candles(current_close: float) -> list:
    """Poprzednia CLOSED + bieżąca OPEN (ta sama godzina).

    Wartości OHLC są spójne dla całego zakresu ``current_close`` użytego w
    teście (101.0 → 103.0): high >= close, low <= close, high >= open,
    low <= open. Inaczej YahooChartProvider odrzuciłby wiersz jako
    ``ohlc_inconsistency`` i trajektoria nie powstałaby.
    """
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


class RecordingOpenAI:
    """Recording double granicy OpenAI — zapisuje dokładnie otrzymany payload."""

    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def analyze(self, payload):
        self.calls.append(payload)
        return self.result


def _build_master(openai_provider):
    from engines.analyst import AnalystEngine
    from engines.ai import DecisionEngine
    from engines.master.engine import MasterEngine
    from engines.news.pipeline import NewsPipeline
    from engines.news.filter import NewsFilterConfig
    from engines.ranking import RankingEngine
    from engines.risk import RiskEngine
    from engines.technical import TechnicalEngine

    news_filter = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
    return MasterEngine(
        technical_engine=TechnicalEngine(),
        news_engine=NewsPipeline(news_filter),
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
        hunter_engine=HunterEngine(_hunter_config()),
        analyst_engine=AnalystEngine(),
        tavily_adapter=None,
        openai_provider=openai_provider,
    )


def _build_runtime(db_path, session, openai_provider, observed_at):
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
        instrument_metadata=instrument_metadata,
        production_matrix_cycle=True,
    )


def _valid_provider_result():
    from engines.ai.openai_provider import AIAnalysisResult, OpenAIProviderResult
    return OpenAIProviderResult(
        result=AIAnalysisResult(
            facts=["Fakt"], hypotheses=["Hipoteza"], alternatives=["Alt"],
            risks=["Ryzyko"], data_limitations=["Limit"], justification="Ok",
            confidence=0.8,
        ),
        response_id="resp-trajectory",
        request_id="req-trajectory",
    )


def test_candle_trajectory_1h_reaches_openai_payload(tmp_path):
    db = tmp_path / "e2e.db"
    daily = _rising_daily(60)

    # --- Cykl 1: baseline 1h (11:00 CLOSED + 12:00 OPEN close=101). ---
    openai1 = RecordingOpenAI(result=_valid_provider_result())
    session1 = FakeYahooSession(
        ["AAA.WA"],
        daily_by_symbol={"AAA.WA": daily},
        intraday_by_symbol={"AAA.WA": _intraday_candles(current_close=101.0)},
    )
    rt1 = _build_runtime(
        db, session1, openai1,
        observed_at=datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc),
    )
    report1 = rt1.run_cycle()
    assert report1.diagnostics["cycle_kind"] == "BASELINE_INITIALIZED"
    assert openai1.calls == []  # pierwszy cykl nie uruchamia silników

    # --- Cykl 2: postęp bieżącej świecy (12:00 OPEN close=103). ---
    openai2 = RecordingOpenAI(result=_valid_provider_result())
    session2 = FakeYahooSession(
        ["AAA.WA"],
        daily_by_symbol={"AAA.WA": daily},
        intraday_by_symbol={"AAA.WA": _intraday_candles(current_close=103.0)},
    )
    rt2 = _build_runtime(
        db, session2, openai2,
        observed_at=datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc),
    )
    report2 = rt2.run_cycle()

    assert report2.diagnostics["cycle_kind"] == "SUBSEQUENT_CYCLE"
    assert report2.diagnostics["candle_progress_saved"] == 1
    assert report2.diagnostics["revisions_saved"] == 0

    # Dokładnie jeden zapis trajektorii na granicy OpenAI w badanym cyklu.
    assert len(openai2.calls) == 1
    payload = openai2.calls[0]
    assert "candle_trajectory_1h" in payload

    traj = payload["candle_trajectory_1h"]
    assert traj["timeframe"] == "1h"
    assert traj["instrument_id"] == "AAA.WA"
    assert traj["candle_start"] == CUR_TS.isoformat()
    assert traj["previous_closed"]["candle_state"] == "CLOSED"
    assert traj["previous_closed_close"] == 100.0

    states = traj["states"]
    assert [s["revision_number"] for s in states] == [1, 2]
    assert [s["candle_state"] for s in states] == ["OPEN", "OPEN"]
    assert states[0]["close"] == 101.0
    assert states[1]["close"] == 103.0