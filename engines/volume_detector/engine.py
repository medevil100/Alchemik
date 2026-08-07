"""
Volume Event Detector — core detection engine.

Detects 5 types of volume-based market events from OHLCV data
provided by MarketScanner / YahooScanProvider.

All detection logic is based on the approved ALCHEMIK documentation:
  - Katalog Zdarzen Rynkowych v2.0 (§2.1–§2.5)
  - Hierarchia Zdarzen Rynkowych v1.0 (§4.2)
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

from config.volume_detector import DEFAULT_CONFIG, VolumeDetectorConfig
from config.signal_timing import lookup_signal_timing
from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from data.models.volume_data import VolumeData


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
    volume_data: VolumeData
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Volume Detector
# ---------------------------------------------------------------------------

class VolumeDetector:
    """
    Detects volume-based market events from OHLCV data.

    Usage:
        detector = VolumeDetector()
        events = detector.detect(
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=market_data_list,
        )

    Returns a list of MarketEvent objects (one per detected event type).
    Returns an empty list if no events are detected.
    """

    DETECTION_SOURCE = "Volume Event Detector (TechnicalEngine)"

    def __init__(self, config: Optional[VolumeDetectorConfig] = None):
        """
        Initialize the detector with optional custom configuration.

        Args:
            config: VolumeDetectorConfig instance. Uses DEFAULT_CONFIG if None.
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
        Run all volume event detections on the given OHLCV data.

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

        # Run all 5 detectors
        detections.extend(self._detect_volume_spike(sorted_data))
        detections.extend(self._detect_near_zero_volume(sorted_data))
        detections.extend(self._detect_cumulative_anomaly(sorted_data))
        detections.extend(self._detect_directional_volume(sorted_data))

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
            event_family=EventFamily.VOLUME,
            event_category=detection.event_category,
            event_type=detection.event_type,
            priority_raw=detection.priority_raw,
            confidence_level=detection.confidence_level,
            detection_source=self.DETECTION_SOURCE,
            event_owner=EventOwner.TechnicalEngine,
            event_subcategory=detection.event_subcategory,
            volume_data=detection.volume_data,
        )

        # Add detection-specific metadata
        if detection.metadata:
            event.metadata.update(detection.metadata)

        return event

    # ------------------------------------------------------------------
    # Helper: build VolumeData from current + previous candle
    # ------------------------------------------------------------------

    def _build_volume_data(
        self,
        current: MarketData,
        previous: MarketData,
        avg_volume: float,
        direction: str = "neutral",
    ) -> VolumeData:
        """
        Build a VolumeData object.

        Args:
            current: Current candle
            previous: Previous candle (for direction calculation)
            avg_volume: Average volume over the reference window
            direction: Direction of price move ('up', 'down', 'neutral')

        Returns:
            VolumeData instance
        """
        volume_ratio = (current.volume / avg_volume) if avg_volume > 0 else 0.0

        # Auto-detect direction if not provided
        if direction == "neutral":
            if current.close > current.open:
                direction = "up"
            elif current.close < current.open:
                direction = "down"
            else:
                direction = "neutral"

        return VolumeData(
            current_volume=current.volume,
            avg_volume=round(avg_volume, 2),
            volume_ratio=round(volume_ratio, 4),
            direction=direction,
        )

    # ------------------------------------------------------------------
    # Helper: clamp confidence to [0.0, 1.0]
    # ------------------------------------------------------------------

    def _clamp_confidence(self, value: float) -> float:
        """Clamp confidence value to [min_confidence, max_confidence]."""
        return max(self._config.min_confidence, min(self._config.max_confidence, value))

    # ------------------------------------------------------------------
    # Helper: compute average volume over a window
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_avg_volume(data: List[MarketData]) -> float:
        """Compute the average volume from a list of candles."""
        if not data:
            return 0.0
        return sum(c.volume for c in data) / len(data)

    # ------------------------------------------------------------------
    # 2.1 VOLUME_SPIKE
    # Source: Katalog §2.1
    # Condition: current volume >= spike_threshold * avg_volume
    # Priority: CRITICAL
    # ------------------------------------------------------------------

    def _detect_volume_spike(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """
        Detect Volume Spike (2.1).

        Checks if the current candle's volume exceeds the configured
        multiple of the average volume over the trailing window.
        """
        results: List[_DetectionResult] = []
        window = self._config.spike_volume_window

        if len(data) < 2:
            return results

        current = data[-1]
        previous = data[-2]

        # Use trailing candles for average, excluding current
        lookback = data[-(window + 1):-1] if len(data) > window else data[:-1]
        if len(lookback) < 1:
            return results

        avg_volume = self._compute_avg_volume(lookback)
        if avg_volume <= 0:
            return results

        volume_ratio = current.volume / avg_volume

        if volume_ratio < self._config.spike_threshold:
            return results

        # Determine direction
        direction = "up" if current.close > previous.close else "down" if current.close < previous.close else "neutral"

        volume_data = self._build_volume_data(
            current=current,
            previous=previous,
            avg_volume=avg_volume,
            direction=direction,
        )

        # Confidence: scales linearly from threshold to confidence_scale
        if volume_ratio >= self._config.spike_confidence_scale:
            confidence = 1.0
        else:
            scale_range = self._config.spike_confidence_scale - self._config.spike_threshold
            if scale_range > 0:
                confidence = (volume_ratio - self._config.spike_threshold) / scale_range
            else:
                confidence = 0.5

        confidence = self._clamp_confidence(confidence)

        results.append(_DetectionResult(
            event_type="VOLUME_SPIKE",
            event_category="Wolumenowe",
            event_subcategory="Odchylenie od średniej",
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=confidence,
            volume_data=volume_data,
            metadata={
                "volume_ratio": round(volume_ratio, 4),
                "avg_volume": round(avg_volume, 2),
                "current_volume": current.volume,
                "threshold": self._config.spike_threshold,
                "volume_window": window,
                "detection_method": "volume_anomaly_detector",
            },
        ))

        return results

    # ------------------------------------------------------------------
    # 2.2 NEAR_ZERO_VOLUME
    # Source: Katalog §2.2
    # Condition: current volume / avg_volume < near_zero_threshold
    # Priority: MEDIUM
    # ------------------------------------------------------------------

    def _detect_near_zero_volume(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """
        Detect Near-Zero Volume (2.2).

        Checks if the current candle's volume is below the configured
        fraction of the average volume over the trailing window.
        """
        results: List[_DetectionResult] = []
        window = self._config.near_zero_volume_window

        if len(data) < 2:
            return results

        current = data[-1]
        previous = data[-2]

        # Use trailing candles for average, excluding current
        lookback = data[-(window + 1):-1] if len(data) > window else data[:-1]
        if len(lookback) < 1:
            return results

        avg_volume = self._compute_avg_volume(lookback)
        if avg_volume <= 0:
            return results

        volume_ratio = current.volume / avg_volume

        if volume_ratio > self._config.near_zero_threshold:
            return results

        # Determine direction
        direction = "up" if current.close > previous.close else "down" if current.close < previous.close else "neutral"

        volume_data = self._build_volume_data(
            current=current,
            previous=previous,
            avg_volume=avg_volume,
            direction=direction,
        )

        # Confidence: higher when volume_ratio is extremely low
        # Scale from near_zero_threshold down to near_zero_confidence_scale
        if volume_ratio <= self._config.near_zero_confidence_scale:
            confidence = 1.0
        else:
            scale_range = self._config.near_zero_threshold - self._config.near_zero_confidence_scale
            if scale_range > 0:
                confidence = (self._config.near_zero_threshold - volume_ratio) / scale_range
            else:
                confidence = 0.5

        confidence = self._clamp_confidence(confidence)

        results.append(_DetectionResult(
            event_type="NEAR_ZERO_VOLUME",
            event_category="Wolumenowe",
            event_subcategory="Odchylenie od średniej",
            priority_raw=PriorityLevel.MEDIUM,
            confidence_level=confidence,
            volume_data=volume_data,
            metadata={
                "volume_ratio": round(volume_ratio, 4),
                "avg_volume": round(avg_volume, 2),
                "current_volume": current.volume,
                "threshold": self._config.near_zero_threshold,
                "volume_window": window,
                "detection_method": "volume_anomaly_detector",
            },
        ))

        return results

    # ------------------------------------------------------------------
    # 2.3 CUMULATIVE_VOLUME_ANOMALY
    # Source: Katalog §2.3
    # Condition: sum of volume over cumulative_window >= cumulative_threshold
    #            * average sum over comparable periods
    # Priority: MEDIUM
    # ------------------------------------------------------------------

    def _detect_cumulative_anomaly(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """
        Detect Cumulative Volume Anomaly (2.3).

        Checks if the cumulative volume over the last N candles is
        significantly higher than the average cumulative volume over
        comparable earlier periods.
        """
        results: List[_DetectionResult] = []
        window = self._config.cumulative_window
        lookback_periods = self._config.cumulative_lookback

        if len(data) < window + 2:
            return results

        current = data[-1]
        previous = data[-2]

        # Current cumulative sum (last `window` candles, including current)
        current_window = data[-window:]
        current_sum = sum(c.volume for c in current_window)

        # Prior periods for comparison
        # Take prior candles up to `lookback_periods`, excluding the current window
        if len(data) > window + lookback_periods:
            prior_data = data[-(window + lookback_periods):-window]
        else:
            prior_data = data[:-window]

        if len(prior_data) < window:
            return results

        # Compute average cumulative sum over prior comparable periods
        prior_sums = []
        for i in range(0, len(prior_data) - window + 1):
            period = prior_data[i:i + window]
            prior_sums.append(sum(c.volume for c in period))

        if not prior_sums:
            return results

        avg_prior_sum = sum(prior_sums) / len(prior_sums)
        if avg_prior_sum <= 0:
            return results

        cumulative_ratio = current_sum / avg_prior_sum

        if cumulative_ratio < self._config.cumulative_threshold:
            return results

        # Determine direction from the last candle in the window
        last_in_window = current_window[-1]
        avg_volume = current_sum / window

        direction = "up" if last_in_window.close > previous.close else "down" if last_in_window.close < previous.close else "neutral"

        volume_data = self._build_volume_data(
            current=last_in_window,
            previous=previous,
            avg_volume=avg_volume,
            direction=direction,
        )

        # Confidence: scales from threshold to confidence_scale
        if cumulative_ratio >= self._config.cumulative_confidence_scale:
            confidence = 1.0
        else:
            scale_range = self._config.cumulative_confidence_scale - self._config.cumulative_threshold
            if scale_range > 0:
                confidence = (cumulative_ratio - self._config.cumulative_threshold) / scale_range
            else:
                confidence = 0.5

        confidence = self._clamp_confidence(confidence)

        results.append(_DetectionResult(
            event_type="CUMULATIVE_VOLUME_ANOMALY",
            event_category="Wolumenowe",
            event_subcategory="Odchylenie od średniej",
            priority_raw=PriorityLevel.MEDIUM,
            confidence_level=confidence,
            volume_data=volume_data,
            metadata={
                "cumulative_ratio": round(cumulative_ratio, 4),
                "current_sum": round(current_sum, 2),
                "avg_prior_sum": round(avg_prior_sum, 2),
                "window_candles": window,
                "lookback_periods": len(prior_data),
                "threshold": self._config.cumulative_threshold,
                "detection_method": "volume_anomaly_detector",
            },
        ))

        return results

    # ------------------------------------------------------------------
    # 2.4 HIGH_VOLUME_ON_DOWN_DAYS / 2.5 HIGH_VOLUME_ON_UP_DAYS
    # Source: Katalog §2.4, §2.5
    # Condition: Average volume on dominant direction exceeds
    #            directional_threshold * average volume on opposite direction
    # Priority: HIGH
    # ------------------------------------------------------------------

    def _detect_directional_volume(
        self, data: List[MarketData]
    ) -> List[_DetectionResult]:
        """
        Detect High Volume on Down Days (2.4) and High Volume on Up Days (2.5).

        Compares the average volume on up days vs down days over the
        configured window. Generates the appropriate event type based on
        which direction has significantly higher volume.
        """
        results: List[_DetectionResult] = []
        window = self._config.directional_volume_window

        if len(data) < 2:
            return results

        current = data[-1]
        previous = data[-2]

        # Gather candles for directional analysis
        analysis_data = data[-(window + 1):] if len(data) > window else data
        if len(analysis_data) < self._config.directional_min_candles * 2:
            return results

        up_volumes = []
        down_volumes = []

        for i in range(1, len(analysis_data)):
            candle = analysis_data[i]
            prev_candle = analysis_data[i - 1]
            if candle.close > prev_candle.close:
                up_volumes.append(candle.volume)
            elif candle.close < prev_candle.close:
                down_volumes.append(candle.volume)

        if len(up_volumes) < self._config.directional_min_candles or len(down_volumes) < self._config.directional_min_candles:
            return results

        avg_up = sum(up_volumes) / len(up_volumes)
        avg_down = sum(down_volumes) / len(down_volumes)

        # Determine which direction dominates
        direction_dominant = None
        directional_ratio = 0.0

        if avg_down > 0 and avg_up > 0:
            if avg_down / avg_up >= self._config.directional_threshold:
                direction_dominant = "down"
                directional_ratio = avg_down / avg_up
            elif avg_up / avg_down >= self._config.directional_threshold:
                direction_dominant = "up"
                directional_ratio = avg_up / avg_down

        if direction_dominant is None:
            return results

        # Determine current candle direction
        current_direction = "up" if current.close > previous.close else "down" if current.close < previous.close else "neutral"

        avg_volume = self._compute_avg_volume(analysis_data)
        volume_data = self._build_volume_data(
            current=current,
            previous=previous,
            avg_volume=avg_volume,
            direction=current_direction,
        )

        # Confidence: scales from threshold to confidence_scale
        if directional_ratio >= self._config.directional_confidence_scale:
            confidence = 1.0
        else:
            scale_range = self._config.directional_confidence_scale - self._config.directional_threshold
            if scale_range > 0:
                confidence = (directional_ratio - self._config.directional_threshold) / scale_range
            else:
                confidence = 0.5

        confidence = self._clamp_confidence(confidence)

        if direction_dominant == "down":
            results.append(_DetectionResult(
                event_type="HIGH_VOLUME_ON_DOWN_DAYS",
                event_category="Wolumenowe",
                event_subcategory="Wolumen kierunkowy",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                volume_data=volume_data,
                metadata={
                    "directional_ratio": round(directional_ratio, 4),
                    "avg_up_volume": round(avg_up, 2),
                    "avg_down_volume": round(avg_down, 2),
                    "up_candles": len(up_volumes),
                    "down_candles": len(down_volumes),
                    "threshold": self._config.directional_threshold,
                    "dominant_direction": "down",
                    "detection_method": "directional_volume_detector",
                },
            ))
        else:
            results.append(_DetectionResult(
                event_type="HIGH_VOLUME_ON_UP_DAYS",
                event_category="Wolumenowe",
                event_subcategory="Wolumen kierunkowy",
                priority_raw=PriorityLevel.HIGH,
                confidence_level=confidence,
                volume_data=volume_data,
                metadata={
                    "directional_ratio": round(directional_ratio, 4),
                    "avg_up_volume": round(avg_up, 2),
                    "avg_down_volume": round(avg_down, 2),
                    "up_candles": len(up_volumes),
                    "down_candles": len(down_volumes),
                    "threshold": self._config.directional_threshold,
                    "dominant_direction": "up",
                    "detection_method": "directional_volume_detector",
                },
            ))

        return results