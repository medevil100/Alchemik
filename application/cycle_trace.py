"""
Obserwowalny ślad cyklu ALCHEMIKA (Punkt 6/7).

RuntimeService pozostaje właścicielem orkiestracji i składa końcowy ślad.
Ten moduł jest wyłącznie addytywnym, deterministycznym rejestratorem:
nie zmienia logiki biznesowej silników, nie tworzy nowej bazy, nie jest
globalnym singletonem i nie przechowuje sekretów.

Ślad jest budowany wyłącznie z bezpiecznych pól (liczniki, statusy, czasy,
booleany, typy wyjątków i zredagowane komunikaty). Pełne OHLCV, pełne
odpowiedzi Tavily/OpenAI, nagłówki HTTP, cookie, crumb i sekrety nigdy
nie są zapisywane.

Dodatkowo moduł udostępnia jedną, centralną, deterministyczną redakcję
``sanitize_trace`` używaną zawsze przed dołączeniem śladu do CycleReport.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

# Proste statusy diagnostyczne — nie zmieniają decyzji silników.
NOT_STARTED = "NOT_STARTED"
SUCCESS = "SUCCESS"
PARTIAL = "PARTIAL"
FAILED = "FAILED"
SKIPPED = "SKIPPED"
EXECUTED_EMPTY = "EXECUTED_EMPTY"
# Addytywne statusy kontrolne trybu CONTROLLED_VALIDATION_ONLY (Krok 7B/8).
# Nie zmieniają znaczenia istniejących statusów normalnego cyklu.
EXECUTED = "EXECUTED"
BLOCKED_BY_BUDGET = "BLOCKED_BY_BUDGET"
NATURAL_PIPELINE_STOP = "NATURAL_PIPELINE_STOP"

DIAGNOSTIC_STATUSES = frozenset({
    NOT_STARTED, SUCCESS, PARTIAL, FAILED, SKIPPED, EXECUTED_EMPTY,
    EXECUTED, BLOCKED_BY_BUDGET, NATURAL_PIPELINE_STOP,
})

# Wymagana kolejność etapów śladu (pkt 7 zadania).
STAGE_ORDER: List[str] = [
    "discovery",
    "chart",
    "market_scan",
    "observation",
    "reading_persistence",
    "technical",
    "hunter",
    "master",
    "news",
    "tavily",
    "ai",
    "ranking",
    "risk",
    "final_result",
    "alert_build",
    "alert_dispatch",
    "telegram",
]

# Osobna, addytywna lista etapów kontrolnych trybu CONTROLLED_VALIDATION_ONLY
# (Krok 7B/8). Nie modyfikuje istniejącej STAGE_ORDER normalnego cyklu.
CONTROLLED_STAGE_ORDER: List[str] = [
    "preflight",
    "discovery",
    "symbol_selection",
    "daily",
    "intraday",
    "controlled_overlay",
    "chart_validation",
    "reading_persistence",
    "baseline_comparison",
    "hunter",
    "technical",
    "master",
    "market_event",
    "tavily",
    "openai",
    "ai_result",
    "ranking",
    "risk",
    "analyst",
    "final_analysis",
    "alert_builder",
    "alert_dispatcher",
    "telegram",
    "cycle_persistence",
    "final_database_check",
]

# ---------------------------------------------------------------------------
# Centralna, deterministyczna redakcja
# ---------------------------------------------------------------------------

_FORBIDDEN_KEY_MARKERS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
    "cookie",
    "crumb",
    "bearer",
    "chat_id",
    "bot_token",
    "telegram_token",
    "openai_key",
    "tavily_key",
)

_FORBIDDEN_VALUE_MARKERS: tuple[str, ...] = (
    "sk-",
    "tvly-",
)

_FORBIDDEN_VALUE_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"Basic\s+[A-Za-z0-9+/=]+", re.IGNORECASE),
)

_REDACTED = "[REDACTED]"


def _contains_forbidden_key_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _FORBIDDEN_KEY_MARKERS)


def _redact_text(value: str) -> str:
    """Deterministycznie usuwa znane wzorce sekretów z pojedynczego tekstu."""
    out = value
    for pattern in _FORBIDDEN_VALUE_PATTERNS:
        out = pattern.sub(_REDACTED, out)
    lowered = out.lower()
    for marker in _FORBIDDEN_VALUE_MARKERS:
        if marker in lowered:
            # Usuń prefiks sekretu i pozostaw wyłącznie bezpieczny opis.
            idx = lowered.find(marker)
            out = out[:idx] + _REDACTED
            break
    return out


def _redact_any(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {str(k): _redact_value_pair(k, v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value_pair(None, item) for item in value]
    return value


def _redact_value_pair(key: Any, value: Any) -> Any:
    if key is not None and isinstance(key, str) and _contains_forbidden_key_marker(key):
        return _REDACTED
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {str(k): _redact_value_pair(k, v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value_pair(None, item) for item in value]
    return value


def sanitize_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    """Centralna redakcja śladu — zwraca nowy, bezpieczny obiekt.

    Sekrety, nagłówki, cookie, crumb i pełne payloady providerów nigdy nie
    trafiają do tego słownika, ale ta funkcja jest obowiązkową, deterministyczną
    siatką bezpieczeństwa przed dołączeniem śladu do ``CycleReport``.
    """
    return _redact_any(trace)


# ---------------------------------------------------------------------------
# Budowa śladu
# ---------------------------------------------------------------------------

def _new_stage(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "status": NOT_STARTED,
        "start_utc": None,
        "end_utc": None,
        "duration_ms": None,
        "input_count": 0,
        "output_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "reason": None,
    }


def new_instrument_entry(symbol: str) -> Dict[str, Any]:
    """Bezpieczny słownik per instrument (pkt 8 zadania)."""
    return {
        "symbol": symbol,
        "event_id": None,
        "final_result_id": None,
        "alert_id": None,
        "discovery_status": NOT_STARTED,
        "chart_status": NOT_STARTED,
        "candles_received": 0,
        "candles_valid": 0,
        "candles_rejected": 0,
        "rejection_reasons": {},
        "latest_raw_timestamp": None,
        "latest_valid_timestamp": None,
        "http_status": None,
        "error_kind": "none",
        "latest_data_timestamp": None,
        "current_price": None,
        "volume": None,
        "observation_status": NOT_STARTED,
        "reading_status": None,
        "baseline_exists": False,
        "baseline_close": None,
        "change_vs_baseline_pct": None,
        "technical_status": NOT_STARTED,
        "indicators_count": 0,
        "insufficient_data_error": False,
        "hunter_status": NOT_STARTED,
        "events_count": 0,
        "master_status": NOT_STARTED,
        "tavily_attempted": 0,
        "tavily_sent": 0,
        "tavily_success": 0,
        "ai_attempted": 0,
        "ai_sent": 0,
        "ai_validated": 0,
        "ai_refusal": 0,
        "ai_signal_created": False,
        "final_result_created": False,
        "alert_built": False,
        "telegram_attempted": 0,
        "telegram_sent": 0,
        "telegram_success": 0,
        "final_status": NOT_STARTED,
        "error_types": [],
    }


def new_trace(
    cycle_id: Optional[str] = None,
    started_at_utc: Optional[str] = None,
    stage_order: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Utwórz świeży, pusty ślad cyklu.

    Każda instancja śladu dostaje nowy ``cycle_id`` (nie dziedziczy danych
    poprzedniego cyklu).
    """
    if cycle_id is None:
        cycle_id = str(uuid.uuid4())
    if started_at_utc is None:
        started_at_utc = datetime.now(timezone.utc).isoformat()

    ordered = stage_order or STAGE_ORDER
    return {
        "schema_version": SCHEMA_VERSION,
        "cycle_id": cycle_id,
        "started_at_utc": started_at_utc,
        "ended_at_utc": None,
        "duration_ms": None,
        "overall_status": NOT_STARTED,
        "stages": {name: _new_stage(name) for name in ordered},
        "instruments": {},
        "counters": {
            "instruments_total": 0,
            "instruments_success": 0,
            "instruments_partial": 0,
            "instruments_failed": 0,
            "instruments_skipped": 0,
            "retry_count": 0,
            "fallback_count": 0,
        },
        "errors": [],
        "external_calls": {
            "yahoo_attempts": 0,
            "yahoo_real_sent": 0,
            "tavily_attempts": 0,
            "tavily_real_sent": 0,
            "openai_attempts": 0,
            "openai_real_sent": 0,
            "telegram_attempts": 0,
            "telegram_real_sent": 0,
        },
        "data_flow_complete": False,
    }


class CycleTraceRecorder:
    """Skromny rejestrator śladu używany przez RuntimeService i MasterEngine.

    Nie jest singletonem i nie przechowuje stanu cyklu poza jednym obiektem
    ``trace`` tworzonym per ``run_cycle()``.
    """

    def __init__(
        self,
        cycle_id: Optional[str] = None,
        clock=None,
        stage_order: Optional[List[str]] = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.trace = new_trace(
            cycle_id=cycle_id, started_at_utc=self._now_iso(), stage_order=stage_order
        )

    # -- czas -----------------------------------------------------------------
    def _now_iso(self) -> str:
        return self._clock().isoformat()

    def _now_timestamp(self) -> float:
        return self._clock().timestamp()

    # -- etapy (agregaty całego cyklu) ----------------------------------------
    def stage_start(self, name: str) -> None:
        stage = self.trace["stages"].get(name)
        if stage is None:
            return
        stage["start_utc"] = self._now_iso()
        stage["_start_ts"] = self._now_timestamp()

    _STATUS_SEVERITY = {
        NOT_STARTED: 0,
        SKIPPED: 1,
        NATURAL_PIPELINE_STOP: 1,
        SUCCESS: 2,
        EXECUTED: 2,
        PARTIAL: 3,
        FAILED: 4,
        BLOCKED_BY_BUDGET: 4,
    }

    def stage_end(
        self,
        name: str,
        status: str,
        *,
        reason: Optional[str] = None,
        input_count: Optional[int] = None,
        output_count: Optional[int] = None,
        accepted_count: Optional[int] = None,
        rejected_count: Optional[int] = None,
        skipped_count: Optional[int] = None,
        error_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        stage = self.trace["stages"].get(name)
        if stage is None:
            return
        existing = stage.get("status", NOT_STARTED)
        if self._STATUS_SEVERITY.get(status, 0) > self._STATUS_SEVERITY.get(existing, 0):
            stage["status"] = status
        stage["end_utc"] = self._now_iso()
        start_ts = stage.pop("_start_ts", None)
        if start_ts is not None:
            stage["duration_ms"] = max(0, int((self._now_timestamp() - start_ts) * 1000))
        if reason is not None:
            stage["reason"] = reason
        if details is not None:
            # Jawny, bezpieczny słownik szczegółów etapu (np. kontrolowany
            # overlay). Wartości są redagowane centralnie przez sanitize_trace
            # przed dołączeniem śladu do CycleReport.
            stage["details"] = details
        for field, value in (
            ("input_count", input_count),
            ("output_count", output_count),
            ("accepted_count", accepted_count),
            ("rejected_count", rejected_count),
            ("skipped_count", skipped_count),
            ("error_count", error_count),
        ):
            if value is not None:
                stage[field] = value

    def stage_count_bump(self, name: str, field: str, amount: int = 1) -> None:
        stage = self.trace["stages"].get(name)
        if stage is None:
            return
        stage[field] = int(stage.get(field, 0)) + amount

    # -- instrumenty ----------------------------------------------------------
    def ensure_instrument(self, symbol: str) -> Dict[str, Any]:
        instruments = self.trace["instruments"]
        if symbol not in instruments:
            instruments[symbol] = new_instrument_entry(symbol)
            self.trace["counters"]["instruments_total"] += 1
        return instruments[symbol]

    def instrument_update(self, symbol: str, **fields: Any) -> None:
        entry = self.ensure_instrument(symbol)
        entry.update(fields)

    def instrument_error_type(self, symbol: str, error_type: str) -> None:
        entry = self.ensure_instrument(symbol)
        types = entry["error_types"]
        if error_type not in types:
            types.append(error_type)

    # -- liczniki zewnętrzne --------------------------------------------------
    def bump_external(self, name: str, amount: int = 1) -> None:
        calls = self.trace["external_calls"]
        if name in calls:
            calls[name] += amount

    def set_external(self, name: str, value: int) -> None:
        """Ustaw licznik zewnętrzny (np. rzeczywiste wywołania sieciowe)."""
        calls = self.trace["external_calls"]
        if name in calls:
            calls[name] = int(value)

    def add_error(self, stage: str, symbol: Optional[str], error_type: str, message: str) -> None:
        self.trace["errors"].append({
            "stage": stage,
            "symbol": symbol,
            "error_type": error_type,
            "message": _redact_text(str(message)),
        })

    def finish(self, *, data_flow_complete: bool, overall_status: str) -> Dict[str, Any]:
        ended = self._now_iso()
        self.trace["ended_at_utc"] = ended
        start = self._parse_ts(self.trace["started_at_utc"])
        end = self._parse_ts(ended)
        if start is not None and end is not None:
            self.trace["duration_ms"] = max(0, int((end - start).total_seconds() * 1000))
        self.trace["overall_status"] = overall_status
        self.trace["data_flow_complete"] = bool(data_flow_complete)

        # Agregaty per instrument.
        c = self.trace["counters"]
        for entry in self.trace["instruments"].values():
            status = entry.get("final_status", NOT_STARTED)
            c[f"instruments_{status.lower()}"] = c.get(f"instruments_{status.lower()}", 0) + 1

        return sanitize_trace(self.trace)

    def finalize_skipped_stages(self) -> None:
        """Oznacz nieuruchomione etapy jako SKIPPED (jawne, bez pomijania)."""
        for name, stage in self.trace["stages"].items():
            if stage["status"] == NOT_STARTED:
                stage["status"] = SKIPPED
                stage["end_utc"] = stage["start_utc"]
                stage["duration_ms"] = 0

    @staticmethod
    def _parse_ts(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None


def safe_error_type(exc: BaseException) -> str:
    """Zwróć bezpieczną nazwę typu wyjątku (bez danych z payloadu)."""
    return type(exc).__name__


def build_trace_summary(trace: Dict[str, Any]) -> Dict[str, Any]:
    """Zbuduj agregatowy podsumowanie śladu (inny schemat niż raw).

    ``raw`` niesie pełną strukturę (etapy + instrumenty); ``summary``
    zachowuje wyłącznie agregaty i status końcowy, aby artefakty były
    różne treściowo, rozmiarem i hashem (pkt 11 zadania).
    """
    external = trace.get("external_calls", {})
    counters = trace.get("counters", {})
    stages = trace.get("stages", {})
    instruments = trace.get("instruments", {})
    return {
        "schema": "cycle_trace_summary",
        "schema_version": trace.get("schema_version"),
        "cycle_id": trace.get("cycle_id"),
        "started_at_utc": trace.get("started_at_utc"),
        "ended_at_utc": trace.get("ended_at_utc"),
        "duration_ms": trace.get("duration_ms"),
        "overall_status": trace.get("overall_status"),
        "data_flow_complete": trace.get("data_flow_complete"),
        "counters": dict(counters),
        "external_calls": dict(external),
        "error_total": len(trace.get("errors", [])),
        "stage_status": {name: st.get("status") for name, st in stages.items()},
        "instruments_total": counters.get("instruments_total", len(instruments)),
    }


def build_trace_report_text(trace: Dict[str, Any]) -> str:
    """Zbuduj czytelny, bezpieczny raport tekstowy dla właściciela."""
    lines = [
        "ALCHEMIK — raport śladu cyklu",
        f"cycle_id: {trace.get('cycle_id')}",
        f"started_at_utc: {trace.get('started_at_utc')}",
        f"ended_at_utc: {trace.get('ended_at_utc')}",
        f"duration_ms: {trace.get('duration_ms')}",
        f"overall_status: {trace.get('overall_status')}",
        f"data_flow_complete: {trace.get('data_flow_complete')}",
    ]

    stages = trace.get("stages", {})
    lines.append("")
    lines.append("ETAPY:")
    for name in STAGE_ORDER:
        stage = stages.get(name)
        if not stage:
            continue
        lines.append(
            f"  {name}: status={stage.get('status')} "
            f"input={stage.get('input_count')} output={stage.get('output_count')} "
            f"accepted={stage.get('accepted_count')} rejected={stage.get('rejected_count')} "
            f"skipped={stage.get('skipped_count')} errors={stage.get('error_count')}"
            + (f" reason={stage.get('reason')}" if stage.get("reason") else "")
        )

    parts = []
    for name, entry in trace.get("instruments", {}).items():
        parts.append(
            f"{name}: chart={entry.get('chart_status')} "
            f"reading={entry.get('reading_status')} "
            f"technical={entry.get('technical_status')} "
            f"master={entry.get('master_status')} "
            f"final={entry.get('final_status')}"
        )

    if parts:
        lines.append("")
        lines.append("INSTRUMENTY:")
        lines.extend(f"  {p}" for p in parts)

    external = trace.get("external_calls", {})
    lines.append("")
    lines.append(
        "LICZNIKI ZEWNĘTRZNE: "
        + ", ".join(f"{k}={v}" for k, v in external.items())
    )

    if trace.get("errors"):
        lines.append("")
        lines.append("BŁĘDY (zredagowane):")
        for err in trace["errors"]:
            lines.append(
                f"  [{err.get('stage')}] {err.get('symbol')} "
                f"{err.get('error_type')}: {err.get('message')}"
            )

    return "\n".join(lines) + "\n"
