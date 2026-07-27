# ALCHEMIK — CHECK POINT

## Status projektu

| Atrybut | Wartość |
|---------|---------|
| Status projektu | **AKTYWNY** |
| Aktualny etap | **ETAP 7.5** (zakończony, nie zamrożony) |
| Ukończone etapy | ETAP 1, ETAP 2, ETAP 3, ETAP 4, ETAP 5, FAZA 1 ETAPU 6, FAZA 2 ETAPU 6 |
| Zamrożone etapy | ETAP 1, ETAP 2, ETAP 3, ETAP 4, ETAP 5, FAZA 1 ETAPU 6, FAZA 2 ETAPU 6 |
| Etapy w trakcie | ETAP 7 (zaimplementowane podetapy 7.1–7.5; podetapy 7.6–7.7 nierozpoczęte) |
| Ostatni commit | `6670061` (27.07.2026) — FAZA 2 ETAP 6: zakończenie i zamrożenie |
| Branch | `master` |
| Data ostatniego commita | 27.07.2026 |
| Liczba testów backendu | **1104** testów (pytest) — wszystkie przechodzą |
| Liczba testów frontendu | **10** plików testowych w `dashboard/src/` (build frontendu przechodzi; testy jednostkowe Vitest mają problemy infrastrukturalne niezwiązane z ETAP 7.5) |

## Status modułów

| Moduł | Status | Uwagi |
|-------|--------|-------|
| **Backend (Python)** | ✅ Zamrożony | Kompletna architektura 7 silników + warstwa aplikacyjna |
| **Frontend (React)** | ✅ Zamrożony | SPA w `dashboard/`, zaimplementowane widoki DashboardView, MarketEventsView, HealthView, komponenty UI |
| **API (FastAPI)** | ✅ Zamrożony | REST API na porcie 8000, endpointy: /health, /api/v1/dashboard, /api/v1/market-events, /api/v1/cycles, /api/v1/tickers |
| **Runtime** | ✅ Zamrożony | Cykliczne uruchamianie pipeline'u MasterEngine przez Scheduler |
| **Scheduler** | ✅ Zamrożony | Interval-based scheduling cykli analizy |
| **SQLite** | ✅ Zamrożony | Baza danych z WAL mode, współdzielona między Runtime a API |
| **Dashboard** | ✅ Zamrożony | DashboardReadService z agregacjami po stronie SQLite |
| **AI Engine** | ✅ Zamrożony | DecisionEngine, Pipeline, Analyzer, AIProvider, PromptBuilder |
| **Technical Engine** | ✅ Zamrożony | Wskaźniki: SMA, EMA, RSI, MACD, ATR, BB, OBV, VWAP, RVOL, Fibonacci + detekcja formacji świecowych |
| **News Engine** | ✅ Zamrożony | Pipeline, cleaner, filter, cache |
| **Ranking Engine** | ✅ Zamrożony | Ocena i rankingowanie danych |
| **Risk Engine** | ✅ Zamrożony | Ocena ryzyka: risk_score, risk_level, stop_loss, take_profit |
| **Hunter Engine** | ✅ Zamrożony | Gromadzenie danych z Yahoo Finance |
| **Analyst Engine** | ✅ Zamrożony | Generowanie końcowej analizy |
| **Master Engine** | ✅ Zamrożony | Orkiestracja pipeline'u analizy, przekazuje MarketEvent do DecisionEngine |
| **DecisionEngine** | ✅ Zamrożony | Kanoniczny kontrakt: process_event(MarketEvent), adapter process_data(dict) |
| **Price Detector** | ✅ Zamrożony | Wykrywanie zdarzeń cenowych, tworzy MarketEvent |
| **Volume Detector** | ✅ Zamrożony | Wykrywanie zdarzeń wolumenowych, tworzy MarketEvent |
| **Universe** | ✅ Zamrożony | Lista dozwolonych instrumentów |
| **Market Scanner** | ✅ Zamrożony | Skanowanie rynku, dostarcza OHLCV do pipeline |
| **Opportunity Deduplicator** | ✅ Zamrożony | Deduplikacja zdarzeń |
| **Alert Builder** | ✅ Zamrożony | Decyzja o wysłaniu alertu |
| **Alert Dispatcher** | ✅ Zamrożony | Wysyłka alertów przez kanały |
| **Telegram Channel** | ✅ Zamrożony | Integracja z Telegram API |
| **Detector Framework** | ✅ Zamrożony | BaseDetector, DetectionContext, DetectionResult, DetectorRegistry, DetectorOrchestrator |
| **Detektory (9 nowych)** | ✅ Zamrożony | Technical, Fundamental, Corporate, Regulatory, Macro, ETF, Derivatives, Sentiment, System |
| **TechnicalIntegrator** | 🔄 ETAP 7 | Warstwa integracyjna MarketEvent → TechnicalEngine. Wyłącznie do Manual Analysis, NIE w pipeline automatycznym. Używa Public API, nie modyfikuje zamrożonych silników. |
| **QualityEngine** | 🔄 ETAP 7 | engines/quality/ — ocena jakości zdarzeń (quality_level), ETAP 7.2 |
| **ComposerEngine** | 🔄 ETAP 7 | engines/composer/ — scalanie zdarzeń w Composite Events, ETAP 7.3 |
| **PipelineDecision** | 🔄 ETAP 7 | data/models/pipeline_decision.py — model decyzji pipeline'u, ETAP 7.4 |
| **CompositeEvent** | 🔄 ETAP 7 | data/models/composite_event.py — model zdarzeń złożonych, ETAP 7.3 |

## Status ETAPU 7

ETAP 7 został wstrzymany na podetapie **7.4 (DecisionEngine)**. Poniżej status poszczególnych podetapów:

| Podetap | Status | Opis |
|---------|--------|------|
| 7.1 Specyfikacja | ✅ Ukończony | `docs/ETAP_7_PLAN.md` — plan i podział na podetapy |
| 7.2 Quality Assessment | ✅ Zaimplementowany | `engines/quality/engine.py`, `config/quality.py`, `tests/test_quality_engine.py` |
| 7.3 Composite Events | ✅ Zaimplementowany | `engines/composer/engine.py`, `data/models/composite_event.py`, `config/composer.py`, `tests/test_composer_engine.py`, `tests/test_composite_event.py` |
| 7.4 DecisionEngine | ✅ Zaimplementowany | `DecisionEngine.decide_pipeline()`, `data/models/pipeline_decision.py`, `tests/test_pipeline_decision.py`, `tests/test_decision_engine.py` (rozbudowane) |
| 7.5 Alerty | ✅ Zaimplementowany | Rozbudowa AlertBuilder i AlertDispatcher z integracją TelegramChannel (ETAP 7.5 + 7.5a + 7.5b) |
| 7.5a Testy Runtime | ✅ Zaimplementowany | Pełne pokrycie testowe integracji Runtime z systemem alertów |
| 7.5b Porządkowanie repo | ✅ Zakończony | Czyszczenie staging area, aktualizacja .gitignore, przygotowanie do commita |
| 7.6 Dashboard zdarzeniowy | ❌ Nierozpoczęty | Rozbudowa frontendu o filtry zdarzeń |
| 7.7 Testy i zamrożenie | ❌ Nierozpoczęty | Testy integracyjne pełnego pipeline'u + commit |

## Decyzje architektoniczne ETAPU 7

- **MasterEngine pozostaje głównym orkiestratorem** — wywołuje sekwencyjnie silniki, koordynuje przepływ danych.
- **TechnicalIntegrator wyłącznie dla Manual Analysis** — nie jest częścią automatycznego pipeline'u Runtime. Służy do ręcznej analizy technicznej pojedynczego MarketEvent.
- **Tavily po InitialAnalysisResult** — wyszukiwanie Tavily uruchamiane jest po wstępnej analizie, przed AI, zgodnie z zaakceptowaną architekturą.

## Zamrożone moduły (architektura rdzenia)

Wszystkie moduły ETAPÓW 1–6 są zamrożone zgodnie z zasadą zamrożenia architektury projektu. Moduły ETAPU 7 NIE są jeszcze zamrożone.

## Lista zamrożonych modułów

- `application/` — cała warstwa aplikacyjna (z wyjątkiem `technical_integrator.py`)
- `config/` — wszystkie konfiguracje (z wyjątkiem `composer.py`, `quality.py`)
- `data/` — modele danych, źródła danych (z wyjątkiem `composite_event.py`, `pipeline_decision.py`)
- `engines/` — wszystkie silniki (ai, analyst, hunter, master, news, price_detector, ranking, risk, technical, volume_detector, detectors, z wyjątkiem `composer/` i `quality/`)
- `tests/` — wszystkie testy (z wyjątkiem nowych testów ETAPU 7)
- `scripts/` — skrypty diagnostyczne
- `dashboard/` — cały frontend React

## Następny planowany etap

**ETAP 7.6** — rozbudowa dashboardu o widoki zdarzeniowe.

Szczegóły w `docs/ETAP_7_PLAN.md` §7.6.

## Daty

| Zdarzenie | Data |
|-----------|------|
| Ostatnia aktualizacja dokumentacji | 27.07.2026 |
| Zakończenie ETAPU 7.5 | 27.07.2026 |
| Zakończenie ETAPU 7.5a (testy Runtime) | 27.07.2026 |
| Zakończenie ETAPU 7.5b (porządkowanie repo) | 27.07.2026 |
| Zatrzymanie prac na ETAPIE 7.4 | 27.07.2026 |
| Zamrożenie ETAPU 5 | 22.07.2026 |
| Zamrożenie FAZY 1 ETAPU 6 (MarketEvent Pipeline) | 23.07.2026 |
| Zamrożenie FAZY 2 ETAPU 6 (Detektory + Integracja MasterEngine) | 27.07.2026 |
