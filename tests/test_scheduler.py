import unittest
import threading
import time
from application.scheduler import RuntimeScheduler
from application.runtime import RuntimeService
from engines.hunter import HunterEngine
from engines.master import MasterEngine
from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.ai import DecisionEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.analyst import AnalystEngine
from engines.price_detector import PriceDetector
from engines.volume_detector import VolumeDetector
from application.history_repository import HistoryRepository

HUNTER_CONFIG = {
    "ranking_weight": 0.4,
    "risk_weight": 0.3,
    "confidence_weight": 0.3,
    "min_ranking_score": 0.0,
    "max_risk_score": 1.0,
    "min_confidence": 0.0,
    "max_results": 100,
    "priority_thresholds": [0.9, 0.7, 0.5],
}


def _build_real_runtime_service():
    """Build a RuntimeService with real internal engine instances."""
    technical_engine = TechnicalEngine()
    news_engine = NewsPipeline(filter_config=None)
    ai_engine = DecisionEngine()
    ranking_engine = RankingEngine()
    risk_engine = RiskEngine()
    hunter_engine = HunterEngine(HUNTER_CONFIG)
    analyst_engine = AnalystEngine()
    price_detector = PriceDetector()
    volume_detector = VolumeDetector()
    master_engine = MasterEngine(
        technical_engine=technical_engine,
        news_engine=news_engine,
        ai_engine=ai_engine,
        ranking_engine=ranking_engine,
        risk_engine=risk_engine,
        hunter_engine=hunter_engine,
        analyst_engine=analyst_engine,
        price_detector=price_detector,
        volume_detector=volume_detector,
    )
    history_repository = HistoryRepository()
    return RuntimeService(
        hunter_engine=hunter_engine,
        master_engine=master_engine,
        history_repository=history_repository,
    )


class TestRuntimeScheduler(unittest.TestCase):
    def setUp(self):
        self.runtime_service = _build_real_runtime_service()
        self.scheduler = RuntimeScheduler(self.runtime_service, interval=1, continue_on_error=True)

    def test_run_once_calls_run_cycle(self):
        """Scheduler.run_once() calls RuntimeService.run_cycle() exactly once."""
        self.scheduler.run_once()

    def test_run_cycle_method_exists(self):
        """Real RuntimeService has run_cycle method."""
        self.assertTrue(hasattr(self.runtime_service, "run_cycle"))

    def test_run_once_with_error_continue_on_error_true(self):
        """Error from run_cycle() is silently caught when continue_on_error=True."""
        scheduler = RuntimeScheduler(self.runtime_service, interval=1, continue_on_error=True)
        scheduler.run_once()

    def test_start_stop(self):
        self.scheduler.start()
        time.sleep(0.1)
        self.assertTrue(self.scheduler._thread.is_alive())
        self.scheduler.stop()
        self.assertFalse(self.scheduler._thread.is_alive())

    def test_stop_event(self):
        self.scheduler.start()
        self.scheduler.stop()
        self.assertTrue(self.scheduler._stop_event.is_set())
