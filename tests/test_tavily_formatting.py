"""
Tests for DecisionEngine._format_tavily_context() — KROK 4B verifier.

Covers:
    - None / empty / non-dict → empty string
    - Empty top_results → empty string
    - Valid context with title, URL, published_date, score, content, sentiment
    - Missing optional fields
    - Empty title → skipped
    - Content limit (500 chars)
    - Result ordering preserved
    - No repr() / str() on entire dict
    - Tavily label present
    - Yahoo Finance not referenced in Tavily section
"""

import unittest
from datetime import datetime, timezone

from engines.ai.decision_engine import DecisionEngine


class TestFormatTavilyContext(unittest.TestCase):
    """Tests for DecisionEngine._format_tavily_context()."""

    # ------------------------------------------------------------------
    # Empty / None / Invalid
    # ------------------------------------------------------------------

    def test_none_returns_empty_string(self):
        result = DecisionEngine._format_tavily_context(None)
        self.assertEqual(result, "")

    def test_empty_dict_returns_empty_string(self):
        result = DecisionEngine._format_tavily_context({})
        self.assertEqual(result, "")

    def test_non_dict_returns_empty_string(self):
        result = DecisionEngine._format_tavily_context("not-a-dict")
        self.assertEqual(result, "")

    def test_empty_top_results_returns_empty_string(self):
        result = DecisionEngine._format_tavily_context(
            {"top_results": [], "results_count": 0}
        )
        self.assertEqual(result, "")

    def test_top_results_not_list_returns_empty_string(self):
        result = DecisionEngine._format_tavily_context(
            {"top_results": "not-a-list"}
        )
        self.assertEqual(result, "")

    def test_top_results_is_none_returns_empty_string(self):
        result = DecisionEngine._format_tavily_context(
            {"top_results": None}
        )
        self.assertEqual(result, "")

    # ------------------------------------------------------------------
    # Valid context
    # ------------------------------------------------------------------

    def test_label_present(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{"title": "News"}],
        })
        self.assertIn("Tavily external context:", result)

    def test_query_present(self):
        result = DecisionEngine._format_tavily_context({
            "query": "stock TEST GPW price surge",
            "top_results": [{"title": "News"}],
        })
        self.assertIn("Query: stock TEST GPW price surge.", result)

    def test_results_count_present(self):
        result = DecisionEngine._format_tavily_context({
            "results_count": 5,
            "top_results": [{"title": "News"}],
        })
        self.assertIn("Found: 5 result(s).", result)

    def test_sentiment_present(self):
        result = DecisionEngine._format_tavily_context({
            "sentiment": 0.42,
            "top_results": [{"title": "News"}],
        })
        self.assertIn("Sentiment: 0.42", result)

    def test_sentiment_none_not_shown(self):
        result = DecisionEngine._format_tavily_context({
            "sentiment": None,
            "top_results": [{"title": "News"}],
        })
        self.assertNotIn("Sentiment", result)

    # ------------------------------------------------------------------
    # Individual result fields
    # ------------------------------------------------------------------

    def test_title_displayed(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{"title": "Breaking News"}],
        })
        self.assertIn("[1] Breaking News", result)

    def test_published_date_displayed(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "published_date": "2026-07-28T10:00:00+00:00",
            }],
        })
        self.assertIn("Date: 2026-07-28T10:00:00+00:00", result)

    def test_url_displayed(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "url": "https://example.com/news",
            }],
        })
        self.assertIn("URL: https://example.com/news", result)

    def test_score_displayed(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "score": 0.95,
            }],
        })
        self.assertIn("Relevance: 0.95", result)

    def test_content_displayed(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "content": "Stock surges on earnings beat.",
            }],
        })
        self.assertIn("Content: Stock surges on earnings beat.", result)

    def test_full_result_displayed(self):
        result = DecisionEngine._format_tavily_context({
            "query": "stock XYZ GPW price surge",
            "results_count": 1,
            "top_results": [{
                "title": "XYZ Stock Surge",
                "url": "https://example.com/xyz",
                "content": "XYZ stock surged 12% today following strong Q2 results.",
                "score": 0.92,
                "published_date": "2026-07-28T12:00:00+00:00",
            }],
            "sentiment": 0.55,
        })
        self.assertIn("Tavily external context:", result)
        self.assertIn("Query: stock XYZ GPW price surge.", result)
        self.assertIn("Found: 1 result(s).", result)
        self.assertIn("[1] XYZ Stock Surge", result)
        self.assertIn("Date: 2026-07-28T12:00:00+00:00", result)
        self.assertIn("URL: https://example.com/xyz", result)
        self.assertIn("Relevance: 0.92", result)
        self.assertIn("Content: XYZ stock surged 12% today following strong Q2 results.", result)
        self.assertIn("Sentiment: 0.55", result)

    # ------------------------------------------------------------------
    # Missing optional fields
    # ------------------------------------------------------------------

    def test_missing_title_skipped(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [
                {"title": "", "url": "https://a.com"},  # empty title
                {"title": "Valid", "url": "https://b.com"},
            ],
        })
        # Only Valid should appear, empty title skipped (index 2 preserved)
        self.assertIn("[2] Valid", result)

    def test_missing_date_not_blocking(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "url": "https://a.com",
                # No published_date
            }],
        })
        self.assertIn("News", result)
        self.assertNotIn("Date:", result)

    def test_missing_url_not_blocking(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                # No url
            }],
        })
        self.assertIn("News", result)
        self.assertNotIn("URL:", result)

    def test_missing_score_not_blocking(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                # No score
            }],
        })
        self.assertIn("News", result)
        self.assertNotIn("Relevance:", result)

    def test_missing_content_not_blocking(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "url": "https://a.com",
                # No content
            }],
        })
        self.assertIn("News", result)
        self.assertNotIn("Content:", result)

    # ------------------------------------------------------------------
    # Content limit
    # ------------------------------------------------------------------

    def test_content_long_truncated(self):
        long_content = "x" * 1000
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "content": long_content,
            }],
        })
        self.assertIn("Content: " + ("x" * 500), result)
        self.assertNotIn("x" * 501, result)  # no chars beyond 500

    def test_content_short_not_truncated(self):
        short = "Hello world."
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "content": short,
            }],
        })
        self.assertIn(f"Content: {short}", result)

    def test_content_exact_500_not_adds_truncation(self):
        exact = "y" * 500
        result = DecisionEngine._format_tavily_context({
            "top_results": [{
                "title": "News",
                "content": exact,
            }],
        })
        self.assertIn(f"Content: {exact}", result)

    # ------------------------------------------------------------------
    # Ordering preserved
    # ------------------------------------------------------------------

    def test_result_order_preserved(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [
                {"title": "First"},
                {"title": "Second"},
                {"title": "Third"},
            ],
        })
        idx1 = result.find("[1] First")
        idx2 = result.find("[2] Second")
        idx3 = result.find("[3] Third")
        self.assertLess(idx1, idx2)
        self.assertLess(idx2, idx3)

    # ------------------------------------------------------------------
    # No repr() or str() of entire dict
    # ------------------------------------------------------------------

    def test_no_repr_in_result(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{"title": "News"}],
        })
        self.assertNotIn("{'", result)
        self.assertNotIn("{", result)  # no raw dict repr

    def test_no_str_dict_in_result(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{"title": "News"}],
        })
        self.assertNotIn("'title'", result)  # no Python repr of keys

    # ------------------------------------------------------------------
    # Yahoo Finance not referenced
    # ------------------------------------------------------------------

    def test_no_yahoo_finance_in_tavily_section(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [{"title": "News about XYZ"}],
        })
        self.assertNotIn("Yahoo", result)

    # ------------------------------------------------------------------
    # Non-dict item in top_results
    # ------------------------------------------------------------------

    def test_non_dict_item_skipped(self):
        result = DecisionEngine._format_tavily_context({
            "top_results": [
                "not-a-dict",
                {"title": "Valid"},
            ],
        })
        # Only Valid should appear, non-dict item skipped (index 2 preserved)
        self.assertIn("[2] Valid", result)

    # ------------------------------------------------------------------
    # Integration: process_event uses tavily_context
    # ------------------------------------------------------------------

    def test_process_event_with_tavily_context(self):
        """process_event includes Tavily section when tavily_context available."""
        from data.models.market_event import MarketEvent
        from data.models.event_enums import (
            EventFamily, EventOwner, InstrumentType, PriorityLevel,
        )
        from data.models.price_data import PriceData

        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.85,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            price_data=PriceData(
                open=100.0, high=110.0, low=98.0, close=108.0,
                prev_close=100.0, change_pct=8.0, change_abs=8.0,
            ),
        )
        event.tavily_context = {
            "query": "stock TEST GPW price surge",
            "results_count": 1,
            "top_results": [{
                "title": "Test News",
                "url": "https://example.com",
                "content": "Test content.",
            }],
        }

        engine = DecisionEngine()
        signal = engine.process_event(event)

        self.assertIn("Tavily external context:", signal.reasoning)
        self.assertIn("Test News", signal.reasoning)

    def test_process_event_without_tavily_context_no_section(self):
        """process_event without tavily_context does NOT include Tavily section."""
        from data.models.market_event import MarketEvent
        from data.models.event_enums import (
            EventFamily, EventOwner, InstrumentType, PriorityLevel,
        )
        from data.models.price_data import PriceData

        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.85,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            price_data=PriceData(
                open=100.0, high=110.0, low=98.0, close=108.0,
                prev_close=100.0, change_pct=8.0, change_abs=8.0,
            ),
        )
        # No tavily_context set

        engine = DecisionEngine()
        signal = engine.process_event(event)

        self.assertNotIn("Tavily external context:", signal.reasoning)

    def test_process_event_with_none_tavily_context(self):
        """process_event with tavily_context=None does NOT include Tavily section."""
        from data.models.market_event import MarketEvent
        from data.models.event_enums import (
            EventFamily, EventOwner, InstrumentType, PriorityLevel,
        )
        from data.models.price_data import PriceData

        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.85,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            price_data=PriceData(
                open=100.0, high=110.0, low=98.0, close=108.0,
                prev_close=100.0, change_pct=8.0, change_abs=8.0,
            ),
        )
        event.tavily_context = None

        engine = DecisionEngine()
        signal = engine.process_event(event)

        self.assertNotIn("Tavily external context:", signal.reasoning)

    def test_process_event_with_empty_tavily_context(self):
        """process_event with empty tavily_context dict does NOT include Tavily section."""
        from data.models.market_event import MarketEvent
        from data.models.event_enums import (
            EventFamily, EventOwner, InstrumentType, PriorityLevel,
        )
        from data.models.price_data import PriceData

        event = MarketEvent.create_new(
            event_type="PRICE_SURGE",
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.85,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            price_data=PriceData(
                open=100.0, high=110.0, low=98.0, close=108.0,
                prev_close=100.0, change_pct=8.0, change_abs=8.0,
            ),
        )
        event.tavily_context = {}

        engine = DecisionEngine()
        signal = engine.process_event(event)

        self.assertNotIn("Tavily external context:", signal.reasoning)


if __name__ == "__main__":
    unittest.main()