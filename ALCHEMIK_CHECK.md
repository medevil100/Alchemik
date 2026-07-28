# ALCHEMIK — CHECK POINT (PEŁNY AUDYT)

## Data audytu

28.07.2026

## Zakres audytu

Pełny audyt weryfikacyjny całego projektu ALCHEMIK — stan na dzień 28.07.2026.
Obejmuje strukturę repozytorium, przepływ Runtime, wszystkie silniki, detektory, modele danych, moduł Tavily Plan B, bazę danych, API, frontend, alerty, konfigurację, testy oraz zgodność dokumentacji z kodem.

## Stan Git w chwili audytu

```
A  alchemik.code-workspace
A  data/tavily/config.py
A  data/tavily/errors.py
A  data/tavily/models.py
M  engines/master/engine.py
M  tests/test_master_engine.py
M  tests/test_master_engine_e2e.py
AM tests/test_tavily_config.py
A  tests/test_tavily_errors.py
A  tests/test_tavily_models.py
?? data/tavily/client.py
?? tests/test_tavily_client.py
```

- Branch: `master`
- Ostatni commit: `8aa45ec` (HEAD)
- W staging area znajdują się pliki Tavily (config, errors, models) oraz zmodyfikowany MasterEngine
- `git diff --stat`: tylko 1 zmiana w `tests/test_tavily_config.py`
- Pliki `data/tavily/client.py` i `tests/test_tavily_client.py` są untracked

## Przeczytana dokumentacja

1. `.clinerules`
2. `README.md`
3. `struktura_alchemik.txt`
4. `ALCHEMIK_PROJEKT.md`
5. `ALCHEMIK_CHECK.md` (poprzednia wersja)
6. `docs/Przeplyw_Danych.md`
7. `docs/INSTRUKCJA_DLA_CLINE.md`
8. `docs/FILOZOFIA_ALCHEMIKA.md`
9. `docs/ZASADY_PROJEKTU.md`
10. `docs/Kontrakt_Zdarzen_Rynkowych.md` (1057 linii)
11. `docs/API_README.md`
12. `docs/Hierarchia_Zdarzen_Rynkowych.md`
13. `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md`
14. `docs/ETAP_6_ARCHITEKTURA.md`
15. `docs/ETAP_7_PLAN.md`
16. `docs/Przeplyw_Zdarzen_Rynkowych.md`
17. `struktura_runtime.txt`

## Brakująca dokumentacja

- `docs/Katalog_Zdarzen_Rynkowych.md` — dokument istnieje w repozytorium, nie został wczytany w trakcie audytu (priorytetyzacja); jego istnienie jest potwierdzone przez `struktura_alchemik.txt` i referencje w innych dokumentach

## Aktualna struktura projektu

Struktura repozytorium jest zasadniczo zgodna z `struktura_alchemik.txt`.

**Pliki obecne w repozytorium, ale niewymienione w `struktura_alchemik.txt`:**
- `alchemik.code-workspace` (w staging)
- `data/tavily/config.py`, `data/tavily/errors.py`, `data/tavily/models.py`, `data/tavily/client.py`
- `tests/test_tavily_config.py`, `tests/test_tavily_errors.py`, `tests/test_tavily_models.py`, `tests/test_tavily_client.py`
- `data/models/event_enums.py` (obecny w `struktura_alchemik.txt`, OK)
- `data/models/history_entry.py` (obecny, OK)

**Pliki wymienione w `struktura_alchemik.txt`, ale nieobecne w repozytorium w widoczny sposób:** Brak — wszystkie kluczowe pliki istnieją.

**Nowe pliki od czasu poprzedniego audytu:**
- `data/tavily/config.py` — konfiguracja modułu Tavily (149 linii)
- `data/tavily/errors.py` — hierarchia wyjątków Tavily (40 linii)
- `data/tavily/models.py` — modele danych Tavily (160 linii)
- `data/tavily/client.py` — klient HTTP Tavily (179 linii, untracked)
- `tests/test_tavily_config.py` — testy konfiguracji
- `tests/test_tavily_errors.py` — testy wyjątków
- `tests/test_tavily_models.py` — testy modeli
- `tests/test_tavily_client.py` — testy klienta (untracked)

## Aktualny główny przepływ Runtime

**Rzeczywista sekwencja wywołań w `application/runtime.py::RuntimeService.run_cycle()`:**

```
1. MarketScanner.scan() → lista kandydatów
2. HunterEngine.scan(candidates) → HunterResult
3. Dla każdego candidate w hunter_result.opportunities:
   a. Deduplicator.should_process() → skip jeśli duplikat
   b. resolve_instrument_metadata(ticker) → market, instrument_type
   c. MasterEngine.run_analysis(
        symbol=ticker,
        market=market,
        instrument_type=instrument_type,
        events_out=detected_events,
        ohlcv_data=candidate_ohlcv,
      ) → FinalAnalysisResult
   d. Jeśli alert_builder + alert_dispatcher + detected_events:
      Dla każdego MarketEvent z quality_level ∉ {IGNORE, LOW}:
        AlertBuilder.should_alert(result, event=ev)
        AlertBuilder.build_alert(result, event=ev)
        AlertDispatcher.dispatch(alert, [telegram_channel])
   e. Deduplicator.mark_processed()
4. HistoryRepository.save_cycle() → zapis cyklu
5. HistoryRepository.save_market_events() → batch persistence MarketEvent
```

**Rzeczywista sekwencja w `engines/master/engine.py::MasterEngine.run_analysis()`:**

```
1. TechnicalEngine.analyze(ohlcv_data) → AnalysisResult
2. Detektory:
   a. PriceDetector.detect(ticker, market, instrument_type, ohlcv_data) → List[MarketEvent]
   b. VolumeDetector.detect(ticker, market, instrument_type, ohlcv_data) → List[MarketEvent]
   c. DetectorOrchestrator.run_all(DetectionContext) przez 9 BaseDetectorów:
      TechnicalEventDetector, FundamentalEventDetector, CorporateEventDetector,
      RegulatoryEventDetector, MacroEventDetector, ETFEventDetector,
      DerivativesEventDetector, SentimentNewsEventDetector, SystemEventDetector
   d. _result_to_market_event() konwertuje DetectionResult → MarketEvent (katalog ~30 typów)
3. ComposerEngine.compose(market_events) → scalanie w Composite Events
4. QualityEngine.assess(ev) dla każdego eventu → quality_level
5. DecisionEngine.decide_pipeline(ev) dla każdego eventu → PipelineDecision
6. Jeśli jakikolwiek run_news: NewsPipeline.process([symbol]) → news_result
7. Jeśli jakikolwiek run_ai:
   Dla każdego eventu z run_ai=True:
     DecisionEngine.process_event(ev) → AISignal
     ev.ai_context = {signal_type, confidence, reasoning, generated_at}
8. RankingEngine.calculate_ranking([ai_result]) → FullRanking
9. RiskEngine.assess_risk(ai_result, ranking_result) → RiskResult
10. HunterEngine.scan([symbol, risk, ranking]) → HunterResult
11. AnalystEngine.generate_analysis(hunter_result) → AnalystResult
12. FinalAnalysisResult(symbol, final_rating, confidence_level, recommendation, ...)
```

**Kluczowe wnioski z analizy przepływu:**

- ComposerEngine jest **rzeczywiście wywoływany** w linii 375 MasterEngine: `self._composer_engine.compose(market_events)`
- QualityEngine jest **rzeczywiście wywoływany** w linii 381 MasterEngine: `self._quality_engine.assess(ev)`
- DecisionEngine.decide_pipeline() jest **rzeczywiście wywoływany** w linii 389
- PipelineDecision **rzeczywiście wpływa** na przepływ — flagi `run_news` i `run_ai` warunkują wykonanie News i AI
- **Tavily NIE jest wywoływany** — flaga `run_tavily` jest ustawiana (True dla CRITICAL) ale nigdy nie jest używana do wywołania TavilyClient
- Przepływ jest zgodny z dokumentacją dla zaimplementowanych elementów ETAPU 7

## Stan wszystkich silników

| Silnik | Status | Dowód integracji | Uwagi |
|--------|--------|-----------------|-------|
| **TechnicalEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 351 | |
| **PriceDetector** | ✅ Zintegrowany | `MasterEngine.run_detectors()` linia 303 | |
| **VolumeDetector** | ✅ Zintegrowany | `MasterEngine.run_detectors()` linia 312 | |
| **BaseDetector-orchestrated (9)** | ✅ Zintegrowane | `MasterEngine._run_base_detectors()` linia 224 | Technical, Fundamental, Corporate, Regulatory, Macro, ETF, Derivatives, Sentiment, System |
| **ComposerEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 375 | **ZAIMPLEMENTOWANY I ZINTEGROWANY** |
| **QualityEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 381 | **ZAIMPLEMENTOWANY I ZINTEGROWANY** |
| **DecisionEngine (decide_pipeline)** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 389 | **ZAIMPLEMENTOWANY I ZINTEGROWANY** |
| **DecisionEngine (process_event)** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 420 | Warunkowo, gdy run_ai=True |
| **NewsPipeline** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 405 | Warunkowo, gdy run_news=True |
| **RankingEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 439 | |
| **RiskEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 442 | |
| **HunterEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 445 | |
| **AnalystEngine** | ✅ Zintegrowany | `MasterEngine.run_analysis()` linia 448 | |
| **AlertBuilder** | ✅ Zintegrowany | `RuntimeService.run_cycle()` linia 158 | Warunkowo, z MarketEvent |
| **AlertDispatcher** | ✅ Zintegrowany | `RuntimeService.run_cycle()` linia 162 | |
| **TelegramChannel** | ✅ Zintegrowany | `RuntimeService.run_cycle()` linia 161 | Jako kanał alertów |
| **TechnicalIntegrator** | 🔄 ETAP 7 | NIE w pipeline automatycznym | Wyłącznie Manual Analysis, niepodłączony do Runtime |
| **TavilyClient** | 🔄 ETAP 7 | **BRAK INTEGRACJI** | Moduł samodzielny, niepodłączony |

## Stan detektorów

| Detektor | Plik | Status | Integracja |
|----------|------|--------|------------|
| **BaseDetector** (abstrakcyjny) | `engines/detectors/` | ✅ Zamrożony | Framework dla 9 detektorów |
| **DetectionContext** | `engines/detectors/` | ✅ Zamrożony | Niemutowalny, niepuste OHLCV |
| **DetectionResult** | `engines/detectors/` | ✅ Zamrożony | Tylko event_type + confidence_level |
| **DetectorRegistry** | `engines/detectors/` | ✅ Zamrożony | Rejestracja i wyszukiwanie |
| **DetectorOrchestrator** | `engines/detectors/` | ✅ Zamrożony | run_all(context) → tuple[DetectionResult] |
| **PriceDetector** | `engines/price_detector/` | ✅ Zamrożony | Zamrożone API, nie BaseDetector |
| **VolumeDetector** | `engines/volume_detector/` | ✅ Zamrożony | Zamrożone API, nie BaseDetector |
| **TechnicalEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **FundamentalEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **CorporateEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **RegulatoryEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **MacroEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **ETFEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **DerivativesEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **SentimentNewsEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |
| **SystemEventDetector** | `engines/detectors/` | ✅ Zamrożony | BaseDetector, zintegrowany |

**Katalog zdarzeń w MasterEngine** (`_CATALOGUE`): zawiera ~30 wpisów mapujących event_type → (EventFamily, event_category, event_subcategory, PriorityLevel). Obejmuje rodziny TECHNICAL (Zmienność, Wybicia, Formacje świecowe, Trend, Momentum, Wskaźniki techniczne). **Brakuje wpisów dla rodzin PRICE, VOLUME, FUNDAMENTAL, CORPORATE, REGULATORY, MACRO, ETF, DERIVATIVES, SENTIMENT, SYSTEM** — te zdarzenia przechodzą przez `_lookup_catalogue()` która zwraca domyślnie `(EventFamily.SYSTEM, "System", None, PriorityLevel.LOW)`. Liczba brakujących typów: ~127 (z ~157 w Katalogu). Detektory używają różnych event_type niż te zmapowane w katalogu.

## Stan modeli danych

| Model | Plik | Używany w Runtime | Używany w API | Używany w testach | Status |
|-------|------|:---:|:---:|:---:|--------|
| **MarketEvent** | `data/models/market_event.py` | ✅ | ✅ | ✅ | **Centralny model pipeline'u** |
| **CompositeEvent** | `data/models/composite_event.py` | ❌ (pośrednio) | ❌ | ✅ | **ZAIMPLEMENTOWANY, LECZ NIEZINTEGROWANY** — model istnieje, testowany, ale NIE jest importowany ani używany przez ComposerEngine (który operuje na MarketEvent) |
| **PipelineDecision** | `data/models/pipeline_decision.py` | ✅ | ❌ | ✅ | Używany przez DecisionEngine.decide_pipeline() |
| **FinalAnalysisResult** | `data/models/final_analysis_result.py` | ✅ | ❌ | ✅ | Produkt MasterEngine.run_analysis() |
| **AnalysisResult** | `data/models/analysis_result.py` | ✅ | ❌ | ✅ | Produkt TechnicalEngine |
| **AISignal** | `data/models/ai_signal.py` | ✅ | ❌ | ✅ | Produkt DecisionEngine |
| **NewsItem** | `data/models/news_item.py` | ✅ (pośrednio) | ❌ | ✅ | Wewnątrz NewsPipeline |
| **CompanyInfo** | `data/models/company_info.py` | ❌ | ❌ | ❌ | **NIEUŻYWANY** — brak importów poza modelem |
| **HistoryEntry** | `data/models/history_entry.py` | ✅ (pośrednio) | ❌ | ✅ | Używany w MarketEvent |
| **PriceData** | `data/models/price_data.py` | ✅ | ❌ | ✅ | Wewnątrz PriceDetector/MarketEvent |
| **VolumeData** | `data/models/volume_data.py` | ✅ | ❌ | ✅ | Wewnątrz VolumeDetector/MarketEvent |
| **MarketData** | `data/models/market_data.py` | ✅ | ❌ | ✅ | W DetectionContext/OHLCV |
| **RankingResult** | `data/models/ranking_result.py` | ✅ | ❌ | ✅ | Produkt RankingEngine |
| **FullRanking** | `data/models/full_ranking.py` | ✅ | ❌ | ✅ | Produkt RankingEngine |
| **RiskResult** | `data/models/risk_result.py` | ✅ | ❌ | ✅ | Produkt RiskEngine |
| **HunterResult** | `data/models/hunter_result.py` | ✅ | ❌ | ✅ | Produkt HunterEngine |
| **HunterScanResult** | (w hunter_result.py) | ✅ | ❌ | ✅ | Wewnątrz HunterResult |
| **EventEnums** | `data/models/event_enums.py` | ✅ | ❌ | ✅ | EventFamily, EventOwner, PriorityLevel, InstrumentType |
| **TavilyResultItem** | `data/tavily/models.py` | ❌ | ❌ | ✅ | **ZAIMPLEMENTOWANY, LECZ NIEZINTEGROWANY** |
| **TavilyContext** | `data/tavily/models.py` | ❌ | ❌ | ✅ | **ZAIMPLEMENTOWANY, LECZ NIEZINTEGROWANY** |
| **TavilyQueryRequest** | `data/tavily/models.py` | ❌ | ❌ | ✅ | **ZAIMPLEMENTOWANY, LECZ NIEZINTEGROWANY** |

## Stan ComposerEngine i CompositeEvent

**ComposerEngine** (`engines/composer/engine.py`):
- **ZAIMPLEMENTOWANY I ZINTEGROWANY** — wywoływany w `MasterEngine.run_analysis()` linia 375
- Metoda `compose(events: list[MarketEvent]) -> list[MarketEvent]`
- Operuje na obiektach MarketEvent, tworzy Composite Events (is_composite=True, composite_events=[...])
- Respektuje macierz kompatybilności rodzin zdarzeń (ETAP_7_PLAN.md §7.3.1)

**CompositeEvent** (`data/models/composite_event.py`):
- **ZAIMPLEMENTOWANY, LECZ NIEZINTEGROWANY** — model istnieje i ma testy, ale NIE jest używany przez ComposerEngine (który operuje bezpośrednio na MarketEvent)
- Model jest kontenerem danych z walidacją, serializacją i factory method `create()`
- Nie importowany przez żaden moduł produkcyjny poza własnymi testami
- Rola modelu CompositeEvent w architekturze: NIEUSTALONE — model istnieje jako osobny byt, ale ComposerEngine nie tworzy instancji CompositeEvent

## Stan QualityEngine

**QualityEngine** (`engines/quality/engine.py`):
- **ZAIMPLEMENTOWANY I ZINTEGROWANY** — wywoływany w `MasterEngine.run_analysis()` linia 381
- Metoda `assess(event: MarketEvent) -> MarketEvent`
- Przypisuje `quality_level` na podstawie priority_raw, instrument_type, is_composite
- Konfiguracja: `config/quality.py`

## Stan DecisionEngine i PipelineDecision

**DecisionEngine** (`engines/ai/decision_engine.py`):
- **ZAIMPLEMENTOWANY I ZINTEGROWANY**
- Metoda `decide_pipeline(event) → PipelineDecision` — wywoływana w MasterEngine linia 389
- Reguły decyzyjne: CRITICAL → News+Tavily+AI, HIGH → News+AI, MEDIUM → News, LOW → archiwizacja, IGNORE → stop
- Metoda `process_event(event) → AISignal` — wywoływana warunkowo dla AI (linia 420)
- Metoda `process_data(dict) → AISignal` — adapter kompatybilności wstecznej (linia 434)
- **UWAGA**: `run_tavily=True` jest ustawiane dla CRITICAL, ale NIGDY nie jest konsumowane — nie ma kodu, który wywołuje TavilyClient na podstawie tej flagi

**PipelineDecision** (`data/models/pipeline_decision.py`):
- **ZAIMPLEMENTOWANY I ZINTEGROWANY** — używany w MasterEngine do warunkowania News i AI

## Stan modułu News

**News Engine** (`engines/news/`):
- Pipeline, cleaner, filter, cache — zamrożone
- Wywoływany warunkowo w MasterEngine na podstawie `run_news` z PipelineDecision
- `tavily_news_provider.py` istnieje jako plik — NIEUSTALONE, czy jest używany
- News Engine i Tavily to dwa **niezależne** mechanizmy — News Engine korzysta z własnego pipeline'u, Tavily jest osobnym modułem

## Stan modułu Tavily Plan B

### Dokładna lista plików Tavily

| Plik | Linie | Status w Git | Odpowiedzialność |
|------|-------|-------------|-----------------|
| `data/tavily/__init__.py` | 1 | Committed | Placeholder |
| `data/tavily/config.py` | 149 | Staged (A) | Konfiguracja z env vars |
| `data/tavily/errors.py` | 40 | Staged (A) | Hierarchia wyjątków (7 klas) |
| `data/tavily/models.py` | 160 | Staged (A) | TavilyResultItem, TavilyContext, TavilyQueryRequest |
| `data/tavily/client.py` | 179 | Untracked (??) | TavilyClient — synchroniczny HTTP |
| `tests/test_tavily_config.py` | — | Staged (AM) | Testy konfiguracji |
| `tests/test_tavily_errors.py` | — | Staged (A) | Testy wyjątków |
| `tests/test_tavily_models.py` | — | Staged (A) | Testy modeli |
| `tests/test_tavily_client.py` | — | Untracked (??) | Testy klienta HTTP |

### Funkcjonalności Tavily ukończone ✅

1. **Konfiguracja** (`TavilyConfig`): immutable dataclass, factory `from_env()`, zmienne środowiskowe (TAVILY_API_KEY, TAVILY_ENABLED, TAVILY_TIMEOUT, TAVILY_MAX_RETRIES, TAVILY_RATE_LIMIT), walidacja
2. **Wyjątki** (7 klas): TavilyError (bazowy), TavilyConfigError, TavilyAPIError, TavilyTimeoutError, TavilyRateLimitError, TavilyConnectionError, TavilyValidationError
3. **Modele danych** (3 klasy): TavilyResultItem (frozen, walidacja title/url/score), TavilyContext (frozen, query + results_count + top_results + sentiment), TavilyQueryRequest (frozen, query + max_results + search_depth + domain filtering)
4. **Klient HTTP** (`TavilyClient`): synchroniczny, używa `requests`, POST do `/search`, buduje payload z api_key + query + max_results + search_depth + domain filtering, timeout przez `config.timeout_seconds`, obsługa błędów HTTP (429 → TavilyRateLimitError, 4xx/5xx → TavilyAPIError), obsługa timeout (requests.Timeout → TavilyTimeoutError), obsługa ConnectionError (→ TavilyConnectionError), obsługa błędnego JSON (JSONDecodeError → TavilyValidationError), obsługa non-dict JSON (→ TavilyValidationError), mapowanie wyjątków zgodne z dokumentacją docstring
5. **Walidacja modeli**: `__post_init__` dla wszystkich trzech modeli, zakresy score [0.0, 1.0], sentiment [-1.0, 1.0], niepuste stringi, max_results >= 1
6. **Testy**: 117 testów + 37 subtestów, wszystkie przechodzą (0.32s)

### Funkcjonalności Tavily nieukończone ❌

1. **Brak warstwy serwisowej** — nie ma klasy/service'u, który łączyłby TavilyClient z pipeline'm (pobieranie konfiguracji, budowanie zapytania na podstawie MarketEvent, przetwarzanie odpowiedzi na TavilyContext)
2. **Brak query buildera** — nie ma komponentu budującego zapytanie na podstawie ticker, giełdy, rodzaju ruchu i czasu zdarzenia
3. **Brak filtrowania maksymalnego okna 24h** — `max_age_hours` jest w konfiguracji, ale nie ma logiki filtrującej wyniki
4. **Brak retry** — `max_retries` jest w konfiguracji, ale TavilyClient nie implementuje retry
5. **Brak rate limiting** — `max_requests_per_minute` jest w konfiguracji, ale nie ma limitera
6. **Brak cache** — brak warstwy cache dla wyników
7. **Brak konwersji TavilyQueryRequest → odpowiedź API → TavilyContext** — klient zwraca surowy dict, nie TavilyContext
8. **Brak integracji z DecisionEngine** — `run_tavily=True` jest ustawiane, ale nie konsumowane
9. **Brak integracji z MasterEngine** — brak importu lub wywołania Tavily
10. **Brak integracji z Runtime** — brak ścieżki Tavily w cyklu

### Status integracji Tavily z pipeline

| Punkt integracji | Status | Dowód |
|-----------------|--------|-------|
| Import w MasterEngine | ❌ Brak | `engines/master/engine.py` nie importuje `data.tavily` |
| Wywołanie w MasterEngine.run_analysis() | ❌ Brak | Brak kodu wywołującego TavilyClient |
| Wywołanie w RuntimeService.run_cycle() | ❌ Brak | Brak referencji do Tavily |
| Flaga run_tavily w PipelineDecision | ✅ Ustawiana | `DecisionEngine.decide_pipeline()` dla CRITICAL |
| Konsumpcja flagi run_tavily | ❌ Brak | Żaden kod nie sprawdza `decision.run_tavily` |
| Wynik Tavily → AnalystEngine/AI | ❌ Brak | Brak przepływu danych |
| Wynik Tavily → MarketEvent.tavily_context | ❌ Brak | Pole nie jest wypełniane |
| Wynik Tavily → API | ❌ Brak | API nie zwraca tavily_context |
| Wynik Tavily → frontend | ❌ Brak | Dashboard nie wyświetla danych Tavily |

**Tavily jest obecnie modułem SAMODZIELNYM, a NIE częścią działającego pipeline.**

Kroki Tavily zakończone: Konfiguracja, Modele, Wyjątki, Klient HTTP (wszystkie — krok "Podstawowa infrastruktura").

**Pierwszy niewykonany krok Tavily**: Warstwa serwisowa łącząca TavilyClient z MarketEvent (query builder, filtrowanie 24h, konwersja dict → TavilyContext).

## Stan bazy danych i historii

- **Baza**: SQLite z WAL mode, `data/runtime/alchemik_runtime.db`
- **Tabele**: `cycles`, `market_events` (potwierdzone przez `sqlite_history_repository.py`)
- **Inicjalizacja**: `SQLiteHistoryRepository` tworzy schemat przy pierwszym użyciu
- **Zapis cyklu**: `HistoryRepository.save_cycle()` — wywoływane w RuntimeService.run_cycle() linia 220
- **Zapis MarketEvent**: `HistoryRepository.save_market_events()` batch — wywoływane w RuntimeService linia 241
- **Zapis CompositeEvent**: NIE — CompositeEvent istnieje jako model, ale nie ma dedykowanej tabeli ani zapisu
- **Zapis PipelineDecision**: NIE — decyzje nie są utrwalane
- **Zapis Tavily**: NIE — brak integracji
- **Lifecycle MarketEvent**: Utworzenie (detektor) → Composer → Quality → Decision → (News/AI warunkowo) → Alert → Persistence
- **Dane dostępne przez API**: cykle, MarketEvents (poprzez ReadService + DashboardReadService)
- **Modele powstające, ale nieutrwalane**: CompositeEvent, PipelineDecision, TavilyContext

## Stan alertów i Telegrama

- **AlertBuilder**: `should_alert(result, event)` + `build_alert(result, event)` — zintegrowany w Runtime
- **AlertDispatcher**: `dispatch(alert, channels)` — zintegrowany
- **TelegramChannel**: przekazywany jako kanał do dispatchera
- **Warunki alertu**: quality_level ∉ {IGNORE, LOW}, final_rating ≥ 70, confidence ≥ 70%
- **Zapis historii alertów**: tylko przez `save_market_events()` — brak dedykowanej tabeli alertów
- **telegram_message_id**: świadomie NIE zapisywany (decyzja architektoniczna ETAP 7.5)
- **Alert a CompositeEvent**: alert budowany na podstawie MarketEvent + FinalAnalysisResult — CompositeEvent jest typem MarketEvent (is_composite=True)
- **Alert a PipelineDecision**: decyzje nie są dołączane do alertu
- **Alert a Tavily**: brak kontekstu Tavily w alercie

## Stan API

Endpointy zdefiniowane w `application/api_entrypoint.py`:

| Metoda | Ścieżka | Handler | Używane repozytorium | Testy |
|--------|---------|---------|---------------------|:---:|
| GET | `/health` | `health()` | `RuntimeReadService` | ✅ |
| GET | `/api/v1/runtime/statistics` | `runtime_statistics()` | `RuntimeReadService` | ✅ |
| GET | `/api/v1/cycles` | `list_cycles()` | `RuntimeReadService` | ✅ |
| GET | `/api/v1/cycles/{cycle_id}` | `get_cycle()` | `RuntimeReadService` | ✅ |
| GET | `/api/v1/dashboard` | `get_dashboard()` | `DashboardReadService` | ✅ |
| GET | `/api/v1/market-events` | `list_market_events()` | `RuntimeReadService` | ✅ |
| GET | `/api/v1/market-events/{event_id}` | `get_market_event()` | `RuntimeReadService` | ✅ |
| GET | `/api/v1/tickers/{ticker}/market-events` | `get_ticker_market_events()` | `RuntimeReadService` | ✅ |

**Zgodność z dokumentacją API_README.md**: ✅ Pełna — wszystkie endpointy, parametry i struktury odpowiedzi są zgodne.

**Endpointy nieużywane przez frontend**: NIEUSTALONE — wymaga analizy frontendu. Prawdopodobnie `/api/v1/cycles`, `/api/v1/cycles/{cycle_id}`, `/api/v1/runtime/statistics` i `/api/v1/tickers/{ticker}/market-events` mogą nie być używane przez obecne 3 widoki (DashboardView, HealthView, MarketEventsView), które używają `/health`, `/api/v1/dashboard` i `/api/v1/market-events`.

## Stan dashboardu

- **Widoki zaimplementowane**: DashboardView, HealthView, MarketEventsView (3 widoki)
- **Widoki niezaimplementowane**: CyclesView, CycleDetail (wymienione w ETAP_5_ARCHITEKTURA_FRONTENDU.md)
- **Hooki**: useApiHealth, useDashboard, useMarketEvents
- **Komponenty**: Navigation, StatusBar, LoadingSpinner, ErrorBanner, EmptyState, DashboardCard
- **Polling**: zaimplementowany w hookach
- **Paginacja**: "Załaduj więcej" na mobile, standardowa na desktop (dla MarketEventsView)
- **Obsługa błędów**: loading, error, empty state — zaimplementowane
- **Responsywność**: CSS Modules + media queries
- **Dane Tavily w frontendzie**: ❌ Brak — API nie zwraca tavily_context
- **Widoki CyclesView i CycleDetail**: Zdefiniowane w dokumentacji ETAP_5_ARCHITEKTURA_FRONTENDU.md, ale **NIE są zaimplementowane** w kodzie — brak plików `CyclesView.tsx`, `CycleDetail.tsx` w `dashboard/src/views/`
- **RuntimeStatistics i ticker events**: Endpointy istnieją w API, ale nie ma dla nich widoków w frontendzie

## Stan testów

### Testy backendu

- **Liczba testów**: 1235 passed + 41 subtests passed
- **Czas wykonania**: 12.68s
- **Wynik**: ✅ Wszystkie testy przechodzą
- **Liczba plików testowych**: ~47 plików w `tests/`

### Testy Tavily

- **Liczba testów**: 117 passed + 37 subtests passed
- **Czas wykonania**: 0.32s
- **Wynik**: ✅ Wszystkie testy przechodzą
- **Pliki**: test_tavily_errors.py, test_tavily_config.py, test_tavily_models.py, test_tavily_client.py

### Testy i build frontendu

- **Nie wykonano** — testy frontendu (Vitest) i build Vite nie zostały uruchomione podczas audytu.
- Powód: Potencjalne problemy infrastrukturalne z zależnościami npm (opisane w poprzednim ALCHEMIK_CHECK.md jako "problemy infrastrukturalne niezwiązane z ETAP 7.5").

## Elementy niepodłączone do Runtime

| Element | Status | Wyjaśnienie |
|---------|--------|-------------|
| **TechnicalIntegrator** | 🔄 ETAP 7 | Wyłącznie Manual Analysis, NIE w pipeline automatycznym |
| **TavilyClient** | 🔄 ETAP 7 | Moduł samodzielny — klient HTTP gotowy, ale niepodłączony |
| **TavilyContext** | 🔄 ETAP 7 | Model gotowy, ale nie jest tworzony w pipeline |
| **TavilyResultItem** | 🔄 ETAP 7 | Model gotowy, nieużywany |
| **TavilyQueryRequest** | 🔄 ETAP 7 | Model gotowy, nieużywany |
| **CompositeEvent** (model) | 🔄 ETAP 7 | Model gotowy, ale ComposerEngine używa MarketEvent bezpośrednio |
| **CompanyInfo** | ❓ | Model zdefiniowany, nieużywany w Runtime ani API |

## Modele nieużywane w Runtime lub API

- **CompanyInfo** (`data/models/company_info.py`) — brak importów produkcyjnych
- **TavilyResultItem** — tylko testy
- **TavilyContext** — tylko testy
- **TavilyQueryRequest** — tylko testy (pośrednio przez TavilyClient w testach)
- **CompositeEvent** (`data/models/composite_event.py`) — tylko testy, nieużywany przez ComposerEngine

## Endpointy nieużywane przez frontend

Na podstawie analizy 3 zaimplementowanych widoków:
- `/api/v1/cycles` — prawdopodobnie nieużywany (brak widoku CyclesView)
- `/api/v1/cycles/{cycle_id}` — prawdopodobnie nieużywany (brak widoku CycleDetail)
- `/api/v1/runtime/statistics` — prawdopodobnie nieużywany (brak dedykowanego widoku)
- `/api/v1/tickers/{ticker}/market-events` — prawdopodobnie nieużywany (brak widoku tickerowego)

## Rozbieżności kod–dokumentacja

| # | Dokument | Sekcja | Stan deklarowany | Stan rzeczywisty | Dowód | Klasyfikacja |
|---|----------|--------|-----------------|-----------------|-------|-------------|
| 1 | `ALCHEMIK_CHECK.md` (poprzedni) | Status modułów | "ComposerEngine: 🔄 ETAP 7", "QualityEngine: 🔄 ETAP 7" | Oba silniki są **zintegrowane** w MasterEngine.run_analysis() | `engines/master/engine.py` linie 375, 381 | Dokumentacja nieaktualna |
| 2 | `ALCHEMIK_CHECK.md` (poprzedni) | Status modułów | "PipelineDecision: 🔄 ETAP 7" | PipelineDecision jest **zintegrowany** i warunkuje News/AI | `engines/master/engine.py` linie 385-397 | Dokumentacja nieaktualna |
| 3 | `ALCHEMIK_CHECK.md` (poprzedni) | Status ETAPU 7 | "ETAP 7.5: Alerty — Zaimplementowany" | Zgadza się — kod istnieje i działa | `application/runtime.py` linie 148-172 | Zgodne |
| 4 | `ALCHEMIK_PROJEKT.md` | §5.13 | "Composer Engine (...) Status: 🔄 ETAP 7.3 (zaimplementowany, nie zamrożony)" | Zaimplementowany i **zintegrowany** — więcej niż deklaruje dokumentacja | `engines/master/engine.py` linia 375 | Implementacja wykracza poza dokumentację |
| 5 | `ALCHEMIK_PROJEKT.md` | §5.12 | "Quality Engine (...) Status: 🔄 ETAP 7.2 (zaimplementowany, nie zamrożony)" | Zaimplementowany i **zintegrowany** — więcej niż deklaruje dokumentacja | `engines/master/engine.py` linia 381 | Implementacja wykracza poza dokumentację |
| 6 | `ALCHEMIK_PROJEKT.md` | §6 (tabela modeli) | CompositeEvent: "(ETAP 7.3)" — sugeruje użycie | Model istnieje, ale ComposerEngine używa MarketEvent bezpośrednio, nie CompositeEvent | `engines/composer/engine.py` — brak importu CompositeEvent | Niejednoznaczność |
| 7 | `docs/Kontrakt_Zdarzen_Rynkowych.md` | ETAP 7 (Tavily) | Tavily wypełnia `tavily_context` w MarketEvent | Tavily NIE jest wywoływany — `tavily_context` nigdy nie jest wypełniane | Brak wywołania TavilyClient w pipeline | Implementacja niepełna |
| 8 | `docs/Kontrakt_Zdarzen_Rynkowych.md` | ETAP 1-2 | "Detektor (...) ustawia event_family, event_category, event_subcategory, event_type, priority_raw" | Zgodne — katalog w MasterEngine dostarcza klasyfikację, detektory dostarczają event_type + confidence_level | `engines/master/engine.py` _CATALOGUE i _result_to_market_event() | Zgodne |
| 9 | `docs/Katalog_Zdarzen_Rynkowych.md` | ~157 typów zdarzeń | Wszystkie typy powinny być obsługiwane | Katalog w MasterEngine zawiera ~30 wpisów (głównie TECHNICAL). Detektory używają własnych event_type. Pozostałe ~127 typów nie ma mapowania w _CATALOGUE — fallback do System/LOW. | `engines/master/engine.py` _CATALOGUE (linie 52-100) | Implementacja niepełna |
| 10 | `docs/ETAP_7_PLAN.md` | §7.4 | "run_tavily: bool — czy uruchomić wyszukiwanie Tavily" | Flaga jest ustawiana (dla CRITICAL) ale NIE jest konsumowana | `engines/ai/decision_engine.py` linia 178 — ustawia `run_tavily=True`, ale MasterEngine nie sprawdza tej flagi | Implementacja niepełna |
| 11 | `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md` | §9.4, §9.5 | Widoki CyclesView i CycleDetail | NIE istnieją w kodzie — brak plików | `dashboard/src/views/` — tylko 3 widoki | Implementacja niepełna |
| 12 | `struktura_alchemik.txt` | — | Nie wymienia plików Tavily (config.py, errors.py, models.py, client.py) | Pliki istnieją fizycznie | `data/tavily/` | Dokumentacja nieaktualna |
| 13 | `struktura_alchemik.txt` | — | Nie wymienia `data/models/event_enums.py`, `data/models/history_entry.py`, `data/models/composite_event.py`, `data/models/pipeline_decision.py`, `data/models/price_data.py`, `data/models/volume_data.py` | Pliki istnieją fizycznie | `data/models/` | Dokumentacja nieaktualna |
| 14 | `struktura_runtime.txt` | — | Nie odzwierciedla aktualnej struktury po ETAPIE 6 i 7 | Brak katalogów `engines/detectors/`, `engines/composer/`, `engines/quality/`, nowych modeli, Tavily | Porównanie z `struktura_alchemik.txt` | Dokumentacja nieaktualna |

## Ukończone etapy i kroki

| Etap | Status |
|------|--------|
| ETAP 1 (Detektory ceny i wolumenu) | ✅ Zamrożony |
| ETAP 2 (Runtime → SQLite) | ✅ Zamrożony |
| ETAP 3 (Read Service + API) | ✅ Zamrożony |
| ETAP 4 (Dashboard API) | ✅ Zamrożony |
| ETAP 5 (Frontend React) | ✅ Zamrożony |
| FAZA 1 ETAPU 6 (MarketEvent jako centralny obiekt) | ✅ Zamrożony |
| FAZA 2 ETAPU 6 (11 detektorów + integracja MasterEngine) | ✅ Zamrożony |
| ETAP 7.1 (Specyfikacja) | ✅ Ukończony |
| ETAP 7.2 (Quality Assessment) | ✅ Zaimplementowany i zintegrowany |
| ETAP 7.3 (Composite Events — ComposerEngine) | ✅ Zaimplementowany i zintegrowany |
| ETAP 7.3 (CompositeEvent — model) | ✅ Zaimplementowany, NIEZINTEGROWANY |
| ETAP 7.4 (DecisionEngine + PipelineDecision) | ✅ Zaimplementowany i zintegrowany |
| ETAP 7.5 (Alerty) | ✅ Zaimplementowany |
| ETAP 7.5a (Testy Runtime) | ✅ Zaimplementowany |
| ETAP 7.5b (Porządkowanie repo) | ✅ Zakończony |
| ETAP 7.6 (Dashboard zdarzeniowy) | ❌ Nierozpoczęty |
| ETAP 7.7 (Testy i zamrożenie) | ❌ Nierozpoczęty |
| Tavily Plan B — infrastruktura podstawowa | ✅ Ukończona |
| Tavily Plan B — warstwa serwisowa | ❌ Nierozpoczęta |
| Tavily Plan B — integracja z pipeline | ❌ Nierozpoczęta |

## Pierwszy niewykonany krok dla każdego aktywnego obszaru

| Obszar | Pierwszy niewykonany krok |
|--------|--------------------------|
| **Dashboard** | ETAP 7.6 — implementacja CyclesView, CycleDetail, filtrów priorytetów w MarketEventsView |
| **Tavily** | Warstwa serwisowa: query builder (ticker + giełda + rodzaj ruchu + czas) → TavilyQueryRequest, konwersja odpowiedzi API → TavilyContext, filtrowanie 24h |
| **Integracja Tavily** | Podłączenie flagi `run_tavily` w MasterEngine: wywołanie TavilyClient.search() dla eventów CRITICAL, zapisanie TavilyContext do MarketEvent.tavily_context |
| **CompositeEvent (model)** | Decyzja architektoniczna: czy ComposerEngine powinien używać modelu CompositeEvent, czy pozostać przy MarketEvent |
| **Katalog zdarzeń** | Rozszerzenie _CATALOGUE w MasterEngine o pozostałe ~127 typów zdarzeń z Katalogu |

## Lista problemów blokujących

1. **Tavily nie jest zintegrowany z pipeline** — flaga `run_tavily` jest ustawiana, ale nie konsumowana. CRITICAL eventy nie otrzymują `tavily_context`. Blokuje to pełny cykl życia zdarzenia zgodnie z Kontraktem Zdarzeń Rynkowych (ETAP 7).

2. **Katalog zdarzeń w MasterEngine jest niekompletny** — tylko ~30 z ~157 typów zdarzeń ma poprawne mapowanie. Pozostałe ~127 typów otrzymuje domyślną klasyfikację (EventFamily.SYSTEM, PriorityLevel.LOW). Może to prowadzić do nieprawidłowej priorytetyzacji i brakujących kategoryzacji.

3. **CompositeEvent (model) jest nieużywany** — model istnieje i ma testy, ale ComposerEngine operuje bezpośrednio na MarketEvent. WYMAGA DECYZJI ARCHITEKTONICZNEJ: czy model CompositeEvent ma zostać zintegrowany z ComposerEngine, czy pozostać jako samodzielny kontener danych do przyszłych zastosowań.

## Lista problemów nieblokujących

1. **`struktura_alchemik.txt` jest nieaktualna** — nie uwzględnia plików dodanych w ETAPIE 6 (detektory, modele) i ETAPIE 7 (composer, quality, Tavily).

2. **`struktura_runtime.txt` jest nieaktualna** — stan sprzed ETAPU 6.

3. **Dokumentacja ALCHEMIK_PROJEKT.md** — opisuje ComposerEngine i QualityEngine jako "zaimplementowane, nie zamrożone", ale nie odzwierciedla ich faktycznej integracji w MasterEngine.

4. **CompanyInfo** — model zdefiniowany, ale nieużywany produkcyjnie.

5. **`docs/Przeplyw_Zdarzen_Rynkowych.md`** — opisuje architekturę w trybie przyszłym ("Detektory opisane poniżej reprezentują przyszłą strukturę logiczną"), co może wprowadzać w błąd przy czytaniu obok rzeczywistego kodu gdzie detektory już istnieją.

6. **Brak widoków CyclesView i CycleDetail w frontendzie** — endpointy API istnieją, ale frontend nie ma widoków do ich prezentacji (ETAP 7.6).

7. **Brak testów frontendu** — audyt nie zweryfikował testów Vitest ze względu na potencjalne problemy infrastrukturalne.

## Czy cały projekt jest obecnie kompletny?

**NIE.** Projekt ALCHEMIK NIE jest kompletny end-to-end.

Backend jest w zaawansowanym stanie — wszystkie silniki, detektory, pipeline alertów i API działają. Brakuje jednak:
- Integracji Tavily z pipeline'm (flaga run_tavily nie jest konsumowana)
- Rozszerzenia katalogu zdarzeń o pełne ~157 typów
- Rozbudowy frontendu o widoki cykli, szczegółów zdarzeń i filtrów priorytetów (ETAP 7.6)
- Testów integracyjnych pełnego pipeline'u (ETAP 7.7)
- Zamrożenia ETAPU 7 (commit Git)

## Czy Tavily jest obecnie kompletnym modułem end-to-end?

**NIE.** Moduł Tavily Plan B ma ukończoną infrastrukturę podstawową (konfiguracja, wyjątki, modele, klient HTTP), ale:
- Nie ma warstwy serwisowej łączącej TavilyClient z MarketEvent
- Nie ma integracji z DecisionEngine/MasterEngine/Runtime
- Nie jest wywoływany w żadnym momencie cyklu życia zdarzenia
- Wyniki Tavily nie trafiają do MarketEvent, API ani frontendu

Tavily jest **modułem samodzielnym, przygotowanym do integracji**, ale nie jest **modułem działającym end-to-end**.

## Rekomendowany następny krok zgodny z istniejącą roadmapą

Zgodnie z `docs/ETAP_7_PLAN.md`, następnym krokiem jest **ETAP 7.6 — Dashboard zdarzeniowy** (rozbudowa frontendu o widoki zdarzeniowe, filtry priorytetów, CyclesView, CycleDetail).

Równolegle lub bezpośrednio po nim rekomendowane jest dokończenie integracji Tavily (konsumpcja flagi `run_tavily`, warstwa serwisowa), aby domknąć cykl życia zdarzenia zgodnie z Kontraktem Zdarzeń Rynkowych.

## Oświadczenie

Audyt nie zmienił kodu produkcyjnego, testów, konfiguracji ani architektury. Jedynym zmodyfikowanym plikiem jest `ALCHEMIK_CHECK.md`. Nie wykonano `git add`, `git commit` ani `git push`.

---

**KONIEC DOKUMENTU**