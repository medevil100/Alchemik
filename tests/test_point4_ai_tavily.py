"""
Point 4/7 — rzeczywiste AI i Tavily (testy offline).

Przepływ testowany na prawdziwych modułach wewnętrznych:

    TechnicalEngine → detektory → Composer → Quality → DecisionEngine
    → Tavily (realny adapter + realny service, fake wyłącznie transportu
      TavilyClient) → GPT-4o boundary (fake zamiast transportu OpenAI)
    → walidowany AISignal → Ranking → Risk → Hunter → Analyst
    → końcowy wynik domenowy.

Test doubles wyłącznie na granicach systemu:
    - ``FakeYahooSession``     — zamiast transportu Yahoo (dla testów Runtime),
    - ``FakeTavilyClient``     — zamiast HTTP transportu Tavily API,
    - ``FakeOpenAIProvider``    — zamiast HTTP transportu OpenAI API.

Prawdziwy ``TavilyEventAdapter``, prawdziwy ``TavilyService``, prawdziwe
silniki i prawdziwy ``MasterEngine``. Żaden wewnętrzny komponent ALCHEMIKA
nie jest mockowany.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from application import entrypoint
from data.models import MarketData
from data.models.ai_signal import AISignal
from data.tavily.config import TavilyConfig
from data.tavily.errors import TavilyAPIError
from data.tavily.event_adapter import TavilyEventAdapter
from data.tavily.service import TavilyService
from engines.ai import DecisionEngine
from engines.ai.openai_provider import (
    AIAnalysisResult,
    AIProviderError,
    OpenAIProvider,
    OpenAIProviderResult,
)
from engines.analyst import AnalystEngine
from engines.hunter import HunterEngine
from engines.master.engine import MasterEngine
from engines.news import NewsPipeline
from engines.news.filter import NewsFilterConfig
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.technical import TechnicalEngine
from engines.technical.errors import InsufficientDataError
from tests.test_point2_e2e_flow import FakeYahooSession, make_quote


# ---------------------------------------------------------------------------
# Deterministic fixtures (no network)
# ---------------------------------------------------------------------------

HUNTER_CONFIG = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.5,
    "max_risk_score": 0.7,
    "min_confidence": 0.6,
    "max_results": 10,
    "priority_thresholds": [0.9, 0.7, 0.5],
}

FAKE_TAVILY_RESULTS = [
    {
        "title": "Spółka AAA raportuje mocny wzrost",
        "url": "https://example.com/aaa-growth",
        "content": "Treść wiadomości o spółce AAA i jej wzroście.",
        "score": 0.92,
        "published_date": "2026-03-01T00:00:00Z",
    }
]


def _rising_md(n: int = 60) -> list:
    """Rosnąca seria: ATH/RSI_DIVERGENCE/COMPOSITE → quality HIGH (run_ai)."""
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


def _vol_spike_md(n: int = 60) -> list:
    """Seria z pikiem zmienności: VOLATILITY_SPIKE → quality CRITICAL (run_tavily)."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    out = []
    for d in range(n):
        rng = 0.3 if d < n - 6 else 8.0
        out.append(
            MarketData(
                open=100.0 + d * 0.05,
                high=100.0 + d * 0.05 + rng,
                low=100.0 + d * 0.05 - rng,
                close=100.1 + d * 0.05,
                volume=500000.0,
                timestamp=base + timedelta(days=d),
            )
        )
    return out


def _yahoo_rows(md_list: list) -> list:
    """Convert MarketData list to Yahoo chart row tuples (ts, o, h, l, c, v)."""
    return [
        (int(m.timestamp.timestamp()), m.open, m.high, m.low, m.close, m.volume)
        for m in md_list
    ]


class FakeTavilyClient:
    """Test double wyłącznie dla transportu HTTP Tavily API."""

    def __init__(self, results=None, exc=None):
        self.results = results if results is not None else FAKE_TAVILY_RESULTS
        self.exc = exc
        self.queries = []

    def search(self, request):
        self.queries.append(request.query)
        if self.exc is not None:
            raise self.exc
        return {"results": self.results}


class FakeOpenAIProvider:
    """Test double wyłącznie dla transportu HTTP OpenAI API."""

    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    def analyze(self, payload):
        self.calls.append(payload)
        if self.exc is not None:
            raise self.exc
        return self.result


def valid_provider_result(confidence: float = 0.8) -> OpenAIProviderResult:
    return OpenAIProviderResult(
        result=AIAnalysisResult(
            facts=["Cena akcji rośnie w oknie obserwacji"],
            hypotheses=["Możliwa kontynuacja trendu"],
            alternatives=["Możliwa korekta techniczna"],
            risks=["Podwyższona zmienność"],
            data_limitations=["Brak danych fundamentalnych"],
            justification="Wzrost potwierdzony danymi OHLCV i wskaźnikami",
            confidence=confidence,
        ),
        response_id="resp_test_123",
        request_id="req_test_456",
    )


def make_tavily_adapter(results=None, exc=None) -> TavilyEventAdapter:
    config = TavilyConfig(
        api_key="test-tavily-key-not-a-secret",
        enabled=True,
        # Szerokie okno deterministyczne: fixture używa ustalonej daty,
        # a event timestamp_utc pochodzi z czasu detekcji (wall-clock).
        max_age_hours=24 * 366,
    )
    service = TavilyService(config)
    service._client = FakeTavilyClient(results=results, exc=exc)
    return TavilyEventAdapter(service), service._client


def make_master(tavily_adapter=None, openai_provider=None) -> MasterEngine:
    return MasterEngine(
        technical_engine=TechnicalEngine(),
        news_engine=NewsPipeline(
            NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        ),
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
        hunter_engine=HunterEngine(HUNTER_CONFIG),
        analyst_engine=AnalystEngine(),
        tavily_adapter=tavily_adapter,
        openai_provider=openai_provider,
    )


def run_events(master, symbol="AAA.WA", md=None):
    """Run analysis and return (result, events)."""
    events = []
    result = master.run_analysis(symbol, events_out=events, ohlcv_data=md)
    return result, events


# ---------------------------------------------------------------------------
# 1/2/11 — Tavily: dokładnie raz, trafia do kontekstu, błąd bez wymyślania
# ---------------------------------------------------------------------------

class TestPoint4Tavily:
    def test_qualified_event_invokes_tavily_exactly_once(self):
        adapter, client = make_tavily_adapter()
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(tavily_adapter=adapter, openai_provider=provider)

        _, events = run_events(master, md=_vol_spike_md())

        qualified = [
            ev for ev in events
            if master.ai_engine.decide_pipeline(ev).run_tavily
        ]
        assert len(qualified) >= 1

        # Dokładnie jedno wywołanie transportu Tavily na zakwalifikowane zdarzenie.
        assert len(client.queries) == len(qualified)
        assert len(set(client.queries)) == len(client.queries), (
            "brak duplikatów zapytań Tavily"
        )

    def test_tavily_result_lands_in_own_instrument_context(self):
        adapter, client = make_tavily_adapter()
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(tavily_adapter=adapter, openai_provider=provider)

        _, events = run_events(master, symbol="AAA.WA", md=_vol_spike_md())

        tavily_events = [
            ev for ev in events
            if master.ai_engine.decide_pipeline(ev).run_tavily
        ]
        assert tavily_events
        for ev in tavily_events:
            assert ev.tavily_context is not None
            assert "AAA.WA" in ev.tavily_context["query"]
            assert ev.tavily_context["results_count"] == 1
            assert len(ev.tavily_context["top_results"]) == 1
            assert ev.tavily_context["top_results"][0]["url"] == (
                "https://example.com/aaa-growth"
            )

    def test_tavily_error_does_not_fabricate_news(self):
        adapter, _ = make_tavily_adapter(exc=TavilyAPIError("boom"))
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(tavily_adapter=adapter, openai_provider=provider)

        result, events = run_events(master, md=_vol_spike_md())

        # Błąd Tavily nie usuwa domenowego wyniku silników.
        assert result is not None
        assert result.symbol == "AAA.WA"
        # Brak wymyślonego kontekstu wiadomości ani Tavily.
        for ev in events:
            assert ev.tavily_context is None
            assert ev.news_context is None


# ---------------------------------------------------------------------------
# 3/6/7/8/9/10/13 — AI: dokładnie raz, schemat, refusal, błąd, non-CRITICAL
# ---------------------------------------------------------------------------

class TestPoint4AI:
    def test_qualified_event_invokes_ai_exactly_once(self):
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(openai_provider=provider)

        run_events(master, md=_rising_md())

        assert len(provider.calls) == 1

    def test_valid_result_creates_correct_aisignal(self):
        provider = FakeOpenAIProvider(result=valid_provider_result(confidence=0.8))
        master = make_master(openai_provider=provider)

        result, events = run_events(master, md=_rising_md())

        # Placeholder confidence=0.0 nie jest używany po poprawnym wyniku.
        assert result.confidence_level == 0.8
        ai_contexts = [
            ev for ev in events if ev.ai_context and "response_id" in ev.ai_context
        ]
        assert ai_contexts
        assert ai_contexts[0].ai_context["confidence"] == 0.8
        assert ai_contexts[0].ai_context["response_id"] == "resp_test_123"

    def test_ai_runs_for_all_qualified_not_only_critical(self):
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(openai_provider=provider)

        _, events = run_events(master, md=_rising_md())

        # Seria rosnąca nie ma zdarzenia CRITICAL, a AI i tak się uruchamia.
        qualities = {
            getattr(ev.quality_level, "value", str(ev.quality_level))
            for ev in events
        }
        assert "CRITICAL" not in qualities
        assert len(provider.calls) == 1

    def test_openai_error_keeps_domain_engine_result(self):
        provider = FakeOpenAIProvider(exc=AIProviderError("provider down"))
        master = make_master(openai_provider=provider)

        result, events = run_events(master, md=_rising_md())

        # Domenowy wynik silników nadal istnieje (nie Exception).
        assert result is not None
        assert result.symbol == "AAA.WA"
        assert result.confidence_level == 0.0
        # Błąd zapisany jawnie, nie jako sukces.
        assert any(
            ev.ai_context and ev.ai_context.get("confidence") == 0.0
            for ev in events
        )

    def test_placeholder_not_used_after_valid_provider_result(self):
        provider = FakeOpenAIProvider(result=valid_provider_result(confidence=0.65))
        master = make_master(openai_provider=provider)

        result, events = run_events(master, md=_rising_md())

        assert result.confidence_level == 0.65
        assert result.confidence_level != 0.0


class TestProviderResultMapping:
    """Bezpośredni kontrakt mapowania wyniku providera na AISignal."""

    def test_valid_schema_creates_combined_aisignal(self):
        signal = MasterEngine._provider_result_to_aisignal(
            valid_provider_result(confidence=0.7)
        )
        assert isinstance(signal, AISignal)
        assert signal.signal_type == "combined_analysis"
        assert signal.confidence == 0.7
        assert "Fakty" in signal.reasoning

    def test_schema_incompatible_does_not_create_fake_success(self):
        signal = MasterEngine._provider_result_to_aisignal(
            OpenAIProviderResult(
                result=None,
                response_id="resp_none",
                request_id=None,
                refusal=None,
            )
        )
        assert signal.signal_type == "ai_error"
        assert signal.confidence == 0.0

    def test_refusal_is_preserved_explicitly(self):
        signal = MasterEngine._provider_result_to_aisignal(
            OpenAIProviderResult(
                result=None,
                response_id="resp_refusal",
                request_id=None,
                refusal="Model odmówił analizy",
            )
        )
        assert signal.signal_type == "refusal"
        assert signal.confidence == 0.0
        assert "Model odmówił analizy" in signal.reasoning


# ---------------------------------------------------------------------------
# 4/5/16 — payload AI: komplet danych, brak innego symbolu, brak sekretów
# ---------------------------------------------------------------------------

class TestPoint4Payload:
    def test_payload_contains_full_instrument_engine_data(self):
        adapter, _ = make_tavily_adapter()
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(tavily_adapter=adapter, openai_provider=provider)

        run_events(master, symbol="AAA.WA", md=_vol_spike_md())

        payload = provider.calls[0]
        assert payload["symbol"] == "AAA.WA"
        assert payload["market"] == "UNKNOWN"
        assert isinstance(payload["current_price"], float)
        assert isinstance(payload["volume"], float)
        assert payload["data_timestamp"] is not None
        assert payload["baseline_close"] is not None
        assert payload["change_vs_baseline_pct"] is not None
        assert len(payload["history"]) >= 34
        assert payload["technical_indicators"] != {}
        assert payload["detected_events"] is not []
        assert payload["data_completeness"] == "COMPLETE"

        for ev in payload["detected_events"]:
            assert ev["quality_level"] in {
                "LOW", "MEDIUM", "HIGH", "CRITICAL", "IGNORE"
            }
            assert "pipeline_decision" in ev
            assert "price_data" in ev
            assert "volume_data" in ev

        # Kontekst Tavily jest obecny w wykrytym zdarzeniu CRITICAL.
        critical_events = [
            ev for ev in payload["detected_events"]
            if ev["quality_level"] == "CRITICAL"
        ]
        assert critical_events
        assert any(ev["tavily_context"] is not None for ev in critical_events)

    def test_payload_does_not_contain_other_symbol(self):
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(openai_provider=provider)

        run_events(master, symbol="AAA.WA", md=_rising_md())

        payload = provider.calls[0]
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        assert "BBB.WA" not in serialized

    def test_no_secret_in_payload(self):
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(openai_provider=provider)

        run_events(master, symbol="AAA.WA", md=_rising_md())

        payload = provider.calls[0]
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        for forbidden in ("api_key", "Authorization", "Bearer", "sk-", "tvly-"):
            assert forbidden not in serialized

    def test_zero_volume_is_preserved(self):
        """volume=0 to poprawna wartość danych i musi trafić do payloadu."""
        from data.models.analysis_result import AnalysisResult

        latest = MarketData(
            open=10.0, high=11.0, low=9.0, close=10.5,
            volume=0.0, timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        technical_result = AnalysisResult(
            company=None, market_data=[latest], news=[], signals=[],
            generated_at=datetime.now(timezone.utc),
        )
        technical_result.indicators = {}

        payload = MasterEngine._build_ai_payload(
            symbol="AAA.WA",
            market="GPW",
            instrument_type=__import__(
                "data.models.event_enums", fromlist=["InstrumentType"]
            ).InstrumentType.STOCK_GPW,
            technical_result=technical_result,
            market_events=[],
            decisions_map={},
        )
        assert payload["volume"] == 0.0


# ---------------------------------------------------------------------------
# 12 — dwa instrumenty zachowują oddzielny kontekst
# ---------------------------------------------------------------------------

class TestPoint4Isolation:
    def test_two_instruments_keep_separate_ai_context(self):
        adapter, _ = make_tavily_adapter()
        provider = FakeOpenAIProvider(result=valid_provider_result())
        master = make_master(tavily_adapter=adapter, openai_provider=provider)

        events_aaa = []
        master.run_analysis("AAA.WA", events_out=events_aaa, ohlcv_data=_vol_spike_md())

        events_bbb = []
        master.run_analysis(
            "BBB.WA", events_out=events_bbb,
            ohlcv_data=_vol_spike_md(),
        )

        assert len(provider.calls) == 2
        serialized_aaa = json.dumps(provider.calls[0], default=str)
        serialized_bbb = json.dumps(provider.calls[1], default=str)
        assert "BBB.WA" not in serialized_aaa
        assert "AAA.WA" not in serialized_bbb


# ---------------------------------------------------------------------------
# 14/15/18 — Runtime: niezmieniony odczyt, krótka historia, brak Telegrama
# ---------------------------------------------------------------------------

class TestPoint4Runtime:
    def _build_with_fakes(self, tmp_path, session, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        rt = entrypoint.build_runtime_service(
            persist_path=Path(tmp_path) / "e2e.db",
            yahoo_session=session,
        )
        assert rt.telegram_channel is None  # Telegram wyłączony (18)
        rt.master_engine.openai_provider = FakeOpenAIProvider(
            result=valid_provider_result()
        )
        rt.master_engine._tavily_adapter, _ = make_tavily_adapter()
        return rt

    def test_unchanged_reading_does_not_reach_ai(self, tmp_path, monkeypatch):
        rows = _yahoo_rows(_rising_md())
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": rows},
        )
        rt = self._build_with_fakes(tmp_path, session, monkeypatch)

        first = rt.run_cycle()
        assert first.success_count == 1
        assert len(rt.master_engine.openai_provider.calls) == 1

        second_session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": rows},
        )
        rt2 = self._build_with_fakes(tmp_path, second_session, monkeypatch)
        second = rt2.run_cycle()

        assert second.success_count == 0
        assert second.results == []
        assert len(rt2.master_engine.openai_provider.calls) == 0

    def test_very_short_history_no_fake_result_or_ai(self, tmp_path, monkeypatch):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md(1))},
        )
        rt = self._build_with_fakes(tmp_path, session, monkeypatch)
        report = rt.run_cycle()

        assert report.success_count == 0
        assert report.results == []
        assert any("data points" in e.message for e in report.errors)
        assert len(rt.master_engine.openai_provider.calls) == 0
        assert len(rt.master_engine._tavily_adapter._service._client.queries) == 0


# ---------------------------------------------------------------------------
# 17 — composition root buduje rzeczywisty OpenAI provider i Tavily adapter
# ---------------------------------------------------------------------------

class TestPoint4Composition:
    def test_composition_root_builds_real_provider_and_adapter(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key-not-a-secret")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        monkeypatch.setenv("OPENAI_TIMEOUT", "30")
        monkeypatch.setenv("TAVILY_API_KEY", "fake-tavily-key-not-a-secret")
        monkeypatch.setenv("TAVILY_ENABLED", "True")
        # Izolacja od stanu środowiska pozostawionego przez inne testy
        # (test_tavily_config.py ustawia niepoprawne wartości liczbowe).
        monkeypatch.delenv("TAVILY_TIMEOUT", raising=False)
        monkeypatch.delenv("TAVILY_MAX_RETRIES", raising=False)
        monkeypatch.delenv("TAVILY_RATE_LIMIT", raising=False)

        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _yahoo_rows(_rising_md())},
        )
        rt = entrypoint.build_runtime_service(
            persist_path=Path(tmp_path) / "e2e.db",
            yahoo_session=session,
        )

        # Kontrakty zamiast isinstance: inne testy Tavily wymuszają świeży
        # import modułu (usuwają go z sys.modules), przez co klasa w tym
        # module może różnić się tożsamością od klasy zaimportowanej tutaj.
        provider = rt.master_engine.openai_provider
        adapter = rt.master_engine._tavily_adapter
        assert provider is not None
        assert provider.__class__.__name__ == "OpenAIProvider"
        assert provider.model == "gpt-4o"
        assert provider.max_retries == 0
        assert adapter is not None
        assert adapter.__class__.__name__ == "TavilyEventAdapter"
        assert callable(getattr(adapter, "search_for_event", None))
