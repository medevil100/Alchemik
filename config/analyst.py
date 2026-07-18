"""
Analyst Engine configuration.

This file contains all configuration parameters for the Analyst Engine,
including weights, thresholds, and rules for generating final analysis.
"""

from typing import Dict, List

# Weights for final_score calculation
FINAL_SCORE_WEIGHTS: Dict[str, float] = {
    "ranking_score": 0.4,
    "risk_score": 0.3,
    "hunter_score": 0.2,
    "confidence_level": 0.1
}

# Recommendation thresholds
RECOMMENDATION_THRESHOLDS: Dict[str, float] = {
    "STRONG_BUY": 0.9,
    "BUY": 0.7,
    "HOLD": 0.4,
    "REDUCE": 0.2,
    "AVOID": 0.0
}

# Positive factors thresholds
POSITIVE_FACTORS_THRESHOLDS: Dict[str, float] = {
    "HIGH_RANKING": 0.7,
    "LOW_RISK": 0.3,
    "HIGH_HUNTER": 0.7,
    "HIGH_CONFIDENCE": 0.8
}

# Risk factors thresholds
RISK_FACTORS_THRESHOLDS: Dict[str, float] = {
    "HIGH_RISK": 0.7,
    "LOW_CONFIDENCE": 0.4,
    "LOW_RANKING": 0.3,
    "LOW_HUNTER": 0.3
}

# Warnings thresholds
WARNINGS_THRESHOLDS: Dict[str, float] = {
    "CRITICAL_RISK": 0.8,
    "LOW_CONFIDENCE": 0.3,
    "DATA_INCOMPLETE": 0.5
}

# Minimum confidence level required for analysis
MINIMUM_CONFIDENCE: float = 0.3

# Rules for handling missing data
MISSING_DATA_RULES: Dict[str, str] = {
    "partial_data": "warn",
    "critical_data": "reject"
}