# ALCHEMIK — CHECK POINT

## Status projektu

| Atrybut | Wartość |
|---------|---------|
| Status projektu | **AKTYWNY** |
| Aktualny etap | **FAZA 2 ETAPU 6** (ukończona, zamrożona) |
| Ukończone etapy | ETAP 1, ETAP 2, ETAP 3, ETAP 4, ETAP 5, FAZA 1 ETAPU 6, FAZA 2 ETAPU 6 |
| Zamrożone etapy | ETAP 1, ETAP 2, ETAP 3, ETAP 4, ETAP 5, FAZA 1 ETAPU 6, FAZA 2 ETAPU 6 |
| Ostatni commit | `22a7108` (23.07.2026) |
| Branch | `master` |
| Data ostatniego commita | 23.07.2026 |
| Liczba testów backendu | **42** plików testowych w `tests/` |
| Liczba testów frontendu | **10** plików testowych w `dashboard/src/` (w podkatalogach `api/__tests__/`, `components/__tests__/`, `hooks/__tests__/`, `views/__tests__/`, `__tests__/`) |

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

## Zamrożone moduły (architektura rdzenia)

Wszystkie moduły powyżej są zamrożone zgodnie z zasadą zamrożenia architektury projektu.

## Lista zamrożonych modułów

- `application/` — cała warstwa aplikacyjna
- `config/` — wszystkie konfiguracje
- `data/` — modele danych, źródła danych
- `engines/` — wszystkie silniki (ai, analyst, hunter, master, news, price_detector, ranking, risk, technical, volume_detector)
- `tests/` — wszystkie testy (29 plików)
- `scripts/` — skrypty diagnostyczne
- `dashboard/` — cały frontend React

## Następny planowany etap

**ETAP 7** — rozbudowa alertów, dashboard zdarzeniowy, ocena jakości zdarzeń (Critical/High/Medium/Low/Ignore), scalanie zdarzeń (Composite Events).

Szczegóły zostaną określone w dokumentacji planistycznej ETAPU 7.

## Daty

| Zdarzenie | Data |
|-----------|------|
| Ostatnia aktualizacja dokumentacji | 23.07.2026 |
| Zamrożenie ETAPU 5 | 22.07.2026 |
| Zamrożenie FAZY 1 ETAPU 6 (MarketEvent Pipeline) | 23.07.2026 |
| Zamrożenie FAZY 2 ETAPU 6 (Detektory + Integracja MasterEngine) | 23.07.2026 |
