"""
Point 5/7 — produkcyjny TelegramChannel i jedno kontrolowane wysłanie (testy offline).

Zakres:
  - TelegramChannel: timeout, brak retry/fallbacku, redakcja tokenu i chat ID,
    porównanie zwróconego ``result.chat.id`` ze skonfigurowanym odbiorcą.
  - AlertDispatcher: rozpoznaje ``ChannelSendResult.success == False``.
  - AlertBuilder: jedna zwięzła wiadomość zawierająca symbol, czas danych,
    cenę, wolumen (w tym 0), zmianę względem baseline, typ zdarzenia, wynik
    techniczny, wynik AI, confidence, fakty/hipotezy/ryzyka/ograniczenia
    oraz zastrzeżenie; limit długości Telegrama.
  - Composition root: produkcyjny TelegramChannel z ``TELEGRAM_BOT_TOKEN``
    i ``TELEGRAM_CHAT_ID``; brak konfiguracji wyłącza kanał bezpiecznie.
  - Runtime: dokładnie jedno wywołanie kanału dla jednego kwalifikującego
    wyniku; brak wyniku / STALE_TIMESTAMP nie wysyła wiadomości.

Test doubles wyłącznie na granicy HTTP Telegrama. Wewnętrzne komponenty
(AlertBuilder, AlertDispatcher, RuntimeService) są rzeczywiste.
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from application import entrypoint
from application.alert_builder import AlertBuilder, AlertMessage
from application.alert_dispatcher import AlertDispatcher
from application.channels.telegram_channel import TelegramChannel, ChannelSendResult
from application.runtime import RuntimeService
from data.models import MarketData
from data.models.event_enums import InstrumentType, PriorityLevel
from data.models.final_analysis_result import FinalAnalysisResult
from data.models.market_event import MarketEvent
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData
from tests.test_point2_e2e_flow import FakeYahooSession, make_quote


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chat_match(result):
    return getattr(result, "returned_chat_matches_configured", None)


def _alert(text="hello") -> AlertMessage:
    return AlertMessage(
        alert_id="a1",
        symbol="AAA.WA",
        market="GPW",
        event_type="PRICE_SURGE",
        event_family="TECHNICAL",
        priority_final="HIGH",
        quality_level="HIGH",
        is_composite=False,
        composite_count=0,
        recommendation="STRONG_BUY",
        ai_rating=None,
        final_score=0.85,
        confidence_level=0.9,
        risk_level=None,
        ai_summary=None,
        created_at=datetime.now(timezone.utc),
        formatted_message=text,
    )


def _make_result(symbol="AAA.WA", rating=0.85, confidence=0.90) -> FinalAnalysisResult:
    return FinalAnalysisResult(
        symbol=symbol,
        final_rating=rating,
        confidence_level=confidence,
        recommendation="STRONG_BUY",
        positive_factors=[],
        risk_factors=[],
        warnings=[],
        summary="Analiza testowa",
        generated_at=datetime.now(timezone.utc),
    )


def _make_market_event(symbol="AAA.WA", quality=PriorityLevel.HIGH) -> MarketEvent:
    ev = MarketEvent.create_new(
        ticker=symbol,
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        event_type="PRICE_SURGE",
    )
    ev.set_quality_assessment(quality)
    return ev


def _simple_event(**opts) -> SimpleNamespace:
    ev = SimpleNamespace()
    ev.event_type = opts.get("event_type", "PRICE_SURGE")
    ev.event_family = SimpleNamespace(value=opts.get("event_family", "TECHNICAL"))
    ev.priority_final = SimpleNamespace(value=opts.get("priority_final", "HIGH"))
    ev.quality_level = SimpleNamespace(value=opts.get("quality_level", "HIGH"))
    ev.is_composite = opts.get("is_composite", False)
    ev.composite_events = opts.get("composite_events", [])
    ev.market = opts.get("market", "GPW")
    ev.ai_context = opts.get("ai_context", None)
    ev.price_data = opts.get("price_data", None)
    ev.volume_data = opts.get("volume_data", None)
    ev.technical_context = opts.get("technical_context", None)
    ev.timestamp_utc = opts.get("timestamp_utc", None)
    return ev


class StubChannel:
    def __init__(self, success: bool = True):
        self.success = success
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return ChannelSendResult(
            channel_name="StubChannel",
            success=self.success,
            message_id="1" if self.success else None,
        )


def _make_alert_runtime(channel, *, events=None, scan_result_return="ACCEPTED",
                        scanner_candidates=None):
    hunter = MagicMock()
    master = MagicMock()
    repo = MagicMock()
    repo.load_observation.return_value = None
    repo.save_reading.return_value = scan_result_return
    repo.save_cycle.return_value = None
    repo.save_market_events.return_value = None
    dedup = MagicMock()
    dedup.should_process.return_value = True

    result = _make_result()

    def populate(*args, **kwargs):
        out = kwargs.get("events_out")
        if out is not None and events is not None:
            out.extend(events)
        return result

    master.run_analysis.side_effect = populate

    hunter_result = MagicMock()
    hunter_result.rejected = 0

    kwargs = dict(
        hunter_engine=hunter,
        master_engine=master,
        history_repository=repo,
        deduplicator=dedup,
        alert_builder=AlertBuilder(),
        alert_dispatcher=AlertDispatcher(),
        telegram_channel=channel,
    )

    if scanner_candidates is not None:
        scanner = MagicMock()
        scanner.scan.return_value = scanner_candidates
        hunter_result.opportunities = []
        kwargs["market_scanner"] = scanner
    else:
        hunter_result.opportunities = [MagicMock(instrument_id="AAA.WA")]

    hunter.scan.return_value = hunter_result
    return RuntimeService(**kwargs)


# ---------------------------------------------------------------------------
# TelegramChannel — transport / bezpieczeństwo / timeout
# ---------------------------------------------------------------------------

class TestTelegramChannelPoint5:
    def test_http_200_ok_true_success_and_chat_match(self):
        chat_id = "123456"
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "ok": True,
            "result": {"message_id": 99, "chat": {"id": 123456}},
        }
        http = Mock(return_value=response)
        channel = TelegramChannel(bot_token="tok", chat_id=chat_id, http_client=http)

        result = channel.send(_alert("hello"))

        assert result.success is True
        assert result.message_id == "99"
        assert _chat_match(result) is True
        http.assert_called_once()

    def test_chat_id_mismatch_is_error(self):
        channel = TelegramChannel(bot_token="tok", chat_id="123456")
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "ok": True,
            "result": {"message_id": 99, "chat": {"id": 999999}},
        }
        http = Mock(return_value=response)
        channel.http_client = http

        result = channel.send(_alert("hello"))

        assert result.success is False
        assert _chat_match(result) is False
        http.assert_called_once()

    def test_http_4xx_5xx_error_no_retry(self):
        response = Mock()
        response.status_code = 500
        response.text = "Server error"
        http = Mock(return_value=response)
        channel = TelegramChannel(bot_token="tok", chat_id="123", http_client=http)

        result = channel.send(_alert("hello"))

        assert result.success is False
        assert "HTTP 500" in result.error_message
        http.assert_called_once()

    def test_http_200_ok_false_is_error(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"ok": False, "description": "Bad Request"}
        http = Mock(return_value=response)
        channel = TelegramChannel(bot_token="tok", chat_id="123", http_client=http)

        result = channel.send(_alert("hello"))

        assert result.success is False
        assert result.error_message == "Bad Request"
        http.assert_called_once()

    def test_transport_error_no_retry(self):
        import requests
        http = Mock(side_effect=requests.exceptions.Timeout("timeout"))
        channel = TelegramChannel(bot_token="tok", chat_id="123", http_client=http)

        result = channel.send(_alert("hello"))

        assert result.success is False
        http.assert_called_once()

    def test_explicit_default_timeout(self):
        channel = TelegramChannel(bot_token="tok", chat_id="123")
        assert channel.timeout is not None
        assert channel.timeout > 0

    def test_success_path_executes_without_name_error(self):
        # Regression: brak importu datetime powodował NameError na ścieżce 200 OK.
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "ok": True,
            "result": {"message_id": 5, "chat": {"id": 123}},
        }
        http = Mock(return_value=response)
        channel = TelegramChannel(bot_token="tok", chat_id="123", http_client=http)

        result = channel.send(_alert("hello"))

        assert result.success is True

    def test_token_not_in_error_message(self):
        token = "SECRET_TOKEN_123"
        import requests
        http = Mock(side_effect=requests.exceptions.RequestException(
            f"Invalid URL: https://api.telegram.org/bot{token}/sendMessage"
        ))
        channel = TelegramChannel(bot_token=token, chat_id="123", http_client=http)

        result = channel.send(_alert("hello"))

        assert token not in (result.error_message or "")

    def test_chat_id_not_in_error_message(self):
        chat_id = "SECRET_CHAT_456"
        import requests
        http = Mock(side_effect=requests.exceptions.RequestException(
            f"chat {chat_id} rejected"
        ))
        channel = TelegramChannel(bot_token="tok", chat_id=chat_id, http_client=http)

        result = channel.send(_alert("hello"))

        assert chat_id not in (result.error_message or "")

    def test_url_with_token_redacted_http_error(self):
        token = "SUPER_SECRET_TOKEN"
        response = Mock()
        response.status_code = 401
        response.text = f"https://api.telegram.org/bot{token}/sendMessage"
        http = Mock(return_value=response)
        channel = TelegramChannel(bot_token=token, chat_id="123", http_client=http)

        result = channel.send(_alert("hello"))

        assert token not in (result.error_message or "")

    def test_special_characters_preserved(self):
        text = "🚨 ALCHEMIK ❗ | linia\nąęśżźć — ✓"
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"ok": True, "result": {"message_id": 1, "chat": {"id": 123}}}
        http = Mock(return_value=response)
        channel = TelegramChannel(bot_token="tok", chat_id="123", http_client=http)

        channel.send(_alert(text))

        payload = http.call_args[1]["json"]
        assert payload["text"] == text


# ---------------------------------------------------------------------------
# AlertDispatcher — rozpoznanie ChannelSendResult.success == False
# ---------------------------------------------------------------------------

class TestAlertDispatcherPoint5:
    def test_failed_channel_result_counts_as_error(self):
        alert = SimpleNamespace(alert_id="a1", formatted_message="x")
        channel = StubChannel(success=False)
        dispatcher = AlertDispatcher()

        report = dispatcher.dispatch(alert, [channel])

        assert report.success_count == 0
        assert report.error_count == 1
        assert str(channel) in report.failed_channels

    def test_exception_kept_diagnostically_without_secret(self):
        alert = SimpleNamespace(alert_id="a1", formatted_message="x")
        channel = Mock()
        channel.send.side_effect = Exception("boom")
        dispatcher = AlertDispatcher()

        report = dispatcher.dispatch(alert, [channel])

        assert report.error_count == 1
        assert "boom" in report.failed_channels[str(channel)]


# ---------------------------------------------------------------------------
# AlertBuilder / formatter
# ---------------------------------------------------------------------------

class TestAlertBuilderPoint5:
    def test_single_message_with_required_fields(self):
        builder = AlertBuilder()
        event = _simple_event(
            price_data=PriceData(open=10.0, high=10.6, low=9.9, close=10.5,
                                 prev_close=10.17, change_pct=3.2, change_abs=0.33),
            volume_data=VolumeData(current_volume=0.0, avg_volume=120000.0,
                                   volume_ratio=0.0, direction="neutral"),
            technical_context={"rsi": 71.2},
            timestamp_utc=datetime(2026, 1, 2, tzinfo=timezone.utc),
            ai_context={"signal_type": "combined_analysis",
                        "reasoning": "Fakty: cena rośnie | Hipotezy: kontynuacja"},
        )

        alert = builder.build_alert(_make_result(), event=event)

        assert isinstance(alert.formatted_message, str)
        assert alert.symbol == "AAA.WA"
        msg = alert.formatted_message
        assert "ALCHEMIK" in msg
        assert "AAA.WA" in msg
        assert "Price: 10.5" in msg
        assert "Volume: 0.0" in msg
        assert "Change vs baseline: 3.2%" in msg
        assert "Data time:" in msg
        assert "Event Type: PRICE_SURGE" in msg
        assert "Technical:" in msg
        assert "Fakty:" in msg
        assert "Hipotezy:" in msg
        assert "Zastrzeżenie" in msg

    def test_volume_zero_not_dropped(self):
        builder = AlertBuilder()
        event = _simple_event(
            volume_data=VolumeData(current_volume=0.0, avg_volume=100.0,
                                   volume_ratio=0.0, direction="neutral"),
        )
        msg = builder.build_alert(_make_result(), event=event).formatted_message
        assert "Volume: 0.0" in msg

    def test_ai_result_not_replaced_by_placeholder(self):
        builder = AlertBuilder()
        event = _simple_event(
            ai_context={"signal_type": "combined_analysis",
                        "reasoning": "Fakty: realny powód X"},
        )
        msg = builder.build_alert(_make_result(), event=event).formatted_message
        assert "realny powód X" in msg

    def test_facts_hypotheses_risks_limitations_distinct(self):
        builder = AlertBuilder()
        event = _simple_event(
            ai_context={"reasoning": (
                "Fakty: F1 | Hipotezy: H1 | Alternatywy: A1 | "
                "Ryzyka: R1 | Ograniczenia: O1"
            )},
        )
        msg = builder.build_alert(_make_result(), event=event).formatted_message
        assert "Fakty:" in msg
        assert "Hipotezy:" in msg
        assert "Alternatywy:" in msg
        assert "Ryzyka:" in msg
        assert "Ograniczenia:" in msg

    def test_one_instrument_does_not_contain_other_instrument(self):
        builder = AlertBuilder()
        aaa = builder.build_alert(_make_result("AAA.WA"), event=SimpleNamespace(
            event_type="PRICE_SURGE",
            event_family=SimpleNamespace(value="TECHNICAL"),
            priority_final=SimpleNamespace(value="HIGH"),
            quality_level=SimpleNamespace(value="HIGH"),
            is_composite=False, composite_events=[], market="GPW",
            ai_context=None, price_data=None, volume_data=None,
            technical_context=None, timestamp_utc=None,
        )).formatted_message
        bbb = builder.build_alert(_make_result("BBB.WA"), event=SimpleNamespace(
            event_type="PRICE_SURGE",
            event_family=SimpleNamespace(value="TECHNICAL"),
            priority_final=SimpleNamespace(value="HIGH"),
            quality_level=SimpleNamespace(value="HIGH"),
            is_composite=False, composite_events=[], market="GPW",
            ai_context=None, price_data=None, volume_data=None,
            technical_context=None, timestamp_utc=None,
        )).formatted_message

        assert "BBB.WA" not in aaa
        assert "AAA.WA" not in bbb

    def test_message_within_telegram_limit(self):
        builder = AlertBuilder()
        event = _simple_event(
            ai_context={"reasoning": "dane " * 5000},
        )
        msg = builder.build_alert(_make_result(), event=event).formatted_message
        assert len(msg) <= 4096

    def test_long_message_truncated_to_single_message(self):
        builder = AlertBuilder()
        event = _simple_event(
            ai_context={"reasoning": "x" * 10000},
        )
        msg = builder.build_alert(_make_result(), event=event).formatted_message
        assert len(msg) <= 4096
        assert "…" in msg  # jawny wskaźnik skrócenia


# ---------------------------------------------------------------------------
# Composition root
# ---------------------------------------------------------------------------

def _fake_session(symbol="AAA.WA"):
    row = (
        int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()),
        10.0, 10.1, 9.9, 10.05, 0.0,
    )
    return FakeYahooSession(
        quotes=[make_quote(symbol)],
        chart_rows_by_symbol={symbol: [row]},
    )


class TestCompositionRootPoint5:
    def test_builds_telegram_channel_when_configured(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-bot-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")

        rt = entrypoint.build_runtime_service(
            persist_path=tmp_path / "e2e.db",
            yahoo_session=_fake_session(),
        )

        assert rt.telegram_channel is not None
        assert isinstance(rt.telegram_channel, TelegramChannel)
        assert rt.telegram_channel.timeout is not None and rt.telegram_channel.timeout > 0

    def test_passes_channel_to_runtime(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-bot-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")

        rt = entrypoint.build_runtime_service(
            persist_path=tmp_path / "e2e.db",
            yahoo_session=_fake_session(),
        )

        assert rt.telegram_channel is not None
        assert rt.telegram_channel.chat_id == "123456"

    def test_no_channel_when_unconfigured(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        rt = entrypoint.build_runtime_service(
            persist_path=tmp_path / "e2e.db",
            yahoo_session=_fake_session(),
        )

        assert rt.telegram_channel is None

    def test_composition_root_does_not_reference_secrets_toml(self):
        src = inspect.getsource(entrypoint.build_runtime_service)
        assert ".streamlit/secrets.toml" not in src
        assert "streamlit" not in src


# ---------------------------------------------------------------------------
# Runtime — dokładnie jedno wysłanie / brak wyniku / STALE_TIMESTAMP
# ---------------------------------------------------------------------------

class TestRuntimePoint5:
    def test_one_qualifying_result_sends_exactly_once(self):
        channel = StubChannel(success=True)
        rt = _make_alert_runtime(channel, events=[_make_market_event()])

        rt.run_cycle({})

        assert len(channel.sent) == 1

    def test_no_results_does_not_send(self):
        channel = StubChannel(success=True)
        rt = _make_alert_runtime(channel, events=[])

        rt.run_cycle({})

        assert len(channel.sent) == 0

    def test_stale_timestamp_does_not_send(self):
        channel = StubChannel(success=True)
        md = MarketData(open=1.0, high=1.1, low=0.9, close=1.05, volume=0.0,
                        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        rt = _make_alert_runtime(
            channel,
            events=None,
            scan_result_return="STALE_TIMESTAMP",
            scanner_candidates=[{"symbol": "AAA.WA", "data": [md]}],
        )

        rt.run_cycle({})

        assert len(channel.sent) == 0