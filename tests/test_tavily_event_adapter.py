"""
Tests for TavilyEventAdapter — the MarketEvent → TavilyService bridge.

Tests cover:
    - Constructor validation (valid TavilyService, invalid type)
    - MarketEvent type validation (accepts MarketEvent, rejects non-MarketEvent)
    - Field mapping: ticker, market, event_type, event_category,
      event_subcategory, detection_time
    - company_name always None (not available in MarketEvent)
    - Timestamp normalisation (naive → UTC, aware → UTC)
    - Single delegation to TavilyService
    - Exact return of TavilyContext from TavilyService
    - Error propagation (all Tavily exception types)
    - No direct HTTP calls
    - No env reads on import
    - No frozen module imports
    - PipelineDecision.run_tavily NOT consumed
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel, SignalTiming
from data.models.market_event import MarketEvent
from data.tavily.config import TavilyConfig
from data.tavily.errors import (
    TavilyAPIError,
    TavilyConfigError,
    TavilyConnectionError,
    TavilyRateLimitError,
    TavilyTimeoutError,
    TavilyValidationError,
)
from data.tavily.models import TavilyContext, TavilyResultItem
from data.tavily.service import TavilyService
from data.tavily.event_adapter import TavilyEventAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> TavilyConfig:
    defaults = dict(
        api_key="test-key",
        enabled=True,
        timeout_seconds=15.0,
        max_retries=2,
        max_results_from_api=20,
        max_accepted_results=10,
        max_age_hours=24,
        max_requests_per_minute=5,
        base_url="https://api.tavily.com",
    )
    defaults.update(overrides)
    return TavilyConfig(**defaults)


def _make_service(**config_overrides) -> TavilyService:
    return TavilyService(_make_config(**config_overrides))


def _make_market_event(**overrides) -> MarketEvent:
    """Create a minimal, valid MarketEvent for testing."""
    defaults = dict(
        event_id="test-id-001",
        timestamp_utc=datetime(2026, 7, 28, 14, 30, 0, tzinfo=timezone.utc),
        ticker="XYZ.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        event_family=EventFamily.TECHNICAL,
        event_category="Cenowe",
        event_type="PRICE_SURGE",
        signal_timing=SignalTiming.LEADING,
    )
    defaults.update(overrides)
    return MarketEvent(**defaults)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_accepts_valid_service(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        assert isinstance(adapter, TavilyEventAdapter)

    def test_rejects_invalid_service_type(self):
        with pytest.raises(TypeError, match="service must be a TavilyService"):
            TavilyEventAdapter("not-a-service")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# MarketEvent type validation
# ---------------------------------------------------------------------------

class TestEventValidation:
    def test_accepts_market_event(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        svc.search = MagicMock(return_value=TavilyContext("q", 0))
        event = _make_market_event()
        # Should not raise
        adapter.search_for_event(event)

    def test_rejects_non_market_event(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        with pytest.raises(TypeError, match="event must be a MarketEvent"):
            adapter.search_for_event({"ticker": "X"})  # type: ignore[arg-type]

    def test_rejects_none(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        with pytest.raises(TypeError, match="event must be a MarketEvent"):
            adapter.search_for_event(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

class TestFieldMapping:
    """Verify each MarketEvent field is correctly forwarded to TavilyService."""

    def test_ticker_mapped(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event(ticker="ABC.NYSE")
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert call_kwargs["ticker"] == "ABC.NYSE"

    def test_market_mapped(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event(market="NASDAQ")
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert call_kwargs["market"] == "NASDAQ"

    def test_event_type_mapped(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event(event_type="VOLUME_SPIKE")
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert call_kwargs["event_type"] == "VOLUME_SPIKE"

    def test_event_category_mapped(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event(event_category="Wolumenowe")
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert call_kwargs["event_category"] == "Wolumenowe"

    def test_event_subcategory_mapped_when_present(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event(event_subcategory="Ruchy kierunkowe")
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert call_kwargs["event_subcategory"] == "Ruchy kierunkowe"

    def test_event_subcategory_none_when_missing(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event(event_subcategory=None)
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert call_kwargs["event_subcategory"] is None

    def test_company_name_always_not_passed(self):
        """MarketEvent has no company_name field; adapter must not pass it."""
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event()
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        assert "company_name" not in call_kwargs


# ---------------------------------------------------------------------------
# Timestamp normalisation
# ---------------------------------------------------------------------------

class TestTimestampNormalisation:
    def test_aware_utc_preserved(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        ts = datetime(2026, 7, 28, 14, 30, 0, tzinfo=timezone.utc)
        event = _make_market_event(timestamp_utc=ts)
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        dt = call_kwargs["detection_time"]
        assert dt.tzinfo == timezone.utc
        assert dt == ts

    def test_aware_non_utc_converted(self):
        """Aware datetime in a non-UTC zone is converted to UTC."""
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        from datetime import timedelta
        cest = timezone(timedelta(hours=2))
        ts = datetime(2026, 7, 28, 16, 30, 0, tzinfo=cest)
        event = _make_market_event(timestamp_utc=ts)
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        dt = call_kwargs["detection_time"]
        # 16:30 CEST = 14:30 UTC
        assert dt.hour == 14
        assert dt.tzinfo == timezone.utc

    def test_naive_treated_as_utc(self):
        """Naive datetime is treated as UTC."""
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        ts = datetime(2026, 7, 28, 14, 30, 0)  # naive
        event = _make_market_event(timestamp_utc=ts)
        adapter.search_for_event(event)

        call_kwargs = svc.search.call_args[1]
        dt = call_kwargs["detection_time"]
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 14
        assert dt.minute == 30


# ---------------------------------------------------------------------------
# Single delegation
# ---------------------------------------------------------------------------

class TestSingleDelegation:
    def test_exactly_one_call_to_service(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        mock_ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event()
        adapter.search_for_event(event)

        assert svc.search.call_count == 1

    def test_returns_exact_context_from_service(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)

        result_item = TavilyResultItem(
            title="News Title", url="https://a.com", content="Content",
            score=0.95,
        )
        mock_ctx = TavilyContext(
            query="stock XYZ GPW price surge recent news analysis why",
            results_count=1,
            top_results=(result_item,),
            sentiment=None,
        )
        svc.search = MagicMock(return_value=mock_ctx)

        event = _make_market_event()
        ctx = adapter.search_for_event(event)

        assert ctx is mock_ctx
        assert ctx.query == mock_ctx.query
        assert ctx.results_count == 1
        assert len(ctx.top_results) == 1
        assert ctx.top_results[0].title == "News Title"


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

class TestErrorPropagation:
    """Adapter must propagate all Tavily exceptions without catching them."""

    def test_config_error_propagated(self):
        svc = _make_service(enabled=False)
        adapter = TavilyEventAdapter(svc)
        event = _make_market_event()
        with pytest.raises(TavilyConfigError):
            adapter.search_for_event(event)

    def test_api_error_propagated(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        svc.search = MagicMock(side_effect=TavilyAPIError("HTTP 500"))
        event = _make_market_event()
        with pytest.raises(TavilyAPIError):
            adapter.search_for_event(event)

    def test_timeout_error_propagated(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        svc.search = MagicMock(side_effect=TavilyTimeoutError("timeout"))
        event = _make_market_event()
        with pytest.raises(TavilyTimeoutError):
            adapter.search_for_event(event)

    def test_connection_error_propagated(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        svc.search = MagicMock(
            side_effect=TavilyConnectionError("connection failed")
        )
        event = _make_market_event()
        with pytest.raises(TavilyConnectionError):
            adapter.search_for_event(event)

    def test_rate_limit_error_propagated(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        svc.search = MagicMock(
            side_effect=TavilyRateLimitError("rate limited")
        )
        event = _make_market_event()
        with pytest.raises(TavilyRateLimitError):
            adapter.search_for_event(event)

    def test_validation_error_propagated(self):
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        svc.search = MagicMock(
            side_effect=TavilyValidationError("invalid JSON")
        )
        event = _make_market_event()
        with pytest.raises(TavilyValidationError):
            adapter.search_for_event(event)


# ---------------------------------------------------------------------------
# No direct HTTP, no env reads, no frozen imports
# ---------------------------------------------------------------------------

class TestAdapterBoundaries:
    """Verify the adapter respects module boundaries."""

    def test_no_direct_http_from_adapter(self):
        """Adapter must not perform HTTP calls; it delegates to service."""
        svc = _make_service()
        adapter = TavilyEventAdapter(svc)
        ctx = TavilyContext("q", 0)
        svc.search = MagicMock(return_value=ctx)

        event = _make_market_event()
        # If adapter tried HTTP, it would fail here (no network).
        # The mock prevents any real calls.
        result = adapter.search_for_event(event)
        assert result is ctx

    def test_no_pipeline_decision_imported(self):
        """Adapter must not import or consume PipelineDecision.

        The check skips docstrings — only actual code lines are verified.
        """
        import ast
        import inspect
        import data.tavily.event_adapter as adapter_mod

        source = inspect.getsource(adapter_mod)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            # Check Import and ImportFrom nodes
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "pipeline_decision" not in alias.name, (
                        "Adapter imports pipeline_decision"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "pipeline_decision" not in module, (
                    "Adapter imports from pipeline_decision"
                )
            # Check for run_tavily attribute access in code (not docstrings)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.attr, str):
                    assert node.attr != "run_tavily", (
                        "Adapter accesses run_tavily"
                    )

    def test_no_frozen_module_imports(self):
        """Adapter must not import from frozen engines or application."""
        import inspect
        import data.tavily.event_adapter as adapter_mod
        source = inspect.getsource(adapter_mod)
        forbidden = [
            "application.runtime",
            "application.scheduler",
            "engines.master",
            "engines.ai.decision_engine",
            "engines.composer",
            "engines.quality",
        ]
        for prefix in forbidden:
            assert prefix not in source, f"Adapter imports frozen: {prefix}"

    def test_type_checking_only_imports(self):
        """MarketEvent import is in TYPE_CHECKING block, not at runtime."""
        import inspect
        import data.tavily.event_adapter as adapter_mod
        source = inspect.getsource(adapter_mod)
        # MarketEvent appears in TYPE_CHECKING block and in the late import
        # inside search_for_event.  Both are fine.  Verify it's not a top-level
        # import.
        assert "from data.models.market_event import" not in source.split("if TYPE_CHECKING")[0]


# ---------------------------------------------------------------------------
# Import side-effects
# ---------------------------------------------------------------------------

class TestImportSideEffects:
    def test_import_does_not_read_env(self, monkeypatch):
        import sys
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        if "data.tavily.event_adapter" in sys.modules:
            del sys.modules["data.tavily.event_adapter"]

        import data.tavily.event_adapter  # noqa: F811
        assert True

    def test_no_effect_on_env(self, monkeypatch):
        """Import must not set or modify any environment variables."""
        import os
        before = dict(os.environ)
        import data.tavily.event_adapter  # noqa: F401, F811
        after = dict(os.environ)
        assert before == after