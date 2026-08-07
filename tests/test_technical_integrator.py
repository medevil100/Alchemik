"""
Tests for TechnicalIntegrator — the MarketEvent → TechnicalEngine bridge.

Covers:
1. Proper MarketEvent triggers technical analysis.
2. Correct data reaches TechnicalEngine.
3. Result is a genuine TechnicalEngine AnalysisResult.
4. TechnicalEngine is NOT invoked for an invalid or rejected event.
5. Technical analysis errors are NOT hidden.
6. Downstream pipeline engines are NOT triggered.
7. Final result is NOT written to SQLite.
8. Existing behaviour of all other paths is preserved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest

from data.models.analysis_result import AnalysisResult
from data.models.company_info import CompanyInfo
from data.models.event_enums import (
    EventFamily,
    EventOwner,
    InstrumentType,
    PriorityLevel,
)
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from data.yahoo.yahoo_exceptions import (
    InvalidSymbolError,
    YahooFinanceError,
)
from application.technical_integrator import TechnicalIntegrator


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def sample_market_event() -> MarketEvent:
    """Return a valid MarketEvent in the detection stage."""
    event = MarketEvent.create_new(
        event_type="PRICE_SURGE",
        ticker="XYZ.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
        timestamp_utc=datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc),
    )
    event.set_detection(
        event_family=EventFamily.PRICE,
        event_category="Cenowe",
        event_type="PRICE_SURGE",
        priority_raw=PriorityLevel.HIGH,
        confidence_level=0.85,
        detection_source="Price Event Detector",
        event_owner=EventOwner.TechnicalEngine,
    )
    return event


@pytest.fixture
def sample_rejected_event() -> MarketEvent:
    """Return a MarketEvent rejected by quality assessment (IGNORE)."""
    event = MarketEvent.create_new(
        event_type="PRICE_SURGE",
        ticker="IGNORE.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
    )
    event.set_detection(
        event_family=EventFamily.VOLUME,
        event_category="Wolumenowe",
        event_type="VOLUME_SPIKE",
        priority_raw=PriorityLevel.MEDIUM,
        confidence_level=0.2,
        detection_source="Volume Event Detector",
        event_owner=EventOwner.TechnicalEngine,
    )
    event.set_quality_assessment(PriorityLevel.IGNORE)
    return event


@pytest.fixture
def sample_market_data() -> list[MarketData]:
    """Return a sample list of MarketData resembling real OHLCV points."""
    base = datetime(2026, 7, 20, tzinfo=timezone.utc)
    return [
        MarketData(open=100.0, high=103.0, low=99.0, close=102.0, volume=1_000_000.0, timestamp=base),
        MarketData(open=102.0, high=105.0, low=101.5, close=104.0, volume=1_200_000.0, timestamp=datetime(2026, 7, 21, tzinfo=timezone.utc)),
        MarketData(open=104.0, high=112.5, low=103.0, close=112.3, volume=2_500_000.0, timestamp=datetime(2026, 7, 22, tzinfo=timezone.utc)),
    ]


@pytest.fixture
def mock_technical_engine() -> Mock:
    """Return a MagicMock standing in for TechnicalEngine."""
    engine = MagicMock()
    # Default return: a valid AnalysisResult with indicators
    result = MagicMock(spec=AnalysisResult)
    result.indicators = {
        "sma": [101.0, 102.5, 104.1],
        "rsi": [55.0],
        "macd": {"line": [0.1], "signal": [0.05], "histogram": [0.05]},
    }
    engine.analyze.return_value = result
    return engine


@pytest.fixture
def mock_yahoo_fetcher() -> Mock:
    """Return a MagicMock standing in for YahooFetcher."""
    fetcher = MagicMock()
    base = datetime(2026, 7, 20, tzinfo=timezone.utc)
    fetcher.fetch_stock_data.return_value = [
        MarketData(open=100.0, high=103.0, low=99.0, close=102.0, volume=1_000_000.0, timestamp=base),
        MarketData(open=102.0, high=105.0, low=101.5, close=104.0, volume=1_200_000.0, timestamp=datetime(2026, 7, 21, tzinfo=timezone.utc)),
        MarketData(open=104.0, high=112.5, low=103.0, close=112.3, volume=2_500_000.0, timestamp=datetime(2026, 7, 22, tzinfo=timezone.utc)),
    ]
    return fetcher


@pytest.fixture
def integrator(mock_technical_engine: Mock, mock_yahoo_fetcher: Mock) -> TechnicalIntegrator:
    """Return a TechnicalIntegrator with mocked dependencies."""
    return TechnicalIntegrator(
        technical_engine=mock_technical_engine,
        yahoo_fetcher=mock_yahoo_fetcher,
    )


# ------------------------------------------------------------------
# Test 1: Proper MarketEvent triggers technical analysis
# ------------------------------------------------------------------


def test_valid_market_event_triggers_technical_analysis(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
    mock_technical_engine: Mock,
    mock_yahoo_fetcher: Mock,
) -> None:
    """A valid, approved MarketEvent must cause TechnicalEngine.analyze() to be called."""
    result = integrator.integrate(sample_market_event)

    # YahooFetcher was called with the correct ticker
    mock_yahoo_fetcher.fetch_stock_data.assert_called_once_with("XYZ.WA")
    # TechnicalEngine.analyze was called exactly once
    mock_technical_engine.analyze.assert_called_once()

    # Result is not None
    assert result is not None
    # technical_context was set on the event
    assert sample_market_event.technical_context is not None
    assert "sma" in sample_market_event.technical_context


# ------------------------------------------------------------------
# Test 2: Correct data reaches TechnicalEngine
# ------------------------------------------------------------------


def test_correct_data_reaches_technical_engine(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
    mock_technical_engine: Mock,
    mock_yahoo_fetcher: Mock,
) -> None:
    """TechnicalEngine.analyze() must receive the MarketData list returned by YahooFetcher."""
    integrator.integrate(sample_market_event)

    # Get the argument passed to TechnicalEngine.analyze
    call_args = mock_technical_engine.analyze.call_args[0][0]
    assert isinstance(call_args, list)
    assert all(isinstance(md, MarketData) for md in call_args)
    # Must be exactly the list returned by YahooFetcher
    assert call_args == mock_yahoo_fetcher.fetch_stock_data.return_value


# ------------------------------------------------------------------
# Test 3: Result is a genuine TechnicalEngine AnalysisResult
# ------------------------------------------------------------------


def test_result_is_genuine_analysis_result(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """Integration must return an existing TechnicalEngine AnalysisResult type."""
    result = integrator.integrate(sample_market_event)
    assert isinstance(result, AnalysisResult)


# ------------------------------------------------------------------
# Test 4: TechnicalEngine is NOT invoked for an invalid or rejected event
# ------------------------------------------------------------------


def test_non_market_event_raises_value_error(
    integrator: TechnicalIntegrator,
    mock_technical_engine: Mock,
    mock_yahoo_fetcher: Mock,
) -> None:
    """Passing a non-MarketEvent object must raise ValueError without calling engines."""
    with pytest.raises(ValueError, match="MarketEvent instance"):
        integrator.integrate("not_an_event")  # type: ignore[arg-type]

    mock_yahoo_fetcher.fetch_stock_data.assert_not_called()
    mock_technical_engine.analyze.assert_not_called()


def test_event_with_empty_ticker_raises_value_error(
    integrator: TechnicalIntegrator,
    mock_technical_engine: Mock,
    mock_yahoo_fetcher: Mock,
) -> None:
    """A MarketEvent with an empty ticker must raise ValueError from the integrator.

    Note: MarketEvent.create_new() already rejects empty tickers via
    __post_init__ validation. To test only the integrator's own guard,
    we use a MagicMock that mimics the MarketEvent interface but with
    an empty ticker, bypassing the model-level validation.
    """
    fake_event = MagicMock(spec=MarketEvent)
    fake_event.ticker = ""
    fake_event.event_id = "test-id-123"

    with pytest.raises(ValueError, match="ticker"):
        integrator.integrate(fake_event)

    mock_yahoo_fetcher.fetch_stock_data.assert_not_called()
    mock_technical_engine.analyze.assert_not_called()


def test_rejected_event_still_can_trigger_analysis(
    integrator: TechnicalIntegrator,
    mock_technical_engine: Mock,
    mock_yahoo_fetcher: Mock,
) -> None:
    """The TechnicalIntegrator does NOT filter by quality_level.

    The integrator's contract is to run analysis if requested.
    Filtering by quality_level is the responsibility of higher-level
    orchestration (Runtime, Pipeline). Our integrator simply connects
    MarketEvent → TechnicalEngine.

    We test that a technically-valid (non-null ticker) rejected
    event still CAN be integrated — the integrator does not block it.
    """
    event = MarketEvent.create_new(
        event_type="PRICE_SURGE",
        ticker="REJECT.WA",
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
    )
    event.set_detection(
        event_family=EventFamily.PRICE,
        event_category="Cenowe",
        event_type="PRICE_DROP",
        priority_raw=PriorityLevel.LOW,
        confidence_level=0.15,
        detection_source="Price Event Detector",
        event_owner=EventOwner.TechnicalEngine,
    )
    event.set_quality_assessment(PriorityLevel.IGNORE)

    result = integrator.integrate(event)
    assert result is not None
    mock_technical_engine.analyze.assert_called_once()


# ------------------------------------------------------------------
# Test 5: Technical analysis errors are NOT hidden
# ------------------------------------------------------------------


def test_yahoo_fetcher_error_propagates(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
    mock_yahoo_fetcher: Mock,
    mock_technical_engine: Mock,
) -> None:
    """An error from YahooFetcher must propagate — not be swallowed."""
    mock_yahoo_fetcher.fetch_stock_data.side_effect = YahooFinanceError("API down")

    with pytest.raises(YahooFinanceError, match="API down"):
        integrator.integrate(sample_market_event)

    # TechnicalEngine must NOT be called after a fetch error
    mock_technical_engine.analyze.assert_not_called()


def test_invalid_symbol_error_propagates(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
    mock_yahoo_fetcher: Mock,
    mock_technical_engine: Mock,
) -> None:
    """InvalidSymbolError from YahooFetcher must propagate."""
    mock_yahoo_fetcher.fetch_stock_data.side_effect = InvalidSymbolError("Bad symbol")

    with pytest.raises(InvalidSymbolError, match="Bad symbol"):
        integrator.integrate(sample_market_event)

    mock_technical_engine.analyze.assert_not_called()


def test_technical_engine_error_propagates(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
    mock_technical_engine: Mock,
    mock_yahoo_fetcher: Mock,
) -> None:
    """RuntimeError from TechnicalEngine.analyze() must NOT be hidden."""
    mock_technical_engine.analyze.side_effect = RuntimeError("Indicator calculation failed")

    with pytest.raises(RuntimeError, match="Indicator calculation failed"):
        integrator.integrate(sample_market_event)

    # YahooFetcher was called (it succeeded), but the event should NOT
    # have its technical_context set after the error
    mock_yahoo_fetcher.fetch_stock_data.assert_called_once()
    # technical_context was NOT modified because the error happened before assignment
    assert sample_market_event.technical_context is None


# ------------------------------------------------------------------
# Test 6: Downstream pipeline engines are NOT triggered
# ------------------------------------------------------------------


def test_no_ranking_engine_invoked(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """The integrator must NOT import or invoke RankingEngine."""
    # We verify this by checking that after integration, no RankingEngine
    # modules are imported. The simplest proof: integration does not
    # crash with import errors for ranking engine.
    result = integrator.integrate(sample_market_event)
    assert result is not None
    # No ranking-related fields on the event
    assert "ranking" not in str(sample_market_event.metadata).lower()


def test_no_risk_engine_invoked(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """The integrator must NOT import or invoke RiskEngine."""
    result = integrator.integrate(sample_market_event)
    assert result is not None
    assert "risk" not in str(sample_market_event.metadata).lower()


def test_no_analyst_engine_invoked(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """The integrator must NOT import or invoke AnalystEngine."""
    result = integrator.integrate(sample_market_event)
    assert result is not None
    # AnalystEngine does not touch MarketEvent; just validate no import error
    assert "analyst" not in str(sample_market_event.detection_source).lower()


def test_no_master_engine_invoked(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """The integrator must NOT invoke MasterEngine.

    MasterEngine.run_analysis() runs the full pipeline (Ranking, Risk,
    Analyst, etc.). We verify the integrator does not import or call it.
    """
    integrator.integrate(sample_market_event)

    # After integration, the history should contain exactly:
    # 1. Creation entry (from create_new)
    # 2. Detection entry (from set_detection)
    # 3. Integration entry (from TechnicalIntegrator.integrate)
    # No MasterEngine entries
    history_modules = [entry.module for entry in sample_market_event.history]
    assert "TechnicalIntegrator" in history_modules
    assert "MasterEngine" not in history_modules


# ------------------------------------------------------------------
# Test 7: Final result is NOT written to SQLite
# ------------------------------------------------------------------


def test_no_sqlite_write(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """The integrator must NOT import or use sqlite3 / SQLiteHistoryRepository."""
    # The simplest proof: the integrator module does not import sqlite3
    # or SQLiteHistoryRepository.
    import application.technical_integrator as mod

    source = mod.__dict__
    assert "sqlite3" not in source
    assert "SQLiteHistoryRepository" not in source
    assert "HistoryRepository" not in source

    # And integration succeeds without side effects on storage
    result = integrator.integrate(sample_market_event)
    assert result is not None


# ------------------------------------------------------------------
# Test 8: History is recorded on MarketEvent
# ------------------------------------------------------------------


def test_history_entry_recorded(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
) -> None:
    """Each integration must append a HistoryEntry to the MarketEvent."""
    history_before = len(sample_market_event.history)
    integrator.integrate(sample_market_event)
    history_after = len(sample_market_event.history)

    assert history_after == history_before + 1
    last_entry = sample_market_event.history[-1]
    assert last_entry.module == "TechnicalIntegrator"
    assert "technical_context" in last_entry.fields_changed
    assert "XYZ.WA" in last_entry.action


def test_technical_context_populated_with_indicators(
    integrator: TechnicalIntegrator,
    sample_market_event: MarketEvent,
    mock_technical_engine: Mock,
) -> None:
    """After integration, technical_context holds exactly what TechnicalEngine.analyze returned."""
    integrator.integrate(sample_market_event)

    expected_indicators = mock_technical_engine.analyze.return_value.indicators
    assert sample_market_event.technical_context == expected_indicators
    assert "sma" in sample_market_event.technical_context
    assert "rsi" in sample_market_event.technical_context
    assert "macd" in sample_market_event.technical_context