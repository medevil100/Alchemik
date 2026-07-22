# ALCHEMIK — ETAP 6: ARCHITEKTURA DETEKTORÓW ZDARZEŃ RYNKOWYCH

## DOKUMENT PROJEKTOWY — PLAN ETAPU 6

Data: 22.07.2026
Wersja: 1.0
Status: Dokument planistyczny — nie implementacyjny

---

## SPIS TREŚCI

1. [Cel ETAPU 6](#1-cel-etapu-6)
2. [Uzasadnienie](#2-uzasadnienie)
3. [Miejsce ETAPU 6 w projekcie](#3-miejsce-etapu-6-w-projekcie)
4. [Zależności](#4-zależności)
5. [Zakres](#5-zakres)
6. [Elementy poza zakresem](#6-elementy-poza-zakresem)
7. [Proponowany podział na kroki](#7-proponowany-podział-na-kroki)
8. [Ryzyka](#8-ryzyka)
9. [Kryteria ukończenia](#9-kryteria-ukończenia)
10. [Kryteria zamrożenia](#10-kryteria-zamrożenia)

---

## 1. CEL ETAPU 6

Celem ETAPU 6 jest zaprojektowanie i wdrożenie dedykowanych detektorów zdarzeń rynkowych jako logicznych jednostek odpowiedzialnych za wykrywanie konkretnych typów zdarzeń, zgodnie z dokumentami projektowymi:

- `docs/Katalog_Zdarzen_Rynkowych.md` (~157 typów zdarzeń)
- `docs/Hierarchia_Zdarzen_Rynkowych.md` (11 rodzin zdarzeń)
- `docs/Przeplyw_Zdarzen_Rynkowych.md` (przepływ wykrywania zdarzeń)
- `docs/Kontrakt_Zdarzen_Rynkowych.md` (kontrakt wymiany danych)

ETAP 6 przekształca obecną, rozproszoną logikę detekcyjną w scentralizowany system detektorów z jasno zdefiniowanymi interfejsami.

---

## 2. UZASADNIENIE

Obecnie logika detekcyjna jest rozproszona pomiędzy istniejącymi silnikami (TechnicalEngine, AnalystEngine, NewsEngine). Detektory są opisane w dokumentacji projektowej jako jednostki logiczne, ale nie mają wydzielonych komponentów w kodzie.

Realizacja ETAPU 6 jest konieczna, ponieważ:

1. **Zgodność z dokumentacją** — Katalog Zdarzeń Rynkowych definiuje ~157 typów zdarzeń, które muszą być wykrywalne przez system.
2. **Skalowalność** — Dodawanie nowych zdarzeń wymaga architektury wtyczkowej (registry pattern), a nie modyfikacji istniejących silników.
3. **Uporządkowanie** — Obecnie detektory cenowe (Price Detector) i wolumenowe (Volume Detector) są już wydzielone, ale pozostałe rodziny zdarzeń nie mają dedykowanych komponentów.
4. **Przygotowanie pod ETAP 7+** — Działające detektory są warunkiem wstępnym dla pełnej automatyzacji alertów i dashboardu zdarzeniowego.

---

## 3. MIEJSCE ETAPU 6 W PROJEKCIE

### Mapa zależności między etapami

```
ETAP 1-4 (backend, silniki, API, dashboard API)
    │
    ▼
ETAP 5 (frontend React)
    │
    ▼
ETAP 6 (detektory zdarzeń) ◄── BIŻESZNY ETAP
    │
    ▼
ETAP 7+ (rozbudowa alertów, dashboard zdarzeniowy)
```

### Relacja do istniejących silników

Detektory są **rozszerzeniami** istniejących silników, zgodnie z zasadą zamrożenia architektury rdzenia:

| Istniejący silnik | Nowe detektory |
|-------------------|----------------|
| TechnicalEngine | Price Event Detector, Volume Event Detector, Technical Event Detector |
| AnalystEngine | Fundamental Event Detector, ETF Event Detector, Derivatives Event Detector |
| NewsEngine | Corporate Event Detector, Regulatory Event Detector, Macro Event Detector, Sentiment & News Event Detector |
| Multi-Engine | System Event Detector |

---

## 4. ZALEŻNOŚCI

### Wymagane do rozpoczęcia ETAPU 6

| Zależność | Status | Uwagi |
|-----------|--------|-------|
| ETAP 5 zamrożony | ✅ Zakończony | Frontend React działa i jest zamrożony |
| Dokumenty projektowe zdarzeń | ✅ Gotowe | Katalog, Hierarchia, Przepływ, Kontrakt |
| Istniejące silniki | ✅ Działające | Technical, News, AI, Ranking, Risk, Hunter, Analyst |
| Price Detector | ✅ Działający | Wydzielony w ETAP 1 |
| Volume Detector | ✅ Działający | Wydzielony w ETAP 1 |
| MarketEvent model | ✅ Działający | 27 pól, 13 etapów cyklu życia |
| Konfiguracje progów | ✅ Gotowe | price_detector.py, volume_detector.py |

### Zależności wewnątrz ETAPU 6

| Krok | Zależy od |
|------|-----------|
| Krok 1 (interfejsy) | — (pierwszy krok) |
| Krok 2 (Technical Event Detector) | Krok 1 |
| Krok 3 (Fundamental Event Detector) | Krok 1 |
| Krok 4 (korporacyjne/regulacyjne) | Krok 1 |
| Krok 5 (makro/ETF/derivatives) | Krok 1 |
| Krok 6 (sentiment/system) | Krok 1 |
| Krok 7 (scalanie) | Kroki 2-6 |
| Krok 8 (testy) | Kroki 2-7 |

---

## 5. ZAKRES

### 5.1 Nowe komponenty

| Komponent | Opis |
|-----------|------|
| **Technical Event Detector** | Wykrywanie: zmienność (ATR, BB), wybicia S/R, formacje świecowe, trend (MA), momentum (RSI, MACD, Stochastic), wskaźniki (OBV, VWAP, Fibonacci) |
| **Fundamental Event Detector** | Wykrywanie: zmiany wskaźników finansowych (P/E, P/BV), wyniki kwartalne, raporty, dywidendy, splity, emisje, skup akcji |
| **Corporate Event Detector** | Wykrywanie: insider trading, zmiany akcjonariatu, rekomendacje, ratingi, fuzje i przejęcia, kontrakty, kwestie prawne, upadłości, zmiany zarządu |
| **Regulatory Event Detector** | Wykrywanie: komunikaty ESPI (GPW), EBI (NewConnect), opóźnienia publikacji |
| **Macro Event Detector** | Wykrywanie: dane makroekonomiczne, decyzje o stopach, inflacja, ruchy walutowe, surowce, geopolityka |
| **ETF Event Detector** | Wykrywanie: zmiany składu ETF, przepływy, premia/dyskonto, likwidacje |
| **Derivatives Event Detector** | Wykrywanie: nietypowa aktywność na opcjach, short interest, dark pool, nietypowe transakcje |
| **Sentiment & News Event Detector** | Wykrywanie: wzmianki w social media, zmiany sentymentu, newsy, wyniki Tavily |
| **System Event Detector** | Wykrywanie: zdarzenia złożone, zmiany stanu instrumentu, zdarzenia międzyinstrumentowe, sezonowe, sektorowe, korelacje |

### 5.2 Modyfikacje istniejących komponentów

| Komponent | Zakres modyfikacji |
|-----------|-------------------|
| `engines/price_detector/` | Brak — już wydzielony, działa. Możliwa refaktoryzacja pod wspólny interfejs. |
| `engines/volume_detector/` | Brak — już wydzielony, działa. Możliwa refaktoryzacja pod wspólny interfejs. |
| `config/` | Dodanie nowych konfiguracji progów dla nowych detektorów. |
| `engines/master/engine.py` | Rozszerzenie orkiestracji o nowe detektory (jeśli wymagane). |
| `data/models/market_event.py` | Ewentualne dodanie brakujących pól kontekstowych dla nowych rodzin zdarzeń. |

### 5.3 Nowe pliki konfiguracyjne

| Plik | Opis |
|------|------|
| `config/technical_events.py` | Progi dla Technical Event Detector |
| `config/fundamental_events.py` | Progi dla Fundamental Event Detector |
| `config/corporate_events.py` | Progi dla Corporate Event Detector |
| `config/macro_events.py` | Progi dla Macro Event Detector |
| `config/etf_events.py` | Progi dla ETF Event Detector |
| `config/sentiment_events.py` | Progi dla Sentiment & News Event Detector |

### 5.4 Nowe testy

Dla każdego nowego detektora:
- Testy jednostkowe detektora (mockowane dane wejściowe)
- Testy integracyjne z istniejącymi silnikami
- Testy kontraktu danych (zgodność z MarketEvent)

---

## 6. ELEMENTY POZA ZAKRESEM

Następujące elementy **nie wchodzą** w zakres ETAPU 6:

1. **Implementacja DecisionEngine** — logika decyzyjna AI pozostaje placeholderem (zgodnie z dokumentacją).
2. **Implementacja oceny jakości zdarzeń** — Critical/High/Medium/Low/Ignore pozostaje do ETAPU 7+.
3. **Scalanie zdarzeń (Composite Events)** — logika łączenia podobnych zdarzeń pozostaje do ETAPU 7+.
4. **Nowe źródła danych** — nie dodajemy nowych źródeł (ESPI, EBI, SEC, social media API).
5. **Modyfikacja Public API istniejących silników** — silniki pozostają zamrożone.
6. **Modyfikacja warstwy aplikacyjnej** — Runtime, Scheduler, AlertBuilder pozostają bez zmian.
7. **Modyfikacja frontendu** — widoki dashboardu pozostają bez zmian.
8. **Modyfikacja API** — endpointy REST pozostają bez zmian.
9. **Dodawanie kryptowalut, Forex, indeksów** — poza zakresem (ETAP 6 skupia się na GPW/USA/ETF).

---

## 7. PROPONOWANY PODZIAŁ NA KROKI

### Krok 1: Wspólny interfejs detektorów i registry pattern

**Zakres**:
- Zaprojektowanie i implementacja abstrakcyjnego interfejsu `BaseDetector`
- Implementacja `DetectorRegistry` (rejestracja i wywoływanie detektorów)
- Implementacja `DetectionResult` (wspólny format wyniku detekcji)
- Implementacja `DetectionContext` (dane wejściowe dla wszystkich detektorów)
- Adaptacja istniejących `PriceDetector` i `VolumeDetector` do nowego interfejsu

**Rezultat**: Framework dla wszystkich detektorów.

### Krok 2: Technical Event Detector

**Zakres**:
- Implementacja wykrywania zdarzeń zmienności (Volatility Spike, BB Expansion, BB Squeeze)
- Implementacja wykrywania wybić technicznych (Resistance Breakout, Support Breakdown)
- Implementacja wykrywania formacji świecowych (jeśli nie są jeszcze w TechnicalEngine)
- Implementacja wykrywania trendu (MA Crossover, Price vs MA, Trend Structure Change)
- Implementacja wykrywania momentum (RSI Overbought/Oversold, MACD Crossover)
- Implementacja wykrywania wskaźników technicznych (OBV Divergence, ATR Expansion)

**Rezultat**: Technical Event Detector wykrywający ~34 zdarzenia.

### Krok 3: Fundamental Event Detector

**Zakres**:
- Implementacja wykrywania zmian wskaźników finansowych (P/E, P/BV, Market Cap, Debt, Revenue, Net Income)
- Implementacja wykrywania wyników finansowych (Earnings Release, Guidance Update)
- Implementacja wykrywania raportów (Quarterly/Annual Report Filed)
- Implementacja wykrywania dywidend, splitów, emisji, skupu akcji

**Rezultat**: Fundamental Event Detector wykrywający ~24 zdarzenia.

### Krok 4: Corporate Event Detector + Regulatory Event Detector

**Zakres**:
- Implementacja wykrywania insider trading
- Implementacja wykrywania zmian akcjonariatu
- Implementacja wykrywania rekomendacji i ratingów
- Implementacja wykrywania fuzji i przejęć
- Implementacja wykrywania kontraktów, kwestii prawnych, upadłości, zmian zarządu
- Implementacja wykrywania komunikatów ESPI/EBI (szkielet — wymaga integracji z API GPW)

**Rezultat**: Corporate (~34 zdarzenia) + Regulatory (~3 zdarzenia) Event Detectors.

### Krok 5: Macro Event Detector + ETF Event Detector + Derivatives Event Detector

**Zakres**:
- Implementacja wykrywania zdarzeń makroekonomicznych (PKB, stopy, inflacja, waluty, surowce, geopolityka)
- Implementacja wykrywania zdarzeń ETF (rebalancing, flows, premium/discount, closure)
- Implementacja wykrywania zdarzeń pochodnych (opcje, short interest, dark pool, block trades)

**Rezultat**: Macro (~16), ETF (~4), Derivatives (~9) Event Detectors.

### Krok 6: Sentiment & News Event Detector + System Event Detector

**Zakres**:
- Implementacja wykrywania zdarzeń sentymentowych (social media spike, sentiment shift, VIX)
- Implementacja wykrywania newsów (breaking news, analityczne, wywiady)
- Implementacja wykrywania zdarzeń Tavily
- Implementacja wykrywania zdarzeń systemowych (composite events, state change, recurrence)
- Implementacja wykrywania zdarzeń międzyinstrumentowych, sezonowych, sektorowych, korelacji

**Rezultat**: Sentiment (~11) + System (~12) Event Detectors.

### Krok 7: Integracja i orkiestracja

**Zakres**:
- Podłączenie wszystkich detektorów do MasterEngine
- Testy integracyjne pełnego pipeline'u detekcji
- Walidacja spójności z kontraktem MarketEvent
- Benchmark wydajności detekcji

**Rezultat**: W pełni zintegrowany system detektorów.

### Krok 8: Testy i dokumentacja

**Zakres**:
- Testy jednostkowe wszystkich detektorów
- Testy integracyjne z istniejącymi silnikami
- Testy wydajnościowe
- Aktualizacja dokumentacji projektu
- Finalny przegląd kodu

**Rezultat**: W pełni przetestowany system detektorów, gotowy do zamrożenia.

---

## 8. RYZYKA

| Ryzyko | Prawdopodobieństwo | Wpływ | Sposób ograniczenia |
|--------|-------------------|-------|---------------------|
| **Rozmiar ETAPU 6** — implementacja 9 detektorów to duży zakres | Wysokie | Średni | Podział na 8 małych kroków, każdy zamykany osobno |
| **Brak źródeł danych** — ESPI, EBI, SEC, social media wymagają zewnętrznych API | Wysokie | Wysoki | Detektory wymagające zewn. źródeł oznaczamy jako `[Future]` i implementujemy tylko szkielet |
| **Złożoność formacji świecowych** — implementacja 10 formacji to dużo kodu | Średnie | Niski | Większość formacji może być zaimplementowana przez kombinację istniejących funkcji w candle.py |
| **Brak danych fundamentalnych dla GPW** — yfinance ma ograniczone dane dla GPW | Średnie | Średni | Fundamental Event Detector dla GPW działa z dostępnymi danymi, reszta oznaczona jako `[Future]` |
| **Zgodność z zamrożoną architekturą** — detektory nie mogą modyfikować Public API silników | Niskie | Wysoki | Detektory są rozszerzeniami, nie modyfikacjami; korzystają wyłącznie z Public API |
| **Wydajność** — 9 detektorów dla ~157 zdarzeń może być wolne | Niskie | Średni | Detektory są uruchamiane tylko gdy spełnione są wstępne kryteria (np. Price Surge uruchamia się tylko przy zmianie > progu) |

---

## 9. KRYTERIA UKOŃCZENIA

ETAP 6 jest ukończony, gdy:

1. **Interfejs detektorów**: `BaseDetector` i `DetectorRegistry` są zaimplementowane i działają.

2. **Wszystkie 9 detektorów** jest zaimplementowanych:
   - Price Event Detector (istniejący, dostosowany do nowego interfejsu)
   - Volume Event Detector (istniejący, dostosowany do nowego interfejsu)
   - Technical Event Detector
   - Fundamental Event Detector
   - Corporate Event Detector
   - Regulatory Event Detector
   - Macro Event Detector
   - ETF Event Detector
   - Derivatives Event Detector
   - Sentiment & News Event Detector
   - System Event Detector

3. **Każdy detektor** poprawnie:
   - Wykrywa zdarzenia zgodne z Katalogiem Zdarzeń Rynkowych
   - Zwraca `DetectionResult` z poprawnym typem zdarzenia
   - Respektuje niezmienniki kontraktu `MarketEvent`

4. **Testy**:
   - Wszystkie testy jednostkowe przechodzą
   - Testy integracyjne z istniejącymi silnikami przechodzą
   - Testy kontraktu danych (zgodność z MarketEvent) przechodzą

5. **Brak naruszeń rdzenia**:
   - Nie zmieniono Public API istniejących silników
   - Nie zmieniono warstwy aplikacyjnej
   - Nie zmieniono frontendu
   - Nie zmieniono API
   - Detektory są rozszerzeniami, nie modyfikacjami

6. **Dokumentacja**:
   - Nowe detektory są udokumentowane
   - `struktura_alchemik.txt` odzwierciedla nowe komponenty
   - Dokumentacja projektu jest zaktualizowana

---

## 10. KRYTERIA ZAMROŻENIA

ETAP 6 zostaje zamrożony, gdy:

1. Wszystkie kryteria ukończenia są spełnione.
2. Wszystkie testy przechodzą w 100%.
3. Repozytorium jest w spójnym stanie (git commit).
4. Brak otwartych problemów (issue) związanych z detektorami.
5. Dokumentacja jest kompletna i zgodna z kodem.
6. Właściciel projektu zaakceptował stan ETAPU 6.

Po zamrożeniu ETAPU 6:
- Detektory stają się częścią zamrożonej architektury rdzenia.
- Nowe typy zdarzeń są dodawane przez rozszerzenia, nie modyfikacje istniejących detektorów.
- Zmiana interfejsu detektora wymaga świadomej decyzji projektowej i nowej rewizji dokumentacji.

---

## 11. KONTRAKT WSPÓLNEGO FRAMEWORKA DETEKTORÓW

### 11.1 Cel kontraktu

Framework detektorów definiuje jednolity interfejs dla wszystkich detektorów zdarzeń rynkowych Etapu 6. Detektor jest samodzielną jednostką odpowiedzialną za analizę danych wejściowych i zwrócenie listy wyników detekcji. Każdy wynik reprezentuje pojedyncze wykryte zdarzenie. Konwersja wyniku detekcji na obiekt `MarketEvent` należy do warstwy orkiestracji (Krok 7 — Integracja), a nie do samego detektora.

Kontrakt został zaprojektowany w oparciu o istniejącą architekturę:
- wzorzec `PriceDetector.detect(ticker, market, instrument_type, ohlcv_data) -> list[MarketEvent]`,
- wewnętrzny model `_DetectionResult` używany przez `PriceDetector` przed utworzeniem `MarketEvent`,
- model `MarketEvent` z 27 polami zdefiniowanymi w `docs/Kontrakt_Zdarzen_Rynkowych.md`.

### 11.2 Hierarchia klasyfikacji zdarzeń

Projekt ALCHEMIK definiuje czteropoziomową hierarchię klasyfikacji zdarzeń rynkowych, opisaną w `docs/Hierarchia_Zdarzen_Rynkowych.md` i `docs/Katalog_Zdarzen_Rynkowych.md`:

```text
EventFamily (enum, 11 wartości)
└── event_category (str, ~30 wartości katalogowych)
    └── event_subcategory (str | None, tylko dla rodzin PRICE, VOLUME, TECHNICAL)
        └── event_type (str, ~157 wartości — unikalny identyfikator)
```

**Przykład z Katalogu** — zdarzenie `PRICE_SURGE` (ID 1.1):

```text
EventFamily: TECHNICAL (ustawiane przez orkiestrację na podstawie detector_id)
└── event_category: "Cenowe"      — pobrane z Katalogu na podstawie event_type
    └── event_subcategory: "Ruchy kierunkowe"  — pobrane z Katalogu na podstawie event_type
        └── event_type: "PRICE_SURGE"  — ustawiane przez detektor
                   priority_raw: CRITICAL  — pobrane z Katalogu na podstawie event_type
```

**Przykład** — dwa zdarzenia w tej samej rodzinie TECHNICAL, różniące się kategorią i podkategorią:

```text
EventFamily: TECHNICAL
├── event_category: "Zmienność" / event_subcategory: "Odchylenie ATR"
│   └── event_type: "VOLATILITY_SPIKE" (ID 3.1)
│
├── event_category: "Wybicia" / event_subcategory: "Poziomy S/R"
│   └── event_type: "RESISTANCE_BREAKOUT" (ID 4.1)
│
├── event_category: "Momentum" / event_subcategory: "RSI"
│   └── event_type: "RSI_OVERSOLD" (ID 7.2)
│
└── event_category: "Fundamenty spółki" / event_subcategory: None
    └── event_type: "PE_RATIO_CHANGE" (ID 9.1)
```

#### Definicje poziomów

| Poziom | Typ w kodzie | Znaczenie | Występowanie |
|--------|------------|-----------|-------------|
| `EventFamily` | `EventFamily` (enum) | Najwyższy poziom — rodzina zdarzeń. Odpowiada detektorowi. | Zawsze obecny. 11 wartości: `PRICE`, `VOLUME`, `TECHNICAL`, `FUNDAMENTAL`, `CORPORATE`, `REGULATORY`, `MACRO`, `ETF`, `DERIVATIVES`, `SENTIMENT`, `SYSTEM`. |
| `event_category` | `str` | Podgrupa w ramach rodziny. Np. `"Cenowe"`, `"Zmienność"`, `"Wybicia"`. | Zawsze obecny. Około 30 wartości zdefiniowanych w `docs/Hierarchia_Zdarzen_Rynkowych.md` §4. |
| `event_subcategory` | `Optional[str]` | Drobniejszy podział wewnątrz kategorii. Np. `"Ruchy kierunkowe"`, `"Luki"`, `"RSI"`. | **Tylko dla rodzin PRICE, VOLUME, TECHNICAL** (zob. §4.1–4.3 w Hierarchii). `None` dla pozostałych rodzin (FUNDAMENTAL, CORPORATE, REGULATORY, MACRO, ETF, DERIVATIVES, SENTIMENT, SYSTEM). |
| `event_type` | `str` | Najdokładniejszy identyfikator — konkretny typ zdarzenia. | Zawsze obecny. ~157 wartości w `docs/Katalog_Zdarzen_Rynkowych.md`. |

#### Kluczowa właściwość: `event_type` jednoznacznie determinuje pozostałe poziomy

Każdy `event_type` w Katalogu Zdarzeń Rynkowych ma dokładnie jedno przypisanie:
- jednej `EventFamily` (poprzez mapowanie w `docs/Hierarchia_Zdarzen_Rynkowych.md` §4),
- jednej `event_category`,
- jednej `event_subcategory` (lub jej brak),
- jednego `priority_raw`.

W związku z tym **detektor przekazuje wyłącznie `event_type`**, a pozostałe wartości (`event_category`, `event_subcategory`, `priority_raw`, `EventFamily`) są pobierane z Katalogu przez warstwę orkiestracji podczas konwersji do `MarketEvent`. Zapobiega to niespójnościom — niemożliwe jest utworzenie `DetectionResult`, w którym `event_type` wskazuje zdarzenie z rodziny PRICE, a `event_category` wskazuje kategorię z rodziny VOLUME.

### 11.3 Źródła prawdy dla klasyfikacji

Każdy element hierarchii ma dokładnie jedno źródło prawdy:

| Element | Typ w kontrakcie | Źródło prawdy | Ustawia | Waliduje |
|---------|-----------------|---------------|---------|----------|
| `EventFamily` | `EventFamily` (enum `data/models/event_enums.py`) | `docs/Hierarchia_Zdarzen_Rynkowych.md` §4 — mapowanie `event_type → EventFamily` | **Orkiestracja** — pobiera z mapowania na podstawie `event_type` | Orkiestracja (zgodność z mapowaniem) |
| `event_category` | `str` | `docs/Hierarchia_Zdarzen_Rynkowych.md` §4 — kolumna "Kategoria" dla każdego `event_type` | **Orkiestracja** — pobiera z Katalogu na podstawie `event_type` | Orkiestracja (musi odpowiadać wpisowi katalogowemu) |
| `event_subcategory` | `Optional[str]` | `docs/Hierarchia_Zdarzen_Rynkowych.md` §4 — kolumna "Podkategoria" (jeśli istnieje) | **Orkiestracja** — pobiera z Katalogu na podstawie `event_type` | Orkiestracja (musi odpowiadać wpisowi; `None` gdy katalog nie definiuje) |
| `event_type` | `str` | `docs/Katalog_Zdarzen_Rynkowych.md` — zamknięty katalog ~157 typów | **Detektor** — zwraca w `DetectionResult` | Orkiestracja (musi istnieć w Katalogu) + detektor (deklaruje w `event_types`) |
| `priority_raw` | `PriorityLevel` (enum `data/models/event_enums.py`) | `docs/Katalog_Zdarzen_Rynkowych.md` — pole "Priorytet" dla każdego zdarzenia | **Orkiestracja** — pobiera z Katalogu na podstawie `event_type` | Orkiestracja (zgodność z Katalogiem) |
| `confidence_level` | `float` | Obliczane przez detektor | **Detektor** — w `DetectionResult` | Orkiestracja (clamp `[0.0, 1.0]`) |

**Nie istnieje alternatywne źródło prawdy.** Wszystkie elementy poza `event_type` i `confidence_level` są jednoznacznie wyznaczane przez `event_type` na podstawie Katalogu.

### 11.4 DetectionContext

#### Obowiązkowe OHLCV — decyzja właściciela

Decyzja architektoniczna właściciela projektu:

> Detektor nie może zostać uruchomiony bez danych OHLCV.

Brak danych OHLCV nie powoduje zwrócenia pustej listy wyników. Brak danych OHLCV oznacza, że `DetectionContext` jest nieprawidłowy. Warstwa wywołująca detektor ma obowiązek dostarczyć kompletne dane wymagane przez kontrakt. Detektor analizuje dane — nie uzupełnia ich braku.

#### Definicja

`DetectionContext` jest niemutowalnym kontenerem danych wejściowych przekazywanym do każdego wywołania `detect()`. Jest tworzony przez warstwę orkiestracji przed wywołaniem detektorów. Kontekst bez danych OHLCV jest nieprawidłowy i nie może zostać utworzony.

**Odpowiedzialność**: dostarczenie wspólnego, kompletnego zestawu danych wejściowych dla wszystkich detektorów. Detektor używa tylko tych pól, które są dla niego istotne — pozostałe ignoruje.

**Typ**: `@dataclass(frozen=True)`.

| Pole | Typ | Wymagane | Źródło | Znaczenie |
|------|-----|----------|--------|----------|
| `ticker` | `str` | TAK | MarketScanner / HunterEngine | Symbol instrumentu (np. `"PKN.ORLEN.WA"`). Nie może być pustym łańcuchem. |
| `market` | `str` | TAK | MarketScanner / HunterEngine | Rynek notowań (np. `"GPW"`, `"NYSE"`). Nie może być pustym łańcuchem. |
| `instrument_type` | `InstrumentType` | TAK | MarketScanner / HunterEngine | Klasyfikacja instrumentu (`STOCK_GPW`, `STOCK_USA`, `ETF`). |
| `ohlcv_data` | `tuple[MarketData, ...]` | TAK | YahooFinanceFetcher → MarketScanner | Krotka niemutowalna. Niepusta. Elementy posortowane chronologicznie według `MarketData.timestamp` (najstarszy pierwszy). Każdy element jest instancją `MarketData`. Dane muszą dotyczyć instrumentu wskazanego przez `ticker`, `market` i `instrument_type`. |

**Konwencje**:

- `ohlcv_data` jest polem bezwzględnie wymaganym, nie posiada wartości domyślnej.
- Konstruktor `DetectionContext` wymaga jawnego przekazania niepustej krotki `ohlcv_data`.
- Pusta krotka `()` **nie jest dozwolona** — próba utworzenia `DetectionContext` z pustym `ohlcv_data` jest błędem kontraktu.
- `ohlcv_data` używa `tuple[MarketData, ...]`, co w połączeniu z `frozen=True` gwarantuje niemutowalność strukturalną kontekstu.
- Detektor nie modyfikuje `DetectionContext` — obiekt jest niemutowalny.

**Uwaga — świadome ograniczenie**: `DetectionContext` gwarantuje niemutowalność swojej struktury i referencji do kolekcji OHLCV, ale nie gwarantuje głębokiej niemutowalności obiektów `MarketData`, ponieważ istniejący zamrożony model `MarketData` nie jest modelem `frozen`. Nie można zmienić pola `ohlcv_data`, nie można zastąpić krotki inną krotką, nie można dodawać ani usuwać elementów krotki, ale pojedynczy obiekt `MarketData` wewnątrz krotki może pozostać mutowalny. Jest to świadome ograniczenie istniejącego zamrożonego modelu i nie stanowi błędu ani blokera.
- Wszystkie detektory otrzymują ten sam `DetectionContext` podczas jednego cyklu analizy dla danego instrumentu.
- Pola `ticker`, `market`, `instrument_type` odpowiadają polom 3–5 `MarketEvent` i będą przepisane bezpośrednio podczas konwersji przez warstwę orkiestracji.

#### Walidacja strukturalna (`DetectionContext`)

`DetectionContext` odpowiada za walidację strukturalną przy tworzeniu:

| Warunek | Konsekwencja niespełnienia |
|---------|---------------------------|
| `ticker` nie jest pusty | Nie można utworzyć poprawnego `DetectionContext` |
| `market` nie jest pusty | Nie można utworzyć poprawnego `DetectionContext` |
| `instrument_type` jest instancją `InstrumentType` | Nie można utworzyć poprawnego `DetectionContext` |
| `ohlcv_data` jest krotką (`tuple`) | Nie można utworzyć poprawnego `DetectionContext` |
| `ohlcv_data` nie jest puste (`len(ohlcv_data) > 0`) | Nie można utworzyć poprawnego `DetectionContext` |
| Każdy element `ohlcv_data` jest instancją `MarketData` | Nie można utworzyć poprawnego `DetectionContext` |
| `ohlcv_data` jest uporządkowane chronologicznie według `timestamp` | Nie można utworzyć poprawnego `DetectionContext` |

Nieprawidłowy `DetectionContext` nie może zostać przekazany do `detect()`. Warstwa orkiestracji nie może wywołać detektora z nieprawidłowym kontekstem.

### 11.5 DetectionResult

`DetectionResult` jest wewnętrznym, lekkim modelem reprezentującym pojedyncze wykrycie zdarzenia przez detektor. **Nie jest** publicznym zdarzeniem systemowym — służy wyłącznie do przekazania wyniku z detektora do warstwy orkiestracji, która tworzy z niego obiekt `MarketEvent`.

**Odpowiedzialność**: przeniesienie minimalnego, niezbędnego zestawu danych z detektora do orkiestracji. `DetectionResult` zawiera **wyłącznie** dane, których orkiestracja nie może samodzielnie ustalić na podstawie `event_type` i Katalogu Zdarzeń.

**Zasada**: detektor przekazuje tylko to, co sam wykrył i obliczył. Wszystkie wartości wyliczalne z `event_type` są pobierane przez orkiestrację z Katalogu. Dzięki temu `DetectionResult` nie może zawierać sprzecznej klasyfikacji — niemożliwe jest, aby `event_type` wskazywał zdarzenie PRICE, a przekazana osobno `event_category` wskazywała kategorię z rodziny VOLUME.

**Typ**: `@dataclass(frozen=True)`.

| Pole | Typ | Wymagane | Znaczenie | Kto ustawia / skąd |
|------|-----|----------|-----------|-------------------|
| `event_type` | `str` | TAK | Identyfikator typu zdarzenia — klucz do Katalogu (np. `"PRICE_SURGE"`, `"RSI_OVERSOLD"`). Wartość musi należeć do zamkniętego katalogu w `docs/Katalog_Zdarzen_Rynkowych.md`. | **Detektor** — wybiera na podstawie analizy. |
| `confidence_level` | `float` | TAK | Pewność detekcji obliczona przez detektor. Musi należeć do `[0.0, 1.0]`. | **Detektor** — oblicza na podstawie siły sygnału. |
| `price_data` | `PriceData \| None` | NIE | Dane cenowe OHLCV z bieżącej i poprzedniej świecy. **Wymagane** dla detektorów operujących na danych cenowych (rodziny PRICE, VOLUME, TECHNICAL). `None` dla pozostałych. | **Detektor** — tworzy z `context.ohlcv_data`. |
| `volume_data` | `VolumeData \| None` | NIE | Dane wolumenowe. **Wymagane** dla detektorów rodziny VOLUME. `None` dla pozostałych. | **Detektor** — tworzy z `context.ohlcv_data`. |

**Pola NIEobecne w `DetectionResult`** (pobierane przez orkiestrację z Katalogu):

| Pole | Dlaczego nie w `DetectionResult` |
|------|--------------------------------|
| `event_category` | Jednoznacznie wyznaczane przez `event_type` na podstawie `docs/Hierarchia_Zdarzen_Rynkowych.md` §4 |
| `event_subcategory` | Jednoznacznie wyznaczane przez `event_type` na podstawie `docs/Hierarchia_Zdarzen_Rynkowych.md` §4 |
| `priority_raw` | Jednoznacznie wyznaczane przez `event_type` na podstawie `docs/Katalog_Zdarzen_Rynkowych.md` |
| `EventFamily` | Jednoznacznie wyznaczane przez `event_type` na podstawie `docs/Hierarchia_Zdarzen_Rynkowych.md` §4 |
| `metadata` | Usunięte — wszystkie dane potrzebne do utworzenia `MarketEvent` są przekazywane przez jawne pola kontraktu |

**Konwencje**:

- `event_type` i `confidence_level` są zawsze wymagane, bez wartości domyślnych.
- `price_data` i `volume_data` używają składni `X | None` (równoważnej `Optional[X]`).
  - Detektory rodzin PRICE/VOLUME/TECHNICAL: **muszą ustawić `price_data`** na instancję `PriceData`.
  - Detektory rodziny VOLUME: **muszą dodatkowo ustawić `volume_data`** na instancję `VolumeData`.
  - Detektory pozostałych rodzin: ustawiają `price_data=None`, `volume_data=None`.
- Brak detekcji → `[]`. Pusta lista **nie** oznacza błędu — oznacza poprawną analizę bez wykrycia.
- Każdy `DetectionResult` → dokładnie jeden przyszły `MarketEvent`.

#### Rozróżnienie: brak danych vs. brak detekcji

| Sytuacja | Znaczenie | Zachowanie |
|----------|-----------|------------|
| `ohlcv_data == ()` | **Błąd kontraktu** | `DetectionContext` nie zostaje utworzony. Orkiestracja otrzymuje błąd walidacji. |
| Poprawny kontekst, analiza OK, nic nie wykryto | **Brak detekcji** — normalny przypadek | `detect()` → `[]` |
| Poprawny kontekst, zdarzenia wykryte | **Sukces** | `detect()` → `[DetectionResult(...), ...]` |

#### Ochrona przed niespójną klasyfikacją

Ponieważ `DetectionResult` zawiera wyłącznie `event_type` (a nie `event_category`, `event_subcategory` czy `priority_raw`), **niemożliwe jest utworzenie niespójnego wyniku** — nie istnieje mechanizm, w którym detektor przekazałby sprzeczne wartości klasyfikacji. Orkiestracja pobiera wszystkie elementy klasyfikacji z jednego źródła prawdy (Katalogu) na podstawie `event_type`.

### 11.6 BaseDetector

`BaseDetector` jest abstrakcyjną klasą bazową dla wszystkich detektorów.

**Docelowe Public API**:

```python
from abc import ABC, abstractmethod

from engines.detectors.models import DetectionContext, DetectionResult


class BaseDetector(ABC):
    """Abstract base class for all market event detectors."""

    @property
    @abstractmethod
    def detector_id(self) -> str:
        """Unique identifier for this detector (e.g. 'technical_volatility')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g. 'Technical Volatility Detector')."""
        ...

    @property
    @abstractmethod
    def event_types(self) -> tuple[str, ...]:
        """
        Immutable tuple of event type identifiers this detector can emit.
        Every value must exist in docs/Katalog_Zdarzen_Rynkowych.md.
        """
        ...

    @abstractmethod
    def detect(self, context: DetectionContext) -> list[DetectionResult]:
        """
        Run detection logic on the given context.

        Preconditions:
            - context.ohlcv_data is non-empty.
            - context passes all structural validations from §11.4.
            The orchestrator must not call detect() without a valid context.

        Returns:
            list[DetectionResult] — empty list [] means the analysis
            completed successfully but no events were detected.
        """
        ...

    def can_handle(self, event_type: str) -> bool:
        """Return True if event_type is in self.event_types."""
        return event_type in self.event_types
```

**Wymagania implementacyjne**:

- `detect()` **nie** przyjmuje `**kwargs`, `*args` ani `Any`.
- `BaseDetector` jest klasą abstrakcyjną — nie można utworzyć jej instancji.
- `event_types` używa `tuple[str, ...]` — niemutowalna krotka.
- `detect()` zwraca `list[DetectionResult]`.
- `[]` = poprawna analiza bez detekcji. **Nie** = błąd.
- Detektor otrzymuje zwalidowany kontekst. Nie pobiera danych, nie rekonstruuje, nie zgaduje.
- Detektor zwraca tylko `event_type` + `confidence_level` + opcjonalne dane OHLCV. Klasyfikację (`EventFamily`, `event_category`, `event_subcategory`, `priority_raw`) pobiera orkiestracja z Katalogu.

### 11.7 Kardynalność wyniku

`detect()` zwraca **zawsze** `list[DetectionResult]`:

| Sytuacja | Wynik |
|----------|-------|
| Brak wykrytych zdarzeń po poprawnej analizie | `[]` |
| Jedno wykryte zdarzenie | `[DetectionResult(...)]` |
| Wiele wykrytych zdarzeń | `[DetectionResult(...), ...]` |
| Brak OHLCV | **Nie dotyczy** — `DetectionContext` nie powstaje, błąd przed wywołaniem |

### 11.8 Relacja DetectionResult → MarketEvent

```text
Warstwa orkiestracji:
  1. Tworzy i waliduje DetectionContext (niepuste OHLCV obowiązkowe)
        │
        ▼ (tylko jeśli kontekst poprawny)
  Dla każdego zarejestrowanego detektora:
        │
        ▼
    BaseDetector.detect(context) → list[DetectionResult]
        │
        ▼ (dla każdego DetectionResult)
    1. Pobiera event_type z DetectionResult
    2. Odczytuje z Katalogu: EventFamily, event_category,
       event_subcategory, priority_raw
    3. MarketEvent.create_new(ticker, market, instrument_type)
    4. event.set_detection(
           event_family=...,
           event_category=...,
           event_type=result.event_type,
           priority_raw=...,
           confidence_level=clamp(result.confidence_level, 0.0, 1.0),
           detection_source=f"{detector.name} (silnik)",
           event_owner=...,
           event_subcategory=...,
           price_data=result.price_data,
       )
    5. Dodaje HistoryEntry (creation + detection)
        │
        ▼
    list[MarketEvent] → MasterEngine pipeline
```

**Odpowiedzialności**:

| Komponent | Odpowiada za |
|-----------|-------------|
| **Detektor** | Otrzymuje poprawny `DetectionContext`. Wykonuje analizę. Zwraca `list[DetectionResult]` z `event_type` + `confidence_level` + opcjonalnymi danymi OHLCV. Nie tworzy `MarketEvent`. Nie przekazuje klasyfikacji (jest ona pobierana z Katalogu). |
| **Orkiestracja (Krok 7)** | Pobiera z Katalogu `EventFamily`, `event_category`, `event_subcategory`, `priority_raw` dla każdego `event_type`. Konwertuje `DetectionResult` → `MarketEvent`. Ustawia `timestamp_utc`, `detection_source`, `event_owner`. Clampuje `confidence_level`. |
| **MarketEvent** | Przenoszony przez pipeline silników (normalizacja, deduplikacja, AI, ranking, ryzyko, alert). |

### 11.9 Granice odpowiedzialności

```text
┌──────────────────────────────────────────────────────────────┐
│              WARSTWA ORKIESTRACJI (Krok 7)                    │
│                                                               │
│  - Tworzy i waliduje DetectionContext (niepuste OHLCV)        │
│  - NIE wywołuje detektora bez poprawnego kontekstu            │
│  - Wywołuje wszystkie zarejestrowane detektory                │
│  - Zbiera list[DetectionResult]                               │
│  - Pobiera klasyfikację z Katalogu dla każdego event_type     │
│  - Konwertuje DetectionResult → MarketEvent                   │
│  - Ustawia event_family, event_category, event_subcategory,   │
│    priority_raw, detection_source, event_owner,               │
│    timestamp_utc                                              │
│  - Clampuje confidence_level do [0.0, 1.0]                    │
│  - Dodaje HistoryEntry                                        │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                DETEKTORY (engines/detectors/)                  │
│                                                               │
│  - Implementują BaseDetector                                  │
│  - Otrzymują poprawny DetectionContext (tylko do odczytu)     │
│  - Zwracają list[DetectionResult] z: event_type,              │
│    confidence_level, price_data?, volume_data?                │
│  - [] = poprawna analiza bez detekcji                         │
│  - NIE przekazują event_category, event_subcategory,          │
│    priority_raw — są one pobierane z Katalogu                 │
│  - NIE tworzą MarketEvent                                     │
│  - NIE pobierają brakujących danych                           │
│  - NIE modyfikują istniejących silników                       │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│             ISTNIEJĄCE SILNIKI (ZAMROŻONE)                    │
│  - Otrzymują MarketEvent przez MasterEngine                   │
│  - Public API bez zmian                                       │
└──────────────────────────────────────────────────────────────┘
```

### 11.10 Zasady walidacji

| Co | Kto | Zasada |
|----|-----|--------|
| `context.ticker` niepusty | `DetectionContext` | Nie można utworzyć z pustym |
| `context.market` niepusty | `DetectionContext` | Nie można utworzyć z pustym |
| `context.ohlcv_data` niepuste | `DetectionContext` | `len(ohlcv_data) > 0` |
| `context.ohlcv_data` kolejność chronologiczna | `DetectionContext` | Według `MarketData.timestamp` |
| Orkiestracja nie wywołuje bez kontekstu | Orkiestracja | Sprawdza przed `detect()` |
| `event_type` istnieje w Katalogu | Orkiestracja | Przy konwersji do `MarketEvent` |
| `event_type` w `event_types` detektora | Detektor (deklaratywnie) + testy | `can_handle()` |
| `confidence_level ∈ [0.0, 1.0]` | Orkiestracja | Clamp przy konwersji |
| `price_data` ustawione gdy wymagane | Detektor | PRICE/VOLUME/TECHNICAL: instancja `PriceData` |
| `volume_data` ustawione gdy wymagane | Detektor | VOLUME: instancja `VolumeData` |
| Detektor nie modyfikuje kontekstu | Python | `frozen=True` + `tuple` |
| Klasyfikacja niesprzeczna | Niemożliwa przez konstrukcję | `DetectionResult` nie zawiera pól klasyfikacji — pobierane z jednego źródła |

### 11.11 Przykład kontraktu (nieimplementacyjny)

**Przykład poprawny** — detektor zwraca tylko `event_type` i `confidence_level`:

```python
context = DetectionContext(
    ticker="PKN.ORLEN.WA",
    market="GPW",
    instrument_type=InstrumentType.STOCK_GPW,
    ohlcv_data=(
        MarketData(open=62.0, high=63.5, low=61.8, close=63.2, volume=1_200_000, timestamp=...),
        MarketData(open=63.3, high=66.0, low=63.0, close=65.8, volume=2_500_000, timestamp=...),
    ),
)

detector = TechnicalVolatilityDetector()
results: list[DetectionResult] = detector.detect(context)
# results = [
#     DetectionResult(
#         event_type="VOLATILITY_SPIKE",
#         confidence_level=0.82,
#         price_data=PriceData(open=63.3, high=66.0, low=63.0, close=65.8, prev_close=63.2, ...),
#         volume_data=None,
#     ),
# ]
# — lub brak detekcji: results = []

# --- Konwersja do MarketEvent przez orkiestrację ---
# Dla każdego result:
#   classification = CATALOG[result.event_type]
#   # classification = {EventFamily: TECHNICAL, event_category: "Zmienność",
#   #                   event_subcategory: "Odchylenie ATR", priority_raw: CRITICAL}
#   event = MarketEvent.create_new(...)
#   event.set_detection(
#       event_family=classification.event_family,
#       event_category=classification.event_category,
#       event_type=result.event_type,
#       priority_raw=classification.priority_raw,
#       confidence_level=clamp(result.confidence_level, 0.0, 1.0),
#       detection_source=f"{detector.name} (TechnicalEngine)",
#       event_owner=EventOwner.TechnicalEngine,
#       event_subcategory=classification.event_subcategory,
#       price_data=result.price_data,
#   )
```

**Przykład niepoprawny** — błąd kontraktu:

```python
# BŁĄD KONTRAKTU — detektor nie może zostać uruchomiony bez OHLCV.
context = DetectionContext(
    ticker="PKN.ORLEN.WA",
    market="GPW",
    instrument_type=InstrumentType.STOCK_GPW,
    ohlcv_data=(),  # ❌ pusta krotka — błąd kontraktu
)
# Orkiestracja NIE wywoła detector.detect(context).
```

### 11.12 Adaptacja istniejących detektorów (zamrożonych)

Istniejące detektory `PriceDetector` (`engines/price_detector/engine.py`) i `VolumeDetector` (`engines/volume_detector/engine.py`) są częścią zamrożonego rdzenia (ETAP 1). Ich adaptacja do nowego interfejsu `BaseDetector` **wymaga osobnej decyzji właściciela projektu** o odmrożeniu tych modułów.

Do czasu podjęcia decyzji:

- Nowe detektory (Kroki 2–6) implementują `BaseDetector.detect(context: DetectionContext) -> list[DetectionResult]`.
- Istniejące `PriceDetector` i `VolumeDetector` zachowują swoje obecne Public API.
- Warstwa orkiestracji (Krok 7) obsługuje oba interfejsy równolegle.
- Możliwa przyszła opcja: adapter `PriceDetectorAdapter(BaseDetector)` bez modyfikacji istniejącego kodu.

### 11.13 Zaktualizowane kryteria ukończenia Kroku 1

Krok 1 jest ukończony, gdy:

1. `BaseDetector` ma docelową sygnaturę `detect(context: DetectionContext) -> list[DetectionResult]`.
2. `context` obowiązkowy z niepustym `ohlcv_data`. `[]` = analiza OK, brak detekcji.
3. `DetectionContext` jako `@dataclass(frozen=True)`: `ticker: str`, `market: str`, `instrument_type: InstrumentType`, `ohlcv_data: tuple[MarketData, ...]` (wymagane, bez wartości domyślnej, niepuste).
4. Pusta krotka `()` dla `ohlcv_data` → błąd kontraktu.
5. `DetectionResult` jako `@dataclass(frozen=True)`: `event_type: str`, `confidence_level: float`, `price_data: PriceData | None`, `volume_data: VolumeData | None`.
6. `DetectionResult` **nie zawiera** `event_category`, `event_subcategory`, `priority_raw`, `metadata` — są pobierane z Katalogu przez orkiestrację.
7. Wszystkie kolekcje używają `tuple[...]` i `list[...]` (nie `Tuple`/`List` z `typing`).
8. `frozen=True` nie jest łączone z mutowalnymi kolekcjami.
9. Żadne pole wymagane nie ma wartości domyślnej.
10. Brak `**kwargs`, `*args`, `Any`.
11. `BaseDetector` abstrakcyjna — nie można instancjonować.
12. `can_handle()` jako metoda konkretna.
13. `event_types` jako `tuple[str, ...]`.
14. Implementator nie zgaduje — każdy element hierarchii ma jedno źródło prawdy.

---

## 12. KRYTERIA UKOŃCZENIA

ETAP 6 jest ukończony, gdy:

1. **Interfejs detektorów**: `BaseDetector`, `DetectionContext`, `DetectionResult` i `DetectorRegistry` są zaimplementowane i działają zgodnie z sekcją 11.

2. **Wszystkie 11 detektorów** jest zaimplementowanych:
   - Price Event Detector (istniejący — adaptacja wymaga decyzji właściciela, zob. §11.10)
   - Volume Event Detector (istniejący — adaptacja wymaga decyzji właściciela, zob. §11.10)
   - Technical Event Detector
   - Fundamental Event Detector
   - Corporate Event Detector
   - Regulatory Event Detector
   - Macro Event Detector
   - ETF Event Detector
   - Derivatives Event Detector
   - Sentiment & News Event Detector
   - System Event Detector

3. **Każdy detektor** poprawnie:
   - Wykrywa zdarzenia zgodne z Katalogiem Zdarzeń Rynkowych
   - Zwraca `List[DetectionResult]` z poprawnym typem zdarzenia
   - Respektuje niezmienniki kontraktu `MarketEvent`

4. **Testy**:
   - Wszystkie testy jednostkowe przechodzą
   - Testy integracyjne z istniejącymi silnikami przechodzą
   - Testy kontraktu danych (zgodność z MarketEvent) przechodzą

5. **Brak naruszeń rdzenia**:
   - Nie zmieniono Public API istniejących silników
   - Nie zmieniono warstwy aplikacyjnej
   - Nie zmieniono frontendu
   - Nie zmieniono API
   - Detektory są rozszerzeniami, nie modyfikacjami

6. **Dokumentacja**:
   - Nowe detektory są udokumentowane
   - `struktura_alchemik.txt` odzwierciedla nowe komponenty
   - Dokumentacja projektu jest zaktualizowana

---

## 13. KRYTERIA ZAMROŻENIA

ETAP 6 zostaje zamrożony, gdy:

1. Wszystkie kryteria ukończenia są spełnione.
2. Wszystkie testy przechodzą w 100%.
3. Repozytorium jest w spójnym stanie (git commit).
4. Brak otwartych problemów (issue) związanych z detektorami.
5. Dokumentacja jest kompletna i zgodna z kodem.
6. Właściciel projektu zaakceptował stan ETAPU 6.

Po zamrożeniu ETAPU 6:
- Detektory stają się częścią zamrożonej architektury rdzenia.
- Nowe typy zdarzeń są dodawane przez rozszerzenia, nie modyfikacje istniejących detektorów.
- Zmiana interfejsu detektora wymaga świadomej decyzji projektowej i nowej rewizji dokumentacji.

---

## KONIEC DOKUMENTU

| Atrybut | Wartość |
|---------|---------|
| Data | 22.07.2026 |
| Wersja | 1.1 |
| Status | Dokument planistyczny — plan ETAPU 6 (uzupełniony o kontrakt detektorów) |
| Bazuje na | docs/Katalog_Zdarzen_Rynkowych.md, docs/Hierarchia_Zdarzen_Rynkowych.md, docs/Przeplyw_Zdarzen_Rynkowych.md, docs/Kontrakt_Zdarzen_Rynkowych.md |
