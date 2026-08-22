"""
Test-first RED — kontrakt domenowy timeframe i candle_state (Krok 7C.4A).

Wariant A+C zatwierdzony przez właściciela 2026-08-21.

Testy wyłącznie domenowe (modele InstrumentReading / InstrumentObservation),
bez SQLite, bez migracji, bez mocków i bez silników.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from data.models.instrument_reading import InstrumentReading
from data.models.instrument_observation import InstrumentObservation


def _make_observation(instrument_id="SYNTH-001", observation_id="obs-001", timeframe="1h"):
    return InstrumentObservation(
        observation_id=observation_id,
        instrument_id=instrument_id,
        timeframe=timeframe,
    )


def _make_reading(
    instrument_id="SYNTH-001",
    observation_id="obs-001",
    market_ts=None,
    timeframe="1h",
    candle_state="OPEN",
):
    if market_ts is None:
        market_ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    return InstrumentReading(
        reading_id="rdg-1",
        observation_id=observation_id,
        instrument_id=instrument_id,
        market_data_timestamp=market_ts,
        scan_timestamp=datetime(2026, 8, 21, 12, 15, tzinfo=timezone.utc),
        open=100.0,
        high=105.0,
        low=99.0,
        close=102.0,
        volume=1000.0,
        timeframe=timeframe,
        candle_state=candle_state,
    )


class TestReadingTimeframe:
    def test_reading_has_timeframe_field(self):
        reading = _make_reading(timeframe="1h")
        assert reading.timeframe == "1h"

    def test_reading_has_candle_state_field(self):
        reading = _make_reading(candle_state="OPEN")
        assert reading.candle_state == "OPEN"

    def test_canonical_identity_distinguishes_5m_and_1h(self):
        ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        reading_5m = _make_reading(market_ts=ts, timeframe="5m")
        reading_1h = _make_reading(market_ts=ts, timeframe="1h")
        assert reading_5m.canonical_identity() != reading_1h.canonical_identity()

    def test_timeframe_immutable(self):
        reading = _make_reading(timeframe="1h")
        with pytest.raises(AttributeError):
            reading.timeframe = "5m"

    def test_candle_state_immutable(self):
        reading = _make_reading(candle_state="OPEN")
        with pytest.raises(AttributeError):
            reading.candle_state = "CLOSED"

    def test_allowed_candle_states_include_open_closed_legacy(self):
        for state in ("OPEN", "CLOSED", "LEGACY_UNKNOWN"):
            reading = _make_reading(candle_state=state)
            assert reading.candle_state == state


class TestObservationTimeframe:
    def test_observation_has_timeframe_field(self):
        obs = _make_observation(timeframe="1h")
        assert obs.timeframe == "1h"

    def test_observation_timeframe_immutable(self):
        obs = _make_observation(timeframe="1h")
        with pytest.raises(AttributeError):
            obs.timeframe = "5m"


class TestRetiredTimeframe:
    def test_active_observation_can_be_retired_via_public_api(self):
        """ACTIVE Observation może zostać zakończona przez istniejące publiczne
        API terminate() ze statusem RETIRED_TIMEFRAME i jawnym powodem."""
        obs = _make_observation(timeframe="5m")
        obs.terminate("RETIRED_TIMEFRAME", "przejście na 1h")
        assert obs.state == "RETIRED_TIMEFRAME"

    def test_retirement_records_status_and_reason(self):
        """Po zakończeniu status, terminated_at i termination_reason są poprawne."""
        obs = _make_observation(timeframe="5m")
        obs.terminate("RETIRED_TIMEFRAME", "archiwum 5m")
        assert obs.state == "RETIRED_TIMEFRAME"
        assert obs.terminated_at is not None
        assert obs.termination_reason == "archiwum 5m"

    def test_retired_timeframe_is_terminal(self):
        """RETIRED_TIMEFRAME zachowuje się terminalnie: nie można wykonać
        kolejnego przejścia terminalnego ani reaktywować do ACTIVE."""
        obs = _make_observation(timeframe="5m")
        obs.terminate("RETIRED_TIMEFRAME", "koniec 5m")
        with pytest.raises(ValueError):
            obs.state = "ACTIVE"

    def test_retired_timeframe_not_reactivated_as_active(self):
        """RETIRED_TIMEFRAME nie może zostać reaktywowany jako ACTIVE."""
        obs = _make_observation(timeframe="5m")
        obs.terminate("RETIRED_TIMEFRAME", "koniec 5m")
        with pytest.raises(ValueError):
            obs.state = "ACTIVE"

    def test_integrity_breached_semantics_preserved(self):
        """INTEGRITY_BREACHED pozostaje terminalny i nie może być cofnięty."""
        obs = _make_observation(timeframe="5m")
        obs.terminate("INTEGRITY_BREACHED", "konflikt treści")
        assert obs.state == "INTEGRITY_BREACHED"
        with pytest.raises(ValueError):
            obs.state = "ACTIVE"


class TestDistinctDomainIdentities:
    def test_5m_and_1h_form_distinct_domain_identities(self):
        ts = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        reading_5m = _make_reading(market_ts=ts, timeframe="5m")
        reading_1h = _make_reading(market_ts=ts, timeframe="1h")
        assert reading_5m.canonical_identity() != reading_1h.canonical_identity()
