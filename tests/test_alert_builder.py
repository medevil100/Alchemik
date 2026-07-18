import unittest
from datetime import datetime
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
    
    def test_should_alert_valid(self):
        """Test that valid result qualifies for alert"""
        self.assertTrue(self.builder.should_alert(self.valid_result))
    
    def test_should_alert_low_score(self):
        """Test that low final_score prevents alert"""
        low_score = self.valid_result
        low_score.final_rating = 60.0
        self.assertFalse(self.builder.should_alert(low_score))
    
    def test_should_alert_low_confidence(self):
        """Test that low confidence_level prevents alert"""
        low_conf = self.valid_result
        low_conf.confidence_level = 60.0
        self.assertFalse(self.builder.should_alert(low_conf))
    
    def test_should_alert_bad_recommendation(self):
        """Test that disallowed recommendation prevents alert"""
        bad_rec = self.valid_result
        bad_rec.recommendation = "HOLD"
        self.assertFalse(self.builder.should_alert(bad_rec))
    
    def test_build_alert(self):
        """Test building a valid alert"""
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
        """Test message formatting"""
        alert = self.builder.build_alert(self.valid_result)
        msg = self.builder.format_message(alert)
        self.assertIn("TEST", msg)
        self.assertIn("STRONG_BUY", msg)
        self.assertIn("80.0", msg)
        self.assertIn("85.0%", msg)
        self.assertIn("Test summary", msg)
    
    def test_invalid_result_type(self):
        """Test invalid result type raises error"""
        with self.assertRaises(ValueError):
            self.builder.should_alert(None)
    
    def test_empty_symbol(self):
        """Test empty symbol raises error"""
        empty_sym = self.valid_result
        empty_sym.symbol = ""
        with self.assertRaises(ValueError):
            self.builder.should_alert(empty_sym)

if __name__ == "__main__":
    unittest.main()