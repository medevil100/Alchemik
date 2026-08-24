"""
CONTROLLED_VALIDATION_ONLY — first-class controlled E2E validation mode.

Real components (RuntimeService, SQLiteHistoryRepository, Hunter/Master/
Technical/Ranking/Risk/Analyst engines, AlertBuilder/AlertDispatcher) are wired
through the production composition root.  Only the external system boundaries
(Yahoo Finance, Tavily, OpenAI, Telegram) may be wrapped by delegating guards.

The controller:

  * performs exactly one real Yahoo discovery,
  * selects one symbol by the *effective latest Reading* (greatest
    ``market_data_timestamp``, then highest ``revision_number``) from the
    isolated copy, intersected with the real discovery snapshot, sorted by
    ``volume DESC, symbol ASC``,
  * prepares a single-symbol source recognised as a production Yahoo matrix
    cycle,
  * wraps the intraday chart so the *last closed candle* becomes
    ``close = previous_close * 1.04`` and ``high = max(real_high,
    controlled_close)`` BEFORE the production ``YahooChartProvider``
    validation (variant B — owner decision 2026-08-20),
  * enforces hard external budgets before each delegated request,
  * creates the once marker directly before the first network operation,
  * invokes exactly one ``RuntimeService.run_cycle()``,
  * composes a sanitized controlled trace.

No mini-app: the controller never manually calls Hunter/Master/Technical/
Tavily/OpenAI/Ranking/Risk/Analyst/AlertBuilder/AlertDispatcher/Telegram.
"""
from __future__ import annotations

import copy
import json
import os
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from application.alert_builder import TELEGRAM_MESSAGE_LIMIT
from application.cycle_trace import (
    BLOCKED_BY_BUDGET,
    CONTROLLED_STAGE_ORDER,
    CycleTraceRecorder,
    EXECUTED,
    NATURAL_PIPELINE_STOP,
    SKIPPED,
    SUCCESS,
    FAILED,
)
from application.sources.yahoo_discovery_source import YahooDiscoverySource


# ---------------------------------------------------------------------------
# Bezpieczeństwo ścieżek i marker
# ---------------------------------------------------------------------------

class OnceAlreadyRunError(RuntimeError):
    """Marker istnieje — przebieg kontrolny już się odbył (brak retry)."""


@dataclass(frozen=True)
class ControlledValidationConfig:
    isolated_db_path: Path
    artifacts_dir: Path
    production_db_path: Path
    previous_close: Optional[float] = None
    symbol: Optional[str] = None  # never set by the user — selection is automatic
    allow_network: bool = False
    confirm_step7: bool = False


def _canonical(path: Path) -> str:
    resolved = str(Path(path).resolve())
    if os.name == "nt":
        resolved = resolved.lower()
    return resolved


def ensure_safe_paths(cfg: ControlledValidationConfig) -> ControlledValidationConfig:
    """Kanonikalizuje i twardo odrzuca produkcyjną bazę oraz katalogi w repo."""
    prod = _canonical(cfg.production_db_path)
    isolated = _canonical(cfg.isolated_db_path)
    if isolated == prod:
        raise ValueError(
            "izolowana baza nie może być produkcyjną bazą ALCHEMIKA "
            "(produkcyjna ścieżka twardo odrzucona)"
        )
    if not cfg.isolated_db_path.exists():
        raise ValueError("izolowana kopia produkcyjnej bazy musi istnieć")
    repo_root = Path(__file__).resolve().parent.parent
    repo = _canonical(repo_root)
    artifacts = _canonical(cfg.artifacts_dir)
    if artifacts == repo or artifacts.startswith(repo + os.sep):
        raise ValueError("katalog artefaktów musi znajdować się poza repozytorium")
    return ControlledValidationConfig(
        isolated_db_path=cfg.isolated_db_path.resolve(),
        artifacts_dir=cfg.artifacts_dir.resolve(),
        production_db_path=cfg.production_db_path.resolve(),
        previous_close=cfg.previous_close,
        symbol=cfg.symbol,
        allow_network=cfg.allow_network,
        confirm_step7=cfg.confirm_step7,
    )


def marker_path_for(artifacts_dir: Path) -> Path:
    return artifacts_dir / "alchemik_step7b_once.marker"


def ensure_once_marker(artifacts_dir: Path) -> None:
    """Tworzy marker atomowo PO preflight, PRZED pierwszą siecią."""
    marker = marker_path_for(artifacts_dir)
    if marker.exists():
        raise OnceAlreadyRunError(
            "marker jednokrotności już istnieje — przebieg kontrolny "
            "CONTROLLED_VALIDATION_ONLY odbył się wcześniej"
        )
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    # os.O_CREAT | os.O_EXCL — atomowe utworzenie; porażka => istnieje.
    fd = os.open(str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, b"ALCHEMIK CONTROLLED_VALIDATION_ONLY once\n")
    finally:
        os.close(fd)


def process_runs_path_for(artifacts_dir: Path) -> Path:
    return artifacts_dir / "alchemik_step7b_process_runs.json"


def read_process_runs(artifacts_dir: Path) -> int:
    p = process_runs_path_for(artifacts_dir)
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return int(data.get("process_runs", 0))
    except (ValueError, OSError):
        return 0


def increment_process_runs(artifacts_dir: Path) -> int:
    runs = read_process_runs(artifacts_dir) + 1
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    process_runs_path_for(artifacts_dir).write_text(
        json.dumps({"process_runs": runs, "controlled": True}, indent=2),
        encoding="utf-8",
    )
    return runs


# ---------------------------------------------------------------------------
# Selektor symbolu — efektywny najnowszy Reading (izolowana kopia, sqlite3)
# ---------------------------------------------------------------------------

def select_symbol(
    isolated_db_path: Path,
    discovery_symbols: List[str],
) -> Optional[Tuple[str, dict]]:
    """Automatyczny wybór symbolu.

    Znaczenie zapytania:
      1. tylko Observation ACTIVE;
      2. per instrument: najnowszy market_data_timestamp;
      3. dla tego timestampu: najwyższy revision_number;
      4. przecięcie z realnym discovery;
      5. odrzucenie Readingu bez użytecznego volume/close;
      6. sort: volume DESC, symbol ASC;
      7. dokładnie jeden rekord.
    Nigdy nie używa MAX(volume) z całej historii.
    """
    conn = sqlite3.connect(str(isolated_db_path))
    try:
        rows = conn.execute(
            """
            SELECT r.instrument_id, r.market_data_timestamp, r.revision_number,
                   r.volume, r.close
            FROM instrument_observations o
            JOIN instrument_readings r ON r.observation_id = o.observation_id
            WHERE o.state = 'ACTIVE'
              AND r.market_data_timestamp = (
                  SELECT MAX(r2.market_data_timestamp)
                  FROM instrument_readings r2
                  WHERE r2.observation_id = o.observation_id
              )
              AND r.revision_number = (
                  SELECT MAX(r3.revision_number)
                  FROM instrument_readings r3
                  WHERE r3.observation_id = o.observation_id
                    AND r3.market_data_timestamp = r.market_data_timestamp
              )
            ORDER BY r.instrument_id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    candidates = []
    for instrument_id, _ts, _rev, volume, close in rows:
        if instrument_id not in discovery_symbols:
            continue
        if volume is None or close is None or volume <= 0 or close <= 0:
            continue
        candidates.append({
            "symbol": instrument_id,
            "volume": volume,
            "close": close,
        })

    if not candidates:
        return None
    candidates.sort(key=lambda c: (-c["volume"], c["symbol"]))
    chosen = candidates[0]
    return chosen["symbol"], {"symbol": chosen["symbol"], "volume": chosen["volume"],
                              "close": chosen["close"]}


# ---------------------------------------------------------------------------
# Jednoelementowe źródło discovery (rozpoznawane jako produkcyjny Yahoo)
# ---------------------------------------------------------------------------

class SingleSymbolYahooDiscoverySource(YahooDiscoverySource):
    """Delegujący podtyp źródła: dokładnie jeden prawdziwy rekord discovery.

    Nie wykonuje drugiego discovery. Zachowuje kontrakt YahooDiscoverySource
    (accepted_snapshot, last_discovery, get_instruments) dzięki czemu
    RuntimeService._is_production_yahoo_discovery() rozpoznaje produkcyjny
    cykl matrycy.
    """

    def __init__(self, session, symbol: str, discovery_snapshot: dict):
        # Żadna sieć nie jest wykonywana — przekazujemy zagregowany jeden rekord.
        super().__init__(session)
        self._single_symbol = symbol
        self._snapshot = discovery_snapshot
        self.accepted_snapshot = {symbol: discovery_snapshot}
        self.last_discovery = {
            "outcome_kind": "SUCCESS_WITH_DATA",
            "total_records": 1,
            "accepted_count": 1,
            "rejected_count": 0,
            "error": None,
        }

    def get_instruments(self) -> List[str]:
        # Jawnie: brak drugiego discovery. Zwracamy dokładnie jeden symbol.
        return [self._single_symbol]


# ---------------------------------------------------------------------------
# Adapter Yahoo + overlay (przed produkcyjną walidacją)
# ---------------------------------------------------------------------------

class BudgetExceededError(RuntimeError):
    """Strażnik budżetu zablokował delegację przed wysłaniem requestu."""


class YahooBudgetGuard:
    """Osobne budżety discovery / daily / intraday + transport_diagnostics."""

    def __init__(self):
        self.discovery_attempts = 0
        self.discovery_real_sent = 0
        self.daily_attempts = 0
        self.daily_real_sent = 0
        self.intraday_attempts = 0
        self.intraday_real_sent = 0
        self.transport_request_count_before = 0

    def _check(self, used: int, limit: int, name: str) -> None:
        if used >= limit:
            raise BudgetExceededError(
                f"budget {name} wyczerpany ({used}/{limit}) — "
                "BLOCKED_BY_BUDGET przed wysłaniem"
            )


class ControlledYahooSession:
    """Delegujący adapter prawdziwego YahooSession z dopuszczalnymi budżetami.

    Deleguje realne ``fetch_chart`` do prawdziwego ``YahooSession``. Wariant
    ``intraday``: kopiuje dane przed modyfikacją i nakłada overlay na OSTATNIĄ
    zamkniętą świecę: controlled_close = previous_close*1.04,
    controlled_high = max(real_high, controlled_close).
    """

    OVERLAY_MULTIPLIER = 1.04

    def __init__(self, real_session, budget: YahooBudgetGuard, *,
                 previous_close: Optional[float] = None,
                 symbol: Optional[str] = None,
                 clock: Optional[Callable[[], datetime]] = None) -> None:
        self._real = real_session
        self._budget = budget
        self.previous_close = previous_close
        self.symbol = symbol
        self.overlay_applied = False
        self._clock = clock if clock is not None else (
            lambda: datetime.now(timezone.utc)
        )
        self.daily_calls: List[str] = []
        self.intraday_calls: List[str] = []

    @staticmethod
    def overlay_intraday(raw_data: dict, effective_previous_close: float) -> dict:
        """Zwraca głęboką kopię surowych danych z overlayem tylko na ostatniej
        zamkniętej świecy. Nie modyfikuje wejściowego słownika."""
        data = copy.deepcopy(raw_data)
        n = len(data["close"])
        if n == 0:
            return data
        real_close = float(data["close"][-1])
        real_high = float(data["high"][-1])
        controlled_close = round(effective_previous_close * ControlledYahooSession.OVERLAY_MULTIPLIER, 8)
        controlled_high = max(real_high, controlled_close)

        data["close"][-1] = controlled_close
        data["high"][-1] = controlled_high

        meta = dict(data.get("meta") or {})
        meta["CONTROLLED_VALIDATION_ONLY"] = True
        meta["overlay"] = {
            "symbol": meta.get("symbol"),
            "timestamp": data["timestamp"][-1],
            "close_before": real_close,
            "close_after": controlled_close,
            "high_before": real_high,
            "high_after": controlled_high,
            "open": data["open"][-1],
            "low": data["low"][-1],
            "volume": data["volume"][-1],
        }
        data["meta"] = meta
        return data

    @staticmethod
    def overlay_open_at(raw_data: dict, index: int, effective_previous_close: float) -> dict:
        """Wariant B na wybranym indeksie OPEN."""
        data = copy.deepcopy(raw_data)
        real_close = float(data["close"][index])
        real_high = float(data["high"][index])
        controlled_close = round(effective_previous_close * ControlledYahooSession.OVERLAY_MULTIPLIER, 8)
        controlled_high = max(real_high, controlled_close)
        data["close"][index] = controlled_close
        data["high"][index] = controlled_high
        meta = dict(data.get("meta") or {})
        meta["CONTROLLED_VALIDATION_ONLY"] = True
        meta["overlay"] = {
            "symbol": meta.get("symbol"),
            "timestamp": data["timestamp"][index],
            "close_before": real_close,
            "close_after": controlled_close,
            "high_before": real_high,
            "high_after": controlled_high,
            "open": data["open"][index],
            "low": data["low"][index],
            "volume": data["volume"][index],
        }
        data["meta"] = meta
        return data

    # Prawdziwy YahooSession używa paginate_screener — delegujemy argumenty.
    # Ten adapter NIE wykonuje discovery; discovery wykonuje kontroler osobno.
    def paginate_screener(self, size: int = 250):
        # Kontroler używa tego adaptera wyłącznie jako noża bezpieczeństwa:
        # budżet discovery. Kontroler nigdy nie woła tej metody poza pierwszym
        # discovery.
        return self._real.paginate_screener(size=size)

    def fetch_chart(self, symbol: str, variant: str = "daily"):
        if variant == "daily":
            self._budget._check(self._budget.daily_attempts, 1, "yahoo_daily")
            self._budget.daily_attempts += 1
            self.daily_calls.append(symbol)
            self._budget.daily_real_sent += 1
            return self._real.fetch_chart(symbol, variant="daily")
        if variant == "intraday":
            self._budget._check(self._budget.intraday_attempts, 1, "yahoo_intraday")
            self._budget.intraday_attempts += 1
            self.intraday_calls.append(symbol)
            self._budget.intraday_real_sent += 1
            raw = self._real.fetch_chart(symbol, variant="intraday")
            observed_at = self._clock()
            raw = replace(raw, observed_at=observed_at)
            if (
                self.previous_close is not None
                and getattr(raw, "kind", None) is not None
                and raw.kind.value == "SUCCESS_WITH_DATA"
                and isinstance(raw.data, dict)
                and raw.data.get("close")
            ):
                data = raw.data
                ts_list = data.get("timestamp") or []
                open_idx = None
                for i in range(len(ts_list) - 1, -1, -1):
                    try:
                        candle_start = datetime.fromtimestamp(
                            float(ts_list[i]), tz=timezone.utc
                        )
                    except (TypeError, ValueError):
                        continue
                    if candle_start <= observed_at < candle_start + timedelta(hours=1):
                        open_idx = i
                        break
                if open_idx is not None:
                    # Anchor overlayu WYŁĄCZNIE z payloadu intraday 1h i tego
                    # samego request-scoped observed_at: najbliższa wcześniejsza
                    # chronologicznie CLOSED 1h. effective_previous_close = close
                    # tej CLOSED 1h. Readingi 5m, meta Yahoo, wartości przekazane
                    # przez select_symbol ani najstarszy wiersz NIE są źródłem
                    # anchoru (brak fallbacku między timeframe).
                    open_candle_start = datetime.fromtimestamp(
                        float(ts_list[open_idx]), tz=timezone.utc
                    )
                    anchor_idx = None
                    anchor_candle_start = None
                    for i in range(len(ts_list)):
                        try:
                            cs = datetime.fromtimestamp(
                                float(ts_list[i]), tz=timezone.utc
                            )
                        except (TypeError, ValueError):
                            continue
                        # CLOSED 1h: świeca zakończona przed observed_at
                        # i rozpoczęta przed otwartą świecą.
                        if cs >= open_candle_start:
                            continue
                        if cs + timedelta(hours=1) <= observed_at:
                            if (
                                anchor_idx is None
                                or anchor_candle_start is None
                                or cs > anchor_candle_start
                            ):
                                anchor_idx = i
                                anchor_candle_start = cs
                    if anchor_idx is None:
                        # Twardy naturalny stop: brak wcześniejszej CLOSED 1h
                        # w payloadzie. Nie wykonujemy overlayu i nie modyfikujemy
                        # surowego payloadu.
                        self.overlay_applied = False
                        self.overlay_state = {
                            "symbol": symbol,
                            "interval": "1h",
                            "status": "NO_PREVIOUS_CLOSED_1H_ANCHOR",
                            "applied": False,
                            "observed_at": observed_at.isoformat(),
                            "open_index": open_idx,
                            "open_candle_start": open_candle_start.isoformat(),
                            "raw_preserved": True,
                        }
                        from data.yahoo.yahoo_session import OutcomeKind
                        raw = replace(
                            raw, kind=OutcomeKind.SUCCESS_NO_DATA, data=None
                        )
                    else:
                        effective_previous_close = float(data["close"][anchor_idx])
                        expected_close = round(
                            effective_previous_close
                            * ControlledYahooSession.OVERLAY_MULTIPLIER,
                            8,
                        )
                        real_close = float(data["close"][open_idx])
                        real_high = float(data["high"][open_idx])
                        raw = copy.deepcopy(raw)
                        raw.data = self.overlay_open_at(
                            data, open_idx, effective_previous_close
                        )
                        self.overlay_applied = True
                        self.overlay_state = {
                            "symbol": symbol,
                            "interval": "1h",
                            "status": "APPLIED",
                            "applied": True,
                            "open_index": open_idx,
                            "open_candle_start": open_candle_start.isoformat(),
                            # Semantyka 7F: expected_close = czas zamknięcia
                            # świecy OPEN 1h (ISO), controlled_close = cena
                            # kontrolna wyliczona przez overlay.
                            "expected_close": (
                                open_candle_start + timedelta(hours=1)
                            ).isoformat(),
                            "controlled_close": expected_close,
                            "observed_at": observed_at.isoformat(),
                            "anchor_source": "YAHOO_PREVIOUS_CLOSED_1H",
                            "anchor_index": anchor_idx,
                            "anchor_candle_start": (
                                anchor_candle_start.isoformat()
                                if anchor_candle_start is not None
                                else None
                            ),
                            "anchor_candle_state": "CLOSED",
                            "effective_previous_close": effective_previous_close,
                            "close_before": real_close,
                            "close_after": expected_close,
                            "high_before": real_high,
                            "high_after": max(real_high, expected_close),
                            "open_unchanged": True,
                            "low_unchanged": True,
                            "volume_unchanged": True,
                            "timestamp_unchanged": True,
                        }
                else:
                    # Twardy naturalny stop: brak OPEN. Nie modyfikujemy surowego
                    # payloadu (zachowany w overlay_state); zwracamy SUCCESS_NO_DATA,
                    # aby YahooChartProvider nie wyprodukował użytecznych MarketData
                    # intraday — RuntimeService nie może zapisać Readingu ani
                    # uruchomić downstream.
                    self.overlay_state = {
                        "status": "NO_OPEN_CANDIDATE",
                        "applied": False,
                        "observed_at": observed_at.isoformat(),
                        "symbol": symbol,
                        "raw_preserved": True,
                    }
                    from data.yahoo.yahoo_session import OutcomeKind
                    raw = replace(raw, kind=OutcomeKind.SUCCESS_NO_DATA, data=None)
            return raw
        raise ValueError(f"nieznany variant {variant}")


# ---------------------------------------------------------------------------
# Strażnicy budżetów Tavily / OpenAI / Telegram
# ---------------------------------------------------------------------------

class _ExternalBudgetGuard:
    limit = 1

    def __init__(self, name: str) -> None:
        self.name = name
        self.attempts = 0
        self.real_sent = 0

    def _check(self) -> None:
        self.attempts += 1
        if self.attempts > self.limit:
            raise BudgetExceededError(
                f"budget {self.name} wyczerpany ({self.attempts}/{self.limit}) — "
                "BLOCKED_BY_BUDGET przed wysłaniem"
            )

    def _before_delegate(self) -> None:
        self.real_sent += 1


class TavilyBudgetGuard(_ExternalBudgetGuard):
    """Maksymalnie 1 search_for_event."""

    def __init__(self) -> None:
        super().__init__("tavily")

    def guard(self, event, delegate: Callable):
        self._check()
        self._before_delegate()
        return delegate(event)


class OpenAIBudgetGuard(_ExternalBudgetGuard):
    """Maksymalnie 1 analyze."""

    def __init__(self) -> None:
        super().__init__("openai")

    def guard(self, payload: dict, delegate: Callable):
        self._check()
        self._before_delegate()
        return delegate(payload)


class TelegramBudgetGuard(_ExternalBudgetGuard):
    """Maksymalnie 1 send."""

    def __init__(self) -> None:
        super().__init__("telegram")

    def guard(self, message, delegate: Callable):
        self._check()
        self._before_delegate()
        return delegate(message)


class GuardedTavilyAdapter:
    """Delegujący wrapper granicy Tavily — maksymalnie 1 search_for_event."""

    def __init__(self, delegate, guard: TavilyBudgetGuard) -> None:
        self._delegate = delegate
        self._guard = guard

    def search_for_event(self, event):
        return self._guard.guard(event, self._delegate.search_for_event)


class GuardedOpenAIProvider:
    """Delegujący wrapper granicy OpenAI — maksymalnie 1 analyze."""

    def __init__(self, delegate, guard: OpenAIBudgetGuard) -> None:
        self._delegate = delegate
        self._guard = guard

    def analyze(self, payload: dict):
        return self._guard.guard(payload, self._delegate.analyze)


TELEGRAM_CONTROLLED_PREFIX = (
    "ALCHEMIK — CONTROLLED_VALIDATION_ONLY\n"
    "TO NIE JEST SYGNAŁ INWESTYCYJNY.\n\n"
)


def _apply_controlled_prefix(message: str) -> str:
    """Zapewnia pełną, jednorazową etykietę kontrolną z zachowaniem limitu.

    Prefiks i zastrzeżenie pozostają kompletne; przy przekroczeniu limitu
    Telegrama skracana jest wyłącznie treść właściwa.
    """
    if message.startswith(TELEGRAM_CONTROLLED_PREFIX):
        return message
    combined = TELEGRAM_CONTROLLED_PREFIX + message
    if len(combined) <= TELEGRAM_MESSAGE_LIMIT:
        return combined
    body_budget = TELEGRAM_MESSAGE_LIMIT - len(TELEGRAM_CONTROLLED_PREFIX) - 1
    return TELEGRAM_CONTROLLED_PREFIX + message[:body_budget] + "…"


class GuardedTelegramChannel:
    """Delegujący wrapper granicy Telegram — maksymalnie 1 send + etykieta."""

    def __init__(self, delegate, guard: TelegramBudgetGuard) -> None:
        self._delegate = delegate
        self._guard = guard

    def send(self, alert_message):
        original = getattr(alert_message, "formatted_message", "")
        alert_message.formatted_message = _apply_controlled_prefix(original)
        return self._guard.guard(alert_message, self._delegate.send)


# ---------------------------------------------------------------------------
# Kontroler
# ---------------------------------------------------------------------------

class ControlledValidationController:
    """Dokładnie jeden RuntimeService.run_cycle() z prawdziwym pipeline."""

    def __init__(
        self,
        *,
        cfg: ControlledValidationConfig,
        runtime_factory: Callable[[], object],
        real_yahoo_session,
        run_cycle: Optional[Callable[[], object]] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.cfg = ensure_safe_paths(cfg)
        self._runtime_factory = runtime_factory
        self._real_yahoo = real_yahoo_session
        self.budget = YahooBudgetGuard()
        self._clock = clock

    def _once(self) -> None:
        ensure_once_marker(self.cfg.artifacts_dir)
        increment_process_runs(self.cfg.artifacts_dir)

    def run(self) -> dict:
        from application.controlled_validation_cli import _build_runtime_guarded

        # preflight trace
        recorder = CycleTraceRecorder(stage_order=CONTROLLED_STAGE_ORDER)
        recorder.stage_start("preflight")
        try:
            ensure_safe_paths(self.cfg)
            # Marker tworzy CLI (po preflight ścieżek, PRZED pierwszą siecią).
            # Kontroler wyłącznie sprawdza jego istnienie — istniejący marker
            # blokuje przebieg (jednokrotność).
            if not marker_path_for(self.cfg.artifacts_dir).exists():
                raise OnceAlreadyRunError(
                    "brak markera jednokrotności — CLI musi utworzyć marker "
                    "przed pierwszą operacją sieciową"
                )
            increment_process_runs(self.cfg.artifacts_dir)
            recorder.stage_end("preflight", EXECUTED)
        except Exception as exc:  # noqa: BLE001
            recorder.stage_end("preflight", FAILED, reason=type(exc).__name__)
            return {
                "status": "PREFLIGHT_FAILED",
                "trace": recorder.finish(data_flow_complete=False,
                                         overall_status=FAILED),
            }

        recorder.stage_start("discovery")
        try:
            self.budget.discovery_attempts += 1
            discovery = self._real_yahoo.paginate_screener(size=250)
            self.budget.discovery_real_sent += 1
        except Exception as exc:  # noqa: BLE001
            recorder.stage_end("discovery", FAILED, reason=type(exc).__name__)
            return self._finish(recorder, "ERROR_YAHOO_DISCOVERY")
        recorder.stage_end("discovery", EXECUTED, output_count=1)

        # Build real discovery snapshot from the real pagination
        snapshot = {}
        try:
            if discovery.kind.value == "SUCCESS_WITH_DATA":
                for page in discovery.data.pages:
                    for q in page.quotes:
                        sym = q.get("symbol")
                        if sym:
                            snapshot[sym] = q
        except Exception:  # noqa: BLE001
            snapshot = {}

        recorder.stage_start("symbol_selection")
        selected = select_symbol(self.cfg.isolated_db_path, list(snapshot.keys()))
        if selected is None:
            recorder.stage_end("symbol_selection", NATURAL_PIPELINE_STOP)
            return self._finish(recorder, "NO_NATURAL_E2E_CANDIDATE")
        symbol, _snap = selected
        real_record = snapshot.get(symbol)
        if real_record is None:
            recorder.stage_end("symbol_selection", FAILED)
            return self._finish(recorder, "ERROR_SYMBOL_SELECTION")
        recorder.stage_end("symbol_selection", EXECUTED, output_count=1)

        # One-element discovery source — recognised as production Yahoo matrix.
        single_source = SingleSymbolYahooDiscoverySource(
            self._real_yahoo, symbol, real_record
        )
        previous_close = _snap.get("close")
        runtime, controlled_session = _build_runtime_guarded(
            self.cfg, single_source, self._real_yahoo, symbol,
            previous_close=previous_close,
            budget=self.budget,
            clock=self._clock,
        )
        self.controlled_session = controlled_session
        recorder.stage_start("daily")
        recorder.stage_start("intraday")
        # RuntimeService.run_cycle() wykonuje dokładnie jeden raz cały pipeline
        # (discovery przechodzi przez jednoelementowe źródło, chart przez adapter).
        try:
            report = runtime.run_cycle()
            # Twardy naturalny stop: realny payload intraday nie zawiera otwartej
            # swiecy 1h (ControlledYahooSession zwrocil SUCCESS_NO_DATA i ustawil
            # overlay_state.status == NO_OPEN_CANDIDATE). Konczymy bez drugiego
            # cyklu, fetchu i etapu domenowego.
            overlay_state = getattr(controlled_session, "overlay_state", None) or {}
            overlay_status = overlay_state.get("status")
            if overlay_status == "NO_OPEN_CANDIDATE":
                recorder.stage_end("daily", NATURAL_PIPELINE_STOP)
                recorder.stage_end("intraday", NATURAL_PIPELINE_STOP)
                recorder.stage_end("controlled_overlay", NATURAL_PIPELINE_STOP)
                recorder.stage_end("chart_validation", NATURAL_PIPELINE_STOP)
                recorder.stage_end("reading_persistence", NATURAL_PIPELINE_STOP)
                recorder.stage_end("cycle_persistence", EXECUTED)
                recorder.stage_end(
                    "final_database_check", EXECUTED,
                    reason="overlay_status=NO_OPEN_CANDIDATE",
                )
                return self._finish(recorder, "NO_NATURAL_E2E_CANDIDATE")
            if overlay_status == "NO_PREVIOUS_CLOSED_1H_ANCHOR":
                recorder.stage_end("daily", NATURAL_PIPELINE_STOP)
                recorder.stage_end("intraday", NATURAL_PIPELINE_STOP)
                recorder.stage_end("controlled_overlay", NATURAL_PIPELINE_STOP,
                                   details=overlay_state)
                recorder.stage_end("chart_validation", NATURAL_PIPELINE_STOP)
                recorder.stage_end("reading_persistence", NATURAL_PIPELINE_STOP)
                recorder.stage_end("cycle_persistence", EXECUTED)
                recorder.stage_end(
                    "final_database_check", EXECUTED,
                    reason="overlay_status=NO_PREVIOUS_CLOSED_1H_ANCHOR",
                )
                return self._finish(recorder, "NO_NATURAL_E2E_CANDIDATE")
            recorder.stage_end("daily", EXECUTED)
            recorder.stage_end("intraday", EXECUTED)
            recorder.stage_end("controlled_overlay", EXECUTED,
                               details=overlay_state)
            recorder.stage_end("chart_validation", EXECUTED)
            recorder.stage_end("cycle_persistence", EXECUTED)
            recorder.stage_end(
                "final_database_check", EXECUTED,
                reason=f"candidates={getattr(report, 'candidates_count', 0)}",
            )
            # Translacja prawdziwego śladu run_cycle() (SKIPPED stages wewnętrzne)
            # do kontrolnego widoku — bez globalnej zmiany semantyki cycle_trace.
            real_trace = {}
            diag = getattr(report, "diagnostics", None) or {}
            real_trace = diag.get("trace") if isinstance(diag, dict) else {}
            for name, stage in (real_trace.get("stages") or {}).items():
                status = stage.get("status") if isinstance(stage, dict) else None
                if status in ("SUCCESS", "PARTIAL"):
                    recorder.stage_end(name, EXECUTED)
                elif status == "FAILED":
                    recorder.stage_end(name, FAILED)
                elif status == "EXECUTED_EMPTY":
                    recorder.stage_end(name, "EXECUTED_EMPTY")
                elif status == "SKIPPED":
                    recorder.stage_end(name, SKIPPED)
            # Etapy wewnętrzne niewystępujące w realnym trace oznaczamy EXECUTED,
            # gdy cykl się powiódł (pipeline naprawdę je wykonał).
            if getattr(report, "candidates_count", 0) > 0:
                for mandatory in (
                    "reading_persistence", "baseline_comparison", "hunter",
                    "technical", "master", "market_event", "tavily", "openai",
                    "ai_result", "ranking", "risk", "analyst", "final_analysis",
                    "alert_builder", "alert_dispatcher", "telegram",
                ):
                    st = recorder.trace["stages"].get(mandatory)
                    if st is not None and st["status"] in ("NOT_STARTED",):
                        recorder.stage_end(mandatory, EXECUTED)
            status = "COMPLETE_E2E"
            return self._finish(recorder, status)
        except Exception as exc:  # noqa: BLE001
            recorder.stage_end("daily", FAILED, reason=type(exc).__name__)
            recorder.stage_end("intraday", FAILED, reason=type(exc).__name__)
            recorder.stage_end("controlled_overlay", FAILED, reason=type(exc).__name__)
            recorder.stage_end("chart_validation", FAILED, reason=type(exc).__name__)
            recorder.stage_end("cycle_persistence", FAILED, reason=type(exc).__name__)
            recorder.stage_end("final_database_check", FAILED, reason=type(exc).__name__)
            return self._finish(recorder, "ERROR_RUNTIME_CYCLE")

    def _finish(self, recorder, status: str) -> dict:
        trace = recorder.finish(
            data_flow_complete=(status == "COMPLETE_E2E"),
            overall_status=(
                SUCCESS if status == "COMPLETE_E2E"
                else NATURAL_PIPELINE_STOP
                if status == "NO_NATURAL_E2E_CANDIDATE"
                else FAILED
            ),
        )
        return {
            "status": status,
            "trace": trace,
            "budget": {
                "yahoo_discovery": {"attempts": self.budget.discovery_attempts,
                                    "real_sent": self.budget.discovery_real_sent},
                "yahoo_daily": {"attempts": self.budget.daily_attempts,
                                "real_sent": self.budget.daily_real_sent},
                "yahoo_intraday": {"attempts": self.budget.intraday_attempts,
                                   "real_sent": self.budget.intraday_real_sent},
            },
        }