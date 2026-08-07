"""
Price Event Detector — core detection engine.

Detects 10 types of price-based market events from OHLCV data
provided by MarketScanner / YahooScanProvider.

All detection logic is based on the approved ALCHEMIK documentation:
  - Katalog Zdarzen Rynkowych v2.0 (§1.1–§1.10)
  - Hierarchia Zdarzen Rynkowych v1.0 (§4.1)
  - Przeplyw Zdarzen Rynkowych v1.0 (§2.1)
  - Kontrakt Zdarzen Rynkowych v1.0

The detector:
  - Reads OHLCV data (List[MarketData])
  - Creates MarketEvent via create_new() + set_detection()
  - Does NOT call AI, fetch news, send Telegram, or make investment decisions
  - Does NOT modify priority_final, quality_level, or perform deduplication
  - Does NOT depend on other detectors or modify engines/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from config.price_detector import DEFAULT_CONFIG, PriceDetectorConfig
from config.signal_timing import lookup_signal_timing
from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from data.models.price_data import PriceData


# ---------------------------------------------------------------------------
# Detection result — internal data class
# ---------------------------------------------------------------------------

@dataclass
class _DetectionResult:
    """Internal container for a single detection before MarketEvent creation."""

    event_type: str
    event_category: str
    event_subcategory: Optional[str]
    priority_raw: PriorityLevel
    confidence_level: float
    price_data: PriceData
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Price Detector
# ---------------------------------------------------------------------------

class PriceDetector:
    """
    Detects price-based market events from OHLCV data.

    Usage:
        detector = PriceDetector()
        events = detector.detect(
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=market_data_list,
        )

    Returns a list of MarketEvent objects (one per detected event type).
    Returns an empty list if no events are detected.
    """

    DETECTION_SOURCE = "Price Event Detector (TechnicalEngine)"

    def __init__(self, config: Optional[PriceDetectorConfig] = None):
        """
        Initialize the detector with optional custom configuration.

        Args:
            config: PriceDetectorConfig instance. Uses DEFAULT_CONFIG if None.
        """
        self._config = config or DEFAULT_CONFIG

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        ticker: str,
        market: str,
        instrument_type: InstrumentType,
        ohlcv_data: List[MarketData],
    ) -> List[MarketEvent]:
        """
        Run all price event detections on the given OHLCV data.

        Args:
            ticker: Instrument symbol (e.g., "XYZ.WA")
            market: Market identifier (e.g., "GPW", "NYSE")
            instrument_type: Instrument type classification
            ohlcv_data: List of MarketData candles sorted chronologically
                        (oldest first). Must contain at least 2 candles.

        Returns:
            List of MarketEvent objects, one per detected event.
            Empty list if no events detected or data insufficient.
        """
        if not ohlcv_data or len(ohlcv_data) < 2:
            return []

        # Ensure data is sorted by timestamp (oldest first)
        sorted_data = sorted(ohlcv_data, key=lambda d: d.timestamp)

        detections: List[_DetectionResult] = []

        # Run all 10 detectors
        detections.extend(self._detect_surge_drop(sorted_data))
        detections.extend(self._detect_gaps(sorted_data))
        detections.extend(self._detect_52w_extremes(sorted_data))
        detections.extend(self._detect_ath_atl(sorted_data))
        detections.extend(self._detect_level_rejection(sorted_data))
        detections.extend(self._detect_psych_level_cross(sorted_data))

        # Convert detections to MarketEvent objects
        events: List[MarketEvent] = []
        for det in detections:
            event = self._build_market_event(
                ticker=ticker,
                market=market,
                instrument_type=instrument_type,
                detection=det,
            )
            events.append(event)

        return events

    # ------------------------------------------------------------------
    # MarketEvent construction
    # ------------------------------------------------------------------

    def _build_market_event(
        self,
        ticker: str,
        market: str,
        instrument_type: InstrumentType,
        detection: _DetectionResult,
    ) -> MarketEvent:
        """
        Create a MarketEvent using the approved lifecycle methods.

        Stage 1: create_new() — sets identification fields
        Stage 2: set_detection() — sets detection fields
        """
        event = MarketEvent.create_new(
            ticker=ticker,
            market=market,
            instrument_type=instrument_type,
            event_type=detection.event_type,
        )

        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category=detection.event_category,
            event_type=detection.event_type,
            priority_raw=detection.priority_raw,
            confidence_level=detection.confidence_level,
            detection_source=self.DETECTION_SOURCE,
            event_owner=EventOwner.TechnicalEngine,
            event_subcategory=detection.event_subcategory,
            price_data=detection.price_data,
        )

        # Add detection-specific metadata
        if detection.metadata:
            event.metadata.update(detection.metadata)

        return event

    # ------------------------------------------------------------------
    # Helper: build PriceData from current + previous candle
    # ------------------------------------------------------------------

    @staticmethod
    def _build_price_data(
        current: MarketData,
        previous: MarketData,
    ) -> PriceData:
        """Build a PriceData object from two consecutive candles."""
        change_abs = current.close - previous.close
        change_pct = (change_abs / previous.close) * 100.0 if previous.close != 0 else 0.0
        return PriceData(
            open=current.open,
            high=current.high,
            low=current.low,
            close=current.close,
            prev_close=previous.close,
            change_pct=round(change_pct, 4),
            change_abs=round(change_abs, 4),
        )

    # ------------------------------------------------------------------
    # Helper: clamp confidence to [0.0, 1.0]
    # ------------------------------------------------------------------

    def _clamp_confidence(self, value: float) -> float:
        """Clamp confidence value to [min_confidence, max_confidence]."""
        return max(self._config.min_confidence, min(self._config.max_confidence, value))

    # ------------------------------------------------------------------
    # 1.1 PRICE_SURGE / 1.2 PRICE_DROP
    # Source: Katalog §1.1, §1.2
    # Condition: |change_pct| >= surge_threshold_pct
    # Priority: CRITICAL
    # ------------------------------------------------------------------

    def _detect_surge_drop(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """Detect Price Surge (1.1) and Price Drop (1.2)."""
        results: List[_DetectionResult] = []
        if len(data) < 2:
            return results

        current = data[-1]
        previous = data[-2]

        if previous.close == 0:
            return results

        change_pct = ((current.close - previous.close) / previous.close) * 100.0
        abs_change = abs(change_pct)

        if abs_change < self._config.surge_threshold_pct:
            return results

        price_data = self._build_price_data(current, previous)

        # Confidence: scales linearly from threshold to 2x threshold
        confidence = min(1.0, abs_change / self._config.surge_confidence_scale_pct)
        confidence = self._clamp_confidence(confidence)

        if change_pct > 0:
            results.append(_DetectionResult(
                event_type="PRICE_SURGE",
                event_category="Cenowe",
                event_subcategory="Ruchy kierunkowe",
                priority_raw=PriorityLevel.CRITICAL,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "change_pct": round(change_pct, 4),
                    "threshold_pct": self._config.surge_threshold_pct,
                    "detection_method": "price_move_detector",
                },
            ))
        else:
            results.append(_DetectionResult(
                event_type="PRICE_DROP",
                event_category="Cenowe",
                event_subcategory="Ruchy kierunkowe",
                priority_raw=PriorityLevel.CRITICAL,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "change_pct": round(change_pct, 4),
                    "threshold_pct": self._config.surge_threshold_pct,
                    "detection_method": "price_move_detector",
                },
            ))

        return results

    # ------------------------------------------------------------------
    # 1.3 GAP_UP / 1.4 GAP_DOWN
    # Source: Katalog §1.3, §1.4
    # Condition: open vs prev_close gap >= gap_threshold_pct
    # Priority: HIGH
    # ------------------------------------------------------------------

    def _detect_gaps(self, data: List[MarketData]) -> List[_DetectionResult]:
        """Detect Gap Up (1.3) and Gap Down (1.4)."""
        results: List[_DetectionResult] = []
        if len(data) < 2:
            return results

        current = data[-1]
        previous = data[-2]

        if previous.close == 0:
            return results

        gap_pct = ((current.open - previous.close) / previous.close) * 100.0
        abs_gap = abs(gap_pct)

        if abs_gap < self._config.gap_threshold_pct:
            return results

        # Stronger confirmation: check vs prev_high / prev_low
        confirmed = True
        if self._config.gap_vs_high_low:
            if gap_pct > 0:
                confirmed = current.open > previous.high
            else:
                confirmed = current.open < previous.low

        if not confirmed:
            return results

        price_data = self._build_price_data(current, previous)

        confidence = min(1.0, abs_gap / self._config.gap_confidence_scale_pct)
        confidence = self._clamp_confidence(confidence)

        if gap_pct > 0:
            results.append(_DetectionResult(
                event_type="GAP_UP",
                event_category="Cenowe",
                event_subcategory="Luki",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "gap_pct": round(gap_pct, 4),
                    "threshold_pct": self._config.gap_threshold_pct,
                    "prev_high": previous.high,
                    "prev_low": previous.low,
                    "detection_method": "gap_detector",
                },
            ))
        else:
            results.append(_DetectionResult(
                event_type="GAP_DOWN",
                event_category="Cenowe",
                event_subcategory="Luki",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "gap_pct": round(gap_pct, 4),
                    "threshold_pct": self._config.gap_threshold_pct,
                    "prev_high": previous.high,
                    "prev_low": previous.low,
                    "detection_method": "gap_detector",
                },
            ))

        return results

    # ------------------------------------------------------------------
    # 1.5 52W_HIGH / 1.6 52W_LOW
    # Source: Katalog §1.5, §1.6
    # Condition: current high/low is the max/min of last 260 candles
    # Priority: HIGH
    # ------------------------------------------------------------------

    def _detect_52w_extremes(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """Detect 52-Week High (1.5) and 52-Week Low (1.6)."""
        results: List[_DetectionResult] = []
        window = self._config.fifty_two_week_window

        if len(data) < 2:
            return results

        # Use up to `window` candles, excluding the current one
        lookback = data[-(window + 1):-1] if len(data) > window else data[:-1]

        if len(lookback) < 1:
            return results

        current = data[-1]
        previous = data[-2]

        max_high = max(c.high for c in lookback)
        min_low = min(c.low for c in lookback)

        price_data = self._build_price_data(current, previous)

        # 52-Week High
        if current.high > max_high:
            # Confidence: higher when the new high significantly exceeds the old
            margin_pct = ((current.high - max_high) / max_high) * 100.0 if max_high > 0 else 0.0
            confidence = min(1.0, 0.5 + margin_pct * 10.0)
            confidence = self._clamp_confidence(confidence)

            results.append(_DetectionResult(
                event_type="52W_HIGH",
                event_category="Cenowe",
                event_subcategory="Ekstrema",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "previous_52w_high": max_high,
                    "new_high": current.high,
                    "lookback_candles": len(lookback),
                    "detection_method": "extrema_detector",
                },
            ))

        # 52-Week Low
        if current.low < min_low:
            margin_pct = ((min_low - current.low) / min_low) * 100.0 if min_low > 0 else 0.0
            confidence = min(1.0, 0.5 + margin_pct * 10.0)
            confidence = self._clamp_confidence(confidence)

            results.append(_DetectionResult(
                event_type="52W_LOW",
                event_category="Cenowe",
                event_subcategory="Ekstrema",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "previous_52w_low": min_low,
                    "new_low": current.low,
                    "lookback_candles": len(lookback),
                    "detection_method": "extrema_detector",
                },
            ))

        return results

    # ------------------------------------------------------------------
    # 1.7 ATH / 1.8 ATL
    # Source: Katalog §1.7, §1.8
    # Condition: current high/low exceeds all historical highs/lows
    # Priority: HIGH for ATH, CRITICAL for ATL
    # ------------------------------------------------------------------

    def _detect_ath_atl(self, data: List[MarketData]) -> List[_DetectionResult]:
        """Detect All-Time High (1.7) and All-Time Low (1.8)."""
        results: List[_DetectionResult] = []

        if len(data) < self._config.ath_min_history:
            return results

        current = data[-1]
        previous = data[-2]
        history = data[:-1]  # All candles except current

        if len(history) < 1:
            return results

        max_high = max(c.high for c in history)
        min_low = min(c.low for c in history)

        price_data = self._build_price_data(current, previous)

        # ATH
        if current.high > max_high:
            margin_pct = ((current.high - max_high) / max_high) * 100.0 if max_high > 0 else 0.0
            confidence = min(1.0, 0.6 + margin_pct * 10.0)
            confidence = self._clamp_confidence(confidence)

            results.append(_DetectionResult(
                event_type="ATH",
                event_category="Cenowe",
                event_subcategory="Ekstrema",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "previous_ath": max_high,
                    "new_ath": current.high,
                    "total_history_candles": len(data),
                    "detection_method": "extrema_detector",
                },
            ))

        # ATL
        if current.low < min_low:
            margin_pct = ((min_low - current.low) / min_low) * 100.0 if min_low > 0 else 0.0
            confidence = min(1.0, 0.6 + margin_pct * 10.0)
            confidence = self._clamp_confidence(confidence)

            results.append(_DetectionResult(
                event_type="ATL",
                event_category="Cenowe",
                event_subcategory="Ekstrema",
                priority_raw=PriorityLevel.CRITICAL,
                confidence_level=confidence,
                price_data=price_data,
                metadata={
                    "previous_atl": min_low,
                    "new_atl": current.low,
                    "total_history_candles": len(data),
                    "detection_method": "extrema_detector",
                },
            ))

        return results

    # ------------------------------------------------------------------
    # 1.9 LEVEL_REJECTION
    # Source: Katalog §1.9
    # Condition: price approached a support/resistance level and
    #            rebounded sharply from it
    # Priority: HIGH
    # ------------------------------------------------------------------

    def _detect_level_rejection(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """
        Detect Level Rejection (1.9).

        Identifies swing highs (resistance) and swing lows (support)
        from recent candles, then checks if the current candle
        approached one of these levels and rebounded.
        """
        results: List[_DetectionResult] = []
        lookback = self._config.level_rejection_lookback
        strength = self._config.level_rejection_min_swing_strength

        if len(data) < lookback + 2:
            return results

        current = data[-1]
        previous = data[-2]
        recent = data[-(lookback + 1):-1]  # Exclude current candle

        # Find swing highs and swing lows
        swing_highs = self._find_swing_points(recent, strength, find_highs=True)
        swing_lows = self._find_swing_points(recent, strength, find_highs=False)

        price_data = self._build_price_data(current, previous)
        current_price = current.close

        # Check resistance rejection: price approached a resistance, then fell
        for res_level in swing_highs:
            proximity = abs(current.high - res_level) / res_level * 100.0
            if proximity <= self._config.level_rejection_proximity_pct:
                # Check rebound: close is significantly below the level
                rebound_pct = (res_level - current.close) / res_level * 100.0
                if rebound_pct >= self._config.level_rejection_rebound_pct:
                    confidence = min(1.0, 0.4 + rebound_pct / 5.0)
                    confidence = self._clamp_confidence(confidence)
                    results.append(_DetectionResult(
                        event_type="LEVEL_REJECTION",
                        event_category="Cenowe",
                        event_subcategory="Poziomy",
                        priority_raw=PriorityLevel.HIGH,
                        confidence_level=confidence,
                        price_data=price_data,
                        metadata={
                            "level_type": "resistance",
                            "level_value": res_level,
                            "approach_high": current.high,
                            "rebound_pct": round(rebound_pct, 4),
                            "detection_method": "level_detector",
                        },
                    ))
                    break  # One rejection per candle

        # Check support rejection: price approached a support, then rose
        for sup_level in swing_lows:
            proximity = abs(current.low - sup_level) / sup_level * 100.0
            if proximity <= self._config.level_rejection_proximity_pct:
                rebound_pct = (current.close - sup_level) / sup_level * 100.0
                if rebound_pct >= self._config.level_rejection_rebound_pct:
                    confidence = min(1.0, 0.4 + rebound_pct / 5.0)
                    confidence = self._clamp_confidence(confidence)
                    results.append(_DetectionResult(
                        event_type="LEVEL_REJECTION",
                        event_category="Cenowe",
                        event_subcategory="Poziomy",
                        priority_raw=PriorityLevel.HIGH,
                        confidence_level=confidence,
                        price_data=price_data,
                        metadata={
                            "level_type": "support",
                            "level_value": sup_level,
                            "approach_low": current.low,
                            "rebound_pct": round(rebound_pct, 4),
                            "detection_method": "level_detector",
                        },
                    ))
                    break

        return results

    @staticmethod
    def _find_swing_points(
        data: List[MarketData],
        strength: int,
        find_highs: bool = True,
    ) -> List[float]:
        """
        Find swing high or swing low points in the data.

        A swing high is a candle whose high is higher than `strength`
        candles on both sides. A swing low is a candle whose low is
        lower than `strength` candles on both sides.

        Args:
            data: List of MarketData candles
            strength: Number of candles on each side for confirmation
            find_highs: If True, find swing highs; if False, find swing lows

        Returns:
            List of swing point price levels
        """
        if len(data) < 2 * strength + 1:
            return []

        levels: List[float] = []
        for i in range(strength, len(data) - strength):
            if find_highs:
                candidate = data[i].high
                left_max = max(d.high for d in data[i - strength:i])
                right_max = max(d.high for d in data[i + 1:i + strength + 1])
                if candidate > left_max and candidate > right_max:
                    levels.append(candidate)
            else:
                candidate = data[i].low
                left_min = min(d.low for d in data[i - strength:i])
                right_min = min(d.low for d in data[i + 1:i + strength + 1])
                if candidate < left_min and candidate < right_min:
                    levels.append(candidate)

        return levels

    # ------------------------------------------------------------------
    # 1.10 PSYCH_LEVEL_CROSS
    # Source: Katalog §1.10
    # Condition: price crossed a round psychological level
    # Priority: MEDIUM
    # ------------------------------------------------------------------

    def _detect_psych_level_cross(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """
        Detect Psychological Level Cross (1.10).

        Checks if the current candle's close crossed a round level
        that the previous candle's close was on the other side of.
        """
        results: List[_DetectionResult] = []
        if len(data) < 2:
            return results

        current = data[-1]
        previous = data[-2]

        relevant_levels = self._config.get_psych_levels_for_price(current.close)
        price_data = self._build_price_data(current, previous)

        for level in relevant_levels:
            prev_above = previous.close > level
            curr_above = current.close > level

            # Cross from below to above (bullish)
            if not prev_above and curr_above:
                # Confirm: close is meaningfully above the level
                margin_pct = (current.close - level) / level * 100.0
                if margin_pct >= self._config.psych_level_proximity_pct:
                    confidence = min(1.0, 0.3 + margin_pct * 20.0)
                    confidence = self._clamp_confidence(confidence)
                    results.append(_DetectionResult(
                        event_type="PSYCH_LEVEL_CROSS",
                        event_category="Cenowe",
                        event_subcategory="Poziomy",
                        priority_raw=PriorityLevel.MEDIUM,
                        confidence_level=confidence,
                        price_data=price_data,
                        metadata={
                            "level": level,
                            "direction": "up",
                            "prev_close": previous.close,
                            "curr_close": current.close,
                            "detection_method": "psych_level_detector",
                        },
                    ))
                    break  # One cross per candle

            # Cross from above to below (bearish)
            elif prev_above and not curr_above:
                margin_pct = (level - current.close) / level * 100.0
                if margin_pct >= self._config.psych_level_proximity_pct:
                    confidence = min(1.0, 0.3 + margin_pct * 20.0)
                    confidence = self._clamp_confidence(confidence)
                    results.append(_DetectionResult(
                        event_type="PSYCH_LEVEL_CROSS",
                        event_category="Cenowe",
                        event_subcategory="Poziomy",
                        priority_raw=PriorityLevel.MEDIUM,
                        confidence_level=confidence,
                        price_data=price_data,
                        metadata={
                            "level": level,
                            "direction": "down",
                            "prev_close": previous.close,
                            "curr_close": current.close,
                            "detection_method": "psych_level_detector",
                        },
                    ))
                    break

        return results