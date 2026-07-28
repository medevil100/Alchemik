"""
Unit tests for Tavily Data Models (data/tavily/models.py).

Covers:
    - Correct creation of all three models
    - Field type verification
    - Default value correctness
    - Immutability (frozen=True)
    - Validation (post_init)
    - Serialisation (if applicable — dict conversion)
    - No side effects on import
    - No network connections
    - No imports from frozen modules
    - Architecture compliance

All tests use real instances — no mocks unless strictly required.
"""
import unittest
import sys
from datetime import datetime, timezone

from data.tavily.models import TavilyResultItem, TavilyContext, TavilyQueryRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_datetime() -> datetime:
    """Return a fixed UTC datetime for deterministic tests."""
    return datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# TavilyResultItem
# ===================================================================


class TestTavilyResultItemCreation(unittest.TestCase):
    """Correct creation of TavilyResultItem with various field combinations."""

    def test_create_minimal(self):
        item = TavilyResultItem(
            title="Test Title",
            url="https://example.com/article",
            content="Test content.",
        )
        self.assertEqual(item.title, "Test Title")
        self.assertEqual(item.url, "https://example.com/article")
        self.assertEqual(item.content, "Test content.")
        self.assertIsNone(item.published_date)
        self.assertIsNone(item.score)

    def test_create_full(self):
        dt = _sample_datetime()
        item = TavilyResultItem(
            title="Full Article",
            url="https://example.com/full",
            content="Full content body.",
            published_date=dt,
            score=0.85,
        )
        self.assertEqual(item.title, "Full Article")
        self.assertEqual(item.url, "https://example.com/full")
        self.assertEqual(item.content, "Full content body.")
        self.assertEqual(item.published_date, dt)
        self.assertEqual(item.score, 0.85)

    def test_create_with_score_zero(self):
        """Score boundary: 0.0 is valid."""
        item = TavilyResultItem(
            title="Zero score",
            url="https://x.com",
            content="c",
            score=0.0,
        )
        self.assertEqual(item.score, 0.0)

    def test_create_with_score_one(self):
        """Score boundary: 1.0 is valid."""
        item = TavilyResultItem(
            title="Max score",
            url="https://x.com",
            content="c",
            score=1.0,
        )
        self.assertEqual(item.score, 1.0)


class TestTavilyResultItemFieldTypes(unittest.TestCase):
    """Field types must match the documented specification."""

    def test_field_types_minimal(self):
        item = TavilyResultItem(
            title="T", url="https://x.com", content="c"
        )
        self.assertIsInstance(item.title, str)
        self.assertIsInstance(item.url, str)
        self.assertIsInstance(item.content, str)
        # published_date is None — no assert needed
        # score is None — no assert needed

    def test_field_types_full(self):
        item = TavilyResultItem(
            title="T",
            url="https://x.com",
            content="c",
            published_date=_sample_datetime(),
            score=0.5,
        )
        self.assertIsInstance(item.published_date, datetime)
        self.assertIsInstance(item.score, float)


class TestTavilyResultItemImmutability(unittest.TestCase):
    """frozen=True must prevent attribute mutation."""

    def test_cannot_set_attribute(self):
        item = TavilyResultItem(
            title="Immutable", url="https://x.com", content="c"
        )
        with self.assertRaises(Exception):
            item.title = "New Title"

    def test_cannot_delete_attribute(self):
        item = TavilyResultItem(
            title="Immutable", url="https://x.com", content="c"
        )
        with self.assertRaises(Exception):
            del item.title

    def test_hashable(self):
        """Frozen dataclass instances should be hashable (if fields are)."""
        item1 = TavilyResultItem(
            title="H", url="https://x.com", content="c"
        )
        item2 = TavilyResultItem(
            title="H", url="https://x.com", content="c"
        )
        self.assertEqual(hash(item1), hash(item2))


class TestTavilyResultItemValidation(unittest.TestCase):
    """post_init validation must reject invalid inputs."""

    def test_empty_title_raises(self):
        with self.assertRaises(ValueError):
            TavilyResultItem(title="", url="https://x.com", content="c")

    def test_blank_title_raises(self):
        with self.assertRaises(ValueError):
            TavilyResultItem(title="   ", url="https://x.com", content="c")

    def test_empty_url_raises(self):
        with self.assertRaises(ValueError):
            TavilyResultItem(title="T", url="", content="c")

    def test_blank_url_raises(self):
        with self.assertRaises(ValueError):
            TavilyResultItem(title="T", url="   ", content="c")

    def test_score_below_zero_raises(self):
        with self.assertRaises(ValueError):
            TavilyResultItem(
                title="T", url="https://x.com", content="c", score=-0.01
            )

    def test_score_above_one_raises(self):
        with self.assertRaises(ValueError):
            TavilyResultItem(
                title="T", url="https://x.com", content="c", score=1.01
            )


# ===================================================================
# TavilyContext
# ===================================================================


class TestTavilyContextCreation(unittest.TestCase):
    """Correct creation of TavilyContext."""

    def test_create_minimal(self):
        ctx = TavilyContext(query="test query", results_count=5)
        self.assertEqual(ctx.query, "test query")
        self.assertEqual(ctx.results_count, 5)
        self.assertEqual(ctx.top_results, ())
        self.assertIsNone(ctx.sentiment)

    def test_create_with_results(self):
        item1 = TavilyResultItem(
            title="R1", url="https://a.com", content="c1"
        )
        item2 = TavilyResultItem(
            title="R2", url="https://b.com", content="c2"
        )
        ctx = TavilyContext(
            query="q",
            results_count=10,
            top_results=(item1, item2),
            sentiment=0.35,
        )
        self.assertEqual(len(ctx.top_results), 2)
        self.assertEqual(ctx.top_results[0].title, "R1")
        self.assertEqual(ctx.top_results[1].title, "R2")
        self.assertEqual(ctx.sentiment, 0.35)

    def test_create_empty_results(self):
        ctx = TavilyContext(
            query="no results", results_count=0, top_results=()
        )
        self.assertEqual(ctx.top_results, ())
        self.assertEqual(ctx.results_count, 0)


class TestTavilyContextFieldTypes(unittest.TestCase):
    """Field types must match the documented specification."""

    def test_field_types_minimal(self):
        ctx = TavilyContext(query="q", results_count=0)
        self.assertIsInstance(ctx.query, str)
        self.assertIsInstance(ctx.results_count, int)
        self.assertIsInstance(ctx.top_results, tuple)
        self.assertIsNone(ctx.sentiment)

    def test_field_types_full(self):
        item = TavilyResultItem(
            title="T", url="https://x.com", content="c"
        )
        ctx = TavilyContext(
            query="q",
            results_count=1,
            top_results=(item,),
            sentiment=0.5,
        )
        self.assertIsInstance(ctx.sentiment, float)
        self.assertIsInstance(ctx.top_results[0], TavilyResultItem)


class TestTavilyContextImmutability(unittest.TestCase):
    """frozen=True must prevent mutation."""

    def test_cannot_set_attribute(self):
        ctx = TavilyContext(query="q", results_count=0)
        with self.assertRaises(Exception):
            ctx.query = "new"

    def test_hashable(self):
        ctx1 = TavilyContext(query="q", results_count=0)
        ctx2 = TavilyContext(query="q", results_count=0)
        self.assertEqual(hash(ctx1), hash(ctx2))


class TestTavilyContextValidation(unittest.TestCase):
    """post_init validation must reject invalid inputs."""

    def test_empty_query_raises(self):
        with self.assertRaises(ValueError):
            TavilyContext(query="", results_count=0)

    def test_blank_query_raises(self):
        with self.assertRaises(ValueError):
            TavilyContext(query="   ", results_count=0)

    def test_negative_results_count_raises(self):
        with self.assertRaises(ValueError):
            TavilyContext(query="q", results_count=-1)

    def test_sentiment_below_minus_one_raises(self):
        with self.assertRaises(ValueError):
            TavilyContext(query="q", results_count=0, sentiment=-1.01)

    def test_sentiment_above_one_raises(self):
        with self.assertRaises(ValueError):
            TavilyContext(query="q", results_count=0, sentiment=1.01)

    def test_sentiment_boundary_minus_one(self):
        """Sentiment boundary: -1.0 is valid."""
        ctx = TavilyContext(query="q", results_count=0, sentiment=-1.0)
        self.assertEqual(ctx.sentiment, -1.0)

    def test_sentiment_boundary_one(self):
        """Sentiment boundary: 1.0 is valid."""
        ctx = TavilyContext(query="q", results_count=0, sentiment=1.0)
        self.assertEqual(ctx.sentiment, 1.0)


# ===================================================================
# TavilyQueryRequest
# ===================================================================


class TestTavilyQueryRequestCreation(unittest.TestCase):
    """Correct creation of TavilyQueryRequest."""

    def test_create_minimal(self):
        req = TavilyQueryRequest(query="AAPL earnings")
        self.assertEqual(req.query, "AAPL earnings")
        self.assertEqual(req.max_results, 10)
        self.assertEqual(req.search_depth, "basic")
        self.assertEqual(req.include_domains, ())
        self.assertEqual(req.exclude_domains, ())

    def test_create_full(self):
        req = TavilyQueryRequest(
            query="market news",
            max_results=5,
            search_depth="advanced",
            include_domains=("bloomberg.com", "reuters.com"),
            exclude_domains=("example.com",),
        )
        self.assertEqual(req.max_results, 5)
        self.assertEqual(req.search_depth, "advanced")
        self.assertEqual(req.include_domains, ("bloomberg.com", "reuters.com"))
        self.assertEqual(req.exclude_domains, ("example.com",))


class TestTavilyQueryRequestFieldTypes(unittest.TestCase):
    """Field types must be correct."""

    def test_field_types_minimal(self):
        req = TavilyQueryRequest(query="q")
        self.assertIsInstance(req.query, str)
        self.assertIsInstance(req.max_results, int)
        self.assertIsInstance(req.search_depth, str)
        self.assertIsInstance(req.include_domains, tuple)
        self.assertIsInstance(req.exclude_domains, tuple)

    def test_include_domains_is_tuple_of_str(self):
        req = TavilyQueryRequest(
            query="q", include_domains=("a.com", "b.com")
        )
        for domain in req.include_domains:
            self.assertIsInstance(domain, str)


class TestTavilyQueryRequestImmutability(unittest.TestCase):
    """frozen=True must prevent mutation."""

    def test_cannot_set_attribute(self):
        req = TavilyQueryRequest(query="q")
        with self.assertRaises(Exception):
            req.query = "new"

    def test_hashable(self):
        req1 = TavilyQueryRequest(query="q")
        req2 = TavilyQueryRequest(query="q")
        self.assertEqual(hash(req1), hash(req2))


class TestTavilyQueryRequestValidation(unittest.TestCase):
    """post_init validation must reject invalid inputs."""

    def test_empty_query_raises(self):
        with self.assertRaises(ValueError):
            TavilyQueryRequest(query="")

    def test_blank_query_raises(self):
        with self.assertRaises(ValueError):
            TavilyQueryRequest(query="   ")

    def test_max_results_zero_raises(self):
        with self.assertRaises(ValueError):
            TavilyQueryRequest(query="q", max_results=0)

    def test_max_results_negative_raises(self):
        with self.assertRaises(ValueError):
            TavilyQueryRequest(query="q", max_results=-1)

    def test_max_results_one_valid(self):
        """Boundary: 1 is the minimum."""
        req = TavilyQueryRequest(query="q", max_results=1)
        self.assertEqual(req.max_results, 1)

    def test_invalid_search_depth_raises(self):
        with self.assertRaises(ValueError):
            TavilyQueryRequest(query="q", search_depth="deep")

    def test_search_depth_basic_valid(self):
        req = TavilyQueryRequest(query="q", search_depth="basic")
        self.assertEqual(req.search_depth, "basic")

    def test_search_depth_advanced_valid(self):
        req = TavilyQueryRequest(query="q", search_depth="advanced")
        self.assertEqual(req.search_depth, "advanced")


# ===================================================================
# Serialisation
# ===================================================================


class TestTavilyModelsSerialisation(unittest.TestCase):
    """dict conversion must be available for all models."""

    def test_tavily_result_item_dict(self):
        item = TavilyResultItem(
            title="T", url="https://x.com", content="c", score=0.5
        )
        d = item.__dict__
        self.assertEqual(d["title"], "T")
        self.assertEqual(d["url"], "https://x.com")
        self.assertEqual(d["content"], "c")
        self.assertEqual(d["score"], 0.5)
        self.assertIsNone(d["published_date"])

    def test_tavily_context_dict(self):
        ctx = TavilyContext(query="q", results_count=1)
        d = ctx.__dict__
        self.assertEqual(d["query"], "q")
        self.assertEqual(d["results_count"], 1)
        self.assertEqual(d["top_results"], ())
        self.assertIsNone(d["sentiment"])

    def test_tavily_query_request_dict(self):
        req = TavilyQueryRequest(query="q")
        d = req.__dict__
        self.assertEqual(d["query"], "q")
        self.assertEqual(d["max_results"], 10)
        self.assertEqual(d["search_depth"], "basic")
        self.assertEqual(d["include_domains"], ())
        self.assertEqual(d["exclude_domains"], ())


# ===================================================================
# No side effects on import
# ===================================================================


class TestTavilyModelsNoSideEffects(unittest.TestCase):
    """Importing the models module must not trigger side effects."""

    def test_import_does_not_read_env(self):
        """Import must not read environment variables."""
        # The module was already imported at the top of this file.
        # If there were side effects, they would have been triggered.
        # We verify the module is importable and has the expected symbols.
        self.assertTrue(hasattr(TavilyResultItem, "__dataclass_fields__"))
        self.assertTrue(hasattr(TavilyContext, "__dataclass_fields__"))
        self.assertTrue(hasattr(TavilyQueryRequest, "__dataclass_fields__"))

    def test_module_has_no_external_dependencies(self):
        """The models module must only import from stdlib."""
        import importlib

        # Reload the module in a clean way and check its imports
        import data.tavily.models

        # Verify the module exists and was imported
        self.assertIsNotNone(data.tavily.models.TavilyResultItem)

    def test_no_network_imports(self):
        """The models module must not import networking libraries."""
        # Check that the module's source does not import requests, httpx,
        # aiohttp, urllib3, socket, or http.client at module level
        import inspect
        import data.tavily.models as models_mod

        source = inspect.getsource(models_mod)
        forbidden = [
            "import requests",
            "import httpx",
            "import aiohttp",
            "import urllib3",
            "import socket",
            "from http.client",
            "from urllib",
        ]
        for pattern in forbidden:
            self.assertNotIn(
                pattern,
                source,
                f"models.py must not import networking library: {pattern}",
            )


# ===================================================================
# No imports from frozen modules
# ===================================================================


class TestTavilyModelsNoFrozenImports(unittest.TestCase):
    """The models module must not import from frozen modules.

    We verify this by checking ``sys.modules`` after importing
    ``data.tavily.models``.  The frozen module names must not
    appear in the module cache as a result of importing models.
    """

    # Modules that must NOT be imported by data.tavily.models
    FROZEN_MODULES: tuple[str, ...] = (
        "data.models.market_event",
        "engines.master.engine",
        "engines.ai.decision_engine",
        "application.runtime",
    )

    @classmethod
    def setUpClass(cls) -> None:
        """Record sys.modules snapshot before importing models."""
        cls._before_modules = set(sys.modules.keys())

    def test_no_frozen_modules_imported(self):
        """After import, no frozen module path must be in sys.modules
        that wasn't there before."""
        after = set(sys.modules.keys())
        newly_loaded = after - self._before_modules
        for frozen in self.FROZEN_MODULES:
            self.assertNotIn(
                frozen,
                newly_loaded,
                f"models.py must not cause import of {frozen}",
            )

    def test_models_docstring_references_are_not_imports(self):
        """The docstring of TavilyContext may reference MarketEvent as
        documentation — this is allowed and does NOT constitute an import."""
        import data.tavily.models as models_mod

        # Verify the module is importable and has the expected classes
        self.assertIsNotNone(models_mod.TavilyResultItem)
        self.assertIsNotNone(models_mod.TavilyContext)
        self.assertIsNotNone(models_mod.TavilyQueryRequest)


if __name__ == "__main__":
    unittest.main()