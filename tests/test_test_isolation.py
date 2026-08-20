"""ALCHEMIK — korekta izolacji testów od produkcyjnej bazy SQLite.

Test regresyjny potwierdza, że budowa composition root w teście używa
wyłącznie tymczasowej bazy SQLite, prawdziwy SQLiteHistoryRepository działa
na tej bazie, a produkcyjna baza data/runtime/alchemik_runtime.db nie jest
modyfikowana (SHA-256 przed i po teście identyczny).

Jedyna kontrolowana granica to test double sesji Yahoo (FakeSession) —
zgodnie z regułą 20 .clinerules. Żaden wewnętrzny komponent ALCHEMIKA
nie jest zastępowany mockiem.

RED: obecny composition root konstruuje SQLiteHistoryRepository PRZED
walidacją static_tickers (test ``test_static_validation_precedes_any_db_open``
wykrywa złą kolejność w źródle, bez otwierania jakiejkolwiek bazy).
GREEN: walidacja następuje przed konstrukcją repozytorium.
"""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

from application import entrypoint
from application.sqlite_history_repository import SQLiteHistoryRepository
from data.yahoo.yahoo_session import FetchResult, OutcomeKind, ScreenerPagination

PRODUCTION_DB = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "runtime"
    / "alchemik_runtime.db"
)
EXPECTED_PRODUCTION_SHA256 = (
    "ca2b8d03bdbb0221dc2d2431b3894ccdeaa2f56251fa0bc9443548919fa867fb"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FakeSession:
    """Test double wyłącznie na zewnętrznej granicy Yahoo (reguła 20)."""

    def paginate_screener(self, size=250):
        return FetchResult(
            kind=OutcomeKind.SUCCESS_WITH_DATA,
            data=ScreenerPagination(total=0, pages=[]),
            message=None,
        )

    def fetch_chart(self, symbol, variant="daily"):
        return FetchResult(
            kind=OutcomeKind.SUCCESS_NO_DATA,
            data=None,
            message=None,
        )


def test_composition_root_and_real_sqlite_use_only_temp_db(tmp_path):
    """GREEN: composition root w teście buduje prawdziwe SQLite repozytorium
    na jawnej tymczasowej ścieżce; produkcyjna baza pozostaje nietknięta."""
    assert PRODUCTION_DB.exists()
    sha_before = _sha256(PRODUCTION_DB)

    temp_db = tmp_path / "isolation_contract.db"
    runtime = entrypoint.build_runtime_service(
        persist_path=temp_db,
        yahoo_session=FakeSession(),
    )

    repo = runtime.history_repository
    assert isinstance(repo, SQLiteHistoryRepository)
    # Repozytorium wskazuje jawną tymczasową ścieżkę, nie RuntimeConfig.
    assert Path(repo.db_path).resolve() == temp_db.resolve()

    # Rzeczywisty zapis/odczyt na prawdziwym SQLite (bez mocka repozytorium).
    repo.save_cycle(
        "isolation_probe",
        {
            "execution_time": 1.0,
            "candidates_count": 0,
            "success_count": 0,
            "error_count": 0,
            "report": {},
        },
    )
    stored = repo.get_cycle("isolation_probe")
    assert stored is not None
    assert stored["cycle_id"] == "isolation_probe"

    # Produkcyjna baza nie jest modyfikowana — SHA przed i po identyczny.
    sha_after = _sha256(PRODUCTION_DB)
    assert sha_before == sha_after == EXPECTED_PRODUCTION_SHA256


def test_static_validation_precedes_any_db_open():
    """RED na obecnym kodzie: walidacja static_tickers musi wystąpić PRZED
    konstrukcją SQLiteHistoryRepository, aby błędna konfiguracja nie otwierała
    produkcyjnej bazy. Test statyczny — nie otwiera żadnej bazy."""
    src = inspect.getsource(entrypoint.build_runtime_service)
    repo_pos = src.find("SQLiteHistoryRepository(")
    validate_pos = src.find("validate_static_tickers(")
    assert repo_pos != -1, "build_runtime_service nie konstruuje SQLiteHistoryRepository"
    assert validate_pos != -1, "build_runtime_service nie waliduje static_tickers"
    assert validate_pos < repo_pos, (
        "SQLiteHistoryRepository jest konstruowane PRZED walidacją static_tickers — "
        "błędna konfiguracja otwiera produkcyjną bazę."
    )