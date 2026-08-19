"""Międzyprocesowa blokada pojedynczego cyklu produkcyjnego ALCHEMIKA.

Systemowa, nieblokująca blokada pliku:
* Windows: ``msvcrt.locking(LK_NBLCK)`` na jednym bajcie pliku;
* POSIX: ``fcntl.flock(LOCK_EX | LOCK_NB)``.

Plik techniczny leży w systemowym katalogu tymczasowym, nigdy w repozytorium
i nigdy obok bazy. Nazwa pliku jest wyprowadzona deterministycznie z SHA-256
kanonicznej, absolutnej ścieżki produkcyjnej bazy SQLite, więc dwa procesy
korzystające z tej samej bazy zawsze używają tego samego pliku.

Fail-fast: brak retry, pętli, sleep, backoff ani fallbacku. Zwolnienie następuje
jawnie oraz automatycznie przez system operacyjny po śmierci procesu.
Pozostający plik ``.lock`` bez blokady systemowej NIE jest aktywną blokadą.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - platform
    import msvcrt  # type: ignore

    _IS_WINDOWS = True
except ImportError:  # pragma: no cover - platform
    _IS_WINDOWS = False


class CycleAlreadyRunningError(RuntimeError):
    """Inny proces wykonuje już cykl dla tej samej produkcyjnej bazy."""


def lock_identity_for_db(db_path: Path) -> str:
    """Deterministyczny identyfikator blokady z kanonicznej ścieżki bazy.

    Na Windows ścieżka jest normalizowana bez rozróżniania wielkości liter.
    """
    canonical = str(Path(db_path).resolve())
    if _IS_WINDOWS:
        canonical = canonical.lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def lock_path_for_db(db_path: Path) -> Path:
    """Pełna ścieżka technicznego pliku blokady w systemowym katalogu tymczasowym."""
    identity = lock_identity_for_db(db_path)
    return Path(tempfile.gettempdir()) / f"alchemik_cycle_{identity}.lock"


class CycleLock:
    """Systemowa, międzyprocesowa blokada pojedynczego cyklu ALCHEMIKA."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.lock_path = lock_path_for_db(self.db_path)
        self._fh: Optional[object] = None

    # ------------------------------------------------------------------
    # Pozyskanie i zwolnienie
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Pozyskaj blokadę natychmiast (fail-fast).

        Raises:
            CycleAlreadyRunningError: jeżeli inny proces trzyma blokadę.
        """
        if self._fh is not None:
            raise CycleAlreadyRunningError(
                "Cycle lock already held by this process "
                f"(lock file: {self.lock_path.name})"
            )
        if not self.lock_path.exists():
            self.lock_path.touch()
        if self.lock_path.stat().st_size == 0:
            with open(self.lock_path, "wb") as zf:
                zf.write(b"\x00")
        fh = open(self.lock_path, "r+b")
        try:
            if _IS_WINDOWS:
                fh.seek(0)
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    fh.close()
                    raise CycleAlreadyRunningError(
                        "Another ALCHEMIK cycle is already running "
                        f"(lock file: {self.lock_path.name})"
                    )
            else:
                import fcntl

                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    fh.close()
                    raise CycleAlreadyRunningError(
                        "Another ALCHEMIK cycle is already running "
                        f"(lock file: {self.lock_path.name})"
                    )
        except CycleAlreadyRunningError:
            raise
        except Exception:
            fh.close()
            raise
        self._fh = fh

    def release(self) -> None:
        """Zwolnij blokadę. Wielokrotne wywołanie jest bezpieczne (idempotentne)."""
        if self._fh is None:
            return
        fh = self._fh
        self._fh = None
        try:
            if _IS_WINDOWS:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "CycleLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Diagnostyka
    # ------------------------------------------------------------------

    @property
    def held(self) -> bool:
        """Czy bieżący proces trzyma blokadę systemową."""
        return self._fh is not None

    def __repr__(self) -> str:
        return (
            f"<CycleLock {self.lock_path.name} "
            f"{'held' if self.held else 'free'}>"
        )