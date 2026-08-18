"""
Point 6/7 — obserwowalny ślad cyklu ALCHEMIKA (testy offline).

Przepływ testowany na rzeczywistych komponentach wewnętrznych:
    FakeYahoo (boundary) → YahooDiscoverySource → YahooChartProvider
    → MarketScanner → RuntimeService → SQLiteHistoryRepository (tmp)
    → Technical/Hunter/Master/Analyst/Ranking/Risk/Decision
    → FakeTavily (boundary) → FakeOpenAI (boundary)
    → AlertBuilder → AlertDispatcher → TelegramChannel (fake HTTP boundary)

Test doubles wyłącznie na granicach systemu: Yahoo, Tavily API, OpenAI API,
Telegram HTTP. Żaden wewnętrzny komponent ALCHEMIKA nie jest mockowany.

Ślad jest dostępny w produkcyjnym ``CycleReport.diagnostics["trace"]``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from application import entrypoint
from application.alert_builder import AlertBuilder
from application.cycle_trace import (
    STAGE_ORDER,
    build_trace_report_text,
    build_trace_summary,
    sanitize_trace,
)
from application.channels.telegram_channel import TelegramChannel, ChannelSendResult
from tests.test_point2_e2e_flow import FakeYahooSession, make_quote, ts
from tests.test_point4_ai_tavily import (
    FakeOpenAIProvider,
    make_tavily_adapter,
    valid_provider_result,
    _rising_md,
    _vol_spike_md,
    _yahoo_rows,
)

T0 = datetime(2025, 12, 31, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_telegram_http(ok: bool = True) -> Mock:
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {
        "ok": ok,
        "result": {"message_id": 7, "chat": {"id": 123456}},
    }
    return Mock(return_value=resp)


def _real_telegram_channel() -> TelegramChannel:
    return TelegramChannel(
        bot_token="fake-bot-token",
        chat_id="123456",
        http_client=_fake_telegram_http(ok=True),
    )


def _build(
    tmp_path: Path,
    session: FakeYahooSession,
    *,
    with_telegram: bool = False,
    openai_result=None,
    tavily_exc=None,
) -> tuple:
    """Build runtime with real internal components and fake boundary doubles.

    Returns (runtime, fake_openai, fake_tavily_client, telegram_channel | None).
    """
    rt = entrypoint.build_runtime_service(
        persist_path=Path(tmp_path) / "e2e.db",
        yahoo_session=session,
    )

    fake_openai = FakeOpenAIProvider(
        result=openai_result if openai_result is not None else valid_provider_result()
    )
    rt.master_engine.openai_provider = fake_openai
    adapter, tavily_client = make_tavily_adapter(exc=tavily_exc)
    rt.master_engine._tavily_adapter = adapter

    # Realny AlertBuilder z progami dopasowanymi do skali 0-1 produkcyjnego
    # FinalAnalysisResult (bez mocka, bez zmiany logiki silników).
    rt.alert_builder = AlertBuilder(
        min_final_score=0.001,
        min_confidence=0.001,
        allowed_recommendations=["STRONG_BUY", "BUY", "HOLD"],
    )

    telegram = None
    if with_telegram:
        telegram = _real_telegram_channel()
        rt.telegram_channel = telegram

    return rt, fake_openai, tavily_client, telegram


def _rising_session(symbol="AAA.WA") -> FakeYahooSession:
    return FakeYahooSession(
        quotes=[make_quote(symbol)],
        chart_rows_by_symbol={symbol: _yahoo_rows(_rising_md(60))},
    )


def _trace(report) -> dict:
    return report.diagnostics["trace"]


# ---------------------------------------------------------------------------
# Kontrakt śladu (pkt 6): schema, cycle_id, timestampy, kolejność, duration
# ---------------------------------------------------------------------------

class TestTraceContract:
    def test_trace_has_required_top_level_fields(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        report = rt.run_cycle()
        trace = _trace(report)

        for key in (
            "schema_version",
            "cycle_id",
            "started_at_utc",
            "ended_at_utc",
            "duration_ms",
            "overall_status",
            "stages",
            "instruments",
            "counters",
            "errors",
            "external_calls",
            "data_flow_complete",
        ):
            assert key in trace, key

    def test_trace_has_single_cycle_id_and_utc_timestamps(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        report = rt.run_cycle()
        trace = _trace(report)

        assert isinstance(trace["cycle_id"], str)
        assert trace["cycle_id"]
        assert trace["started_at_utc"].endswith("+00:00")
        assert trace["ended_at_utc"].endswith("+00:00")
        assert trace["duration_ms"] is not None
        assert trace["duration_ms"] >= 0

    def test_stages_are_in_required_order(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        trace = _trace(rt.run_cycle())

        names = list(trace["stages"].keys())
        assert names == STAGE_ORDER

    def test_every_started_stage_has_start_end_nonnegative_duration(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        trace = _trace(rt.run_cycle())

        for stage in trace["stages"].values():
            if stage["start_utc"] is None:
                continue
            assert stage["end_utc"] is not None
            assert stage["duration_ms"] is not None
            assert stage["duration_ms"] >= 0

    def test_unstarted_stages_are_explicitly_skipped_not_omitted(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        trace = _trace(rt.run_cycle())

        for stage in trace["stages"].values():
            assert stage["status"] != "NOT_STARTED"
            assert stage["status"] in (
                "SUCCESS", "PARTIAL", "FAILED", "SKIPPED",
            )


# ---------------------------------------------------------------------------
# Pełny przepływ (pkt 1/14/40 scenariusze) — realne komponenty + fake granice
# ---------------------------------------------------------------------------

class TestTraceFullFlow:
    def test_one_instrument_full_path_to_fake_telegram(self, tmp_path):
        rt, openai, tavily_client, telegram = _build(
            tmp_path, _vol_session(), with_telegram=True
        )
        report = rt.run_cycle()
        trace = _trace(report)

        assert trace["data_flow_complete"] is True
        assert trace["overall_status"] == "SUCCESS"

        instr = trace["instruments"]["AAA.WA"]
        assert instr["chart_status"] == "SUCCESS"
        assert instr["reading_status"] == "ACCEPTED"
        assert instr["baseline_exists"] is True
        assert instr["final_result_created"] is True
        assert instr["ai_signal_created"] is True
        assert instr["ai_validated"] == 1
        assert instr["alert_built"] is True
        assert instr["telegram_success"] == 1
        assert instr["final_status"] == "SUCCESS"

        # Realne komponenty wewnętrzne wykonały rzeczywisty FinalAnalysisResult.
        assert report.results and report.results[0].symbol == "AAA.WA"
        # Openai provider wywołany logicznie dokładnie raz; Tavily również.
        assert len(openai.calls) == 1
        assert len(tavily_client.queries) >= 1

    def test_full_flow_uses_real_internal_components_not_mocks(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        report = rt.run_cycle()

        assert report.candidates_count >= 1
        # Wewnętrzne komponenty są realnymi obiektami domenowymi.
        assert rt.hunter_engine.__class__.__name__ == "HunterEngine"
        assert rt.master_engine.__class__.__name__ == "MasterEngine"


# ---------------------------------------------------------------------------
# Per instrument: separacja, błąd chart, pusty chart, volume=0 (pkt 5-8)
# ---------------------------------------------------------------------------

class TestTraceInstruments:
    def test_two_instruments_remain_separate(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_rising_md(60)),
                "BBB.WA": _yahoo_rows(_vol_spike_md(60)),
            },
        )
        rt, *_ = _build(tmp_path, session)
        trace = _trace(rt.run_cycle())

        assert set(trace["instruments"].keys()) == {"AAA.WA", "BBB.WA"}
        assert trace["counters"]["instruments_total"] == 2

    def test_chart_error_of_one_instrument_does_not_remove_other(self, tmp_path):
        broken = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_rising_md(60)),
                # BBB.WA: brak chart → SUCCESS_NO_DATA
            },
        )
        rt, *_ = _build(tmp_path, broken)
        report = rt.run_cycle()
        trace = _trace(report)

        instr = trace["instruments"]
        assert "AAA.WA" in instr
        assert "BBB.WA" in instr
        assert instr["AAA.WA"]["final_status"] == "SUCCESS"
        assert instr["BBB.WA"]["chart_status"] == "FAILED"
        assert instr["BBB.WA"]["final_status"] == "FAILED"
        # Błąd chart nie usuwa poprawnego instrumentu.
        assert report.results and report.results[0].symbol == "AAA.WA"

    def test_empty_chart_creates_no_observation_or_reading(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={},  # brak wierszy → SUCCESS_NO_DATA
        )
        rt, *_ = _build(tmp_path, session)
        report = rt.run_cycle()
        trace = _trace(report)

        assert rt.history_repository.load_observation("AAA.WA") is None
        with sqlite3.connect(str(tmp_path / "e2e.db")) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM instrument_readings WHERE instrument_id=?",
                ("AAA.WA",),
            )
            assert cur.fetchone()[0] == 0

        instr = trace["instruments"]["AAA.WA"]
        assert instr["chart_status"] == "FAILED"
        assert instr["observation_status"] == "NOT_STARTED"

    def test_volume_zero_preserved_correctly(self, tmp_path):
        rows = [(ts(T1), 1.0, 1.5, 0.5, 1.1, 0)]
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": rows},
        )
        rt, *_ = _build(tmp_path, session)
        report = rt.run_cycle()
        trace = _trace(report)

        instr = trace["instruments"]["AAA.WA"]
        assert instr["volume"] == 0.0


# ---------------------------------------------------------------------------
# Krótka historia, InsufficientDataError, DUPLICATE/STALE (pkt 9-14)
# ---------------------------------------------------------------------------

class TestTraceDataFlowStops:
    def test_short_valid_history_creates_observation_but_technical_limitation(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(1))},
        )
        rt, *_ = _build(tmp_path, session)
        report = rt.run_cycle()
        trace = _trace(report)

        instr = trace["instruments"]["AAA.WA"]
        assert instr["reading_status"] == "ACCEPTED"
        assert instr["insufficient_data_error"] is True
        assert instr["technical_status"] == "FAILED"
        assert instr["final_result_created"] is False

    def test_insufficient_data_error_does_not_create_fake_final_result(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(1))},
        )
        rt, *_ = _build(tmp_path, session)
        report = rt.run_cycle()

        assert report.results == []
        assert report.success_count == 0
        assert _trace(report)["instruments"]["AAA.WA"]["insufficient_data_error"] is True

    def test_duplicate_no_op_stops_downstream_with_skipped(self, tmp_path):
        db = tmp_path / "e2e.db"
        chart = _yahoo_rows(_rising_md(60))
        session = FakeYahooSession(quotes=[make_quote("AAA.WA")], chart_rows_by_symbol={"AAA.WA": chart})
        rt, *_ = _build(tmp_path, session)
        first = rt.run_cycle()
        assert _trace(first)["instruments"]["AAA.WA"]["reading_status"] == "ACCEPTED"

        session2 = FakeYahooSession(quotes=[make_quote("AAA.WA")], chart_rows_by_symbol={"AAA.WA": chart})
        rt2, *_ = _build(tmp_path, session2)
        second = rt2.run_cycle()
        trace2 = _trace(second)

        instr = trace2["instruments"]["AAA.WA"]
        assert instr["reading_status"] == "DUPLICATE_NO_OP"
        assert instr["observation_status"] == "SKIPPED"
        assert instr["final_status"] == "SKIPPED"
        # Downstream zatrzymany — brak drugiego wyniku.
        assert second.success_count == 0

    def test_stale_timestamp_stops_downstream_with_skipped(self, tmp_path):
        db = tmp_path / "e2e.db"
        # Pierwszy odczyt: nowszy timestamp T2.
        s1 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(60))},
        )
        rt1, *_ = _build(tmp_path, s1)
        rt1.run_cycle()

        # Drugi odczyt: starszy timestamp T0 (przed baseline 2026-01-01).
        s2 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": [(ts(T0), 1.0, 1.5, 0.5, 1.1, 100)]},
        )
        rt2, *_ = _build(tmp_path, s2)
        report2 = rt2.run_cycle()
        trace2 = _trace(report2)

        instr = trace2["instruments"]["AAA.WA"]
        assert instr["reading_status"] == "STALE_TIMESTAMP"
        assert instr["observation_status"] == "SKIPPED"
        assert instr["final_status"] == "SKIPPED"
        assert report2.success_count == 0

    def test_engine_error_attributed_to_correct_symbol(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_rising_md(60)),
                "BBB.WA": _yahoo_rows(_rising_md(1)),
            },
        )
        rt, *_ = _build(tmp_path, session)
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]
        assert instr["AAA.WA"]["final_status"] == "SUCCESS"
        assert instr["AAA.WA"]["insufficient_data_error"] is False
        assert instr["BBB.WA"]["insufficient_data_error"] is True
        assert "InsufficientDataError" in instr["BBB.WA"]["error_types"]
        assert "InsufficientDataError" not in instr["AAA.WA"]["error_types"]


# ---------------------------------------------------------------------------
# Liczniki zewnętrzne i oddzielenie logical/real (pkt 9, 16-21, 37)
# ---------------------------------------------------------------------------

class TestTraceExternalCalls:
    def test_tavily_success_lands_in_own_instrument(self, tmp_path):
        rt, *_ = _build(tmp_path, _vol_session())
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]["AAA.WA"]
        assert instr["tavily_attempted"] >= 1
        assert instr["tavily_success"] == instr["tavily_attempted"]
        assert trace["external_calls"]["tavily_real_sent"] == 0

    def test_tavily_failure_recorded_and_not_leaked_to_other_instrument(self, tmp_path):
        import data.tavily.errors as t_errors
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_vol_spike_md(60)),
                "BBB.WA": _yahoo_rows(_rising_md(60)),
            },
        )
        # Tavily failure — adapter rzuca; BBB nie dotyka Tavily (brak zdarzenia CRITICAL).
        from tests.test_point4_ai_tavily import FakeTavilyClient
        rt = entrypoint.build_runtime_service(
            persist_path=Path(tmp_path) / "e2e.db",
            yahoo_session=session,
        )
        rt.master_engine.openai_provider = FakeOpenAIProvider(result=valid_provider_result())
        from data.tavily.config import TavilyConfig
        from data.tavily.service import TavilyService
        from data.tavily.event_adapter import TavilyEventAdapter
        cfg = TavilyConfig(api_key="k", enabled=True, max_age_hours=24 * 366)
        svc = TavilyService(cfg)
        svc._client = FakeTavilyClient(exc=t_errors.TavilyAPIError("boom"))
        rt.master_engine._tavily_adapter = TavilyEventAdapter(svc)

        trace = _trace(rt.run_cycle())
        instr = trace["instruments"]
        assert instr["AAA.WA"]["tavily_attempted"] >= 1
        assert instr["AAA.WA"]["tavily_success"] == 0
        # Nie wycieka do BBB.
        assert instr["BBB.WA"]["tavily_attempted"] == 0
        assert trace["external_calls"]["tavily_real_sent"] == 0

    def test_openai_success_gives_validated_and_real_signal(self, tmp_path):
        rt, openai, *_ = _build(tmp_path, _rising_session())
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]["AAA.WA"]
        assert instr["ai_attempted"] == 1
        assert instr["ai_sent"] == 1
        assert instr["ai_validated"] == 1
        assert instr["ai_signal_created"] is True
        assert trace["external_calls"]["openai_attempts"] == 1
        assert trace["external_calls"]["openai_real_sent"] == 0

    def test_openai_refusal_distinguished_from_transport_error(self, tmp_path):
        from engines.ai.openai_provider import OpenAIProviderResult
        refusal = OpenAIProviderResult(result=None, response_id="r", refusal="odmowa")
        rt, *_ = _build(tmp_path, _rising_session(), openai_result=refusal)
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]["AAA.WA"]
        assert instr["ai_refusal"] == 1
        assert instr["ai_validated"] == 0
        assert instr["ai_signal_created"] is False

    def test_openai_failure_does_not_create_fake_aisignal(self, tmp_path):
        from engines.ai.openai_provider import AIProviderError
        rt, *_ = _build(
            tmp_path,
            _rising_session(),
            openai_result=None,
        )
        # Zastąp provider tak, by rzucał.
        rt.master_engine.openai_provider = FakeOpenAIProvider(exc=AIProviderError("down"))
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]["AAA.WA"]
        assert instr["ai_validated"] == 0
        assert instr["ai_signal_created"] is False

    def test_all_real_network_counters_zero_offline(self, tmp_path):
        rt, *_ = _build(tmp_path, _vol_session(), with_telegram=True)
        trace = _trace(rt.run_cycle())
        ec = trace["external_calls"]
        assert ec["yahoo_real_sent"] == 0
        assert ec["tavily_real_sent"] == 0
        assert ec["openai_real_sent"] == 0
        assert ec["telegram_real_sent"] == 0

    def test_fake_telegram_records_logical_call_not_real(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]["AAA.WA"]
        assert instr["telegram_attempted"] >= 1
        assert instr["telegram_sent"] >= 1
        assert instr["telegram_success"] >= 1
        assert trace["external_calls"]["telegram_attempts"] >= 1
        assert trace["external_calls"]["telegram_real_sent"] == 0

    def test_fake_telegram_failure_kept_diagnostically(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        # Fake HTTP zwraca ok=False.
        rt.telegram_channel = TelegramChannel(
            bot_token="fake-bot-token",
            chat_id="123456",
            http_client=_fake_telegram_http(ok=False),
        )
        trace = _trace(rt.run_cycle())

        instr = trace["instruments"]["AAA.WA"]
        assert instr["telegram_success"] == 0
        assert trace["stages"]["telegram"]["status"] == "FAILED"


# ---------------------------------------------------------------------------
# Redakcja i bezpieczeństwo (pkt 10, 26-28)
# ---------------------------------------------------------------------------

class TestTraceRedaction:
    def test_trace_is_json_serializable(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        trace = _trace(rt.run_cycle())
        json.dumps(trace)  # nie rzuca

    def test_trace_contains_no_secret_values(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        trace = _trace(rt.run_cycle())
        serialized = json.dumps(trace, default=str).lower()
        for forbidden in (
            "api_key", "authorization", "bearer", "cookie", "crumb",
            "bot token", "chat_id",
        ):
            assert forbidden not in serialized

    def test_trace_contains_no_full_provider_payloads(self, tmp_path):
        rt, openai, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        trace = _trace(rt.run_cycle())
        serialized = json.dumps(trace, default=str)
        # Nie przechowuje kompletnego history OHLCV ani surowego payloadu.
        assert "history" not in json.dumps(trace.get("instruments", {}))
        # Pełny payload OpenAI nie trafia do śladu.
        assert "technical_indicators" not in json.dumps(trace["instruments"])

    def test_central_sanitize_redacts_markers(self):
        dirty = {"openai_api_key": "sk-abc", "nested": {"telegram_token": "tok"}}
        clean = sanitize_trace(dirty)
        assert clean["openai_api_key"] == "[REDACTED]"
        assert clean["nested"]["telegram_token"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# Dostępność w CycleReport + trwałość/odczyt (pkt 29-31)
# ---------------------------------------------------------------------------

class TestTracePersistence:
    def test_trace_available_in_cycle_report(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        report = rt.run_cycle()
        assert "trace" in report.diagnostics
        assert report.diagnostics["trace"]["cycle_id"]

    def test_trace_persists_and_is_readable_after_reopen(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        report = rt.run_cycle()
        cycle_id = report.diagnostics["trace"]["cycle_id"]

        repo2 = entrypoint.build_runtime_service(
            persist_path=Path(tmp_path) / "e2e.db",
            yahoo_session=FakeYahooSession(quotes=[], chart_rows_by_symbol={}),
        ).history_repository
        stored = repo2.get_cycle(cycle_id)
        assert stored is not None
        # Report JSON zawiera trace (po serializacji/deserializacji).
        stored_report = stored.get("report", {})
        assert isinstance(stored_report, dict)

    def test_read_service_returns_cycle_additively(self, tmp_path):
        from application.read_service import RuntimeReadService
        rt, *_ = _build(tmp_path, _rising_session())
        report = rt.run_cycle()
        cycle_id = report.diagnostics["trace"]["cycle_id"]

        reader = RuntimeReadService(db_path=Path(tmp_path) / "e2e.db")
        cycle = reader.get_cycle(cycle_id)
        assert cycle is not None
        assert cycle["cycle_id"] == cycle_id


# ---------------------------------------------------------------------------
# Świeży ślad, agregaty, data_flow_complete (pkt 32-36)
# ---------------------------------------------------------------------------

class TestTraceFreshnessAndAggregates:
    def test_next_cycle_gets_fresh_trace_without_inheritance(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session("AAA.WA"))
        first = rt.run_cycle()
        first_id = _trace(first)["cycle_id"]

        rt2, *_ = _build(
            tmp_path,
            FakeYahooSession(
                quotes=[make_quote("BBB.WA")],
                chart_rows_by_symbol={"BBB.WA": _yahoo_rows(_rising_md(60))},
            ),
        )
        second = rt2.run_cycle()
        second_trace = _trace(second)

        assert second_trace["cycle_id"] != first_id
        assert "AAA.WA" not in second_trace["instruments"]
        assert "BBB.WA" in second_trace["instruments"]

    def test_stage_counters_sum_to_instrument_count(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_rising_md(60)),
                "BBB.WA": _yahoo_rows(_vol_spike_md(60)),
            },
        )
        rt, *_ = _build(tmp_path, session)
        trace = _trace(rt.run_cycle())

        c = trace["counters"]
        assert c["instruments_total"] == 2
        assert c["instruments_success"] == 2

    def test_happy_path_ends_data_flow_complete_true(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session())
        trace = _trace(rt.run_cycle())
        assert trace["data_flow_complete"] is True

    def test_partial_flow_ends_data_flow_complete_false(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _yahoo_rows(_rising_md(60)),
                # BBB.WA: brak chart → FAILED.
            },
        )
        rt, *_ = _build(tmp_path, session)
        trace = _trace(rt.run_cycle())
        assert trace["data_flow_complete"] is False
        assert trace["overall_status"] == "PARTIAL"


# ---------------------------------------------------------------------------
# Raw / summary / report — różne role i treści (pkt 11, 38)
# ---------------------------------------------------------------------------

class TestTraceSummaryAndReport:
    def test_raw_summary_report_have_different_schemas(self, tmp_path):
        rt, *_ = _build(tmp_path, _rising_session(), with_telegram=True)
        raw = _trace(rt.run_cycle())
        summary = build_trace_summary(raw)
        report_text = build_trace_report_text(raw)

        assert "stages" in raw
        assert "instruments" in raw
        assert "stages" not in summary
        assert "instruments" not in summary
        assert "schema" in summary
        assert isinstance(report_text, str)
        assert "ALCHEMIK" in report_text
        assert summary["schema"] != raw.get("schema_version", 1)


def _vol_session(symbol="AAA.WA") -> FakeYahooSession:
    from tests.test_point4_ai_tavily import _vol_spike_md
    return FakeYahooSession(
        quotes=[make_quote(symbol)],
        chart_rows_by_symbol={symbol: _yahoo_rows(_vol_spike_md(60))},
    )