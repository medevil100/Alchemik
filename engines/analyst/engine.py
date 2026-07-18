"""
Analyst Engine - responsible for generating final analysis based on results from other engines.

This module provides the public API for the Analyst Engine, which combines insights from:
- AI Engine
- Ranking Engine
- Risk Engine
- Hunter Engine

Note: This is a skeleton implementation as per ETAP 11 requirements.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from data.models import FinalAnalysisResult, AnalysisResult, RankingResult
from data.models.risk_result import RiskResult
from data.models.hunter_result import HunterResult
from config.analyst import FINAL_SCORE_WEIGHTS, RECOMMENDATION_THRESHOLDS, POSITIVE_FACTORS_THRESHOLDS, RISK_FACTORS_THRESHOLDS, WARNINGS_THRESHOLDS


class AnalystEngine:
    """
    Public interface for the Analyst Engine.
    """

    def __init__(self):
        """Initialize the Analyst Engine."""
        pass

    def generate_analysis(
        self,
        symbol: str,
        analysis_result: AnalysisResult,
        ranking_result: RankingResult,
        risk_result: RiskResult,
        hunter_result: HunterResult
    ) -> FinalAnalysisResult:
        """
        Generate final analysis based on results from other engines.

        Args:
            symbol: Instrument symbol
            analysis_result: Results from Analysis Engine
            ranking_result: Results from Ranking Engine
            risk_result: Results from Risk Engine
            hunter_result: Results from Hunter Engine

        Returns:
            FinalAnalysisResult: The final analysis result

        Raises:
            ValueError: If any input model is None or invalid
        """
        # Validate inputs
        if not all([analysis_result, ranking_result, risk_result, hunter_result]):
            raise ValueError("All input models must be provided")
        
        # Validate types
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")
        if not isinstance(analysis_result, AnalysisResult):
            raise TypeError("analysis_result must be an AnalysisResult instance")
        if not isinstance(ranking_result, RankingResult):
            raise TypeError("ranking_result must be a RankingResult instance")
        if not isinstance(risk_result, RiskResult):
            raise TypeError("risk_result must be a RiskResult instance")
        if not isinstance(hunter_result, HunterResult):
            raise TypeError("hunter_result must be a HunterResult instance")

        # Calculate final score (0.0-1.0)
        final_score = (
            ranking_result.score * FINAL_SCORE_WEIGHTS["ranking_score"] +
            (1 - risk_result.risk_score) * FINAL_SCORE_WEIGHTS["risk_score"] +
            hunter_result.hunter_score * FINAL_SCORE_WEIGHTS["hunter_score"] +
            analysis_result.confidence_level * FINAL_SCORE_WEIGHTS["confidence_level"]
        )

        # Determine recommendation
        recommendation = "HOLD"
        for rec, threshold in RECOMMENDATION_THRESHOLDS.items():
            if final_score >= threshold:
                recommendation = rec
                break

        # Gather positive factors
        positive_factors = []
        if ranking_result.score >= POSITIVE_FACTORS_THRESHOLDS["HIGH_RANKING"]:
            positive_factors.append(f"High ranking score ({ranking_result.score:.2f})")
        if risk_result.risk_score <= POSITIVE_FACTORS_THRESHOLDS["LOW_RISK"]:
            positive_factors.append(f"Low risk score ({risk_result.risk_score:.2f})")
        if hunter_result.hunter_score >= POSITIVE_FACTORS_THRESHOLDS["HIGH_HUNTER"]:
            positive_factors.append(f"High hunter score ({hunter_result.hunter_score:.2f})")
        if analysis_result.confidence_level >= POSITIVE_FACTORS_THRESHOLDS["HIGH_CONFIDENCE"]:
            positive_factors.append(f"High confidence ({analysis_result.confidence_level:.2f})")

        # Gather risk factors
        risk_factors = []
        if risk_result.risk_score >= RISK_FACTORS_THRESHOLDS["HIGH_RISK"]:
            risk_factors.append(f"High risk score ({risk_result.risk_score:.2f})")
        if analysis_result.confidence_level <= RISK_FACTORS_THRESHOLDS["LOW_CONFIDENCE"]:
            risk_factors.append(f"Low confidence ({analysis_result.confidence_level:.2f})")
        if ranking_result.score <= RISK_FACTORS_THRESHOLDS["LOW_RANKING"]:
            risk_factors.append(f"Low ranking score ({ranking_result.score:.2f})")
        if hunter_result.hunter_score <= RISK_FACTORS_THRESHOLDS["LOW_HUNTER"]:
            risk_factors.append(f"Low hunter score ({hunter_result.hunter_score:.2f})")

        # Gather warnings
        warnings = hunter_result.warnings.copy() if hunter_result.warnings else []
        if risk_result.risk_score >= WARNINGS_THRESHOLDS["CRITICAL_RISK"]:
            warnings.append(f"Critical risk level ({risk_result.risk_score:.2f})")
        if analysis_result.confidence_level <= WARNINGS_THRESHOLDS["LOW_CONFIDENCE"]:
            warnings.append(f"Low confidence level ({analysis_result.confidence_level:.2f})")
        if analysis_result.data_completeness <= WARNINGS_THRESHOLDS["DATA_INCOMPLETE"]:
            warnings.append(f"Incomplete data ({analysis_result.data_completeness:.2f}%)")

        # Generate summary
        summary = (
            f"{symbol}: Final score {final_score:.2f} ({recommendation}). "
            f"Key factors: {len(positive_factors)} positive, {len(risk_factors)} risks. "
            f"Generated at {datetime.now()}"
        )

        return FinalAnalysisResult(
            symbol=symbol,
            final_rating=final_score,
            confidence_level=analysis_result.confidence_level,
            recommendation=recommendation,
            positive_factors=positive_factors,
            risk_factors=risk_factors,
            warnings=warnings,
            summary=summary,
            generated_at=datetime.now()
        )
