import unittest
import threading
import time
from unittest.mock import MagicMock
from application.scheduler import RuntimeScheduler

class TestRuntimeScheduler(unittest.TestCase):
    def setUp(self):
        self.mock_runtime_service = MagicMock()
        self.scheduler = RuntimeScheduler(self.mock_runtime_service, interval=1, continue_on_error=True)

    def test_run_once(self):
        self.scheduler.run_once()
        self.mock_runtime_service.run.assert_called_once()

    def test_run_once_with_error(self):
        self.mock_runtime_service.run.side_effect = Exception("Test error")
        self.scheduler.run_once()  # Should not raise

    def test_start_stop(self):
        self.scheduler.start()
        time.sleep(0.1)  # Allow thread to start
        self.assertTrue(self.scheduler._thread.is_alive())
        self.scheduler.stop()
        self.assertFalse(self.scheduler._thread.is_alive())

    def test_stop_event(self):
        self.scheduler.start()
        self.scheduler.stop()
        self.assertTrue(self.scheduler._stop_event.is_set())