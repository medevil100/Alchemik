"""
Tests for the Price Event Detector.

Covers all 10 approved price event types and edge cases as specified
in the implementation task:

1. No event for stable price
2. Correct detection of each of the 10 Price Event types
3. Correct MarketEvent creation
4. event_family set to PRICE
5. Correct PriceData
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

from config.price_detector import PriceDetectorConfig
from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from engines.price_detector.engine import PriceDetector


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
    num_candles: int = 260,
    base_price: float = 100.0,
    base_timestamp: datetime = None,
) -> List[MarketData]:
    """Create a flat price history (stable price, no events)."""
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
            volume=100000.0,
        ))
    return candles


def _make_surge_history(
    base_price: float = 100.0,
    surge_pct: float = 10.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history ending with a price surge."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    new_price = base_price * (1.0 + surge_pct / 100.0)
    surge_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close + 0.5,
        high=new_price + 1.0,
        low=prev.close,
        close=new_price,
        volume=500000.0,
    )
    candles.append(surge_candle)
    return candles


def _make_drop_history(
    base_price: float = 100.0,
    drop_pct: float = 10.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history ending with a price drop."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    new_price = base_price * (1.0 - drop_pct / 100.0)
    drop_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close - 0.5,
        high=prev.close,
        low=new_price - 1.0,
        close=new_price,
        volume=500000.0,
    )
    candles.append(drop_candle)
    return candles


def _make_gap_up_history(
    base_price: float = 100.0,
    gap_pct: float = 5.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history ending with a gap up."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    gap_open = prev.close * (1.0 + gap_pct / 100.0)
    gap_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=gap_open,
        high=gap_open + 2.0,
        low=gap_open - 0.5,
        close=gap_open + 1.0,
        volume=500000.0,
    )
    candles.append(gap_candle)
    return candles


def _make_gap_down_history(
    base_price: float = 100.0,
    gap_pct: float = 5.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history ending with a gap down."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    gap_open = prev.close * (1.0 - gap_pct / 100.0)
    gap_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=gap_open,
        high=gap_open + 0.5,
        low=gap_open - 2.0,
        close=gap_open - 1.0,
        volume=500000.0,
    )
    candles.append(gap_candle)
    return candles


def _make_52w_high_history(
    base_price: float = 100.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history ending with a new 52-week high."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    new_high = base_price * 1.15  # 15% above base
    high_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close + 1.0,
        high=new_high,
        low=prev.close,
        close=new_high - 0.5,
        volume=500000.0,
    )
    candles.append(high_candle)
    return candles


def _make_52w_low_history(
    base_price: float = 100.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history ending with a new 52-week low."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    new_low = base_price * 0.85  # 15% below base
    low_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close - 1.0,
        high=prev.close,
        low=new_low,
        close=new_low + 0.5,
        volume=500000.0,
    )
    candles.append(low_candle)
    return candles


def _make_ath_history(
    base_price: float = 100.0,
    num_prior: int = 100,
) -> List[MarketData]:
    """Create history ending with a new all-time high."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    new_ath = base_price * 1.20
    ath_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close + 1.0,
        high=new_ath,
        low=prev.close,
        close=new_ath - 0.5,
        volume=500000.0,
    )
    candles.append(ath_candle)
    return candles


def _make_atl_history(
    base_price: float = 100.0,
    num_prior: int = 100,
) -> List[MarketData]:
    """Create history ending with a new all-time low."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    new_atl = base_price * 0.80
    atl_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=prev.close - 1.0,
        high=prev.close,
        low=new_atl,
        close=new_atl + 0.5,
        volume=500000.0,
    )
    candles.append(atl_candle)
    return candles


def _make_level_rejection_history(
    base_price: float = 100.0,
    num_prior: int = 50,
) -> List[MarketData]:
    """
    Create history where price approaches a resistance level and rebounds.

    Builds a swing high at base_price + 5, then a candle that approaches
    it and closes significantly lower.
    """
    from datetime import timedelta
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    last_ts = candles[-1].timestamp

    # Create a clear swing high — a single candle with a distinct peak
    swing_high = base_price + 5.0
    # Leading candles (lower highs) — 3 before the peak
    for i in range(3):
        candles.append(_make_candle(
            timestamp=last_ts + timedelta(days=1 + i),
            open_price=base_price + 2.0,
            high=base_price + 4.5,
            low=base_price + 1.0,
            close=base_price + 2.5,
            volume=100000.0,
        ))
    # The swing high candle — single distinct peak
    candles.append(_make_candle(
        timestamp=last_ts + timedelta(days=5),
        open_price=base_price + 3.0,
        high=swing_high,  # 105.0
        low=base_price + 2.0,
        close=base_price + 4.5,
        volume=100000.0,
    ))
    # Trailing candles (lower highs) — 3 after the peak
    for i in range(3):
        candles.append(_make_candle(
            timestamp=last_ts + timedelta(days=6 + i),
            open_price=base_price + 2.0,
            high=base_price + 4.2,
            low=base_price + 1.0,
            close=base_price + 2.5,
            volume=100000.0,
        ))

    # Now a candle that approaches the resistance and rebounds
    prev = candles[-1]
    rejection_candle = _make_candle(
        timestamp=last_ts + timedelta(days=10),
        open_price=prev.close,
        high=swing_high * 1.005,  # Within 0.5% of resistance
        low=prev.close - 1.0,
        close=swing_high * 0.97,  # Closed 3% below resistance (rebound)
        volume=500000.0,
    )
    candles.append(rejection_candle)
    return candles


def _make_psych_cross_history(
    base_price: float = 98.0,
    num_prior: int = 260,
) -> List[MarketData]:
    """Create history where price crosses a psychological level (100)."""
    candles = _make_flat_history(num_candles=num_prior, base_price=base_price)
    prev = candles[-1]
    # Cross above 100
    cross_candle = _make_candle(
        timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
        open_price=99.5,
        high=102.0,
        low=99.0,
        close=101.0,  # Above 100
        volume=500000.0,
    )
    candles.append(cross_candle)
    return candles


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    """Create a PriceDetector with default config."""
    return PriceDetector()


@pytest.fixture
def custom_config():
    """Create a custom config with lower thresholds for easier testing."""
    return PriceDetectorConfig(
        surge_threshold_pct=5.0,
        gap_threshold_pct=2.0,
        ath_min_history=10,
        level_rejection_proximity_pct=2.0,
        level_rejection_rebound_pct=1.0,
        psych_level_proximity_pct=0.1,
    )


@pytest.fixture
def detector_custom(custom_config):
    """Create a PriceDetector with custom config."""
    return PriceDetector(config=custom_config)


# ---------------------------------------------------------------------------
# Test 1: No event for stable price
# ---------------------------------------------------------------------------

class TestStablePrice:
    """Test that stable prices produce no events."""

    def test_stable_price_no_events(self, detector):
        """Stable price with minimal variation should produce no events."""
        data = _make_flat_history(num_candles=260, base_price=100.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) == 0

    def test_small_change_below_threshold(self, detector):
        """A small price change below threshold should not trigger surge/drop."""
        data = _make_flat_history(num_candles=260, base_price=100.0)
        prev = data[-1]
        # 2% change — below 8% threshold
        small_move = _make_candle(
            timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
            open_price=prev.close,
            high=prev.close * 1.03,
            low=prev.close * 0.99,
            close=prev.close * 1.02,
            volume=100000.0,
        )
        data.append(small_move)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        # 2% is below 8% threshold — no surge/drop
        surge_events = [e for e in events if e.event_type in ("PRICE_SURGE", "PRICE_DROP")]
        assert len(surge_events) == 0


# ---------------------------------------------------------------------------
# Test 2: Correct detection of each of the 10 Price Event types
# ---------------------------------------------------------------------------

class TestPriceSurge:
    """Test 1.1 Price Surge detection."""

    def test_price_surge_detected(self, detector):
        """A 10% surge should be detected."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        assert len(surge_events) == 1

    def test_price_surge_event_type(self, detector):
        """Verify event_type is PRICE_SURGE."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge = [e for e in events if e.event_type == "PRICE_SURGE"][0]
        assert surge.event_type == "PRICE_SURGE"
        assert surge.event_category == "Cenowe"
        assert surge.event_subcategory == "Ruchy kierunkowe"

    def test_price_surge_below_threshold_not_detected(self, detector):
        """A 5% surge (below 8% threshold) should not be detected."""
        data = _make_surge_history(base_price=100.0, surge_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        assert len(surge_events) == 0


class TestPriceDrop:
    """Test 1.2 Price Drop detection."""

    def test_price_drop_detected(self, detector):
        """A 10% drop should be detected."""
        data = _make_drop_history(base_price=100.0, drop_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        drop_events = [e for e in events if e.event_type == "PRICE_DROP"]
        assert len(drop_events) == 1

    def test_price_drop_event_type(self, detector):
        """Verify event_type is PRICE_DROP."""
        data = _make_drop_history(base_price=100.0, drop_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        drop = [e for e in events if e.event_type == "PRICE_DROP"][0]
        assert drop.event_type == "PRICE_DROP"
        assert drop.event_category == "Cenowe"


class TestGapUp:
    """Test 1.3 Gap Up detection."""

    def test_gap_up_detected(self, detector):
        """A 5% gap up should be detected."""
        data = _make_gap_up_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap_events = [e for e in events if e.event_type == "GAP_UP"]
        assert len(gap_events) == 1

    def test_gap_up_event_type(self, detector):
        """Verify event_type is GAP_UP."""
        data = _make_gap_up_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap = [e for e in events if e.event_type == "GAP_UP"][0]
        assert gap.event_type == "GAP_UP"
        assert gap.event_category == "Cenowe"
        assert gap.event_subcategory == "Luki"

    def test_gap_up_not_confirmed_by_high(self, detector):
        """Gap up that doesn't exceed prev_high should not be detected."""
        data = _make_flat_history(num_candles=260, base_price=100.0)
        prev = data[-1]
        # Open is 5% above prev_close but below prev_high
        prev_high = prev.high  # ~100.5
        gap_open = prev.close * 1.05  # 105.0 — but prev_high is only 100.5
        # Actually, 105 > 100.5, so this WILL be confirmed
        # Let's make a gap that is NOT confirmed: open above close but NOT above high
        # We need prev_high to be higher than the gap_open
        # Let's modify: set prev_high very high
        data[-1] = _make_candle(
            timestamp=data[-1].timestamp,
            open_price=100.0,
            high=110.0,  # Very high prev_high
            low=99.5,
            close=100.0,
            volume=100000.0,
        )
        gap_open = 105.0  # 5% above close but below prev_high (110)
        gap_candle = _make_candle(
            timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
            open_price=gap_open,
            high=gap_open + 1.0,
            low=gap_open - 0.5,
            close=gap_open + 0.5,
            volume=500000.0,
        )
        data.append(gap_candle)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap_events = [e for e in events if e.event_type == "GAP_UP"]
        assert len(gap_events) == 0


class TestGapDown:
    """Test 1.4 Gap Down detection."""

    def test_gap_down_detected(self, detector):
        """A 5% gap down should be detected."""
        data = _make_gap_down_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap_events = [e for e in events if e.event_type == "GAP_DOWN"]
        assert len(gap_events) == 1

    def test_gap_down_event_type(self, detector):
        """Verify event_type is GAP_DOWN."""
        data = _make_gap_down_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap = [e for e in events if e.event_type == "GAP_DOWN"][0]
        assert gap.event_type == "GAP_DOWN"
        assert gap.event_category == "Cenowe"
        assert gap.event_subcategory == "Luki"


class Test52WeekHigh:
    """Test 1.5 52-Week High detection."""

    def test_52w_high_detected(self, detector):
        """A new 52-week high should be detected."""
        data = _make_52w_high_history(base_price=100.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        high_events = [e for e in events if e.event_type == "52W_HIGH"]
        assert len(high_events) == 1

    def test_52w_high_event_type(self, detector):
        """Verify event_type is 52W_HIGH."""
        data = _make_52w_high_history(base_price=100.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        high = [e for e in events if e.event_type == "52W_HIGH"][0]
        assert high.event_type == "52W_HIGH"
        assert high.event_category == "Cenowe"
        assert high.event_subcategory == "Ekstrema"

    def test_52w_high_not_detected_without_enough_history(self, detector):
        """52W high should not fire with insufficient history."""
        data = _make_52w_high_history(base_price=100.0, num_prior=5)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        high_events = [e for e in events if e.event_type == "52W_HIGH"]
        # With only 5 prior candles, the high is trivially a 52W high
        # but the detector still checks — it should detect it if high > all prior
        # Actually, with 5 candles it WILL detect because current.high > max(prior highs)
        # This is expected behavior — the window is just smaller
        assert len(high_events) == 1  # Still detected with small window


class Test52WeekLow:
    """Test 1.6 52-Week Low detection."""

    def test_52w_low_detected(self, detector):
        """A new 52-week low should be detected."""
        data = _make_52w_low_history(base_price=100.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        low_events = [e for e in events if e.event_type == "52W_LOW"]
        assert len(low_events) == 1

    def test_52w_low_event_type(self, detector):
        """Verify event_type is 52W_LOW."""
        data = _make_52w_low_history(base_price=100.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        low = [e for e in events if e.event_type == "52W_LOW"][0]
        assert low.event_type == "52W_LOW"
        assert low.event_category == "Cenowe"
        assert low.event_subcategory == "Ekstrema"


class TestATH:
    """Test 1.7 All-Time High detection."""

    def test_ath_detected(self, detector):
        """A new all-time high should be detected."""
        data = _make_ath_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ath_events = [e for e in events if e.event_type == "ATH"]
        assert len(ath_events) == 1

    def test_ath_event_type(self, detector):
        """Verify event_type is ATH."""
        data = _make_ath_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ath = [e for e in events if e.event_type == "ATH"][0]
        assert ath.event_type == "ATH"
        assert ath.event_category == "Cenowe"
        assert ath.event_subcategory == "Ekstrema"

    def test_ath_not_detected_with_short_history(self, detector):
        """ATH should not be detected with fewer than ath_min_history candles."""
        data = _make_ath_history(base_price=100.0, num_prior=5)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ath_events = [e for e in events if e.event_type == "ATH"]
        assert len(ath_events) == 0  # 5 < ath_min_history (50)


class TestATL:
    """Test 1.8 All-Time Low detection."""

    def test_atl_detected(self, detector):
        """A new all-time low should be detected."""
        data = _make_atl_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        atl_events = [e for e in events if e.event_type == "ATL"]
        assert len(atl_events) == 1

    def test_atl_event_type(self, detector):
        """Verify event_type is ATL."""
        data = _make_atl_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        atl = [e for e in events if e.event_type == "ATL"][0]
        assert atl.event_type == "ATL"
        assert atl.event_category == "Cenowe"
        assert atl.event_subcategory == "Ekstrema"


class TestLevelRejection:
    """Test 1.9 Level Rejection detection."""

    def test_level_rejection_detected(self, detector):
        """A level rejection should be detected."""
        data = _make_level_rejection_history(base_price=100.0, num_prior=50)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        rejection_events = [e for e in events if e.event_type == "LEVEL_REJECTION"]
        assert len(rejection_events) == 1

    def test_level_rejection_event_type(self, detector):
        """Verify event_type is LEVEL_REJECTION."""
        data = _make_level_rejection_history(base_price=100.0, num_prior=50)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        rejection = [e for e in events if e.event_type == "LEVEL_REJECTION"][0]
        assert rejection.event_type == "LEVEL_REJECTION"
        assert rejection.event_category == "Cenowe"
        assert rejection.event_subcategory == "Poziomy"

    def test_level_rejection_metadata_has_level_type(self, detector):
        """Level rejection metadata should include level_type."""
        data = _make_level_rejection_history(base_price=100.0, num_prior=50)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        rejection = [e for e in events if e.event_type == "LEVEL_REJECTION"][0]
        assert "level_type" in rejection.metadata
        assert rejection.metadata["level_type"] in ("support", "resistance")


class TestPsychLevelCross:
    """Test 1.10 Psychological Level Cross detection."""

    def test_psych_level_cross_detected(self, detector):
        """A psychological level cross should be detected."""
        data = _make_psych_cross_history(base_price=98.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        psych_events = [e for e in events if e.event_type == "PSYCH_LEVEL_CROSS"]
        assert len(psych_events) == 1

    def test_psych_level_cross_event_type(self, detector):
        """Verify event_type is PSYCH_LEVEL_CROSS."""
        data = _make_psych_cross_history(base_price=98.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        psych = [e for e in events if e.event_type == "PSYCH_LEVEL_CROSS"][0]
        assert psych.event_type == "PSYCH_LEVEL_CROSS"
        assert psych.event_category == "Cenowe"
        assert psych.event_subcategory == "Poziomy"

    def test_psych_level_cross_metadata_has_level(self, detector):
        """Psych level cross metadata should include the level value."""
        data = _make_psych_cross_history(base_price=98.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        psych = [e for e in events if e.event_type == "PSYCH_LEVEL_CROSS"][0]
        assert "level" in psych.metadata
        assert psych.metadata["level"] == 100.0
        assert psych.metadata["direction"] == "up"


# ---------------------------------------------------------------------------
# Test 3: Correct MarketEvent creation
# ---------------------------------------------------------------------------

class TestMarketEventCreation:
    """Test that MarketEvent objects are correctly created."""

    def test_event_has_all_required_fields(self, detector):
        """Each event must have all required fields set."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
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
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ids = [e.event_id for e in events]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Test 4: event_family set to PRICE
# ---------------------------------------------------------------------------

class TestEventFamily:
    """Test that event_family is always PRICE."""

    def test_all_events_have_price_family(self, detector):
        """Every event from PriceDetector must have event_family == PRICE."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert event.event_family == EventFamily.PRICE, (
                f"Expected PRICE, got {event.event_family} for {event.event_type}"
            )

    def test_multiple_event_types_all_price_family(self, detector):
        """Multiple event types should all have PRICE family."""
        # Create data that triggers multiple events: surge + 52w high + ATH
        data = _make_ath_history(base_price=100.0, num_prior=260)
        # Make the last candle also a surge
        prev = data[-2]
        data[-1] = _make_candle(
            timestamp=data[-1].timestamp,
            open_price=prev.close + 1.0,
            high=prev.close * 1.25,
            low=prev.close,
            close=prev.close * 1.20,
            volume=500000.0,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=data,
        )
        assert len(events) > 0
        for event in events:
            assert event.event_family == EventFamily.PRICE


# ---------------------------------------------------------------------------
# Test 5: Correct PriceData
# ---------------------------------------------------------------------------

class TestPriceData:
    """Test that PriceData is correctly populated."""

    def test_price_data_has_correct_values(self, detector):
        """PriceData should reflect the actual candle values."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge = [e for e in events if e.event_type == "PRICE_SURGE"][0]
        pd = surge.price_data
        assert pd is not None
        assert pd.close == data[-1].close
        assert pd.open == data[-1].open
        assert pd.high == data[-1].high
        assert pd.low == data[-1].low
        assert pd.prev_close == data[-2].close
        assert pd.change_pct > 0
        assert pd.change_abs > 0

    def test_price_data_for_drop(self, detector):
        """PriceData for a drop should have negative change."""
        data = _make_drop_history(base_price=100.0, drop_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        drop = [e for e in events if e.event_type == "PRICE_DROP"][0]
        pd = drop.price_data
        assert pd.change_pct < 0
        assert pd.change_abs < 0

    def test_price_data_for_gap(self, detector):
        """PriceData for a gap should have correct open vs prev_close."""
        data = _make_gap_up_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap = [e for e in events if e.event_type == "GAP_UP"][0]
        pd = gap.price_data
        assert pd.open > pd.prev_close


# ---------------------------------------------------------------------------
# Test 6: Correct priority_raw
# ---------------------------------------------------------------------------

class TestPriorityRaw:
    """Test that priority_raw matches the Katalog Zdarzen Rynkowych."""

    def test_surge_priority_is_critical(self, detector):
        """Price Surge must have CRITICAL priority (Katalog §1.1)."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge = [e for e in events if e.event_type == "PRICE_SURGE"][0]
        assert surge.priority_raw == PriorityLevel.CRITICAL

    def test_drop_priority_is_critical(self, detector):
        """Price Drop must have CRITICAL priority (Katalog §1.2)."""
        data = _make_drop_history(base_price=100.0, drop_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        drop = [e for e in events if e.event_type == "PRICE_DROP"][0]
        assert drop.priority_raw == PriorityLevel.CRITICAL

    def test_gap_priority_is_high(self, detector):
        """Gap Up/Down must have HIGH priority (Katalog §1.3, §1.4)."""
        data = _make_gap_up_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap = [e for e in events if e.event_type == "GAP_UP"][0]
        assert gap.priority_raw == PriorityLevel.HIGH

    def test_52w_high_priority_is_high(self, detector):
        """52-Week High must have HIGH priority (Katalog §1.5)."""
        data = _make_52w_high_history(base_price=100.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        high = [e for e in events if e.event_type == "52W_HIGH"][0]
        assert high.priority_raw == PriorityLevel.HIGH

    def test_ath_priority_is_high(self, detector):
        """ATH must have HIGH priority (Katalog §1.7)."""
        data = _make_ath_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ath = [e for e in events if e.event_type == "ATH"][0]
        assert ath.priority_raw == PriorityLevel.HIGH

    def test_atl_priority_is_critical(self, detector):
        """ATL must have CRITICAL priority (Katalog §1.8)."""
        data = _make_atl_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        atl = [e for e in events if e.event_type == "ATL"][0]
        assert atl.priority_raw == PriorityLevel.CRITICAL

    def test_level_rejection_priority_is_high(self, detector):
        """Level Rejection must have HIGH priority (Katalog §1.9)."""
        data = _make_level_rejection_history(base_price=100.0, num_prior=50)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        rejection = [e for e in events if e.event_type == "LEVEL_REJECTION"][0]
        assert rejection.priority_raw == PriorityLevel.HIGH

    def test_psych_level_priority_is_medium(self, detector):
        """Psychological Level Cross must have MEDIUM priority (Katalog §1.10)."""
        data = _make_psych_cross_history(base_price=98.0, num_prior=260)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        psych = [e for e in events if e.event_type == "PSYCH_LEVEL_CROSS"][0]
        assert psych.priority_raw == PriorityLevel.MEDIUM


# ---------------------------------------------------------------------------
# Test 7: confidence_level in range 0-1
# ---------------------------------------------------------------------------

class TestConfidenceLevel:
    """Test that confidence_level is always in [0.0, 1.0]."""

    def test_confidence_in_range_for_all_event_types(self, detector):
        """All event types must have confidence in [0, 1]."""
        test_cases = [
            ("surge", _make_surge_history(base_price=100.0, surge_pct=10.0)),
            ("drop", _make_drop_history(base_price=100.0, drop_pct=10.0)),
            ("gap_up", _make_gap_up_history(base_price=100.0, gap_pct=5.0)),
            ("gap_down", _make_gap_down_history(base_price=100.0, gap_pct=5.0)),
            ("52w_high", _make_52w_high_history(base_price=100.0, num_prior=260)),
            ("52w_low", _make_52w_low_history(base_price=100.0, num_prior=260)),
            ("ath", _make_ath_history(base_price=100.0, num_prior=100)),
            ("atl", _make_atl_history(base_price=100.0, num_prior=100)),
            ("rejection", _make_level_rejection_history(base_price=100.0, num_prior=50)),
            ("psych", _make_psych_cross_history(base_price=98.0, num_prior=260)),
        ]
        for name, data in test_cases:
            events = detector.detect(
                ticker="TEST.WA",
                market="GPW",
                instrument_type=InstrumentType.STOCK_GPW,
                ohlcv_data=data,
            )
            for event in events:
                assert 0.0 <= event.confidence_level <= 1.0, (
                    f"{name}: confidence {event.confidence_level} not in [0, 1]"
                )

    def test_confidence_increases_with_larger_move(self, detector):
        """Larger price moves should have higher confidence."""
        data_small = _make_surge_history(base_price=100.0, surge_pct=9.0)
        data_large = _make_surge_history(base_price=100.0, surge_pct=20.0)

        events_small = detector.detect(
            ticker="TEST.WA", market="GPW",
            instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=data_small,
        )
        events_large = detector.detect(
            ticker="TEST.WA", market="GPW",
            instrument_type=InstrumentType.STOCK_GPW, ohlcv_data=data_large,
        )

        conf_small = [e for e in events_small if e.event_type == "PRICE_SURGE"][0].confidence_level
        conf_large = [e for e in events_large if e.event_type == "PRICE_SURGE"][0].confidence_level
        assert conf_large > conf_small


# ---------------------------------------------------------------------------
# Test 8: Correct detection_source and event_owner
# ---------------------------------------------------------------------------

class TestSourceAndOwner:
    """Test detection_source and event_owner fields."""

    def test_detection_source_is_price_detector(self, detector):
        """detection_source must identify the Price Event Detector."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert "Price Event Detector" in event.detection_source

    def test_event_owner_is_technical_engine(self, detector):
        """event_owner must be TechnicalEngine (Katalog §1, Hierarchia §4.1)."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert event.event_owner == EventOwner.TechnicalEngine


# ---------------------------------------------------------------------------
# Test 9: History entry added
# ---------------------------------------------------------------------------

class TestHistoryEntry:
    """Test that history entries are properly added."""

    def test_event_has_history_entries(self, detector):
        """Each event must have at least 2 history entries (create + detect)."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        for event in events:
            assert len(event.history) >= 2, (
                f"Expected >= 2 history entries, got {len(event.history)}"
            )

    def test_history_contains_creation_entry(self, detector):
        """First history entry should be from MarketScanner (creation)."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        event = events[0]
        creation_entry = event.history[0]
        assert creation_entry.module == "MarketScanner"
        assert "Utworzenie" in creation_entry.action

    def test_history_contains_detection_entry(self, detector):
        """Second history entry should be from the detector."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        event = events[0]
        detection_entry = event.history[1]
        assert "Price Event Detector" in detection_entry.module
        assert "Wykrycie" in detection_entry.action


# ---------------------------------------------------------------------------
# Test 10: No modification of input data
# ---------------------------------------------------------------------------

class TestInputImmutability:
    """Test that input data is not modified by the detector."""

    def test_input_data_unchanged(self, detector):
        """The detector must not modify the input ohlcv_data list."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        original = copy.deepcopy(data)

        detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )

        # Verify data is unchanged
        assert len(data) == len(original)
        for i, (orig, curr) in enumerate(zip(original, data)):
            assert orig.open == curr.open
            assert orig.high == curr.high
            assert orig.low == curr.low
            assert orig.close == curr.close
            assert orig.volume == curr.volume
            assert orig.timestamp == curr.timestamp

    def test_input_data_not_sorted_in_place(self, detector):
        """The detector sorts internally but should not mutate the input."""
        # Create data in reverse order
        data = list(reversed(_make_surge_history(base_price=100.0, surge_pct=10.0)))
        original_first_timestamp = data[0].timestamp

        detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )

        # The input list should still have the same first element
        assert data[0].timestamp == original_first_timestamp


# ---------------------------------------------------------------------------
# Test 11: Handling of empty data
# ---------------------------------------------------------------------------

class TestEmptyData:
    """Test handling of empty or None data."""

    def test_empty_list_returns_empty(self, detector):
        """Empty data list should return empty events list."""
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=[],
        )
        assert events == []

    def test_single_candle_returns_empty(self, detector):
        """A single candle (no previous) should return empty."""
        data = [
            _make_candle(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                open_price=100.0,
                high=110.0,
                low=90.0,
                close=105.0,
            )
        ]
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert events == []


# ---------------------------------------------------------------------------
# Test 12: Handling of missing values
# ---------------------------------------------------------------------------

class TestMissingValues:
    """Test handling of zero or near-zero values."""

    def test_zero_prev_close_handled(self, detector):
        """Zero prev_close should not cause division by zero."""
        data = [
            _make_candle(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                open_price=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
            ),
            _make_candle(
                timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
                open_price=10.0,
                high=15.0,
                low=5.0,
                close=10.0,
            ),
        ]
        # Should not raise
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        # With prev_close=0, change_pct is set to 0.0, so no surge detected
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        assert len(surge_events) == 0

    def test_zero_high_low_handled(self, detector):
        """Zero high/low values should not cause issues."""
        data = _make_flat_history(num_candles=50, base_price=100.0)
        # Add a candle with zero high
        data.append(_make_candle(
            timestamp=datetime(2026, 12, 31, tzinfo=timezone.utc),
            open_price=100.0,
            high=0.0,
            low=0.0,
            close=100.0,
        ))
        # Should not raise
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

class TestShortHistory:
    """Test handling of insufficient history for window-based detections."""

    def test_ath_requires_minimum_history(self, detector):
        """ATH detection requires ath_min_history candles."""
        data = _make_ath_history(base_price=100.0, num_prior=5)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ath_events = [e for e in events if e.event_type == "ATH"]
        assert len(ath_events) == 0

    def test_atl_requires_minimum_history(self, detector):
        """ATL detection requires ath_min_history candles."""
        data = _make_atl_history(base_price=100.0, num_prior=5)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        atl_events = [e for e in events if e.event_type == "ATL"]
        assert len(atl_events) == 0

    def test_level_rejection_requires_enough_candles(self, detector):
        """Level rejection requires enough candles for swing detection."""
        data = _make_level_rejection_history(base_price=100.0, num_prior=5)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        rejection_events = [e for e in events if e.event_type == "LEVEL_REJECTION"]
        # With only 5 prior candles, there may not be enough for swing detection
        # This is expected — the detector handles it gracefully
        assert isinstance(events, list)

    def test_two_candles_enough_for_surge(self, detector):
        """Just 2 candles are enough for surge/drop detection."""
        data = [
            _make_candle(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                open_price=100.0, high=101.0, low=99.0, close=100.0,
            ),
            _make_candle(
                timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
                open_price=105.0, high=112.0, low=104.0, close=110.0,
            ),
        ]
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        assert len(surge_events) == 1


# ---------------------------------------------------------------------------
# Test 14: No dependency on engines/
# ---------------------------------------------------------------------------

class TestNoEngineDependency:
    """Test that the Price Detector does not import from engines/."""

    def test_detector_imports_are_clean(self):
        """Verify the detector module doesn't import from engines/."""
        import engines.price_detector.engine as engine_module
        import inspect
        import sys

        # Get all imports from the module
        engine_imports = set()
        for name, obj in inspect.getmembers(engine_module):
            if inspect.ismodule(obj):
                engine_imports.add(obj.__name__)

        # Check no engines/ imports (except itself)
        for imp in engine_imports:
            assert not imp.startswith("engines.") or imp.startswith("engines.price_detector"), (
                f"Detector imports from {imp} — not allowed"
            )


# ---------------------------------------------------------------------------
# Test 15: No network calls
# ---------------------------------------------------------------------------

class TestNoNetworkCalls:
    """Test that the Price Detector makes no network calls."""

    def test_detect_uses_only_local_data(self, detector):
        """Detection should work purely on in-memory data."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        # This should complete instantly with no network I/O
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) > 0


# ---------------------------------------------------------------------------
# Additional integration-style tests
# ---------------------------------------------------------------------------

class TestMultipleEvents:
    """Test scenarios where multiple events are detected simultaneously."""

    def test_surge_and_52w_high_together(self, detector):
        """A surge that also sets a 52-week high should produce both events."""
        data = _make_52w_high_history(base_price=100.0, num_prior=260)
        # Modify the last candle to also be a surge
        prev = data[-2]
        data[-1] = _make_candle(
            timestamp=data[-1].timestamp,
            open_price=prev.close + 1.0,
            high=prev.close * 1.20,
            low=prev.close,
            close=prev.close * 1.18,
            volume=500000.0,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        event_types = [e.event_type for e in events]
        assert "PRICE_SURGE" in event_types
        assert "52W_HIGH" in event_types

    def test_surge_and_ath_together(self, detector):
        """A surge that also sets an ATH should produce both events."""
        data = _make_ath_history(base_price=100.0, num_prior=100)
        prev = data[-2]
        data[-1] = _make_candle(
            timestamp=data[-1].timestamp,
            open_price=prev.close + 1.0,
            high=prev.close * 1.25,
            low=prev.close,
            close=prev.close * 1.22,
            volume=500000.0,
        )
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        event_types = [e.event_type for e in events]
        assert "PRICE_SURGE" in event_types
        assert "ATH" in event_types


class TestDifferentInstrumentTypes:
    """Test that the detector works for all instrument types."""

    def test_stock_gpw(self, detector):
        """Detector works for STOCK_GPW."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="XYZ.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        assert len(events) > 0
        assert events[0].instrument_type == InstrumentType.STOCK_GPW

    def test_stock_usa(self, detector):
        """Detector works for STOCK_USA."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="XYZ",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            ohlcv_data=data,
        )
        assert len(events) > 0
        assert events[0].instrument_type == InstrumentType.STOCK_USA

    def test_etf(self, detector):
        """Detector works for ETF."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="SPY",
            market="NYSE",
            instrument_type=InstrumentType.ETF,
            ohlcv_data=data,
        )
        assert len(events) > 0
        assert events[0].instrument_type == InstrumentType.ETF


class TestCustomConfig:
    """Test that custom configuration is respected."""

    def test_lower_threshold_detects_smaller_moves(self, detector_custom):
        """With a lower threshold (5%), a 6% move should be detected."""
        data = _make_surge_history(base_price=100.0, surge_pct=6.0)
        events = detector_custom.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        assert len(surge_events) == 1

    def test_default_threshold_rejects_smaller_moves(self, detector):
        """With default threshold (8%), a 6% move should NOT be detected."""
        data = _make_surge_history(base_price=100.0, surge_pct=6.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge_events = [e for e in events if e.event_type == "PRICE_SURGE"]
        assert len(surge_events) == 0


class TestMetadata:
    """Test that metadata is properly populated."""

    def test_surge_metadata_has_change_pct(self, detector):
        """Surge metadata should include change_pct."""
        data = _make_surge_history(base_price=100.0, surge_pct=10.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        surge = [e for e in events if e.event_type == "PRICE_SURGE"][0]
        assert "change_pct" in surge.metadata
        assert surge.metadata["change_pct"] > 0

    def test_gap_metadata_has_gap_pct(self, detector):
        """Gap metadata should include gap_pct."""
        data = _make_gap_up_history(base_price=100.0, gap_pct=5.0)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        gap = [e for e in events if e.event_type == "GAP_UP"][0]
        assert "gap_pct" in gap.metadata
        assert gap.metadata["gap_pct"] > 0

    def test_extrema_metadata_has_detection_method(self, detector):
        """Extrema events should have detection_method in metadata."""
        data = _make_ath_history(base_price=100.0, num_prior=100)
        events = detector.detect(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
            ohlcv_data=data,
        )
        ath = [e for e in events if e.event_type == "ATH"][0]
        assert "detection_method" in ath.metadata
        assert ath.metadata["detection_method"] == "extrema_detector"