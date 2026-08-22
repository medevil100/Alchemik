"""
Point 7/7 — controlled single-instrument E2E validation (testy offline, RED→GREEN).

PRZED zmiana produkcyjna (RED): testy wykazują brakujący kontrakt:
  - produkcyjny AlertBuilder nie przepuszcza naturalnego wyniku domenowego
    (final_rating=0.8, confidence=0.8, recommendation="BUY");
  - RuntimeService nie ma trybu ``CONTROLLED_E2E_VALIDATION``;
  - trace nie wiąże wywołań zewnętrznych z event_id/final_result_id/alert_id;
  - trace nie raportuje yahoo_attempts/yahoo_real_sent jako dowodu rzeczywistych
    wywołań;
  - NewsPipeline nie ma jawnego oznaczenia EXECUTED_EMPTY.

Test doubles wyłącznie na zewnętrznych granicach (Yahoo, Tavily API, OpenAI API,
Telegram HTTP) — ręcznie napisane deterministyczne recording transports.
BEZ ``unittest.mock``, ``Mock``, ``MagicMock``, ``patch``, ``monkeypatch``.
Wewnętrzne komponenty ALCHEMIKA są prawdziwe (TechnicalEngine, MasterEngine,
AlertBuilder, AlertDispatcher, SQLiteHistoryRepository, itd.).
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from application import entrypoint
from application.alert_builder import AlertBuilder
from application.runtime import RuntimeService
from application.channels.telegram_channel import TelegramChannel
from data.models import FinalAnalysisResult, MarketData, MarketEvent
from data.models.event_enums import (
    EventFamily,
    EventOwner,
    InstrumentType,
    PriorityLevel,
    SignalTiming,
)
from data.models.pipeline_decision import PipelineDecision
from engines.ai.openai_provider import AIAnalysisResult, OpenAIProviderResult
from tests.test_point2_e2e_flow import make_quote, ts
from tests.test_point4_ai_tavily import (
    _rising_md,
    _vol_spike_md,
    _yahoo_rows,
)


T1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Recording transports — wyłącznie granice zewnętrzne (bez unittest.mock)
# ---------------------------------------------------------------------------

class RecordingYahooSession:
    """Nagrywająca granica Yahoo: zero sieci, zapis każdego wywołania."""

    def __init__(self, quotes, chart_rows_by_symbol):
        self._quotes = list(quotes)
        self._chart_rows = dict(chart_rows_by_symbol)
        self.paginate_calls = 0
        self.chart_calls = []
        self.real_network_sent = 0  # transport nigdy nie dotyka sieci

    def paginate_screener(self, size=250):
        from data.yahoo.yahoo_session import (
            FetchResult,
            OutcomeKind,
            ScreenerPage,
            ScreenerPagination,
        )
        self.paginate_calls += 1
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

    def fetch_chart(self, symbol, variant="daily"):
        from data.yahoo.yahoo_session import FetchResult, OutcomeKind
        self.chart_calls.append(symbol)
        rows = self._chart_rows.get(symbol)
        if rows is None:
            return FetchResult(kind=OutcomeKind.SUCCESS_NO_DATA, data=None, message=None)
        timestamps = [r[0] for r in rows]
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data={
                "variant": variant,
                "meta": {
                    "symbol": symbol,
                    "instrumentType": "EQUITY",
                    "currency": "PLN",
                    "exchangeName": "WSE",
                },
                "timestamp": timestamps,
                "open": [r[1] for r in rows],
                "high": [r[2] for r in rows],
                "low": [r[3] for r in rows],
                "close": [r[4] for r in rows],
                "volume": [r[5] for r in rows],
                "events": {},
            },
            message=None,
        )


class RecordingTavilyClient:
    """Nagrywająca granica HTTP Tavily API."""

    def __init__(self, results=None):
        self.results = results if results is not None else [
            {
                "title": "Spółka AAPL raportuje wyniki",
                "url": "https://example.com/aapl-results",
                "content": "Treść wiadomości o spółce AAPL i jej wynikach.",
                "score": 0.9,
                "published_date": "2026-03-01T00:00:00Z",
            }
        ]
        self.queries = []

    def search(self, request):
        self.queries.append(request.query)
        return {"results": self.results}


class RecordingOpenAIProvider:
    """Nagrywająca granica HTTP OpenAI API (zwraca zwalidowany wynik)."""

    def __init__(self, result=None, exc=None):
        self.result = result if result is not None else _valid_provider_result()
        self.exc = exc
        self.calls = []

    def analyze(self, payload):
        self.calls.append(payload)
        if self.exc is not None:
            raise self.exc
        return self.result


class RecordingTelegramHTTP:
    """Nagrywająca granica HTTP Telegram (deterministyczna odpowiedź)."""

    def __init__(self, ok=True, message_id=42, chat_id="123456"):
        self.calls = []
        self.ok = ok
        self.message_id = message_id
        self.chat_id = chat_id

    def __call__(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse(
            status_code=200,
            payload={
                "ok": self.ok,
                "result": {
                    "message_id": self.message_id,
                    "chat": {"id": int(self.chat_id)},
                },
            },
        )


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _valid_provider_result(confidence=0.8) -> OpenAIProviderResult:
    return OpenAIProviderResult(
        result=AIAnalysisResult(
            facts=["Cena rośnie w oknie obserwacji"],
            hypotheses=["Możliwa kontynuacja trendu"],
            alternatives=["Możliwa korekta"],
            risks=["Wysoka zmienność"],
            data_limitations=["Brak danych fundamentalnych"],
            justification="Wzrost potwierdzony danymi OHLCV i wskaźnikami",
            confidence=confidence,
        ),
        response_id="resp_point7_1",
        request_id="req_point7_1",
    )


# ---------------------------------------------------------------------------
# Helpers budowy runtime (realne komponenty wewnętrzne)
# ---------------------------------------------------------------------------

def _make_tavily_adapter(client=None):
    from data.tavily.config import TavilyConfig
    from data.tavily.event_adapter import TavilyEventAdapter
    from data.tavily.service import TavilyService
    cfg = TavilyConfig(
        api_key="test-tavily-key",
        enabled=True,
        max_age_hours=24 * 366,
    )
    svc = TavilyService(cfg)
    svc._client = client if client is not None else RecordingTavilyClient()
    return TavilyEventAdapter(svc), svc._client


def _build_runtime(tmp_path, session, *, telegram=None):
    """Produkcyjny composition root + realne komponenty + recording granice."""
    rt = entrypoint.build_runtime_service(
        persist_path=Path(tmp_path) / "e2e.db",
        yahoo_session=session,
    )
    rt.master_engine.openai_provider = RecordingOpenAIProvider()
    adapter, client = _make_tavily_adapter()
    rt.master_engine._tavily_adapter = adapter
    if telegram is not None:
        rt.telegram_channel = telegram
    return rt


def _telegram_channel() -> TelegramChannel:
    return TelegramChannel(
        bot_token="fake-bot-token",
        chat_id="123456",
        http_client=RecordingTelegramHTTP(),
    )


def _natural_event(symbol="AAA.WA") -> MarketEvent:
    return MarketEvent(
        event_id="ev_point7_1",
        timestamp_utc=datetime.now(timezone.utc),
        ticker=symbol,
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        event_family=EventFamily.TECHNICAL,
        event_category="Trend",
        event_type="MA_CROSSOVER",
        signal_timing=SignalTiming.LEADING,
        priority_raw=PriorityLevel.HIGH,
        priority_final=PriorityLevel.HIGH,
        confidence_level=0.8,
        detection_source="Point7Test",
        event_owner=EventOwner.TechnicalEngine,
        quality_level=PriorityLevel.HIGH,
    )


def _natural_final(symbol="AAA.WA") -> FinalAnalysisResult:
    return FinalAnalysisResult(
        symbol=symbol,
        final_rating=0.8,
        confidence_level=0.8,
        recommendation="BUY",
        positive_factors=["High ranking score (0.90)"],
        risk_factors=[],
        warnings=[],
        summary="AAA.WA: Final score 0.80 (BUY).",
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# 7/18 — produkcyjny AlertBuilder przepuszcza naturalny wynik domenowy (RED)
# ---------------------------------------------------------------------------

class TestProductionAlertBuilder:
    def test_production_alert_builder_passes_natural_domain_result(self):
        """final_rating=0.8 / confidence=0.8 / BUY (skala config/analyst.py)
        musi naturalnie przejść przez produkcyjny AlertBuilder(min 0.7/0.7)."""
        builder = AlertBuilder()  # progi produkcyjne 0.7 / 0.7
        assert builder.should_alert(_natural_final(), event=_natural_event())

    def test_alert_build_uses_real_final_result_fields(self):
        builder = AlertBuilder()
        alert = builder.build_alert(_natural_final(), event=_natural_event())
        assert alert.symbol == "AAA.WA"
        assert alert.formatted_message
        assert "AAA.WA" in alert.formatted_message
        assert "BUY" in alert.formatted_message
        assert "nie jest automatyczną rekomendacją BUY/SELL" in alert.formatted_message


# ---------------------------------------------------------------------------
# 1 — RuntimeService ma minimalny tryb CONTROLLED_E2E_VALIDATION (RED)
# ---------------------------------------------------------------------------

class TestControlledE2EModeContract:
    def test_runtime_has_controlled_e2e_validation_method(self):
        assert hasattr(RuntimeService, "run_controlled_e2e_validation")

    def test_e2e_mode_is_additive_and_does_not_touch_run_cycle(self, tmp_path):
        """run_cycle() nie zmienia swojego zachowania po dodaniu trybu E2E."""
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA", price=5.0)],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_vol_spike_md(60))},
        )
        rt = _build_runtime(tmp_path, session)
        report = rt.run_cycle()
        # Domyślny tryb nadal działa (1 instrument, żadnej sieci).
        assert report.candidates_count >= 1
        assert report.diagnostics["trace"]["external_calls"]["yahoo_real_sent"] == 0


# ---------------------------------------------------------------------------
# 8/9 — pierwszy naturalny kandydat zatrzymuje zewnętrzne przetwarzanie (RED)
# ---------------------------------------------------------------------------

class TestSingleNaturalCandidateStop:
    def test_stops_after_first_natural_candidate(self, tmp_path):
        """Chart tylko do pierwszego naturalnie kwalifikującego instrumentu;
        OpenAI i Telegram maksymalnie raz."""
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA", price=5.0), make_quote("BBB.WA", price=6.0)],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_vol_spike_md(60)),
                "BBB.WA": _yahoo_rows(_rising_md(60)),
            },
        )
        rt = _build_runtime(tmp_path, session, telegram=_telegram_channel())
        result = rt.run_controlled_e2e_validation()

        # Openai dokładnie 1; Tavily co najwyżej dla zdarzeń pierwszego instrumentu.
        assert len(rt.master_engine.openai_provider.calls) == 1
        assert len(session.chart_calls) <= 2  # może sprawdzić drugi przed znalezieniem

        # Telegram wysłany dokładnie raz, gdy alert naturalny.
        if result.get("status") == "COMPLETE_E2E":
            assert result.get("telegram_attempts", 0) <= 1
            assert result.get("telegram_sent", 0) <= 1

    def test_no_natural_candidate_returns_no_natural_e2e_candidate(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA", price=5.0)],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_rising_md(1)),  # za krótka historia
            },
        )
        rt = _build_runtime(tmp_path, session, telegram=_telegram_channel())
        result = rt.run_controlled_e2e_validation()
        assert result.get("status") == "NO_NATURAL_E2E_CANDIDATE"
        # Brak OpenAI i Telegrama przy braku kandydata.
        assert len(rt.master_engine.openai_provider.calls) == 0


# ---------------------------------------------------------------------------
# 18 — błąd discovery nie uruchamia fallbacku (RED)
# ---------------------------------------------------------------------------

class TestDiscoveryErrorNoFallback:
    def test_error_discovery_is_not_success_fallback(self, tmp_path):
        class BrokenDiscovery(RecordingYahooSession):
            def paginate_screener(self, size=250):
                from data.yahoo.yahoo_session import (
                    FetchResult,
                    OutcomeKind,
                )
                return FetchResult(
                    kind=OutcomeKind.HTTP_ERROR,
                    data=None,
                    message="HTTP 500",
                )

        session = BrokenDiscovery(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={},
        )
        rt = _build_runtime(tmp_path, session)
        result = rt.run_controlled_e2e_validation()
        assert result.get("status") == "ERROR_YAHOO_DISCOVERY"
        assert len(rt.master_engine.openai_provider.calls) == 0


# ---------------------------------------------------------------------------
# 19 — błąd jednego instrumentu nie zatrzymuje kolejnych (RED)
# ---------------------------------------------------------------------------

class TestInstrumentErrorContinues:
    def test_bad_first_instrument_continues_to_next(self, tmp_path):
        """Pierwszy instrument z błędem chart nie zatrzymuje drugiego."""
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                # AAA.WA: brak chart → SUCCESS_NO_DATA (błąd, nie kandydat)
                "BBB.WA": _yahoo_rows(_rising_md(60)),
            },
        )
        rt = _build_runtime(tmp_path, session)
        result = rt.run_controlled_e2e_validation()
        assert "BBB.WA" in session.chart_calls


# ---------------------------------------------------------------------------
# 5/6/16 — brak konstruowania suffixu, brak sztucznych zdarzeń, data_flow (RED)
# ---------------------------------------------------------------------------

class TestContractStaticChecks:
    def test_no_symbol_suffix_construction_in_runtime_source(self):
        import textwrap
        source = textwrap.dedent(
            inspect.getsource(RuntimeService.run_controlled_e2e_validation)
        )
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.endswith(".WA"), (
                    "kod trybu E2E nie może konstruować symboli"
                )
                assert ".NC" not in node.value

    def test_no_manual_market_event_creation_in_e2e_mode(self):
        import textwrap
        source = textwrap.dedent(
            inspect.getsource(RuntimeService.run_controlled_e2e_validation)
        )
        assert "MarketEvent(" not in source
        assert "FinalAnalysisResult(" not in source

    def test_no_alert_threshold_lowering_in_e2e_mode(self):
        import textwrap
        source = textwrap.dedent(
            inspect.getsource(RuntimeService.run_controlled_e2e_validation)
        )
        assert "AlertBuilder(" not in source
        assert "min_final_score" not in source


# ---------------------------------------------------------------------------
# 12/13/14 — trace: Yahoo attempts/real_sent, wiązanie, ranking/risk (RED)
# ---------------------------------------------------------------------------

class TestTraceBindingE2E:
    def test_trace_has_yahoo_attempts_and_real_sent(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(60))},
        )
        rt = _build_runtime(tmp_path, session)
        result = rt.run_controlled_e2e_validation()
        trace = result.get("trace") or {}
        ec = trace.get("external_calls", {})
        assert "yahoo_attempts" in ec
        assert "yahoo_real_sent" in ec

    def test_instrument_trace_has_event_final_alert_ids(self, tmp_path):
        import application.cycle_trace as ct
        entry = ct.new_instrument_entry("AAA.WA")
        for key in ("event_id", "final_result_id", "alert_id"):
            assert key in entry, f"trace per-instrument nie ma pola {key}"

    def test_trace_binds_external_calls_to_cycle_and_symbol(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_vol_spike_md(60))},
        )
        rt = _build_runtime(tmp_path, session, telegram=_telegram_channel())
        result = rt.run_controlled_e2e_validation()
        trace = result.get("trace") or {}
        assert trace.get("cycle_id")
        for name in ("tavily", "openai", "telegram"):
            assert f"{name}_real_sent" in trace.get("external_calls", {})

    def test_ranking_and_risk_have_explicit_execution_markers(self, tmp_path):
        import application.cycle_trace as ct
        stages = ct.STAGE_ORDER
        assert "ranking" in stages
        assert "risk" in stages


# ---------------------------------------------------------------------------
# 15 — wiadomość Telegram z prawdziwego FinalAnalysisResult (RED)
# ---------------------------------------------------------------------------

class TestTelegramFromRealFinalResult:
    def test_telegram_message_comes_from_real_final_result(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_vol_spike_md(60))},
        )
        http = RecordingTelegramHTTP()
        rt = _build_runtime(
            tmp_path,
            session,
            telegram=TelegramChannel(
                bot_token="fake-bot-token",
                chat_id="123456",
                http_client=http,
            ),
        )
        result = rt.run_controlled_e2e_validation()
        trace = result.get("trace") or {}
        if result.get("status") == "COMPLETE_E2E":
            instr = trace["instruments"]["AAA.WA"]
            assert instr["alert_id"], "alert_id musi być powiązany w trace"
            assert instr["final_result_id"], "final_result_id musi być powiązany"
            assert instr["event_id"], "event_id musi być powiązany"
            assert http.calls, "Telegram musiał zostać wywołany"
            text = http.calls[0]["json"]["text"]
            assert "AAA.WA" in text
            assert "CONTROLLED_E2E_VALIDATION" in text


# ---------------------------------------------------------------------------
# 16 — data_flow_complete nie może być true bez potwierdzonego Telegrama (RED)
# ---------------------------------------------------------------------------

class TestDataFlowRequiresTelegram:
    def test_data_flow_complete_false_without_confirmed_telegram(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_vol_spike_md(60))},
        )
        # Telegram zwraca ok=False — brak potwierdzenia.
        rt = _build_runtime(
            tmp_path,
            session,
            telegram=TelegramChannel(
                bot_token="fake-bot-token",
                chat_id="123456",
                http_client=RecordingTelegramHTTP(ok=False),
            ),
        )
        result = rt.run_controlled_e2e_validation()
        trace = result.get("trace") or {}
        assert trace.get("data_flow_complete") is False


# ---------------------------------------------------------------------------
# 20/21/22 — sekrety, serializowalność, brak retry/fallbacku
# ---------------------------------------------------------------------------

class TestSafetyAndSerialization:
    def test_trace_has_no_secrets(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(60))},
        )
        rt = _build_runtime(tmp_path, session)
        result = rt.run_controlled_e2e_validation()
        trace = result.get("trace") or {}
        serialized = json.dumps(trace, default=str).lower()
        for forbidden in (
            "api_key", "authorization", "bearer", "cookie", "crumb",
            "bot_token", "chat_id", "sk-", "tvly-",
        ):
            assert forbidden not in serialized, forbidden

    def test_trace_is_json_serializable(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(60))},
        )
        rt = _build_runtime(tmp_path, session)
        result = rt.run_controlled_e2e_validation()
        json.dumps(result, default=str)  # nie rzuca

    def test_no_retry_or_fallback_in_trace_counters(self, tmp_path):
        session = RecordingYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(60))},
        )
        rt = _build_runtime(tmp_path, session)
        result = rt.run_controlled_e2e_validation()
        trace = result.get("trace") or {}
        counters = trace.get("counters", {})
        assert counters.get("retry_count", 0) == 0
        assert counters.get("fallback_count", 0) == 0


# ---------------------------------------------------------------------------
# Krok 7B — nowy kontrakt: dokładnie jedno run_cycle() + kontrolne GUI
# ---------------------------------------------------------------------------

class TestStep7BControlledContract:
    def test_controlled_validation_delegates_to_exactly_one_run_cycle(
        self, tmp_path
    ):
        """Kontroler wywołuje dokładnie jedno RuntimeService.run_cycle().

        Nie zastępujemy RuntimeService mockiem — używamy prawdziwego cyklu
        i sprawdzamy, że istniała tylko jedna wykonywana logika runtime (poprzez
        statyczną kontrolę pojedynczego miejsca wywołania w kontrolerze).
        """
        import inspect
        from application.controlled_validation import ControlledValidationController
        source = inspect.getsource(ControlledValidationController.run)
        # Docstring wspomina run_cycle() (RuntimeService.run_cycle()), ale
        # rzeczywiste wywołanie metody to dokładnie jedno runtime.run_cycle().
        assert source.count("runtime.run_cycle()") == 1

    def test_controlled_stage_statuses_exist(self):
        from application import cycle_trace as ct
        from application.controlled_validation import CONTROLLED_STAGE_ORDER
        assert ct.EXECUTED in ct.DIAGNOSTIC_STATUSES
        assert ct.BLOCKED_BY_BUDGET in ct.DIAGNOSTIC_STATUSES
        assert ct.NATURAL_PIPELINE_STOP in ct.DIAGNOSTIC_STATUSES
        assert "preflight" in CONTROLLED_STAGE_ORDER
        assert "controlled_overlay" in CONTROLLED_STAGE_ORDER
        assert "cycle_persistence" in CONTROLLED_STAGE_ORDER
        assert "final_database_check" in CONTROLLED_STAGE_ORDER
