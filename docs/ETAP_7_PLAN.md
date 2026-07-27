# ALCHEMIK — ETAP 7: PLAN IMPLEMENTACJI

## DOKUMENT PLANISTYCZNY — SPECYFIKACJA WYKONAWCZA

Data: 24.07.2026
Wersja: 1.0
Status: Dokument planistyczny — nie implementacyjny

---

## SPIS TREŚCI

1. [Cel ETAPU 7](#1-cel-etapu-7)
2. [Zakres ETAPU 7](#2-zakres-etapu-7)
3. [Elementy wchodzące w skład ETAPU 7](#3-elementy-wchodzące-w-skład-etapu-7)
4. [Elementy pozostające poza zakresem ETAPU 7](#4-elementy-pozostające-poza-zakresem-etapu-7)
5. [Podział ETAPU 7 na podetapy](#5-podział-etapu-7-na-podetapy)
    - [7.1 Specyfikacja](#71-specyfikacja)
    - [7.2 Quality Assessment](#72-quality-assessment)
    - [7.3 Composite Events](#73-composite-events)
    - [7.4 DecisionEngine](#74-decisionengine)
    - [7.5 Alerty](#75-alerty)
    - [7.6 Dashboard](#76-dashboard)
    - [7.7 Testy i zamrożenie](#77-testy-i-zamrożenie)
6. [Kryteria zakończenia każdego podetapu](#6-kryteria-zakończenia-każdego-podetapu)
7. [Kryteria zakończenia całego ETAPU 7](#7-kryteria-zakończenia-całego-etapu-7)
8. [Wykaz dokumentów będących źródłem specyfikacji](#8-wykaz-dokumentów-będących-źródłem-specyfikacji)

---

## 1. CEL ETAPU 7

Celem ETAPU 7 jest domknięcie pełnego cyklu życia zdarzenia rynkowego (`MarketEvent`) — od momentu wykrycia przez detektory, przez scalanie zdarzeń pokrewnych w Composite Events, ocenę jakości (Quality Assessment), decyzję o uruchomieniu AI (DecisionEngine), decyzję o wysłaniu alertu, aż po rozbudowę dashboardu o widok zdarzeniowy. ETAP 7 realizuje etapy cyklu życia zdarzenia, które w dokumentacji Kontraktu Zdarzeń Rynkowych zostały opisane jako etapy 3–12, a które nie zostały jeszcze w pełni zaimplementowane.

ETAP 7 przekształca system z pasywnego rejestratora zdarzeń w aktywny system alarmowy, który:
- scala pokrewne zdarzenia w zdarzenia złożone (Composite Events),
- ocenia jakość każdego zdarzenia (Critical / High / Medium / Low / Ignore),
- podejmuje decyzję o uruchomieniu kosztownych zasobów (News, Tavily, AI),
- wysyła alerty Telegram do inwestora,
- prezentuje zdarzenia w czasie zbliżonym do rzeczywistego na dashboardzie.

---

## 2. ZAKRES ETAPU 7

ETAP 7 obejmuje implementację następujących komponentów:

1. **Quality Assessment** — warstwa oceny jakości zdarzeń, przypisująca `quality_level` (Critical / High / Medium / Low / Ignore) na podstawie `priority_raw`, `priority_final`, grupy instrumentu, liczby zdarzeń składowych i powtarzalności.

2. **Composite Events (scalanie zdarzeń)** — warstwa łączenia pokrewnych zdarzeń w zdarzenia złożone. Zdarzenia dotyczące tego samego instrumentu, wykryte w zbliżonym czasie, są scalane w jeden `MarketEvent` z `is_composite=True` i listą `composite_events`.

3. **DecisionEngine** — pełna implementacja silnika decyzyjnego, który na podstawie `quality_level` i dostępnych danych kontekstowych decyduje o uruchomieniu kolejnych etapów pipeline'u (News, Tavily, AI). Obecny `engines/ai/decision_engine.py` istnieje jako szkielet — ETAP 7 nadaje mu pełną funkcjonalność.

4. **Alerty** — implementacja logiki decyzyjnej `AlertBuilder` (już istnieje szkielet) i integracja `AlertDispatcher → TelegramChannel` w oparciu o `MarketEvent`. System wysyła alerty Telegram dla zdarzeń spełniających kryteria (final_rating ≥ 70, confidence ≥ 70%).

5. **Dashboard zdarzeniowy** — rozbudowa frontendowego dashboardu o widoki prezentujące zdarzenia rynkowe w czasie zbliżonym do rzeczywistego, z możliwością filtrowania po priorytecie, rodzinie zdarzeń, tickerze i rynku.

6. **Testy i zamrożenie** — pełny zestaw testów jednostkowych i integracyjnych dla wszystkich nowych komponentów, testy end-to-end pełnego cyklu życia zdarzenia, aktualizacja dokumentacji, zamrożenie ETAPU 7.

---

## 3. ELEMENTY WCHODZĄCE W SKŁAD ETAPU 7

### 3.1 Quality Assessment (ocena jakości)

| Element | Opis |
|---------|------|
| `engines/quality/` | Nowy katalog: silnik oceny jakości zdarzeń (lub komponent w warstwie aplikacyjnej) |
| `engines/quality/engine.py` | QualityEngine — przyjmuje `MarketEvent`, zwraca `MarketEvent` z ustawionym `quality_level` |
| `engines/quality/__init__.py` | Inicjalizacja modułu |
| Algorytm oceny jakości | Wyznaczanie `quality_level` na podstawie: `priority_raw`, `priority_final`, grupy instrumentu (`instrument_type`), liczby zdarzeń składowych (dla Composite), powtarzalności zdarzenia |
| Konfiguracja `config/quality.py` | Progi i reguły oceny jakości (mapowanie priorytetów na poziomy jakości dla różnych grup instrumentów) |
| Testy `tests/test_quality_engine.py` | Testy jednostkowe QualityEngine |

### 3.2 Composite Events (scalanie zdarzeń)

| Element | Opis |
|---------|------|
| `engines/composer/` | Nowy katalog: silnik scalania zdarzeń |
| `engines/composer/engine.py` | ComposerEngine — przyjmuje listę `MarketEvent`, zwraca listę z dodanymi Composite Events |
| `engines/composer/__init__.py` | Inicjalizacja modułu |
| Algorytm scalania | Identyfikacja zdarzeń pokrewnych (ten sam instrument, bliski timestamp), tworzenie Composite Events, obliczanie `priority_final` jako `max(priorities of component events)` |
| Konfiguracja `config/composer.py` | Okno czasowe scalania, reguły łączenia rodzin zdarzeń |
| Testy `tests/test_composer_engine.py` | Testy jednostkowe ComposerEngine |

### 3.3 DecisionEngine (pełna implementacja)

| Element | Opis |
|---------|------|
| `engines/ai/decision_engine.py` | Rozbudowa istniejącego szkieletu do pełnej funkcjonalności |
| Logika decyzyjna | Na podstawie `quality_level`: CRITICAL/HIGH → News + Tavily + AI; MEDIUM → tylko News (warunkowo); LOW → tylko archiwizacja; IGNORE → przerwanie |
| Integracja z pipeline | DecisionEngine.process_event(MarketEvent) → decyzja o kolejnych krokach |
| Testy `tests/test_decision_engine.py` | Rozbudowa istniejących testów |

### 3.4 Alerty

| Element | Opis |
|---------|------|
| `application/alert_builder.py` | Rozbudowa istniejącego szkieletu — decyzja o alercie na podstawie `MarketEvent` i `FinalAnalysisResult` |
| `application/alert_dispatcher.py` | Rozbudowa — wysyłka alertów przez kanały |
| `application/channels/telegram_channel.py` | Istniejący — integracja z pipeline'm alertów |
| Kryteria alertu | `final_rating ≥ 70`, `confidence_level ≥ 70%`, rekomendacja `STRONG_BUY` lub `BUY`, brak duplikatu |
| Format wiadomości Telegram | Symbol, zdarzenie, priorytet, rekomendacja, score, confidence, podsumowanie AI |
| Testy | Rozbudowa `tests/test_alert_builder.py`, `tests/test_alert_dispatcher.py` |

### 3.5 Dashboard zdarzeniowy

| Element | Opis |
|---------|------|
| `dashboard/src/views/MarketEventsView.tsx` | Rozbudowa istniejącego widoku — filtrowanie po priorytecie, rodzinie zdarzeń, tickerze, rynku |
| `dashboard/src/hooks/useMarketEvents.ts` | Rozbudowa hooka — nowe parametry filtrowania |
| Nowe komponenty UI (jeśli wymagane) | Filtry zdarzeń, wskaźniki priorytetów, podgląd szczegółów zdarzenia |
| API | Istniejące endpointy `/api/v1/market-events` z filtrami — wykorzystanie istniejącej infrastruktury |

### 3.6 Testy i zamrożenie

| Element | Opis |
|---------|------|
| Testy jednostkowe | Dla każdego nowego komponentu: QualityEngine, ComposerEngine, DecisionEngine (rozbudowa), AlertBuilder (rozbudowa) |
| Testy integracyjne | Pełny pipeline: detekcja → scalanie → ocena jakości → decyzja → alert |
| Testy end-to-end | `test_master_engine_e2e.py` — rozbudowa o nowe etapy |
| Aktualizacja dokumentacji | `ALCHEMIK_PROJEKT.md`, `ALCHEMIK_CHECK.md`, `struktura_alchemik.txt` |
| Zamrożenie | Commit Git, oznakowanie ETAPU 7 jako zamrożonego |

---

## 4. ELEMENTY POZOSTAJĄCE POZA ZAKRESEM ETAPU 7

Następujące elementy **nie wchodzą** w zakres ETAPU 7:

1. **Modyfikacja detektorów** — wszystkie detektory (11 rodzin) są zamrożone w ETAPIE 6. ETAP 7 nie zmienia logiki detekcji.
2. **Modyfikacja istniejących silników** — TechnicalEngine, NewsEngine, AIEngine, RankingEngine, RiskEngine, HunterEngine, AnalystEngine, MasterEngine pozostają zamrożone w zakresie swojego Public API. ETAP 7 dodaje nowe komponenty, nie modyfikuje istniejących.
3. **Nowe źródła danych** — nie dodajemy integracji z ESPI, EBI, SEC, social media API.
4. **Modyfikacja kontraktu `MarketEvent`** — model 27 pól pozostaje niezmieniony. ETAP 7 wykorzystuje istniejące pola (`quality_level`, `is_composite`, `composite_events`, `priority_final`, `ai_context`, `news_context`, `tavily_context`).
5. **Modyfikacja Runtime / Scheduler** — cykl życia runtime'u pozostaje bez zmian.
6. **Nowe endpointy API** — nie dodajemy nowych endpointów REST. Istniejące endpointy `/api/v1/market-events` i `/api/v1/dashboard` są wystarczające.
7. **Zmiana architektury frontendu** — nie przebudowujemy struktury dashboardu. Rozszerzamy istniejące widoki.
8. **Nowe kanały powiadomień** — tylko Telegram (istniejący). Email, SMS, push notifications pozostają poza zakresem.
9. **Implementacja pełnej analizy fundamentalnej** — dane fundamentalne są ograniczone przez dostępność w Yahoo Finance.
10. **Dodawanie kryptowalut, Forex, indeksów** — poza zakresem, zgodnie z decyzją z ETAPU 6.

---

## 5. PODZIAŁ ETAPU 7 NA PODETAPY

```
ETAP 7 — STAN NA 27.07.2026 (ukończony do 7.5b)
├── 7.1 Specyfikacja                                        ✅ UKOŃCZONY
├── 7.2 Quality Assessment                                  ✅ ZAIMPLEMENTOWANY
├── 7.3 Composite Events                                     ✅ ZAIMPLEMENTOWANY
├── 7.4 DecisionEngine                                       ✅ ZAIMPLEMENTOWANY
├── 7.5 Alerty                                              ✅ ZAIMPLEMENTOWANY
├── 7.5a Testy Runtime                                       ✅ ZAIMPLEMENTOWANY
├── 7.5b Porządkowanie repo                                  ✅ ZAKOŃCZONY
├── 7.6 Dashboard                                           ❌ NIEROZPOCZĘTY
└── 7.7 Testy i zamrożenie                                  ❌ NIEROZPOCZĘTY
```

**Uwaga:** Podetapy 7.1–7.5b są zaimplementowane w kodzie, ale NIE są jeszcze zamrożone (nie wykonano commita Git dla ETAPU 7). Podetapy 7.6–7.7 pozostają nierozpoczęte.

**Nowe komponenty dodane w ETAPIE 7 (7.1–7.4):**

| Podetap | Pliki | Opis |
|---------|-------|------|
| 7.2 | `engines/quality/__init__.py`, `engines/quality/engine.py`, `config/quality.py`, `tests/test_quality_engine.py` | QualityEngine — ocena jakości zdarzeń |
| 7.3 | `engines/composer/__init__.py`, `engines/composer/engine.py`, `config/composer.py`, `data/models/composite_event.py`, `tests/test_composer_engine.py`, `tests/test_composite_event.py` | ComposerEngine + CompositeEvent — scalanie zdarzeń |
| 7.4 | `data/models/pipeline_decision.py`, `tests/test_pipeline_decision.py` + rozbudowa `engines/ai/decision_engine.py` (`decide_pipeline()`), `tests/test_decision_engine.py` | PipelineDecision + DecisionEngine — decyzje o pipeline |
| — | `application/technical_integrator.py`, `tests/test_technical_integrator.py` | TechnicalIntegrator — warstwa integracyjna MarketEvent → TechnicalEngine (Manual Analysis). Dodany poza planem, zgodny architektonicznie. |

### 7.1 Specyfikacja

**Cel**: Opracowanie dokumentu planistycznego ETAPU 7 — specyfikacji wykonawczej określającej zakres, podział na podetapy i kryteria zakończenia.

**Status**: ✅ UKOŃCZONY (24.07.2026)

**Zakres**:
- Analiza istniejącej dokumentacji projektowej
- Określenie zakresu ETAPU 7 na podstawie dokumentów źródłowych
- Zdefiniowanie podetapów i ich kolejności
- Określenie kryteriów zakończenia dla każdego podetapu i całego ETAPU 7
- Identyfikacja elementów pozostających poza zakresem

**Rezultat**: Dokument `docs/ETAP_7_PLAN.md` (niniejszy dokument).

**Zależności**: Brak — jest to pierwszy krok ETAPU 7.

**Kryteria zakończenia**:
- [x] Dokument `docs/ETAP_7_PLAN.md` istnieje
- [x] Dokument jest zgodny z obowiązującą dokumentacją projektu
- [x] Dokument nie projektuje nowych funkcji niewynikających z dokumentacji
- [x] Dokument został zaakceptowany przez właściciela projektu
- [x] Nie zmodyfikowano żadnego kodu projektu

---

### 7.2 Quality Assessment

**Cel**: Implementacja warstwy oceny jakości zdarzeń, która przypisuje każdemu `MarketEvent` końcowy poziom jakości (`quality_level`), determinujący dalsze przetwarzanie zdarzenia.

**Miejsce w cyklu życia zdarzenia**: ETAP 5 wg Kontraktu Zdarzeń Rynkowych — po deduplikacji, przed News Engine.

**Zakres implementacji**:

1. **Nowy komponent `engines/quality/`**:
    - `engine.py` — `QualityEngine` z metodą `assess(event: MarketEvent) -> MarketEvent`
    - `__init__.py` — eksport Public API

2. **Algorytm oceny jakości**:
    - Wejście: `MarketEvent` z ustawionym `priority_raw`, `priority_final` (dla Composite: max składowych), `instrument_type`, `is_composite`
    - Wyjście: `MarketEvent` z ustawionym `quality_level` ∈ {CRITICAL, HIGH, MEDIUM, LOW, IGNORE}
    - Reguły wyznaczania `quality_level`:
        - CRITICAL: Composite Event + priority_raw = CRITICAL, lub 3+ zdarzenia składowe
        - HIGH: priority_raw = CRITICAL (pojedyncze), lub Composite z HIGH + minimum 2 zdarzenia składowe
        - MEDIUM: priority_raw = HIGH, lub Composite z MEDIUM+
        - LOW: priority_raw = MEDIUM
        - IGNORE: priority_raw = LOW, lub duplikat (ustawiane przez deduplikator)

3. **Konfiguracja `config/quality.py`**:
    - Mapowanie `priority_raw` → `quality_level` dla różnych `instrument_type` (GPW, USA, ETF)
    - Progi liczby zdarzeń składowych dla Composite Events
    - Współczynniki korekty `confidence_level`

4. **Integracja z pipeline**:
    - `QualityEngine` jest wywoływany po `OpportunityDeduplicator`, przed `NewsPipeline`
    - Zdarzenia z `quality_level ∈ {IGNORE, LOW}` kończą przetwarzanie (tylko archiwizacja)
    - Zdarzenia z `quality_level ∈ {CRITICAL, HIGH, MEDIUM}` przechodzą dalej

5. **Niezmienniki kontraktu** (z `docs/Kontrakt_Zdarzen_Rynkowych.md`):
    - N11: `quality_level == IGNORE` → natychmiastowe przerwanie. `quality_level == LOW` → tylko archiwizacja
    - N5: `confidence_level` może być skorygowane przez etap oceny jakości
    - `event_id`, `ticker`, `detection_source`, `event_owner`, `priority_raw` pozostają niezmienne

**Rezultat**: Działający `QualityEngine` z testami jednostkowymi.

**Kryteria zakończenia**:
- `engines/quality/engine.py` zaimplementowany
- `config/quality.py` zdefiniowany
- `QualityEngine` poprawnie ustawia `quality_level` dla wszystkich kombinacji wejściowych
- Testy jednostkowe `tests/test_quality_engine.py` przechodzą
- Nie zmieniono Public API istniejących silników
- Nie zmieniono modelu `MarketEvent`

---

### 7.3 Composite Events

**Cel**: Implementacja warstwy scalania zdarzeń (ComposerEngine), która identyfikuje pokrewne zdarzenia dotyczące tego samego instrumentu i łączy je w zdarzenia złożone (Composite Events).

**Miejsce w cyklu życia zdarzenia**: ETAP 3 wg Kontraktu Zdarzeń Rynkowych — po detekcji, przed deduplikacją.

**Zakres implementacji**:

**Element przygotowawczy**: Model danych `CompositeEvent` (`data/models/composite_event.py`) jest kontenerem danych dla zdarzeń złożonych, wykorzystywanym przez `ComposerEngine`. Zapewnia walidację pól, serializację (to_dict/from_dict) oraz factory method `create()`. Model został zaimplementowany jako pierwszy krok ETAPU 7.3 i stanowi podstawę danych dla algorytmu scalania. Testy modelu znajdują się w `tests/test_composite_event.py`.

1. **Nowy komponent `engines/composer/`**:
    - `engine.py` — `ComposerEngine` z metodą `compose(events: list[MarketEvent]) -> list[MarketEvent]`
    - `__init__.py` — eksport Public API

2. **Algorytm scalania**:
    - Grupowanie zdarzeń według `ticker` (ten sam instrument)
    - W ramach grupy: identyfikacja zdarzeń w oknie czasowym (konfigurowalne, domyślnie 60 sekund)
    - Tworzenie Composite Event dla grup 2+ zdarzeń:
        - Nowy `event_id` (UUID v4)
        - `is_composite = True`
        - `composite_events = [event_ids zdarzeń składowych]`
        - `priority_final = max(priorities of component events)` (zgodnie z N10)
        - `event_family` ustawiane na podstawie zdarzeń składowych
        - `event_type` oznaczane jako typ złożony (np. `COMPOSITE_MULTI_EVENT`)
    - Zdarzenia niescalone przechodzą bez zmian (z `is_composite=False`, `composite_events=[]`)

3. **Konfiguracja `config/composer.py`**:
    - `time_window_seconds: int` — okno czasowe scalania (domyślnie 60)
    - `max_composite_events: int` — maksymalna liczba zdarzeń składowych (domyślnie 10)

4. **Reguły kompatybilności rodzin zdarzeń (7.3.1)**:

Macierz kompatybilności operuje wyłącznie na istniejących wartościach `EventFamily` zdefiniowanych w `data/models/event_enums.py`:

```
PRICE, VOLUME, TECHNICAL, FUNDAMENTAL, CORPORATE, REGULATORY,
MACRO, ETF, DERIVATIVES, SENTIMENT, SYSTEM
```

Nie utworzono nowych rodzin. Kategorie logiczne MOMENTUM, VOLATILITY, GAP i BREAKOUT są podtypami zdarzeń w ramach istniejących rodzin — ComposerEngine ocenia ich zgodność na podstawie faktycznego `event_family` nadanego przez detektor. LIQUIDITY, RISK i NEWS nie istnieją jako `EventFamily` i nie zostały dodane.

#### 4.1 Macierz kompatybilności

| Rodzina      | Może być łączona z                        |
|-------------|------------------------------------------|
| PRICE       | PRICE, VOLUME, TECHNICAL                 |
| VOLUME      | VOLUME, PRICE, TECHNICAL                 |
| TECHNICAL   | TECHNICAL, PRICE, VOLUME                 |
| FUNDAMENTAL | FUNDAMENTAL, CORPORATE, REGULATORY       |
| CORPORATE   | CORPORATE, FUNDAMENTAL, REGULATORY       |
| REGULATORY  | REGULATORY, CORPORATE, FUNDAMENTAL       |
| MACRO       | MACRO                                    |
| ETF         | ETF                                      |
| DERIVATIVES | DERIVATIVES                              |
| SENTIMENT   | SENTIMENT                                |
| SYSTEM      | SYSTEM                                   |

Macierz jest **symetryczna**: jeżeli rodzina A może być łączona z B, to B może być łączona z A.

#### 4.2 Zasady łączenia

- **Zdarzenia tej samej rodziny** są zawsze kompatybilne ze sobą (dotyczy każdej z 11 rodzin).
- **PRICE, VOLUME, TECHNICAL** tworzą grupę rynkowo-techniczną — mogą być wzajemnie łączone.
- **FUNDAMENTAL, CORPORATE, REGULATORY** tworzą grupę fundamentalno-informacyjną — mogą być wzajemnie łączone.
- **MACRO, ETF, DERIVATIVES, SENTIMENT, SYSTEM** mogą być łączone wyłącznie w ramach własnej rodziny.
- Nie łączy się automatycznie rodzin rynkowo-technicznych z fundamentalnymi ani informacyjnymi.
- Nie łączy się PRICE/VOLUME/TECHNICAL z CORPORATE ani REGULATORY.
- Nie łączy się MACRO z ruchem konkretnego tickera (PRICE/VOLUME/TECHNICAL).
- Nie łączy się SENTIMENT z PRICE/VOLUME/TECHNICAL.
- Nie łączy się SYSTEM z jakąkolwiek inną rodziną.

#### 4.3 Grupy wieloelementowe

Grupa składająca się z więcej niż dwóch zdarzeń może zostać scalona tylko wtedy, gdy **każda** rodzina występująca w grupie jest kompatybilna z **każdą** pozostałą rodziną w tej grupie (pełna zgodność parami).

Przykład dozwolony:
```
PRICE + VOLUME + TECHNICAL
```
Każda para jest kompatybilna.

Przykład niedozwolony:
```
PRICE + VOLUME + CORPORATE
```
PRICE i CORPORATE nie są kompatybilne — grupa nie może zostać scalona w jeden Composite Event.

#### 4.4 Maksymalne kompatybilne podgrupy

Jeżeli klaster tickera zawiera zarówno rodziny kompatybilne, jak i niekompatybilne, ComposerEngine:
1. Tworzy maksymalne kompatybilne podgrupy (greedy, deterministycznie).
2. Tworzy Composite Event dla każdej podgrupy zawierającej co najmniej 2 zdarzenia.
3. Pozostawia bez zmian zdarzenia, których nie można przypisać do żadnej grupy o rozmiarze ≥ 2.
4. Nie duplikuje zdarzenia wejściowego w więcej niż jednym Composite Event.

#### 4.5 Deterministyczność

Przed grupowaniem ComposerEngine stosuje deterministyczny porządek:
1. Czas zdarzenia (`timestamp_utc`).
2. Identyfikator zdarzenia (`event_id`).

Przy konflikcie, gdy jedno zdarzenie może zostać przypisane do więcej niż jednej kompatybilnej podgrupy:
1. Preferowana jest podgrupa z większą liczbą zdarzeń.
2. Przy tej samej liczbie — podgrupa zawierająca wcześniejsze zdarzenie.
3. Przy dalszym remisie — porządek po `event_id`.

Wynik nie zależy od kolejności zdarzeń przekazanych na wejściu.

5. **Niezmienniki kontraktu**:
    - N10: Composite Event dziedziczy najwyższy priorytet: `priority_final = max(składowe)`
    - `event_id` zdarzeń składowych pozostaje niezmieniony (są referencjami w `composite_events`)
    - Composite Event nie może mieć niższego priorytetu niż jego składowe
    - `detection_source` Composite Event wskazuje na ComposerEngine

5. **Integracja z pipeline**:
    - `ComposerEngine` jest wywoływany po detektorach (DetectorOrchestrator), przed deduplikacją
    - Zdarzenia składowe przechodzą do pipeline'u niezależnie ORAZ jako Composite Event
    - Deduplikacja uwzględnia Composite Events

**Rezultat**: Działający `ComposerEngine` z testami jednostkowymi.

**Kryteria zakończenia**:
- `engines/composer/engine.py` zaimplementowany
- `config/composer.py` zdefiniowany
- `ComposerEngine` poprawnie tworzy Composite Events dla pokrewnych zdarzeń
- `priority_final` Composite Event = max(składowe) — zgodnie z N10
- Testy jednostkowe `tests/test_composer_engine.py` przechodzą
- Nie zmieniono Public API istniejących silników
- Nie zmieniono modelu `MarketEvent`

---

### 7.4 DecisionEngine

**Cel**: Pełna implementacja silnika decyzyjnego, który na podstawie `quality_level` i kontekstu decyduje o uruchomieniu kolejnych etapów pipeline'u: News, Tavily, AI.

**Miejsce w cyklu życia zdarzenia**: ETAP 8–9 wg Kontraktu Zdarzeń Rynkowych — po ocenie jakości i News, przed RiskEngine.

**Zakres implementacji**:

1. **Rozbudowa `engines/ai/decision_engine.py`**:
    - Istniejący szkielet `DecisionEngine.process_event(MarketEvent) -> AISignal` — zachowanie kompatybilności wstecznej
    - Nowa metoda `decide_pipeline(event: MarketEvent) -> PipelineDecision` — decyzja o kolejnych krokach

2. **Logika decyzyjna**:
    - Wejście: `MarketEvent` z `quality_level`, `news_context`, `tavily_context`
    - Wyjście: `PipelineDecision` z flagami:
        - `run_news: bool` — czy uruchomić NewsPipeline
        - `run_tavily: bool` — czy uruchomić wyszukiwanie Tavily
        - `run_ai: bool` — czy uruchomić analizę AI
    - Reguły (zgodne z Kontraktem):
        - `quality_level == CRITICAL` → News + Tavily + AI (pełna analiza)
        - `quality_level == HIGH` → News + AI (Tavily opcjonalnie, gdy News nie dostarczył wystarczającego kontekstu)
        - `quality_level == MEDIUM` → tylko News (warunkowo, dla zdarzeń fundamentalnych/korporacyjnych)
        - `quality_level == LOW` → tylko archiwizacja (bez analizy)
        - `quality_level == IGNORE` → przerwanie (nawet bez archiwizacji — duplikat)

3. **Integracja z AI**:
    - `run_ai == True` → `AIProvider.analyze(event)` → `ai_context` w `MarketEvent`
    - AI interpretuje zebrane dane, nie podejmuje decyzji inwestycyjnych (zgodnie z Filozofią)
    - AI odpowiada na pytania: Co się dzieje? Dlaczego? Czy podobna sytuacja występowała? Scenariusze?

4. **PipelineDecision** (nowy model):
    - `data/models/pipeline_decision.py` — prosty model decyzji pipeline'u
    - Pola: `run_news: bool`, `run_tavily: bool`, `run_ai: bool`, `reason: str`

5. **Testy**:
    - Rozbudowa `tests/test_decision_engine.py` o testy decyzji pipeline'u
    - Testy dla wszystkich kombinacji `quality_level`

**Rezultat**: W pełni funkcjonalny `DecisionEngine` sterujący przepływem pipeline'u.

**Kryteria zakończenia**:
- `DecisionEngine.decide_pipeline()` zaimplementowany
- `PipelineDecision` model zdefiniowany
- Logika decyzyjna zgodna z Kontraktem Zdarzeń Rynkowych (etapy 8–9)
- Testy `tests/test_decision_engine.py` przechodzą (istniejące + nowe)
- Kompatybilność wsteczna z `process_event()` zachowana
- AI uruchamiana tylko dla CRITICAL/HIGH — zgodnie z Filozofią
- Nie zmieniono Public API `engines/ai/__init__.py`

---

### 7.5 Alerty

**Cel**: Implementacja pełnego łańcucha alertów: decyzja o alercie (AlertBuilder) → wysyłka (AlertDispatcher → TelegramChannel) dla zdarzeń spełniających kryteria.

**Miejsce w cyklu życia zdarzenia**: ETAP 11–12 wg Kontraktu Zdarzeń Rynkowych — po RiskEngine, przed archiwizacją.

#### Decyzja architektoniczna — ETAP 7.5 — Integracja Telegram

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

Na obecnym etapie nie została jeszcze zaprojektowana docelowa architektura przechowywania historii wysłanych powiadomień.

W późniejszych etapach może zostać wprowadzony dedykowany model, np.:

- `AlertRecord`,
- `NotificationRecord`,
- `AlertHistory`,

lub inne rozwiązanie wynikające z dalszego rozwoju projektu.

Do tego czasu ETAP 7.5 odpowiada wyłącznie za poprawne wygenerowanie i wysłanie alertu przez Telegram.

**Zakres implementacji**:

1. **Rozbudowa `application/alert_builder.py`**:
    - Istniejący szkielet — rozbudowa o logikę decyzyjną opartą na `MarketEvent`
    - Metoda `should_alert(event: MarketEvent, analysis: FinalAnalysisResult) -> bool`
    - Kryteria alertu (zgodne z `ALCHEMIK_PROJEKT.md`):
        - `final_rating ≥ 70`
        - `confidence_level ≥ 70%`
        - Rekomendacja ∈ {STRONG_BUY, BUY}
        - Nie duplikat (sprawdzane przez deduplikator)
    - Metoda `build_alert(event: MarketEvent) -> AlertMessage`

2. **Rozbudowa `application/alert_dispatcher.py`**:
    - Integracja z `TelegramChannel.send(alert)`
    - Format wiadomości Telegram zgodny z diagramem w Kontrakcie:
        ```
        🚨 ALCHEMIK ALERT
        Symbol: XYZ.WA
        Zdarzenie: PRICE_SURGE (+12.3%) + VOLUME_SPIKE (4.2x)
        Priorytet: CRITICAL
        Rekomendacja: STRONG_BUY
        Score: 87.3 | Confidence: 91%
        Podsumowanie: [analiza AI]
        ```

3. **Integracja z pipeline**:
    - `AlertBuilder` wywoływany po `RiskEngine`, przed archiwizacją
    - `should_alert() == True` → `build_alert()` → `AlertDispatcher.send()` → `TelegramChannel`
    - `should_alert() == False` → tylko archiwizacja
    - Każda decyzja zapisywana w `metadata.alert_decision`

4. **Testy**:
    - Rozbudowa `tests/test_alert_builder.py`
    - Rozbudowa `tests/test_alert_dispatcher.py`
    - Testy integracyjne z `TelegramChannel`

**Rezultat**: Działający łańcuch alertów Telegram dla zdarzeń spełniających kryteria.

**Kryteria zakończenia**:
- `AlertBuilder.should_alert()` zwraca poprawne decyzje dla przypadków granicznych
- `AlertBuilder.build_alert()` tworzy poprawny format wiadomości
- `AlertDispatcher` poprawnie przekazuje alert do `TelegramChannel`
- Testy `tests/test_alert_builder.py` i `tests/test_alert_dispatcher.py` przechodzą
- Format wiadomości Telegram zgodny ze specyfikacją
- Nie wysyłamy rekomendacji BUY/SELL — zgodnie z Filozofią (system przedstawia obraz sytuacji, nie rekomenduje)

---

### 7.6 Dashboard

**Cel**: Rozbudowa frontendowego dashboardu o widoki prezentujące zdarzenia rynkowe z możliwością filtrowania.

**Miejsce w architekturze**: Frontend React (`dashboard/`) — rozszerzenie istniejących widoków.

**Zakres implementacji**:

1. **Rozbudowa `MarketEventsView`**:
    - Dodanie filtrów: `priority_final`, `event_family`, `event_type`, `market`
    - Wizualne wskaźniki priorytetu (kolorowe oznaczenia CRITICAL/HIGH/MEDIUM/LOW)
    - Sortowanie po czasie, priorytecie, tickerze
    - Paginacja (istniejący mechanizm API)

2. **Rozbudowa `DashboardView`**:
    - Sekcja "Ostatnie zdarzenia krytyczne" (top 5 CRITICAL/HIGH)
    - Podsumowanie zdarzeń w ostatnim cyklu
    - Wykresy zdarzeń wg priorytetu (wykorzystanie danych z `/api/v1/dashboard`)

3. **Rozbudowa hooków**:
    - `useMarketEvents` — nowe parametry filtrowania
    - Nowy hook `useEventDetails` (jeśli potrzebny)

4. **Komponenty UI** (jeśli wymagane):
    - `PriorityBadge` — wizualny wskaźnik priorytetu
    - `EventFilterBar` — pasek filtrów zdarzeń

5. **API**:
    - Wykorzystanie istniejących endpointów `/api/v1/market-events` (już wspiera filtry)
    - Wykorzystanie `/api/v1/dashboard` (już zawiera `event_breakdown`)

**Rezultat**: Rozbudowany dashboard z widokiem zdarzeń rynkowych.

**Kryteria zakończenia**:
- `MarketEventsView` obsługuje filtrowanie po priorytecie, rodzinie, typie, rynku
- Wizualne wskaźniki priorytetów działają
- `DashboardView` wyświetla podsumowanie zdarzeń krytycznych
- Istniejące testy frontendu przechodzą (po aktualizacji)
- Nowe testy dla rozbudowanych komponentów przechodzą
- Nie zmieniono backend API
- Dashboard NIE wysyła rekomendacji inwestycyjnych

---

### 7.7 Testy i zamrożenie

**Cel**: Kompleksowe testy wszystkich nowych komponentów, testy integracyjne pełnego cyklu życia zdarzenia, aktualizacja dokumentacji, zamrożenie ETAPU 7.

**Zakres implementacji**:

1. **Testy jednostkowe**:
    - `tests/test_quality_engine.py` — QualityEngine (wszystkie kombinacje quality_level)
    - `tests/test_composer_engine.py` — ComposerEngine (scalanie, Composite Events)
    - `tests/test_decision_engine.py` — rozbudowa istniejących testów o PipelineDecision
    - `tests/test_alert_builder.py` — rozbudowa istniejących testów
    - `tests/test_alert_dispatcher.py` — rozbudowa istniejących testów

2. **Testy integracyjne**:
    - `tests/test_pipeline_e2e.py` — nowy plik: pełny cykl od detekcji do alertu
    - Test ścieżki: detektory → scalanie → ocena jakości → decyzja → alert → archiwizacja
    - Test ścieżki IGNORE: detekcja → duplikat → quality_level=IGNORE → przerwanie
    - Test ścieżki LOW: detekcja → quality_level=LOW → tylko archiwizacja

3. **Uruchomienie pełnego zestawu testów**:
    - Wszystkie istniejące testy projektu (42+ plików backendu, 10 plików frontendu)
    - Weryfikacja, że nowe komponenty nie łamią istniejących testów

4. **Aktualizacja dokumentacji**:
    - `ALCHEMIK_PROJEKT.md` — dodanie ETAPU 7 do roadmapy i ukończonych etapów
    - `ALCHEMIK_CHECK.md` — aktualizacja statusu projektu
    - `struktura_alchemik.txt` — odzwierciedlenie nowych katalogów i plików

5. **Zamrożenie**:
    - Commit Git ze spójnym stanem projektu
    - Oznakowanie ETAPU 7 jako zamrożonego
    - Nowe komponenty stają się częścią zamrożonej architektury rdzenia

**Rezultat**: Przetestowany, udokumentowany i zamrożony ETAP 7.

**Kryteria zakończenia**:
- Wszystkie nowe testy jednostkowe przechodzą
- Wszystkie istniejące testy projektu przechodzą (bez regresji)
- Testy integracyjne pełnego pipeline'u przechodzą
- Dokumentacja zaktualizowana
- Repozytorium w spójnym stanie (git commit)
- ETAP 7 oznaczony jako zamrożony

---

## 6. KRYTERIA ZAKOŃCZENIA KAŻDEGO PODETAPU

| Podetap | Kryteria zakończenia |
|---------|----------------------|
| **7.1 Specyfikacja** | Dokument `docs/ETAP_7_PLAN.md` istnieje, zgodny z dokumentacją, zaakceptowany. Brak modyfikacji kodu. |
| **7.2 Quality Assessment** | `QualityEngine` zaimplementowany, `config/quality.py` zdefiniowany, testy przechodzą, `quality_level` poprawnie wyznaczany, nie naruszono kontraktu `MarketEvent`. |
| **7.3 Composite Events** | `ComposerEngine` zaimplementowany, `config/composer.py` zdefiniowany, testy przechodzą, Composite Events poprawnie tworzone, `priority_final` = max(składowe). |
| **7.4 DecisionEngine** | `DecisionEngine.decide_pipeline()` zaimplementowany, `PipelineDecision` model, testy przechodzą, logika zgodna z Kontraktem, kompatybilność wsteczna zachowana. |
| **7.5 Alerty** | `AlertBuilder` i `AlertDispatcher` rozbudowane, testy przechodzą, łańcuch alertów Telegram działa, format wiadomości zgodny ze specyfikacją. |
| **7.6 Dashboard** | `MarketEventsView` rozbudowany o filtry, wizualne wskaźniki priorytetów, testy frontendu przechodzą. |
| **7.7 Testy i zamrożenie** | Wszystkie testy przechodzą (nowe + istniejące), dokumentacja zaktualizowana, commit Git, ETAP 7 zamrożony. |

---

## 7. KRYTERIA ZAKOŃCZENIA CAŁEGO ETAPU 7

ETAP 7 jest ukończony, gdy:

1. **Wszystkie podetapy 7.2–7.7 są zrealizowane** i spełniają swoje kryteria zakończenia.

2. **Quality Assessment** działa poprawnie:
    - `quality_level` jest wyznaczany dla każdego zdarzenia
    - Zdarzenia IGNORE/LOW są poprawnie odrzucane
    - Zdarzenia CRITICAL/HIGH/MEDIUM przechodzą do dalszej analizy

3. **Composite Events** są poprawnie tworzone:
    - Zdarzenia pokrewne są scalane
    - `priority_final` Composite Event = max(składowe)
    - Niezmiennik N10 zachowany

4. **DecisionEngine** steruje pipeline'm:
    - Decyzje o News/Tavily/AI podejmowane na podstawie `quality_level`
    - AI uruchamiana tylko dla CRITICAL/HIGH
    - Zgodność z Filozofią: AI interpretuje, nie decyduje

5. **Alerty** są wysyłane:
    - Kryteria alertu spełnione → Telegram
    - Format wiadomości zgodny ze specyfikacją
    - Brak rekomendacji BUY/SELL w treści alertu

6. **Dashboard** prezentuje zdarzenia:
    - Filtrowanie działa
    - Wskaźniki priorytetów widoczne
    - Dane pobierane z istniejącego API

7. **Testy**:
    - Wszystkie nowe testy jednostkowe przechodzą
    - Testy integracyjne pełnego pipeline'u przechodzą
    - Wszystkie istniejące testy projektu przechodzą (brak regresji)

8. **Brak naruszeń zamrożonej architektury**:
    - Nie zmieniono Public API istniejących silników
    - Nie zmieniono kontraktu `MarketEvent` (model 27 pól)
    - Nie zmieniono warstwy aplikacyjnej (Runtime, Scheduler)
    - Nie zmieniono istniejących endpointów API
    - Detektory (ETAP 6) pozostają niezmienione

9. **Dokumentacja**:
    - `ALCHEMIK_PROJEKT.md` zaktualizowany o ETAP 7
    - `ALCHEMIK_CHECK.md` zaktualizowany
    - `struktura_alchemik.txt` odzwierciedla nowe komponenty

10. **Zamrożenie**:
    - Commit Git
    - ETAP 7 oznaczony jako zamrożony

---

## 8. WYKAZ DOKUMENTÓW BĘDĄCYCH ŹRÓDŁEM SPECYFIKACJI

| Lp. | Dokument | Kluczowe informacje dla ETAPU 7 |
|-----|----------|--------------------------------|
| 1 | `docs/FILOZOFIA_ALCHEMIKA.md` | Filozofia: AI interpretuje, nie decyduje. System nie wydaje rekomendacji BUY/SELL. Przepływ logiczny 1–11. |
| 2 | `docs/ZASADY_PROJEKTU.md` | Zasada zamrożenia architektury. Etapy: projektowanie → akceptacja → zamrożenie → implementacja → testy. Punkty kontrolne Git. |
| 3 | `docs/INSTRUKCJA_DLA_CLINE.md` | Komunikacja przez Public API. Uniwersalność — bez twardych tickerów. |
| 4 | `docs/Kontrakt_Zdarzen_Rynkowych.md` | Cykl życia zdarzenia (13 etapów). Odpowiedzialność modułów. Niezmienniki N1–N13. Pola `quality_level`, `is_composite`, `composite_events`, `priority_final`. |
| 5 | `docs/Katalog_Zdarzen_Rynkowych.md` | ~157 typów zdarzeń. Priorytety (`priority_raw`). Struktura klasyfikacji. |
| 6 | `docs/Hierarchia_Zdarzen_Rynkowych.md` | 11 rodzin zdarzeń. Mapowanie `event_type → EventFamily`. Kategorie i podkategorie. |
| 7 | `docs/Przeplyw_Zdarzen_Rynkowych.md` | Przepływ wykrywania zdarzeń przez detektory. |
| 8 | `docs/Przeplyw_Danych.md` | Przepływ danych między silnikami. Role: AI Engine, Ranking Engine, Risk Engine. |
| 9 | `docs/API_README.md` | Istniejące endpointy API. `/api/v1/market-events` — filtrowanie. `/api/v1/dashboard` — agregacje. |
| 10 | `docs/ETAP_6_ARCHITEKTURA.md` | Elementy poza zakresem ETAPU 6: ocena jakości, Composite Events, DecisionEngine — delegowane do ETAPU 7. Kontrakt frameworka detektorów. |
| 11 | `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md` | Architektura frontendu. Istniejące widoki, komponenty, hooki. |
| 12 | `ALCHEMIK_PROJEKT.md` | Opis ETAPU 7: "rozbudowa alertów, dashboard zdarzeniowy, ocena jakości zdarzeń, scalanie zdarzeń (Composite Events)". Istniejące silniki, moduły. |
| 13 | `ALCHEMIK_CHECK.md` | Status projektu. Zamrożone moduły. Następny planowany etap: ETAP 7. |
| 14 | `README.md` | Ogólny opis projektu. |
| 15 | `struktura_alchemik.txt` | Aktualna struktura katalogów i plików. |
| 16 | `.clinerules` | Zasady pracy Cline: analiza przed implementacją, niezmienianie architektury, raport końcowy. |

---

## KONIEC DOKUMENTU

| Atrybut | Wartość |
|---------|---------|
| Data | 24.07.2026 |
| Wersja | 1.0 |
| Status | Dokument planistyczny — specyfikacja wykonawcza ETAPU 7 |
| Bazuje na | 16 dokumentach źródłowych (wymienionych w sekcji 8) |
| Następny krok | Akceptacja dokumentu przez właściciela projektu, przejście do podetapu 7.2 (Quality Assessment) |