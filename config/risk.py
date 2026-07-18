"""
Central configuration for the Risk Engine.

Defines weights, thresholds, and parameters for risk calculations.
"""

# Weights for risk score calculation
WEIGHTS = {
    "ai_signal": 0.3,    # Weight for AI signal confidence
    "technical": 0.4,    # Weight for technical analysis results
    "ranking": 0.3       # Weight for ranking results
}

# Risk level thresholds (inclusive)
RISK_THRESHOLDS = {
    "LOW": 0.25,         # 0.0 <= score <= 0.25
    "MEDIUM": 0.5,      # 0.25 < score <= 0.5
    "HIGH": 0.75,       # 0.5 < score <= 0.75
    "CRITICAL": 1.0     # 0.75 < score <= 1.0
}

# Position management parameters
POSITION_LIMITS = {
    "min": 0.01,        # Minimum position size (1% of portfolio)
    "max": 0.1         # Maximum position size (10% of portfolio)
}

# Default stop loss and take profit percentages
STOP_LOSS = 0.05          # 5% stop loss
TAKE_PROFIT = 0.1         # 10% take profit

# Handling of missing data
MISSING_DATA_HANDLING = "zero"  # Options: "zero", "ignore", "average"