import threading
import time
from typing import Optional

class RuntimeScheduler:
    def __init__(self, runtime_service, interval: int = 60, continue_on_error: bool = False):
        self.runtime_service = runtime_service
        self.interval = interval
        self.continue_on_error = continue_on_error
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_once(self):
        try:
            self.runtime_service.run()
        except Exception as e:
            if not self.continue_on_error:
                raise
            # Log the error if necessary

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

    def _run_loop(self):
        while not self._stop_event.is_set():
            self.run_once()
            time.sleep(self.interval)