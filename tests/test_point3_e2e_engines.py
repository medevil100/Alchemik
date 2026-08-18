"""
Point 3/7 — pełny wewnętrzny przepływ przez silniki ALCHEMIKA.

Scenariusze obowiązkowe Punktu 3 (po wąskiej korekcie obsługi krótkiej
historii). Przepływ testowany na prawdziwych modułach wewnętrznych:

    MarketScanner → RuntimeService → Observation/Baseline → SQLite
    → pierwszy Hunter (pass-through) → MasterEngine
    → TechnicalEngine → detektory → Composer → Quality → DecisionEngine
    → News → Ranking → Risk → końcowy Hunter → AnalystEngine
    → finalny wynik domenowy.

Test double dozwolony wyłącznie na zewnętrznej granicy Yahoo
(``FakeYahooSession``). Żaden wewnętrzny komponent nie jest mockowany,
z wyjątkiem jednego jawnego stuba ``TechnicalEngine.analyze`` w teście
``test_unrelated_valueerror_not_swallowed``, który zastępuje zewnętrzną
granicę obliczeń tylko po to, by udowodnić, że niezwiązany z długością
historii ``ValueError`` nie jest połykany przez ``MasterEngine``.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from application import entrypoint
from data.models import MarketData
from engines.technical import TechnicalEngine
from engines.technical.errors import InsufficientDataError
from engines.technical.indicators.atr import calculate_atr
from tests.test_point2_e2e_flow import FakeYahooSession, make_quote, ts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REALISTIC = 60  # realistyczna historia krótsza niż 52 tygodnie (260 dni)


def _rows(n: int, offset_days: int = 0) -> list:
    """Return *n* strictly increasing, valid OHLCV rows (Yahoo chart shape)."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=offset_days)
    return [
        (
            ts(base + timedelta(days=d)),
            100.0 + d * 0.1,
            101.0 + d * 0.1,
            99.5 + d * 0.1,
            100.5 + d * 0.1,
            500_000,
        )
        for d in range(n)
    ]


def _md(n: int, offset_days: int = 0) -> list:
    """Return *n* strongly increasing MarketData candles."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=offset_days)
    return [
        MarketData(
            open=100.0 + d * 0.1,
            high=101.0 + d * 0.1,
            low=99.5 + d * 0.1,
            close=100.5 + d * 0.1,
            volume=500_000.0,
            timestamp=base + timedelta(days=d),
        )
        for d in range(n)
    ]


def _build(tmp_path: Path, session):
    return entrypoint.build_runtime_service(
        persist_path=Path(tmp_path) / "e2e.db",
        yahoo_session=session,
    )


HUNTER_CONFIG = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.5,
    "max_risk_score": 0.7,
    "min_confidence": 0.6,
    "max_results": 10,
    "priority_thresholds": [0.9, 0.7, 0.5],
}


def _make_master(technical_engine=None):
    from engines.master.engine import MasterEngine
    from engines.ai import DecisionEngine
    from engines.ranking import RankingEngine
    from engines.risk import RiskEngine
    from engines.hunter import HunterEngine
    from engines.analyst import AnalystEngine
    from engines.news import NewsPipeline
    from engines.news.filter import NewsFilterConfig

    return MasterEngine(
        technical_engine=technical_engine if technical_engine is not None else TechnicalEngine(),
        news_engine=NewsPipeline(
            NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        ),
        ai_engine=DecisionEngine(),
        ranking_engine=RankingEngine(),
        risk_engine=RiskEngine(),
        hunter_engine=HunterEngine(HUNTER_CONFIG),
        analyst_engine=AnalystEngine(),
    )


# ---------------------------------------------------------------------------
# 4.1/4.2 — rozróżnienie krótkiej historii od błędu
# ---------------------------------------------------------------------------

class TestPoint3ShortHistoryContract:
    def test_very_short_history_keeps_observation_no_fake_result(self, tmp_path):
        """Bardzo krótka historia nie tworzy pozornie poprawnej analizy.

        Observation pozostaje zapisana (persystencja przed TechnicalEngine),
        ale instrument nie otrzymuje FinalAnalysisResult udającego pełną
        analizę techniczną — zamiast tego zachowany jest jawny błąd.
        """
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(1)},
        )
        rt = _build(tmp_path, session)
        report = rt.run_cycle()

        assert report.candidates_count == 1
        assert report.success_count == 0
        assert report.results == []
        assert any("data points" in e.message for e in report.errors)

        # Observation zostaje zapisana mimo braku gotowości Technical Engine.
        assert rt.history_repository.load_observation("AAA.WA") is not None

    def test_realistic_sub_52w_history_passes_full_flow(self, tmp_path):
        """Realistyczna historia krótsza niż 52 tygodnie, ale wystarczająca
        dla wszystkich używanych wskaźników, przechodzi przez pełny przepływ."""
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC)},
        )
        report = _build(tmp_path, session).run_cycle()

        assert report.success_count == 1, [e.message for e in report.errors]
        assert report.results[0].symbol == "AAA.WA"

    def test_minimal_indicator_history_is_34_candles(self):
        """Minimalne wymaganie danych wynika z MACD: EMA(26) + signal EMA(9)
        → 26 + 9 - 1 = 34 świece. Żaden nowy próg biznesowy nie jest tworzony."""
        te = TechnicalEngine()
        with pytest.raises(InsufficientDataError):
            te.analyze(_md(33))

        result = te.analyze(_md(34))
        assert result.indicators != {}

    def test_indicator_distinguishes_insufficient_history(self):
        """Dedykowany wyjątek odróżnia krótką historię od prawdziwego błędu."""
        # Niewystarczająca historia → InsufficientDataError (podklasa ValueError)
        with pytest.raises(InsufficientDataError):
            calculate_atr(_md(3), window=14)

        # Błędna konfiguracja okna → zwykły ValueError, NIE InsufficientDataError
        with pytest.raises(ValueError) as exc:
            calculate_atr(_md(REALISTIC), window=0)
        assert not isinstance(exc.value, InsufficientDataError)

    def test_unrelated_valueerror_not_swallowed(self):
        """Niezwiązany z długością historii ValueError propaguje dalej.

        Jedyny jawny stub tego testu zastępuje ``TechnicalEngine.analyze``,
        by udowodnić, że MasterEngine nie zamienia dowolnego ValueError na
        pusty, pozornie poprawny wynik.
        """
        class _BrokenTechnicalEngine:
            def analyze(self, data):
                raise ValueError("boom not related to history")

        master = _make_master(technical_engine=_BrokenTechnicalEngine())
        with pytest.raises(ValueError, match="boom not related to history"):
            master.run_analysis("AAA.WA", ohlcv_data=_md(REALISTIC))


# ---------------------------------------------------------------------------
# 1/3/8/11/15 — jeden symbol przechodzi przez wszystkie prawdziwe silniki
# ---------------------------------------------------------------------------

class TestPoint3SingleSymbolFullEngines:
    def test_single_symbol_runs_all_real_engines(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC)},
        )
        rt = _build(tmp_path, session)
        report = rt.run_cycle()

        assert report.candidates_count == 1
        assert report.success_count == 1, [e.message for e in report.errors]
        assert report.error_count == 0
        assert len(report.results) == 1

        result = report.results[0]
        assert result.symbol == "AAA.WA"
        assert 0.0 <= result.final_rating <= 1.0
        assert isinstance(result.recommendation, str)
        assert result.generated_at is not None

        # Cykl i artefakty domenowe zostały zapisane.
        assert rt.history_repository.count() >= 1
        assert rt.history_repository.load_observation("AAA.WA") is not None

    def test_final_result_carries_instrument_symbol(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _rows(REALISTIC),
                "BBB.WA": _rows(REALISTIC, offset_days=100),
            },
        )
        report = _build(tmp_path, session).run_cycle()
        symbols = {r.symbol for r in report.results}
        assert symbols == {"AAA.WA", "BBB.WA"}

    def test_decision_engine_reached_but_ai_is_placeholder(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC)},
        )
        report = _build(tmp_path, session).run_cycle()
        result = report.results[0]
        # DecisionEngine osiągany, ale AI pozostaje placeholderem.
        assert result.confidence_level == 0.0

    def test_final_hunter_contract_uses_correct_fields(self):
        from engines.hunter.engine import HunterEngine

        hunter = HunterEngine(HUNTER_CONFIG)
        scan = hunter.scan([
            {
                "instrument_id": "AAA.WA",
                "ranking_score": 0.8,
                "risk_score": 0.2,
                "confidence": 0.9,
            }
        ])
        assert scan.qualified >= 1
        opp = scan.opportunities[0]
        assert opp.instrument_id == "AAA.WA"
        assert isinstance(opp.ranking_score, float)
        assert isinstance(opp.risk_score, float)
        assert isinstance(opp.confidence, float)


# ---------------------------------------------------------------------------
# 7/8 — izolacja błędów i niezależność instrumentów
# ---------------------------------------------------------------------------

class TestPoint3MultiSymbolIsolation:
    def test_two_symbols_processed_independently(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _rows(REALISTIC),
                "BBB.WA": _rows(REALISTIC, offset_days=100),
            },
        )
        report = _build(tmp_path, session).run_cycle()
        assert report.success_count == 2
        assert {r.symbol for r in report.results} == {"AAA.WA", "BBB.WA"}

    def test_one_technical_error_does_not_remove_other_result(self, tmp_path):
        """Błąd TechnicalEngine (zbyt krótka historia) jednego symbolu nie
        usuwa poprawnego FinalAnalysisResult drugiego symbolu."""
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA"), make_quote("BBB.WA")],
            chart_rows_by_symbol={
                "AAA.WA": _rows(REALISTIC),
                "BBB.WA": _rows(1, offset_days=100),
            },
        )
        report = _build(tmp_path, session).run_cycle()

        assert any(r.symbol == "AAA.WA" for r in report.results)
        assert report.success_count == 1
        assert any(
            e.candidate_id == "BBB.WA" and "data points" in e.message
            for e in report.errors
        )


# ---------------------------------------------------------------------------
# 9 — restart → restore → zmiana → pełny przepływ
# ---------------------------------------------------------------------------

class TestPoint3RestoreFullFlow:
    def test_restore_then_changed_reading_enters_full_engine_flow(self, tmp_path):
        db = tmp_path / "e2e.db"

        s1 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC)},
        )
        _build(tmp_path, s1).run_cycle()

        # Symulowany restart — nowa instancja nad tą samą bazą.
        rt_restart = _build(
            tmp_path,
            FakeYahooSession(quotes=[], chart_rows_by_symbol={}),
        )
        restored = rt_restart.restore_active_observations()
        assert len(restored) == 1

        # Zmieniony odczyt po restarcie wchodzi do pełnego przepływu silników.
        s2 = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC, offset_days=100)},
        )
        report = _build(tmp_path, s2).run_cycle()
        assert report.success_count == 1
        assert report.results[0].symbol == "AAA.WA"


# ---------------------------------------------------------------------------
# 5/18 — niezmieniony odczyt zatrzymuje silniki
# ---------------------------------------------------------------------------

class TestPoint3UnchangedReading:
    def test_unchanged_reading_does_not_run_any_engine(self, tmp_path):
        rows = _rows(REALISTIC)
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": rows},
        )
        first = _build(tmp_path, session).run_cycle()
        assert first.success_count == 1

        second = _build(
            tmp_path,
            FakeYahooSession(
                quotes=[make_quote("AAA.WA")],
                chart_rows_by_symbol={"AAA.WA": rows},
            ),
        ).run_cycle()

        assert second.candidates_count == 0
        assert second.success_count == 0
        assert second.results == []


# ---------------------------------------------------------------------------
# 5-b/14 — kontrakt NewsEngine, brak sieci
# ---------------------------------------------------------------------------

class TestPoint3NewsContractAndNoNetwork:
    def test_news_engine_receives_proper_input_type(self, tmp_path, capsys):
        """NewsPipeline otrzymuje List[NewsItem] (obecnie pustą), a nie
        listę symboli (List[str])."""
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC)},
        )
        _build(tmp_path, session).run_cycle()

        captured = capsys.readouterr()
        assert "Pipeline error" not in captured.out
        assert "Pipeline error" not in captured.err

    def test_no_network_sent(self, tmp_path):
        session = FakeYahooSession(
            quotes=[make_quote("AAA.WA")],
            chart_rows_by_symbol={"AAA.WA": _rows(REALISTIC)},
        )
        _build(tmp_path, session).run_cycle()
        assert session.real_network_sent == 0