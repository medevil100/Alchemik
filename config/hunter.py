"""
Configuration for the Hunter Engine.

This module defines the weights and thresholds used by the Hunter Engine to filter and prioritize opportunities.
"""

HUNTER_CONFIG = {
    # Weights for hunter score calculation
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,

    # Thresholds for filtering
    "min_ranking_score": 0.5,
    "max_risk_score": 0.7,
    "min_confidence": 0.6,

    # Priority thresholds (sorted in descending order)
    "priority_thresholds": [0.9, 0.7, 0.5],

    # Other settings
    "max_results": 10,
    "handle_missing_data": "skip",  # Options: 'skip', 'default', 'reject'
    "handle_ties": "priority"  # Options: 'priority', 'random', 'first'
}