"""
Configuration for the Technical Event Detector.

All thresholds, windows, and detection parameters are derived from the
approved ALCHEMIK documentation (Katalog Zdarzen Rynkowych v2.0,
Hierarchia Zdarzen Rynkowych v1.0).

Source references are provided for every parameter.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalEventsConfig:
    """
    Configuration for technical event detection.

    All values are configurable — they are NOT hardcoded in the detector.
    """

    # ------------------------------------------------------------------
    # Volatility (3.1, 3.2, 8.3)
    # Source: Katalog §3.1, §3.2, §8.3
    # ------------------------------------------------------------------
    atr_window: int = 14
    """Window for ATR calculation (Standard: 14)."""

    volatility_spike_threshold: float = 1.5
    """ATR / avg(ATR) ratio required to trigger Volatility Spike."""

    volatility_contraction_threshold: float = 0.5
    """ATR / avg(ATR) ratio below which to trigger Volatility Contraction."""

    volatility_lookback: int = 20
    """Number of periods for average ATR calculation."""

    # ------------------------------------------------------------------
    # Bollinger Bands (3.3, 3.4)
    # Source: Katalog §3.3, §3.4
    # ------------------------------------------------------------------
    bb_window: int = 20
    """SMA window for Bollinger Bands (Standard: 20)."""

    bb_num_std: int = 2
    """Number of standard deviations for Bollinger Bands."""

    bb_expansion_threshold: float = 1.5
    """BB width / avg(width) ratio to trigger BB Expansion."""

    bb_squeeze_threshold: float = 0.5
    """BB width / avg(width) ratio below which to trigger BB Squeeze."""

    bb_width_lookback: int = 20
    """Number of periods for average BB width."""

    # ------------------------------------------------------------------
    # Breakouts — Support / Resistance (4.1, 4.2)
    # Source: Katalog §4.1, §4.2
    # ------------------------------------------------------------------
    breakout_lookback: int = 20
    """Lookback window to identify recent swing high/low."""

    breakout_confirmation_pct: float = 0.5
    """Close must exceed level by this % to confirm breakout."""

    # ------------------------------------------------------------------
    # Candle patterns — single (5.1, 5.2, 5.5, 5.9)
    # Source: Katalog §5.1, §5.2, §5.5, §5.9
    # ------------------------------------------------------------------
    hammer_wick_body_ratio: float = 2.0
    """Lower wick must be at least this many times the body for Hammer."""

    hammer_upper_wick_max_pct: float = 10.0
    """Upper wick must be <= this % of total range for Hammer."""

    shooting_star_wick_body_ratio: float = 2.0
    """Upper wick must be at least this many times the body."""

    shooting_star_lower_wick_max_pct: float = 10.0
    """Lower wick must be <= this % of total range."""

    doji_body_max_pct: float = 5.0
    """Body must be <= this % of total range for Doji."""

    marubozu_body_min_pct: float = 90.0
    """Body must be >= this % of total range for Marubozu."""

    # ------------------------------------------------------------------
    # Candle patterns — engulfing (5.3, 5.4)
    # Source: Katalog §5.3, §5.4
    # ------------------------------------------------------------------
    engulfing_body_ratio: float = 1.0
    """Current body must be > previous body * ratio to count as engulfing."""

    # ------------------------------------------------------------------
    # Candle patterns — morning/evening star (5.6)
    # Source: Katalog §5.6
    # ------------------------------------------------------------------
    star_middle_body_max_pct: float = 30.0
    """Middle candle body must be <= this % of first candle body."""

    star_third_body_min_pct: float = 50.0
    """Third candle must close at least this % into first candle body."""

    # ------------------------------------------------------------------
    # Candle patterns — three soldiers/crows (5.7, 5.8)
    # Source: Katalog §5.7, §5.8
    # ------------------------------------------------------------------
    three_soldiers_min_body_pct: float = 60.0
    """Each candle body must be >= this % of its range."""

    # ------------------------------------------------------------------
    # Candle patterns — harami (5.10)
    # Source: Katalog §5.10
    # ------------------------------------------------------------------
    harami_body_ratio: float = 0.6
    """Second candle body must be <= this ratio of first candle body."""

    # ------------------------------------------------------------------
    # Moving Averages — crossover (6.1)
    # Source: Katalog §6.1
    # ------------------------------------------------------------------
    ma_fast_window: int = 20
    """Fast SMA window."""

    ma_slow_window: int = 50
    """Slow SMA window."""

    # ------------------------------------------------------------------
    # Moving Averages — slope change (6.2)
    # Source: Katalog §6.2
    # ------------------------------------------------------------------
    ma_slope_window: int = 20
    """SMA period for slope calculation."""

    ma_slope_lookback: int = 3
    """Number of periods to compare slope."""

    # ------------------------------------------------------------------
    # Price vs MA (6.3)
    # Source: Katalog §6.3
    # ------------------------------------------------------------------
    price_vs_ma_window: int = 200
    """SMA window for price vs MA (Standard: 200)."""

    # ------------------------------------------------------------------
    # Consecutive candles (6.4)
    # Source: Katalog §6.4
    # ------------------------------------------------------------------
    consecutive_candles_min: int = 5
    """Minimum number of consecutive directional candles."""

    # ------------------------------------------------------------------
    # Trend structure change (6.5)
    # Source: Katalog §6.5
    # ------------------------------------------------------------------
    swing_lookback: int = 5
    """Lookback for swing point identification."""

    # ------------------------------------------------------------------
    # RSI (7.1, 7.2, 7.3)
    # Source: Katalog §7.1, §7.2, §7.3
    # ------------------------------------------------------------------
    rsi_window: int = 14
    """RSI calculation window (Standard: 14)."""

    rsi_overbought: float = 70.0
    """RSI threshold for overbought."""

    rsi_oversold: float = 30.0
    """RSI threshold for oversold."""

    rsi_divergence_lookback: int = 20
    """Lookback for RSI divergence detection."""

    # ------------------------------------------------------------------
    # MACD (7.4, 7.5)
    # Source: Katalog §7.4, §7.5
    # ------------------------------------------------------------------
    macd_fast: int = 12
    """MACD fast EMA window."""

    macd_slow: int = 26
    """MACD slow EMA window."""

    macd_signal: int = 9
    """MACD signal line window."""

    # ------------------------------------------------------------------
    # OBV — divergence (8.1)
    # Source: Katalog §8.1
    # ------------------------------------------------------------------
    obv_divergence_lookback: int = 20
    """Lookback for OBV divergence detection."""

    # ------------------------------------------------------------------
    # Fibonacci (8.4)
    # Source: Katalog §8.4
    # ------------------------------------------------------------------
    fibo_levels: tuple[float, ...] = (0.382, 0.5, 0.618)
    """Key Fibonacci retracement levels to monitor."""

    fibo_tolerance_pct: float = 1.0
    """Tolerance for price to be considered at a Fibo level (%)."""

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------
    confidence_scale_factor: float = 2.0
    """Divide signal strength by this factor to cap confidence at 1.0."""


DEFAULT_TECHNICAL_CONFIG = TechnicalEventsConfig()