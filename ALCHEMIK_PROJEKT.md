# ALCHEMIK — GŁÓWNA DOKUMENTACJA PROJEKTU

## Status dokumentu

| Atrybut | Wartość |
|---------|---------|
| Data | 27.07.2026 |
| Wersja | 1.1 |
| Status | **AKTUALNY — zgodny z kodem (ETAP 7.4)** |
| Bazuje na | rzeczywistym stanie repozytorium (commit `6670061`, stan roboczy ETAPU 7.4) |

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
│  master │ quality │ composer │ detectors │ price_detector   │
│  volume_detector                                              │
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

**Decyzje architektoniczne ETAPU 7:**
- **MasterEngine pozostaje głównym orkiestratorem** — wywołuje sekwencyjnie silniki, koordynuje przepływ danych
- **TechnicalIntegrator wyłącznie dla Manual Analysis** — nie jest częścią automatycznego pipeline'u Runtime
- **Tavily po InitialAnalysisResult** — wyszukiwanie Tavily uruchamiane po wstępnej analizie, przed AI

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
- **Uwaga**: MasterEngine pozostaje głównym orkiestratorem w architekturze ETAPU 7

### 5.9 Price Detector (`engines/price_detector/`)
- **Cel**: Wykrywanie zdarzeń cenowych (w ramach TechnicalEngine)

### 5.10 Volume Detector (`engines/volume_detector/`)
- **Cel**: Wykrywanie zdarzeń wolumenowych (w ramach TechnicalEngine)

### 5.11 Detector Framework (`engines/detectors/`)
- **Cel**: Wspólny interfejs dla wszystkich detektorów (BaseDetector, DetectionContext, DetectionResult, DetectorRegistry, DetectorOrchestrator)
- **Detektory**: Technical, Fundamental, Corporate, Regulatory, Macro, ETF, Derivatives, Sentiment, System (+ istniejące Price i Volume)
- **Status**: ✅ Zamrożony (FAZA 2 ETAPU 6)

### 5.12 Quality Engine (`engines/quality/`) — ETAP 7.2
- **Cel**: Ocena jakości zdarzeń — przypisywanie `quality_level` (Critical/High/Medium/Low/Ignore)
- **Konfiguracja**: `config/quality.py` — mapowanie `priority_raw` → `quality_level` dla GPW/USA/ETF, reguły promocji Composite
- **Status**: 🔄 ETAP 7.2 (zaimplementowany, nie zamrożony)

### 5.13 Composer Engine (`engines/composer/`) — ETAP 7.3
- **Cel**: Scalanie pokrewnych zdarzeń w Composite Events
- **Konfiguracja**: `config/composer.py` — okno czasowe scalania (60s), maksymalna liczba zdarzeń składowych (10)
- **Status**: 🔄 ETAP 7.3 (zaimplementowany, nie zamrożony)

---

## 6. Warstwa danych (`data/`)

| Moduł | Opis |
|-------|------|
| `data/yahoo/` | YahooFinanceFetcher, wyjątki |
| `data/tavily/` | Integracja z API Tavily |
| `data/models/` | Modele danych: MarketEvent, PriceData, VolumeData, HistoryEntry, AnalysisResult, RankingResult, RiskResult, HunterResult, FinalAnalysisResult, AISignal, CompanyInfo, NewsItem, MarketData, EventEnums, CompositeEvent, PipelineDecision |

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
| CompositeEvent | `data/models/composite_event.py` | Model zdarzeń złożonych — kontener danych z walidacją, serializacją i factory method `create()` (ETAP 7.3) |
| PipelineDecision | `data/models/pipeline_decision.py` | Decyzja o uruchomieniu pipeline'u (News/Tavily/AI) na podstawie quality_level (ETAP 7.4) |

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
| `technical_integrator.py` | TechnicalIntegrator — warstwa integracyjna MarketEvent → TechnicalEngine. Wyłącznie do Manual Analysis. Używa Public API, nie modyfikuje zamrożonych silników. (ETAP 7) |
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
- `engines/ai/decision_engine.py` — decyzja o użyciu AI. Rozbudowany w ETAPIE 7.4 o metodę `decide_pipeline(event) -> PipelineDecision`.
- `engines/ai/pipeline.py` — pipeline AI
- `engines/ai/analyzer.py` — analiza AI
- `engines/ai/ai_provider.py` — provider AI (OpenAI)
- `engines/ai/prompt_builder.py` — budowanie promptów

**Zasada**: AI jest uruchamiana wyłącznie dla zdarzeń o priorytecie Critical/High, wymagających interpretacji kontekstu. Decyzję podejmuje `DecisionEngine.decide_pipeline()` na podstawie `quality_level`.

---

## 13. Telegram

**Komponenty**:
- `application/alert_builder.py` — decyzja o alercie
- `application/alert_dispatcher.py` — wysyłka alertu
- `application/channels/telegram_channel.py` — integracja z Telegram API

**Warunki wysyłki**: final_rating ≥ 70, confidence ≥ 70%, rekomendacja STRONG_BUY lub BUY.

### 13.1 Decyzja architektoniczna — ETAP 7.5 — Integracja Telegram

**Status**: ZATWIERDZONA

ETAP 7.5 obejmuje pełną integrację systemu alertów z `TelegramChannel`.

**Zakres ETAPU 7.5:**

- `AlertBuilder` podejmuje decyzję o wygenerowaniu alertu.
- `AlertDispatcher` przekazuje alert do `TelegramChannel`.
- `TelegramChannel` wysyła wiadomość do Telegram API.
- Runtime kontynuuje pracę nawet w przypadku błędu wysyłki.
- Alert może zawierać pole „AI Rating" będące wynikiem analizy AI (np. BUY, HOLD, SELL), jednak nie stanowi ono rekomendacji inwestycyjnej ani polecenia wykonania transakcji. Ostateczna decyzja zawsze należy do użytkownika.

**Świadomie NIE wchodzi w zakres ETAPU 7.5:**

- zapisywanie `telegram_message_id`,
- zapisywanie identyfikatora wiadomości Telegram w `MarketEvent`,
- zapisywanie identyfikatora wiadomości w `metadata`,
- zapisywanie informacji o wiadomości w `HistoryRepository`,
- zapisywanie informacji o wiadomości w `SQLite`.

Jest to świadoma decyzja architektoniczna, a nie brak implementacji.

**Powód:**

Na obecnym etapie nie została jeszcze zaprojektowana docelowa architektura przechowywania historii wysłanych powiadomień. W późniejszych etapach może zostać wprowadzony dedykowany model (np. `AlertRecord`, `NotificationRecord`, `AlertHistory`) lub inne rozwiązanie wynikające z dalszego rozwoju projektu.

Do tego czasu ETAP 7.5 odpowiada wyłącznie za poprawne wygenerowanie i wysłanie alertu przez Telegram.

---

## 14. Testy

**Backend**: 46 plików testowych w `tests/`
**Frontend**: 10 plików testowych w `dashboard/src/` (w podkatalogach `api/__tests__/`, `components/__tests__/`, `hooks/__tests__/`, `views/__tests__/`, `__tests__/`)

### Lista testów backendu

| Plik | Opis |
|------|------|
| `test_ai_pipeline_integration.py` | Integracja pipeline AI |
| `test_alert_builder.py` | Alert builder |
| `test_alert_dispatcher.py` | Alert dispatcher |
| `test_analyst_engine.py` | Analyst engine |
| `test_composer_engine.py` | ComposerEngine — scalanie zdarzeń (ETAP 7.3) |
| `test_composite_event.py` | Model CompositeEvent (ETAP 7.3) |
| `test_corporate_detector.py` | Corporate Event Detector |
| `test_dashboard_api.py` | Dashboard API |
| `test_dashboard_repository.py` | Dashboard repository |
| `test_dashboard_service.py` | Dashboard service |
| `test_decision_engine.py` | Decision engine (rozbudowany w ETAPIE 7.4) |
| `test_derivatives_detector.py` | Derivatives Event Detector |
| `test_detector_orchestrator.py` | DetectorOrchestrator |
| `test_detector_registry.py` | DetectorRegistry |
| `test_detectors_base.py` | BaseDetector, DetectionContext, DetectionResult |
| `test_etf_detector.py` | ETF Event Detector |
| `test_fundamental_detector.py` | Fundamental Event Detector |
| `test_history_repository.py` | History repository |
| `test_hunter_engine.py` | Hunter engine |
| `test_macro_detector.py` | Macro Event Detector |
| `test_market_event_models.py` | Market event models |
| `test_market_scanner.py` | Market scanner |
| `test_master_detector_integration.py` | Integracja detektorów z MasterEngine |
| `test_master_engine.py` | Master engine |
| `test_master_engine_e2e.py` | Master engine E2E |
| `test_opportunity_deduplicator.py` | Opportunity deduplicator |
| `test_pipeline_decision.py` | PipelineDecision i decide_pipeline() (ETAP 7.4) |
| `test_price_detector.py` | Price detector |
| `test_quality_engine.py` | QualityEngine — ocena jakości (ETAP 7.2) |
| `test_ranking_engine.py` | Ranking engine |
| `test_read_api.py` | Read API |
| `test_regulatory_detector.py` | Regulatory Event Detector |
| `test_risk_engine.py` | Risk engine |
| `test_runtime.py` | Runtime |
| `test_scheduler.py` | Scheduler |
| `test_sentiment_detector.py` | Sentiment & News Event Detector |
| `test_sqlite_history_repository.py` | SQLite history repository |
| `test_static_instrument_source.py` | Static instrument source |
| `test_system_detector.py` | System Event Detector |
| `test_technical_detector.py` | Technical Event Detector |
| `test_technical_integrator.py` | TechnicalIntegrator — integracja MarketEvent → TechnicalEngine (ETAP 7) |
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
│   ├── technical_integrator.py  # MarketEvent → TechnicalEngine (Manual Analysis, ETAP 7)
│   ├── models.py
│   └── channels/
│       └── telegram_channel.py
│
├── config/                      # Konfiguracje
│   ├── analyst.py
│   ├── composer.py             # Konfiguracja ComposerEngine (ETAP 7.3)
│   ├── corporate_events.py     # Progi Corporate Event Detector
│   ├── etf_events.py           # Progi ETF Event Detector
│   ├── fundamental_events.py   # Progi Fundamental Event Detector
│   ├── hunter.py
│   ├── indicators.py
│   ├── macro_events.py         # Progi Macro Event Detector
│   ├── price_detector.py
│   ├── quality.py              # Konfiguracja QualityEngine (ETAP 7.2)
│   ├── ranking.py
│   ├── risk.py
│   ├── sentiment_events.py     # Progi Sentiment & News Event Detector
│   ├── technical_events.py     # Progi Technical Event Detector
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
│   │   ├── composite_event.py   # Model CompositeEvent (ETAP 7.3)
│   │   └── pipeline_decision.py # Model PipelineDecision (ETAP 7.4)
│   ├── tavily/                  # Integracja Tavily
│   └── yahoo/                   # Integracja Yahoo Finance
│
├── docs/                        # Dokumentacja
│   ├── API_README.md
│   ├── ETAP_5_ARCHITEKTURA_FRONTENDU.md
│   ├── ETAP_6_ARCHITEKTURA.md
│   ├── ETAP_7_PLAN.md
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
│   ├── composer/               # ComposerEngine — scalanie zdarzeń (ETAP 7.3)
│   ├── detectors/              # Framework detektorów (BaseDetector, DetectorOrchestrator)
│   ├── hunter/                 # Hunter Engine
│   ├── master/                 # Master Engine (główny orkiestrator)
│   ├── news/                   # News Engine
│   ├── price_detector/         # Price Detector
│   ├── quality/                # QualityEngine — ocena jakości zdarzeń (ETAP 7.2)
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
├── tests/                       # Testy (46 plików)
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
- **Status**: ✅ Zakończony i zamrożony (27.07.2026, commit `6670061`)

---

## 17. Zamrożone etapy

Wszystkie etapy od ETAP 1 do ETAP 6 (FAZA 1 i FAZA 2) są zamrożone. Zgodnie z zasadami projektu, architektura rdzenia nie może być modyfikowana bez świadomej decyzji projektowej.

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
| ETAP 7 | 🔄 W trakcie | Domknięcie cyklu życia zdarzenia (Quality, Composite, DecisionEngine, Alerty, Dashboard) |
| ├ 7.1 Specyfikacja | ✅ Ukończony | `docs/ETAP_7_PLAN.md` |
| ├ 7.2 Quality Assessment | ✅ Zaimplementowany | `QualityEngine`, `config/quality.py` |
| ├ 7.3 Composite Events | ✅ Zaimplementowany | `ComposerEngine`, `CompositeEvent`, `config/composer.py` |
| ├ 7.4 DecisionEngine | ✅ Zaimplementowany | `decide_pipeline()`, `PipelineDecision` |
| ├ 7.5 Alerty | ✅ Zaimplementowany | Rozbudowa AlertBuilder i AlertDispatcher + integracja TelegramChannel |
| ├ 7.5a Testy Runtime | ✅ Zaimplementowany | Pełne pokrycie testowe integracji Runtime z alertami |
| ├ 7.5b Porządkowanie repo | ✅ Zakończony | Czyszczenie staging area, .gitignore, przygotowanie commita |
| ├ 7.6 Dashboard | ❌ Nierozpoczęty | Rozbudowa frontendu |
| └ 7.7 Testy i zamrożenie | ❌ Nierozpoczęty | Testy integracyjne + commit |

---

## 19. Aktualny stan projektu

- Backend: kompletny, zamrożony (ETAP 1–6)
- Frontend: kompletny, zamrożony
- API: kompletne, zamrożone
- FAZA 1 ETAPU 6: zakończony i zamrożony (23.07.2026)
- FAZA 2 ETAPU 6: zakończony i zamrożony (27.07.2026)
- Detektory: 11 detektorów — wszystkie zaimplementowane, przetestowane i zamrożone
- ETAP 7.1–7.4: zaimplementowany, nie zamrożony
- ETAP 7.5 + 7.5a + 7.5b: zaimplementowany
- ETAP 7.6–7.7: nierozpoczęty
- Prace zatrzymane na ETAPIE 7.4 (wznowione dla ETAPU 7.5)
- Testy: 46 plików testowych backendu, 10 frontendu
- Dokumentacja: zaktualizowana do stanu ETAPU 7.4
- Ostatnia aktualizacja: 27.07.2026
- Branch: `master`

---

## 20. Następny etap

**ETAP 7.6** — rozbudowa dashboardu o widoki zdarzeniowe.

Szczegóły w `docs/ETAP_7_PLAN.md` §7.6.

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
| ETAP 7 Plan | `docs/ETAP_7_PLAN.md` | Plan ETAPU 7 |
| Check point | `ALCHEMIK_CHECK.md` | Status projektu |
| Projekt | `ALCHEMIK_PROJEKT.md` | Główna dokumentacja (ten plik) |

---

## KONIEC DOKUMENTU