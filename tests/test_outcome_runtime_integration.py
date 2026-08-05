"""Testy integracyjne OutcomeComputer z RuntimeService.

Używają rzeczywistych:
  - RuntimeService
  - OutcomeComputer
  - TradingCalendar
  - EventOutcome, SessionOutcome
  - SQLiteHistoryRepository

YahooFetcher jest mockowany jako granica zewnętrzna.
"""
import tempfile
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pytest

from application.runtime import RuntimeService
from application.sqlite_history_repository import SQLiteHistoryRepository
from application.opportunity_deduplicator import OpportunityDeduplicator
from engines.outcome.engine import OutcomeComputer
from engines.outcome.calendar import TradingCalendar
from config.outcome import OutcomeConfig
from engines.hunter.engine import HunterEngine
from data.models.hunter_result import HunterResult, HunterScanResult
from data.models.market_event import MarketEvent
from data.models.event_enums import (
    EventFamily, EventOwner, InstrumentType, PriorityLevel,
)
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData
from data.models.market_data import MarketData
from data.models.event_outcome import EventOutcome, EventOutcomeState
from data.models.session_outcome import SessionOutcome, SessionOutcomeState


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

HUNTER_CONFIG_WIDE = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.0,
    "max_risk_score": 1.0,
    "min_confidence": 0.0,
    "max_results": 100,
    "priority_thresholds": [0.9, 0.7, 0.5],
}


def make_market_event(ticker="TST", market="GPW", event_type="PRICE_SURGE",
                       price=100.0, volume=10000.0, ts=None):
    """Tworzy prawdziwy MarketEvent."""
    if ts is None:
        ts = datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc)
    event = MarketEvent.create_new(
        event_type=event_type,
        ticker=ticker,
        market=market,
        instrument_type=InstrumentType.STOCK_GPW,
    )
    # Jawnie ustaw timestamp wykrycia (create_new ustawia datetime.now())
    event.timestamp_utc = ts
    event.set_detection(
        event_family=EventFamily.PRICE,
        event_category="price",
        event_type=event_type,
        priority_raw=PriorityLevel.HIGH,
        confidence_level=0.85,
        detection_source="test",
        event_owner=EventOwner.TechnicalEngine,
    )
    event.quality_level = PriorityLevel.HIGH
    event.price_data = PriceData(
        open=price - 1.0, high=price + 1.0, low=price - 2.0,
        close=price, prev_close=price - 2.0,
        change_pct=2.0, change_abs=2.0,
    )
    event.volume_data = VolumeData(
        current_volume=volume, avg_volume=8000.0,
        volume_ratio=1.25, direction="up",
    )
    return event


def make_hunter_scan_result(*instrument_ids):
    """Buduje realny HunterScanResult."""
    opportunities = [
        HunterResult(
            instrument_id=sid,
            hunter_score=0.8,
            priority=1,
            ranking_score=0.8,
            risk_score=0.2,
            risk_level="low",
            confidence=0.9,
            reasons=[],
            warnings=[],
            timestamp=datetime.now(timezone.utc),
        )
        for sid in instrument_ids
    ]
    return HunterScanResult(
        opportunities=opportunities,
        analyzed=len(instrument_ids),
        rejected=0,
        qualified=len(opportunities),
        timestamp=datetime.now(timezone.utc),
    )


# ------------------------------------------------------------------
# Testy
# ------------------------------------------------------------------

class TestOutcomeRuntimeIntegration:
    """Testy integracyjne OutcomeComputer z RuntimeService."""

    @pytest.fixture
    def tmp_db(self):
        """Tworzy tymczasową bazę SQLite."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except (OSError, PermissionError):
            pass

    @pytest.fixture
    def components(self, tmp_db):
        """Buduje prawdziwe komponenty do testów integracyjnych."""
        repo = SQLiteHistoryRepository(db_path=tmp_db)
        yahoo_fetcher = Mock()
        calendar = TradingCalendar()
        config = OutcomeConfig()
        outcome_computer = OutcomeComputer(
            repository=repo,
            yahoo_fetcher=yahoo_fetcher,
            calendar=calendar,
            config=config,
        )

        hunter = HunterEngine(HUNTER_CONFIG_WIDE)
        # Minimal master engine mock — nie używamy go w tych testach
        master_engine = Mock()
        master_engine.run_analysis = Mock(return_value="fake_result")

        dedup = OpportunityDeduplicator(deduplication_window_seconds=3600)
        dedup.should_process = Mock(return_value=True)

        runtime = RuntimeService(
            hunter_engine=hunter,
            master_engine=master_engine,
            history_repository=repo,
            deduplicator=dedup,
            outcome_computer=outcome_computer,
        )

        return {
            "runtime": runtime,
            "repo": repo,
            "yahoo_fetcher": yahoo_fetcher,
            "outcome_computer": outcome_computer,
            "hunter": hunter,
            "master_engine": master_engine,
            "dedup": dedup,
        }

    def _store_market_event(self, repo, cycle_id, market_event):
        """Zapisuje MarketEvent w repozytorium bezpośrednio."""
        events_data = [market_event.to_dict()]
        repo.save_market_events(cycle_id, events_data)

    def _make_market_data(self, days_offset=1, base_price=100.0):
        """Tworzy dane rynkowe dla sesji horyzontowej."""
        return MarketData(
            open=base_price + 1.0,
            high=base_price + 5.0,
            low=base_price - 1.0,
            close=base_price + 3.0,
            volume=12000.0,
            timestamp=datetime(2026, 7, 20, tzinfo=timezone.utc) + timedelta(days=days_offset),
        )

    # ------------------------------------------------------------------
    # Test 1: Inicjalizacja Outcome po zapisie MarketEvent
    # ------------------------------------------------------------------

    def test_initialize_new_events_after_market_event_persistence(self, components):
        """Runtime zapisuje MarketEvent, initialize_new_events() tworzy
        EventOutcome + SessionOutcome."""
        comp = components
        me = make_market_event(ticker="INTL1.WA", market="GPW")

        # Zapisujemy MarketEvent przez repozytorium (symuluje Runtime)
        self._store_market_event(comp["repo"], "cycle-1", me)

        # Wywołujemy initialize_new_events
        outcomes = comp["outcome_computer"].initialize_new_events()

        assert len(outcomes) == 1
        outcome = outcomes[0]
        assert outcome.market_event_id == me.event_id
        assert outcome.state == EventOutcomeState.PENDING
        assert outcome.ticker == "INTL1.WA"

        # Powinny powstać 4 SessionOutcome
        sessions = comp["repo"].get_session_outcomes_for_event(outcome.event_outcome_id)
        assert len(sessions) == 4
        horizon_ids = {s.horizon_id for s in sessions}
        assert horizon_ids == {"+1", "+2", "+3", "+5"}
        for s in sessions:
            assert s.state == SessionOutcomeState.PENDING

    # ------------------------------------------------------------------
    # Test 2: Obliczenie pending horizons
    # ------------------------------------------------------------------

    def test_compute_pending_horizons_updates_sessions(self, components):
        """Pending horizon jest obliczany, metryki zapisane,
        stany SessionOutcome i EventOutcome zaktualizowane."""
        comp = components
        me = make_market_event(
            ticker="INTL2.WA", market="GPW",
            ts=datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc),
        )
        self._store_market_event(comp["repo"], "cycle-2", me)

        # Inicjalizacja
        outcomes = comp["outcome_computer"].initialize_new_events()
        outcome = outcomes[0]

        # Mock danych rynkowych dla sesji 2026-07-21 (wtorek, +1)
        md = self._make_market_data(days_offset=1, base_price=100.0)
        comp["yahoo_fetcher"].fetch_stock_data.return_value = [md]

        # Obliczenie
        updated = comp["outcome_computer"].compute_pending_horizons()
        assert updated >= 1

        # Sesja +1 powinna być CALCULATED
        sessions = comp["repo"].get_session_outcomes_for_event(outcome.event_outcome_id)
        calc = [s for s in sessions if s.horizon_id == "+1" and s.state == SessionOutcomeState.CALCULATED]
        assert len(calc) == 1
        s = calc[0]
        assert s.close_price == 103.0
        assert s.price_change_pct is not None
        assert s.data_source == "YahooFinance"

        # EventOutcome powinien być PARTIAL (+1 wyliczone, +2,+3,+5 PENDING)
        updated_outcome = comp["repo"].get_event_outcome_by_id(outcome.event_outcome_id)
        assert updated_outcome.state == EventOutcomeState.PARTIAL
        assert updated_outcome.horizons_calculated >= 1

    # ------------------------------------------------------------------
    # Test 3: Outcome bez nowych MarketEvent
    # ------------------------------------------------------------------

    def test_no_new_market_events_does_not_block_pending_horizons(self, components):
        """Brak nowych MarketEvent nie blokuje compute_pending_horizons."""
        comp = components
        me = make_market_event(
            ticker="INTL3.WA", market="GPW",
            ts=datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc),
        )
        self._store_market_event(comp["repo"], "cycle-3", me)

        # Inicjalizacja i pierwsze obliczenie
        comp["outcome_computer"].initialize_new_events()
        md = self._make_market_data(days_offset=1)
        comp["yahoo_fetcher"].fetch_stock_data.return_value = [md]
        comp["outcome_computer"].compute_pending_horizons()

        # Drugie wywołanie: brak nowych MarketEvent, ale oblicza horyzonty
        initialize_result = comp["outcome_computer"].initialize_new_events()
        assert len(initialize_result) == 0  # brak nowych

        compute_result = comp["outcome_computer"].compute_pending_horizons()
        # +1 już CALCULATED, +2 może być już osiągalne albo jeszcze nie
        assert compute_result >= 0  # nie rzuca wyjątku

    # ------------------------------------------------------------------
    # Test 4: Błąd inicjalizacji nie zatrzymuje cyklu
    # ------------------------------------------------------------------

    def test_initialize_error_does_not_stop_cycle(self, components):
        """Błąd w initialize_new_events nie zatrzymuje Runtime."""
        comp = components

        # Sprawiamy, że repo nie wspiera wymaganej metody
        comp["outcome_computer"]._repo = Mock(spec=[])
        # Metoda nie istnieje → AttributeError → obsłużone przez OutcomeComputer

        report = comp["runtime"].run_cycle({})
        assert report is not None
        assert report.error_count >= 0  # cykl nie został przerwany

    # ------------------------------------------------------------------
    # Test 5: Błąd compute_pending_horizons nie zatrzymuje cyklu
    # ------------------------------------------------------------------

    def test_compute_error_does_not_stop_cycle(self, components):
        """Błąd w compute_pending_horizons nie zatrzymuje Runtime."""
        comp = components
        me = make_market_event(ticker="INTL4.WA", market="GPW")
        self._store_market_event(comp["repo"], "cycle-4", me)

        # Normalna inicjalizacja
        comp["outcome_computer"].initialize_new_events()

        # Psujemy repozytorium dla compute
        comp["outcome_computer"]._repo = Mock(spec=[])

        report = comp["runtime"].run_cycle({})
        assert report is not None
        assert report.error_count >= 0  # cykl nie został przerwany

    # ------------------------------------------------------------------
    # Test 6: Brak podwójnego wywołania (idempotentność)
    # ------------------------------------------------------------------

    def test_idempotent_initialize_no_duplicate_outcomes(self, components):
        """Drugie wywołanie initialize_new_events() nie tworzy duplikatów."""
        comp = components
        me = make_market_event(ticker="INTL5.WA", market="GPW")
        self._store_market_event(comp["repo"], "cycle-5", me)

        first = comp["outcome_computer"].initialize_new_events()
        assert len(first) == 1

        second = comp["outcome_computer"].initialize_new_events()
        assert len(second) == 0

        # Tylko jeden EventOutcome w bazie
        all_eo_ids = comp["repo"].get_all_event_outcome_ids()
        assert len(all_eo_ids) == 1
        assert me.event_id in all_eo_ids

    # ------------------------------------------------------------------
    # Test 7: Wiele tickerów — izolacja błędów
    # ------------------------------------------------------------------

    def test_multiple_tickers_independent_outcomes(self, components):
        """Wiele MarketEvent może zainicjalizować wiele EventOutcome niezależnie."""
        comp = components

        me1 = make_market_event(ticker="INTL6.WA", market="GPW",
                                 price=100.0, volume=10000.0)
        me2 = make_market_event(ticker="INTL7.WA", market="GPW",
                                 price=50.0, volume=5000.0)

        self._store_market_event(comp["repo"], "cycle-6", me1)
        self._store_market_event(comp["repo"], "cycle-6", me2)

        outcomes = comp["outcome_computer"].initialize_new_events()
        assert len(outcomes) == 2

        tickers = {o.ticker for o in outcomes}
        assert tickers == {"INTL6.WA", "INTL7.WA"}

        # Każdy ma 4 sesje
        for o in outcomes:
            sessions = comp["repo"].get_session_outcomes_for_event(o.event_outcome_id)
            assert len(sessions) == 4

        # Obliczamy dla obu (mock danych)
        md = self._make_market_data(days_offset=1)
        comp["yahoo_fetcher"].fetch_stock_data.return_value = [md]
        updated = comp["outcome_computer"].compute_pending_horizons()
        assert updated >= 2  # +1 dla każdego

    # ------------------------------------------------------------------
    # Test: EventOutcome zapis w bazie
    # ------------------------------------------------------------------

    def test_event_outcome_persisted_in_sqlite(self, tmp_db):
        """EventOutcome jest trwale zapisywany w SQLite."""
        repo = SQLiteHistoryRepository(db_path=tmp_db)
        me = make_market_event(ticker="INTL8.WA", market="GPW")
        repo.save_market_events("cycle-p", [me.to_dict()])

        yahoo_fetcher = Mock()
        calendar = TradingCalendar()
        config = OutcomeConfig()
        oc = OutcomeComputer(
            repository=repo,
            yahoo_fetcher=yahoo_fetcher,
            calendar=calendar,
            config=config,
        )

        outcomes = oc.initialize_new_events()
        assert len(outcomes) == 1

        # Ponowna inicjalizacja tego samego repozytorium (symulacja restartu)
        repo2 = SQLiteHistoryRepository(db_path=tmp_db)
        existing_ids = repo2.get_all_event_outcome_ids()
        assert len(existing_ids) == 1
        assert me.event_id in existing_ids

        # Odczyt EventOutcome
        eo = repo2.get_event_outcome_by_market_event_id(me.event_id)
        assert eo is not None
        assert eo.ticker == "INTL8.WA"
        assert eo.state == EventOutcomeState.PENDING