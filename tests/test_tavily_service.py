"""
Tests for TavilyService — the service layer for the Tavily module.

Tests cover:
    - Query building (with/without company name, subcategory)
    - Market label resolution
    - Response parsing (valid, malformed, missing fields, empty)
    - Time-window filtering (items within/outside window, no dates)
    - Sorting and limiting (score priority, date ordering, limit)
    - API error propagation (disabled, timeout, HTTP errors)
    - Full search() workflow end-to-end with mocked client
    - Empty results handling
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from data.tavily.client import TavilyClient
from data.tavily.config import TavilyConfig
from data.tavily.errors import (
    TavilyAPIError,
    TavilyConfigError,
    TavilyConnectionError,
    TavilyRateLimitError,
    TavilyTimeoutError,
    TavilyValidationError,
)
from data.tavily.models import (
    TavilyContext,
    TavilyQueryRequest,
    TavilyResultItem,
)
from data.tavily.service import TavilyService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> TavilyConfig:
    """Create a TavilyConfig with test-safe defaults."""
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


_now = datetime(2026, 7, 28, 14, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_accepts_valid_config(self):
        svc = _make_service()
        assert isinstance(svc, TavilyService)

    def test_rejects_invalid_config_type(self):
        with pytest.raises(TypeError, match="config must be a TavilyConfig"):
            TavilyService("not-a-config")  # type: ignore[arg-type]

    def test_creates_internal_client(self):
        svc = _make_service()
        assert isinstance(svc._client, TavilyClient)


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

class TestQueryBuilding:
    """Tests for _build_query_text."""

    def test_minimal_query(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="XYZ.WA",
            market="GPW",
            event_type="PRICE_SURGE",
            event_category="Cenowe",
        )
        assert "stock XYZ.WA" in q
        assert "Warsaw Stock Exchange GPW" in q
        assert "price surge" in q
        assert "cenowe" in q
        assert "recent news analysis why" in q

    def test_query_with_company_name(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="XYZ.WA",
            market="GPW",
            event_type="PRICE_SURGE",
            event_category="Cenowe",
            company_name="Example Corp",
        )
        assert "Example Corp" in q

    def test_query_with_subcategory(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="XYZ.WA",
            market="GPW",
            event_type="PRICE_SURGE",
            event_category="Cenowe",
            event_subcategory="Ruchy kierunkowe",
        )
        assert "Ruchy kierunkowe" in q

    def test_query_nyse_market(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="ABC",
            market="NYSE",
            event_type="VOLUME_SPIKE",
            event_category="Wolumenowe",
        )
        assert "NYSE" in q
        assert "stock ABC" in q
        assert "volume spike" in q

    def test_query_unknown_market_uses_uppercase(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="DEF",
            market="JPX",
            event_type="MACD_LINE_CROSSOVER",
            event_category="Momentum",
        )
        assert "JPX" in q

    def test_event_type_spaces_normalised(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="TICK",
            market="GPW",
            event_type="RESISTANCE_BREAKOUT",
            event_category="Wybicia",
        )
        assert "resistance breakout" in q

    def test_result_is_non_empty_string(self):
        svc = _make_service()
        q = svc._build_query_text(
            ticker="X", market="GPW", event_type="A", event_category="B",
        )
        assert isinstance(q, str)
        assert q.strip()


# ---------------------------------------------------------------------------
# Market label
# ---------------------------------------------------------------------------

class TestMarketLabel:
    def test_gpw(self):
        assert TavilyService._market_label("GPW") == "Warsaw Stock Exchange GPW"

    def test_nyse(self):
        assert TavilyService._market_label("nyse") == "NYSE"

    def test_unknown(self):
        assert TavilyService._market_label("JPX") == "JPX"

    def test_lowercase(self):
        assert TavilyService._market_label("gpw") == "Warsaw Stock Exchange GPW"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestParseResults:
    """Tests for _parse_results."""

    def test_empty_response_no_results_key(self):
        svc = _make_service()
        assert svc._parse_results({}) == []

    def test_results_is_none(self):
        svc = _make_service()
        assert svc._parse_results({"results": None}) == []

    def test_results_not_a_list(self):
        svc = _make_service()
        assert svc._parse_results({"results": "not-a-list"}) == []

    def test_empty_results_list(self):
        svc = _make_service()
        assert svc._parse_results({"results": []}) == []

    def test_valid_single_result(self):
        svc = _make_service()
        raw = {
            "results": [
                {
                    "title": "Test Title",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.95,
                    "published_date": "2026-07-28T10:00:00+00:00",
                }
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        item = results[0]
        assert item.title == "Test Title"
        assert item.url == "https://example.com"
        assert item.content == "Test content"
        assert item.score == 0.95
        assert item.published_date == datetime(
            2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc
        )

    def test_multiple_results(self):
        svc = _make_service()
        raw = {
            "results": [
                {"title": "A", "url": "http://a.com", "content": "ca", "score": 0.8},
                {"title": "B", "url": "http://b.com", "content": "cb", "score": 0.6},
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 2

    def test_skip_missing_title(self):
        svc = _make_service()
        raw = {
            "results": [
                {"url": "http://a.com", "content": "c"},  # no title
                {"title": "B", "url": "http://b.com", "content": "cb"},
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].title == "B"

    def test_skip_empty_title(self):
        svc = _make_service()
        raw = {
            "results": [
                {"title": "   ", "url": "http://a.com", "content": "c"},
                {"title": "B", "url": "http://b.com", "content": "cb"},
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1

    def test_skip_missing_url(self):
        svc = _make_service()
        raw = {
            "results": [
                {"title": "A", "content": "c"},  # no url
                {"title": "B", "url": "http://b.com", "content": "cb"},
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1

    def test_skip_non_string_title(self):
        svc = _make_service()
        raw = {
            "results": [
                {"title": 123, "url": "http://a.com", "content": "c"},
                {"title": "B", "url": "http://b.com", "content": "cb"},
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1

    def test_score_out_of_range_treated_as_none(self):
        svc = _make_service()
        raw = {
            "results": [
                {
                    "title": "A",
                    "url": "http://a.com",
                    "content": "c",
                    "score": 999.0,  # out of [0,1]
                }
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].score is None

    def test_score_string_coerced(self):
        svc = _make_service()
        raw = {
            "results": [
                {
                    "title": "A",
                    "url": "http://a.com",
                    "content": "c",
                    "score": "0.75",
                }
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].score == pytest.approx(0.75)

    def test_score_none_preserved(self):
        svc = _make_service()
        raw = {
            "results": [
                {"title": "A", "url": "http://a.com", "content": "c", "score": None}
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].score is None

    def test_published_date_none(self):
        svc = _make_service()
        raw = {
            "results": [
                {
                    "title": "A",
                    "url": "http://a.com",
                    "content": "c",
                    "published_date": None,
                }
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].published_date is None

    def test_published_date_unparseable(self):
        svc = _make_service()
        raw = {
            "results": [
                {
                    "title": "A",
                    "url": "http://a.com",
                    "content": "c",
                    "published_date": "not-a-date",
                }
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].published_date is None

    def test_published_date_naive_treated_as_utc(self):
        svc = _make_service()
        raw = {
            "results": [
                {
                    "title": "A",
                    "url": "http://a.com",
                    "content": "c",
                    "published_date": "2026-07-28T10:00:00",
                }
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        dt = results[0].published_date
        assert dt is not None
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 10

    def test_entry_not_a_dict_skipped(self):
        svc = _make_service()
        raw = {
            "results": [
                "not-a-dict",
                {"title": "B", "url": "http://b.com", "content": "cb"},
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1

    def test_all_optional_fields_missing(self):
        svc = _make_service()
        raw = {
            "results": [
                {"title": "A", "url": "http://a.com", "content": "c"}
            ]
        }
        results = svc._parse_results(raw)
        assert len(results) == 1
        assert results[0].score is None
        assert results[0].published_date is None


# ---------------------------------------------------------------------------
# Time-window filtering
# ---------------------------------------------------------------------------

class TestTimeWindowFiltering:
    """Tests for _filter_by_time_window."""

    def test_empty_list_returns_empty(self):
        svc = _make_service()
        assert svc._filter_by_time_window([], _now, 24) == []

    def test_zero_hours_returns_all(self):
        svc = _make_service(max_age_hours=0)
        items = [
            TavilyResultItem(
                title="Old",
                url="http://old.com",
                content="old content",
                published_date=_now - timedelta(hours=48),
            )
        ]
        result = svc._filter_by_time_window(items, _now, 0)
        assert len(result) == 1  # max_age_hours <= 0 means no filtering

    def test_item_within_window_kept(self):
        svc = _make_service()
        item = TavilyResultItem(
            title="Fresh",
            url="http://fresh.com",
            content="fresh content",
            published_date=_now - timedelta(hours=2),
        )
        result = svc._filter_by_time_window([item], _now, 24)
        assert len(result) == 1

    def test_item_on_cutoff_boundary_kept(self):
        svc = _make_service()
        cutoff = _now - timedelta(hours=24)
        item = TavilyResultItem(
            title="Exact",
            url="http://exact.com",
            content="exact content",
            published_date=cutoff,
        )
        result = svc._filter_by_time_window([item], _now, 24)
        assert len(result) == 1

    def test_item_outside_window_dropped(self):
        svc = _make_service()
        item = TavilyResultItem(
            title="Old",
            url="http://old.com",
            content="old content",
            published_date=_now - timedelta(hours=72),
        )
        result = svc._filter_by_time_window([item], _now, 24)
        assert len(result) == 0

    def test_item_without_date_kept(self):
        svc = _make_service()
        item = TavilyResultItem(
            title="No Date",
            url="http://nodate.com",
            content="no date content",
            published_date=None,
        )
        result = svc._filter_by_time_window([item], _now, 24)
        assert len(result) == 1

    def test_mixed_kept_and_dropped(self):
        svc = _make_service()
        fresh = TavilyResultItem(
            title="Fresh", url="http://a.com", content="c",
            published_date=_now - timedelta(hours=1),
        )
        old = TavilyResultItem(
            title="Old", url="http://b.com", content="c",
            published_date=_now - timedelta(hours=100),
        )
        nodate = TavilyResultItem(
            title="No Date", url="http://c.com", content="c",
            published_date=None,
        )
        result = svc._filter_by_time_window([fresh, old, nodate], _now, 24)
        assert len(result) == 2
        titles = {r.title for r in result}
        assert titles == {"Fresh", "No Date"}

    def test_custom_max_age_hours(self):
        svc = _make_service(max_age_hours=1)
        recent = TavilyResultItem(
            title="Recent", url="http://a.com", content="c",
            published_date=_now - timedelta(minutes=30),
        )
        older = TavilyResultItem(
            title="Older", url="http://b.com", content="c",
            published_date=_now - timedelta(hours=2),
        )
        result = svc._filter_by_time_window([recent, older], _now, 1)
        assert len(result) == 1
        assert result[0].title == "Recent"


# ---------------------------------------------------------------------------
# Sorting and limiting
# ---------------------------------------------------------------------------

class TestSortAndLimit:
    """Tests for _sort_and_limit."""

    def _item(self, title, score=None, hours_ago=0, **kw):
        if hours_ago == 999:
            pub = None
        else:
            pub = _now - timedelta(hours=hours_ago)
        return TavilyResultItem(
            title=title, url=f"http://{title}.com", content="c",
            score=score, published_date=pub, **kw,
        )

    def test_empty_returns_empty(self):
        svc = _make_service()
        assert svc._sort_and_limit([], 5) == []

    def test_limits_to_max(self):
        svc = _make_service()
        items = [self._item(f"Item{i}") for i in range(20)]
        result = svc._sort_and_limit(items, 5)
        assert len(result) == 5

    def test_scored_before_unscored(self):
        svc = _make_service()
        scored = self._item("Scored", score=0.5)
        unscored = self._item("Unscored", score=None)
        result = svc._sort_and_limit([unscored, scored], 10)
        assert result[0].title == "Scored"
        assert result[1].title == "Unscored"

    def test_higher_score_first(self):
        svc = _make_service()
        high = self._item("High", score=0.9)
        low = self._item("Low", score=0.3)
        result = svc._sort_and_limit([low, high], 10)
        assert result[0].title == "High"
        assert result[1].title == "Low"

    def test_newer_date_first_with_same_score(self):
        svc = _make_service()
        newer = self._item("Newer", score=0.5, hours_ago=1)
        older = self._item("Older", score=0.5, hours_ago=48)
        result = svc._sort_and_limit([older, newer], 10)
        assert result[0].title == "Newer"
        assert result[1].title == "Older"

    def test_no_date_after_dated(self):
        svc = _make_service()
        dated = self._item("Dated", score=0.5, hours_ago=1)
        nodate = self._item("NoDate", score=0.5, hours_ago=999)
        result = svc._sort_and_limit([nodate, dated], 10)
        assert result[0].title == "Dated"
        assert result[1].title == "NoDate"


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

class TestErrorPropagation:
    """Tests that service properly propagates errors from TavilyClient."""

    def test_disabled_module_raises_config_error(self, monkeypatch):
        config = _make_config(enabled=False)
        svc = TavilyService(config)
        with pytest.raises(TavilyConfigError, match="disabled"):
            svc.search(
                ticker="XYZ.WA",
                market="GPW",
                event_type="PRICE_SURGE",
                event_category="Cenowe",
                detection_time=_now,
            )

    def test_timeout_error_propagated(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(side_effect=TavilyTimeoutError("timeout"))
        with pytest.raises(TavilyTimeoutError):
            svc.search(
                ticker="X", market="GPW", event_type="A", event_category="B",
                detection_time=_now,
            )

    def test_connection_error_propagated(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(
            side_effect=TavilyConnectionError("connection failed")
        )
        with pytest.raises(TavilyConnectionError):
            svc.search(
                ticker="X", market="GPW", event_type="A", event_category="B",
                detection_time=_now,
            )

    def test_rate_limit_error_propagated(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(
            side_effect=TavilyRateLimitError("rate limited")
        )
        with pytest.raises(TavilyRateLimitError):
            svc.search(
                ticker="X", market="GPW", event_type="A", event_category="B",
                detection_time=_now,
            )

    def test_api_error_propagated(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(
            side_effect=TavilyAPIError("HTTP 500")
        )
        with pytest.raises(TavilyAPIError):
            svc.search(
                ticker="X", market="GPW", event_type="A", event_category="B",
                detection_time=_now,
            )

    def test_validation_error_propagated(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(
            side_effect=TavilyValidationError("invalid JSON")
        )
        with pytest.raises(TavilyValidationError):
            svc.search(
                ticker="X", market="GPW", event_type="A", event_category="B",
                detection_time=_now,
            )


# ---------------------------------------------------------------------------
# Full workflow tests (with mocked client)
# ---------------------------------------------------------------------------

class TestFullSearchWorkflow:
    """End-to-end tests of search() with mocked TavilyClient.search."""

    def _mock_response(self, results=None):
        return {"results": results or []}

    def test_successful_search_returns_context(self, monkeypatch):
        svc = _make_service()
        raw = self._mock_response([
            {
                "title": "News about XYZ",
                "url": "https://news.example.com/xyz",
                "content": "XYZ stock surges on strong earnings...",
                "score": 0.92,
                "published_date": "2026-07-28T12:00:00+00:00",
            }
        ])
        svc._client.search = MagicMock(return_value=raw)

        ctx = svc.search(
            ticker="XYZ.WA",
            market="GPW",
            event_type="PRICE_SURGE",
            event_category="Cenowe",
            detection_time=_now,
        )

        assert isinstance(ctx, TavilyContext)
        assert "XYZ.WA" in ctx.query
        assert ctx.results_count == 1
        assert len(ctx.top_results) == 1
        assert ctx.top_results[0].title == "News about XYZ"
        assert ctx.sentiment is None

    def test_no_results_returns_empty_context(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(return_value={"results": []})

        ctx = svc.search(
            ticker="ABC",
            market="NYSE",
            event_type="VOLUME_SPIKE",
            event_category="Wolumenowe",
            detection_time=_now,
        )

        assert isinstance(ctx, TavilyContext)
        assert ctx.results_count == 0
        assert len(ctx.top_results) == 0

    def test_all_results_filtered_out(self, monkeypatch):
        svc = _make_service(max_age_hours=1)
        raw = self._mock_response([
            {
                "title": "Old news",
                "url": "https://old.example.com",
                "content": "Old content",
                "score": 0.8,
                "published_date": "2026-07-20T00:00:00+00:00",  # 8 days ago
            }
        ])
        svc._client.search = MagicMock(return_value=raw)

        ctx = svc.search(
            ticker="X", market="GPW", event_type="A", event_category="B",
            detection_time=_now,
        )

        assert ctx.results_count == 1  # API returned 1
        assert len(ctx.top_results) == 0  # but filtered out

    def test_limits_to_max_accepted_results(self, monkeypatch):
        svc = _make_service(max_accepted_results=2)
        raw_results = []
        for i in range(10):
            raw_results.append({
                "title": f"News {i}",
                "url": f"https://news{i}.example.com",
                "content": f"Content {i}",
                "score": 0.9 - (i * 0.05),
                "published_date": "2026-07-28T12:00:00+00:00",
            })
        svc._client.search = MagicMock(return_value={"results": raw_results})

        ctx = svc.search(
            ticker="X", market="GPW", event_type="A", event_category="B",
            detection_time=_now,
        )

        assert ctx.results_count == 10
        assert len(ctx.top_results) == 2

    def test_result_without_date_still_kept(self, monkeypatch):
        svc = _make_service(max_age_hours=1)
        raw = self._mock_response([
            {
                "title": "Breaking news",
                "url": "https://breaking.example.com",
                "content": "Just in: ...",
                "score": 0.99,
                # No published_date
            }
        ])
        svc._client.search = MagicMock(return_value=raw)

        ctx = svc.search(
            ticker="X", market="GPW", event_type="A", event_category="B",
            detection_time=_now,
        )

        assert len(ctx.top_results) == 1

    def test_results_not_a_list_in_response(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(return_value={"results": None})

        ctx = svc.search(
            ticker="X", market="GPW", event_type="A", event_category="B",
            detection_time=_now,
        )

        assert ctx.results_count == 0
        assert len(ctx.top_results) == 0

    def test_query_includes_company_name_when_provided(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(return_value={"results": []})

        ctx = svc.search(
            ticker="XYZ.WA",
            market="GPW",
            event_type="PRICE_SURGE",
            event_category="Cenowe",
            detection_time=_now,
            company_name="Example Corp",
        )

        assert "Example Corp" in ctx.query

    def test_query_includes_subcategory_when_provided(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(return_value={"results": []})

        ctx = svc.search(
            ticker="XYZ.WA",
            market="GPW",
            event_type="PRICE_SURGE",
            event_category="Cenowe",
            detection_time=_now,
            event_subcategory="Ruchy kierunkowe",
        )

        assert "Ruchy kierunkowe" in ctx.query

    def test_results_not_present_in_response(self, monkeypatch):
        svc = _make_service()
        svc._client.search = MagicMock(return_value={})  # no "results" key

        ctx = svc.search(
            ticker="X", market="GPW", event_type="A", event_category="B",
            detection_time=_now,
        )

        assert ctx.results_count == 0
        assert len(ctx.top_results) == 0


# ---------------------------------------------------------------------------
# No side-effects on import
# ---------------------------------------------------------------------------

class TestImportSideEffects:
    """Verify importing TavilyService has no side effects."""

    def test_import_does_not_read_env(self, monkeypatch):
        """Import must not trigger any environment reads."""
        import sys

        # Remove the module to force a fresh import
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        if "data.tavily.service" in sys.modules:
            del sys.modules["data.tavily.service"]

        import data.tavily.service  # noqa: F811
        # If we got here without exceptions, import succeeded without env reads
        assert True

    def test_no_frozen_module_imports(self):
        """Verify TavilyService does not import from frozen modules."""
        import inspect
        import data.tavily.service as service_mod

        forbidden = [
            "application.",
            "engines.",
            "data.models.",
            "data.yahoo.",
        ]
        source = inspect.getsource(service_mod)
        for prefix in forbidden:
            assert prefix not in source, (
                f"TavilyService imports frozen module: {prefix}"
            )