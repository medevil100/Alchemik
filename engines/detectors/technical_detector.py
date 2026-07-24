"""
TechnicalEventDetector — detects technical market events from OHLCV data.

Implements detection for events from the TECHNICAL family (34 events)
as defined in docs/Katalog_Zdarzen_Rynkowych.md and
docs/Hierarchia_Zdarzen_Rynkowych.md.

Only events with fully available data in DetectionContext are declared
in ``event_types``.  Events requiring external data sources or
specialised pattern-recognition infrastructure are excluded and
documented in the class docstring.

Reference:
    docs/ETAP_6_ARCHITEKTURA.md — § Technical Event Detector
"""

from __future__ import annotations

import math
from typing import Callable

from config.technical_events import DEFAULT_TECHNICAL_CONFIG, TechnicalEventsConfig
from data.models.market_data import MarketData
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData
from engines.detectors.base import BaseDetector
from engines.detectors.context import DetectionContext
from engines.detectors.result import DetectionResult
from engines.technical.candle import analyze_candle
from engines.technical.indicators.atr import calculate_atr
from engines.technical.indicators.bollinger_bands import calculate_bollinger_bands
from engines.technical.indicators.macd import (
    calculate_macd_histogram,
    calculate_macd_line,
    calculate_signal_line,
)
from engines.technical.indicators.obv import calculate_obv
from engines.technical.indicators.rsi import calculate_rsi
from engines.technical.indicators.sma import calculate_sma

# =========================================================================
# Event types — implemented subset of the TECHNICAL family (29 / 34).
#
# The following catalogue events are NOT detectable with current context:
#   - TRIANGLE_BREAKOUT (4.3)       — requires geometric pattern engine
#   - CHANNEL_BREAKOUT  (4.4)       — requires geometric pattern engine
#   - FLAG_PENNANT_BREAKOUT (4.5)   — requires geometric pattern engine
#   - STOCHASTIC_EXTREME     (7.6)  — Stochastic not yet implemented
#   - VWAP_DEVIATION         (8.2)  — requires intraday VWAP
# =========================================================================

_EVENT_TYPES: tuple[str, ...] = (
    # Zmienność (4)
    "VOLATILITY_SPIKE",
    "VOLATILITY_CONTRACTION",
    "BB_EXPANSION",
    "BB_SQUEEZE",
    # Wybicia techniczne (2)
    "RESISTANCE_BREAKOUT",
    "SUPPORT_BREAKDOWN",
    # Formacje świecowe (10)
    "HAMMER_HANGING_MAN",
    "SHOOTING_STAR_INV_HAMMER",
    "BULLISH_ENGULFING",
    "BEARISH_ENGULFING",
    "DOJI",
    "MORNING_EVENING_STAR",
    "THREE_WHITE_SOLDIERS",
    "THREE_BLACK_CROWS",
    "MARUBOZU",
    "HARAMI",
    # Trend (5)
    "MA_CROSSOVER",
    "MA_SLOPE_CHANGE",
    "PRICE_VS_MA",
    "CONSECUTIVE_CANDLES",
    "TREND_STRUCTURE_CHANGE",
    # Momentum (5)
    "RSI_OVERBOUGHT",
    "RSI_OVERSOLD",
    "RSI_DIVERGENCE",
    "MACD_LINE_CROSSOVER",
    "MACD_ZERO_CROSS",
    # Wskaźniki techniczne (3)
    "OBV_DIVERGENCE",
    "ATR_EXPANSION",
    "FIBONACCI_HIT",
)

assert len(_EVENT_TYPES) == len(set(_EVENT_TYPES)), "duplicate event_type detected"


# =========================================================================
# Helper utilities
# =========================================================================


def _make_price_data(md: MarketData, prev_md: MarketData | None = None) -> PriceData:
    """Build a PriceData snapshot from one or two MarketData entries."""
    prev_close = prev_md.close if prev_md is not None else md.open
    change_abs = md.close - prev_close
    change_pct = (change_abs / prev_close * 100.0) if prev_close != 0 else 0.0
    return PriceData(
        open=md.open,
        high=md.high,
        low=md.low,
        close=md.close,
        prev_close=prev_close,
        change_pct=change_pct,
        change_abs=change_abs,
    )


def _make_volume_data(
    md: MarketData,
    avg_volume: float,
    direction: str = "neutral",
) -> VolumeData:
    """Build a VolumeData snapshot."""
    volume_ratio = md.volume / avg_volume if avg_volume > 0 else 0.0
    return VolumeData(
        current_volume=md.volume,
        avg_volume=avg_volume,
        volume_ratio=volume_ratio,
        direction=direction,
    )


def _clip_confidence(value: float) -> float:
    """Clamp confidence to [0.0, 1.0]."""
    return max(0.0, min(1.0, value))


def _avg_volume(data: list[MarketData]) -> float:
    """Average volume across all candles."""
    volumes = [d.volume for d in data if d.volume >= 0]
    return sum(volumes) / len(volumes) if volumes else 0.0


def _direction(md: MarketData) -> str:
    """Return 'up', 'down', or 'neutral' based on close vs open."""
    if md.close > md.open:
        return "up"
    if md.close < md.open:
        return "down"
    return "neutral"


# =========================================================================
# TechnicalEventDetector
# =========================================================================


class TechnicalEventDetector(BaseDetector):
    """
    Detector for the TECHNICAL event family (29 implementable events).

    Events not detectable with current DetectionContext data:
        TRIANGLE_BREAKOUT, CHANNEL_BREAKOUT, FLAG_PENNANT_BREAKOUT,
        STOCHASTIC_EXTREME, VWAP_DEVIATION

    All detection is deterministic, does not mutate input, and uses
    only the OHLCV data provided in DetectionContext.
    """

    def __init__(self, config: TechnicalEventsConfig | None = None) -> None:
        self._config = config or DEFAULT_TECHNICAL_CONFIG

    # -----------------------------------------------------------------
    # BaseDetector abstract properties
    # -----------------------------------------------------------------

    @property
    def detector_id(self) -> str:
        return "technical"

    @property
    def name(self) -> str:
        return "Technical Event Detector"

    @property
    def event_types(self) -> tuple[str, ...]:
        return _EVENT_TYPES

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------

    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run all technical detection rules on the given context.

        Returns:
            list[DetectionResult] — ordered by event_types index,
            one result per detected event type at most.
        """
        data = list(context.ohlcv_data)

        if len(data) < 2:
            return []

        latest = data[-1]
        prev = data[-2]
        price_data = _make_price_data(latest, prev)

        results: list[DetectionResult] = []

        # Each private method returns list[DetectionResult]
        results.extend(self._detect_volatility_events(data, latest, price_data))
        results.extend(self._detect_breakout_events(data, latest, price_data))
        results.extend(self._detect_candle_events(data, latest, price_data))
        results.extend(self._detect_trend_events(data, latest, price_data))
        results.extend(self._detect_momentum_events(data, latest, price_data))
        results.extend(self._detect_indicator_events(data, latest, price_data))

        # Stabilise order by event_types index (deduplicate by event_type)
        order_map = {et: idx for idx, et in enumerate(_EVENT_TYPES)}
        seen: set[str] = set()
        ordered: list[DetectionResult] = []
        for r in results:
            if r.event_type not in seen:
                seen.add(r.event_type)
                ordered.append(r)
        ordered.sort(key=lambda r: order_map.get(r.event_type, 999))
        return ordered

    # =================================================================
    # 3. Zmienność  (VOLATILITY_SPIKE, VOLATILITY_CONTRACTION,
    #                BB_EXPANSION, BB_SQUEEZE)
    # =================================================================

    def _detect_volatility_events(
        self,
        data: list[MarketData],
        latest: MarketData,
        price_data: PriceData,
    ) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        cfg = self._config

        # --- ATR-based (3.1, 3.2, 8.3) ------------------------------------
        need_atr = cfg.atr_window + cfg.volatility_lookback
        if len(data) >= cfg.atr_window + 1:
            atr_vals = calculate_atr(data, cfg.atr_window)
            if len(atr_vals) >= cfg.volatility_lookback + 1:
                recent_atr = atr_vals[-cfg.volatility_lookback:]  # noqa: F841
                # atr_vals is List[float]; last element is the most recent ATR
                current_atr = atr_vals[-1]
                avg_atr = sum(atr_vals[-cfg.volatility_lookback:]) / cfg.volatility_lookback
                if avg_atr > 0:
                    atr_ratio = current_atr / avg_atr

                    # VOLATILITY_SPIKE
                    if atr_ratio >= cfg.volatility_spike_threshold:
                        confidence = _clip_confidence(
                            (atr_ratio - 1.0) / cfg.confidence_scale_factor
                        )
                        results.append(
                            DetectionResult(
                                event_type="VOLATILITY_SPIKE",
                                confidence_level=confidence,
                                price_data=price_data,
                            )
                        )

                    # VOLATILITY_CONTRACTION
                    if atr_ratio <= cfg.volatility_contraction_threshold and atr_ratio > 0:
                        confidence = _clip_confidence(
                            (1.0 - atr_ratio) / cfg.confidence_scale_factor
                        )
                        results.append(
                            DetectionResult(
                                event_type="VOLATILITY_CONTRACTION",
                                confidence_level=confidence,
                                price_data=price_data,
                            )
                        )

        # --- Bollinger Bands (3.3, 3.4) ------------------------------------
        bb_min = cfg.bb_window + cfg.bb_width_lookback
        if len(data) >= cfg.bb_window:
            upper, middle, lower = calculate_bollinger_bands(
                data, cfg.bb_window, cfg.bb_num_std
            )
            if len(upper) > cfg.bb_width_lookback:
                # Compute widths
                widths = [
                    (u - l) if (u is not None and l is not None) else None
                    for u, l in zip(upper, lower)
                ]
                # Most recent valid widths
                recent_widths = [w for w in widths[-cfg.bb_width_lookback:] if w is not None]
                if recent_widths:
                    current_width = recent_widths[-1]
                    avg_width = sum(recent_widths) / len(recent_widths)
                    if avg_width > 0:
                        width_ratio = current_width / avg_width

                        # BB_EXPANSION
                        if width_ratio >= cfg.bb_expansion_threshold:
                            confidence = _clip_confidence(
                                (width_ratio - 1.0) / cfg.confidence_scale_factor
                            )
                            results.append(
                                DetectionResult(
                                    event_type="BB_EXPANSION",
                                    confidence_level=confidence,
                                    price_data=price_data,
                                )
                            )

                        # BB_SQUEEZE
                        if width_ratio <= cfg.bb_squeeze_threshold and width_ratio > 0:
                            confidence = _clip_confidence(
                                (1.0 - width_ratio) / cfg.confidence_scale_factor
                            )
                            results.append(
                                DetectionResult(
                                    event_type="BB_SQUEEZE",
                                    confidence_level=confidence,
                                    price_data=price_data,
                                )
                            )

        return results

    # =================================================================
    # 4. Wybicia techniczne (RESISTANCE_BREAKOUT, SUPPORT_BREAKDOWN)
    # =================================================================

    def _detect_breakout_events(
        self,
        data: list[MarketData],
        latest: MarketData,
        price_data: PriceData,
    ) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        cfg = self._config

        if len(data) < cfg.breakout_lookback + 1:
            return results

        # Lookback: exclude the current (last) candle to find recent swing points
        lookback_data = data[-(cfg.breakout_lookback + 1):-1]
        if not lookback_data:
            return results

        recent_high = max(d.high for d in lookback_data)
        recent_low = min(d.low for d in lookback_data)

        # RESISTANCE_BREAKOUT
        if latest.close > recent_high:
            breakout_pct = (latest.close - recent_high) / recent_high * 100.0
            if breakout_pct >= 0:  # always true but explicit
                confidence = _clip_confidence(breakout_pct / cfg.confidence_scale_factor)
                results.append(
                    DetectionResult(
                        event_type="RESISTANCE_BREAKOUT",
                        confidence_level=_clip_confidence(max(0.1, confidence)),
                        price_data=price_data,
                    )
                )

        # SUPPORT_BREAKDOWN
        if latest.close < recent_low:
            breakdown_pct = (recent_low - latest.close) / recent_low * 100.0
            confidence = _clip_confidence(breakdown_pct / cfg.confidence_scale_factor)
            results.append(
                DetectionResult(
                    event_type="SUPPORT_BREAKDOWN",
                    confidence_level=_clip_confidence(max(0.1, confidence)),
                    price_data=price_data,
                )
            )

        return results

    # =================================================================
    # 5. Formacje świecowe  (10 event types)
    # =================================================================

    def _detect_candle_events(
        self,
        data: list[MarketData],
        latest: MarketData,
        price_data: PriceData,
    ) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        cfg = self._config

        if len(data) < 2:
            return results

        prev = data[-2]
        latest_analysis = analyze_candle(latest)
        prev_analysis = analyze_candle(prev)

        if latest_analysis is None:
            return results

        total_range = latest_analysis.total_range
        body_pct = latest_analysis.body_percentage
        upper_wick_pct = latest_analysis.upper_wick_percentage
        lower_wick_pct = latest_analysis.lower_wick_percentage
        _dir = latest_analysis.direction
        body_to_wicks = latest_analysis.body_to_wicks_ratio

        # --- HAMMER_HANGING_MAN (5.1) ---
        # Long lower wick, small/no upper wick, body small relative to lower wick
        if (
            lower_wick_pct >= upper_wick_pct * 2
            and latest_analysis.lower_wick_length >= latest_analysis.body_size * cfg.hammer_wick_body_ratio
            and upper_wick_pct <= cfg.hammer_upper_wick_max_pct
            and total_range > 0
        ):
            strength = (
                latest_analysis.lower_wick_length / max(total_range, 0.0001)
            ) / cfg.confidence_scale_factor
            results.append(
                DetectionResult(
                    event_type="HAMMER_HANGING_MAN",
                    confidence_level=_clip_confidence(strength),
                    price_data=price_data,
                )
            )

        # --- SHOOTING_STAR_INV_HAMMER (5.2) ---
        # Long upper wick, small/no lower wick
        if (
            upper_wick_pct >= lower_wick_pct * 2
            and latest_analysis.upper_wick_length >= latest_analysis.body_size * cfg.shooting_star_wick_body_ratio
            and lower_wick_pct <= cfg.shooting_star_lower_wick_max_pct
            and total_range > 0
        ):
            strength = (
                latest_analysis.upper_wick_length / max(total_range, 0.0001)
            ) / cfg.confidence_scale_factor
            results.append(
                DetectionResult(
                    event_type="SHOOTING_STAR_INV_HAMMER",
                    confidence_level=_clip_confidence(strength),
                    price_data=price_data,
                )
            )

        # --- DOJI (5.5) ---
        if body_pct <= cfg.doji_body_max_pct and total_range > 0:
            strength = (1.0 - body_pct / cfg.doji_body_max_pct) / cfg.confidence_scale_factor
            results.append(
                DetectionResult(
                    event_type="DOJI",
                    confidence_level=_clip_confidence(strength),
                    price_data=price_data,
                )
            )

        # --- MARUBOZU (5.9) ---
        if body_pct >= cfg.marubozu_body_min_pct and total_range > 0:
            strength = (body_pct / 100.0) / cfg.confidence_scale_factor
            results.append(
                DetectionResult(
                    event_type="MARUBOZU",
                    confidence_level=_clip_confidence(strength),
                    price_data=price_data,
                )
            )

        # Two-candle patterns (need prev candle analysis)
        if prev_analysis is not None and len(data) >= 2:
            # --- BULLISH_ENGULFING (5.3) ---
            if (
                _dir == "up"
                and prev_analysis.direction == "down"
                and latest_analysis.body_size > prev_analysis.body_size * cfg.engulfing_body_ratio
                and latest.open < prev.close
                and latest.close > prev.open
            ):
                strength = (
                    latest_analysis.body_size / max(prev_analysis.body_size, 0.0001)
                ) / (cfg.confidence_scale_factor * 2)
                results.append(
                    DetectionResult(
                        event_type="BULLISH_ENGULFING",
                        confidence_level=_clip_confidence(strength),
                        price_data=price_data,
                    )
                )

            # --- BEARISH_ENGULFING (5.4) ---
            if (
                _dir == "down"
                and prev_analysis.direction == "up"
                and latest_analysis.body_size > prev_analysis.body_size * cfg.engulfing_body_ratio
                and latest.open > prev.close
                and latest.close < prev.open
            ):
                strength = (
                    latest_analysis.body_size / max(prev_analysis.body_size, 0.0001)
                ) / (cfg.confidence_scale_factor * 2)
                results.append(
                    DetectionResult(
                        event_type="BEARISH_ENGULFING",
                        confidence_level=_clip_confidence(strength),
                        price_data=price_data,
                    )
                )

            # --- HARAMI (5.10) ---
            if (
                latest_analysis.body_size <= prev_analysis.body_size * cfg.harami_body_ratio
                and latest.high <= prev.high
                and latest.low >= prev.low
                and prev_analysis.body_size > 0
            ):
                strength = (
                    1.0 - latest_analysis.body_size / max(prev_analysis.body_size, 0.0001)
                ) / cfg.confidence_scale_factor
                results.append(
                    DetectionResult(
                        event_type="HARAMI",
                        confidence_level=_clip_confidence(strength),
                        price_data=price_data,
                    )
                )

        # Three-candle patterns
        if len(data) >= 3:
            d1, d2, d3 = data[-3], data[-2], data[-1]
            a1, a2 = analyze_candle(d1), analyze_candle(d2)

            # --- MORNING_EVENING_STAR (5.6) ---
            if a1 is not None:
                first_body = abs(d1.close - d1.open)
                second_body = abs(d2.close - d2.open)
                third_body = abs(d3.close - d3.open)
                first_range = d1.high - d1.low

                # Morning Star: down, small middle (gap down optional), up third piercing into first
                if (
                    a1.direction == "down"
                    and second_body <= first_body * cfg.star_middle_body_max_pct / 100.0
                    and _direction(d3) == "up"
                    and d3.close > (d1.open + d1.close) / 2  # closes above midpoint of first
                ):
                    strength = 0.5
                    results.append(
                        DetectionResult(
                            event_type="MORNING_EVENING_STAR",
                            confidence_level=_clip_confidence(strength),
                            price_data=price_data,
                        )
                    )

                # Evening Star: up, small middle, down third piercing into first
                if (
                    a1.direction == "up"
                    and second_body <= first_body * cfg.star_middle_body_max_pct / 100.0
                    and _direction(d3) == "down"
                    and d3.close < (d1.open + d1.close) / 2
                ):
                    strength = 0.5
                    results.append(
                        DetectionResult(
                            event_type="MORNING_EVENING_STAR",
                            confidence_level=_clip_confidence(strength),
                            price_data=price_data,
                        )
                    )

            # --- THREE_WHITE_SOLDIERS (5.7) ---
            if (
                _direction(d1) == "up"
                and _direction(d2) == "up"
                and _direction(d3) == "up"
                and d1.close > d1.open
                and d2.close > d2.open
                and d3.close > d3.open
                and d2.close > d1.close
                and d3.close > d2.close
                and d2.open >= d1.open
                and d2.open <= d1.close
                and d3.open >= d2.open
                and d3.open <= d2.close
            ):
                # Calculate body percentages
                bp1 = abs(d1.close - d1.open) / max(d1.high - d1.low, 0.0001) * 100
                bp2 = abs(d2.close - d2.open) / max(d2.high - d2.low, 0.0001) * 100
                bp3 = abs(d3.close - d3.open) / max(d3.high - d3.low, 0.0001) * 100
                if (
                    bp1 >= cfg.three_soldiers_min_body_pct
                    and bp2 >= cfg.three_soldiers_min_body_pct
                    and bp3 >= cfg.three_soldiers_min_body_pct
                ):
                    strength = min(bp1, bp2, bp3) / 100.0
                    results.append(
                        DetectionResult(
                            event_type="THREE_WHITE_SOLDIERS",
                            confidence_level=_clip_confidence(strength),
                            price_data=price_data,
                        )
                    )

            # --- THREE_BLACK_CROWS (5.8) ---
            if (
                _direction(d1) == "down"
                and _direction(d2) == "down"
                and _direction(d3) == "down"
                and d1.close < d1.open
                and d2.close < d2.open
                and d3.close < d3.open
                and d2.close < d1.close
                and d3.close < d2.close
                and d2.open <= d1.open
                and d2.open >= d1.close
                and d3.open <= d2.open
                and d3.open >= d2.close
            ):
                bp1 = abs(d1.close - d1.open) / max(d1.high - d1.low, 0.0001) * 100
                bp2 = abs(d2.close - d2.open) / max(d2.high - d2.low, 0.0001) * 100
                bp3 = abs(d3.close - d3.open) / max(d3.high - d3.low, 0.0001) * 100
                if (
                    bp1 >= cfg.three_soldiers_min_body_pct
                    and bp2 >= cfg.three_soldiers_min_body_pct
                    and bp3 >= cfg.three_soldiers_min_body_pct
                ):
                    strength = min(bp1, bp2, bp3) / 100.0
                    results.append(
                        DetectionResult(
                            event_type="THREE_BLACK_CROWS",
                            confidence_level=_clip_confidence(strength),
                            price_data=price_data,
                        )
                    )

        return results

    # =================================================================
    # 6. Trend  (MA_CROSSOVER, MA_SLOPE_CHANGE, PRICE_VS_MA,
    #            CONSECUTIVE_CANDLES, TREND_STRUCTURE_CHANGE)
    # =================================================================

    def _detect_trend_events(
        self,
        data: list[MarketData],
        latest: MarketData,
        price_data: PriceData,
    ) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        cfg = self._config

        # --- MA_CROSSOVER (6.1) ----------------------------------------
        max_ma = max(cfg.ma_fast_window, cfg.ma_slow_window)
        if len(data) >= max_ma + 1:
            sma_fast = calculate_sma(data, cfg.ma_fast_window)
            sma_slow = calculate_sma(data, cfg.ma_slow_window)

            # Need at least 2 computed values to detect a cross
            valid_fast = [v for v in sma_fast if v is not None]
            valid_slow = [v for v in sma_slow if v is not None]
            if len(valid_fast) >= 2 and len(valid_slow) >= 2:
                prev_fast = sma_fast[-2]
                prev_slow = sma_slow[-2]
                curr_fast = sma_fast[-1]
                curr_slow = sma_slow[-1]

                if (
                    prev_fast is not None
                    and prev_slow is not None
                    and curr_fast is not None
                    and curr_slow is not None
                ):
                    # Golden cross: fast crosses above slow
                    if prev_fast <= prev_slow and curr_fast > curr_slow:
                        delta = (curr_fast - curr_slow) / max(abs(curr_slow), 0.0001)
                        strength = _clip_confidence(abs(delta) * 10.0 / cfg.confidence_scale_factor)
                        results.append(
                            DetectionResult(
                                event_type="MA_CROSSOVER",
                                confidence_level=strength,
                                price_data=price_data,
                            )
                        )
                    # Death cross: fast crosses below slow
                    elif prev_fast >= prev_slow and curr_fast < curr_slow:
                        delta = (curr_slow - curr_fast) / max(abs(curr_slow), 0.0001)
                        strength = _clip_confidence(abs(delta) * 10.0 / cfg.confidence_scale_factor)
                        results.append(
                            DetectionResult(
                                event_type="MA_CROSSOVER",
                                confidence_level=strength,
                                price_data=price_data,
                            )
                        )

        # --- MA_SLOPE_CHANGE (6.2) -------------------------------------
        need_slope = cfg.ma_slope_window + cfg.ma_slope_lookback
        if len(data) >= cfg.ma_slope_window + 1:
            sma_vals = calculate_sma(data, cfg.ma_slope_window)
            valid_sma = [v for v in sma_vals if v is not None]
            if len(valid_sma) >= cfg.ma_slope_lookback + 1:
                recent = valid_sma[-(cfg.ma_slope_lookback + 1):]
                # Check if slope changed sign
                old_slope = sum(
                    recent[i + 1] - recent[i] for i in range(cfg.ma_slope_lookback - 1)
                ) / (cfg.ma_slope_lookback - 1)
                new_slope = recent[-1] - recent[-2]
                if (old_slope > 0 and new_slope < 0) or (old_slope < 0 and new_slope > 0):
                    strength = abs(new_slope - old_slope) / max(abs(old_slope) + abs(new_slope), 0.0001)
                    results.append(
                        DetectionResult(
                            event_type="MA_SLOPE_CHANGE",
                            confidence_level=_clip_confidence(strength),
                            price_data=price_data,
                        )
                    )

        # --- PRICE_VS_MA (6.3) -----------------------------------------
        if len(data) >= cfg.price_vs_ma_window + 1:
            sma_long = calculate_sma(data, cfg.price_vs_ma_window)
            valid_long = [v for v in sma_long if v is not None]
            if len(valid_long) >= 2:
                prev_sma = sma_long[-2]
                curr_sma = sma_long[-1]
                prev_close = data[-2].close
                if (
                    prev_sma is not None
                    and curr_sma is not None
                    and curr_sma > 0
                ):
                    # Price crossed above MA
                    if prev_close <= prev_sma and latest.close > curr_sma:
                        delta = abs(latest.close - curr_sma) / curr_sma
                        results.append(
                            DetectionResult(
                                event_type="PRICE_VS_MA",
                                confidence_level=_clip_confidence(delta * 10.0),
                                price_data=price_data,
                            )
                        )
                    # Price crossed below MA
                    elif prev_close >= prev_sma and latest.close < curr_sma:
                        delta = abs(latest.close - curr_sma) / curr_sma
                        results.append(
                            DetectionResult(
                                event_type="PRICE_VS_MA",
                                confidence_level=_clip_confidence(delta * 10.0),
                                price_data=price_data,
                            )
                        )

        # --- CONSECUTIVE_CANDLES (6.4) ----------------------------------
        if len(data) >= cfg.consecutive_candles_min:
            # Check last N candles
            lookback = data[-cfg.consecutive_candles_min:]
            all_up = all(d.close > d.open for d in lookback)
            all_down = all(d.close < d.open for d in lookback)
            if all_up:
                strength = len(lookback) / (cfg.consecutive_candles_min * 2)
                results.append(
                    DetectionResult(
                        event_type="CONSECUTIVE_CANDLES",
                        confidence_level=_clip_confidence(strength),
                        price_data=price_data,
                    )
                )
            elif all_down:
                strength = len(lookback) / (cfg.consecutive_candles_min * 2)
                results.append(
                    DetectionResult(
                        event_type="CONSECUTIVE_CANDLES",
                        confidence_level=_clip_confidence(strength),
                        price_data=price_data,
                    )
                )

        # --- TREND_STRUCTURE_CHANGE (6.5) --------------------------------
        if len(data) >= cfg.swing_lookback * 4:
            # Find swing highs and lows
            swings_high = self._find_swings(data, "high")
            swings_low = self._find_swings(data, "low")
            if len(swings_high) >= 2 and len(swings_low) >= 2:
                # Higher low after lower lows = bullish structure change
                last_two_lows = swings_low[-2:]
                if last_two_lows[0] < last_two_lows[1]:
                    # Check we had a series of lower lows before
                    if len(swings_low) >= 3 and all(
                        swings_low[i] < swings_low[i + 1]
                        for i in range(len(swings_low) - 3)
                    ):
                        strength = 0.6
                        results.append(
                            DetectionResult(
                                event_type="TREND_STRUCTURE_CHANGE",
                                confidence_level=strength,
                                price_data=price_data,
                            )
                        )
                # Lower high after higher highs = bearish structure change
                last_two_highs = swings_high[-2:]
                if last_two_highs[0] > last_two_highs[1]:
                    if len(swings_high) >= 3 and all(
                        swings_high[i] > swings_high[i + 1]
                        for i in range(len(swings_high) - 3)
                    ):
                        strength = 0.6
                        results.append(
                            DetectionResult(
                                event_type="TREND_STRUCTURE_CHANGE",
                                confidence_level=strength,
                                price_data=price_data,
                            )
                        )

        return results

    @staticmethod
    def _find_swings(data: list[MarketData], field: str) -> list[float]:
        """Identify swing points (peaks for 'high', troughs for 'low')."""
        lookback = 3
        result = []
        for i in range(lookback, len(data) - lookback):
            window = data[i - lookback : i + lookback + 1]
            if field == "high":
                vals = [d.high for d in window]
                if max(vals[:lookback]) < vals[lookback] and max(vals[lookback + 1:]) < vals[lookback]:
                    result.append(vals[lookback])
            else:
                vals = [d.low for d in window]
                if min(vals[:lookback]) > vals[lookback] and min(vals[lookback + 1:]) > vals[lookback]:
                    result.append(vals[lookback])
        return result

    # =================================================================
    # 7. Momentum  (RSI_OVERBOUGHT, RSI_OVERSOLD, RSI_DIVERGENCE,
    #               MACD_LINE_CROSSOVER, MACD_ZERO_CROSS)
    # =================================================================

    def _detect_momentum_events(
        self,
        data: list[MarketData],
        latest: MarketData,
        price_data: PriceData,
    ) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        cfg = self._config

        # --- RSI (7.1, 7.2, 7.3) ---------------------------------------
        if len(data) >= cfg.rsi_window + 1:
            try:
                rsi_vals = calculate_rsi(data, cfg.rsi_window)
                valid_rsi = [v for v in rsi_vals if v is not None]
                if valid_rsi:
                    latest_rsi = valid_rsi[-1]

                    # RSI_OVERBOUGHT
                    if latest_rsi >= cfg.rsi_overbought:
                        confidence = _clip_confidence(
                            (latest_rsi - cfg.rsi_overbought) / (100.0 - cfg.rsi_overbought)
                        )
                        results.append(
                            DetectionResult(
                                event_type="RSI_OVERBOUGHT",
                                confidence_level=confidence,
                                price_data=price_data,
                            )
                        )

                    # RSI_OVERSOLD
                    if latest_rsi <= cfg.rsi_oversold:
                        confidence = _clip_confidence(
                            (cfg.rsi_oversold - latest_rsi) / cfg.rsi_oversold
                        )
                        results.append(
                            DetectionResult(
                                event_type="RSI_OVERSOLD",
                                confidence_level=confidence,
                                price_data=price_data,
                            )
                        )

                    # RSI_DIVERGENCE
                    div_lookback = cfg.rsi_divergence_lookback
                    if len(valid_rsi) >= div_lookback and len(data) >= div_lookback:
                        rsi_window_vals = valid_rsi[-div_lookback:]
                        price_close_vals = [d.close for d in data[-div_lookback:]]
                        if len(rsi_window_vals) >= 5 and len(price_close_vals) >= 5:
                            rsi_high_idx = rsi_window_vals.index(max(rsi_window_vals))
                            price_high_idx = price_close_vals.index(max(price_close_vals))
                            rsi_low_idx = rsi_window_vals.index(min(rsi_window_vals))
                            price_low_idx = price_close_vals.index(min(price_close_vals))

                            # Bearish divergence: price higher high, RSI lower high
                            if (
                                price_high_idx > rsi_high_idx
                                and price_close_vals[price_high_idx]
                                > price_close_vals[price_high_idx - 1]
                            ):
                                results.append(
                                    DetectionResult(
                                        event_type="RSI_DIVERGENCE",
                                        confidence_level=0.6,
                                        price_data=price_data,
                                    )
                                )
                            # Bullish divergence: price lower low, RSI higher low
                            elif (
                                price_low_idx > rsi_low_idx
                                and price_close_vals[price_low_idx]
                                < price_close_vals[price_low_idx - 1]
                            ):
                                results.append(
                                    DetectionResult(
                                        event_type="RSI_DIVERGENCE",
                                        confidence_level=0.6,
                                        price_data=price_data,
                                    )
                                )
            except (ValueError, ZeroDivisionError):
                pass

        # --- MACD (7.4, 7.5) -------------------------------------------
        macd_min = max(cfg.macd_slow, cfg.macd_signal) + 1
        if len(data) >= cfg.macd_slow + 1:
            try:
                macd_line = calculate_macd_line(data, cfg.macd_fast, cfg.macd_slow)
                signal = calculate_signal_line(macd_line, cfg.macd_signal)

                valid_macd = [v for v in macd_line if v is not None]
                valid_sig = [v for v in signal if v is not None]
                if len(valid_macd) >= 2 and len(valid_sig) >= 2:
                    prev_macd = macd_line[-2]
                    prev_sig = signal[-2]
                    curr_macd = macd_line[-1]
                    curr_sig = signal[-1]

                    if (
                        prev_macd is not None
                        and prev_sig is not None
                        and curr_macd is not None
                        and curr_sig is not None
                    ):
                        # MACD_LINE_CROSSOVER — strictly checks the last
                        # two valid MACD/Signal pairs for a crossover.
                        if prev_macd <= prev_sig and curr_macd > curr_sig:
                            delta = abs(curr_macd - curr_sig) / max(abs(curr_sig), 0.0001)
                            results.append(
                                DetectionResult(
                                    event_type="MACD_LINE_CROSSOVER",
                                    confidence_level=_clip_confidence(delta),
                                    price_data=price_data,
                                )
                            )
                        elif prev_macd >= prev_sig and curr_macd < curr_sig:
                            delta = abs(curr_macd - curr_sig) / max(abs(curr_sig), 0.0001)
                            results.append(
                                DetectionResult(
                                    event_type="MACD_LINE_CROSSOVER",
                                    confidence_level=_clip_confidence(delta),
                                    price_data=price_data,
                                )
                            )

                        # MACD_ZERO_CROSS
                        if prev_macd <= 0 and curr_macd > 0:
                            delta = abs(curr_macd) / max(abs(prev_macd - curr_macd), 0.0001)
                            results.append(
                                DetectionResult(
                                    event_type="MACD_ZERO_CROSS",
                                    confidence_level=_clip_confidence(delta),
                                    price_data=price_data,
                                )
                            )
                        elif prev_macd >= 0 and curr_macd < 0:
                            delta = abs(curr_macd) / max(abs(prev_macd - curr_macd), 0.0001)
                            results.append(
                                DetectionResult(
                                    event_type="MACD_ZERO_CROSS",
                                    confidence_level=_clip_confidence(delta),
                                    price_data=price_data,
                                )
                            )
            except (ValueError, ZeroDivisionError):
                pass

        return results

    # =================================================================
    # 8. Wskaźniki techniczne  (OBV_DIVERGENCE, ATR_EXPANSION,
    #                           FIBONACCI_HIT)
    # =================================================================

    def _detect_indicator_events(
        self,
        data: list[MarketData],
        latest: MarketData,
        price_data: PriceData,
    ) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        cfg = self._config

        # --- OBV_DIVERGENCE (8.1) ---------------------------------------
        obv_lookback = cfg.obv_divergence_lookback
        if len(data) >= obv_lookback + 1:
            obv_vals = calculate_obv(data)
            if len(obv_vals) >= obv_lookback:
                obv_window = obv_vals[-obv_lookback:]
                price_window = [d.close for d in data[-obv_lookback:]]
                if len(obv_window) >= 3:
                    obv_start, obv_end = obv_window[0], obv_window[-1]
                    price_start, price_end = price_window[0], price_window[-1]

                    # OBV divergence: price up, OBV down (bearish)
                    if price_end > price_start and obv_end < obv_start:
                        strength = _clip_confidence(
                            (price_end / max(price_start, 0.0001) - 1.0)
                            * abs(obv_start - obv_end) / max(abs(obv_start), 0.0001)
                        )
                        results.append(
                            DetectionResult(
                                event_type="OBV_DIVERGENCE",
                                confidence_level=strength,
                                price_data=price_data,
                            )
                        )
                    # OBV divergence: price down, OBV up (bullish)
                    elif price_end < price_start and obv_end > obv_start:
                        strength = _clip_confidence(
                            (1.0 - price_end / max(price_start, 0.0001))
                            * abs(obv_end - obv_start) / max(abs(obv_start), 0.0001)
                        )
                        results.append(
                            DetectionResult(
                                event_type="OBV_DIVERGENCE",
                                confidence_level=strength,
                                price_data=price_data,
                            )
                        )

        # --- ATR_EXPANSION (8.3) — already handled in volatility events ---
        # Check if ATR spike was already detected; emit ATR_EXPANSION independently
        need_atr = cfg.atr_window + cfg.volatility_lookback
        if len(data) >= cfg.atr_window + 1:
            atr_vals = calculate_atr(data, cfg.atr_window)
            if len(atr_vals) >= cfg.volatility_lookback + 1:
                current_atr = atr_vals[-1]
                avg_atr = sum(atr_vals[-cfg.volatility_lookback:]) / cfg.volatility_lookback
                if avg_atr > 0:
                    atr_ratio = current_atr / avg_atr
                    if atr_ratio >= cfg.volatility_spike_threshold:
                        confidence = _clip_confidence(
                            (atr_ratio - 1.0) / cfg.confidence_scale_factor
                        )
                        results.append(
                            DetectionResult(
                                event_type="ATR_EXPANSION",
                                confidence_level=confidence,
                                price_data=price_data,
                            )
                        )

        # --- FIBONACCI_HIT (8.4) ----------------------------------------
        if len(data) >= cfg.swing_lookback * 3:
            swings_high = self._find_swings(data, "high")
            swings_low = self._find_swings(data, "low")
            if swings_high and swings_low:
                # Use most recent swing high and low
                recent_high = swings_high[-1]
                recent_low = swings_low[-1]
                if recent_high > recent_low:
                    diff = recent_high - recent_low
                    for level in cfg.fibo_levels:
                        fib_price = recent_high - diff * level
                        tolerance = diff * cfg.fibo_tolerance_pct / 100.0
                        if abs(latest.close - fib_price) <= tolerance:
                            results.append(
                                DetectionResult(
                                    event_type="FIBONACCI_HIT",
                                    confidence_level=_clip_confidence(
                                        0.5 + 0.5 * (1.0 - abs(latest.close - fib_price) / tolerance)
                                    ),
                                    price_data=price_data,
                                )
                            )
                        # Also check retracement from low to high
                        fib_price_up = recent_low + diff * level
                        if abs(latest.close - fib_price_up) <= tolerance:
                            results.append(
                                DetectionResult(
                                    event_type="FIBONACCI_HIT",
                                    confidence_level=_clip_confidence(
                                        0.5 + 0.5 * (1.0 - abs(latest.close - fib_price_up) / tolerance)
                                    ),
                                    price_data=price_data,
                                )
                            )

        return results