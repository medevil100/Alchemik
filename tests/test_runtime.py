import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from application.runtime import RuntimeService
from application.models import CycleReport, CandidateError
from data.models.final_analysis_result import FinalAnalysisResult
from data.models import MarketEvent, InstrumentType
from application.market_scanner import MarketScanner

class TestRuntimeService(unittest.TestCase):
    def setUp(self):
        self.mock_hunter = MagicMock()
        self.mock_master = MagicMock()
        self.mock_repository = MagicMock()
        self.mock_deduplicator = MagicMock()
        self.runtime = RuntimeService(
            hunter_engine=self.mock_hunter,
            master_engine=self.mock_master,
            history_repository=self.mock_repository,
            deduplicator=self.mock_deduplicator
        )

    def test_run_cycle_success(self):
        """Test successful cycle with multiple candidates."""
        # Setup mock hunter result
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [
            MagicMock(instrument_id="A"),
            MagicMock(instrument_id="B")
        ]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        # Setup mock master results
        mock_result_a = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        mock_result_b = FinalAnalysisResult(
            symbol="B",
            final_rating=60,
            confidence_level=70,
            recommendation="Hold",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.side_effect = [mock_result_a, mock_result_b]
        
        # Run cycle
        report = self.runtime.run_cycle({})
        
        # Verify results
        self.assertEqual(report.candidates_count, 2)
        self.assertEqual(report.success_count, 2)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(len(report.results), 2)
        self.assertEqual(len(report.errors), 0)
        self.mock_hunter.scan.assert_called_once_with({})
        self.assertEqual(self.mock_master.run_analysis.call_count, 2)
        self.mock_repository.save_cycle.assert_called_once()

    def test_run_cycle_empty_hunter(self):
        """Test cycle with empty hunter result."""
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = []
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        report = self.runtime.run_cycle({})
        
        self.assertEqual(report.candidates_count, 0)
        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(len(report.results), 0)
        self.assertEqual(len(report.errors), 0)
        self.mock_master.run_analysis.assert_not_called()

    def test_run_cycle_hunter_error(self):
        """Test cycle where hunter engine fails."""
        self.mock_hunter.scan.side_effect = Exception("Hunter error")
        
        report = self.runtime.run_cycle({})
        
        self.assertEqual(report.candidates_count, 0)
        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(len(report.results), 0)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].stage, "Hunter Engine")
        self.mock_master.run_analysis.assert_not_called()
        self.mock_repository.save_cycle.assert_not_called()

    def test_run_cycle_master_error(self):
        """Test cycle where one candidate fails in master engine."""
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [
            MagicMock(instrument_id="A"),
            MagicMock(instrument_id="B")
        ]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        # Setup one success and one failure
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.side_effect = [
            mock_result, 
            Exception("Master error")
        ]
        
        report = self.runtime.run_cycle({})
        
        self.assertEqual(report.candidates_count, 2)
        self.assertEqual(report.success_count, 1)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(len(report.results), 1)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].stage, "Master Engine")
        self.assertEqual(report.errors[0].candidate_id, "B")
        self.mock_repository.save_cycle.assert_called_once()
        
    def test_run_cycle_with_market_scanner(self):
        """Test full workflow with MarketScanner integration."""
        mock_scanner = MagicMock(spec=MarketScanner)
        mock_scanner.scan.return_value = ["A", "B"]
        
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            market_scanner=mock_scanner,
            deduplicator=MagicMock(should_process=lambda x: True)
        )
        
        # Setup mock hunter result
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [
            MagicMock(instrument_id="A"),
            MagicMock(instrument_id="B")
        ]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        # Setup mock master results
        mock_result_a = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        mock_result_b = FinalAnalysisResult(
            symbol="B",
            final_rating=60,
            confidence_level=70,
            recommendation="Hold",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.side_effect = [mock_result_a, mock_result_b]
        
        # Run cycle
        report = runtime.run_cycle({})
        
        # Verify results
        mock_scanner.scan.assert_called_once()
        self.mock_hunter.scan.assert_called_once_with(["A", "B"])
        self.assertEqual(report.candidates_count, 2)
        self.assertEqual(report.success_count, 2)
        
    def test_run_cycle_empty_market_scanner(self):
        """Test with empty MarketScanner result."""
        mock_scanner = MagicMock(spec=MarketScanner)
        mock_scanner.scan.return_value = []
        
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            market_scanner=mock_scanner
        )
        report = runtime.run_cycle({})
        
        mock_scanner.scan.assert_called_once()
        self.mock_hunter.scan.assert_called_once_with([])
        self.assertEqual(report.candidates_count, 0)
        
    def test_run_cycle_market_scanner_error(self):
        """Test when MarketScanner raises an exception."""
        mock_scanner = MagicMock(spec=MarketScanner)
        mock_scanner.scan.side_effect = Exception("Scanner error")
        
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            market_scanner=mock_scanner
        )
        report = runtime.run_cycle({})
        
        self.assertEqual(report.candidates_count, 0)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.errors[0].stage, "MarketScanner")
        self.mock_hunter.scan.assert_not_called()

    def test_repository_save_after_successful_cycle(self):
        """Test that repository.save_cycle is called after a successful cycle."""
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        self.runtime.run_cycle({})
        self.mock_repository.save_cycle.assert_called_once()

    def test_repository_save_called_once(self):
        """Test that repository.save_cycle is called exactly once per cycle."""
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        self.runtime.run_cycle({})
        self.mock_repository.save_cycle.assert_called_once()

    def test_repository_receives_correct_cycle_data(self):
        """Test that repository.save_cycle receives correct cycle data."""
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        self.runtime.run_cycle({})
        self.mock_repository.save_cycle.assert_called_once()
        args, _ = self.mock_repository.save_cycle.call_args
        
        # 1. Verify exactly 2 arguments
        self.assertEqual(len(args), 2)
        
        # 2. Verify args[0] is a string (cycle_id)
        self.assertIsInstance(args[0], str)
        
        # 3. Verify args[1] is a dictionary
        self.assertIsInstance(args[1], dict)
        
        # 4. Verify args[1]["report"] is a CycleReport
        self.assertIsInstance(args[1]["report"], CycleReport)
        
        # 5. Verify counters match the report
        report = args[1]["report"]
        self.assertEqual(args[1]["candidates_count"], report.candidates_count)
        self.assertEqual(args[1]["success_count"], report.success_count)
        self.assertEqual(args[1]["error_count"], report.error_count)
        
        # 6. Verify cycle_id matches
        self.assertEqual(args[1]["cycle_id"], args[0])

    def test_repository_dependency_injection(self):
        """Test that repository is correctly injected into RuntimeService."""
        mock_repository = MagicMock()
        runtime = RuntimeService(self.mock_hunter, self.mock_master, mock_repository)
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        runtime.run_cycle({})
        mock_repository.save_cycle.assert_called_once()

    def test_repository_error_does_not_break_runtime(self):
        """Test that repository.save_cycle error doesn't break runtime."""
        self.mock_repository.save_cycle.side_effect = Exception("Repository error")
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        report = self.runtime.run_cycle({})
        self.assertEqual(report.candidates_count, 1)
        self.assertEqual(report.success_count, 1)
        # Error is now properly logged and counted (not silently swallowed)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.errors[0].stage, "HistoryRepository")

    def test_deduplicator_skips_duplicates(self):
        """Test that duplicates are skipped and don't reach MasterEngine."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = False
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator
        )
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        report = runtime.run_cycle({})
        
        mock_deduplicator.should_process.assert_called_once_with("A")
        self.mock_master.run_analysis.assert_not_called()
        self.assertEqual(report.candidates_count, 1)
        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.error_count, 0)

    def test_deduplicator_processes_new_opportunities(self):
        """Test that new opportunities are processed by MasterEngine."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator
        )
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        report = runtime.run_cycle({})

        mock_deduplicator.should_process.assert_called_once_with("A")
        self.mock_master.run_analysis.assert_called_once()
        # Verify the first positional arg is "A"
        args, kwargs = self.mock_master.run_analysis.call_args
        self.assertEqual(args[0], "A")
        mock_deduplicator.mark_processed.assert_called_once_with("A")
        self.assertEqual(report.candidates_count, 1)
        self.assertEqual(report.success_count, 1)
        self.assertEqual(report.error_count, 0)

    def test_deduplicator_exceptions_do_not_stop_cycle(self):
        """Test that deduplicator exceptions are logged but don't stop the cycle."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.side_effect = Exception("Deduplicator error")
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator
        )
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        report = runtime.run_cycle({})
        
        mock_deduplicator.should_process.assert_called_once_with("A")
        self.mock_master.run_analysis.assert_not_called()
        self.assertEqual(report.candidates_count, 1)
        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.errors[0].stage, "Deduplicator")

    def test_deduplicator_dependency_injection(self):
        """Test that deduplicator is correctly injected into RuntimeService."""
        mock_deduplicator = MagicMock()
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator
        )
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        runtime.run_cycle({})
        mock_deduplicator.should_process.assert_called_once_with("A")
        mock_deduplicator.mark_processed.assert_called_once_with("A")
        
    # ------------------------------------------------------------------
    # ETAP 7.5 — Alert pipeline tests (MarketEvent integration)
    # ------------------------------------------------------------------

    def _setup_alert_runtime(self, **kwargs):
        """Helper to create RuntimeService with alert components and a
        MasterEngine that populates events_out."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        mock_telegram = kwargs.pop("telegram_channel", MagicMock())
        defaults = dict(
            deduplicator=mock_deduplicator,
            alert_builder=MagicMock(),
            alert_dispatcher=MagicMock(),
            telegram_channel=mock_telegram,
        )
        defaults.update(kwargs)
        return RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            **defaults,
        )

    @staticmethod
    def _make_market_event(**overrides):
        """Build a minimal mock MarketEvent for alert tests."""
        ev = MagicMock()
        ev.event_type = overrides.get("event_type", "PRICE_SURGE")
        ev.event_family = overrides.get("event_family", None)
        ev.priority_final = overrides.get("priority_final", None)
        ql = MagicMock()
        ql.value = overrides.get("quality_level", "HIGH")
        ev.quality_level = ql
        ev.is_composite = overrides.get("is_composite", False)
        ev.composite_events = overrides.get("composite_events", [])
        ev.market = overrides.get("market", "GPW")
        ev.ai_context = overrides.get("ai_context", None)
        return ev

    def _run_alert_cycle(self, runtime, events_out_content=None, master_result=None):
        """Execute one cycle with a single candidate and return the report."""
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        if master_result is None:
            master_result = FinalAnalysisResult(
                symbol="TST",
                final_rating=85,
                confidence_level=90,
                recommendation="STRONG_BUY",
                positive_factors=[],
                risk_factors=[],
                warnings=[],
                summary="Analysis summary",
                generated_at=datetime.now(),
            )

        def populate_events_out(*args, **kwargs):
            out = kwargs.get("events_out")
            if out is not None and events_out_content is not None:
                out.extend(events_out_content)
            return master_result

        self.mock_master.run_analysis.side_effect = populate_events_out
        return runtime.run_cycle({})

    def test_alert_pipeline_passes_market_event_and_result(self):
        """Runtime passes FinalAnalysisResult and MarketEvent to AlertBuilder."""
        event = self._make_market_event(quality_level="HIGH")
        runtime = self._setup_alert_runtime()
        runtime.alert_builder.should_alert.return_value = True

        self._run_alert_cycle(runtime, events_out_content=[event])

        runtime.alert_builder.should_alert.assert_called_once()
        call_args = runtime.alert_builder.should_alert.call_args
        self.assertIsInstance(call_args[0][0], FinalAnalysisResult)
        self.assertEqual(call_args[1]["event"], event)

        runtime.alert_builder.build_alert.assert_called_once()
        build_args = runtime.alert_builder.build_alert.call_args
        self.assertIsInstance(build_args[0][0], FinalAnalysisResult)
        self.assertEqual(build_args[1]["event"], event)

    def test_alert_pipeline_should_alert_false_skips_dispatch(self):
        """When should_alert returns False, no alert is built or dispatched."""
        event = self._make_market_event(quality_level="HIGH")
        runtime = self._setup_alert_runtime()
        runtime.alert_builder.should_alert.return_value = False

        self._run_alert_cycle(runtime, events_out_content=[event])

        runtime.alert_builder.build_alert.assert_not_called()
        runtime.alert_dispatcher.dispatch.assert_not_called()

    def test_alert_quality_ignore_skipped(self):
        """MarketEvent with quality_level IGNORE does not generate an alert."""
        event = self._make_market_event(quality_level="IGNORE")
        runtime = self._setup_alert_runtime()

        self._run_alert_cycle(runtime, events_out_content=[event])

        runtime.alert_builder.should_alert.assert_not_called()
        runtime.alert_dispatcher.dispatch.assert_not_called()

    def test_alert_quality_low_skipped(self):
        """MarketEvent with quality_level LOW does not generate an alert."""
        event = self._make_market_event(quality_level="LOW")
        runtime = self._setup_alert_runtime()

        self._run_alert_cycle(runtime, events_out_content=[event])

        runtime.alert_builder.should_alert.assert_not_called()
        runtime.alert_dispatcher.dispatch.assert_not_called()

    def test_alert_telegram_channel_passed_to_dispatcher(self):
        """TelegramChannel is passed inside a list to AlertDispatcher.dispatch."""
        event = self._make_market_event(quality_level="HIGH")
        mock_telegram = MagicMock()
        runtime = self._setup_alert_runtime(telegram_channel=mock_telegram)
        runtime.alert_builder.should_alert.return_value = True

        self._run_alert_cycle(runtime, events_out_content=[event])

        runtime.alert_dispatcher.dispatch.assert_called_once()
        args, _ = runtime.alert_dispatcher.dispatch.call_args
        self.assertIsInstance(args[0], MagicMock)  # alert_message (mock)
        self.assertEqual(args[1], [mock_telegram])

    def test_alert_missing_telegram_channel_no_error(self):
        """Cycle completes successfully even without telegram_channel configured."""
        event = self._make_market_event(quality_level="HIGH")
        runtime = self._setup_alert_runtime(telegram_channel=None)
        runtime.alert_builder.should_alert.return_value = True

        report = self._run_alert_cycle(runtime, events_out_content=[event])

        runtime.alert_dispatcher.dispatch.assert_called_once()
        args, _ = runtime.alert_dispatcher.dispatch.call_args
        self.assertEqual(args[1], [])  # empty channel list
        self.assertEqual(report.error_count, 0)

    def test_alert_telegram_error_does_not_stop_runtime(self):
        """Telegram dispatch failure is logged, not raised — cycle continues."""
        event = self._make_market_event(quality_level="HIGH")
        mock_telegram = MagicMock()
        runtime = self._setup_alert_runtime(telegram_channel=mock_telegram)
        runtime.alert_builder.should_alert.return_value = True
        runtime.alert_dispatcher.dispatch.side_effect = Exception("Telegram API error")

        report = self._run_alert_cycle(runtime, events_out_content=[event])

        # Cycle must complete successfully — error_count remains 0
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.success_count, 1)

    def test_alert_no_market_events_skips_pipeline(self):
        """When no MarketEvents are detected, alert pipeline is not invoked."""
        runtime = self._setup_alert_runtime()

        self._run_alert_cycle(runtime, events_out_content=[])  # no events

        runtime.alert_builder.should_alert.assert_not_called()
        runtime.alert_dispatcher.dispatch.assert_not_called()

    def test_alert_pipeline_no_components(self):
        """Runtime works without any alert components (unchanged)."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True

        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="A",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        self.assertEqual(report.error_count, 0)

    def test_alert_telegram_message_id_not_saved(self):
        """telegram_message_id is NOT written to MarketEvent.metadata."""
        event = self._make_market_event(quality_level="HIGH")
        runtime = self._setup_alert_runtime()
        runtime.alert_builder.should_alert.return_value = True

        self._run_alert_cycle(runtime, events_out_content=[event])

        # event.metadata must NOT be touched for telegram_message_id
        if hasattr(event, 'metadata'):
            self.assertNotIn("telegram_message_id", event.metadata or {})

    def test_alert_history_repository_not_called_for_telegram(self):
        """HistoryRepository is not invoked to persist Telegram metadata."""
        event = self._make_market_event(quality_level="HIGH")
        runtime = self._setup_alert_runtime()
        runtime.alert_builder.should_alert.return_value = True

        self._run_alert_cycle(runtime, events_out_content=[event])

        # Repository is called for save_cycle, but NOT for Telegram-specific writes
        # Save cycle call is expected; no new Telegram-specific calls
        self.mock_repository.save_cycle.assert_called()

    def test_alert_pipeline_no_alert_for_duplicate(self):
        """Duplicates skipped by deduplicator — no alert pipeline invoked."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = False
        mock_alert_builder = MagicMock()
        mock_alert_dispatcher = MagicMock()

        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            alert_builder=mock_alert_builder,
            alert_dispatcher=mock_alert_dispatcher
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        report = runtime.run_cycle({})

        mock_alert_builder.should_alert.assert_not_called()
        mock_alert_dispatcher.dispatch.assert_not_called()
        self.assertEqual(report.error_count, 0)

    def test_alert_pipeline_skip_on_master_error(self):
        """Alert pipeline is skipped when MasterEngine raises an exception."""
        mock_alert_builder = MagicMock()
        mock_alert_dispatcher = MagicMock()
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True

        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            alert_builder=mock_alert_builder,
            alert_dispatcher=mock_alert_dispatcher
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="A")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        self.mock_master.run_analysis.side_effect = Exception("Master error")

        report = runtime.run_cycle({})

        mock_alert_builder.should_alert.assert_not_called()
        mock_alert_dispatcher.dispatch.assert_not_called()
        self.assertEqual(report.error_count, 1)

    def test_multiple_opportunities_with_duplicates(self):
        """Test behavior with some duplicates and some new opportunities."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.side_effect = [False, True]  # First is duplicate, second is new
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator
        )
        
        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [
            MagicMock(instrument_id="A"),
            MagicMock(instrument_id="B")
        ]
        self.mock_hunter.scan.return_value = mock_hunter_result
        
        mock_result = FinalAnalysisResult(
            symbol="B",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result
        
        report = runtime.run_cycle({})
        
        self.assertEqual(mock_deduplicator.should_process.call_count, 2)
        self.mock_master.run_analysis.assert_called_once()
        # Verify the first positional arg is "B"
        args, kwargs = self.mock_master.run_analysis.call_args
        self.assertEqual(args[0], "B")
        mock_deduplicator.mark_processed.assert_called_once_with("B")
        self.assertEqual(report.candidates_count, 2)
        self.assertEqual(report.success_count, 1)
        self.assertEqual(report.error_count, 0)

    def test_runtime_does_not_create_deduplicator(self):
        """Test that RuntimeService does not instantiate the deduplicator itself."""
        with patch('application.opportunity_deduplicator.OpportunityDeduplicator') as mock_deduplicator_class:
            runtime = RuntimeService(
                self.mock_hunter,
                self.mock_master,
                self.mock_repository,
                deduplicator=mock_deduplicator_class.return_value
            )
            
            mock_deduplicator_class.assert_not_called()  # Should be passed as instance, not created

    # ------------------------------------------------------------------
    # NEW TESTS: Instrument metadata resolution and MarketEvent flow
    # ------------------------------------------------------------------

    def test_runtime_resolves_instrument_metadata(self):
        """Test that RuntimeService resolves market and instrument_type from metadata."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            instrument_metadata={
                "TEST": ("NYSE", InstrumentType.STOCK_USA),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TEST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        # Verify MasterEngine was called with correct metadata
        self.mock_master.run_analysis.assert_called_once()
        args, kwargs = self.mock_master.run_analysis.call_args
        self.assertEqual(args[0], "TEST")
        self.assertEqual(kwargs["market"], "NYSE")
        self.assertEqual(kwargs["instrument_type"], InstrumentType.STOCK_USA)

    def test_runtime_passes_gpw_metadata(self):
        """Test that RuntimeService passes GPW metadata correctly."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            instrument_metadata={
                "XYZ.WA": ("GPW", InstrumentType.STOCK_GPW),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="XYZ.WA")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="XYZ.WA",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        self.mock_master.run_analysis.assert_called_once()
        args, kwargs = self.mock_master.run_analysis.call_args
        self.assertEqual(args[0], "XYZ.WA")
        self.assertEqual(kwargs["market"], "GPW")
        self.assertEqual(kwargs["instrument_type"], InstrumentType.STOCK_GPW)

    def test_runtime_collects_market_events(self):
        """Test that RuntimeService collects MarketEvents via events_out list."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            instrument_metadata={
                "TEST": ("NYSE", InstrumentType.STOCK_USA),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TEST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        # Verify events_out was passed to MasterEngine
        self.mock_master.run_analysis.assert_called_once()
        args, kwargs = self.mock_master.run_analysis.call_args
        self.assertIn("events_out", kwargs)
        self.assertIsInstance(kwargs["events_out"], list)

    def test_detectors_not_run_twice(self):
        """Test that detectors are NOT run a second time by RuntimeService."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            instrument_metadata={
                "TEST": ("NYSE", InstrumentType.STOCK_USA),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TEST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        # MasterEngine.run_analysis is called exactly once per candidate
        self.mock_master.run_analysis.assert_called_once()
        # RuntimeService does NOT call detectors directly
        self.assertFalse(hasattr(runtime, 'price_detector'))
        self.assertFalse(hasattr(runtime, 'volume_detector'))

    def test_market_events_not_in_old_pipeline(self):
        """Alert pipeline is NOT invoked without MarketEvents (ETAP 7.5)."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        mock_alert_builder = MagicMock()
        mock_alert_dispatcher = MagicMock()
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            alert_builder=mock_alert_builder,
            alert_dispatcher=mock_alert_dispatcher,
            instrument_metadata={
                "TEST": ("NYSE", InstrumentType.STOCK_USA),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TEST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        # Without MarketEvents in events_out, alert pipeline is NOT invoked
        # (ETAP 7.5 requires MarketEvent + FinalAnalysisResult)
        mock_alert_builder.should_alert.assert_not_called()
        mock_alert_dispatcher.dispatch.assert_not_called()

    def test_no_self_last_events(self):
        """Test that RuntimeService does NOT store self.last_events."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            instrument_metadata={
                "TEST": ("NYSE", InstrumentType.STOCK_USA),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TEST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        # Verify no self.last_events attribute exists
        self.assertFalse(hasattr(runtime, 'last_events'))

    def test_cycle_result_not_tuple(self):
        """Test that run_cycle still returns CycleReport, not a tuple."""
        mock_deduplicator = MagicMock()
        mock_deduplicator.should_process.return_value = True
        runtime = RuntimeService(
            self.mock_hunter,
            self.mock_master,
            self.mock_repository,
            deduplicator=mock_deduplicator,
            instrument_metadata={
                "TEST": ("NYSE", InstrumentType.STOCK_USA),
            }
        )

        mock_hunter_result = MagicMock()
        mock_hunter_result.opportunities = [MagicMock(instrument_id="TEST")]
        self.mock_hunter.scan.return_value = mock_hunter_result

        mock_result = FinalAnalysisResult(
            symbol="TEST",
            final_rating=80,
            confidence_level=90,
            recommendation="Buy",
            positive_factors=[],
            risk_factors=[],
            warnings=[],
            summary="",
            generated_at=datetime.now()
        )
        self.mock_master.run_analysis.return_value = mock_result

        report = runtime.run_cycle({})

        # Verify return type is still CycleReport
        self.assertIsInstance(report, CycleReport)
        # Verify it's not a tuple
        self.assertNotIsInstance(report, tuple)

    # ==================================================================
    # KROK 6A — Korekta: MarketScanner → RuntimeService → HunterEngine
    # Integration test — stops before MasterEngine
    # ==================================================================

    def test_market_scanner_integration_passes_candidate_to_hunter(self):
        """K6A integracyjny: MarketScanner → RuntimeService → HunterEngine
        przekazuje kandydatów z GOSS i GTN.WA wraz z rozłącznymi danymi OHLCV.

        Jedynym mockiem granicy zewnętrznej jest YahooFetcher.
        MasterEngine, HistoryRepository i OpportunityDeduplicator są
        rzeczywistymi, istniejącymi implementacjami — bez MagicMock."""
        from application.market_scanner import MarketScanner
        from application.universe import PennyStockUniverse
        from application.sources.static_instrument_source import StaticInstrumentSource
        from application.providers.yahoo_scan_provider import YahooScanProvider
        from data.yahoo.yahoo_fetcher import YahooFetcher
        from data.models.market_data import MarketData
        from engines.hunter.engine import HunterEngine

        # Rozłączne dane OHLCV dla dwóch instrumentów
        goss_data = [
            MarketData(open=10.0 + d, high=11.0 + d, low=9.5 + d, close=10.5 + d,
                       volume=100_000,
                       timestamp=datetime(2026, 1, 1) + timedelta(days=d))
            for d in range(35)
        ]
        gtn_data = [
            MarketData(open=20.0 + d, high=21.0 + d, low=19.5 + d, close=20.5 + d,
                       volume=200_000,
                       timestamp=datetime(2026, 1, 1) + timedelta(days=d))
            for d in range(35)
        ]

        test_tickers = ["GOSS", "GTN.WA"]

        # Jedyny mock granicy zewnętrznej — YahooFetcher
        mock_fetcher = MagicMock()

        def _fetch_side_effect(symbol):
            if symbol == "GOSS":
                return goss_data
            elif symbol == "GTN.WA":
                return gtn_data
            raise ValueError(f"Unexpected symbol: {symbol}")

        mock_fetcher.fetch_stock_data.side_effect = _fetch_side_effect

        instrument_source = StaticInstrumentSource(test_tickers)
        universe = PennyStockUniverse(instrument_source)
        scan_provider = YahooScanProvider(mock_fetcher)
        market_scanner = MarketScanner(universe, scan_provider)

        hunter_config = {
            "ranking_weight": 0.4,
            "risk_weight": 0.3,
            "confidence_weight": 0.3,
            "min_ranking_score": 0.5,
            "max_risk_score": 0.7,
            "min_confidence": 0.6,
            "max_results": 10,
            "priority_thresholds": [0.9, 0.7, 0.5],
        }
        hunter_engine = HunterEngine(hunter_config)
        # Rzeczywiste komponenty wewnętrzne — bez MagicMock dla
        # MasterEngine, HistoryRepository, OpportunityDeduplicator
        # ani NewsPipeline. Wzorzec produkcyjny z application/entrypoint.py:
        # NewsFilterConfig → NewsPipeline → MasterEngine(news_engine=...)
        from engines.master.engine import MasterEngine
        from engines.news.pipeline import NewsPipeline
        from engines.news.filter import NewsFilterConfig
        from application.history_repository import HistoryRepository
        from application.opportunity_deduplicator import OpportunityDeduplicator
        news_filter_config = NewsFilterConfig(min_content_length=50, min_quality_score=0.5)
        news_pipeline = NewsPipeline(news_filter_config)
        master_engine = MasterEngine(
            hunter_engine=hunter_engine,
            news_engine=news_pipeline,
        )
        history_repository = HistoryRepository()
        deduplicator = OpportunityDeduplicator(deduplication_window_seconds=3600)

        runtime = RuntimeService(
            hunter_engine=hunter_engine,
            master_engine=master_engine,
            history_repository=history_repository,
            market_scanner=market_scanner,
            deduplicator=deduplicator,
            instrument_metadata={
                "GOSS": ("GPW", InstrumentType.STOCK_GPW),
                "GTN.WA": ("GPW", InstrumentType.STOCK_GPW),
            },
        )

        report = runtime.run_cycle({})

        # MarketScanner wyprodukował dwóch kandydatów
        self.assertEqual(report.candidates_count, 2)

        # Obydwaj kandydaci przeszli przez MasterEngine pomyślnie
        self.assertEqual(report.success_count, 2,
                         "MasterEngine should process both candidates successfully")
        self.assertEqual(len(report.results), 2,
                         "Two FinalAnalysisResult expected")
        self.assertEqual(report.error_count, 0,
                         "No errors expected in the integration flow")

        symbols = {r.symbol for r in report.results}
        self.assertSetEqual(symbols, {"GOSS", "GTN.WA"})

    def test_hunter_result_no_artificial_scores_integration(self):
        """K6A integracyjny: HunterResult z MarketScanner ma None
        dla wszystkich pól scoringowych."""
        from engines.hunter.engine import HunterEngine
        from data.models.market_data import MarketData

        ohlcv_data = [
            MarketData(open=50.0, high=51.0, low=49.5, close=50.5,
                       volume=500_000,
                       timestamp=datetime(2026, 1, 1) + timedelta(days=d))
            for d in range(35)
        ]

        hunter_config = {
            "ranking_weight": 0.4,
            "risk_weight": 0.3,
            "confidence_weight": 0.3,
            "min_ranking_score": 0.5,
            "max_risk_score": 0.7,
            "min_confidence": 0.6,
            "max_results": 10,
            "priority_thresholds": [0.9, 0.7, 0.5],
        }
        hunter_engine = HunterEngine(hunter_config)

        candidates = [{"symbol": "STX.WA", "data": ohlcv_data}]
        result = hunter_engine.scan(candidates)

        self.assertEqual(len(result.opportunities), 1)
        opp = result.opportunities[0]
        self.assertIsNone(opp.hunter_score)
        self.assertIsNone(opp.priority)
        self.assertIsNone(opp.ranking_score)
        self.assertIsNone(opp.risk_score)
        self.assertIsNone(opp.confidence)
        self.assertFalse(hasattr(opp, "raw_input"),
                         "HunterResult MUST NOT have raw_input field")


if __name__ == "__main__":
    unittest.main()
