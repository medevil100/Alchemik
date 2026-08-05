"""Testy jednostkowe OutcomeComputer."""

import pytest
from datetime import datetime, timezone, date, timedelta
from unittest.mock import Mock

from engines.outcome.engine import OutcomeComputer, DataIntegrityError, _MARKET_CALENDAR_MAP
from engines.outcome.calendar import TradingCalendar, CalendarExpiredError
from config.outcome import OutcomeConfig
from data.models.market_event import MarketEvent
from data.models.market_data import MarketData
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData
from data.models.event_outcome import EventOutcome, EventOutcomeState
from data.models.session_outcome import SessionOutcome, SessionOutcomeState
from data.models.event_enums import EventFamily, EventOwner, InstrumentType, PriorityLevel, SignalTiming
from data.yahoo.yahoo_exceptions import (
    InvalidSymbolError,
    RateLimitExceededError,
    YahooFinanceError,
)


# ---------------------------------------------------------------------------
# Fake repository do testów
# ---------------------------------------------------------------------------

class FakeOutcomeRepository:
    """Implementacja kontraktu OutcomeRepository w pamięci."""

    def __init__(self):
        self.market_events: dict[str, MarketEvent] = {}
        self.event_outcomes: dict[str, EventOutcome] = {}  # event_outcome_id → EventOutcome
        self.outcome_by_market_event: dict[str, str] = {}  # market_event_id → event_outcome_id
        self.session_outcomes: dict[str, SessionOutcome] = {}  # session_outcome_id → SessionOutcome

    def get_all_market_event_ids(self) -> set[str]:
        return set(self.market_events.keys())

    def get_market_event_by_id(self, event_id: str):
        return self.market_events.get(event_id)

    def get_all_event_outcome_ids(self) -> set[str]:
        return set(self.outcome_by_market_event.keys())

    def save_event_outcome(self, event_outcome):
        self.event_outcomes[event_outcome.event_outcome_id] = event_outcome
        self.outcome_by_market_event[event_outcome.market_event_id] = event_outcome.event_outcome_id

    def get_event_outcome_by_id(self, event_outcome_id: str):
        return self.event_outcomes.get(event_outcome_id)

    def get_event_outcome_by_market_event_id(self, market_event_id: str):
        eo_id = self.outcome_by_market_event.get(market_event_id)
        if eo_id:
            return self.event_outcomes.get(eo_id)
        return None

    def get_pending_session_outcomes(self) -> list[SessionOutcome]:
        return [s for s in self.session_outcomes.values() if s.state == SessionOutcomeState.PENDING]

    def get_session_outcomes_for_event(self, event_outcome_id: str) -> list[SessionOutcome]:
        return [s for s in self.session_outcomes.values() if s.event_outcome_id == event_outcome_id]

    def save_session_outcome(self, session):
        self.session_outcomes[session.session_outcome_id] = session

    def get_event_outcomes_by_state(self, state: EventOutcomeState) -> list[EventOutcome]:
        return [eo for eo in self.event_outcomes.values() if eo.state == state]


# ---------------------------------------------------------------------------
# Helper: tworzenie MarketEvent
# ---------------------------------------------------------------------------

def make_market_event(
    event_id="evt-001",
    ticker="CDR.WA",
    market="GPW",
    ts=None,
    price=100.0,
    volume=10000.0,
):
    """Tworzy MarketEvent z minimalnym zestawem pól."""
    if ts is None:
        ts = datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc)  # poniedziałek — horyzont +1 już dawno minął
    return MarketEvent(
        event_id=event_id,
        timestamp_utc=ts,
        ticker=ticker,
        market=market,
        instrument_type=InstrumentType.STOCK_GPW,
        event_family=EventFamily.PRICE,
        event_category="price",
        event_type="PRICE_SURGE",
        signal_timing=SignalTiming.LEADING,
        priority_raw=PriorityLevel.HIGH,
        priority_final=PriorityLevel.HIGH,
        confidence_level=0.85,
        detection_source="test",
        event_owner=EventOwner.TechnicalEngine,
        price_data=PriceData(
            open=99.0, high=101.0, low=98.0, close=price,
            prev_close=98.0, change_pct=2.0, change_abs=2.0,
        ),
        volume_data=VolumeData(
            current_volume=volume, avg_volume=8000.0,
            volume_ratio=1.25, direction="up",
        ),
    )


# ---------------------------------------------------------------------------
# Testy
# ---------------------------------------------------------------------------

class TestInitializeNewEvents:
    """Testy initialize_new_events()."""

    @pytest.fixture
    def computer(self):
        repo = FakeOutcomeRepository()
        config = OutcomeConfig()
        calendar = TradingCalendar()
        fetcher = Mock()
        return OutcomeComputer(repo, fetcher, calendar, config)

    def test_creates_outcome_for_new_event(self, computer):
        me = make_market_event()
        computer._repo.market_events[me.event_id] = me
        outcomes = computer.initialize_new_events()
        assert len(outcomes) == 1
        assert outcomes[0].market_event_id == "evt-001"
        assert outcomes[0].state == EventOutcomeState.PENDING
        assert outcomes[0].ticker == "CDR.WA"
        assert outcomes[0].market == "GPW"
        assert outcomes[0].base_price == 100.0
        assert outcomes[0].base_volume == 10000.0

    def test_creates_four_sessions(self, computer):
        me = make_market_event()
        computer._repo.market_events[me.event_id] = me
        outcomes = computer.initialize_new_events()
        outcome = outcomes[0]
        sessions = computer._repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        assert len(sessions) == 4
        horizon_ids = {s.horizon_id for s in sessions}
        assert horizon_ids == {"+1", "+2", "+3", "+5"}

    def test_all_sessions_pending(self, computer):
        me = make_market_event()
        computer._repo.market_events[me.event_id] = me
        outcomes = computer.initialize_new_events()
        outcome = outcomes[0]
        sessions = computer._repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        for s in sessions:
            assert s.state == SessionOutcomeState.PENDING
            assert s.attempt_count == 0

    def test_idempotent_second_call(self, computer):
        me = make_market_event()
        computer._repo.market_events[me.event_id] = me
        first = computer.initialize_new_events()
        second = computer.initialize_new_events()
        assert len(first) == 1
        assert len(second) == 0  # już istnieje

    def test_market_copied_as_is(self, computer):
        """Market jest kopiowany bez zmian z MarketEvent."""
        me = make_market_event(market="NYSE")
        computer._repo.market_events[me.event_id] = me
        outcomes = computer.initialize_new_events()
        assert len(outcomes) == 1
        assert outcomes[0].market == "NYSE"  # kopiowane bez zgadywania


class TestComputePendingHorizons:
    """Testy compute_pending_horizons()."""

    @pytest.fixture
    def computer_and_repo(self):
        repo = FakeOutcomeRepository()
        config = OutcomeConfig()
        calendar = TradingCalendar()
        fetcher = Mock()
        computer = OutcomeComputer(repo, fetcher, calendar, config)
        return computer, repo, fetcher, calendar

    def _setup_event(self, computer, repo, market="GPW"):
        me = make_market_event(market=market)
        repo.market_events[me.event_id] = me
        outcomes = computer.initialize_new_events()
        return outcomes[0]

    def test_market_not_specified_skips(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        # Utwórz z niepustym market (wymagane przez model), potem nadpisz
        outcome = self._setup_event(computer, repo, market="GPW")
        outcome.market = ""
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        updated = computer.compute_pending_horizons()
        assert updated == 4
        for s in sessions:
            s_updated = repo.session_outcomes[s.session_outcome_id]
            assert s_updated.state == SessionOutcomeState.SKIPPED
            assert s_updated.skip_reason == "market_not_specified"

    def test_unknown_market_skips(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo, market="GPW")
        outcome.market = "LSE"
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        updated = computer.compute_pending_horizons()
        assert updated == 4
        for s in sessions:
            s_updated = repo.session_outcomes[s.session_outcome_id]
            assert s_updated.state == SessionOutcomeState.SKIPPED
            assert s_updated.skip_reason == "unknown_market"

    def test_horizon_not_reached_yet_skips(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        # Ustaw timestamp na "teraz" — horyzont +1 jeszcze nie upłynął
        me = make_market_event(ts=datetime.now(timezone.utc) - timedelta(minutes=5))
        repo.market_events[me.event_id] = me
        computer.initialize_new_events()
        updated = computer.compute_pending_horizons()
        # Sesja horyzontowa jeszcze nie nadeszła (resolve_session_date > now)
        assert updated == 0

    def test_calendar_expired_fails(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        me = make_market_event(ts=datetime(2030, 12, 31, 14, 30, tzinfo=timezone.utc))
        repo.market_events[me.event_id] = me
        outcome = computer.initialize_new_events()[0]
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        # Dla horyzontów poza 2030 — calendar_expired
        updated = computer.compute_pending_horizons()
        # +1 powinno być FAILED (calendar_expired), reszta też
        assert updated >= 1
        failed = [s for s in repo.session_outcomes.values() if s.state == SessionOutcomeState.FAILED and s.failure_reason == "calendar_expired"]
        assert len(failed) >= 1

    def test_instrument_delisted_skips(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo)
        fetcher.fetch_stock_data.side_effect = InvalidSymbolError("delisted")
        sessions_before = repo.get_pending_session_outcomes()
        assert len(sessions_before) == 4
        updated = computer.compute_pending_horizons()
        # Wszystkie sesje SKIPPED (pierwsza + kaskada dla pozostałych, może być >4)
        assert updated >= 4
        for s in repo.session_outcomes.values():
            assert s.state == SessionOutcomeState.SKIPPED
            assert s.skip_reason == "instrument_delisted"

    def test_rate_limit_retry_then_fail(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo)
        fetcher.fetch_stock_data.side_effect = RateLimitExceededError("rate limit")
        # 5 prób (max_retry_attempts=5)
        for i in range(5):
            updated = computer.compute_pending_horizons()
        # Sprawdź stan sesji — powinny być FAILED z rate_limit_exceeded
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        failed_sessions = [s for s in sessions if s.state == SessionOutcomeState.FAILED]
        assert len(failed_sessions) == 4
        for s in failed_sessions:
            assert s.failure_reason == "rate_limit_exceeded"

    def test_successful_computation(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo)

        # Mock danych rynkowych dla daty sesji (wtorek 2026-07-21)
        md = MarketData(
            open=100.0, high=105.0, low=99.0, close=103.0, volume=12000.0,
            timestamp=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )
        fetcher.fetch_stock_data.return_value = [md]

        updated = computer.compute_pending_horizons()
        assert updated >= 1

        # Sesja +1 powinna być CALCULATED
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        calc = [s for s in sessions if s.horizon_id == "+1" and s.state == SessionOutcomeState.CALCULATED]
        assert len(calc) == 1
        s = calc[0]
        assert s.close_price == 103.0
        assert s.high_price == 105.0
        assert s.low_price == 99.0
        assert s.volume == 12000.0
        assert s.price_change_pct == pytest.approx(3.0)  # (103-100)/100*100
        assert s.price_change_abs == pytest.approx(3.0)
        assert s.volume_change_pct == pytest.approx(20.0)  # (12000-10000)/10000*100
        assert s.data_source == "YahooFinance"

    def test_no_data_for_session_retry_then_fail(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo)

        # Zwróć puste dane (brak dla daty sesji)
        md = MarketData(
            open=100.0, high=105.0, low=99.0, close=103.0, volume=12000.0,
            timestamp=datetime(2026, 8, 10, tzinfo=timezone.utc),  # inna data — nie pasuje do 2026-07-21
        )
        fetcher.fetch_stock_data.return_value = [md]

        for _ in range(5):
            computer.compute_pending_horizons()

        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        failed = [s for s in sessions if s.state == SessionOutcomeState.FAILED and s.failure_reason == "no_data_for_session"]
        assert len(failed) == 4

    def test_no_base_price_still_calculated(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo)
        outcome.base_price = None  # brak ceny bazowej

        md = MarketData(
            open=100.0, high=105.0, low=99.0, close=103.0, volume=12000.0,
            timestamp=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )
        fetcher.fetch_stock_data.return_value = [md]

        computer.compute_pending_horizons()
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        calc = [s for s in sessions if s.horizon_id == "+1"]
        assert len(calc) == 1
        assert calc[0].state == SessionOutcomeState.CALCULATED
        assert calc[0].price_change_pct is None
        assert calc[0].price_change_abs is None

    def test_attempt_count_increments(self, computer_and_repo):
        computer, repo, fetcher, _ = computer_and_repo
        outcome = self._setup_event(computer, repo)
        fetcher.fetch_stock_data.side_effect = YahooFinanceError("temp error")
        computer.compute_pending_horizons()
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        for s in sessions:
            s_updated = repo.session_outcomes[s.session_outcome_id]
            assert s_updated.attempt_count == 1


class TestUpdateEventOutcomeState:
    """Testy _update_event_outcome_state()."""

    @pytest.fixture
    def computer_and_repo(self):
        repo = FakeOutcomeRepository()
        config = OutcomeConfig()
        calendar = TradingCalendar()
        fetcher = Mock()
        return OutcomeComputer(repo, fetcher, calendar, config), repo

    def _setup_outcome_with_sessions(self, computer, repo):
        me = make_market_event()
        repo.market_events[me.event_id] = me
        outcomes = computer.initialize_new_events()
        return outcomes[0]

    def test_pending_state(self, computer_and_repo):
        computer, repo = computer_and_repo
        outcome = self._setup_outcome_with_sessions(computer, repo)
        assert outcome.state == EventOutcomeState.PENDING

    def test_all_skipped_becomes_invalid(self, computer_and_repo):
        computer, repo = computer_and_repo
        outcome = self._setup_outcome_with_sessions(computer, repo)
        for s in repo.get_session_outcomes_for_event(outcome.event_outcome_id):
            s.state = SessionOutcomeState.SKIPPED
            s.skip_reason = "market_not_specified"
            repo.save_session_outcome(s)
        computer._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
        updated = repo.event_outcomes[outcome.event_outcome_id]
        assert updated.state == EventOutcomeState.INVALID

    def test_mixed_calculated_and_skipped_becomes_complete(self, computer_and_repo):
        computer, repo = computer_and_repo
        outcome = self._setup_outcome_with_sessions(computer, repo)
        sessions = repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        sessions[0].state = SessionOutcomeState.CALCULATED
        sessions[1].state = SessionOutcomeState.CALCULATED
        sessions[2].state = SessionOutcomeState.SKIPPED
        sessions[2].skip_reason = "instrument_delisted"
        sessions[3].state = SessionOutcomeState.SKIPPED
        sessions[3].skip_reason = "instrument_delisted"
        for s in sessions:
            repo.save_session_outcome(s)
        computer._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
        updated = repo.event_outcomes[outcome.event_outcome_id]
        assert updated.state == EventOutcomeState.COMPLETE


class TestDataIntegrity:
    """Testy integralności danych."""

    def test_orphaned_session_raises_data_integrity_error(self):
        repo = FakeOutcomeRepository()
        config = OutcomeConfig()
        calendar = TradingCalendar()
        fetcher = Mock()
        computer = OutcomeComputer(repo, fetcher, calendar, config)

        # Utwórz osierocony SessionOutcome bez EventOutcome
        session = SessionOutcome(
            session_outcome_id="orphan-1",
            event_outcome_id="non-existent",
            horizon_id="+1",
            state=SessionOutcomeState.PENDING,
        )
        repo.session_outcomes[session.session_outcome_id] = session

        with pytest.raises(DataIntegrityError, match="references non-existent EventOutcome"):
            computer.compute_pending_horizons()