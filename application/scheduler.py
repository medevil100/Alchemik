"""Produkcyjny scheduler ALCHEMIKA (Krok 8.3).

Cykl pracy:
* pierwszy ``run_once()`` wykonywany natychmiast po starcie pętli;
* po kazdej probie przerwalne oczekiwanie ``_stop_event.wait(self.interval)``;
* domyslny interwal produkcyjny: 900 sekund (15 minut);
* brak kolejki, retry, catch-up i rownoleglych cykli.

Podzial odpowiedzialnosci (zatwierdzony po STOP_STEP8_3_CYCLELOCK_CONTRACT_GAP):
* ``RuntimeService.run_cycle()`` pozostaje jedynym wlascicielem przejecia
  i zwolnienia ``CycleLock`` (dekorator ``_cycle_lock_guard``);
* scheduler nie otrzymuje i nie przejmuje ``CycleLock``;
* scheduler wywoluje publiczne, juz chronione ``run_cycle()``;
* zajeta blokada (``CycleAlreadyRunningError`` z chronionego ``run_cycle()``)
  jest mapowana na status ``SKIPPED_OVERLAP``.
"""
import logging
import threading
from typing import Optional

from application.cycle_lock import CycleAlreadyRunningError

logger = logging.getLogger(__name__)

EXECUTED = "EXECUTED"
SKIPPED_OVERLAP = "SKIPPED_OVERLAP"
CYCLE_ERROR = "CYCLE_ERROR"

DEFAULT_INTERVAL_SECONDS = 900


class RuntimeScheduler:
    def __init__(self, runtime_service, interval: int = DEFAULT_INTERVAL_SECONDS,
                 continue_on_error: bool = False):
        if interval <= 0:
            raise ValueError("interval must be a positive number of seconds")
        self.runtime_service = runtime_service
        self.interval = interval
        self.continue_on_error = continue_on_error
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_once(self):
        """Wykonaj dokladnie jedna probe cyklu i zwroc jawny status.

        Returns:
            ``EXECUTED`` po sukcesie;
            ``SKIPPED_OVERLAP`` gdy chroniony ``run_cycle()`` odrzucil probe
            zajeta blokada innego procesu;
            ``CYCLE_ERROR`` po pojedynczym bledzie cyklu, gdy
            ``continue_on_error`` jest wlaczone.
        """
        try:
            self.runtime_service.run_cycle()
        except CycleAlreadyRunningError:
            logger.warning("Scheduler: cycle skipped - CycleLock busy (SKIPPED_OVERLAP)")
            return SKIPPED_OVERLAP
        except Exception:
            logger.exception("Scheduler: cycle error")
            if not self.continue_on_error:
                raise
            return CYCLE_ERROR
        return EXECUTED

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()

    def run_forever(self):
        """Blokujace uruchomienie petli schedulera (dla trybu ``--scheduler``)."""
        self._run_loop()

    def _run_loop(self):
        while not self._stop_event.is_set():
            self.run_once()
            # Przerwalne oczekiwanie: stop() podczas oczekiwania konczy petle
            # bez uruchamiania kolejnego cyklu.
            if self._stop_event.wait(self.interval):
                break