# ALCHEMIK — GŁÓWNA DOKUMENTACJA PROJEKTU

## Status dokumentu

| Atrybut | Wartość |
|---------|---------|
| Data | 22.07.2026 |
| Wersja | 1.0 |
| Status | **AKTUALNY — zgodny z kodem** |
| Bazuje na | rzeczywistym stanie repozytorium (commit `2311de6`) |

---

## 1. Opis projektu

**ALCHEMIK** to profesjonalna platforma do analizy rynku akcji, ze szczególnym naciskiem na spółki typu Penny Stocks (groszówki). System został zaprojektowany jako inteligentny szperacz giełdowy — monitoruje rynek 24/7, wykrywa nietypowe zdarzenia, analizuje je i dostarcza inwestorowi kompletny obraz sytuacji.

ALCHEMIK **nie jest botem inwestycyjnym**. System nie podejmuje decyzji za inwestora, nie wydaje rekomendacji BUY/SELL. Ostateczna decyzja inwestycyjna zawsze należy do użytkownika.

---

## 2. Filozofia projektu

Szczegółowa filozofia działania znajduje się w `docs/FILOZOFIA_ALCHEMIKA.md`.

Kluczowe założenia:
- **Monitoring rynku 24/7** — ciągłe śledzenie instrumentów finansowych
- **Wykrywanie nietypowych zdarzeń** — identyfikacja sytuacji istotnych dla inwestora
- **Czas reakcji** — szybkie wykrycie i poinformowanie daje przewagę
- **Analiza łączna** — cena i wolumen analizowane razem, z uwzględnieniem kontekstu
- **AI jako narzędzie** — AI interpretuje dane, nie podejmuje decyzji
- **Rola inwestora** — ostateczna decyzja należy do człowieka

---

## 3. Cele projektu

1. Zapewnienie inwestorom przewagi czasowej poprzez ciągłe monitorowanie rynku
2. Wykrywanie nietypowych zdarzeń rynkowych w czasie rzeczywistym
3. Automatyczna analiza techniczna, fundamentalna i kontekstowa
4. Dostarczanie kompleksowych raportów przez Telegram
5. Prezentacja danych przez responsywny Dashboard webowy

---

## 4. Architektura systemu

### 4.1 Warstwy

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React SPA)                      │
│                    dashboard/                                │
├─────────────────────────────────────────────────────────────┤
│                    API (FastAPI)                             │
│                    application/api_entrypoint.py             │
├─────────────────────────────────────────────────────────────┤
│                    WARSTWA APLIKACYJNA                       │
│                    application/                              │
├─────────────────────────────────────────────────────────────┤
│                    SILNIKI (engines/)                        │
│  technical │ news │ ai │ ranking │ risk │ hunter │ analyst  │
├─────────────────────────────────────────────────────────────┤
│                    DANE (data/)                              │
│  yahoo │ tavily │ cache │ models                            │
├─────────────────────────────────────────────────────────────┤
│                    SQLITE                                    │
│                    data/runtime/                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Architektura przepływu danych

```
Runtime → SQLite → ReadService → FastAPI → HTTP → Frontend
```

---

## 5. Silniki (engines/)

### 5.1 Technical Engine (`engines/technical/`)
- **Cel**: Analiza techniczna danych OHLCV
- **Wskaźniki**: SMA, EMA, RSI, MACD, ATR, Bollinger Bands, OBV, VWAP, RVOL, Fibonacci
- **Formacje świecowe**: młot, wisielec, objęcia, gwiazdy, marubozu
- **Detektory**: Price Detector, Volume Detector

### 5.2 News Engine (`engines/news/`)
- **Cel**: Monitorowanie i przetwarzanie wiadomości
- **Komponenty**: pipeline, cleaner, filter, cache

### 5.3 AI Engine (`engines/ai/`)
- **Cel**: Wykorzystanie sztucznej inteligencji do analizy
- **Komponenty**: DecisionEngine, Pipeline, Analyzer, AIProvider, PromptBuilder
- **Zasada**: AI interpretuje dane, nie podejmuje decyzji inwestycyjnych

### 5.4 Ranking Engine (`engines/ranking/`)
- **Cel**: Ocena i rankingowanie danych

### 5.5 Risk Engine (`engines/risk/`)
- **Cel**: Ocena ryzyka (risk_score, risk_level, stop_loss, take_profit)

### 5.6 Hunter Engine (`engines/hunter/`)
- **Cel**: Gromadzenie surowych danych z Yahoo Finance

### 5.7 Analyst Engine (`engines/analyst/`)
- **Cel**: Generowanie końcowej analizy (FinalAnalysisResult)

### 5.8 Master Engine (`engines/master/`)
- **Cel**: Orkiestracja pipeline'u analizy dla jednego instrumentu
- **Sekwencja**: Technical → News → Decision → Ranking → Risk → Hunter → Analyst

### 5.9 Price Detector (`engines/price_detector/`)
- **Cel**: Wykrywanie zdarzeń cenowych (w ramach TechnicalEngine)

### 5.10 Volume Detector (`engines/volume_detector/`)
- **Cel**: Wykrywanie zdarzeń wolumenowych (w ramach TechnicalEngine)

---

## 6. Warstwa danych (`data/`)

| Moduł | Opis |
|-------|------|
| `data/yahoo/` | YahooFinanceFetcher, wyjątki |
| `data/tavily/` | Integracja z API Tavily |
| `data/models/` | Modele danych: MarketEvent, PriceData, VolumeData, HistoryEntry, AnalysisResult, RankingResult, RiskResult, HunterResult, FinalAnalysisResult, AISignal, CompanyInfo, NewsItem, MarketData, EventEnums |

### Modele danych — szczegóły

| Model | Plik | Opis |
|-------|------|------|
| MarketEvent | `data/models/market_event.py` | Główny obiekt zdarzenia rynkowego (27 pól) |
| PriceData | `data/models/price_data.py` | Dane cenowe OHLCV |
| VolumeData | `data/models/volume_data.py` | Dane wolumenowe |
| HistoryEntry | `data/models/history_entry.py` | Wpis historii zdarzenia |
| EventEnums | `data/models/event_enums.py` | Enumeracje dla zdarzeń |
| MarketData | `data/models/market_data.py` | Ogólne dane rynkowe |
| CompanyInfo | `data/models/company_info.py` | Informacje o spółce |
| NewsItem | `data/models/news_item.py` | Pojedynczy news |
| AISignal | `data/models/ai_signal.py` | Sygnał z AI |
| AnalysisResult | `data/models/analysis_result.py` | Wynik analizy |
| FinalAnalysisResult | `data/models/final_analysis_result.py` | Końcowy wynik analizy |
| RankingResult | `data/models/ranking_result.py` | Wynik rankingu |
| FullRanking | `data/models/full_ranking.py` | Pełny ranking |
| RiskResult | `data/models/risk_result.py` | Wynik oceny ryzyka |
| HunterResult | `data/models/hunter_result.py` | Wynik skanowania |

### Kontrakt zdarzeń rynkowych

Szczegółowy kontrakt wymiany danych pomiędzy modułami znajduje się w `docs/Kontrakt_Zdarzen_Rynkowych.md`.

Obiekt `MarketEvent` zawiera 27 pól, przechodzi przez 13 etapów cyklu życia, obsługiwany przez 11 modułów z jasno określoną odpowiedzialnością.

---

## 7. Warstwa aplikacyjna (`application/`)

| Moduł | Opis |
|-------|------|
| `runtime.py` | RuntimeService — główna pętla cyklu |
| `scheduler.py` | Scheduler — interval-based scheduling |
| `entrypoint.py` | Entry point dla Runtime |
| `api_entrypoint.py` | Entry point dla API FastAPI |
| `universe.py` | Universe — lista dozwolonych instrumentów |
| `market_scanner.py` | MarketScanner — skanowanie rynku |
| `opportunity_deduplicator.py` | Deduplikacja zdarzeń |
| `alert_builder.py` | Budowanie alertów |
| `alert_dispatcher.py` | Wysyłanie alertów |
| `history_repository.py` | Interfejs repozytorium historii |
| `sqlite_history_repository.py` | Implementacja SQLite HistoryRepository |
| `read_service.py` | RuntimeReadService — odczyt danych |
| `dashboard_read_service.py` | DashboardReadService — agregacje dashboardowe |
| `models.py` | Modele warstwy aplikacyjnej |
| `channels/telegram_channel.py` | Kanał Telegram |

---

## 8. API

**Framework**: FastAPI (async)
**Serwer**: Uvicorn
**Port**: 8000

### Endpointy

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| GET | `/health` | Status API i bazy danych |
| GET | `/api/v1/runtime/statistics` | Statystyki Runtime |
| GET | `/api/v1/cycles` | Lista cykli (paginated) |
| GET | `/api/v1/cycles/{cycle_id}` | Szczegóły cyklu |
| GET | `/api/v1/dashboard` | Zagregowany widok dashboardu |
| GET | `/api/v1/market-events` | Lista MarketEvents z filtrami |
| GET | `/api/v1/market-events/{event_id}` | Szczegóły MarketEvent |
| GET | `/api/v1/tickers/{ticker}/market-events` | Eventy dla tickera |

Szczegółowa dokumentacja API: `docs/API_README.md`

---

## 9. Frontend (Dashboard)

**Technologia**: React 18 + Vite 5 + TypeScript + CSS Modules

### Widoki

| Widok | Plik | Opis |
|-------|------|------|
| DashboardView | `dashboard/src/views/DashboardView.tsx` | Główny widok z podsumowaniem |
| HealthView | `dashboard/src/views/HealthView.tsx` | Status API i bazy danych |
| MarketEventsView | `dashboard/src/views/MarketEventsView.tsx` | Lista zdarzeń z filtrami |

### Komponenty

- Navigation — responsywny pasek nawigacji
- StatusBar — status API online/offline
- LoadingSpinner — wskaźnik ładowania
- ErrorBanner — komunikat błędu
- EmptyState — pusty wynik
- DashboardCard — karta KPI

### Hooks

- `useApiHealth` — monitoring statusu API
- `useDashboard` — pobieranie danych dashboardu
- `useMarketEvents` — pobieranie listy zdarzeń

### API Client

- `api/client.ts` — wrapper fetch z timeoutem
- `api/config.ts` — konfiguracja endpointów
- `api/api.ts` — funkcje mapujące endpointy
- `api/types.ts` — TypeScript interfejsy

Szczegółowa architektura frontendu: `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md`

---

## 10. Backend

**Język**: Python 3.12+
**Framework**: FastAPI
**Baza danych**: SQLite (WAL mode)
**Źródła danych**: Yahoo Finance (yfinance), Tavily API

### Zależności (Python)

- fastapi, uvicorn — serwer API
- yfinance — dane rynkowe
- openai — integracja AI
- tavily-python — wyszukiwanie
- pandas, numpy, plotly — analiza danych
- aiosqlite — asynchroniczny SQLite
- httpx — klient HTTP

---

## 11. SQLite

**Lokalizacja**: `data/runtime/alchemik_runtime.db`
**Tryb**: WAL (Write-Ahead Logging) dla bezpiecznego współbieżnego dostępu
**Tabele**: `cycles`, `market_events`

---

## 12. AI

**Komponenty**:
- `engines/ai/decision_engine.py` — decyzja o użyciu AI
- `engines/ai/pipeline.py` — pipeline AI
- `engines/ai/analyzer.py` — analiza AI
- `engines/ai/ai_provider.py` — provider AI (OpenAI)
- `engines/ai/prompt_builder.py` — budowanie promptów

**Zasada**: AI jest uruchamiana wyłącznie dla zdarzeń o priorytecie Critical/High, wymagających interpretacji kontekstu.

---

## 13. Telegram

**Komponenty**:
- `application/alert_builder.py` — decyzja o alercie
- `application/alert_dispatcher.py` — wysyłka alertu
- `application/channels/telegram_channel.py` — integracja z Telegram API

**Warunki wysyłki**: final_rating ≥ 70, confidence ≥ 70%, rekomendacja STRONG_BUY lub BUY.

---

## 14. Testy

**Backend**: 28 plików testowych w `tests/`
**Frontend**: 10 plików testowych w `dashboard/src/` (w podkatalogach `api/__tests__/`, `components/__tests__/`, `hooks/__tests__/`, `views/__tests__/`, `__tests__/`)

### Lista testów backendu

| Plik | Opis |
|------|------|
| `test_ai_pipeline_integration.py` | Integracja pipeline AI |
| `test_alert_builder.py` | Alert builder |
| `test_alert_dispatcher.py` | Alert dispatcher |
| `test_analyst_engine.py` | Analyst engine |
| `test_dashboard_api.py` | Dashboard API |
| `test_dashboard_repository.py` | Dashboard repository |
| `test_dashboard_service.py` | Dashboard service |
| `test_decision_engine.py` | Decision engine |
| `test_history_repository.py` | History repository |
| `test_hunter_engine.py` | Hunter engine |
| `test_market_event_models.py` | Market event models |
| `test_market_scanner.py` | Market scanner |
| `test_master_engine.py` | Master engine |
| `test_master_engine_e2e.py` | Master engine E2E |
| `test_opportunity_deduplicator.py` | Opportunity deduplicator |
| `test_price_detector.py` | Price detector |
| `test_ranking_engine.py` | Ranking engine |
| `test_read_api.py` | Read API |
| `test_risk_engine.py` | Risk engine |
| `test_runtime.py` | Runtime |
| `test_scheduler.py` | Scheduler |
| `test_sqlite_history_repository.py` | SQLite history repository |
| `test_static_instrument_source.py` | Static instrument source |
| `test_telegram_channel.py` | Telegram channel |
| `test_universe.py` | Universe |
| `test_volume_detector.py` | Volume detector |
| `test_yahoo_fetcher.py` | Yahoo fetcher |
| `test_yahoo_scan_provider.py` | Yahoo scan provider |

---

## 15. Struktura katalogów

```
c:\alchemik\
├── .clinerules                 # Zasady pracy Cline
├── ALCHEMIK_CHECK.md            # Check point projektu
├── ALCHEMIK_PROJEKT.md          # Główna dokumentacja projektu (ten plik)
├── README.md                    # Podstawowe info
├── requirements.txt             # Zależności Python
├── struktura_alchemik.txt       # Struktura katalogów (wygenerowana)
├── struktura_runtime.txt        # Struktura runtime (wygenerowana)
│
├── application/                 # Warstwa aplikacyjna
│   ├── runtime.py              # RuntimeService
│   ├── scheduler.py            # Scheduler
│   ├── entrypoint.py           # Entry point Runtime
│   ├── api_entrypoint.py       # Entry point API
│   ├── universe.py             # Universe instrumentów
│   ├── market_scanner.py       # Skaner rynku
│   ├── opportunity_deduplicator.py
│   ├── alert_builder.py
│   ├── alert_dispatcher.py
│   ├── history_repository.py
│   ├── sqlite_history_repository.py
│   ├── read_service.py
│   ├── dashboard_read_service.py
│   ├── models.py
│   └── channels/
│       └── telegram_channel.py
│
├── config/                      # Konfiguracje
│   ├── analyst.py
│   ├── hunter.py
│   ├── indicators.py
│   ├── ranking.py
│   ├── risk.py
│   ├── price_detector.py
│   └── volume_detector.py
│
├── dashboard/                   # Frontend React
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                # Warstwa API frontendu
│       ├── components/         # Komponenty UI
│       ├── hooks/              # Hooki React
│       ├── styles/             # Style globalne
│       └── views/              # Widoki
│
├── data/                        # Warstwa danych
│   ├── cache/
│   ├── runtime/                 # Baza SQLite
│   ├── models/                  # Modele danych
│   ├── tavily/                  # Integracja Tavily
│   └── yahoo/                   # Integracja Yahoo Finance
│
├── docs/                        # Dokumentacja
│   ├── API_README.md
│   ├── ETAP_5_ARCHITEKTURA_FRONTENDU.md
│   ├── FILOZOFIA_ALCHEMIKA.md
│   ├── Hierarchia_Zdarzen_Rynkowych.md
│   ├── INSTRUKCJA_DLA_CLINE.md
│   ├── Katalog_Zdarzen_Rynkowych.md
│   ├── Kontrakt_Zdarzen_Rynkowych.md
│   ├── Przeplyw_Danych.md
│   ├── Przeplyw_Zdarzen_Rynkowych.md
│   └── ZASADY_PROJEKTU.md
│
├── engines/                     # Silniki
│   ├── ai/                     # AI Engine
│   ├── analyst/                # Analyst Engine
│   ├── hunter/                 # Hunter Engine
│   ├── master/                 # Master Engine
│   ├── news/                   # News Engine
│   ├── price_detector/         # Price Detector
│   ├── ranking/                # Ranking Engine
│   ├── risk/                   # Risk Engine
│   ├── technical/              # Technical Engine
│   │   └── indicators/         # Wskaźniki techniczne
│   └── volume_detector/        # Volume Detector
│
├── scripts/                     # Skrypty
│   ├── diagnose_candidate_flow.py
│   ├── diagnose_market_pipeline.py
│   ├── diagnose_yahoo.py
│   ├── read_stored_data.py
│   ├── run_market_test.py
│   ├── smoke_test_persistence.py
│   ├── test_persistence_restart.py
│   └── test_telegram_integration.py
│
├── tests/                       # Testy (28 plików)
│
├── cache/                       # Cache (pusty — znacznik)
├── database/                    # Database (pusty — znacznik)
├── logs/                        # Logs (pusty — znacznik)
├── notifications/               # Notifications (pusty — znacznik)
└── utils/                       # Utils (pusty — znacznik)
```

---

## 16. Ukończone etapy

### ETAP 1 — Detektory ceny i wolumenu
- Implementacja Price Detector i Volume Detector
- Porządek w repozytorium
- **Commit**: `a807131`

### ETAP 2 — Trwały przepływ Runtime i MarketEvent do SQLite
- RuntimeService, Scheduler
- SQLiteHistoryRepository
- MarketEvent persistence
- **Commit**: `5c8651d`

### ETAP 3 — Read Service i minimalne API HTTP
- RuntimeReadService
- FastAPI endpoints
- **Commit**: `e2b9fe8`

### ETAP 4 — Dashboard API i agregacje odczytu
- DashboardReadService
- Agregacje w SQLite
- Endpoint `/api/v1/dashboard`
- **Commit**: `96d194e`

### ETAP 5 — Architektura responsywnego frontendu
- DashboardView, MarketEventsView, HealthView
- Komponenty UI (Navigation, StatusBar, LoadingSpinner, ErrorBanner, EmptyState, DashboardCard)
- Hooks (useApiHealth, useDashboard, useMarketEvents)
- API Client (client, config, api, types)
- **Commit**: `2311de6`

### FAZA 2 ETAPU 6 — Implementacja wszystkich detektorów zdarzeń rynkowych i integracja z MasterEngine
- Implementacja frameworka detektorów: `BaseDetector`, `DetectionContext`, `DetectionResult`, `DetectorRegistry`, `DetectorOrchestrator`
- Implementacja 11 detektorów: Technical, Fundamental, Corporate, Regulatory, Macro, ETF, Derivatives, Sentiment, System (+ istniejące Price i Volume)
- Konfiguracje progów: `technical_events.py`, `fundamental_events.py`, `corporate_events.py`, `macro_events.py`, `etf_events.py`, `sentiment_events.py`
- Integracja wszystkich detektorów z `MasterEngine` przez `DetectorOrchestrator`
- Testy jednostkowe i integracyjne dla wszystkich detektorów
- **Status**: ✅ Zakończony i zamrożony (23.07.2026)

---

## 17. Zamrożone etapy

Wszystkie etapy od ETAP 1 do ETAP 5 oraz FAZA 1 i FAZA 2 ETAPU 6 są zamrożone. Zgodnie z zasadami projektu, architektura rdzenia nie może być modyfikowana bez świadomej decyzji projektowej.

### FAZA 1 ETAPU 6 — Integracja MarketEvent jako centralnego obiektu pipeline
- `DecisionEngine.process_event(MarketEvent)` jako kanoniczny kontrakt wejściowy
- Mapowanie `technical_context` z `AnalysisResult.indicators` do `MarketEvent`
- `process_data(dict)` jako adapter kompatybilności wstecznej
- Wspólna fabryka `_build_aisignal()` — jedna logika wykonania
- Testy akceptacyjne: 7 testów
- **Status**: ✅ Zakończony i zamrożony (23.07.2026)

### FAZA 2 ETAPU 6 — Implementacja wszystkich detektorów zdarzeń rynkowych i integracja z MasterEngine
- Framework detektorów (`BaseDetector`, `DetectionContext`, `DetectionResult`, `DetectorRegistry`, `DetectorOrchestrator`)
- 11 detektorów (Technical, Fundamental, Corporate, Regulatory, Macro, ETF, Derivatives, Sentiment, System + Price, Volume)
- Konfiguracje progów dla 6 rodzin zdarzeń
- Integracja z `MasterEngine` przez `DetectorOrchestrator`
- Testy jednostkowe i integracyjne
- **Status**: ✅ Zakończony i zamrożony (23.07.2026)

---

## 18. Roadmapa projektu

| Etap | Status | Opis |
|------|--------|------|
| ETAP 1 | ✅ Zamrożony | Detektory ceny i wolumenu |
| ETAP 2 | ✅ Zamrożony | Runtime → SQLite |
| ETAP 3 | ✅ Zamrożony | Read Service + API |
| ETAP 4 | ✅ Zamrożony | Dashboard API |
| ETAP 5 | ✅ Zamrożony | Frontend React |
| FAZA 1 ETAPU 6 | ✅ Zamrożony | Integracja MarketEvent jako centralnego obiektu pipeline |
| FAZA 2 ETAPU 6 | ✅ Zamrożony | Implementacja wszystkich detektorów i integracja z MasterEngine |

---

## 19. Aktualny stan projektu

- Backend: kompletny, zamrożony
- Frontend: kompletny, zamrożony
- API: kompletne, zamrożone
- FAZA 1 ETAPU 6: zakończony i zamrożony (23.07.2026)
- FAZA 2 ETAPU 6: zakończony i zamrożony (23.07.2026)
- Detektory: 11 detektorów — wszystkie zaimplementowane, przetestowane i zamrożone
- Testy: testy jednostkowe i integracyjne dla wszystkich detektorów + istniejące testy projektu
- Dokumentacja: zaktualizowana
- Ostatnia aktualizacja: 23.07.2026
- Branch: `master`

---

## 20. Następny etap

**ETAP 7** — rozbudowa alertów, dashboard zdarzeniowy, ocena jakości zdarzeń, scalanie zdarzeń (Composite Events).

Szczegóły zostaną określone w dokumentacji planistycznej ETAPU 7.
---

## 21. Dokumenty projektu

| Dokument | Lokalizacja | Opis |
|----------|-------------|------|
| Filozofia | `docs/FILOZOFIA_ALCHEMIKA.md` | Filozofia działania |
| Zasady projektu | `docs/ZASADY_PROJEKTU.md` | Zasady realizacji |
| Instrukcja Cline | `docs/INSTRUKCJA_DLA_CLINE.md` | Zasady pracy dla Cline |
| Przepływ danych | `docs/Przeplyw_Danych.md` | Przepływ między silnikami |
| Katalog zdarzeń | `docs/Katalog_Zdarzen_Rynkowych.md` | 157 typów zdarzeń |
| Hierarchia zdarzeń | `docs/Hierarchia_Zdarzen_Rynkowych.md` | Klasyfikacja zdarzeń |
| Przepływ zdarzeń | `docs/Przeplyw_Zdarzen_Rynkowych.md` | Cykl życia zdarzenia |
| Kontrakt zdarzeń | `docs/Kontrakt_Zdarzen_Rynkowych.md` | Standard wymiany danych |
| API README | `docs/API_README.md` | Dokumentacja API |
| ETAP 5 Frontend | `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md` | Architektura frontendu |
| ETAP 6 | `docs/ETAP_6_ARCHITEKTURA.md` | Plan ETAPU 6 |
| Check point | `ALCHEMIK_CHECK.md` | Status projektu |
| Projekt | `ALCHEMIK_PROJEKT.md` | Główna dokumentacja (ten plik) |

---

## KONIEC DOKUMENTU