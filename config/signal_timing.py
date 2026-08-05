"""
Canonical SignalTiming mapping for all 138 ALCHEMIK event_type values.

Each event_type maps to exactly one SignalTiming class. This mapping is
the single source of truth — no detector may define its own mapping,
and no fallback is allowed for unknown event types.

Classification:
  - LEADING (24): signals appearing before/at the start of a market move
  - CONFIRMING (23): signals that confirm a previously initiated move
  - WARNING (31): warning signals about risk, weakening, reversal, or data issues
  - CONTEXT (60): informational signals describing instrument/market state

Contract invariants:
  - Exactly 138 entries (matching all event_type values in _CATALOGUE,
    PriceDetector, and VolumeDetector)
  - No fallback (SignalTiming.CONTEXT)
  - No duplicates (each event_type appears exactly once)
  - No values outside SignalTiming enum
  - Unknown types must cause a clear contract error
"""

from __future__ import annotations
from typing import Dict

from data.models.event_enums import SignalTiming


# ---------------------------------------------------------------------------
# Canonical mapping — sorted alphabetically for auditability
# ---------------------------------------------------------------------------
SIGNAL_TIMING_MAP: Dict[str, SignalTiming] = {
    # ── LEADING (24) ──────────────────────────────────────────────────
    "ATH": SignalTiming.LEADING,
    "ATL": SignalTiming.LEADING,
    "BB_EXPANSION": SignalTiming.LEADING,
    "BREAKING_NEWS": SignalTiming.LEADING,
    "EARNINGS_RELEASE": SignalTiming.LEADING,
    "GAP_DOWN": SignalTiming.LEADING,
    "GAP_UP": SignalTiming.LEADING,
    "INSIDER_BUY": SignalTiming.LEADING,
    "INSIDER_SELL": SignalTiming.LEADING,
    "MA_CROSSOVER": SignalTiming.LEADING,
    "MACD_LINE_CROSSOVER": SignalTiming.LEADING,
    "MERGER_ANNOUNCEMENT": SignalTiming.LEADING,
    "PRICE_DROP": SignalTiming.LEADING,
    "PRICE_SURGE": SignalTiming.LEADING,
    "RESISTANCE_BREAKOUT": SignalTiming.LEADING,
    "RSI_DIVERGENCE": SignalTiming.LEADING,
    "SHORT_INTEREST_SQUEEZE": SignalTiming.LEADING,
    "SOCIAL_MEDIA_SPIKE": SignalTiming.LEADING,
    "SUPPORT_BREAKDOWN": SignalTiming.LEADING,
    "TAKEOVER_BID": SignalTiming.LEADING,
    "TREND_STRUCTURE_CHANGE": SignalTiming.LEADING,
    "UNUSUAL_BLOCK_TRADE": SignalTiming.LEADING,
    "VOLATILITY_SPIKE": SignalTiming.LEADING,
    "VOLUME_SPIKE": SignalTiming.LEADING,

    # ── CONFIRMING (23) ───────────────────────────────────────────────
    "52W_HIGH": SignalTiming.CONFIRMING,
    "52W_LOW": SignalTiming.CONFIRMING,
    "ACQUISITION_ANNOUNCEMENT": SignalTiming.CONFIRMING,
    "ACQUISITION_COMPLETION": SignalTiming.CONFIRMING,
    "ANALYST_DOWNGRADE": SignalTiming.CONFIRMING,
    "ANALYST_UPGRADE": SignalTiming.CONFIRMING,
    "BEARISH_ENGULFING": SignalTiming.CONFIRMING,
    "BULLISH_ENGULFING": SignalTiming.CONFIRMING,
    "HIGH_VOLUME_ON_DOWN_DAYS": SignalTiming.CONFIRMING,
    "HIGH_VOLUME_ON_UP_DAYS": SignalTiming.CONFIRMING,
    "MACD_ZERO_CROSS": SignalTiming.CONFIRMING,
    "MAJOR_CONTRACT_WIN": SignalTiming.CONFIRMING,
    "MERGER_COMPLETION": SignalTiming.CONFIRMING,
    "MORNING_EVENING_STAR": SignalTiming.CONFIRMING,
    "OBV_DIVERGENCE": SignalTiming.CONFIRMING,
    "PRICE_TARGET_DECREASE": SignalTiming.CONFIRMING,
    "PRICE_TARGET_INCREASE": SignalTiming.CONFIRMING,
    "SHAREHOLDER_DECREASE": SignalTiming.CONFIRMING,
    "SHAREHOLDER_INCREASE": SignalTiming.CONFIRMING,
    "SIGNIFICANT_HOLDER_CHANGE": SignalTiming.CONFIRMING,
    "THREE_BLACK_CROWS": SignalTiming.CONFIRMING,
    "THREE_WHITE_SOLDIERS": SignalTiming.CONFIRMING,
    "UNUSUAL_OPTIONS_VOLUME": SignalTiming.CONFIRMING,

    # ── WARNING (31) ──────────────────────────────────────────────────
    "BANKRUPTCY_FILING": SignalTiming.WARNING,
    "BLOCK_TRADE_CLUSTER": SignalTiming.WARNING,
    "CORRELATION_BREAKDOWN": SignalTiming.WARNING,
    "CREDIT_RATING_DOWNGRADE": SignalTiming.WARNING,
    "CREDIT_WATCH_NEGATIVE": SignalTiming.WARNING,
    "CUMULATIVE_VOLUME_ANOMALY": SignalTiming.WARNING,
    "CURRENCY_VOLATILITY_SPIKE": SignalTiming.WARNING,
    "DARK_POOL_PRINT": SignalTiming.WARNING,
    "DARK_POOL_SPIKE": SignalTiming.WARNING,
    "DOJI": SignalTiming.WARNING,
    "ETF_CLOSURE_ANNOUNCEMENT": SignalTiming.WARNING,
    "FILING_DELAY": SignalTiming.WARNING,
    "GEOPOLITICAL_ESCALATION": SignalTiming.WARNING,
    "HAMMER_HANGING_MAN": SignalTiming.WARNING,
    "HARAMI": SignalTiming.WARNING,
    "INSIDER_CLUSTER_BUY": SignalTiming.WARNING,
    "INSIDER_CLUSTER_SELL": SignalTiming.WARNING,
    "LAWSUIT_FILED": SignalTiming.WARNING,
    "LEVEL_REJECTION": SignalTiming.WARNING,
    "MARUBOZU": SignalTiming.WARNING,
    "NEAR_ZERO_VOLUME": SignalTiming.WARNING,
    "OPTIONS_VOLATILITY_SKEW": SignalTiming.WARNING,
    "PRICE_VOLUME_DIVERGENCE": SignalTiming.WARNING,
    "PSYCH_LEVEL_CROSS": SignalTiming.WARNING,
    "RECURRING_PATTERN": SignalTiming.WARNING,
    "REGULATORY_INVESTIGATION": SignalTiming.WARNING,
    "RSI_OVERBOUGHT": SignalTiming.WARNING,
    "RSI_OVERSOLD": SignalTiming.WARNING,
    "SHOOTING_STAR_INV_HAMMER": SignalTiming.WARNING,
    "SHORT_INTEREST_SPIKE": SignalTiming.WARNING,
    "VIX_SPIKE": SignalTiming.WARNING,

    # ── CONTEXT (60) ──────────────────────────────────────────────────
    "ADVANCED_DECLINE_RATIO": SignalTiming.CONTEXT,
    "ANALYST_REPORT": SignalTiming.CONTEXT,
    "ATR_EXPANSION": SignalTiming.CONTEXT,
    "BB_SQUEEZE": SignalTiming.CONTEXT,
    "BOARD_CHANGE": SignalTiming.CONTEXT,
    "CEO_CHANGE": SignalTiming.CONTEXT,
    "CFO_CHANGE": SignalTiming.CONTEXT,
    "COMMODITY_PRICE_DROP": SignalTiming.CONTEXT,
    "COMMODITY_PRICE_SPIKE": SignalTiming.CONTEXT,
    "COMPOSITE_EVENT": SignalTiming.CONTEXT,
    "CONSECUTIVE_CANDLES": SignalTiming.CONTEXT,
    "COVERAGE_DROPPED": SignalTiming.CONTEXT,
    "CPI_BEAT": SignalTiming.CONTEXT,
    "CPI_MISS": SignalTiming.CONTEXT,
    "CREDIT_RATING_UPGRADE": SignalTiming.CONTEXT,
    "CREDIT_WATCH_POSITIVE": SignalTiming.CONTEXT,
    "CROSS_INSTRUMENT_CORRELATION": SignalTiming.CONTEXT,
    "CURRENCY_PLUMMET": SignalTiming.CONTEXT,
    "CURRENCY_SURGE": SignalTiming.CONTEXT,
    "EARNINGS_WHISPER": SignalTiming.CONTEXT,
    "EBI_FILING": SignalTiming.CONTEXT,
    "ESPI_FILING": SignalTiming.CONTEXT,
    "ETF_COMPOSITION_CHANGE": SignalTiming.CONTEXT,
    "ETF_FLOW_SPIKE": SignalTiming.CONTEXT,
    "ETF_PREMIUM_DISCOUNT": SignalTiming.CONTEXT,
    "EXECUTIVE_INTERVIEW": SignalTiming.CONTEXT,
    "FIBONACCI_HIT": SignalTiming.CONTEXT,
    "GDP_BEAT": SignalTiming.CONTEXT,
    "GDP_MISS": SignalTiming.CONTEXT,
    "GDP_REVISION": SignalTiming.CONTEXT,
    "GUIDANCE_UPDATE": SignalTiming.CONTEXT,
    "INFLATION_TREND_CHANGE": SignalTiming.CONTEXT,
    "INSTRUMENT_STATE_CHANGE": SignalTiming.CONTEXT,
    "INTEREST_RATE_CUT": SignalTiming.CONTEXT,
    "INTEREST_RATE_HIKE": SignalTiming.CONTEXT,
    "MA_SLOPE_CHANGE": SignalTiming.CONTEXT,
    "MAJOR_CONTRACT_LOSS": SignalTiming.CONTEXT,
    "MANAGEMENT_SHAKEUP": SignalTiming.CONTEXT,
    "MARKET_BREADTH_CHANGE": SignalTiming.CONTEXT,
    "MULTIPLE_DETECTOR_CONFIRMATION": SignalTiming.CONTEXT,
    "NET_INCOME_CHANGE": SignalTiming.CONTEXT,
    "NEW_COVERAGE": SignalTiming.CONTEXT,
    "NEWS_SENTIMENT_SHIFT": SignalTiming.CONTEXT,
    "OPTIONS_PUT_CALL_RATIO": SignalTiming.CONTEXT,
    "PE_RATIO_CHANGE": SignalTiming.CONTEXT,
    "PPI_SURGE": SignalTiming.CONTEXT,
    "PRICE_VS_MA": SignalTiming.CONTEXT,
    "RATE_DECISION_SURPRISE": SignalTiming.CONTEXT,
    "RATING_CHANGE": SignalTiming.CONTEXT,
    "RESTRUCTURING_PLAN": SignalTiming.CONTEXT,
    "REVENUE_CHANGE": SignalTiming.CONTEXT,
    "SEASONAL_PATTERN": SignalTiming.CONTEXT,
    "SECTOR_ROTATION": SignalTiming.CONTEXT,
    "SETTLEMENT_ANNOUNCED": SignalTiming.CONTEXT,
    "SOCIAL_MEDIA_SENTIMENT_SHIFT": SignalTiming.CONTEXT,
    "TAVILY_RESULT_SPIKE": SignalTiming.CONTEXT,
    "TAVILY_SENTIMENT_SHIFT": SignalTiming.CONTEXT,
    "VIX_COLLAPSE": SignalTiming.CONTEXT,
    "VOLATILITY_CONTRACTION": SignalTiming.CONTEXT,
    "VOLUME_ANOMALY_CLUSTER": SignalTiming.CONTEXT,
}


# ---------------------------------------------------------------------------
# Centralized lookup — no fallback
# ---------------------------------------------------------------------------
def lookup_signal_timing(event_type: str) -> SignalTiming:
    """
    Return the canonical SignalTiming for *event_type*.

    Raises:
        KeyError: If *event_type* is not in SIGNAL_TIMING_MAP.
            This is a contract violation — all 138 types must be mapped.
    """
    if event_type not in SIGNAL_TIMING_MAP:
        raise KeyError(
            f"event_type {event_type!r} has no canonical SignalTiming mapping. "
            f"This is a contract error — all 138 event types must be mapped."
        )
    return SIGNAL_TIMING_MAP[event_type]