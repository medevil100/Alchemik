"""
Cienkie CLI trybu CONTROLLED_VALIDATION_ONLY (Krok 7B/8).

Wymagane dwie jawne flagi: ``--allow-network`` i ``--confirm-step7``.
Bez obu flag CLI kończy się PRZED:
  * importem/fabryką klientów sieciowych,
  * odczytem sekretów,
  * otwarciem zapisywalnej bazy,
  * utworzeniem markera,
  * utworzeniem RuntimeService,
  * jakąkolwiek siecią.

Produkcyjna baza jest twardo odrzucana (również ścieżki równoważne:
symlink/junction/nalewkę case-insensitive). Izolowana kopia musi istnieć.
Katalog artefaktów i marker/licznik process_runs muszą znajdować się poza repo.

Kontroler przygotowuje prawdziwe zależności i wykonuje DOKŁADNIE JEDNO
``RuntimeService.run_cycle()`` — nigdy nie odtwarza pipeline'u ręcznie.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
import tempfile

# Ensure project root is on sys.path (jak w application/entrypoint.py).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from application.controlled_validation import (
    BudgetExceededError,
    ControlledValidationConfig,
    ControlledYahooSession,
    GuardedOpenAIProvider,
    GuardedTavilyAdapter,
    GuardedTelegramChannel,
    OpenAIBudgetGuard,
    TavilyBudgetGuard,
    TelegramBudgetGuard,
    YahooBudgetGuard,
    ensure_once_marker,
    ensure_safe_paths,
    marker_path_for,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROD_DB = PROJECT_ROOT / "data" / "runtime" / "alchemik_runtime.db"

TRACE_ARTIFACT_NAME = "controlled_validation_trace.json"


def write_controlled_trace_json(result: dict, artifacts_dir: Path) -> Path:
    """Jeden jawny, atomowy zapis finalnego sanitizowanego wyniku kontrolera.

    Zapisuje ``<artifacts-dir>/controlled_validation_trace.json`` w UTF-8 po
    pojedynczym controller.run(). Przed zapisem trace jest redagowany przez
    centralny ``sanitize_trace`` (żadnej drugiej logiki redakcji). Plik nie
    zawiera sekretów, środowiska procesu ani konfiguracji klientów — zapis
    obejmuje wyłącznie status i sanitizowany trace wyniku kontrolera.
    """
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    # Lazy import: CLI musi pozostać wolne od importów aplikacji przed
    # sprawdzeniem flag (no-flags-no-effects). sanitize_trace jest centralną
    # redakcją z application.cycle_trace.
    from application.cycle_trace import sanitize_trace
    trace = sanitize_trace(copy.deepcopy(result.get("trace") or {}))
    payload = {
        "status": result.get("status"),
        "trace": trace,
    }
    target = artifacts_dir / TRACE_ARTIFACT_NAME
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{TRACE_ARTIFACT_NAME}.",
        suffix=".tmp",
        dir=str(artifacts_dir),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, str(target))
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return target


def _build_runtime_guarded(
    cfg: ControlledValidationConfig,
    single_source,
    real_yahoo_session,
    symbol: str,
    *,
    previous_close=None,
    budget=None,
    clock=None,
):
    """Buduje prawdziwy RuntimeService z kontrolnymi wrapperami granic.

    Używa produkcyjnego composition root (entrypoint.build_runtime_service) na
    izolowanej kopii bazy. Overlay nałożony przez ControlledYahooSession i
    wrappery budżetów Tavily/OpenAI/Telegram są jedynymi delegującymi zmianami
    na granicach zewnętrznych.
    """
    from application import entrypoint

    budget = budget or YahooBudgetGuard()
    controlled_session = ControlledYahooSession(
        real_yahoo_session,
        budget,
        previous_close=previous_close,
        symbol=symbol,
        clock=clock,
    )

    runtime = entrypoint.build_runtime_service(
        persist_path=cfg.isolated_db_path,
        yahoo_session=controlled_session,
        source_kind=None,  # dynamic — but source substitued below via additive DI
        controlled_source=single_source,
    )

    # Delegujące wrappery zewnętrznych granic (bez zmiany prawdziwych klientów).
    tavily_guard = TavilyBudgetGuard()
    openai_guard = OpenAIBudgetGuard()
    telegram_guard = TelegramBudgetGuard()

    adapter = getattr(runtime.master_engine, "_tavily_adapter", None)
    if adapter is not None:
        runtime.master_engine._tavily_adapter = GuardedTavilyAdapter(
            adapter, tavily_guard
        )
    provider = getattr(runtime.master_engine, "openai_provider", None)
    if provider is not None:
        runtime.master_engine.openai_provider = GuardedOpenAIProvider(
            provider, openai_guard
        )
    if runtime.telegram_channel is not None:
        runtime.telegram_channel = GuardedTelegramChannel(
            runtime.telegram_channel, telegram_guard
        )

    # Produkcyjny cykl matrycy (jak w entrypoint.main()) — dokładnie jedno
    # wywołanie run_cycle() wykona prawdziwy pipeline.
    runtime.production_matrix_cycle = True
    # Jawny uchwyt kontrolnej sesji Yahoo z composition root - bez
    # prywatnego lancucha RuntimeService.market_scanner._provider._session.
    return runtime, controlled_session


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="alchemik-controlled-validation",
        description=(
            "ALCHEMIK CONTROLLED_VALIDATION_ONLY — wymaga dwóch jawnych flag "
            "(--allow-network --confirm-step7); nie jest sygnałem inwestycyjnym."
        ),
    )
    parser.add_argument("--allow-network", action="store_true",
                        help="wymagana flaga zgody na jednorazową sieć")
    parser.add_argument("--confirm-step7", action="store_true",
                        help="wymagana flaga potwierdzenia trybu kontrolnego")
    parser.add_argument("--isolated-db", type=Path, required=True,
                        help="izolowana kopia produkcyjnej bazy (musi istnieć)")
    parser.add_argument("--artifacts-dir", type=Path, required=True,
                        help="katalog artefaktów POZA repo (marker, licznik, raport)")
    args = parser.parse_args(argv)

    if not (args.allow_network and args.confirm_step7):
        print(
            "BŁĄD: tryb CONTROLLED_VALIDATION_ONLY wymaga dwóch jawnych flag "
            "--allow-network i --confirm-step7. Bez obu flag nie wykonano "
            "żadnego efektu (bez sekretów, klientów, zapisywalnej bazy, "
            "markera, RuntimeService i sieci).",
            file=sys.stderr,
        )
        return 2

    cfg = ControlledValidationConfig(
        isolated_db_path=args.isolated_db,
        artifacts_dir=args.artifacts_dir,
        production_db_path=PROD_DB,
        allow_network=True,
        confirm_step7=True,
    )
    try:
        cfg = ensure_safe_paths(cfg)
    except ValueError as exc:
        print(f"BŁĄD ścieżek: {exc}", file=sys.stderr)
        return 3

    # Marker tworzony dopiero po preflight (już zaakceptowanym), PRZED siecią.
    try:
        ensure_once_marker(cfg.artifacts_dir)
    except RuntimeError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 4

    from data.yahoo.yahoo_transport import CurlCffiTransport
    from data.yahoo.yahoo_session import YahooSession

    # Jedyna fabryka sieciowa — wykonywana wyłącznie po obu flagach.
    real_session = YahooSession(CurlCffiTransport())

    from application.controlled_validation import ControlledValidationController

    controller = ControlledValidationController(
        cfg=cfg,
        runtime_factory=lambda: None,  # faktyczny runtime buduje _build_runtime_guarded
        real_yahoo_session=real_session,
    )
    result = controller.run()

    # Krok 7G: trwały eksport kontrolowanego trace — dokładnie jeden zapis
    # po pojedynczym run(), bez ponownego cyklu i bez sekretów.
    write_controlled_trace_json(result, args.artifacts_dir)

    print(f"STATUS: {result.get('status')}")
    print(f"TRACE overall: {result.get('trace', {}).get('overall_status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())