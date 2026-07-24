# Runtime module for ALCHEMIK
import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from data.models import MarketEvent, InstrumentType, MarketData
from data.models.final_analysis_result import FinalAnalysisResult
from .models import CycleReport, CandidateError
from .market_scanner import MarketScanner
from .history_repository import HistoryRepository
from .sqlite_history_repository import SQLiteHistoryRepository
from config import resolve_instrument_metadata

logger = logging.getLogger(__name__)


class RuntimeService:
    def __init__(self, hunter_engine, master_engine, history_repository: HistoryRepository, *, 
                 market_scanner: Optional[MarketScanner] = None, 
                 deduplicator=None,
                 alert_builder=None,
                 alert_dispatcher=None,
                 instrument_metadata: Optional[Dict[str, Tuple[str, InstrumentType]]] = None):
        self.hunter_engine = hunter_engine
        self.master_engine = master_engine
        self.history_repository = history_repository
        self.market_scanner = market_scanner
        self.deduplicator = deduplicator
        self.alert_builder = alert_builder
        self.alert_dispatcher = alert_dispatcher
        self._instrument_metadata = instrument_metadata

    def _get_instrument_metadata(self, ticker: str) -> Tuple[str, InstrumentType]:
        """
        Resolve market and instrument_type for a given ticker.

        Uses config.resolve_instrument_metadata, optionally with
        an override dict injected for testing.

        Args:
            ticker: Instrument symbol.

        Returns:
            Tuple of (market: str, instrument_type: InstrumentType).
        """
        return resolve_instrument_metadata(
            ticker,
            metadata=self._instrument_metadata,
        )

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
        all_detected_events: List[MarketEvent] = []
        
        try:
            # Step 1: Get candidates from MarketScanner or Hunter Engine
            ohlcv_map: Dict[str, List[MarketData]] = {}
            if self.market_scanner:
                candidates = self.market_scanner.scan()
                # Build symbol -> List[MarketData] mapping from scanner results
                for candidate in candidates:
                    if isinstance(candidate, dict):
                        sym = candidate.get('symbol')
                        data = candidate.get('data')
                        if sym and isinstance(data, list):
                            ohlcv_map[sym] = data
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
                
                # Resolve instrument metadata for this candidate
                market, instrument_type = self._get_instrument_metadata(
                    candidate.instrument_id
                )
                
                # Look up OHLCV data for this candidate from the scanner results
                candidate_ohlcv = ohlcv_map.get(candidate.instrument_id)

                # Process candidate through Master Engine
                # Collect detected events via a local list (no tuple, no self.last_events)
                detected_events: List[MarketEvent] = []
                try:
                    result = self.master_engine.run_analysis(
                        candidate.instrument_id,
                        market=market,
                        instrument_type=instrument_type,
                        events_out=detected_events,
                        ohlcv_data=candidate_ohlcv,
                    )
                    results.append(result)
                    success_count += 1

                    # Collect detected events for batch persistence
                    if detected_events:
                        all_detected_events.extend(detected_events)
                        logger.info(
                            "MarketEvent flow [%s]: %d event(s) detected on %s/%s",
                            candidate.instrument_id,
                            len(detected_events),
                            market,
                            instrument_type.value,
                        )
                        for ev in detected_events:
                            logger.info(
                                "  MarketEvent [%s]: type=%s, priority=%s",
                                ev.event_id,
                                ev.event_type,
                                ev.priority_raw.value if hasattr(ev.priority_raw, 'value') else ev.priority_raw,
                            )

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
        
        cycle_id = str(start_time.timestamp())
        try:
            self.history_repository.save_cycle(cycle_id, {
                'cycle_id': cycle_id,
                'execution_time': (report.end_time - report.start_time).total_seconds(),
                'candidates_count': report.candidates_count,
                'success_count': report.success_count,
                'error_count': report.error_count,
                'report': report
            })
        except Exception as e:
            logger.error("Failed to save cycle %s: %s", cycle_id, str(e), exc_info=True)
            report.error_count += 1
            report.errors.append(CandidateError(
                candidate_id=cycle_id,
                stage="HistoryRepository",
                message=str(e)
            ))

        # Persist MarketEvents if the repository supports it
        if hasattr(self.history_repository, 'save_market_events') and all_detected_events:
            try:
                events_data = [ev.to_dict() for ev in all_detected_events]
                self.history_repository.save_market_events(cycle_id, events_data)
                logger.info(
                    "Persisted %d MarketEvent(s) for cycle %s",
                    len(events_data),
                    cycle_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to persist MarketEvents for cycle %s: %s",
                    cycle_id,
                    str(e),
                    exc_info=True,
                )
                report.error_count += 1
                report.errors.append(CandidateError(
                    candidate_id=cycle_id,
                    stage="MarketEvent Storage",
                    message=str(e),
                ))
            
        return report
