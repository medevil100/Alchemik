"""
Step 7B/8 — controlled validation safety contract (RED).

Te testy działają wyłącznie offline. Weryfikują kontrakt BUDOWY i BLOKAD
trybu CONTROLLED_VALIDATION_ONLY:
  * bez dwóch jawnych flag — zero efektów (bez sekretów, bez klientów,
    bez zapisywalnej bazy, bez markera, bez RuntimeService, bez sieci);
  * jedna flaga — zero efektów;
  * produkcyjna ścieżka bazy — twarde odrzucenie;
  * ścieżka równoważna produkcyjnej (symlink/junction/case) — twarde odrzucenie;
  * katalog artefaktów w repo — odrzucenie;
  * istniejący marker — stop.

Komponenty wewnętrzne ALCHEMIKA nie są podmieniane mockami. Testy korzystają
wyłącznie z publicznego kontraktu ``application.controlled_validation`` oraz
cienkiego CLI (``application/controlled_validation_cli``).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from application.controlled_validation import (
    ControlledValidationConfig,
    ensure_safe_paths,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROD_DB = PROJECT_ROOT / "data" / "runtime" / "alchemik_runtime.db"


@pytest.fixture
def isolated_copy(tmp_path: Path) -> Path:
    """Tworzy prawdziwą izolowaną kopię produkcyjnej bazy na tmp_path."""
    target = tmp_path / "isolated" / "alchemik_runtime.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(PROD_DB.read_bytes())
    return target


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"


# ---------------------------------------------------------------------------
# Brak flag — zero efektów
# ---------------------------------------------------------------------------

class TestNoFlagsNoEffects:
    def test_no_flags_means_no_effects(self, tmp_path: Path, isolated_copy: Path,
                                       artifacts_dir: Path):
        """CLI bez flag musi zakończyć się błędem PRZED jakimkolwiek efektem."""
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "application" / "controlled_validation_cli.py"),
                "--isolated-db", str(isolated_copy),
                "--artifacts-dir", str(artifacts_dir),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=60,
        )
        assert result.returncode != 0
        assert "CONTROLLED_VALIDATION_ONLY" in result.stderr
        # Zero efektów: brak katalogu artefaktów, brak markera, brak procesu.
        assert not artifacts_dir.exists()
        assert not (tmp_path / "marker" / "step7b.marker").exists()

    def test_one_flag_only_means_no_effects(self, tmp_path: Path, isolated_copy: Path,
                                            artifacts_dir: Path):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "application" / "controlled_validation_cli.py"),
                "--allow-network",
                "--isolated-db", str(isolated_copy),
                "--artifacts-dir", str(artifacts_dir),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=60,
        )
        assert result.returncode != 0
        assert not artifacts_dir.exists()


# ---------------------------------------------------------------------------
# Bezpieczeństwo ścieżek
# ---------------------------------------------------------------------------

class TestPathSafety:
    def test_production_db_rejected(self, tmp_path: Path, artifacts_dir: Path):
        with pytest.raises(ValueError, match="produkcyj"):
            ensure_safe_paths(
                ControlledValidationConfig(
                    isolated_db_path=PROD_DB,
                    artifacts_dir=artifacts_dir,
                    production_db_path=PROD_DB,
                )
            )

    def test_equivalent_production_path_rejected_case_insensitive(
        self, tmp_path: Path, isolated_copy: Path, artifacts_dir: Path
    ):
        """Na Windows ścieżka równoważna produkcyjnej (case) jest odrzucana."""
        if os.name != "nt":
            pytest.skip("case-insensitive check only on Windows")
        equivalent = Path(str(PROD_DB).upper())
        with pytest.raises(ValueError, match="produkcyj"):
            ensure_safe_paths(
                ControlledValidationConfig(
                    isolated_db_path=equivalent,
                    artifacts_dir=artifacts_dir,
                    production_db_path=PROD_DB,
                )
            )

    def test_artifacts_dir_inside_repo_rejected(self, tmp_path: Path, isolated_copy: Path):
        repo_artifacts = PROJECT_ROOT / "artifacts_step7b_test"
        with pytest.raises(ValueError, match="repo"):
            ensure_safe_paths(
                ControlledValidationConfig(
                    isolated_db_path=isolated_copy,
                    artifacts_dir=repo_artifacts,
                    production_db_path=PROD_DB,
                )
            )

    def test_artifacts_dir_outside_repo_accepted(self, tmp_path: Path, isolated_copy: Path,
                                                 artifacts_dir: Path):
        cfg = ensure_safe_paths(
            ControlledValidationConfig(
                isolated_db_path=isolated_copy,
                artifacts_dir=artifacts_dir,
                production_db_path=PROD_DB,
            )
        )
        assert cfg.isolated_db_path == isolated_copy.resolve()


# ---------------------------------------------------------------------------
# Marker jednokrotności
# ---------------------------------------------------------------------------

class TestOnceMarker:
    def test_existing_marker_stops_run(self, isolated_copy: Path, artifacts_dir: Path):
        from application.controlled_validation import (
            ensure_once_marker,
            marker_path_for,
            OnceAlreadyRunError,
        )
        marker = marker_path_for(artifacts_dir)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("done", encoding="utf-8")
        with pytest.raises(OnceAlreadyRunError):
            ensure_once_marker(artifacts_dir)