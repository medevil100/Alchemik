"""
Configuration for the Ranking Engine.

Defines default weights and parameters for ranking calculations.
"""

DEFAULT_WEIGHTS = {
    "technical": 0.4,
    "news": 0.3,
    "ai_signal": 0.3
}

VALID_SCORE_RANGE = (0.0, 1.0)

MISSING_DATA_HANDLING = "zero"  # Options: "zero", "ignore", "average"