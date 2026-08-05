"""OutcomeComputer — komponent obliczeniowy rezultatów zdarzeń rynkowych."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from .calendar import TradingCalendar, CalendarExpiredError
from config.outcome import OutcomeConfig
from data.models.market_event import MarketEvent
from data.models.market_data import MarketData
from data.yahoo.yahoo_fetcher import YahooFetcher
from data.yahoo.yahoo_exceptions import (
    InvalidSymbolError,
    RateLimitExceededError,
    YahooFinanceError,
)

logger = logging.getLogger(__name__)

# Stała mapowania rynków (importowana przez OutcomeComputer do walidacji)
_MARKET_CALENDAR_MAP: dict[str, str] = {
    "GPW": "GPW",
    "NYSE": "US",
    "NASDAQ": "US",
    "US": "US",
}


class DataIntegrityError(Exception):
    """Naruszenie integralności danych — np. osierocony SessionOutcome."""


class OutcomeComputer:
    """
    Komponent odpowiedzialny za obliczanie rezultatów zdarzeń rynkowych.

    Tworzy EventOutcome i SessionOutcome dla nowych MarketEvent,
    pobiera dane rynkowe przez YahooFetcher, oblicza metryki
    i zarządza cyklami życia obu modeli.
    """

    def __init__(self, repository, yahoo_fetcher, calendar, config):
        """
        Args:
            repository: Obiekt implementujący kontrakt OutcomeRepository (duck typing).
            yahoo_fetcher: YahooFetcher — istniejący komponent pobierania danych.
            calendar: TradingCalendar — kalendarz sesji handlowych.
            config: OutcomeConfig — konfiguracja.
        """
        self._repo = repository
        self._fetcher: YahooFetcher = yahoo_fetcher
        self._calendar: TradingCalendar = calendar
        self._config: OutcomeConfig = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize_new_events(self) -> list:
        """Tworzy EventOutcome + SessionOutcome dla nowych MarketEvent."""
        # Opóźniony import — unikanie cykli w testach jednostkowych
        from data.models.event_outcome import EventOutcome, EventOutcomeState
        from data.models.session_outcome import SessionOutcome, SessionOutcomeState

        try:
            all_event_ids = self._repo.get_all_market_event_ids()
        except AttributeError:
            logger.warning("Repository does not support get_all_market_event_ids()")
            return []
        try:
            existing_outcome_ids = self._repo.get_all_event_outcome_ids()
        except AttributeError:
            logger.warning("Repository does not support get_all_event_outcome_ids()")
            return []

        new_ids = sorted(all_event_ids - existing_outcome_ids)
        new_outcomes = []

        for event_id in new_ids:
            market_event = self._repo.get_market_event_by_id(event_id)
            if market_event is None:
                logger.warning("MarketEvent %s not found in repository", event_id)
                continue
            if not market_event.ticker or not market_event.ticker.strip():
                logger.warning("MarketEvent %s has empty ticker — skipping", event_id)
                continue
            if market_event.timestamp_utc is None:
                logger.warning("MarketEvent %s has no timestamp_utc — skipping", event_id)
                continue

            outcome = self._create_event_outcome(market_event, EventOutcome, EventOutcomeState)
            self._repo.save_event_outcome(outcome)

            for horizon_id in self._config.horizons:
                session = self._create_session_outcome(
                    outcome, horizon_id, SessionOutcome, SessionOutcomeState
                )
                self._repo.save_session_outcome(session)

            new_outcomes.append(outcome)

        return new_outcomes

    def compute_pending_horizons(self) -> int:
        """Oblicza metryki dla PENDING SessionOutcome z upłyniętym horyzontem."""
        from data.models.event_outcome import EventOutcomeState
        from data.models.session_outcome import SessionOutcomeState

        try:
            pending_sessions = self._repo.get_pending_session_outcomes()
        except AttributeError:
            logger.warning("Repository does not support get_pending_session_outcomes()")
            return 0

        # Sortowanie deterministyczne
        pending_sessions.sort(key=lambda s: (s.event_outcome_id, s.horizon_id))

        updated = 0
        for session in pending_sessions:
            try:
                outcome = self._repo.get_event_outcome_by_id(session.event_outcome_id)
            except AttributeError:
                logger.error("Repository does not support get_event_outcome_by_id()")
                break

            if outcome is None:
                raise DataIntegrityError(
                    f"SessionOutcome {session.session_outcome_id} "
                    f"references non-existent EventOutcome {session.event_outcome_id}"
                )

            market_raw = getattr(outcome, "market", "") or ""
            market_norm = market_raw.strip()

            # Walidacja rynku w OutcomeComputer (nie w TradingCalendar)
            if not market_norm:
                session.state = SessionOutcomeState.SKIPPED
                session.skip_reason = "market_not_specified"
                self._repo.save_session_outcome(session)
                updated += 1
                self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                continue

            if market_norm not in _MARKET_CALENDAR_MAP:
                session.state = SessionOutcomeState.SKIPPED
                session.skip_reason = "unknown_market"
                self._repo.save_session_outcome(session)
                updated += 1
                self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                continue

            try:
                horizon_offset = int(session.horizon_id.lstrip("+"))
            except (ValueError, AttributeError):
                session.state = SessionOutcomeState.FAILED
                session.failure_reason = "invalid_horizon_id"
                self._repo.save_session_outcome(session)
                updated += 1
                self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                continue

            try:
                session_date = self._calendar.resolve_session_date(
                    outcome.detection_timestamp, horizon_offset, market_norm
                )
            except CalendarExpiredError:
                session.state = SessionOutcomeState.FAILED
                session.failure_reason = "calendar_expired"
                self._repo.save_session_outcome(session)
                updated += 1
                self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                continue
            except ValueError:
                # Rynek nieobsługiwany — nie powinno wystąpić (walidowane wyżej),
                # ale defensywnie obsługujemy
                session.state = SessionOutcomeState.SKIPPED
                session.skip_reason = "unknown_market"
                self._repo.save_session_outcome(session)
                updated += 1
                self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                continue

            # Sprawdź, czy horyzont już upłynął
            if session_date > datetime.now(timezone.utc):
                continue  # jeszcze nie nadszedł

            # Pobranie danych rynkowych
            ticker = getattr(outcome, "ticker", "")
            try:
                history: list[MarketData] = self._fetcher.fetch_stock_data(ticker)
            except InvalidSymbolError:
                session.state = SessionOutcomeState.SKIPPED
                session.skip_reason = "instrument_delisted"
                self._repo.save_session_outcome(session)
                updated += 1
                self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                # Oznacz pozostałe PENDING sesje dla tego samego tickera
                for other in pending_sessions:
                    if (
                        other.session_outcome_id != session.session_outcome_id
                        and other.event_outcome_id == session.event_outcome_id
                        and other.state == SessionOutcomeState.PENDING
                    ):
                        other.state = SessionOutcomeState.SKIPPED
                        other.skip_reason = "instrument_delisted"
                        self._repo.save_session_outcome(other)
                        updated += 1
                continue
            except RateLimitExceededError:
                session.attempt_count = getattr(session, "attempt_count", 0) + 1
                if session.attempt_count >= self._config.max_retry_attempts:
                    session.state = SessionOutcomeState.FAILED
                    session.failure_reason = "rate_limit_exceeded"
                    self._repo.save_session_outcome(session)
                    updated += 1
                    self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                else:
                    self._repo.save_session_outcome(session)
                continue
            except YahooFinanceError:
                session.attempt_count = getattr(session, "attempt_count", 0) + 1
                if session.attempt_count >= self._config.max_retry_attempts:
                    session.state = SessionOutcomeState.FAILED
                    session.failure_reason = "yahoo_api_error"
                    self._repo.save_session_outcome(session)
                    updated += 1
                    self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                else:
                    self._repo.save_session_outcome(session)
                continue

            # Odfiltruj dane dla daty sesji
            market_data = self._find_market_data(history, session_date)
            if market_data is None:
                session.attempt_count = getattr(session, "attempt_count", 0) + 1
                if session.attempt_count >= self._config.max_retry_attempts:
                    session.state = SessionOutcomeState.FAILED
                    session.failure_reason = "no_data_for_session"
                    self._repo.save_session_outcome(session)
                    updated += 1
                    self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)
                else:
                    self._repo.save_session_outcome(session)
                continue

            # Oblicz metryki
            self._compute_metrics(session, outcome, market_data)
            self._repo.save_session_outcome(session)
            updated += 1
            self._update_event_outcome_state(outcome, EventOutcomeState, SessionOutcomeState)

        return updated

    def get_event_outcome(self, event_id: str):
        """Pobiera EventOutcome dla danego MarketEvent."""
        return self._repo.get_event_outcome_by_market_event_id(event_id)

    def get_event_outcomes_by_state(self, state) -> list:
        """Pobiera wszystkie EventOutcome w danym stanie."""
        try:
            return self._repo.get_event_outcomes_by_state(state)
        except AttributeError:
            return []

    # ------------------------------------------------------------------
    # Metody prywatne
    # ------------------------------------------------------------------

    @staticmethod
    def _create_event_outcome(market_event, EventOutcome, EventOutcomeState):
        """Tworzy EventOutcome z wartościami bazowymi z MarketEvent."""
        base_price = None
        if (
            market_event.price_data is not None
            and getattr(market_event.price_data, "close", None) is not None
        ):
            base_price = market_event.price_data.close

        base_volume = None
        if (
            market_event.volume_data is not None
            and getattr(market_event.volume_data, "current_volume", None) is not None
        ):
            base_volume = market_event.volume_data.current_volume

        market_val = getattr(market_event, "market", "") or ""
        # Kopiowane bez zgadywania — puste zostaje puste

        return EventOutcome(
            event_outcome_id=str(uuid.uuid4()),
            market_event_id=market_event.event_id,
            state=EventOutcomeState.PENDING,
            ticker=market_event.ticker,
            market=market_val,
            detection_timestamp=market_event.timestamp_utc,
            base_price=base_price,
            base_volume=base_volume,
            event_family=getattr(market_event.event_family, "value", str(market_event.event_family)),
            event_type=market_event.event_type,
            quality_level=getattr(market_event.quality_level, "value", str(market_event.quality_level)),
            expected_horizons=4,  # +1, +2, +3, +5
            horizons_calculated=0,
            horizons_failed=0,
            horizons_skipped=0,
            missing_horizons=["+1", "+2", "+3", "+5"],
            created_at=datetime.now(timezone.utc),
            rule_version="1.0.0",
            failure_reason=None,
            invalid_reason=None,
        )

    @staticmethod
    def _create_session_outcome(outcome, horizon_id, SessionOutcome, SessionOutcomeState):
        """Tworzy SessionOutcome w stanie PENDING."""
        return SessionOutcome(
            session_outcome_id=str(uuid.uuid4()),
            event_outcome_id=outcome.event_outcome_id,
            horizon_id=horizon_id,
            state=SessionOutcomeState.PENDING,
            attempt_count=0,
            close_price=None,
            price_change_pct=None,
            price_change_abs=None,
            volume=None,
            volume_change_pct=None,
            high_price=None,
            low_price=None,
            failure_reason=None,
            skip_reason=None,
            computed_at=None,
            rule_version=None,
            data_source=None,
        )

    @staticmethod
    def _find_market_data(history, session_date):
        """Odfiltrowuje MarketData dla konkretnej daty sesji."""
        session_day = session_date.date()
        for md in history:
            md_day = getattr(md, "timestamp", None)
            if md_day is not None:
                if isinstance(md_day, datetime):
                    md_day = md_day.date()
                if md_day == session_day:
                    return md
        return None

    def _compute_metrics(self, session, outcome, market_data):
        """Oblicza metryki i ustawia stan CALCULATED."""
        from data.models.session_outcome import SessionOutcomeState

        session.close_price = market_data.close
        session.high_price = market_data.high
        session.low_price = market_data.low
        session.volume = getattr(market_data, "volume", None)

        base_price = getattr(outcome, "base_price", None)
        if base_price is not None and base_price != 0:
            session.price_change_pct = (market_data.close - base_price) / base_price * 100.0
            session.price_change_abs = market_data.close - base_price
        else:
            session.price_change_pct = None
            session.price_change_abs = None

        base_volume = getattr(outcome, "base_volume", None)
        market_volume = getattr(market_data, "volume", None)
        if base_volume is not None and base_volume > 0 and market_volume is not None:
            session.volume_change_pct = (market_volume - base_volume) / base_volume * 100.0
        else:
            session.volume_change_pct = None

        session.computed_at = datetime.now(timezone.utc)
        session.rule_version = self._config.rule_version
        session.data_source = "YahooFinance"
        session.state = SessionOutcomeState.CALCULATED

    def _update_event_outcome_state(self, outcome, EventOutcomeState, SessionOutcomeState):
        """Aktualizuje stan EventOutcome na podstawie stanów jego SessionOutcome."""
        try:
            sessions = self._repo.get_session_outcomes_for_event(outcome.event_outcome_id)
        except AttributeError:
            return

        total = len(sessions)
        calculated = sum(1 for s in sessions if s.state == SessionOutcomeState.CALCULATED)
        failed = sum(1 for s in sessions if s.state == SessionOutcomeState.FAILED)
        skipped = sum(1 for s in sessions if s.state == SessionOutcomeState.SKIPPED)
        pending = total - calculated - failed - skipped

        outcome.horizons_calculated = calculated
        outcome.horizons_failed = failed
        outcome.horizons_skipped = skipped
        outcome.missing_horizons = [
            s.horizon_id for s in sessions if s.state == SessionOutcomeState.PENDING
        ]

        if calculated == 0 and failed == 0 and skipped == 0:
            outcome.state = EventOutcomeState.PENDING
        elif calculated + failed + skipped == total and pending == 0:
            if failed > 0:
                outcome.state = EventOutcomeState.FAILED
            elif calculated == 0:
                outcome.state = EventOutcomeState.INVALID
            else:
                outcome.state = EventOutcomeState.COMPLETE
        else:
            outcome.state = EventOutcomeState.PARTIAL

        self._repo.save_event_outcome(outcome)