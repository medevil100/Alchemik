# Runtime module for ALCHEMIK
from typing import List, Optional
from datetime import datetime
from data.models.final_analysis_result import FinalAnalysisResult
from .models import CycleReport, CandidateError
from .market_scanner import MarketScanner
from .history_repository import HistoryRepository

class RuntimeService:
    def __init__(self, hunter_engine, master_engine, history_repository: HistoryRepository, *, 
                 market_scanner: Optional[MarketScanner] = None, 
                 deduplicator=None,
                 alert_builder=None,
                 alert_dispatcher=None):
        self.hunter_engine = hunter_engine
        self.master_engine = master_engine
        self.history_repository = history_repository
        self.market_scanner = market_scanner
        self.deduplicator = deduplicator
        self.alert_builder = alert_builder
        self.alert_dispatcher = alert_dispatcher

    def run_cycle(self, input_data: Optional[dict] = None) -> CycleReport:
        """
        Execute one cycle of the ALCHEMIK runtime.
        
        Args:
            input_data: Optional input data for the Hunter Engine.
        
        Returns:
            CycleReport: A report of the cycle execution.
        """
        start_time = datetime.now()
        errors = []
        results = []
        
        try:
            # Step 1: Get candidates from MarketScanner or Hunter Engine
            if self.market_scanner:
                candidates = self.market_scanner.scan()
                hunter_result = self.hunter_engine.scan(candidates)
            else:
                hunter_result = self.hunter_engine.scan(input_data or {})
            
            candidates_count = len(hunter_result.opportunities)
            
            # Step 2: Process each candidate through Master Engine
            success_count = 0
            for candidate in hunter_result.opportunities:
                # Skip duplicates (handle deduplicator exceptions gracefully)
                if self.deduplicator is not None:
                    try:
                        if not self.deduplicator.should_process(candidate.instrument_id):
                            continue
                    except Exception as e:
                        errors.append(CandidateError(
                            candidate_id=candidate.instrument_id,
                            stage="Deduplicator",
                            message=str(e)
                        ))
                        continue
                else:
                    continue  # Skip deduplication if no deduplicator is provided
                
                # Process candidate through Master Engine
                try:
                    result = self.master_engine.run_analysis(candidate.instrument_id)
                    results.append(result)
                    success_count += 1

                    # Process alerts if alert components are available and no MasterEngine errors
                    if not isinstance(result, Exception) and self.alert_builder and self.alert_dispatcher:
                        try:
                            if self.alert_builder.should_alert(result):
                                try:
                                    alert_message = self.alert_builder.build_alert(result)
                                    try:
                                        self.alert_dispatcher.dispatch(alert_message)
                                    except Exception as e:
                                        errors.append(CandidateError(
                                            candidate_id=candidate.instrument_id,
                                            stage="Alert Dispatcher",
                                            message=str(e)
                                        ))
                                except Exception as e:
                                    errors.append(CandidateError(
                                        candidate_id=candidate.instrument_id,
                                        stage="Alert Builder",
                                        message=str(e)
                                    ))
                        except Exception as e:
                            errors.append(CandidateError(
                                candidate_id=candidate.instrument_id,
                                stage="Alert Pipeline",
                                message=str(e)
                            ))

                except Exception as e:
                    errors.append(CandidateError(
                        candidate_id=candidate.instrument_id,
                        stage="Master Engine",
                        message=str(e)
                    ))
                    continue
                
                # Mark as processed if deduplicator is provided
                if self.deduplicator is not None and not isinstance(result, Exception):
                    try:
                        self.deduplicator.mark_processed(candidate.instrument_id)
                    except Exception as e:
                        errors.append(CandidateError(
                            candidate_id=candidate.instrument_id,
                            stage="Deduplicator",
                            message=str(e)
                        ))

        except Exception as e:
            return CycleReport(
                start_time=start_time,
                end_time=datetime.now(),
                candidates_count=0,
                success_count=0,
                error_count=1,
                results=[],
                errors=[CandidateError(
                    candidate_id="N/A",
                    stage="MarketScanner" if self.market_scanner else "Hunter Engine",
                    message=str(e)
                )]
            )

        report = CycleReport(
            start_time=start_time,
            end_time=datetime.now(),
            candidates_count=candidates_count,
            success_count=success_count,
            error_count=len(errors),
            results=results,
            errors=errors
        )
        
        try:
            self.history_repository.save_cycle(str(start_time.timestamp()), {
                'cycle_id': str(start_time.timestamp()),
                'execution_time': (report.end_time - report.start_time).total_seconds(),
                'candidates_count': report.candidates_count,
                'success_count': report.success_count,
                'error_count': report.error_count,
                'report': report
            })
        except Exception as e:
            # Log the error but don't fail the cycle
            pass
            
        return report
