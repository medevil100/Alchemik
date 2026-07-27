import unittest
from datetime import datetime
from unittest.mock import MagicMock
from application.alert_builder import AlertBuilder, AlertMessage
from data.models.final_analysis_result import FinalAnalysisResult


class TestAlertBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = AlertBuilder(
            min_final_score=0.7,
            min_confidence=0.7,
            allowed_recommendations=["STRONG_BUY", "BUY"]
        )

        self.valid_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80.0,
            confidence_level=85.0,
            recommendation="STRONG_BUY",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="Test summary",
            generated_at=datetime.now()
        )

    # ------------------------------------------------------------------
    # Existing tests — backwards compatibility (FinalAnalysisResult only)
    # ------------------------------------------------------------------

    def test_should_alert_valid(self):
        """Test that valid result qualifies for alert"""
        self.assertTrue(self.builder.should_alert(self.valid_result))

    def test_should_alert_low_score(self):
        """Test that low final_score prevents alert"""
        low_score = FinalAnalysisResult(
            symbol="TEST",
            final_rating=60.0,
            confidence_level=85.0,
            recommendation="STRONG_BUY",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="Low score",
            generated_at=datetime.now()
        )
        self.assertFalse(self.builder.should_alert(low_score))

    def test_should_alert_low_confidence(self):
        """Test that low confidence_level prevents alert"""
        low_conf = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80.0,
            confidence_level=60.0,
            recommendation="STRONG_BUY",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="Low confidence",
            generated_at=datetime.now()
        )
        self.assertFalse(self.builder.should_alert(low_conf))

    def test_should_alert_bad_recommendation(self):
        """Test that disallowed recommendation prevents alert"""
        bad_rec = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80.0,
            confidence_level=85.0,
            recommendation="HOLD",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="Bad rec",
            generated_at=datetime.now()
        )
        self.assertFalse(self.builder.should_alert(bad_rec))

    def test_build_alert(self):
        """Test building a valid alert (result only, backwards compat)"""
        alert = self.builder.build_alert(self.valid_result)
        self.assertIsInstance(alert, AlertMessage)
        self.assertEqual(alert.symbol, "TEST")
        self.assertEqual(alert.recommendation, "STRONG_BUY")
        self.assertAlmostEqual(alert.final_score, 0.8)
        self.assertAlmostEqual(alert.confidence_level, 0.85)

    def test_alert_id_deterministic(self):
        """Test that alert_id is deterministic"""
        alert1 = self.builder.build_alert(self.valid_result)
        alert2 = self.builder.build_alert(self.valid_result)
        self.assertEqual(alert1.alert_id, alert2.alert_id)

    def test_format_message(self):
        """Test message formatting (result only — ETAP 7.5 format)"""
        alert = self.builder.build_alert(self.valid_result)
        msg = self.builder.format_message(alert)
        self.assertIn("TEST", msg)
        self.assertIn("STRONG_BUY", msg)
        self.assertIn("80.0", msg)
        self.assertIn("85.0%", msg)
        # Without MarketEvent, ai_summary is None — no summary line expected.
        # The old "Test summary" from FinalAnalysisResult.summary is no longer
        # automatically included; AI summary comes from event.ai_context only.

    def test_invalid_result_type(self):
        """Test invalid result type raises error"""
        with self.assertRaises(ValueError):
            self.builder.should_alert(None)

    def test_empty_symbol(self):
        """Test empty symbol raises error"""
        empty_sym = FinalAnalysisResult(
            symbol="",
            final_rating=80.0,
            confidence_level=85.0,
            recommendation="STRONG_BUY",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="Test summary",
            generated_at=datetime.now()
        )
        with self.assertRaises(ValueError):
            self.builder.should_alert(empty_sym)

    # ------------------------------------------------------------------
    # ETAP 7.5 — MarketEvent integration tests
    # ------------------------------------------------------------------

    def test_should_alert_with_market_event_valid(self):
        """should_alert returns True when MarketEvent passes quality check."""
        event = MagicMock()
        event.quality_level = MagicMock()
        event.quality_level.value = "HIGH"
        self.assertTrue(self.builder.should_alert(self.valid_result, event=event))

    def test_should_alert_with_market_event_ignore(self):
        """should_alert returns False when MarketEvent quality is IGNORE."""
        event = MagicMock()
        event.quality_level = MagicMock()
        event.quality_level.value = "IGNORE"
        self.assertFalse(self.builder.should_alert(self.valid_result, event=event))

    def test_should_alert_with_market_event_low(self):
        """should_alert returns False when MarketEvent quality is LOW."""
        event = MagicMock()
        event.quality_level = MagicMock()
        event.quality_level.value = "LOW"
        self.assertFalse(self.builder.should_alert(self.valid_result, event=event))

    def test_should_alert_with_market_event_no_quality(self):
        """should_alert works when MarketEvent has no quality_level (None)."""
        event = MagicMock()
        event.quality_level = None
        self.assertTrue(self.builder.should_alert(self.valid_result, event=event))

    def test_build_alert_with_market_event_enriches_message(self):
        """build_alert with MarketEvent produces enriched AlertMessage."""
        event = MagicMock()
        event.event_type = "PRICE_SURGE"
        ef = MagicMock()
        ef.value = "TECHNICAL"
        event.event_family = ef
        pf = MagicMock()
        pf.value = "CRITICAL"
        event.priority_final = pf
        ql = MagicMock()
        ql.value = "CRITICAL"
        event.quality_level = ql
        event.is_composite = False
        event.composite_events = []
        event.market = "GPW"
        event.ai_context = {"signal_type": "BUY", "reasoning": "Strong bullish signal"}

        alert = self.builder.build_alert(self.valid_result, event=event)

        self.assertEqual(alert.event_type, "PRICE_SURGE")
        self.assertEqual(alert.event_family, "TECHNICAL")
        self.assertEqual(alert.priority_final, "CRITICAL")
        self.assertEqual(alert.quality_level, "CRITICAL")
        self.assertEqual(alert.market, "GPW")
        self.assertEqual(alert.ai_rating, "BUY")
        self.assertIn("Strong bullish signal", alert.ai_summary or "")

    def test_build_alert_with_composite_event(self):
        """build_alert properly handles composite events."""
        event = MagicMock()
        event.event_type = "COMPOSITE_MULTI_EVENT"
        ef = MagicMock()
        ef.value = "TECHNICAL"
        event.event_family = ef
        pf = MagicMock()
        pf.value = "CRITICAL"
        event.priority_final = pf
        ql = MagicMock()
        ql.value = "CRITICAL"
        event.quality_level = ql
        event.is_composite = True
        event.composite_events = ["id1", "id2", "id3"]
        event.market = "NYSE"
        event.ai_context = None

        alert = self.builder.build_alert(self.valid_result, event=event)

        self.assertTrue(alert.is_composite)
        self.assertEqual(alert.composite_count, 3)

    def test_formatted_message_contains_event_details(self):
        """Format message includes rich event context."""
        event = MagicMock()
        event.event_type = "PRICE_SURGE"
        ef = MagicMock()
        ef.value = "TECHNICAL"
        event.event_family = ef
        pf = MagicMock()
        pf.value = "HIGH"
        event.priority_final = pf
        ql = MagicMock()
        ql.value = "HIGH"
        event.quality_level = ql
        event.is_composite = False
        event.composite_events = []
        event.market = "NYSE"
        event.ai_context = {
            "signal_type": "BUY",
            "reasoning": "Price breaking resistance with volume confirmation."
        }

        alert = self.builder.build_alert(self.valid_result, event=event)
        msg = alert.formatted_message

        self.assertIn("🚨 ALCHEMIK ALERT", msg)
        self.assertIn("Ticker: TEST", msg)
        self.assertIn("Event Type: PRICE_SURGE", msg)
        self.assertIn("Event Family: TECHNICAL", msg)
        self.assertIn("Priority: HIGH", msg)
        self.assertIn("Quality: HIGH", msg)
        self.assertIn("AI Rating: BUY", msg)
        self.assertIn("Score: 80.0", msg)
        self.assertIn("Confidence: 85.0%", msg)
        self.assertIn("Price breaking resistance", msg)

    def test_ai_rating_is_presented_as_information(self):
        """AI Rating is presented factually, not as a command."""
        event = MagicMock()
        event.event_type = "PRICE_SURGE"
        ef = MagicMock()
        ef.value = "TECHNICAL"
        event.event_family = ef
        pf = MagicMock()
        pf.value = "HIGH"
        event.priority_final = pf
        ql = MagicMock()
        ql.value = "HIGH"
        event.quality_level = ql
        event.is_composite = False
        event.composite_events = []
        event.market = None
        event.ai_context = {"signal_type": "SELL", "reasoning": "Reversal pattern detected."}

        alert = self.builder.build_alert(self.valid_result, event=event)
        msg = alert.formatted_message

        # AI Rating is purely informational
        self.assertIn("AI Rating: SELL", msg)
        # No investment commands
        self.assertNotIn("Kup teraz", msg)
        self.assertNotIn("Sprzedaj", msg)
        self.assertNotIn("Otwórz pozycję", msg)


if __name__ == "__main__":
    unittest.main()