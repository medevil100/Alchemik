"""
Unit tests for the PipelineDecision model (ETAP 7.4 — Krok 1).

Tests cover:
  - Correct object creation with defaults and explicit values
  - Field values and types
  - Equality and inequality
  - Default values are correct
"""

import unittest
from data.models.pipeline_decision import PipelineDecision


class TestPipelineDecisionCreation(unittest.TestCase):
    """Tests for creating PipelineDecision instances."""

    def test_create_with_defaults(self):
        """PipelineDecision should be creatable with no arguments."""
        pd = PipelineDecision()
        self.assertIsInstance(pd, PipelineDecision)
        self.assertFalse(pd.run_news)
        self.assertFalse(pd.run_tavily)
        self.assertFalse(pd.run_ai)
        self.assertEqual(pd.reason, "")

    def test_create_with_all_fields(self):
        """PipelineDecision should accept all four fields."""
        pd = PipelineDecision(
            run_news=True,
            run_tavily=True,
            run_ai=True,
            reason="CRITICAL event — full analysis",
        )
        self.assertTrue(pd.run_news)
        self.assertTrue(pd.run_tavily)
        self.assertTrue(pd.run_ai)
        self.assertEqual(pd.reason, "CRITICAL event — full analysis")

    def test_create_news_only(self):
        """MEDIUM quality_level — only News."""
        pd = PipelineDecision(
            run_news=True,
            run_tavily=False,
            run_ai=False,
            reason="MEDIUM event — News only",
        )
        self.assertTrue(pd.run_news)
        self.assertFalse(pd.run_tavily)
        self.assertFalse(pd.run_ai)

    def test_create_all_false(self):
        """IGNORE or LOW quality_level — nothing should run."""
        pd = PipelineDecision(
            run_news=False,
            run_tavily=False,
            run_ai=False,
            reason="IGNORE — duplicate event",
        )
        self.assertFalse(pd.run_news)
        self.assertFalse(pd.run_tavily)
        self.assertFalse(pd.run_ai)
        self.assertEqual(pd.reason, "IGNORE — duplicate event")

    def test_create_high_quality(self):
        """HIGH quality_level — News + AI, Tavily optional."""
        pd = PipelineDecision(
            run_news=True,
            run_tavily=False,
            run_ai=True,
            reason="HIGH event — News + AI",
        )
        self.assertTrue(pd.run_news)
        self.assertFalse(pd.run_tavily)
        self.assertTrue(pd.run_ai)


class TestPipelineDecisionEquality(unittest.TestCase):
    """Tests for equality of PipelineDecision instances."""

    def test_equal_objects(self):
        """Two PipelineDecisions with identical fields should be equal."""
        pd1 = PipelineDecision(
            run_news=True, run_tavily=False, run_ai=True,
            reason="test",
        )
        pd2 = PipelineDecision(
            run_news=True, run_tavily=False, run_ai=True,
            reason="test",
        )
        self.assertEqual(pd1, pd2)

    def test_different_run_news_not_equal(self):
        """Different run_news should make objects unequal."""
        pd1 = PipelineDecision(run_news=True)
        pd2 = PipelineDecision(run_news=False)
        self.assertNotEqual(pd1, pd2)

    def test_different_run_tavily_not_equal(self):
        """Different run_tavily should make objects unequal."""
        pd1 = PipelineDecision(run_tavily=True)
        pd2 = PipelineDecision(run_tavily=False)
        self.assertNotEqual(pd1, pd2)

    def test_different_run_ai_not_equal(self):
        """Different run_ai should make objects unequal."""
        pd1 = PipelineDecision(run_ai=True)
        pd2 = PipelineDecision(run_ai=False)
        self.assertNotEqual(pd1, pd2)

    def test_different_reason_not_equal(self):
        """Different reason should make objects unequal."""
        pd1 = PipelineDecision(reason="CRITICAL")
        pd2 = PipelineDecision(reason="HIGH")
        self.assertNotEqual(pd1, pd2)

    def test_equality_against_non_pipeline_decision(self):
        """Equality check with non-PipelineDecision should return False."""
        pd = PipelineDecision()
        self.assertNotEqual(pd, "not-a-pipeline-decision")
        self.assertNotEqual(pd, None)
        self.assertNotEqual(pd, 42)


class TestPipelineDecisionFieldTypes(unittest.TestCase):
    """Tests for correct field types."""

    def test_run_news_is_bool(self):
        pd = PipelineDecision(run_news=True)
        self.assertIsInstance(pd.run_news, bool)

    def test_run_tavily_is_bool(self):
        pd = PipelineDecision(run_tavily=False)
        self.assertIsInstance(pd.run_tavily, bool)

    def test_run_ai_is_bool(self):
        pd = PipelineDecision(run_ai=True)
        self.assertIsInstance(pd.run_ai, bool)

    def test_reason_is_str(self):
        pd = PipelineDecision(reason="test reason")
        self.assertIsInstance(pd.reason, str)

    def test_default_reason_is_empty_string(self):
        pd = PipelineDecision()
        self.assertEqual(pd.reason, "")
        self.assertIsInstance(pd.reason, str)


class TestPipelineDecisionImmutability(unittest.TestCase):
    """PipelineDecision is a dataclass — fields should be directly settable."""

    def test_fields_are_mutable(self):
        """Dataclass fields can be reassigned after creation."""
        pd = PipelineDecision()
        pd.run_news = True
        pd.run_tavily = True
        pd.run_ai = True
        pd.reason = "updated"
        self.assertTrue(pd.run_news)
        self.assertTrue(pd.run_tavily)
        self.assertTrue(pd.run_ai)
        self.assertEqual(pd.reason, "updated")


if __name__ == "__main__":
    unittest.main()