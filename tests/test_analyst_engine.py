import unittest
from datetime import datetime
from engines.analyst.engine import AnalystEngine
from data.models.final_analysis_result import FinalAnalysisResult
from data.models.analysis_result import AnalysisResult
from data.models.ai_signal import AISignal
from data.models.ranking_result import RankingResult
from data.models.risk_result import RiskResult
from data.models.hunter_result import HunterResult
from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from config.analyst import (
    FINAL_SCORE_WEIGHTS,
    RECOMMENDATION_THRESHOLDS,
    POSITIVE_FACTORS_THRESHOLDS,
    RISK_FACTORS_THRESHOLDS,
    WARNINGS_THRESHOLDS,
    MISSING_DATA_RULES,
)

# =============================================================================
# Helpers — build real model instances with configurable confidence.
# =============================================================================

def _make_analysis_result(*, confidence=0.5, has_market=True, has_signals=True):
    """Build a real AnalysisResult with one AISignal inside signals."""
    return AnalysisResult(
        company=CompanyInfo(name="TestCo", symbol="TST"),
        market_data=[
            MarketData(open=100, high=102, low=99, close=101,
                       volume=5000, timestamp=datetime.now())
        ] if has_market else [],
        news=[],
        signals=[AISignal(
            signal_type="combined_analysis",
            confidence=confidence,
            generated_at=datetime.now(),
            reasoning="",
        )] if has_signals else [],
        generated_at=datetime.now(),
    )


def _make_ranking_result(*, score=0.7):
    return RankingResult(instrument_id="TST", score=score, details={})


def _make_risk_result(*, risk_score=0.3):
    return RiskResult(
        instrument_id="TST",
        risk_score=risk_score,
        risk_level="LOW" if risk_score < 0.5 else "HIGH",
        confidence=0.5,
        risk_factors=[],
        max_position_size=1000.0,
        stop_loss=90.0,
        take_profit=110.0,
        timestamp=datetime.now(),
    )


def _make_hunter_result(*, hunter_score=0.7, warnings=None):
    return HunterResult(
        instrument_id="TST",
        hunter_score=hunter_score,
        priority=1,
        ranking_score=0.7,
        risk_score=0.3,
        risk_level="low",
        confidence=0.5,
        reasons=[],
        warnings=warnings or [],
        timestamp=datetime.now(),
    )


# =============================================================================


class TestAnalystEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalystEngine()

    def test_create_analyst_engine(self):
        self.assertIsInstance(self.engine, AnalystEngine)

    def test_invalid_types_handling(self):
        with self.assertRaises(TypeError):
            self.engine.generate_analysis(
                123, "not AnalysisResult", "not RankingResult",
                "not RiskResult", "not HunterResult",
            )

    # ------------------------------------------------------------------
    # Score / recommendation
    # ------------------------------------------------------------------

    def test_final_score_in_range(self):
        """Final score always 0-1 regardless of inputs."""
        for conf, rk, risk, hnt in [
            (0.9, 0.9, 0.1, 0.9),
            (0.5, 0.5, 0.5, 0.5),
            (0.1, 0.1, 0.9, 0.1),
        ]:
            result = self.engine.generate_analysis(
                "SYM",
                _make_analysis_result(confidence=conf),
                _make_ranking_result(score=rk),
                _make_risk_result(risk_score=risk),
                _make_hunter_result(hunter_score=hnt),
            )
            self.assertGreaterEqual(result.final_rating, 0.0)
            self.assertLessEqual(result.final_rating, 1.0)

    def test_recommendation_is_derived_from_score(self):
        """Recommendation depends solely on final_score and thresholds.

        With weights (ranking=0.4, risk=0.3, hunter=0.2, confidence=0.1)
        and thresholds (STRONG_BUY=0.9, BUY=0.7, HOLD=0.4, REDUCE=0.2, AVOID=0.0).

        Each case uses a ranking_score that pushes the final_score into the
        expected threshold bucket while keeping risk low and hunter/confidence high.
        """
        for rk_score, exp_rec in [
            (0.97, "STRONG_BUY"),  # 0.97*0.4 + 0.9*0.3 + 0.9*0.2 + 0.9*0.1 = 0.388+0.27+0.18+0.09=0.928
            (0.65, "BUY"),         # 0.65*0.4 + 0.9*0.3 + 0.9*0.2 + 0.9*0.1 = 0.26+0.27+0.18+0.09=0.800
            (0.01, "HOLD"),        # 0.01*0.4 + 0.9*0.3 + 0.9*0.2 + 0.9*0.1 = 0.004+0.27+0.18+0.09=0.544
        ]:
            result = self.engine.generate_analysis(
                "SYM",
                _make_analysis_result(confidence=0.9),
                _make_ranking_result(score=rk_score),
                _make_risk_result(risk_score=0.1),
                _make_hunter_result(hunter_score=0.9),
            )
            self.assertEqual(result.recommendation, exp_rec)

    # ------------------------------------------------------------------
    # Positive factors
    # ------------------------------------------------------------------

    def test_positive_factors_populated(self):
        result = self.engine.generate_analysis(
            "SYM",
            _make_analysis_result(confidence=0.9),
            _make_ranking_result(score=0.8),
            _make_risk_result(risk_score=0.2),
            _make_hunter_result(hunter_score=0.8),
        )
        self.assertGreater(len(result.positive_factors), 0)
        for factor in result.positive_factors:
            self.assertTrue(any(phrase in factor for phrase in ["High", "Low"]))

    # ------------------------------------------------------------------
    # Risk factors
    # ------------------------------------------------------------------

    def test_risk_factors_populated(self):
        result = self.engine.generate_analysis(
            "SYM",
            _make_analysis_result(confidence=0.2),
            _make_ranking_result(score=0.2),
            _make_risk_result(risk_score=0.8),
            _make_hunter_result(hunter_score=0.2),
        )
        self.assertGreater(len(result.risk_factors), 0)
        for factor in result.risk_factors:
            self.assertTrue(any(phrase in factor for phrase in ["Low", "High"]))

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------

    def test_warnings_from_risk_and_confidence(self):
        """Critical risk + low confidence produce warnings."""
        result = self.engine.generate_analysis(
            "SYM",
            _make_analysis_result(confidence=0.2),
            _make_ranking_result(score=0.5),
            _make_risk_result(risk_score=0.9),
            _make_hunter_result(hunter_score=0.5, warnings=["Test warning"]),
        )
        # At least the hunter_result warning + risk warning
        self.assertGreaterEqual(len(result.warnings), 1)

    def test_warnings_when_data_incomplete(self):
        """Missing market_data or signals triggers an incompleteness warning."""
        result = self.engine.generate_analysis(
            "SYM",
            _make_analysis_result(confidence=0.2, has_market=False, has_signals=False),
            _make_ranking_result(score=0.5),
            _make_risk_result(risk_score=0.9),
            _make_hunter_result(),
        )
        self.assertGreaterEqual(len(result.warnings), 1)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def test_summary_contains_symbol(self):
        result = self.engine.generate_analysis(
            "SYM",
            _make_analysis_result(confidence=0.8),
            _make_ranking_result(score=0.7),
            _make_risk_result(risk_score=0.3),
            _make_hunter_result(hunter_score=0.8),
        )
        self.assertIn("SYM", result.summary)
        self.assertIn("Final score", result.summary)
        self.assertIn("Key factors", result.summary)

    # ------------------------------------------------------------------
    # Instrument independence
    # ------------------------------------------------------------------

    def test_same_inputs_same_output(self):
        """Identical inputs produce identical output regardless of symbol."""
        results = []
        for sym in ("TST1", "TST2", "TST3"):
            results.append(self.engine.generate_analysis(
                sym,
                _make_analysis_result(confidence=0.8),
                _make_ranking_result(score=0.7),
                _make_risk_result(risk_score=0.3),
                _make_hunter_result(hunter_score=0.8),
            ))
        for i in range(1, len(results)):
            self.assertEqual(results[0].final_rating, results[i].final_rating)
            self.assertEqual(results[0].recommendation, results[i].recommendation)

    # ------------------------------------------------------------------
    # Missing critical data
    # ------------------------------------------------------------------

    def test_null_input_raises_value_error(self):
        """Any None input is rejected with ValueError by the validator."""
        with self.assertRaises(ValueError):
            self.engine.generate_analysis(
                "SYM",
                _make_analysis_result(),
                None,
                _make_risk_result(),
                _make_hunter_result(),
            )


if __name__ == "__main__":
    unittest.main()