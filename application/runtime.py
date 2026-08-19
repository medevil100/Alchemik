# Runtime module for ALCHEMIK
import functools
import logging
import uuid
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timezone
from data.models import MarketEvent, InstrumentType, MarketData
from data.models.final_analysis_result import FinalAnalysisResult
from data.models.instrument_reading import InstrumentReading
from data.models.instrument_observation import InstrumentObservation
from .models import CycleReport, CandidateError, CycleKind
from .market_scanner import MarketScanner
from .history_repository import HistoryRepository
from .sqlite_history_repository import SQLiteHistoryRepository
from .cycle_trace import (
    CycleTraceRecorder,
    SUCCESS,
    PARTIAL,
    FAILED,
    SKIPPED,
    NOT_STARTED,
    safe_error_type,
)
from engines.technical.errors import InsufficientDataError
from config import resolve_instrument_metadata

logger = logging.getLogger(__name__)


def _cycle_lock_guard(fn):
    """Addytywny dekorator: systemowa blokada pojedynczego cyklu (Krok 1/8).

    Pozyskuje blokadę PRZED jakimkolwiek efektem cyklu (CycleTraceRecorder,
    scanner.scan(), discovery, chart, zapisy SQLite, save_cycle) i zwalnia ją
    w finally — także przy wyjątku. Bez skonfigurowanej blokady (None)
    zachowuje niezmienione dotychczasowe zachowanie.
    """

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        lock = getattr(self, "_cycle_lock", None)
        if lock is None:
            return fn(self, *args, **kwargs)
        lock.acquire()
        try:
            return fn(self, *args, **kwargs)
        finally:
            lock.release()

    return wrapper


class RuntimeService:
    def __init__(self, hunter_engine, master_engine, history_repository: HistoryRepository, *,
                 market_scanner: Optional[MarketScanner] = None,
                 deduplicator=None,
                 alert_builder=None,
                 alert_dispatcher=None,
                 telegram_channel=None,
                 instrument_metadata: Optional[Dict[str, Tuple[str, InstrumentType]]] = None,
                 outcome_computer=None,
                 production_matrix_cycle: bool = False,
                 cycle_lock=None):
        self.hunter_engine = hunter_engine
        self.master_engine = master_engine
        self.history_repository = history_repository
        self.market_scanner = market_scanner
        self.deduplicator = deduplicator
        self.alert_builder = alert_builder
        self.alert_dispatcher = alert_dispatcher
        self.telegram_channel = telegram_channel
        self._instrument_metadata = instrument_metadata
        self.outcome_computer = outcome_computer
        # Krok 4/8: jawny tryb produkcyjnej matrycy. Domyślnie wyłączony —
        # zachowuje niezmienione istniejące zachowanie run_cycle().
        self.production_matrix_cycle = bool(production_matrix_cycle)
        # Krok 1/8: opcjonalna, międzyprocesowa blokada pojedynczego cyklu.
        # Produkcyjny composition root zawsze przekazuje rzeczywistą blokadę;
        # ręczne środowiska (testy) mogą jawnie działać bez blokady (None).
        self._cycle_lock = cycle_lock

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

    # ------------------------------------------------------------------
    # Ograniczona integracja Runtime → Observation (Kanon §14)
    # ------------------------------------------------------------------

    def restore_active_observations(self) -> list:
        """
        Jawne odtworzenie ACTIVE Observation wraz z ostatnim Readingiem.

        Wywoływane przez entrypoint przed pierwszym run_cycle().
        Deleguje do HistoryRepository.restore_active_observations().
        """
        if not hasattr(self.history_repository, 'restore_active_observations'):
            return []
        return self.history_repository.restore_active_observations()

    def _persist_observation_and_reading_full(
        self, instrument_id: str, ohlcv_data: List[MarketData]
    ):
        """Utrwala Observation i Reading i zwraca (result, reading, observation).

        Addytywny odpowiednik _persist_observation_and_reading używany przez
        produkcyjny cykl matrycy (Krok 4/8). Nie zmienia istniejącej metody.
        """
        if not ohlcv_data:
            return None, None, None
        if not hasattr(self.history_repository, 'save_reading'):
            return None, None, None

        latest = max(ohlcv_data, key=lambda md: md.timestamp)
        has_ohlc = (
            latest.open is not None
            and latest.high is not None
            and latest.low is not None
            and latest.close is not None
        )
        completeness = "COMPLETE" if has_ohlc else "PARTIAL"

        observation = None
        if hasattr(self.history_repository, 'load_observation'):
            observation = self.history_repository.load_observation(instrument_id)
        if observation is None:
            observation = InstrumentObservation(
                observation_id=str(uuid.uuid4()),
                instrument_id=instrument_id,
            )

        reading = InstrumentReading(
            reading_id=str(uuid.uuid4()),
            observation_id=observation.observation_id,
            instrument_id=instrument_id,
            market_data_timestamp=latest.timestamp,
            scan_timestamp=datetime.now(timezone.utc),
            open=latest.open,
            high=latest.high,
            low=latest.low,
            close=latest.close,
            volume=latest.volume,
            data_completeness=completeness,
        )
        result = self.history_repository.save_reading(observation, reading)
        if result == "ACCEPTED":
            return result, reading, observation
        active = self.history_repository.restore_active_observations()
        for obs, rdg in active:
            if rdg.instrument_id == instrument_id:
                return result, rdg, obs
        return result, None, None

    def _is_production_yahoo_discovery(self) -> bool:
        """Czy bieżące źródło uniwersum to produkcyjny YahooDiscoverySource."""
        scanner = self.market_scanner
        if scanner is None:
            return False
        universe = getattr(scanner, "_universe", None)
        source = getattr(universe, "_source", None)
        from application.sources.yahoo_discovery_source import YahooDiscoverySource
        return isinstance(source, YahooDiscoverySource)

    def _load_latest_readings_map(self) -> Dict[str, InstrumentReading]:
        """Mapa instrument_id → ostatni zaakceptowany Reading (stan trwały)."""
        result: Dict[str, InstrumentReading] = {}
        if not hasattr(self.history_repository, 'restore_active_observations'):
            return result
        for obs, rdg in self.history_repository.restore_active_observations():
            result[rdg.instrument_id] = rdg
        return result

    @staticmethod
    def _reading_market_fingerprint(reading: InstrumentReading) -> tuple:
        """Fingerprint treści rynkowej Readingu (7 pól kontraktu §12.2a)."""
        return (
            reading.open, reading.high, reading.low, reading.close,
            reading.volume, reading.data_completeness, reading.source,
        )

    def _build_universe_snapshot(
        self, symbols, chart_diags, readings_by_symbol, created_at_iso,
        daily_diags=None, intraday_diags=None,
    ):
        """Zbuduj UniverseSnapshot dla bieżącego cyklu.

        Krok 4/8 — daily_diags/intraday_diags rozdzielają jawnie diagnostykę
        daily (1y/1d) i intraday (5d/5m). Istniejące pola chart_status/
        candles_* pozostają aliasem daily (kompatybilność ze starszymi odczytami).
        """
        from data.models.universe_instrument import UniverseInstrument
        from data.models.universe_snapshot import UniverseSnapshot

        daily_diags = daily_diags or {}
        intraday_diags = intraday_diags or {}

        instruments = []
        now_iso = created_at_iso

        existing_by_symbol = {}
        if hasattr(self.history_repository, 'get_current_universe'):
            existing_by_symbol = {
                inst.symbol: inst
                for inst in self.history_repository.get_current_universe()
            }

        for sym in symbols:
            diag = chart_diags.get(sym, {})
            accepted = bool(diag.get("accepted"))
            chart_status = "SUCCESS" if accepted else "FAILED"
            candles_received = int(diag.get("raw_rows") or 0)
            candles_valid = int(diag.get("valid_rows") or 0)
            candles_rejected = int(diag.get("rejected_rows") or 0)
            rejection_reasons = dict(diag.get("rejection_reasons") or {})

            daily_diag = daily_diags.get(sym) or {}
            daily_status = (
                "SUCCESS" if bool(daily_diag.get("accepted")) else "FAILED"
            )
            intraday_diag = intraday_diags.get(sym) or {}
            intraday_status = (
                "SUCCESS" if bool(intraday_diag.get("accepted")) else "FAILED"
            )

            existing = existing_by_symbol.get(sym)
            baseline_status = None
            if existing is not None and existing.baseline_status:
                baseline_status = existing.baseline_status
            elif accepted:
                baseline_status = "PENDING_BASELINE"

            last_reading_id = None
            if existing is not None and existing.last_reading_id:
                last_reading_id = existing.last_reading_id
            if readings_by_symbol.get(sym):
                last_reading_id = readings_by_symbol[sym]

            # Instrument obecny w bieżącym discovery ma status ACTIVE.
            # Wcześniejszy MISSING_IN_CURRENT_SCAN jest nadpisywany (powrót).
            status = "ACTIVE"

            instruments.append(UniverseInstrument(
                symbol=sym,
                quote_type="EQUITY",
                exchange="WSE",
                market="pl_market",
                currency="PLN",
                regular_market_price=None,
                first_seen_at=existing.first_seen_at if existing else now_iso,
                last_seen_at=now_iso,
                status=status,
                chart_status=chart_status,
                candles_received=candles_received,
                candles_valid=candles_valid,
                candles_rejected=candles_rejected,
                rejection_reasons=rejection_reasons,
                daily_status=daily_status,
                daily_candles_received=int(daily_diag.get("raw_rows") or 0),
                daily_candles_valid=int(daily_diag.get("valid_rows") or 0),
                daily_candles_rejected=int(daily_diag.get("rejected_rows") or 0),
                daily_rejection_reasons=dict(daily_diag.get("rejection_reasons") or {}),
                intraday_status=intraday_status,
                intraday_candles_received=int(intraday_diag.get("raw_rows") or 0),
                intraday_candles_valid=int(intraday_diag.get("valid_rows") or 0),
                intraday_candles_rejected=int(intraday_diag.get("rejected_rows") or 0),
                intraday_rejection_reasons=dict(intraday_diag.get("rejection_reasons") or {}),
                baseline_status=baseline_status,
                last_reading_id=last_reading_id,
            ))
        return UniverseSnapshot.from_discovery(
            snapshot_id=str(uuid.uuid4()),
            created_at=now_iso,
            instruments=instruments,
        )

    # ------------------------------------------------------------------
    # Produkcyjny cykl matrycy (Krok 4/8)
    # ------------------------------------------------------------------

    def _run_production_cycle(self, start_time, recorder, cycle_id):
        """Produkcyjny cykl matrycy i porównań dla YahooDiscoverySource.

        Pierwszy cykl tworzy matrycę, Observation, Reading i baseline bez
        uruchamiania Huntera/MasterEngine/Tavily/AI/Telegrama. Kolejne cykle
        porównują nowe dane z ostatnim trwałym Readingiem.
        """
        errors: List = []
        results: List = []
        all_detected_events: List[MarketEvent] = []
        diagnostics = {
            "discovered": 0,
            "chart_ok": 0,
            "chart_error": 0,
            "baseline_created": 0,
            "readings_saved": 0,
            "unchanged": 0,
            "changed": 0,
            "skipped_downstream": 0,
            "errors": 0,
            "cycle_kind": None,
            "snapshot_symbols": 0,
            "saved_count": 0,
            "skipped_unchanged_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        }

        scanner = self.market_scanner
        universe = getattr(scanner, "_universe", None)
        discovery_source = getattr(universe, "_source", None)

        recorder.stage_start("discovery")
        recorder.stage_start("chart")
        recorder.stage_start("market_scan")

        try:
            candidates = scanner.scan()
        except Exception as exc:  # noqa: BLE001 — granica zewnętrzna
            recorder.stage_end("discovery", FAILED, reason=safe_error_type(exc))
            recorder.stage_end("chart", SKIPPED)
            recorder.stage_end("market_scan", SKIPPED)
            recorder.finalize_skipped_stages()
            diagnostics["cycle_kind"] = CycleKind.SOURCE_ERROR
            diagnostics["errors"] = 1
            diagnostics["trace"] = recorder.finish(
                data_flow_complete=False, overall_status=FAILED,
            )
            return CycleReport(
                start_time=start_time,
                end_time=datetime.now(),
                candidates_count=0, success_count=0, error_count=1,
                results=[], diagnostics=diagnostics,
                errors=[CandidateError(
                    candidate_id="N/A", stage="MarketScanner",
                    message=safe_error_type(exc),
                )],
            )

        discovery_meta = dict(getattr(discovery_source, "last_discovery", {}) or {})
        discovery_outcome = discovery_meta.get("outcome_kind")
        accepted_snapshot = dict(getattr(discovery_source, "accepted_snapshot", {}) or {})
        symbols = list(accepted_snapshot.keys())
        diagnostics["discovered"] = len(symbols)

        if discovery_outcome != "SUCCESS_WITH_DATA":
            recorder.stage_end("discovery", FAILED)
            recorder.stage_end("chart", SKIPPED)
            recorder.stage_end("market_scan", SKIPPED)
            recorder.finalize_skipped_stages()
            diagnostics["cycle_kind"] = CycleKind.SOURCE_ERROR
            diagnostics["trace"] = recorder.finish(
                data_flow_complete=False, overall_status=FAILED,
            )
            return CycleReport(
                start_time=start_time,
                end_time=datetime.now(),
                candidates_count=0, success_count=0, error_count=1,
                results=[], diagnostics=diagnostics,
                errors=[CandidateError(
                    candidate_id="N/A", stage="Discovery", message="SOURCE_ERROR",
                )],
            )

        recorder.stage_end("discovery", SUCCESS, output_count=len(symbols))

        chart_diags = self._chart_diagnostics()
        recorder.stage_end(
            "chart",
            PARTIAL if any(not d.get("accepted") for d in chart_diags.values()) else SUCCESS,
            output_count=len(chart_diags),
        )

        ohlcv_map: Dict[str, List[MarketData]] = {}
        for candidate in candidates:
            if isinstance(candidate, dict):
                sym = candidate.get('symbol')
                data = candidate.get('data')
                if sym and isinstance(data, list):
                    ohlcv_map[sym] = data

        # Krok 4/8 — intraday (5d/5m) per symbol: dokładnie 1 żądanie intraday
        # na symbol. Brak zamkniętej świecy intraday jest jawnym brakiem Readingu,
        # ale NIE usuwa daily ani instrumentu z matrycy.
        provider = getattr(scanner, "_provider", None)
        intraday_map: Dict[str, List[MarketData]] = {}
        intraday_diags: Dict[str, dict] = {}
        if hasattr(provider, "fetch_intraday"):
            intraday_result = provider.fetch_intraday(symbols)
            for sym, entry in intraday_result.items():
                intraday_map[sym] = entry.get("market_data") or []
                intraday_diags[sym] = entry.get("diag") or {}
        else:
            for sym in symbols:
                intraday_map[sym] = []
                intraday_diags[sym] = {}

        intraday_ok = 0
        intraday_error = 0
        for sym in symbols:
            if intraday_map.get(sym):
                intraday_ok += 1
                recorder.instrument_update(sym, intraday_status=SUCCESS)
            else:
                intraday_error += 1
                recorder.instrument_update(sym, intraday_status=FAILED)
        diagnostics["intraday_success"] = intraday_ok
        diagnostics["intraday_error"] = intraday_error

        for sym in symbols:
            diag = chart_diags.get(sym, {})
            accepted = bool(diag.get("accepted"))
            self._record_chart_for_instrument(
                recorder, sym, diag, ohlcv_map.get(sym, []),
            )
            recorder.instrument_update(sym, discovery_status=SUCCESS)
            if accepted:
                diagnostics["chart_ok"] += 1
                recorder.instrument_update(sym, chart_status=SUCCESS)
            else:
                diagnostics["chart_error"] += 1
                recorder.instrument_update(sym, chart_status=FAILED, final_status=FAILED)

        recorder.stage_end("market_scan", SUCCESS, output_count=len(chart_diags))

        has_previous_snapshot = False
        if hasattr(self.history_repository, 'get_latest_snapshot'):
            has_previous_snapshot = self.history_repository.get_latest_snapshot() is not None

        prev_readings = self._load_latest_readings_map()

        recorder.stage_start("observation")
        recorder.stage_start("reading_persistence")

        new_readings: Dict[str, InstrumentReading] = {}
        reading_results: Dict[str, Optional[str]] = {}
        baseline_created = 0
        readings_saved = 0
        unchanged = 0
        changed = 0
        changed_symbols: List[str] = []

        # Diagnosticę daily przekazujemy jawnie jako chart_diags (scan() = daily).
        daily_diags = chart_diags

        for sym in symbols:
            intraday_data = intraday_map.get(sym) or []
            if not intraday_data:
                # Brak zamkniętej świecy intraday — jawny brak bieżącego Readingu.
                # Instrument i daily pozostają w matrycy (nie jest to fałszywy baseline).
                reading_results[sym] = "NO_INTRADAY"
                recorder.instrument_update(
                    sym,
                    reading_status="NO_INTRADAY",
                    observation_status=SKIPPED,
                    final_status=SKIPPED,
                )
                diagnostics["skipped_downstream"] += 1
                continue
            result, reading, observation = self._persist_observation_and_reading_full(sym, intraday_data)
            reading_results[sym] = result
            recording_reading = reading
            if result != "ACCEPTED" and reading is None:
                stored = prev_readings.get(sym)
                if stored is not None:
                    recording_reading = stored
            if recording_reading is not None:
                new_readings[sym] = recording_reading
            if result == "ACCEPTED":
                readings_saved += 1
                recorder.instrument_update(sym, reading_status="ACCEPTED", observation_status=SUCCESS)
            elif result in ("DUPLICATE_NO_OP", "STALE_TIMESTAMP"):
                recorder.instrument_update(sym, reading_status=result, observation_status=SKIPPED)
            elif result == "CONFLICT":
                recorder.instrument_update(sym, reading_status="CONFLICT", observation_status=FAILED, final_status=FAILED)
                recorder.instrument_error_type(sym, "CONFLICT")
            else:
                recorder.instrument_update(sym, reading_status=result, observation_status=SUCCESS)

        diagnostics["readings_saved"] = readings_saved
        diagnostics["saved_count"] = readings_saved

        # Porównanie nowego odczytu z ostatnim trwałym Readingiem tego samego symbolu.
        for sym in symbols:
            data = ohlcv_map.get(sym)
            if data is None:
                continue
            new_reading = new_readings.get(sym)
            if new_reading is None:
                continue
            prev_reading = prev_readings.get(sym)
            if prev_reading is None:
                # Pierwszy poprawny Reading → baseline.
                baseline_created += 1
                recorder.instrument_update(sym, baseline_exists=True)
                if has_previous_snapshot:
                    recorder.instrument_update(sym, final_status=SKIPPED)
                    diagnostics["skipped_downstream"] += 1
                continue
            if prev_reading.reading_id == new_reading.reading_id:
                unchanged += 1
                recorder.instrument_update(sym, final_status=SKIPPED)
                diagnostics["skipped_downstream"] += 1
                continue
            prev_fp = self._reading_market_fingerprint(prev_reading)
            new_fp = self._reading_market_fingerprint(new_reading)
            if prev_fp == new_fp:
                unchanged += 1
                recorder.instrument_update(sym, final_status=SKIPPED)
                diagnostics["skipped_downstream"] += 1
            else:
                changed += 1
                changed_symbols.append(sym)
                recorder.instrument_update(sym, final_status=NOT_STARTED)

        diagnostics["baseline_created"] = baseline_created
        diagnostics["unchanged"] = unchanged
        diagnostics["changed"] = changed

        recorder.stage_end("observation", SUCCESS, output_count=len(symbols))
        recorder.stage_end(
            "reading_persistence",
            SUCCESS,
            input_count=len(symbols),
            accepted_count=readings_saved,
            skipped_count=unchanged,
            rejected_count=sum(1 for v in reading_results.values() if v == "CONFLICT"),
        )

        # Zapisz snapshot uniwersum (pełna matryca).
        if hasattr(self.history_repository, 'save_universe_snapshot'):
            last_reading_ids = {
                sym: new_readings[sym].reading_id for sym in new_readings
            }
            snapshot = self._build_universe_snapshot(
                symbols, chart_diags, last_reading_ids,
                datetime.now(timezone.utc).isoformat(),
                daily_diags=daily_diags,
                intraday_diags=intraday_diags,
            )
            diagnostics["snapshot_symbols"] = snapshot.unique_symbols
            self.history_repository.save_universe_snapshot(snapshot)

        cycle_kind = CycleKind.BASELINE_INITIALIZED if not has_previous_snapshot else CycleKind.SUBSEQUENT_CYCLE
        diagnostics["cycle_kind"] = cycle_kind
        diagnostics["errors"] = len(errors)

        # Routing do istniejących silników tylko dla zmienionych instrumentów.
        candidates_to_master: List = []
        if changed_symbols:
            changed_candidates = [
                {"symbol": sym, "data": ohlcv_map[sym]} for sym in changed_symbols
            ]
            recorder.stage_start("hunter")
            hunter_result = self.hunter_engine.scan(changed_candidates)
            recorder.stage_end(
                "hunter",
                SUCCESS,
                input_count=len(changed_candidates),
                output_count=len(hunter_result.opportunities),
            )

            for sym in changed_symbols:
                if sym in {o.instrument_id for o in hunter_result.opportunities}:
                    recorder.instrument_update(sym, hunter_status=SUCCESS)
                else:
                    recorder.instrument_update(sym, hunter_status=FAILED, final_status=FAILED)
            candidates_to_master = list(hunter_result.opportunities)

        # MasterEngine — pełna pętla istniejących silników dla zmienionych kandydatów.
        success_count = 0
        for candidate in candidates_to_master:
            if self.deduplicator is not None:
                try:
                    if not self.deduplicator.should_process(candidate.instrument_id):
                        recorder.instrument_update(candidate.instrument_id, final_status=SKIPPED)
                        continue
                except Exception as e:
                    errors.append(CandidateError(
                        candidate_id=candidate.instrument_id,
                        stage="Deduplicator",
                        message=str(e),
                    ))
                    recorder.instrument_error_type(candidate.instrument_id, safe_error_type(e))
                    continue
            else:
                continue

            market, instrument_type = self._get_instrument_metadata(candidate.instrument_id)
            candidate_ohlcv = ohlcv_map.get(candidate.instrument_id)
            detected_events: List[MarketEvent] = []
            try:
                recorder.stage_start("master")
                result = self.master_engine.run_analysis(
                    candidate.instrument_id,
                    market=market,
                    instrument_type=instrument_type,
                    events_out=detected_events,
                    ohlcv_data=candidate_ohlcv,
                    trace=recorder,
                )
                recorder.stage_end("master", SUCCESS, output_count=1)
                results.append(result)
                success_count += 1
                if detected_events:
                    all_detected_events.extend(detected_events)

                if not isinstance(result, Exception) and self.alert_builder and self.alert_dispatcher and detected_events:
                    for ev in detected_events:
                        ql_value = None
                        if hasattr(ev, 'quality_level') and ev.quality_level is not None:
                            ql_value = getattr(ev.quality_level, 'value', str(ev.quality_level))
                        if ql_value in ("IGNORE", "LOW", "ignore", "low"):
                            continue
                        try:
                            if self.alert_builder.should_alert(result, event=ev):
                                recorder.stage_start("alert_build")
                                alert_message = self.alert_builder.build_alert(result, event=ev)
                                recorder.stage_end("alert_build", SUCCESS, output_count=1)
                                recorder.instrument_update(candidate.instrument_id, alert_built=True)
                                try:
                                    channels = [self.telegram_channel] if self.telegram_channel else []
                                    recorder.stage_start("alert_dispatch")
                                    recorder.stage_start("telegram")
                                    report_dispatch = self.alert_dispatcher.dispatch(alert_message, channels)
                                    recorder.stage_end("alert_dispatch", SUCCESS, output_count=len(channels))
                                    if channels:
                                        recorder.bump_external("telegram_attempts", 1)
                                        recorder.instrument_update(candidate.instrument_id, telegram_attempted=1, telegram_sent=1)
                                    if report_dispatch is not None and getattr(report_dispatch, "success_count", 0) > 0:
                                        recorder.stage_end("telegram", SUCCESS)
                                        recorder.instrument_update(candidate.instrument_id, telegram_success=1)
                                    else:
                                        recorder.stage_end("telegram", FAILED)
                                except Exception as dispatch_err:
                                    recorder.stage_end("alert_dispatch", FAILED)
                                    recorder.stage_end("telegram", FAILED)
                                    recorder.instrument_error_type(candidate.instrument_id, safe_error_type(dispatch_err))
                        except Exception as build_err:
                            recorder.stage_end("alert_build", FAILED)
                            recorder.instrument_error_type(candidate.instrument_id, safe_error_type(build_err))
            except InsufficientDataError as e:
                errors.append(CandidateError(
                    candidate_id=candidate.instrument_id,
                    stage="Master Engine",
                    message=str(e),
                ))
                recorder.stage_end("master", FAILED, reason="InsufficientDataError")
                recorder.instrument_update(
                    candidate.instrument_id,
                    insufficient_data_error=True,
                    technical_status=FAILED,
                    master_status=FAILED,
                    final_status=FAILED,
                )
                recorder.instrument_error_type(candidate.instrument_id, "InsufficientDataError")
                continue
            except Exception as e:
                errors.append(CandidateError(
                    candidate_id=candidate.instrument_id,
                    stage="Master Engine",
                    message=str(e),
                ))
                recorder.stage_end("master", FAILED)
                recorder.instrument_update(
                    candidate.instrument_id,
                    master_status=FAILED,
                    final_status=FAILED,
                )
                recorder.instrument_error_type(candidate.instrument_id, safe_error_type(e))
                continue

            if self.deduplicator is not None and not isinstance(result, Exception):
                try:
                    self.deduplicator.mark_processed(candidate.instrument_id)
                except Exception as e:
                    recorder.instrument_error_type(candidate.instrument_id, safe_error_type(e))

        diagnostics["errors"] = len(errors)

        recorder.finalize_skipped_stages()
        trace = recorder.finish(
            data_flow_complete=success_count > 0 and len(errors) == 0,
            overall_status=SUCCESS if success_count > 0 and len(errors) == 0 else PARTIAL,
        )
        diagnostics["trace"] = trace

        report = CycleReport(
            start_time=start_time,
            end_time=datetime.now(),
            candidates_count=success_count,
            success_count=success_count,
            error_count=len(errors),
            results=results,
            errors=errors,
            diagnostics=diagnostics,
        )

        try:
            self.history_repository.save_cycle(cycle_id, {
                'cycle_id': cycle_id,
                'execution_time': (report.end_time - report.start_time).total_seconds(),
                'candidates_count': report.candidates_count,
                'success_count': report.success_count,
                'error_count': report.error_count,
                'report': report,
            })
        except Exception as e:
            logger.error("Failed to save cycle %s: %s", cycle_id, str(e), exc_info=True)
            report.error_count += 1
            report.errors.append(CandidateError(
                candidate_id=cycle_id,
                stage="HistoryRepository",
                message=str(e),
            ))

        if hasattr(self.history_repository, 'save_market_events') and all_detected_events:
            try:
                events_data = [ev.to_dict() for ev in all_detected_events]
                self.history_repository.save_market_events(cycle_id, events_data)
            except Exception as e:
                report.error_count += 1
                report.errors.append(CandidateError(
                    candidate_id=cycle_id,
                    stage="MarketEvent Storage",
                    message=str(e),
                ))

        return report

    def _persist_observation_and_reading(
        self, instrument_id: str, ohlcv_data: List[MarketData]
    ) -> Optional[str]:
        """
        Utrwala Observation i Reading przed przekazaniem do Market Huntera.

        Reguły (Kanon §14):
        - Wybiera jeden MarketData o największym market_data_timestamp
        - Tworzy jeden InstrumentReading z tego MarketData
        - Ładuje istniejącą ACTIVE Observation lub tworzy nową
        - Wywołuje save_reading(observation, reading) atomowo
        - Nie filtruje, nie triggeruje, nie zmienia dalszego przepływu
        - NO_DATA / pusta lista nie tworzy Observation
        """
        if not ohlcv_data:
            return

        if not hasattr(self.history_repository, 'save_reading'):
            return

        # Wybierz najnowszy MarketData
        latest = max(ohlcv_data, key=lambda md: md.timestamp)

        # Określ data_completeness
        has_ohlc = (
            latest.open is not None
            and latest.high is not None
            and latest.low is not None
            and latest.close is not None
        )
        completeness = "COMPLETE" if has_ohlc else "PARTIAL"

        # Załaduj istniejącą ACTIVE Observation lub utwórz nową
        observation = None
        if hasattr(self.history_repository, 'load_observation'):
            observation = self.history_repository.load_observation(instrument_id)

        if observation is None:
            observation = InstrumentObservation(
                observation_id=str(uuid.uuid4()),
                instrument_id=instrument_id,
            )

        # Zbuduj InstrumentReading
        reading = InstrumentReading(
            reading_id=str(uuid.uuid4()),
            observation_id=observation.observation_id,
            instrument_id=instrument_id,
            market_data_timestamp=latest.timestamp,
            scan_timestamp=datetime.now(timezone.utc),
            open=latest.open,
            high=latest.high,
            low=latest.low,
            close=latest.close,
            volume=latest.volume,
            data_completeness=completeness,
        )

        return self.history_repository.save_reading(observation, reading)

    # ------------------------------------------------------------------
    # Pomocnicze dla śladu cyklu (Punkt 6)
    # ------------------------------------------------------------------

    def _chart_diagnostics(self) -> Dict[str, dict]:
        """Zwróć bezpieczne diagnostyki chart per symbol (jeśli dostępne)."""
        provider = getattr(self.market_scanner, "_provider", None)
        last_scan = getattr(provider, "last_scan", None)
        if not isinstance(last_scan, list):
            return {}
        return {
            d.get("symbol"): d
            for d in last_scan
            if isinstance(d, dict) and d.get("symbol")
        }

    def _record_chart_for_instrument(self, recorder, symbol: str, diag: dict,
                                     market_data: Optional[List[MarketData]]) -> None:
        """Bezpiecznie zapisz status chart i snapshot najnowszego punktu."""
        accepted = bool(diag.get("accepted"))
        raw_rows = int(diag.get("raw_rows") or 0)
        valid_rows = int(diag.get("valid_rows") or 0)
        rejected_rows = int(diag.get("rejected_rows") or 0)
        rejection_reasons = dict(diag.get("rejection_reasons") or {})
        latest_raw_ts = diag.get("latest_raw_timestamp")
        latest_valid_ts = diag.get("latest_valid_timestamp")
        http_status = diag.get("http_status")
        error_kind = diag.get("error_kind") or "none"

        latest_price = None
        latest_volume = None
        latest_ts = None
        baseline_close = None
        change_vs_baseline = None

        if isinstance(market_data, list) and market_data:
            latest = market_data[-1]
            latest_price = latest.close
            latest_volume = latest.volume
            latest_ts = latest.timestamp.isoformat()
            baseline_close = market_data[0].close
            if baseline_close is not None and baseline_close != 0 and latest_price is not None:
                change_vs_baseline = round(
                    (latest_price - baseline_close) / baseline_close * 100.0, 4
                )

        recorder.instrument_update(
            symbol,
            chart_status=SUCCESS if accepted else FAILED,
            candles_received=raw_rows,
            candles_valid=valid_rows,
            candles_rejected=rejected_rows,
            rejection_reasons=rejection_reasons,
            latest_raw_timestamp=latest_raw_ts,
            latest_valid_timestamp=latest_valid_ts,
            http_status=http_status,
            error_kind=error_kind,
            current_price=latest_price,
            volume=latest_volume,
            latest_data_timestamp=latest_ts,
            baseline_close=baseline_close,
            change_vs_baseline_pct=change_vs_baseline,
        )

    # ------------------------------------------------------------------
    # CONTROLLED_E2E_VALIDATION (Punkt 7 — minimalny tryb jednorazowy)
    # ------------------------------------------------------------------
    # Addytywny, jednorazowy tryb walidacji E2E. NIE zmienia domyślnego
    # zachowania run_cycle(), NIE zmienia progów, NIE tworzy zdarzeń,
    # NIE podmienia providerów. Używa produkcyjnego Yahoo discovery,
    # zachowuje naturalną kolejność instrumentów i kończy się po jednym
    # potwierdzonym Telegramie.

    def run_controlled_e2e_validation(self) -> dict:
        """Wykonaj dokładnie jeden kontrolowany przebieg E2E (1 instrument).

        Returns:
            dict ze statusem, trace oraz licznikami zewnętrznymi:
              status: COMPLETE_E2E | NO_NATURAL_E2E_CANDIDATE | ERROR_*
              trace:  bezpieczny pełny ślad (sanitized)
              telegram_attempts / telegram_sent: liczniki wysyłki
        """
        from data.models.event_enums import InstrumentType as _InstrumentType

        recorder = CycleTraceRecorder()
        cycle_id = recorder.trace["cycle_id"]
        errors: List[str] = []
        selected_symbol: Optional[str] = None
        selected_result_id: Optional[str] = None
        selected_event_id: Optional[str] = None
        selected_alert_id: Optional[str] = None
        telegram_confirmed = False
        status = "NO_NATURAL_E2E_CANDIDATE"

        scanner = self.market_scanner
        provider = getattr(scanner, "_provider", None)
        universe = getattr(scanner, "_universe", None)
        discovery_source = getattr(universe, "_source", None)

        if provider is None or discovery_source is None:
            return {
                "status": "ERROR_YAHOO_DISCOVERY",
                "trace": recorder.finish(
                    data_flow_complete=False,
                    overall_status=FAILED,
                ),
                "telegram_attempts": 0,
                "telegram_sent": 0,
            }

        recorder.stage_start("discovery")
        recorder.stage_start("chart")
        recorder.stage_start("market_scan")

        try:
            discovery_source.get_instruments()
        except Exception as exc:  # noqa: BLE001 — granica zewnętrzna
            recorder.stage_end("discovery", FAILED, reason=safe_error_type(exc))
            recorder.stage_end("chart", SKIPPED)
            recorder.stage_end("market_scan", SKIPPED)
            recorder.finalize_skipped_stages()
            return {
                "status": "ERROR_YAHOO_DISCOVERY",
                "trace": recorder.finish(
                    data_flow_complete=False,
                    overall_status=FAILED,
                ),
                "telegram_attempts": 0,
                "telegram_sent": 0,
            }

        accepted_snapshot = dict(getattr(discovery_source, "accepted_snapshot", {}) or {})
        discovery_meta = dict(getattr(discovery_source, "last_discovery", {}) or {})
        recorder.stage_end(
            "discovery",
            SUCCESS if discovery_meta.get("outcome_kind") == "SUCCESS_WITH_DATA" else FAILED,
            output_count=len(accepted_snapshot),
        )

        if not accepted_snapshot:
            recorder.stage_end("chart", SKIPPED)
            recorder.stage_end("market_scan", SKIPPED)
            recorder.finalize_skipped_stages()
            return {
                "status": "ERROR_YAHOO_DISCOVERY",
                "trace": recorder.finish(
                    data_flow_complete=False,
                    overall_status=FAILED,
                ),
                "telegram_attempts": 0,
                "telegram_sent": 0,
            }

        # Przetwarzaj w naturalnej kolejności discovery (dict zachowuje kolejność).
        for symbol in accepted_snapshot:
            recorder.ensure_instrument(symbol)
            recorder.instrument_update(symbol, discovery_status=SUCCESS)
            try:
                raw_candidates = provider.scan([symbol])
            except Exception as exc:  # noqa: BLE001
                recorder.instrument_update(
                    symbol, chart_status=FAILED, final_status=FAILED
                )
                recorder.instrument_error_type(symbol, safe_error_type(exc))
                errors.append(safe_error_type(exc))
                continue

            diag = None
            for d in getattr(provider, "last_scan", []) or []:
                if isinstance(d, dict) and d.get("symbol") == symbol:
                    diag = d
                    break

            data_for_symbol = None
            for cand in raw_candidates:
                if isinstance(cand, dict) and cand.get("symbol") == symbol:
                    data_for_symbol = cand.get("data")
                    break

            if not data_for_symbol or not diag or not diag.get("accepted"):
                self._record_chart_for_instrument(recorder, symbol, diag or {}, data_for_symbol)
                recorder.instrument_update(
                    symbol, chart_status=FAILED, final_status=FAILED
                )
                continue

            self._record_chart_for_instrument(recorder, symbol, diag, data_for_symbol)

            # Persistencja Reading/Observation.
            persist_result = self._persist_observation_and_reading(symbol, data_for_symbol)
            if persist_result != "ACCEPTED":
                recorder.instrument_update(
                    symbol,
                    observation_status=SKIPPED,
                    reading_status=persist_result,
                    final_status=SKIPPED,
                )
                continue
            recorder.instrument_update(
                symbol, observation_status=SUCCESS, reading_status=persist_result
            )

            # Hunter pass-through (produkcyjne zachowanie).
            hunt = self.hunter_engine.scan([{"symbol": symbol, "data": data_for_symbol}])
            if not hunt.opportunities:
                recorder.instrument_update(symbol, hunter_status=FAILED, final_status=FAILED)
                continue
            recorder.instrument_update(symbol, hunter_status=SUCCESS)

            # MasterEngine — pełna pętla silników dla tego jednego instrumentu.
            detected_events: List[MarketEvent] = []
            try:
                result = self.master_engine.run_analysis(
                    symbol,
                    market="GPW",
                    instrument_type=_InstrumentType.STOCK_GPW,
                    events_out=detected_events,
                    ohlcv_data=data_for_symbol,
                    trace=recorder,
                )
            except InsufficientDataError as exc:
                recorder.instrument_update(
                    symbol,
                    insufficient_data_error=True,
                    technical_status=FAILED,
                    master_status=FAILED,
                    final_status=FAILED,
                )
                recorder.instrument_error_type(symbol, "InsufficientDataError")
                errors.append("InsufficientDataError")
                continue
            except Exception as exc:  # noqa: BLE001
                recorder.instrument_update(
                    symbol,
                    master_status=FAILED,
                    final_status=FAILED,
                )
                recorder.instrument_error_type(symbol, safe_error_type(exc))
                errors.append(safe_error_type(exc))
                continue

            if result is not None:
                selected_result_id = getattr(result, "symbol", symbol)
                recorder.instrument_update(
                    symbol,
                    final_result_id=selected_result_id,
                    master_status=SUCCESS,
                    final_result_created=True,
                )

            # Alert + Telegram — wyłącznie naturalna decyzja produkcyjnego AlertBuildera.
            telegram_attempted_for_instrument = 0
            for ev in (detected_events or []):
                ql_value = None
                if hasattr(ev, "quality_level") and ev.quality_level is not None:
                    ql_value = getattr(ev.quality_level, "value", str(ev.quality_level))
                if ql_value in ("IGNORE", "LOW", "ignore", "low"):
                    continue
                if self.alert_builder is None or not self.alert_builder.should_alert(result, event=ev):
                    continue

                try:
                    alert_message = self.alert_builder.build_alert(result, event=ev)
                except Exception as exc:  # noqa: BLE001
                    recorder.instrument_error_type(symbol, safe_error_type(exc))
                    errors.append(safe_error_type(exc))
                    continue

                # Adnotacja trybu jednorazowej walidacji — wyłącznie informacyjna,
                # nie zmienia treści wyników domenowych.
                alert_message.formatted_message = (
                    "ALCHEMIK — CONTROLLED_E2E_VALIDATION\n\n"
                    + alert_message.formatted_message
                )

                selected_event_id = getattr(ev, "event_id", None)
                selected_alert_id = alert_message.alert_id
                recorder.instrument_update(
                    symbol,
                    events_count=len(detected_events),
                    event_id=selected_event_id,
                    alert_id=selected_alert_id,
                    alert_built=True,
                )

                if self.telegram_channel is None:
                    continue

                recorder.stage_start("alert_build")
                recorder.stage_end("alert_build", SUCCESS, output_count=1)
                recorder.stage_start("alert_dispatch")
                recorder.stage_start("telegram")
                try:
                    report_dispatch = self.alert_dispatcher.dispatch(
                        alert_message, [self.telegram_channel]
                    )
                    telegram_attempted_for_instrument += 1
                    recorder.bump_external("telegram_attempts", 1)
                    recorder.instrument_update(
                        symbol, telegram_attempted=telegram_attempted_for_instrument
                    )
                except Exception as exc:  # noqa: BLE001
                    recorder.stage_end("alert_dispatch", FAILED)
                    recorder.stage_end("telegram", FAILED)
                    recorder.instrument_error_type(symbol, safe_error_type(exc))
                    errors.append(safe_error_type(exc))
                    continue

                if report_dispatch is not None and getattr(report_dispatch, "success_count", 0) > 0:
                    recorder.stage_end("alert_dispatch", SUCCESS, output_count=1)
                    recorder.stage_end("telegram", SUCCESS)
                    telegram_confirmed = True
                    recorder.instrument_update(
                        symbol,
                        telegram_sent=1,
                        telegram_success=1,
                        final_status=SUCCESS,
                    )
                    break
                else:
                    recorder.stage_end("alert_dispatch", FAILED)
                    recorder.stage_end("telegram", FAILED)

            if telegram_confirmed:
                status = "COMPLETE_E2E"
                break

        recorder.stage_end("market_scan", SUCCESS, output_count=len(accepted_snapshot))
        recorder.stage_end("chart", SUCCESS if status == "COMPLETE_E2E" else PARTIAL)

        # Liczniki zewnętrzne — Yahoo (rzeczywiste wywołania z transportu, jeżeli dostępne).
        session = getattr(provider, "_session", None)
        transport = getattr(session, "_transport", None) if session is not None else None
        if transport is not None:
            recorder.set_external("yahoo_attempts", int(getattr(transport, "request_count", 0)))
            recorder.set_external("yahoo_real_sent", int(getattr(transport, "request_count", 0)))

        # Zawsze zapisz cykl (tylko raz, jeden proces).
        try:
            self.history_repository.save_cycle(cycle_id, {
                "cycle_id": cycle_id,
                "execution_time": 0.0,
                "candidates_count": 1 if telegram_confirmed else 0,
                "success_count": 1 if telegram_confirmed else 0,
                "error_count": len(errors),
                "report": {"status": status, "errors": errors},
            })
        except Exception:  # noqa: BLE001 — zapis cyklu nie może przerwać wyniku
            pass

        data_flow_complete = bool(telegram_confirmed)
        recorder.finalize_skipped_stages()
        trace = recorder.finish(
            data_flow_complete=data_flow_complete,
            overall_status=SUCCESS if telegram_confirmed else FAILED,
        )
        return {
            "status": status,
            "trace": trace,
            "telegram_attempts": trace["external_calls"]["telegram_attempts"],
            "telegram_sent": 1 if telegram_confirmed else 0,
            "symbol": selected_symbol,
            "final_result_id": selected_result_id,
            "event_id": selected_event_id,
            "alert_id": selected_alert_id,
            "errors": errors,
        }

    @_cycle_lock_guard
    def run_cycle(self, input_data: Optional[dict] = None) -> CycleReport:
        """Execute one cycle of the ALCHEMIK runtime.

        Args:
            input_data: Optional input data for the Hunter Engine.

        Returns:
            CycleReport: A report of the cycle execution.
        """
        start_time = datetime.now()
        errors = []
        results = []
        all_detected_events: List[MarketEvent] = []
        diagnostics = {
            "accepted_count": 0,
            "saved_count": 0,
            "skipped_unchanged_count": 0,
            "rejected_count": 0,
        }
        recorder = CycleTraceRecorder()
        cycle_id = recorder.trace["cycle_id"]

        if self.production_matrix_cycle and self._is_production_yahoo_discovery():
            return self._run_production_cycle(start_time, recorder, cycle_id)

        try:
            # Step 1: Get candidates from MarketScanner or Hunter Engine
            ohlcv_map: Dict[str, List[MarketData]] = {}
            candidates = []
            if self.market_scanner:
                recorder.stage_start("discovery")
                recorder.stage_start("chart")
                recorder.stage_start("market_scan")
                candidates = self.market_scanner.scan()
                recorder.stage_end("discovery", SUCCESS, output_count=len(candidates))

                chart_diags = self._chart_diagnostics()
                recorder.stage_end(
                    "chart",
                    PARTIAL if any(not d.get("accepted") for d in chart_diags.values()) else SUCCESS,
                    output_count=len(chart_diags),
                )

                diagnostics["accepted_count"] = len(candidates)
                # Build symbol -> List[MarketData] mapping from scanner results
                for candidate in candidates:
                    if isinstance(candidate, dict):
                        sym = candidate.get('symbol')
                        data = candidate.get('data')
                        if sym and isinstance(data, list):
                            ohlcv_map[sym] = data

                recorder.stage_end("market_scan", SUCCESS, output_count=len(ohlcv_map))

                # Zarejestruj instrumenty odrzucone na granicy chart, aby błąd
                # chart był jawnie widoczny per instrument (pkt 8 zadania),
                # nie usuwając poprawnych instrumentów.
                for sym, diag in chart_diags.items():
                    if sym in ohlcv_map:
                        continue
                    self._record_chart_for_instrument(recorder, sym, diag, [])
                    recorder.instrument_update(
                        sym,
                        discovery_status=SUCCESS,
                        chart_status=FAILED,
                        final_status=FAILED,
                    )

                # --- Ograniczona integracja: utrwal Observation przed Market Hunterem ---
                # Iteruj po surowych kandydatach MarketScanner, nie po
                # hunter_result.opportunities. Persistencja musi zajść
                # strukturalnie przed hunter_engine.scan(candidates).
                recorder.stage_start("observation")
                recorder.stage_start("reading_persistence")

                persist_results: Dict[str, Optional[str]] = {}
                for candidate in candidates:
                    if isinstance(candidate, dict):
                        sym = candidate.get('symbol')
                        data = ohlcv_map.get(sym)
                        if sym and data is not None:
                            persist_results[sym] = None
                            result = self._persist_observation_and_reading(sym, data)
                            if result is not None:
                                persist_results[sym] = result

                            # Ślad per instrument: discovery + chart + Observation.
                            diag = chart_diags.get(sym, {})
                            self._record_chart_for_instrument(
                                recorder, sym, diag, data
                            )
                            recorder.instrument_update(
                                sym,
                                discovery_status=SUCCESS,
                                reading_status=result,
                            )

                            if result == "ACCEPTED":
                                observation = self.history_repository.load_observation(sym)
                                if observation is not None:
                                    recorder.instrument_update(
                                        sym,
                                        observation_status=SUCCESS,
                                        baseline_exists=True,
                                    )
                                else:
                                    recorder.instrument_update(sym, observation_status=SUCCESS)
                            elif result in ("DUPLICATE_NO_OP", "STALE_TIMESTAMP"):
                                recorder.instrument_update(
                                    sym,
                                    observation_status=SKIPPED,
                                    final_status=SKIPPED,
                                )
                                recorder.stage_count_bump(
                                    "reading_persistence", "skipped_count", 1
                                )
                            elif result == "CONFLICT":
                                recorder.instrument_update(
                                    sym,
                                    observation_status=FAILED,
                                    reading_status=result,
                                    final_status=FAILED,
                                )
                                recorder.stage_count_bump(
                                    "reading_persistence", "error_count", 1
                                )
                                recorder.instrument_error_type(sym, "CONFLICT")

                diagnostics["saved_count"] = sum(
                    1 for v in persist_results.values() if v == "ACCEPTED"
                )
                diagnostics["skipped_unchanged_count"] = sum(
                    1 for v in persist_results.values()
                    if v in ("DUPLICATE_NO_OP", "STALE_TIMESTAMP")
                )

                recorder.stage_end("observation", SUCCESS, output_count=len(persist_results))
                recorder.stage_end(
                    "reading_persistence",
                    SUCCESS,
                    input_count=len(persist_results),
                    accepted_count=diagnostics["saved_count"],
                    skipped_count=diagnostics["skipped_unchanged_count"],
                    rejected_count=sum(
                        1 for v in persist_results.values() if v == "CONFLICT"
                    ),
                )

                # Brak zmiany danych (DUPLICATE_NO_OP / STALE_TIMESTAMP) nie może
                # uruchamiać dalszego przetwarzania wymagającego zmiany.
                candidates_to_hunt = [
                    c for c in candidates
                    if not isinstance(c, dict)
                    or persist_results.get(c.get('symbol')) == "ACCEPTED"
                ]

                recorder.stage_start("hunter")
                hunter_result = self.hunter_engine.scan(candidates_to_hunt)
                recorder.stage_end(
                    "hunter",
                    SUCCESS,
                    input_count=len(candidates_to_hunt),
                    output_count=len(hunter_result.opportunities),
                    rejected_count=getattr(hunter_result, "rejected", 0),
                )
            else:
                recorder.stage_start("hunter")
                hunter_result = self.hunter_engine.scan(input_data or {})
                recorder.stage_end(
                    "hunter",
                    SUCCESS,
                    input_count=len(input_data) if input_data else 0,
                    output_count=len(hunter_result.opportunities),
                )

            diagnostics["rejected_count"] = getattr(hunter_result, "rejected", 0)
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
                        recorder.instrument_error_type(candidate.instrument_id, safe_error_type(e))
                        recorder.add_error(
                            "deduplication", candidate.instrument_id, safe_error_type(e), str(e)
                        )
                        continue
                else:
                    continue  # Skip deduplication if no deduplicator is provided

                # Resolve instrument metadata for this candidate
                market, instrument_type = self._get_instrument_metadata(
                    candidate.instrument_id
                )

                # Look up OHLCV data for this candidate from the scanner results
                candidate_ohlcv = ohlcv_map.get(candidate.instrument_id)

                # Uzupełnij ślad: dane chart/Hunter dla instrumentu, który
                # dotarł do MasterEngine.
                recorder.ensure_instrument(candidate.instrument_id)
                recorder.instrument_update(candidate.instrument_id, hunter_status=SUCCESS)

                # Process candidate through Master Engine
                # Collect detected events via a local list (no tuple, no self.last_events)
                detected_events: List[MarketEvent] = []
                try:
                    recorder.stage_start("master")
                    result = self.master_engine.run_analysis(
                        candidate.instrument_id,
                        market=market,
                        instrument_type=instrument_type,
                        events_out=detected_events,
                        ohlcv_data=candidate_ohlcv,
                        trace=recorder,
                    )
                    recorder.stage_end("master", SUCCESS, output_count=1)
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

                    # Process alerts if alert components are available and no MasterEngine errors.
                    if not isinstance(result, Exception) and self.alert_builder and self.alert_dispatcher and detected_events:
                        for ev in detected_events:
                            ql_value = None
                            if hasattr(ev, 'quality_level') and ev.quality_level is not None:
                                ql_value = getattr(ev.quality_level, 'value', str(ev.quality_level))

                            if ql_value in ("IGNORE", "LOW", "ignore", "low"):
                                continue

                            try:
                                if self.alert_builder.should_alert(result, event=ev):
                                    recorder.stage_start("alert_build")
                                    alert_message = self.alert_builder.build_alert(result, event=ev)
                                    recorder.stage_end("alert_build", SUCCESS, output_count=1)
                                    recorder.ensure_instrument(candidate.instrument_id)
                                    recorder.instrument_update(candidate.instrument_id, alert_built=True)
                                    try:
                                        channels = [self.telegram_channel] if self.telegram_channel else []
                                        recorder.stage_start("alert_dispatch")
                                        recorder.stage_start("telegram")
                                        report_dispatch = self.alert_dispatcher.dispatch(alert_message, channels)
                                        recorder.stage_end("alert_dispatch", SUCCESS, output_count=len(channels))
                                        if channels:
                                            recorder.bump_external("telegram_attempts", 1)
                                            recorder.instrument_update(
                                                candidate.instrument_id,
                                                telegram_attempted=1,
                                                telegram_sent=1,
                                            )
                                        if report_dispatch is not None and getattr(report_dispatch, "success_count", 0) > 0:
                                            recorder.stage_end("telegram", SUCCESS)
                                            recorder.instrument_update(candidate.instrument_id, telegram_success=1)
                                        else:
                                            recorder.stage_end("telegram", FAILED)
                                    except Exception as dispatch_err:
                                        logger.warning(
                                            "Alert dispatch failed for %s: %s",
                                            candidate.instrument_id, str(dispatch_err),
                                        )
                                        recorder.stage_end("alert_dispatch", FAILED)
                                        recorder.stage_end("telegram", FAILED)
                                        recorder.instrument_error_type(candidate.instrument_id, safe_error_type(dispatch_err))
                                        recorder.add_error("telegram", candidate.instrument_id, safe_error_type(dispatch_err), str(dispatch_err))
                            except Exception as build_err:
                                logger.warning(
                                    "Alert builder failed for %s: %s",
                                    candidate.instrument_id, str(build_err),
                                )
                                recorder.stage_end("alert_build", FAILED)
                                recorder.instrument_error_type(candidate.instrument_id, safe_error_type(build_err))
                                recorder.add_error("alert_build", candidate.instrument_id, safe_error_type(build_err), str(build_err))

                except InsufficientDataError as e:
                    errors.append(CandidateError(
                        candidate_id=candidate.instrument_id,
                        stage="Master Engine",
                        message=str(e)
                    ))
                    recorder.stage_end("master", FAILED, reason="InsufficientDataError")
                    recorder.instrument_update(
                        candidate.instrument_id,
                        insufficient_data_error=True,
                        technical_status=FAILED,
                        master_status=FAILED,
                        final_status=FAILED,
                    )
                    recorder.instrument_error_type(candidate.instrument_id, "InsufficientDataError")
                    recorder.add_error("technical", candidate.instrument_id, "InsufficientDataError", str(e))
                    continue
                except Exception as e:
                    errors.append(CandidateError(
                        candidate_id=candidate.instrument_id,
                        stage="Master Engine",
                        message=str(e)
                    ))
                    recorder.stage_end("master", FAILED)
                    recorder.instrument_update(
                        candidate.instrument_id,
                        master_status=FAILED,
                        final_status=FAILED,
                    )
                    recorder.instrument_error_type(candidate.instrument_id, safe_error_type(e))
                    recorder.add_error("master", candidate.instrument_id, safe_error_type(e), str(e))
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
                        recorder.instrument_error_type(candidate.instrument_id, safe_error_type(e))

            data_flow_complete = (
                success_count > 0
                and len(errors) == 0
                and all(
                    e.get("final_status") == SUCCESS
                    for e in recorder.trace["instruments"].values()
                )
            )
            if not recorder.trace["instruments"]:
                overall_status = FAILED
            elif all(
                e.get("final_status") == SUCCESS
                for e in recorder.trace["instruments"].values()
            ):
                overall_status = SUCCESS
            elif any(
                e.get("final_status") == FAILED
                for e in recorder.trace["instruments"].values()
            ) and not any(
                e.get("final_status") == SUCCESS
                for e in recorder.trace["instruments"].values()
            ):
                overall_status = FAILED
            else:
                overall_status = PARTIAL

        except Exception as e:
            recorder.stage_end("discovery", FAILED)
            recorder.stage_end("chart", FAILED)
            recorder.stage_end("market_scan", FAILED)
            recorder.stage_end("observation", FAILED)
            recorder.stage_end("reading_persistence", FAILED)
            recorder.stage_end("hunter", FAILED)
            recorder.finalize_skipped_stages()
            trace = recorder.finish(data_flow_complete=False, overall_status=FAILED)
            diagnostics["trace"] = trace
            return CycleReport(
                start_time=start_time,
                end_time=datetime.now(),
                candidates_count=0,
                success_count=0,
                error_count=1,
                results=[],
                diagnostics=diagnostics,
                errors=[CandidateError(
                    candidate_id="N/A",
                    stage="MarketScanner" if self.market_scanner else "Hunter Engine",
                    message=str(e)
                )]
            )

        recorder.finalize_skipped_stages()
        trace = recorder.finish(
            data_flow_complete=data_flow_complete,
            overall_status=overall_status,
        )
        diagnostics["trace"] = trace

        report = CycleReport(
            start_time=start_time,
            end_time=datetime.now(),
            candidates_count=candidates_count,
            success_count=success_count,
            error_count=len(errors),
            results=results,
            errors=errors,
            diagnostics=diagnostics
        )

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

        # Outcome: initialize new events (best-effort, after MarketEvent persistence)
        if self.outcome_computer is not None:
            try:
                new_outcomes = self.outcome_computer.initialize_new_events()
                if new_outcomes:
                    logger.info(
                        "OutcomeComputer: %d new EventOutcome(s) initialized",
                        len(new_outcomes),
                    )
            except Exception as e:
                logger.error("OutcomeComputer.initialize_new_events() failed: %s", e, exc_info=True)
                report.error_count += 1
                report.errors.append(CandidateError(
                    candidate_id=cycle_id,
                    stage="OutcomeComputer.initialize_new_events",
                    message=str(e),
                ))

        # Outcome: compute pending horizons (best-effort, independent of initialization)
        if self.outcome_computer is not None:
            try:
                updated = self.outcome_computer.compute_pending_horizons()
                if updated > 0:
                    logger.info(
                        "OutcomeComputer: %d SessionOutcome(s) updated",
                        updated,
                    )
            except Exception as e:
                logger.error("OutcomeComputer.compute_pending_horizons() failed: %s", e, exc_info=True)
                report.error_count += 1
                report.errors.append(CandidateError(
                    candidate_id=cycle_id,
                    stage="OutcomeComputer.compute_pending_horizons",
                    message=str(e),
                ))

        return report
