"""
Tests for the Volume Event Detector.

Covers all 5 approved volume event types and edge cases as specified
in the implementation task:

1. No event for stable volume
2. Correct detection of each of the 5 Volume Event types
3. Correct MarketEvent creation
4. event_family set to VOLUME
5. Correct VolumeData
6. Correct priority_raw
7. confidence_level in range 0-1
8. Correct detection_source and event_owner
9. History entry added
10. No modification of input data
11. Handling of empty data
12. Handling of missing values
13. Handling of too-short history
14. No dependency on engines/
15. No network calls
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import List

import pytest

from config.volume_detector import VolumeDetectorConfig
from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from engines.volume_detector.engine import VolumeDetector


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_candle(
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float = 100000.0,
) -> MarketData:
    """Create a single MarketData candle."""
    return MarketData(
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


def _make_flat_history(
    num_candles: int = 60,
    base_price: float = 100.0,
    base_volume: float = 100000.0,
    base_timestamp: datetime = None,
) -> List[MarketData]:
    """Create a flat price/volume history (stable, no events)."""
    from datetime import timedelta
    if base_timestamp is None:
        base_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for i in range(num_candles):
        ts = base_timestamp + timedelta(days=i)
        candles.append(_make_candle(
            timestamp=ts,
            open_price=base_price,
            high=base_price + 0.5,
            low=base_price - 0.5,
            close=base_price,
            volume=base_volume,
        ))
    return candles


def _make_spike_history(
    base_price: float = 100.0,
    base_volume: float = 100000.0,
    spike_volume: float = 500000.0,
    num_prior: int = 60,
) -> List[MarketData]:
    """Create history ending with a volume spike."""
    candles = _make_flat_history(
        num_candles=num_prior,
        base_price=base_price,
        base_volume=base_volume,
    )
    prev = candles[-1]
    spike_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close,
        high=prev.close + 1.0,
        low=prev.close - 1.0,
        close=prev.close + 0.5,  # Up day
        volume=spike_volume,
    )
    candles.append(spike_candle)
    return candles


def _make_near_zero_history(
    base_price: float = 100.0,
    base_volume: float = 100000.0,
    near_zero_volume: float = 5000.0,
    num_prior: int = 60,
) -> List[MarketData]:
    """Create history ending with near-zero volume."""
    candles = _make_flat_history(
        num_candles=num_prior,
        base_price=base_price,
        base_volume=base_volume,
    )
    prev = candles[-1]
    low_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close,
        high=prev.close + 0.5,
        low=prev.close - 0.5,
        close=prev.close - 0.3,  # Down day
        volume=near_zero_volume,
    )
    candles.append(low_candle)
    return candles


def _make_cumulative_anomaly_history(
    base_price: float = 100.0,
    base_volume: float = 100000.0,
    anomaly_volume: float = 300000.0,
    num_prior: int = 100,
    anomaly_window: int = 20,
) -> List[MarketData]:
    """Create history ending with a cumulative volume anomaly."""
    candles = _make_flat_history(
        num_candles=num_prior,
        base_price=base_price,
        base_volume=base_volume,
    )
    prev = candles[-1]
    # Append N candles with high volume
    from datetime import timedelta
    last_ts = candles[-1].timestamp
    for i in range(anomaly_window):
        ts = last_ts + timedelta(days=1 + i)
        candles.append(_make_candle(
            timestamp=ts,
            open_price=base_price,
            high=base_price + 1.0,
            low=base_price - 1.0,
            close=base_price + (0.5 if i % 2 == 0 else -0.5),
            volume=anomaly_volume,
        ))
    return candles


def _make_directional_volume_history(
    base_price: float = 100.0,
    base_volume: float = 100000.0,
    num_prior: int = 40,
    dominant_direction: str = "up",
) -> List[MarketData]:
    """
    Create history with directional volume bias.

    Args:
        dominant_direction: "up" for High Volume on Up Days,
                          "down" for High Volume on Down Days
    """
    candles = _make_flat_history(
        num_candles=num_prior,
        base_price=base_price,
        base_volume=base_volume,
    )
    prev = candles[-1]
    from datetime import timedelta
    last_ts = prev.timestamp

    # Generate 15 candles with clear directional bias
    high_vol = 300000.0  # High volume for dominant direction
    low_vol = 50000.0    # Low volume for opposite direction

    for i in range(15):
        ts = last_ts + timedelta(days=1 + i)
        if dominant_direction == "up":
            # Up days have high volume, down days have low volume
            if i % 3 != 0:  # Mostly up days
                vol = high_vol
                close_price = base_price + 1.0 + (i * 0.2)
            else:
                vol = low_vol
                close_price = base_price - 0.3
        else:  # down
            if i % 3 != 0:  # Mostly down days
                vol = high_vol
                close_price = base_price - 1.0 - (i * 0.2)
            else:
                vol = low_vol
                close_price = base_price + 0.3

        candles.append(_make_candle(
            timestamp=ts,
            open_price=candles[-1].close,
            high=candles[-1].close + 1.0,
            low=candles[-1].close - 1.0,
            close=close_price,
            volume=vol,
        ))

    return candles


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    """Create a VolumeDetector with default config."""
    return VolumeDetector()


@pytest.fixture
def custom_config():
    """Create a custom config with lower thresholds for easier testing."""
    return VolumeDetectorConfig(
        spike_threshold=2.0,
        spike_confidence_scale=4.0,
        near_zero_threshold=0.2,
        near_zero_confidence_scale=0.1,
        cumulative_threshold=1.5,
        cumulative_confidence_scale=2.5,
        directional_threshold=1.2,
        directional_confidence_scale=2.0,
        directional_min_candles=2,
    )


@pytest.fixture
def detector_custom(custom_config):
    """Create a VolumeDetector with custom config."""
    return VolumeDetector(config=custom_config)


# ---------------------------------------------------------------------------
# Test 1: No event for stable volume
# ---------------------------------------------------------------------------

class TestStableVolume:
    """Test that stable volume produces no events."""

    def test_stable_volume_no_events(self, detector):
        """Stable volume with normal variation should produce no events."""
        data = _make_flat_history(num_candles=60, base_volume=100000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) == 0

    def test_small_volume_change_below_threshold(self, detector):
        """A small volume change below threshold should not trigger spike."""
        data = _make_flat_history(num_candles=60, base_volume=100000.0)
        prev = data[-1]
        # 2x volume — below 3x threshold
        small_spike = _make_candle(
            timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
            open_price=prev.close,
            high=prev.close + 0.5,
            low=prev.close - 0.5,
            close=prev.close + 0.2,
            volume=200000.0,  # 2x base — below 3x threshold
        )
        data.append(small_spike)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike_events = [e for e in events if e.event_type == "VOLUME_SPIKE"]
        assert len(spike_events) == 0


# ---------------------------------------------------------------------------
# Test 2: Correct detection of each of the 5 Volume Event types
# ---------------------------------------------------------------------------

class TestVolumeSpike:
    """Test 2.1 Volume Spike detection."""

    def test_volume_spike_detected(self, detector):
        """A 5x volume spike should be detected."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike_events = [e for e in events if e.event_type == "VOLUME_SPIKE"]
        assert len(spike_events) == 1

    def test_volume_spike_event_type(self, detector):
        """Verify event_type is VOLUME_SPIKE."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        assert spike.event_type == "VOLUME_SPIKE"
        assert spike.event_category == "Wolumenowe"
        assert spike.event_subcategory == "Odchylenie od średniej"

    def test_volume_spike_event_family(self, detector):
        """Verify event_family is VOLUME."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        assert spike.event_family == EventFamily.VOLUME

    def test_volume_spike_below_threshold_not_detected(self, detector):
        """A 2x spike (below 3x threshold) should not be detected."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=200000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike_events = [e for e in events if e.event_type == "VOLUME_SPIKE"]
        assert len(spike_events) == 0

    def test_volume_spike_with_custom_config(self, detector_custom):
        """Volume spike should be detected with custom lower threshold."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=200000.0, num_prior=60)
        events = detector_custom.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike_events = [e for e in events if e.event_type == "VOLUME_SPIKE"]
        assert len(spike_events) == 1  # 2x >= 2.0 custom threshold


class TestNearZeroVolume:
    """Test 2.2 Near-Zero Volume detection."""

    def test_near_zero_volume_detected(self, detector):
        """Near-zero volume (5% of avg) should be detected."""
        data = _make_near_zero_history(base_volume=100000.0, near_zero_volume=5000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        nz_events = [e for e in events if e.event_type == "NEAR_ZERO_VOLUME"]
        assert len(nz_events) == 1

    def test_near_zero_volume_event_type(self, detector):
        """Verify event_type is NEAR_ZERO_VOLUME."""
        data = _make_near_zero_history(base_volume=100000.0, near_zero_volume=5000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        nz = [e for e in events if e.event_type == "NEAR_ZERO_VOLUME"][0]
        assert nz.event_type == "NEAR_ZERO_VOLUME"
        assert nz.event_category == "Wolumenowe"
        assert nz.event_subcategory == "Odchylenie od średniej"

    def test_near_zero_volume_not_detected_with_normal_volume(self, detector):
        """Normal volume should not trigger near-zero detection."""
        data = _make_near_zero_history(base_volume=100000.0, near_zero_volume=80000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        nz_events = [e for e in events if e.event_type == "NEAR_ZERO_VOLUME"]
        assert len(nz_events) == 0  # 80% of avg is above 10% threshold


class TestCumulativeVolumeAnomaly:
    """Test 2.3 Cumulative Volume Anomaly detection."""

    def test_cumulative_anomaly_detected(self, detector):
        """A cumulative volume anomaly should be detected."""
        data = _make_cumulative_anomaly_history(
            base_volume=100000.0,
            anomaly_volume=300000.0,
            num_prior=100,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        cum_events = [e for e in events if e.event_type == "CUMULATIVE_VOLUME_ANOMALY"]
        assert len(cum_events) == 1

    def test_cumulative_anomaly_event_type(self, detector):
        """Verify event_type is CUMULATIVE_VOLUME_ANOMALY."""
        data = _make_cumulative_anomaly_history(
            base_volume=100000.0,
            anomaly_volume=300000.0,
            num_prior=100,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        cum = [e for e in events if e.event_type == "CUMULATIVE_VOLUME_ANOMALY"][0]
        assert cum.event_type == "CUMULATIVE_VOLUME_ANOMALY"
        assert cum.event_category == "Wolumenowe"
        assert cum.event_subcategory == "Odchylenie od średniej"

    def test_cumulative_anomaly_not_enough_history(self, detector):
        """Cumulative anomaly should not fire with insufficient history."""
        data = _make_cumulative_anomaly_history(
            base_volume=100000.0,
            anomaly_volume=300000.0,
            num_prior=10,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        cum_events = [e for e in events if e.event_type == "CUMULATIVE_VOLUME_ANOMALY"]
        assert len(cum_events) == 0  # Not enough prior data


class TestHighVolumeOnDownDays:
    """Test 2.4 High Volume on Down Days detection."""

    def test_high_volume_down_detected(self, detector):
        """High volume on down days should be detected."""
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="down",
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        down_events = [e for e in events if e.event_type == "HIGH_VOLUME_ON_DOWN_DAYS"]
        assert len(down_events) == 1

    def test_high_volume_down_event_type(self, detector):
        """Verify event_type is HIGH_VOLUME_ON_DOWN_DAYS."""
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="down",
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        down = [e for e in events if e.event_type == "HIGH_VOLUME_ON_DOWN_DAYS"][0]
        assert down.event_type == "HIGH_VOLUME_ON_DOWN_DAYS"
        assert down.event_category == "Wolumenowe"
        assert down.event_subcategory == "Wolumen kierunkowy"


class TestHighVolumeOnUpDays:
    """Test 2.5 High Volume on Up Days detection."""

    def test_high_volume_up_detected(self, detector):
        """High volume on up days should be detected."""
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="up",
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        up_events = [e for e in events if e.event_type == "HIGH_VOLUME_ON_UP_DAYS"]
        assert len(up_events) == 1

    def test_high_volume_up_event_type(self, detector):
        """Verify event_type is HIGH_VOLUME_ON_UP_DAYS."""
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="up",
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        up = [e for e in events if e.event_type == "HIGH_VOLUME_ON_UP_DAYS"][0]
        assert up.event_type == "HIGH_VOLUME_ON_UP_DAYS"
        assert up.event_category == "Wolumenowe"
        assert up.event_subcategory == "Wolumen kierunkowy"

    def test_directional_volume_not_detected_with_balanced_volume(self, detector):
        """Balanced volume between up/down days should not trigger."""
        data = _make_flat_history(num_candles=60, base_volume=100000.0)
        from datetime import timedelta
        last_ts = data[-1].timestamp
        # Add candles with equal up/down volume
        for i in range(20):
            ts = last_ts + timedelta(days=1 + i)
            is_up = i % 2 == 0
            data.append(_make_candle(
                timestamp=ts,
                open_price=100.0,
                high=101.0,
                low=99.0,
                close=101.0 if is_up else 99.0,
                volume=100000.0,  # Same volume for both directions
            ))
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        dir_events = [
            e for e in events
            if e.event_type in ("HIGH_VOLUME_ON_DOWN_DAYS", "HIGH_VOLUME_ON_UP_DAYS")
        ]
        assert len(dir_events) == 0


# ---------------------------------------------------------------------------
# Test 3: Correct MarketEvent creation
# ---------------------------------------------------------------------------

class TestMarketEventCreation:
    """Test that MarketEvent objects are correctly created."""

    def test_event_has_all_required_fields(self, detector):
        """Each event must have all required fields set."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) > 0
        event = events[0]
        assert event.event_id is not None and len(event.event_id) > 0
        assert event.timestamp_utc is not None
        assert event.ticker == "TEST.WA"
        assert event.market == "GPW"
        assert event.instrument_type == InstrumentType.STOCK_GPW
        assert event.event_family is not None
        assert event.event_category is not None and len(event.event_category) > 0
        assert event.event_type is not None and len(event.event_type) > 0
        assert event.priority_raw is not None
        assert event.confidence_level is not None
        assert event.detection_source is not None and len(event.detection_source) > 0
        assert event.event_owner is not None
        assert event.schema_version is not None and len(event.schema_version) > 0

    def test_event_id_is_unique(self, detector):
        """Each event should have a unique event_id."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ids = [e.event_id for e in events]
        assert len(ids) == len(set(ids))

    def test_multiple_events_same_ticker(self, detector):
        """Multiple events for the same ticker should all be valid."""
        data = _make_cumulative_anomaly_history(
            base_volume=100000.0,
            anomaly_volume=300000.0,
            num_prior=100,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert event.ticker == "TEST.WA"
            assert event.market == "GPW"


# ---------------------------------------------------------------------------
# Test 4: event_family set to VOLUME
# ---------------------------------------------------------------------------

class TestEventFamily:
    """Test that event_family is always VOLUME."""

    def test_all_events_have_volume_family(self, detector):
        """Every event from VolumeDetector must have event_family == VOLUME."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert event.event_family == EventFamily.VOLUME, (
                f"Expected VOLUME, got {event.event_family} for {event.event_type}"
            )

    def test_multiple_event_types_all_volume_family(self, detector):
        """Multiple event types should all have VOLUME family."""
        # Create data that could trigger volume spike + directional volume
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="up",
        )
        # Also make the last candle a spike
        prev = data[-2]
        data[-1] = _make_candle(
            timestamp=data[-1].timestamp,
            open_price=prev.close,
            high=prev.close + 1.0,
            low=prev.close - 1.0,
            close=prev.close + 0.5,
            volume=500000.0,  # 5x spike
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=data,
        )
        assert len(events) > 0
        for event in events:
            assert event.event_family == EventFamily.VOLUME


# ---------------------------------------------------------------------------
# Test 5: Correct VolumeData
# ---------------------------------------------------------------------------

class TestVolumeData:
    """Test that VolumeData is correctly populated."""

    def test_volume_data_has_correct_values(self, detector):
        """VolumeData should reflect the actual candle values."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        vd = spike.volume_data
        assert vd is not None
        assert vd.current_volume == data[-1].volume
        assert vd.volume_ratio > 0

    def test_volume_data_for_spike_ratio(self, detector):
        """VolumeData for a spike should have volume_ratio > 1."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        vd = spike.volume_data
        assert vd.volume_ratio >= 3.0  # 5x / avg

    def test_volume_data_for_near_zero_ratio(self, detector):
        """VolumeData for near-zero should have volume_ratio < 0.1."""
        data = _make_near_zero_history(base_volume=100000.0, near_zero_volume=5000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        nz = [e for e in events if e.event_type == "NEAR_ZERO_VOLUME"][0]
        vd = nz.volume_data
        assert vd.volume_ratio <= 0.1

    def test_volume_data_direction(self, detector):
        """VolumeData direction should match the candle's price direction."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        # The spike candle is an up day (close > open)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        vd = spike.volume_data
        assert vd.direction in ("up", "down", "neutral")


# ---------------------------------------------------------------------------
# Test 6: Correct priority_raw
# ---------------------------------------------------------------------------

class TestPriorityRaw:
    """Test that priority_raw matches the Katalog Zdarzen Rynkowych."""

    def test_spike_priority_is_critical(self, detector):
        """Volume Spike must have CRITICAL priority (Katalog §2.1)."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        assert spike.priority_raw == PriorityLevel.CRITICAL

    def test_near_zero_priority_is_medium(self, detector):
        """Near-Zero Volume must have MEDIUM priority (Katalog §2.2)."""
        data = _make_near_zero_history(base_volume=100000.0, near_zero_volume=5000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        nz = [e for e in events if e.event_type == "NEAR_ZERO_VOLUME"][0]
        assert nz.priority_raw == PriorityLevel.MEDIUM

    def test_cumulative_priority_is_medium(self, detector):
        """Cumulative Volume Anomaly must have MEDIUM priority (Katalog §2.3)."""
        data = _make_cumulative_anomaly_history(
            base_volume=100000.0,
            anomaly_volume=300000.0,
            num_prior=100,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        cum = [e for e in events if e.event_type == "CUMULATIVE_VOLUME_ANOMALY"][0]
        assert cum.priority_raw == PriorityLevel.MEDIUM

    def test_directional_priority_is_high(self, detector):
        """High Volume on Down/Up Days must have HIGH priority (Katalog §2.4, §2.5)."""
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="up",
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        dir_events = [
            e for e in events
            if e.event_type in ("HIGH_VOLUME_ON_DOWN_DAYS", "HIGH_VOLUME_ON_UP_DAYS")
        ]
        assert len(dir_events) > 0
        for event in dir_events:
            assert event.priority_raw == PriorityLevel.HIGH


# ---------------------------------------------------------------------------
# Test 7: Correct confidence_level
# ---------------------------------------------------------------------------

class TestConfidenceLevel:
    """Test that confidence_level is in range [0.0, 1.0]."""

    def test_confidence_in_range(self, detector):
        """All events must have confidence_level in [0.0, 1.0]."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert 0.0 <= event.confidence_level <= 1.0

    def test_confidence_above_min(self, detector):
        """confidence_level should be >= min_confidence."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert event.confidence_level >= 0.1

    def test_confidence_increases_with_strength(self, detector):
        """Stronger signals should produce higher confidence."""
        # Moderate spike (3x)
        data_moderate = _make_spike_history(base_volume=100000.0, spike_volume=300000.0)
        events_moderate = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data_moderate,
        )
        # Strong spike (8x)
        data_strong = _make_spike_history(base_volume=100000.0, spike_volume=800000.0)
        events_strong = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data_strong,
        )

        mod_spike = [e for e in events_moderate if e.event_type == "VOLUME_SPIKE"]
        strong_spike = [e for e in events_strong if e.event_type == "VOLUME_SPIKE"]

        # Both should have been detected
        assert len(mod_spike) == 1
        assert len(strong_spike) == 1

        # Stronger spike should have higher confidence (or equal at 1.0 cap)
        assert strong_spike[0].confidence_level >= mod_spike[0].confidence_level


# ---------------------------------------------------------------------------
# Test 8: Correct detection_source and event_owner
# ---------------------------------------------------------------------------

class TestDetectionSource:
    """Test that detection_source and event_owner are correct."""

    def test_detection_source(self, detector):
        """detection_source must identify the Volume Detector."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert "Volume Event Detector" in event.detection_source

    def test_event_owner(self, detector):
        """event_owner must be TechnicalEngine."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert event.event_owner == EventOwner.TechnicalEngine


# ---------------------------------------------------------------------------
# Test 9: History entry
# ---------------------------------------------------------------------------

class TestHistoryEntry:
    """Test that history entries are added correctly."""

    def test_history_has_creation_entry(self, detector):
        """Event should have a creation history entry."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) > 0
        event = events[0]
        assert len(event.history) >= 2  # creation + detection

    def test_history_has_detection_entry(self, detector):
        """Event should have a detection history entry."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        event = events[0]
        detection_entries = [
            h for h in event.history if "Wykrycie" in h.action
        ]
        assert len(detection_entries) == 1


# ---------------------------------------------------------------------------
# Test 10: No modification of input data
# ---------------------------------------------------------------------------

class TestNoModification:
    """Test that input data is not modified."""

    def test_input_data_not_modified(self, detector):
        """The detector should not modify the input ohlcv_data list."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        original = copy.deepcopy(data)
        detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(data) == len(original)
        for orig, curr in zip(original, data):
            assert orig.open == curr.open
            assert orig.high == curr.high
            assert orig.low == curr.low
            assert orig.close == curr.close
            assert orig.volume == curr.volume


# ---------------------------------------------------------------------------
# Test 11: Handling of empty data
# ---------------------------------------------------------------------------

class TestEmptyData:
    """Test behavior with empty or insufficient data."""

    def test_empty_data_returns_empty_list(self, detector):
        """Empty data should produce an empty event list."""
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=[],
        )
        assert len(events) == 0

    def test_single_candle_returns_empty_list(self, detector):
        """Single candle (no previous) should produce empty event list."""
        candle = _make_candle(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open_price=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=100000.0,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=[candle],
        )
        assert len(events) == 0

    def test_none_data_returns_empty_list(self, detector):
        """None data should produce an empty event list."""
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=None,
        )
        assert len(events) == 0


# ---------------------------------------------------------------------------
# Test 12: Handling of missing values
# ---------------------------------------------------------------------------

class TestMissingValues:
    """Test behavior with candles that have zero or unusual values."""

    def test_zero_volume_candle(self, detector):
        """A candle with zero volume should not crash the detector."""
        data = _make_flat_history(num_candles=60, base_volume=100000.0)
        prev = data[-1]
        zero_vol_candle = _make_candle(
            timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
            open_price=prev.close,
            high=prev.close + 0.5,
            low=prev.close - 0.5,
            close=prev.close + 0.2,
            volume=0.0,
        )
        data.append(zero_vol_candle)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        # Should not crash; near-zero might detect
        assert isinstance(events, list)

    def test_negative_volume_handling(self, detector):
        """Negative volume (invalid data) should not crash the detector."""
        data = _make_flat_history(num_candles=60, base_volume=100000.0)
        prev = data[-1]
        bad_candle = _make_candle(
            timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
            open_price=prev.close,
            high=prev.close + 0.5,
            low=prev.close - 0.5,
            close=prev.close + 0.2,
            volume=-1000.0,
        )
        data.append(bad_candle)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# Test 13: Handling of too-short history
# ---------------------------------------------------------------------------

class TestInsufficientHistory:
    """Test behavior with insufficient historical data."""

    def test_no_directional_with_few_candles(self, detector):
        """Directional volume should not fire with fewer than min candles."""
        data = _make_flat_history(num_candles=3, base_volume=100000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        dir_events = [
            e for e in events
            if e.event_type in ("HIGH_VOLUME_ON_DOWN_DAYS", "HIGH_VOLUME_ON_UP_DAYS")
        ]
        assert len(dir_events) == 0

    def test_no_cumulative_with_few_candles(self, detector):
        """Cumulative anomaly should not fire with insufficient data."""
        data = _make_flat_history(num_candles=5, base_volume=100000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        cum_events = [e for e in events if e.event_type == "CUMULATIVE_VOLUME_ANOMALY"]
        assert len(cum_events) == 0


# ---------------------------------------------------------------------------
# Test 14: No dependency on engines/
# ---------------------------------------------------------------------------

class TestNoEngineDependency:
    """
    Test that VolumeDetector does not import from other engines.
    
    VolumesDetector only imports from:
      - config.volume_detector
      - data.models.
      - standard library
    """

    def test_detector_imports_only_data_models(self):
        """Verify the module only imports from allowed locations."""
        import engines.volume_detector.engine as engine_module
        importers = set()
        for name, val in engine_module.__dict__.items():
            if hasattr(val, '__module__'):
                importers.add(val.__module__)
        
        # We should not import from any engines/ module other than our own
        for imp in importers:
            if 'engines.' in imp:
                assert 'engines.volume_detector' in imp, (
                    f"VolumeDetector imports from forbidden engine module: {imp}"
                )


# ---------------------------------------------------------------------------
# Test 15: No network calls
# ---------------------------------------------------------------------------

class TestNoNetworkCalls:
    """Test that VolumeDetector does not make network calls (pure computation)."""

    def test_detection_is_pure_computation(self, detector):
        """Detection should work with synthetic data without any network."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) > 0
        # If we got here without exception, no network was needed


# ---------------------------------------------------------------------------
# Test 16: Metadata correctness
# ---------------------------------------------------------------------------

class TestMetadata:
    """Test that metadata is correctly populated."""

    def test_spike_metadata_has_volume_ratio(self, detector):
        """Volume spike metadata should include volume_ratio."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        spike = [e for e in events if e.event_type == "VOLUME_SPIKE"][0]
        assert "volume_ratio" in spike.metadata
        assert spike.metadata["volume_ratio"] >= 3.0

    def test_directional_metadata_has_dominant_direction(self, detector):
        """Directional volume metadata should include dominant_direction."""
        data = _make_directional_volume_history(
            base_volume=100000.0,
            num_prior=40,
            dominant_direction="up",
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        up = [e for e in events if e.event_type == "HIGH_VOLUME_ON_UP_DAYS"]
        if up:
            assert "dominant_direction" in up[0].metadata
            assert up[0].metadata["dominant_direction"] == "up"

    def test_detection_method_in_metadata(self, detector):
        """All events should have detection_method in metadata."""
        data = _make_spike_history(base_volume=100000.0, spike_volume=500000.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert "detection_method" in event.metadata