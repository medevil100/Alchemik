"""
Testy jednostkowe dla modeli domenowych InstrumentObservation i InstrumentReading.

KROK 4 — Test First: testy napisane przed implementacja modeli.
Testy korzystaja wylacznie z rzeczywistych nowych modeli.
Dane testowe sa syntetyczne.
"""

import uuid
from datetime import datetime, timezone

import pytest


# =============================================================================
# Testy InstrumentObservation
# =============================================================================


class TestInstrumentObservationCreation:
    """Testy tworzenia InstrumentObservation w stanie ACTIVE."""

    def test_created_observation_is_active(self):
        """Nowo utworzona obserwacja ma stan ACTIVE."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        assert obs.state == "ACTIVE"

    def test_observation_id_is_immutable(self):
        """observation_id nie moze byc zmienione po utworzeniu."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(Exception):
            obs.observation_id = "obs-002"

    def test_instrument_id_is_immutable(self):
        """instrument_id nie moze byc zmienione po utworzeniu."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(Exception):
            obs.instrument_id = "SYNTH-002"

    def test_created_at_is_set_on_creation(self):
        """Pole created_at jest ustawiane automatycznie przy tworzeniu."""
        from data.models.instrument_observation import InstrumentObservation

        before = datetime.now(timezone.utc)
        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        after = datetime.now(timezone.utc)
        assert obs.created_at is not None
        assert before <= obs.created_at <= after

    def test_terminated_at_is_none_on_creation(self):
        """Nowo utworzona obserwacja nie ma terminated_at."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        assert obs.terminated_at is None

    def test_termination_reason_is_none_on_creation(self):
        """Nowo utworzona obserwacja nie ma termination_reason."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        assert obs.termination_reason is None


class TestInstrumentObservationTransitions:
    """Testy przejsc miedzy stanami."""

    def test_active_to_active_allowed(self):
        """Przejscie ACTIVE -> ACTIVE jest dozwolone."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.state = "ACTIVE"
        assert obs.state == "ACTIVE"

    def test_active_to_terminated_domain_with_reason(self):
        """Przejscie ACTIVE -> TERMINATED_DOMAIN po przekazaniu jawnej przyczyny."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("TERMINATED_DOMAIN", "observation_completed")
        assert obs.state == "TERMINATED_DOMAIN"
        assert obs.termination_reason == "observation_completed"
        assert obs.terminated_at is not None

    def test_active_to_terminated_technical_with_reason(self):
        """Przejscie ACTIVE -> TERMINATED_TECHNICAL po przekazaniu jawnej przyczyny."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("TERMINATED_TECHNICAL", "fetch_failure")
        assert obs.state == "TERMINATED_TECHNICAL"
        assert obs.termination_reason == "fetch_failure"
        assert obs.terminated_at is not None

    def test_active_to_integrity_breached_with_reason(self):
        """Przejscie ACTIVE -> INTEGRITY_BREACHED po przekazaniu jawnej przyczyny."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("INTEGRITY_BREACHED", "data_corruption")
        assert obs.state == "INTEGRITY_BREACHED"
        assert obs.termination_reason == "data_corruption"
        assert obs.terminated_at is not None


class TestInstrumentObservationForbiddenTransitions:
    """Testy zabronionych przejsc."""

    def test_terminated_domain_cannot_return_to_active(self):
        """Po TERMINATED_DOMAIN nie mozna wrocic do ACTIVE."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("TERMINATED_DOMAIN", "observation_completed")
        with pytest.raises(ValueError, match="terminal"):
            obs.state = "ACTIVE"

    def test_terminated_technical_cannot_return_to_active(self):
        """Po TERMINATED_TECHNICAL nie mozna wrocic do ACTIVE."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("TERMINATED_TECHNICAL", "fetch_failure")
        with pytest.raises(ValueError, match="terminal"):
            obs.state = "ACTIVE"

    def test_integrity_breached_cannot_return_to_active(self):
        """Po INTEGRITY_BREACHED nie mozna wrocic do ACTIVE."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("INTEGRITY_BREACHED", "data_corruption")
        with pytest.raises(ValueError, match="terminal"):
            obs.state = "ACTIVE"

    def test_terminated_domain_cannot_transition_to_terminated_technical(self):
        """Po TERMINATED_DOMAIN nie mozna przejsc do TERMINATED_TECHNICAL."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("TERMINATED_DOMAIN", "observation_completed")
        with pytest.raises(ValueError, match="terminal"):
            obs.terminate("TERMINATED_TECHNICAL", "fetch_failure")

    def test_terminated_domain_cannot_transition_to_integrity_breached(self):
        """Po TERMINATED_DOMAIN nie mozna przejsc do INTEGRITY_BREACHED."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        obs.terminate("TERMINATED_DOMAIN", "observation_completed")
        with pytest.raises(ValueError, match="terminal"):
            obs.terminate("INTEGRITY_BREACHED", "data_corruption")

    def test_cannot_terminate_without_reason(self):
        """Przejscie terminalne wymaga jawnej przyczyny."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(ValueError):
            obs.terminate("TERMINATED_DOMAIN", "")

    def test_cannot_terminate_with_invalid_state(self):
        """Nie mozna terminowac do nieprawidlowego stanu."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(ValueError):
            obs.terminate("INVALID_STATE", "reason")


class TestInstrumentObservationNoCompletedState:
    """Stan COMPLETED nie istnieje w lifecycle InstrumentObservation."""

    def test_completed_not_in_allowed_states(self):
        """Model nie akceptuje stanu COMPLETED."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(ValueError):
            obs.state = "COMPLETED"

    def test_completed_not_allowed_in_terminate(self):
        """Nie mozna terminowac do COMPLETED."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(ValueError):
            obs.terminate("COMPLETED", "some_reason")


class TestInstrumentObservationAllowedStates:
    """Tylko 4 stany sa dozwolone."""

    def test_allowed_states_are_only_four(self):
        """Model akceptuje tylko ACTIVE, TERMINATED_DOMAIN, TERMINATED_TECHNICAL, INTEGRITY_BREACHED
        — każdy stan mozna ustawic na swiezej instancji (ACTIVE → terminal)."""
        from data.models.instrument_observation import InstrumentObservation

        # ACTIVE — default
        obs1 = InstrumentObservation(observation_id="obs-001", instrument_id="SYNTH-001")
        assert obs1.state == "ACTIVE"

        # TERMINATED_DOMAIN via terminate from ACTIVE
        obs2 = InstrumentObservation(observation_id="obs-002", instrument_id="SYNTH-001")
        obs2.terminate("TERMINATED_DOMAIN", "domain_reason")
        assert obs2.state == "TERMINATED_DOMAIN"

        # TERMINATED_TECHNICAL via terminate from ACTIVE
        obs3 = InstrumentObservation(observation_id="obs-003", instrument_id="SYNTH-001")
        obs3.terminate("TERMINATED_TECHNICAL", "tech_reason")
        assert obs3.state == "TERMINATED_TECHNICAL"

        # INTEGRITY_BREACHED via terminate from ACTIVE
        obs4 = InstrumentObservation(observation_id="obs-004", instrument_id="SYNTH-001")
        obs4.terminate("INTEGRITY_BREACHED", "integrity_reason")
        assert obs4.state == "INTEGRITY_BREACHED"

    def test_non_allowed_state_raises(self):
        """Nieprawidlowy stan powoduje ValueError."""
        from data.models.instrument_observation import InstrumentObservation

        obs = InstrumentObservation(
            observation_id="obs-001",
            instrument_id="SYNTH-001",
        )
        with pytest.raises(ValueError):
            obs.state = "PENDING"


# =============================================================================
# Testy InstrumentReading
# =============================================================================


class TestInstrumentReadingCreation:
    """Testy tworzenia InstrumentReading."""

    def test_create_reading_with_required_fields(self):
        """InstrumentReading tworzy sie z wymaganymi polami."""
        from data.models.instrument_reading import InstrumentReading

        ts = datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc)
        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.reading_id == "rdg-001"
        assert reading.observation_id == "obs-001"
        assert reading.instrument_id == "SYNTH-001"
        assert reading.market_data_timestamp == ts

    def test_reading_default_source(self):
        """Domyslne zrodlo danych."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.source == "YahooFinance"

    def test_custom_source_is_rejected(self):
        """Tylko YahooFinance jest dozwolonym zrodlem danych."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="YahooFinance"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                source="CustomSource",
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=50000.0,
            )

    def test_reading_prev_reading_optional(self):
        """Poprzedni odczyt jest opcjonalny."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.prev_reading_id is None

    def test_reading_prev_reading_set(self):
        """Mozna ustawic relacje do poprzedniego odczytu."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-002",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            prev_reading_id="rdg-001",
            open=101.0,
            high=106.0,
            low=100.0,
            close=104.0,
            volume=55000.0,
        )
        assert reading.prev_reading_id == "rdg-001"


class TestInstrumentReadingImmutability:
    """Testy niezmiennosci InstrumentReading."""

    def test_reading_id_is_immutable(self):
        """reading_id jest niezmienne."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        with pytest.raises(Exception):
            reading.reading_id = "rdg-002"

    def test_observation_id_is_immutable(self):
        """observation_id jest niezmienne."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        with pytest.raises(Exception):
            reading.observation_id = "obs-002"

    def test_instrument_id_is_immutable(self):
        """instrument_id jest niezmienne."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        with pytest.raises(Exception):
            reading.instrument_id = "SYNTH-002"

    def test_market_data_timestamp_is_immutable(self):
        """market_data_timestamp jest niezmienne."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        with pytest.raises(Exception):
            reading.market_data_timestamp = datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc)

    def test_close_price_is_immutable(self):
        """Dane OHLCV sa niezmienne po utworzeniu."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        with pytest.raises(Exception):
            reading.close = 200.0


class TestInstrumentReadingCanonicalIdentity:
    """Testy kanonicznej pary tozsamosci (instrument_id, market_data_timestamp)."""

    def test_canonical_identity_method(self):
        """Model udostepnia kanoniczna pare jako fakt domenowy."""
        from data.models.instrument_reading import InstrumentReading

        ts = datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc)
        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        identity = reading.canonical_identity()
        assert identity == ("SYNTH-001", ts)

    def test_canonical_identity_different_instruments(self):
        """Rozne instrumenty maja rozne pary kanoniczne."""
        from data.models.instrument_reading import InstrumentReading

        ts = datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc)
        r1 = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        r2 = InstrumentReading(
            reading_id="rdg-002",
            observation_id="obs-002",
            instrument_id="SYNTH-002",
            market_data_timestamp=ts,
            scan_timestamp=datetime.now(timezone.utc),
            open=50.0,
            high=55.0,
            low=49.0,
            close=53.0,
            volume=30000.0,
        )
        assert r1.canonical_identity() != r2.canonical_identity()


class TestInstrumentReadingNoData:
    """Testy blokady reprezentowania NO_DATA, SOURCE_ERROR, timeout."""

    def cannot_create_reading_called_no_data(self):
        """Nie mozna utworzyc odczytu o tresci NO_DATA."""
        # Model nie ma specjalnego typu dla NO_DATA — kazdy odczyt musi miec dane OHLCV
        from data.models.instrument_reading import InstrumentReading

        # Proba utworzenia readingu z None w danych OHLCV powinna byc odrzucona
        with pytest.raises(ValueError):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                open=None,
                high=None,
                low=None,
                close=None,
                volume=None,
            )

    def cannot_create_reading_called_source_error(self):
        """Model nie reprezentuje SOURCE_ERROR."""
        # SOURCE_ERROR nie jest stanem odczytu — to zdarzenie operacyjne
        pass

    def cannot_create_reading_called_timeout(self):
        """Model nie reprezentuje timeoutu."""
        # Timeout nie jest stanem odczytu — to zdarzenie operacyjne
        pass


class TestInstrumentReadingDataCompleteness:
    """Testy pola data_completeness."""

    def test_complete_reading_has_all_ohlc(self):
        """COMPLETE wymaga open, high, low i close."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            data_completeness="COMPLETE",
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.data_completeness == "COMPLETE"

    def test_complete_reading_default(self):
        """Domyślnie data_completeness to COMPLETE."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.data_completeness == "COMPLETE"

    def test_complete_requires_open(self):
        """COMPLETE odrzuca brak open."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="COMPLETE"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                data_completeness="COMPLETE",
                open=None,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=50000.0,
            )

    def test_complete_requires_high(self):
        """COMPLETE odrzuca brak high."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="COMPLETE"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                data_completeness="COMPLETE",
                open=100.0,
                high=None,
                low=99.0,
                close=103.0,
                volume=50000.0,
            )

    def test_complete_requires_low(self):
        """COMPLETE odrzuca brak low."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="COMPLETE"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                data_completeness="COMPLETE",
                open=100.0,
                high=105.0,
                low=None,
                close=103.0,
                volume=50000.0,
            )

    def test_complete_requires_close(self):
        """COMPLETE odrzuca brak close."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="COMPLETE"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                data_completeness="COMPLETE",
                open=100.0,
                high=105.0,
                low=99.0,
                close=None,
                volume=50000.0,
            )

    def test_complete_volume_optional(self):
        """COMPLETE dopuszcza brak volume."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            data_completeness="COMPLETE",
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=None,
        )
        assert reading.volume is None

    def test_partial_allows_missing_open(self):
        """PARTIAL dopuszcza brak open."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            data_completeness="PARTIAL",
            open=None,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.data_completeness == "PARTIAL"
        assert reading.open is None

    def test_partial_allows_missing_high(self):
        """PARTIAL dopuszcza brak high."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            data_completeness="PARTIAL",
            open=100.0,
            high=None,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        assert reading.high is None

    def test_partial_allows_missing_low(self):
        """PARTIAL dopuszcza brak low."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            data_completeness="PARTIAL",
            open=100.0,
            high=105.0,
            low=None,
            close=103.0,
            volume=50000.0,
        )
        assert reading.low is None

    def test_partial_requires_close(self):
        """PARTIAL wymaga close."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="PARTIAL.*close"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                data_completeness="PARTIAL",
                open=100.0,
                high=105.0,
                low=99.0,
                close=None,
                volume=50000.0,
            )

    def test_partial_allows_volume_missing(self):
        """PARTIAL dopuszcza brak volume."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            data_completeness="PARTIAL",
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=None,
        )
        assert reading.volume is None

    def test_invalid_data_completeness_rejected(self):
        """Nieprawidlowa wartosc data_completeness jest odrzucana."""
        from data.models.instrument_reading import InstrumentReading

        with pytest.raises(ValueError, match="data_completeness"):
            InstrumentReading(
                reading_id="rdg-001",
                observation_id="obs-001",
                instrument_id="SYNTH-001",
                market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
                scan_timestamp=datetime.now(timezone.utc),
                data_completeness="INVALID",
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=50000.0,
            )

    def test_data_completeness_is_immutable(self):
        """data_completeness jest niezmienne po utworzeniu."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-001",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=50000.0,
        )
        with pytest.raises(Exception):
            reading.data_completeness = "PARTIAL"


class TestInstrumentReadingPrevReading:
    """Testy relacji do poprzedniego odczytu."""

    def test_prev_reading_stored_as_id(self):
        """Relacja do poprzedniego odczytu przechowywana jako reading_id."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-002",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            prev_reading_id="rdg-001",
            open=101.0,
            high=106.0,
            low=100.0,
            close=104.0,
            volume=55000.0,
        )
        assert reading.prev_reading_id == "rdg-001"

    def test_prev_reading_id_is_immutable(self):
        """prev_reading_id jest niezmienne po utworzeniu."""
        from data.models.instrument_reading import InstrumentReading

        reading = InstrumentReading(
            reading_id="rdg-002",
            observation_id="obs-001",
            instrument_id="SYNTH-001",
            market_data_timestamp=datetime(2026, 8, 4, 14, 30, tzinfo=timezone.utc),
            scan_timestamp=datetime.now(timezone.utc),
            prev_reading_id="rdg-001",
            open=101.0,
            high=106.0,
            low=100.0,
            close=104.0,
            volume=55000.0,
        )
        with pytest.raises(Exception):
            reading.prev_reading_id = "rdg-003"