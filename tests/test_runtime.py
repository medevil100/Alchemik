import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from application.runtime import RuntimeService
from application.models import CycleReport, CandidateError
from data.models.final_analysis_result import FinalAnalysisResult
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
        self.assertEqual(report.error_count, 0)

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
        self.mock_master.run_analysis.assert_called_once_with("A")
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
        
    def test_alert_pipeline_success(self):
        """Test successful alert pipeline execution."""
        mock_alert_builder = MagicMock()
        mock_alert_builder.should_alert.return_value = True
        mock_alert_builder.build_alert.return_value = "Test alert message"
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
        
        mock_alert_builder.should_alert.assert_called_once_with(mock_result)
        mock_alert_builder.build_alert.assert_called_once_with(mock_result)
        mock_alert_dispatcher.dispatch.assert_called_once_with("Test alert message")
        self.assertEqual(report.error_count, 0)
        
    def test_alert_pipeline_should_alert_false(self):
        """Test when should_alert returns False."""
        mock_alert_builder = MagicMock()
        mock_alert_builder.should_alert.return_value = False
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
        
        mock_alert_builder.should_alert.assert_called_once_with(mock_result)
        mock_alert_builder.build_alert.assert_not_called()
        mock_alert_dispatcher.dispatch.assert_not_called()
        self.assertEqual(report.error_count, 0)
        
    def test_alert_pipeline_no_alert_for_duplicate(self):
        """Test that no alert is built for duplicates."""
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
        
    def test_alert_pipeline_no_components(self):
        """Test runtime works without alert components."""
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
        
    def test_alert_pipeline_skip_on_master_error(self):
        """Test that alert pipeline is skipped when MasterEngine returns error."""
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
        
    def test_alert_builder_error_handling(self):
        """Test error handling when AlertBuilder fails."""
        mock_alert_builder = MagicMock()
        mock_alert_builder.should_alert.return_value = True
        mock_alert_builder.build_alert.side_effect = Exception("Builder error")
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
        
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.errors[0].stage, "Alert Builder")
        mock_alert_dispatcher.dispatch.assert_not_called()
        
    def test_alert_dispatcher_error_handling(self):
        """Test error handling when AlertDispatcher fails."""
        mock_alert_builder = MagicMock()
        mock_alert_builder.should_alert.return_value = True
        mock_alert_builder.build_alert.return_value = "Test alert message"
        mock_alert_dispatcher = MagicMock()
        mock_alert_dispatcher.dispatch.side_effect = Exception("Dispatcher error")
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
        
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.errors[0].stage, "Alert Dispatcher")

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
        self.mock_master.run_analysis.assert_called_once_with("B")
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

if __name__ == "__main__":
    unittest.main()
