# ALCHEMIK — MODEL DOMENOWY OutcomeComputer

## DOKUMENT ARCHITEKTONICZNY — PROJEKT KOMPONENTU OBLICZENIOWEGO

Data: 30.07.2026
Wersja: 1.4
Status: Dokument projektowy — nie implementacyjny (WERSJA OSTATECZNA)

---

## SPIS TREŚCI

1. [Cel komponentu](#1-cel-komponentu)
2. [Miejsce w architekturze](#2-miejsce-w-architekturze)
3. [Odpowiedzialność komponentu](#3-odpowiedzialność-komponentu)
4. [Granice odpowiedzialności](#4-granice-odpowiedzialności)
5. [Zależności](#5-zależności)
6. [Zakres KROKU 3D i KROKU 3E](#6-zakres-kroku-3d-i-kroku-3e)
7. [Kontrakt OutcomeRepository](#7-kontrakt-outcomerepository)
8. [Sekwencja przepływu danych](#8-sekwencja-przepływu-danych)
9. [Public API — kontrakty metod](#9-public-api--kontrakty-metod)
10. [Struktura katalogowa](#10-struktura-katalogowa)
11. [Algorytm działania](#11-algorytm-działania)
12. [Tworzenie EventOutcome](#12-tworzenie-eventoutcome)
13. [Tworzenie SessionOutcome i własność](#13-tworzenie-sessionoutcome-i-własność)
14. [Obliczanie metryk](#14-obliczanie-metryk)
15. [Zarządzanie stanami](#15-zarządzanie-stanami)
16. [Integracja z Runtime i Scheduler (KROK 3E)](#16-integracja-z-runtime-i-scheduler-krok-3e)
17. [TradingCalendar — kalendarz sesji handlowych](#17-tradingcalendar--kalendarz-sesji-handlowych)
18. [Mapowanie rynków](#18-mapowanie-rynków)
19. [Obsługa błędów i brakujących danych](#19-obsługa-błędów-i-brakujących-danych)
20. [Klasyfikacja błędów — retryable i non-retryable](#20-klasyfikacja-błędów--retryable-i-non-retryable)
21. [Mapowanie błędów na stany FAILED i SKIPPED](#21-mapowanie-błędów-na-stany-failed-i-skipped)
22. [Integralność EventOutcome–SessionOutcome](#22-integralność-eventoutcomesessionoutcome)
23. [Obsługa świąt giełdowych](#23-obsługa-świąt-giełdowych)
24. [Obsługa wycofanych i zawieszonych instrumentów](#24-obsługa-wycofanych-i-zawieszonych-instrumentów)
25. [Strategia ponawiania](#25-strategia-ponawiania)
26. [Przypadki brzegowe](#26-przypadki-brzegowe)
27. [Niezmienniki](#27-niezmienniki)
28. [Konfiguracja](#28-konfiguracja)
29. [Czego OutcomeComputer NIE wykonuje](#29-czego-outcomecomputer-nie-wykonuje)
30. [Decyzje architektoniczne — wszystkie zamknięte](#30-decyzje-architektoniczne--wszystkie-zamknięte)

---

## 1. CEL KOMPONENTU

OutcomeComputer jest komponentem odpowiedzialnym za **obliczenie rezultatu zdarzenia rynkowego** (`MarketEvent`) dla wszystkich skonfigurowanych horyzontów sesyjnych.

Komponent:

- tworzy instancję `EventOutcome` dla każdego nowego `MarketEvent`,
- tworzy instancje `SessionOutcome` — po jednej dla każdego horyzontu (+1, +2, +3, +5),
- pobiera dane rynkowe dla sesji horyzontów przez istniejący `YahooFetcher` (`data.yahoo.yahoo_fetcher.YahooFetcher`),
- oblicza metryki: zmiana ceny procentowa, zmiana ceny absolutna, zmiana wolumenu procentowa, cena high/low w horyzoncie,
- zarządza cyklami życia `EventOutcome` i `SessionOutcome`.

**W KROKU 3D** OutcomeComputer jest komponentem w pełni przetestowanym jednostkowo, gotowym do integracji. **Nie jest jeszcze podłączony do `RuntimeService`** — integracja z Runtime i produkcyjnym repozytorium należy do **KROKU 3E**.

---

## 2. MIEJSCE W ARCHITEKTURZE

### 2.1 Stan po KROKU 3D

```
OutcomeComputer (engines/outcome/engine.py)
    │
    ├── zależy od: kontraktu OutcomeRepository (duck typing)
    ├── zależy od: YahooFetcher (data.yahoo.yahoo_fetcher)
    ├── zależy od: TradingCalendar (engines/outcome/calendar.py)
    ├── zależy od: OutcomeConfig (config/outcome.py)
    ├── zależy od: modeli EventOutcome i SessionOutcome
    │
    └── NIE jest podłączony do RuntimeService (to KROK 3E)
```

### 2.2 Stan po KROKU 3E (docelowy)

```
RuntimeScheduler (application/scheduler.py)
    │
    │  wywołuje co 60 sekund:
    ▼
RuntimeService.run() (application/runtime.py)
    │
    ├── 1. _run_market_scan()
    ├── 2. _run_pipeline()
    │
    ├── 3. OutcomeComputer.initialize_new_events()   ← podłączone w KROKU 3E
    │       └── tworzy EventOutcome + SessionOutcome[]
    │
    └── 4. OutcomeComputer.compute_pending_horizons() ← podłączone w KROKU 3E
            └── oblicza metryki dla dostępnych horyzontów
```

Wywołania są **synchroniczne**, **sekwencyjne**, w tym samym cyklu Runtime.

### 2.3 Relacje z istniejącymi komponentami

| Komponent | Ścieżka | Kierunek zależności | Opis |
|-----------|---------|-------------------|------|
| `MarketEvent` | `data.models.market_event` | OutcomeComputer ← MarketEvent | Odczyt: `event_id`, `ticker`, `market`, `timestamp_utc`, `price_data`, `volume_data` |
| `EventOutcome` | `data.models.event_outcome` | OutcomeComputer → EventOutcome | Tworzony i aktualizowany |
| `SessionOutcome` | `data.models.session_outcome` | OutcomeComputer → SessionOutcome | Tworzony i aktualizowany |
| `YahooFetcher` | `data.yahoo.yahoo_fetcher` | OutcomeComputer → YahooFetcher | `fetch_stock_data(symbol)` |
| `MarketData` | `data.models.market_data` | OutcomeComputer → MarketData | Struktura OHLCV |
| `TradingCalendar` | `engines.outcome.calendar` | OutcomeComputer → TradingCalendar | Wyznaczanie dat sesji |
| `OutcomeRepository` | Kontrakt (duck typing) | OutcomeComputer → repo | Odczyt MarketEvent, zapis/odczyt EventOutcome i SessionOutcome |

### 2.4 Relacja z HunterEngine

OutcomeComputer **nie korzysta** z `HunterEngine` (`engines/hunter/engine.py`). `HunterEngine` skanuje okazje inwestycyjne na podstawie score'ów — nie pobiera danych OHLCV. OutcomeComputer używa bezpośrednio `YahooFetcher.fetch_stock_data(symbol)`.

---

## 3. ODPOWIEDZIALNOŚĆ KOMPONENTU

| Odpowiedzialność | Opis |
|-----------------|------|
| Tworzenie EventOutcome | Dla każdego nowego `MarketEvent` bez EventOutcome — tworzy instancję z wartościami bazowymi, stan PENDING |
| Tworzenie SessionOutcome | Dla każdego horyzontu (+1, +2, +3, +5) — stan PENDING, `attempt_count=0` |
| Pobieranie danych rynkowych | `YahooFetcher.fetch_stock_data(symbol)` → `List[MarketData]`, filtrowanie po dacie sesji |
| Obliczanie metryk | `close_price`, `price_change_pct`, `price_change_abs`, `volume`, `volume_change_pct`, `high_price`, `low_price` |
| Zarządzanie stanami SessionOutcome | PENDING → CALCULATED / FAILED / SKIPPED |
| Zarządzanie stanami EventOutcome | Aktualizacja liczników i stanu ogólnego |
| Ponawianie (tylko retryable) | Dla błędów retryable — `attempt_count` w kolejnych cyklach |
| Wyznaczanie dat sesji | `TradingCalendar.resolve_session_date()` |

---

## 4. GRANICE ODPOWIEDZIALNOŚCI

| Odpowiedzialność | Należy do | NIE należy do OutcomeComputer |
|-----------------|-----------|-------------------------------|
| Wykrywanie zdarzeń | Detektory | OutcomeComputer nie wykrywa zdarzeń |
| Ocena jakości | `QualityEngine` | OutcomeComputer nie ocenia `quality_level` |
| Decyzja o pipeline | `DecisionEngine` | OutcomeComputer nie decyduje o News/Tavily/AI |
| Analiza AI | `engines/ai/` | OutcomeComputer nie interpretuje |
| Ocena ryzyka | `RiskEngine` | OutcomeComputer nie ocenia ryzyka |
| Ranking | `RankingEngine` | OutcomeComputer nie rankinguje |
| Alerty | `AlertBuilder`/`AlertDispatcher` | OutcomeComputer nie wysyła alertów |
| Pobieranie danych | `YahooFetcher` | OutcomeComputer nie implementuje własnego fetchera |
| Implementacja persistencji | `SQLiteHistoryRepository` (KROK 3E) | OutcomeComputer używa kontraktu — nie implementuje SQL, tabel, migracji |
| Integracja z Runtime | `RuntimeService` (KROK 3E) | OutcomeComputer nie jest podłączany do Runtime w KROKU 3D |
| Obliczanie metryk | **OutcomeComputer** | — |
| Zarządzanie stanami | **OutcomeComputer** | — |
| Interpretacja rezultatów | `engines/ai/` | OutcomeComputer nie formułuje wniosków |

---

## 5. ZALEŻNOŚCI

### 5.1 Zależności bezpośrednie — KROK 3D

| Moduł | Ścieżka | Sposób użycia |
|-------|---------|---------------|
| `MarketEvent` | `data.models.market_event` | Odczyt pól |
| `EventOutcome` | `data.models.event_outcome` | Tworzenie, aktualizacja |
| `SessionOutcome` | `data.models.session_outcome` | Tworzenie, aktualizacja |
| `YahooFetcher` | `data.yahoo.yahoo_fetcher` | `fetch_stock_data(symbol)` |
| `MarketData` | `data.models.market_data` | Pola OHLCV |
| `EventOutcomeState` | `data.models.event_outcome` | Enum |
| `SessionOutcomeState` | `data.models.session_outcome` | Enum |
| `TradingCalendar` | `engines.outcome.calendar` | `is_trading_day()`, `resolve_session_date()` |
| `OutcomeConfig` | `config.outcome` | Konfiguracja |
| `InvalidSymbolError` | `data.yahoo.yahoo_exceptions` | Obsługa wycofanych |
| `RateLimitExceededError` | `data.yahoo.yahoo_exceptions` | Limit API |
| `YahooFinanceError` | `data.yahoo.yahoo_exceptions` | Błędy API |

### 5.2 Kontrakt repozytorium — duck typing

OutcomeComputer przyjmuje repozytorium przez konstruktor bez sprawdzania typu. Repozytorium musi implementować metody opisane w §7. Projekt ALCHEMIK stosuje duck typing dla repozytoriów — `HistoryRepository` i `SQLiteHistoryRepository` są niezależnymi klasami bez dziedziczenia. `OutcomeComputer` podąża za tą samą konwencją.

W KROKU 3D repozytorium jest mockowane w testach przez `FakeOutcomeRepository`. W KROKU 3E `SQLiteHistoryRepository` otrzymuje implementację wymaganych metod.

---

## 6. ZAKRES KROKU 3D I KROKU 3E

### 6.1 Źródło podziału

- `docs/MODEL_EVENTOUTCOME.md` §16: *"Projekt komponentu obliczeniowego → KROK 3D"*, *"Integracja z API i bazą danych → KROK 3E"*
- `docs/MODEL_SESSIONOUTCOME.md` §15: *"Projekt komponentu obliczeniowego → KROK 3D"*, *"Integracja z API i bazą danych → KROK 3E"*

### 6.2 KROK 3D — zakres

| Plik | Zawartość | Status |
|------|-----------|--------|
| `engines/outcome/__init__.py` | Eksport `OutcomeComputer`, `TradingCalendar` | NOWY |
| `engines/outcome/engine.py` | `OutcomeComputer` + `DataIntegrityError` | NOWY |
| `engines/outcome/calendar.py` | `TradingCalendar` + `CalendarExpiredError` + pełne dane kalendarza (§17) | NOWY |
| `config/outcome.py` | `OutcomeConfig` | NOWY |
| `tests/test_outcome_computer.py` | Testy jednostkowe z `FakeOutcomeRepository` | NOWY |
| `tests/test_outcome_calendar.py` | Testy jednostkowe `TradingCalendar` | NOWY |

**KROK 3D NIE obejmuje:**
- `application/runtime.py` — bez zmian
- `application/sqlite_history_repository.py` — bez zmian
- `application/scheduler.py` — bez zmian

### 6.3 KROK 3E — zakres

| Plik | Zawartość |
|------|-----------|
| `application/sqlite_history_repository.py` | Implementacja metod kontraktu OutcomeRepository |
| `application/runtime.py` | Podłączenie `OutcomeComputer` w `__init__()` i `run()` |
| Nowe tabele SQLite | `event_outcomes`, `session_outcomes` |
| Testy integracyjne | OutcomeComputer + SQLiteHistoryRepository + Runtime |

---

## 7. KONTRAKT OUTCOMEREPOSITORY

### 7.1 Wymagane metody

| Metoda | Sygnatura | Opis |
|--------|-----------|------|
| `get_all_market_event_ids()` | `() -> set[str]` | Wszystkie `MarketEvent.event_id` |
| `get_market_event_by_id(event_id)` | `(str) -> Optional[MarketEvent]` | Pojedynczy MarketEvent |
| `get_all_event_outcome_ids()` | `() -> set[str]` | `market_event_id` już pokrytych przez EventOutcome |
| `save_event_outcome(event_outcome)` | `(EventOutcome) -> None` | Zapis |
| `get_event_outcome_by_id(event_outcome_id)` | `(str) -> Optional[EventOutcome]` | Po własnym ID |
| `get_event_outcome_by_market_event_id(event_id)` | `(str) -> Optional[EventOutcome]` | Po market_event_id |
| `get_pending_session_outcomes()` | `() -> list[SessionOutcome]` | Wszystkie PENDING |
| `get_session_outcomes_for_event(event_outcome_id)` | `(str) -> list[SessionOutcome]` | Wszystkie sesje dla EventOutcome |
| `save_session_outcome(session)` | `(SessionOutcome) -> None` | Zapis |

### 7.2 FakeOutcomeRepository (testy KROKU 3D)

```python
class FakeOutcomeRepository:
    """Implementacja kontraktu w pamięci — do testów jednostkowych."""
    def __init__(self):
        self.market_events: dict[str, MarketEvent] = {}
        self.event_outcomes: dict[str, EventOutcome] = {}
        self.outcome_by_market_event: dict[str, str] = {}
        self.session_outcomes: dict[str, SessionOutcome] = {}
```

---

## 8. SEKWENCJA PRZEPŁYWU DANYCH

### 8.1 `initialize_new_events()`

```
WEJŚCIE: brak

1. repo.get_all_market_event_ids() → set[str]
2. repo.get_all_event_outcome_ids() → set[str]
3. new_ids = market_event_ids - existing_outcome_ids

4. Dla każdego new_id (alfabetycznie):
   a. repo.get_market_event_by_id(event_id) → MarketEvent | None
      → None: pomiń (log WARNING)
   b. Walidacja: ticker niepusty, timestamp_utc nie-None
      → nieprawidłowy: pomiń (log WARNING)
   c. _create_event_outcome(market_event) → EventOutcome (PENDING)
   d. repo.save_event_outcome(event_outcome)
   e. Dla każdego horyzontu:
      - _create_session_outcome(event_outcome, horizon_id) → SessionOutcome (PENDING)
      - repo.save_session_outcome(session)

WYJŚCIE: list[EventOutcome]
```

### 8.2 `compute_pending_horizons()`

```
WEJŚCIE: brak

1. repo.get_pending_session_outcomes() → list[SessionOutcome]
   Sortowanie: event_outcome_id, horizon_id

2. Dla każdego PENDING SessionOutcome:
   a. repo.get_event_outcome_by_id(session.event_outcome_id) → EventOutcome | None
      → None: DataIntegrityError (log ERROR, pomiń, kontynuuj)
   b. Walidacja rynku przez OutcomeComputer (nie TradingCalendar):
      - Normalizacja: `market.strip()`
      - Jeśli pusty → SKIPPED "market_not_specified" (non-retryable, TradingCalendar nie wywoływany)
      - Jeśli niepusty, ale nie istnieje w `_MARKET_CALENDAR_MAP`:
        → SKIPPED "unknown_market" (non-retryable, TradingCalendar nie wywoływany)
   c. TradingCalendar.resolve_session_date(detection_timestamp, offset, market)
      → wywoływane wyłącznie dla rynku poprawnie zmapowanego
      → CalendarExpiredError: FAILED "calendar_expired" (non-retryable)
   d. Jeśli session_date > now → POMIŃ (nie zwiększaj attempt_count)
   e. YahooFetcher.fetch_stock_data(ticker)
      → InvalidSymbolError: SKIPPED "instrument_delisted" (non-retryable)
      → RateLimitExceededError: retryable (attempt_count+=1; FAILED po limicie)
      → YahooFinanceError: retryable (attempt_count+=1; FAILED po limicie)
      → Sukces: List[MarketData] → kontynuuj
   f. _find_market_data(history, session_date) → MarketData | None
      → None: retryable (attempt_count+=1; FAILED po limicie)
   g. _compute_metrics(session, event_outcome, market_data) → SessionOutcome (CALCULATED)
   h. repo.save_session_outcome(session)
   i. _update_event_outcome_state(event_outcome); repo.save_event_outcome(event_outcome)

WYJŚCIE: int — liczba zmienionych SessionOutcome
```

---

## 9. PUBLIC API — KONTRAKTY METOD

### 9.1 `initialize_new_events() -> list[EventOutcome]`

- **Idempotentność**: TAK (pomija istniejące EventOutcome)
- **Kolejność**: alfabetycznie po `event_id`
- **Limity**: brak
- **Pusty wynik**: `[]`

### 9.2 `compute_pending_horizons() -> int`

- **Idempotentność**: TAK dla CALCULATED (pominięte przez `get_pending_session_outcomes()`)
- **Częściowy błąd**: pojedynczy ticker → kontynuuje; błąd repo → przerywa; `DataIntegrityError` → pomija, kontynuuje
- **Pusty wynik**: `0`

### 9.3 `get_event_outcome(event_id: str) -> Optional[EventOutcome]`

### 9.4 `get_event_outcomes_by_state(state: EventOutcomeState) -> list[EventOutcome]`

---

## 10. STRUKTURA KATALOGOWA

```
engines/
└── outcome/                              # NOWY (KROK 3D)
    ├── __init__.py                       # Eksport: OutcomeComputer, TradingCalendar
    ├── engine.py                         # OutcomeComputer + DataIntegrityError
    └── calendar.py                       # TradingCalendar + CalendarExpiredError
                                          # + _HOLIDAYS (wszystkie święta)
                                          # + _MARKET_CALENDAR_MAP (mapowanie rynków)

config/
└── outcome.py                            # NOWY (KROK 3D)

tests/
├── test_outcome_computer.py              # NOWY (KROK 3D)
└── test_outcome_calendar.py              # NOWY (KROK 3D)
```

---

## 11. ALGORYTM DZIAŁANIA

Patrz §8 — szczegółowa sekwencja przepływu danych.

---

## 12. TWORZENIE EVENTOUTCOME

```python
def _create_event_outcome(self, market_event: MarketEvent) -> EventOutcome:
    return EventOutcome(
        event_outcome_id=str(uuid.uuid4()),
        market_event_id=market_event.event_id,
        state=EventOutcomeState.PENDING,
        ticker=market_event.ticker,
        market=market_event.market,
        detection_timestamp=market_event.timestamp_utc,
        base_price=(
            market_event.price_data.close
            if market_event.price_data and market_event.price_data.close is not None
            else None
        ),
         base_volume=(
             market_event.volume_data.current_volume
             if market_event.volume_data and market_event.volume_data.current_volume is not None
             else None
         ),
        event_family=market_event.event_family.value,
        event_type=market_event.event_type,
        quality_level=market_event.quality_level.value,
        expected_horizons=len(self._config.horizons),
        horizons_calculated=0, horizons_failed=0, horizons_skipped=0,
        missing_horizons=list(self._config.horizons),
        created_at=datetime.now(timezone.utc),
        rule_version=self._config.rule_version,
        failure_reason=None, invalid_reason=None,
    )
```

| Pole EventOutcome | Źródło | Wymagalność |
|-------------------|--------|-------------|
| `market_event_id` | `MarketEvent.event_id` | Wymagane |
| `ticker` | `MarketEvent.ticker` | Wymagane — jeśli puste, zdarzenie pomijane |
| `market` | `MarketEvent.market` | Kopiowane bez zmian — walidacja w `compute_pending_horizons()` |
| `detection_timestamp` | `MarketEvent.timestamp_utc` | Wymagane |
| `base_price` | `MarketEvent.price_data.close` | Opcjonalne |
| `base_volume` | `MarketEvent.volume_data.current_volume` | Opcjonalne |
| `event_family` | `MarketEvent.event_family.value` | Wymagane |
| `event_type` | `MarketEvent.event_type` | Wymagane |
| `quality_level` | `MarketEvent.quality_level.value` | Wymagane |

---

## 13. TWORZENIE SESSIONOUTCOME I WŁASNOŚĆ

```python
def _create_session_outcome(self, event_outcome: EventOutcome, horizon_id: str) -> SessionOutcome:
    return SessionOutcome(
        session_outcome_id=str(uuid.uuid4()),
        event_outcome_id=event_outcome.event_outcome_id,
        horizon_id=horizon_id,
        state=SessionOutcomeState.PENDING,
        attempt_count=0,
        close_price=None, price_change_pct=None, price_change_abs=None,
        volume=None, volume_change_pct=None,
        high_price=None, low_price=None,
        failure_reason=None, skip_reason=None,
        computed_at=None, rule_version=None, data_source=None,
    )
```

**Własność**: EventOutcome jest jedynym właścicielem domenowym kolekcji SessionOutcome (NIEZMIENNIKI N2, N3 z MODEL_SESSIONOUTCOME.md). OutcomeComputer jest komponentem operacyjnym — nie jest właścicielem.

---

## 14. OBLICZANIE METRYK

```python
def _compute_metrics(self, session, event_outcome, market_data):
    session.close_price = market_data.close
    session.high_price = market_data.high
    session.low_price = market_data.low
    session.volume = market_data.volume

    if event_outcome.base_price and event_outcome.base_price != 0:
        session.price_change_pct = (market_data.close - event_outcome.base_price) / event_outcome.base_price * 100.0
        session.price_change_abs = market_data.close - event_outcome.base_price
    else:
        session.price_change_pct = None; session.price_change_abs = None

    if event_outcome.base_volume and event_outcome.base_volume > 0 and market_data.volume is not None:
        session.volume_change_pct = (market_data.volume - event_outcome.base_volume) / event_outcome.base_volume * 100.0
    else:
        session.volume_change_pct = None

    session.computed_at = datetime.now(timezone.utc)
    session.rule_version = self._config.rule_version
    session.data_source = "YahooFinance"
    session.state = SessionOutcomeState.CALCULATED
    return session
```

`YahooFetcher` zwraca adjusted close — OutcomeComputer nie wykonuje własnych korekt.

---

## 15. ZARZĄDZANIE STANAMI

### 15.1 SessionOutcome

| Ze stanu | Do stanu | Wyzwalacz |
|----------|----------|-----------|
| PENDING | CALCULATED | `_compute_metrics()` OK |
| PENDING | FAILED | Retryable po limicie LUB non-retryable kategorii FAILED |
| PENDING | SKIPPED | Non-retryable kategorii SKIPPED |

### 15.2 EventOutcome

```python
def _update_event_outcome_state(self, event_outcome):
    sessions = self._repo.get_session_outcomes_for_event(event_outcome.event_outcome_id)
    total = len(sessions)
    calculated = sum(1 for s in sessions if s.state == SessionOutcomeState.CALCULATED)
    failed = sum(1 for s in sessions if s.state == SessionOutcomeState.FAILED)
    skipped = sum(1 for s in sessions if s.state == SessionOutcomeState.SKIPPED)
    pending = total - calculated - failed - skipped

    event_outcome.horizons_calculated = calculated
    event_outcome.horizons_failed = failed
    event_outcome.horizons_skipped = skipped
    event_outcome.missing_horizons = [s.horizon_id for s in sessions if s.state == SessionOutcomeState.PENDING]

    if calculated == 0 and failed == 0 and skipped == 0:
        event_outcome.state = EventOutcomeState.PENDING
    elif calculated + failed + skipped == total and pending == 0:
        if failed > 0:       event_outcome.state = EventOutcomeState.FAILED
        elif calculated == 0: event_outcome.state = EventOutcomeState.INVALID
        else:                 event_outcome.state = EventOutcomeState.COMPLETE
    else:
        event_outcome.state = EventOutcomeState.PARTIAL

    self._repo.save_event_outcome(event_outcome)
```

| Warunek | Stan EventOutcome |
|---------|-------------------|
| Wszystkie PENDING | PENDING |
| Mieszanka | PARTIAL |
| Wszystkie terminalne, brak FAILED, ≥1 CALCULATED | COMPLETE |
| ≥1 FAILED, brak PENDING | FAILED |
| Wszystkie SKIPPED | INVALID |

---

## 16. INTEGRACJA Z RUNTIME I SCHEDULER (KROK 3E)

**Wszystkie elementy tej sekcji należą do KROKU 3E.** Opisane jako specyfikacja docelowej integracji.

### 16.1 Tworzenie w Runtime

```python
# application/runtime.py — __init__() (KROK 3E)
from engines.outcome.engine import OutcomeComputer
from engines.outcome.calendar import TradingCalendar
from config.outcome import OutcomeConfig
from data.yahoo.yahoo_fetcher import YahooFetcher

self._outcome_computer = OutcomeComputer(
    repository=self.history_repository,
    yahoo_fetcher=YahooFetcher(),
    calendar=TradingCalendar(),
    config=OutcomeConfig(),
)
```

### 16.2 Wywołanie w `run()`

```python
# application/runtime.py — run() (KROK 3E)
def run(self):
    self._run_market_scan()
    self._run_pipeline()

    try:
        new = self._outcome_computer.initialize_new_events()
        if new: logger.info("OutcomeComputer: %s nowych EventOutcome", len(new))
    except Exception as e:
        logger.error("initialize_new_events() błąd: %s", e, exc_info=True)
        if not self.continue_on_error: raise

    try:
        updated = self._outcome_computer.compute_pending_horizons()
        if updated > 0: logger.info("OutcomeComputer: %s zaktualizowanych", updated)
    except Exception as e:
        logger.error("compute_pending_horizons() błąd: %s", e, exc_info=True)
        if not self.continue_on_error: raise
```

### 16.3 Charakterystyka

- **Synchroniczne** — `run()` czeka na zakończenie każdej metody.
- **Sekwencja**: `_run_market_scan()` → `_run_pipeline()` → `initialize_new_events()` → `compute_pending_horizons()`.
- **Częstotliwość**: co cykl Schedulera (domyślnie 60s).
- **Scheduler**: bez zmian — wywołuje tylko `RuntimeService.run()`.
- **Błąd pojedynczego tickera**: nie przerywa pętli.
- **Błąd OutcomeComputer**: nie wpływa na pipeline detekcji.

---

## 17. TRADINGCALENDAR — KALENDARZ SESJI HANDLOWYCH

### 17.1 Decyzja architektoniczna

System używa **statycznego kalendarza** opartego na oficjalnych kalendarzach GPW i NYSE.

Kalendarz zawiera wszystkie weekendy i wszystkie cykliczne święta giełdowe. Nie zawiera dni wyjątkowego zamknięcia (np. żałoba narodowa) — są one nieprzewidywalne i nie mogą być ujęte w statycznym kalendarzu. Konsekwencja: Yahoo Finance nie zwróci danych → retryable → FAILED `"no_data_for_session"` po limicie.

### 17.2 Lokalizacja i struktura danych

**Plik**: `engines/outcome/calendar.py`

**Dane przechowywane w stałej `_HOLIDAYS`**:

```python
_HOLIDAYS: dict[str, dict[int, set[str]]] = {
    "GPW": {
        2025: {"2025-01-01", "2025-01-06", "2025-04-20", "2025-04-21",
               "2025-05-01", "2025-05-03", "2025-06-19",
               "2025-08-15", "2025-11-01", "2025-11-11",
               "2025-12-25", "2025-12-26"},
        2026: {"2026-01-01", "2026-01-06", "2026-04-05", "2026-04-06",
               "2026-05-01", "2026-05-03", "2026-05-14",
               "2026-08-15", "2026-11-01", "2026-11-11",
               "2026-12-25", "2026-12-26"},
        # ... kolejne lata do 2030
    },
    "US": {
        2025: {"2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
               "2025-05-26", "2025-06-19", "2025-07-04",
               "2025-09-01", "2025-11-27", "2025-12-25"},
        2026: {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
               "2026-05-25", "2026-06-19", "2026-07-03",
               "2026-09-07", "2026-11-26", "2026-12-25"},
        # ... kolejne lata do 2030
    },
}
```

Klucz zewnętrzny: kod rynku (`"GPW"`, `"US"`). Klucz wewnętrzny: rok (2025–2030). Wartość: zbiór dat w formacie `"YYYY-MM-DD"` — daty bez handlu (święta + observed holidays).

Struktura jest **słownikiem zagnieżdżonym**. Przy starcie `TradingCalendar.__init__()` daty są parsowane do `datetime.date` i przechowywane w `self._holidays: dict[str, set[date]]`. Święta ruchome są generowane algorytmicznie i dodawane do zbioru.

### 17.3 Public API

```python
class TradingCalendar:
    SUPPORTED_MARKETS: tuple[str, ...] = ("GPW", "US")

    def __init__(self, holidays_override: Optional[dict[str, set[str]]] = None):
        """Tworzy kalendarz. holidays_override pozwala nadpisać/rozszerzyć święta."""

    def is_trading_day(self, date: date, market: str) -> bool:
        """True jeśli Pon-Pt i data nie jest świętem. ValueError dla nieobsługiwanego rynku."""

    def resolve_session_date(
        self, detection_timestamp: datetime, horizon_offset: int, market: str
    ) -> datetime:
        """Wyznacza datę horyzontu po N sesjach handlowych.
        ValueError dla nieobsługiwanego rynku.
        CalendarExpiredError jeśli wynikowa data > 2030-12-31."""

class CalendarExpiredError(Exception):
    """Data poza obsługiwanym zakresem kalendarza."""
```

### 17.4 Obsługiwane święta — GPW

Źródło: oficjalny kalendarz GPW (www.gpw.pl).

**Święta stałe** (zapisane jawnie w `_HOLIDAYS["GPW"][rok]`):

| # | Data | Nazwa | Sposób zapisu |
|---|------|-------|---------------|
| 1 | 1 stycznia | Nowy Rok | Jawna data |
| 2 | 6 stycznia | Trzech Króli | Jawna data |
| 3 | 1 maja | Święto Pracy | Jawna data |
| 4 | 3 maja | Święto Konstytucji 3 Maja | Jawna data |
| 5 | 15 sierpnia | Wniebowzięcie NMP | Jawna data |
| 6 | 1 listopada | Wszystkich Świętych | Jawna data |
| 7 | 11 listopada | Niepodległości | Jawna data |
| 8 | 25 grudnia | Boże Narodzenie (dzień 1) | Jawna data |
| 9 | 26 grudnia | Boże Narodzenie (dzień 2) | Jawna data |

**Święta ruchome** (generowane algorytmem Gaussa przy inicjalizacji):

| # | Nazwa | Algorytm |
|---|-------|----------|
| 10 | Wielkanoc | Algorytm Gaussa (działa 1900–2099) |
| 11 | Poniedziałek Wielkanocny | Wielkanoc + 1 dzień |
| 12 | Boże Ciało | Wielkanoc + 60 dni |

**Weekendy**: sobota i niedziela są zawsze dniami bez handlu. GPW nie stosuje zasady "observed holiday".

**Dni handlowe mimo krótszych sesji**: 24 grudnia (Wigilia), 31 grudnia (Sylwester). NIE są na liście świąt.

### 17.5 Obsługiwane święta — US (NYSE/NASDAQ)

Źródło: oficjalny kalendarz NYSE (www.nyse.com/markets/hours-calendars).

**Święta stałe** (zapisane jawnie):

| # | Data | Nazwa | Sposób zapisu |
|---|------|-------|---------------|
| 1 | 1 stycznia | New Year's Day | Jawna data + observed |
| 2 | Trzeci poniedziałek stycznia | MLK Day | Jawna data |
| 3 | Trzeci poniedziałek lutego | Presidents' Day | Jawna data |
| 4 | Ostatni poniedziałek maja | Memorial Day | Jawna data |
| 5 | 19 czerwca | Juneteenth | Jawna data + observed |
| 6 | 4 lipca | Independence Day | Jawna data + observed |
| 7 | Pierwszy poniedziałek września | Labor Day | Jawna data |
| 8 | Czwarty czwartek listopada | Thanksgiving | Jawna data |
| 9 | 25 grudnia | Christmas Day | Jawna data + observed |

**Święta ruchome** (generowane algorytmem Gaussa):

| # | Nazwa | Algorytm |
|---|-------|----------|
| 10 | Good Friday | Wielkanoc - 2 dni |

**Reguły observed holidays** (stosowane przy generowaniu dat dla każdego roku):
- New Year's Day (1 stycznia): sobota → piątek 31 grudnia wolny; niedziela → poniedziałek 2 stycznia wolny.
- Independence Day (4 lipca): sobota → piątek 3 lipca wolny; niedziela → poniedziałek 5 lipca wolny.
- Christmas Day (25 grudnia): sobota → piątek 24 grudnia wolny; niedziela → poniedziałek 26 grudnia wolny.
- Juneteenth (19 czerwca): sobota → piątek 18 czerwca wolny; niedziela → poniedziałek 20 czerwca wolny.

Reguła NIE dotyczy: Thanksgiving (zawsze czwartek), Good Friday (zawsze piątek), dni zawsze w poniedziałek (MLK, Presidents', Memorial, Labor). Daty observed są wyliczane przy generowaniu `_HOLIDAYS` i zapisywane jawnie jako dodatkowe daty w zbiorze.

**Dni handlowe mimo krótszych sesji**: Black Friday (dzień po Thanksgiving). NIE jest na liście świąt.

### 17.6 Obsługiwany zakres lat

Kalendarz zawiera dane dla lat **2025–2030**. `resolve_session_date()` rzuca `CalendarExpiredError`, jeśli wyznaczona data > 2030-12-31. SessionOutcome → FAILED, `"calendar_expired"`. System nie traktuje nieznanej daty jako sesji handlowej.

### 17.7 Procedura aktualizacji kalendarza

1. Przed końcem 2030 roku zespół utrzymaniowy pobiera oficjalne kalendarze GPW i NYSE na kolejne lata.
2. Dodaje wpisy do stałej `_HOLIDAYS` dla każdego nowego roku (dla GPW i US).
3. Aktualizuje górną granicę zakresu w `resolve_session_date()`.
4. Uruchamia `pytest tests/test_outcome_calendar.py` — wszystkie testy muszą przejść.
5. Zmiana jest commitowana jako aktualizacja kalendarza.

### 17.8 Weryfikacja z oficjalnymi kalendarzami

Testy `test_outcome_calendar.py` weryfikują każdą datę w `_HOLIDAYS` z oczekiwaną listą:
- Dla każdego roku 2025–2030, dla GPW i US: test sprawdza, że liczba świąt i ich daty są zgodne z oczekiwanymi.
- Testy świąt ruchomych: weryfikują algorytm Gaussa na znanych datach (Wielkanoc 2025-04-20, 2026-04-05, itd.).
- Testy observed holidays: weryfikują reguły przesunięć na konkretnych przykładach.

### 17.9 Obsługa zmian kalendarza giełdowego

Jeśli GPW lub NYSE opublikuje zmodyfikowany kalendarz (np. dodane nowe święto), zespół utrzymaniowy aktualizuje `_HOLIDAYS` zgodnie z procedurą w §17.7. Kalendarz **nie** aktualizuje się automatycznie.

### 17.10 Testy

`tests/test_outcome_calendar.py`:
- Testy `is_trading_day()`: każdy dzień 2025–2030 dla GPW i US
- Testy weekendów: sobota i niedziela zawsze False
- Testy wszystkich 12 świąt GPW (każdy rok)
- Testy wszystkich 10 świąt US + observed holidays (każdy rok)
- Testy świąt ruchomych (Wielkanoc, Poniedziałek Wielkanocny, Boże Ciało, Good Friday)
- Testy sesji skróconych: Wigilia, Sylwester, Black Friday → True
- Test `ValueError` dla nieobsługiwanego rynku
- Test `CalendarExpiredError` dla dat poza 2025–2030
- Test `resolve_session_date()`: weekendy, święta, observed holidays
- Test deterministyczności

---

## 18. MAPOWANIE RYNKÓW

### 18.1 Decyzja architektoniczna

System obsługuje **dwa kalendarze**: GPW i US. Mapowanie jest zdefiniowane w stałej `_MARKET_CALENDAR_MAP` w `engines/outcome/calendar.py`.

### 18.2 Tabela mapowania

```python
_MARKET_CALENDAR_MAP: dict[str, str] = {
    "GPW": "GPW",
    "NYSE": "US",
    "NASDAQ": "US",
    "US": "US",
}
```

| Identyfikator rynku | Kalendarz | Giełda |
|---------------------|-----------|--------|
| `"GPW"` | GPW | Giełda Papierów Wartościowych w Warszawie |
| `"NYSE"` | US | New York Stock Exchange |
| `"NASDAQ"` | US | NASDAQ |
| `"US"` | US | Domyślny rynek amerykański |

### 18.3 Sposób wyboru kalendarza

`TradingCalendar` używa mapowania:

```python
def _get_calendar_key(self, market: str) -> str:
    calendar_key = _MARKET_CALENDAR_MAP.get(market)
    if calendar_key is None:
        raise ValueError(f"Unsupported market: {market}")
    return calendar_key
```

### 18.4 Rynek nieobsługiwany

Każdy identyfikator rynku spoza mapowania → `ValueError` → OutcomeComputer ustawia SessionOutcome → SKIPPED, `"unknown_market"`. System nie używa domyślnego kalendarza dla nieobsługiwanego rynku.

### 18.5 Rynek pusty lub nieokreślony

EventOutcome jest tworzony również dla MarketEvent z pustym `market`. Wartość `market` jest kopiowana do EventOutcome bez zgadywania i bez zastępowania jej wartością `"US"`.

W `compute_pending_horizons()` OutcomeComputer normalizuje wartość przez `market.strip()`. Jeśli wynik jest pusty:

- Każde SessionOutcome otrzymuje **SKIPPED** z `skip_reason = "market_not_specified"`.
- Stan jest terminalny i non-retryable.
- **TradingCalendar nie jest wywoływany.**
- Dane pozostają audytowalne: EventOutcome istnieje, SessionOutcome istnieją, przyczyna pominięcia jest jawna.

OutcomeComputer **nie usuwa, nie ignoruje ani nie ukrywa** MarketEvent z pustym rynkiem.

### 18.6 Właściciel mapowania

Mapowanie jest własnością `TradingCalendar` i jest przechowywane jako stała modułu w `engines/outcome/calendar.py`. Konfiguracja `OutcomeConfig` nie zawiera mapowania rynków — nie jest ono konfigurowalne w v1.0. Rozszerzenie listy rynków wymaga zmiany kodu `calendar.py`.

### 18.7 Konfigurowalność w v1.0

Mapowanie rynków **nie jest konfigurowalne** przez `OutcomeConfig`. Jest stałą kodu. Rozszerzenie obsługiwanych rynków w przyszłych wersjach będzie wymagało:
1. Dodania wpisu w `_MARKET_CALENDAR_MAP`.
2. Dodania danych kalendarza w `_HOLIDAYS` dla nowego klucza.
3. Aktualizacji `SUPPORTED_MARKETS`.

---

## 19. OBSŁUGA BŁĘDÓW I BRAKUJĄCYCH DANYCH

| Wyjątek / Warunek | Źródło |
|-------------------|--------|
| `InvalidSymbolError` | `YahooFetcher.fetch_stock_data()` |
| `RateLimitExceededError` | `YahooFetcher.fetch_stock_data()` |
| `YahooFinanceError` | `YahooFetcher.fetch_stock_data()` |
| Brak `MarketData` | `_find_market_data()` → None |
| `ValueError` (nieznany rynek) | `TradingCalendar._get_calendar_key()` |
| `CalendarExpiredError` | `TradingCalendar.resolve_session_date()` |
| `base_price` = None | EventOutcome |
| `base_volume` = None | EventOutcome |
| `DataIntegrityError` | repo — `get_event_outcome_by_id()` → None |

---

## 20. KLASYFIKACJA BŁĘDÓW — RETRYABLE I NON-RETRYABLE

### 20.1 Retryable (ponawiane `max_retry_attempts` razy)

| Błąd | Wyjątek | Stan po limicie | `failure_reason` |
|------|---------|----------------|-----------------|
| Limit API | `RateLimitExceededError` | FAILED | `rate_limit_exceeded` |
| Tymczasowy błąd API | `YahooFinanceError` | FAILED | `yahoo_api_error` |
| Brak danych dla sesji | `_find_market_data()` → None | FAILED | `no_data_for_session` |

### 20.2 Non-retryable — FAILED (natychmiast terminalne)

| Błąd | Wyjątek | `failure_reason` |
|------|---------|-----------------|
| Kalendarz poza zakresem | `CalendarExpiredError` | `calendar_expired` |
| Brak obu danych bazowych | `base_price == None` i `base_volume == None` | `base_price_unavailable` |

### 20.3 Non-retryable — SKIPPED (natychmiast terminalne)

| Błąd | Wyjątek | `skip_reason` |
|------|---------|---------------|
| Instrument wycofany | `InvalidSymbolError` | `instrument_delisted` |
| Pusty lub nieokreślony rynek | Walidacja przed TradingCalendar | `market_not_specified` |
| Nieobsługiwany rynek | `ValueError` | `unknown_market` |

### 20.4 Błędy integralności

| Błąd | Wyjątek | Zachowanie |
|------|---------|------------|
| Osierocony SessionOutcome | `DataIntegrityError` | Log ERROR, pomiń, kontynuuj. NIE zmienia stanu. |

---

## 21. MAPOWANIE BŁĘDÓW NA STANY FAILED I SKIPPED

Definicje z zamrożonych modeli:
- **FAILED**: *"Nie udało się obliczyć metryk z przyczyn technicznych."* (MODEL_SESSIONOUTCOME.md)
- **SKIPPED**: *"Obliczenie nie zostanie wykonane z przyczyn domenowych."* (MODEL_SESSIONOUTCOME.md)

| Błąd | Stan | Uzasadnienie |
|------|------|-------------|
| `rate_limit_exceeded` | FAILED | Techniczny błąd API |
| `yahoo_api_error` | FAILED | Techniczny błąd API |
| `no_data_for_session` | FAILED | Techniczny brak danych |
| `calendar_expired` | FAILED | Techniczna niemożność wyznaczenia daty |
| `base_price_unavailable` | FAILED | Techniczny brak danych wejściowych |
| `instrument_delisted` | SKIPPED | Przyczyna domenowa |
| `market_not_specified` | SKIPPED | Przyczyna domenowa — brak danych wejściowych uniemożliwia wybór kalendarza |
| `unknown_market` | SKIPPED | Przyczyna domenowa |

**Wpływ na EventOutcome:**
- CALCULATED + SKIPPED, brak FAILED, brak PENDING → COMPLETE
- ≥1 FAILED, brak PENDING → FAILED
- Wszystkie SKIPPED → INVALID

---

## 22. INTEGRALNOŚĆ EVENTOUTCOME–SESSIONOUTCOME

- SessionOutcome nie może istnieć bez EventOutcome (N2, N3 z MODEL_SESSIONOUTCOME.md).
- Usunięcie EventOutcome z powiązanymi sesjami jest **zabronione** (`ON DELETE RESTRICT`).
- Cascade delete **nie jest stosowane**.
- Naruszenie integralności: `DataIntegrityError`, log ERROR, pominięcie rekordu, kontynuacja pętli. NIE zmienia stanu SessionOutcome na FAILED.

---

## 23. OBSŁUGA ŚWIĄT GIEŁDOWYCH

Horyzonty liczone w sesjach handlowych. `TradingCalendar.resolve_session_date()` pomija soboty, niedziele i święta z `_HOLIDAYS`. Szczegóły — §17.

---

## 24. OBSŁUGA WYCOFANYCH I ZAWIESZONYCH INSTRUMENTÓW

- **Wycofanie**: `InvalidSymbolError` → SKIPPED `"instrument_delisted"`. Wszystkie PENDING dla tego samego tickera → SKIPPED.
- **Zawieszenie** (v1.0): `InvalidSymbolError` → SKIPPED `"instrument_delisted"`.

---

## 25. STRATEGIA PONAWIANIA

- Dotyczy tylko błędów retryable (§20.1).
- `attempt_count += 1` przy każdej nieudanej próbie.
- `attempt_count >= max_retry_attempts` → FAILED.
- Non-retryable → natychmiastowy stan terminalny.
- Interwał: naturalny — każdy cykl (KROK 3E: RuntimeScheduler, domyślnie 60s).

---

## 26. PRZYPADKI BRZEGOWE

| # | Scenariusz | Zachowanie |
|---|-----------|------------|
| 1 | Horyzont nieupłynięty | PENDING, `attempt_count` bez zmian |
| 2 | Brak danych po sesji | Retryable → FAILED po limicie |
| 3 | Instrument wycofany częściowo | Pozostałe PENDING → SKIPPED; EventOutcome → COMPLETE |
| 4 | `base_price` = None, wolumen OK | CALCULATED, `price_change_pct=None` |
| 5 | `base_volume` = None, cena OK | CALCULATED, `volume_change_pct=None` |
| 6 | Split/dywidenda | Adjusted close z Yahoo Finance |
| 7 | Horyzont w święto | `resolve_session_date()` przesuwa |
| 8 | Zduplikowana inicjalizacja | Idempotentne |
| 9 | Nieobsługiwany rynek | SKIPPED (non-retryable) |
| 10 | Data poza 2030 | FAILED `calendar_expired` (non-retryable) |
| 11 | Osierocony SessionOutcome | `DataIntegrityError`, pominięcie |
| 12 | Wszystkie SKIPPED | EventOutcome → INVALID |
| 13 | Wyjątkowe zamknięcie giełdy | Kalendarz zwraca True → brak danych → retryable → FAILED |

---

## 27. NIEZMIENNIKI

| # | Niezmiennik | Źródło |
|---|------------|--------|
| N1 | 1 MarketEvent : 1 EventOutcome | MODEL_EVENTOUTCOME.md N1 |
| N2 | 1 EventOutcome : 1 SessionOutcome na horyzont | MODEL_SESSIONOUTCOME.md N1 |
| N3 | OutcomeComputer nie interpretuje | FILOZOFIA_EVENTOUTCOME.md N3 |
| N4 | Metryki zamrożone po CALCULATED | MODEL_SESSIONOUTCOME.md N7 |
| N5 | FAILED/SKIPPED muszą mieć przyczynę | MODEL_SESSIONOUTCOME.md N8 |
| N6 | Cykl życia EventOutcome niezależny | MODEL_EVENTOUTCOME.md N13 |
| N7 | Rozszerzenia addytywne | FILOZOFIA_EVENTOUTCOME.md N6 |
| N8 | Idempotentność obliczeń | MODEL_EVENTOUTCOME.md N11 |
| N9 | Best-effort | §8.2 |
| N10 | Jedno źródło prawdy | MODEL_EVENTOUTCOME.md N10 |
| N11 | EventOutcome właścicielem SessionOutcome | MODEL_SESSIONOUTCOME.md N2, N3 |
| N12 | Walidacja rynku przed TradingCalendar — pusty rynek → SKIPPED `"market_not_specified"`, nieobsługiwany rynek → SKIPPED `"unknown_market"`, w obu przypadkach brak retry, TradingCalendar nie jest wywoływany, EventOutcome i SessionOutcome pozostają audytowalnym śladem | §8.2 krok b, §20.3 |
| N13 | Nieznana data → CalendarExpiredError | §17.6 |
| N14 | Osierocony → DataIntegrityError, nie FAILED | §22 |

---

## 28. KONFIGURACJA

`config/outcome.py`:

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class OutcomeConfig:
    horizons: Tuple[str, ...] = ("+1", "+2", "+3", "+5")
    max_retry_attempts: int = 5
    fetch_timeout_seconds: int = 30
    rule_version: str = "1.0.0"
```

---

## 29. CZEGO OUTCOMECOMPUTER NIE WYKONUJE

1. NIE wykrywa zdarzeń
2. NIE ocenia jakości (`QualityEngine`)
3. NIE decyduje o pipeline (`DecisionEngine`)
4. NIE analizuje sentymentu/fundamentalnych/technicznych
5. NIE interpretuje wyników
6. NIE wydaje rekomendacji
7. NIE ocenia ryzyka (`RiskEngine`)
8. NIE rankinguje (`RankingEngine`)
9. NIE wysyła alertów
10. NIE archiwizuje MarketEvent
11. NIE implementuje fetchera (używa `YahooFetcher`)
12. NIE implementuje persistencji (KROK 3E)
13. NIE integruje się z Runtime (KROK 3E)
14. NIE używa wątków/asyncio
15. NIE modyfikuje MarketEvent
16. NIE modyfikuje istniejących silników
17. NIE używa zewnętrznego API kalendarza
18. NIE przelicza terminalnych stanów (v1.0)
19. NIE naprawia naruszonej integralności

---

## 30. DECYZJE ARCHITEKTONICZNE — WSZYSTKIE ZAMKNIĘTE

Wszystkie decyzje architektoniczne dla KROKU 3D zostały rozstrzygnięte. Dokument nie zawiera otwartych decyzji.

| # | Decyzja | Rozstrzygnięcie | Sekcja |
|---|---------|----------------|--------|
| 1 | Cel komponentu | Obliczanie rezultatów zdarzeń dla horyzontów +1, +2, +3, +5 | §1 |
| 2 | Miejsce w architekturze | `engines/outcome/engine.py`, wywoływany przez Runtime (KROK 3E) | §2 |
| 3 | Podział KROK 3D / 3E | 3D = logika + testy. 3E = Runtime + SQLiteHistoryRepository | §6 |
| 4 | Kontrakt repozytorium | Duck typing — 9 metod | §7 |
| 5 | Kolejność przetwarzania | Alfabetycznie po `event_id` (inicjalizacja); po `event_outcome_id`, `horizon_id` (obliczenia) | §8 |
| 6 | Limity rekordów na cykl | Brak | §9 |
| 7 | Struktura katalogowa | `engines/outcome/` z `engine.py` i `calendar.py` | §10 |
| 8 | Walidacja MarketEvent | `ticker` niepusty, `timestamp_utc` nie-None; `market` kopiowane bez zmian, walidowane później w `compute_pending_horizons()` | §8.2 krok b, §12 |
| 9 | Własność SessionOutcome | EventOutcome jest jedynym właścicielem | §13 |
| 10 | Wzory metryk | `price_change_pct = (close - base_price) / base_price * 100` | §14 |
| 11 | Użycie adjusted close | Tak — YahooFetcher zwraca adjusted close | §14 |
| 12 | Stany SessionOutcome | PENDING → CALCULATED / FAILED / SKIPPED (terminalne w v1.0) | §15 |
| 13 | Stany EventOutcome | PENDING, PARTIAL, COMPLETE, FAILED, INVALID | §15 |
| 14 | Reguły stanu EventOutcome | Wszystkie PENDING → PENDING; mieszanka → PARTIAL; terminalne bez FAILED z ≥1 CALCULATED → COMPLETE; ≥1 FAILED → FAILED; wszystkie SKIPPED → INVALID | §15 |
| 15 | Integracja z Runtime | KROK 3E: synchronicznie, sekwencyjnie, po `_run_pipeline()` | §16 |
| 16 | Scheduler | Bez zmian — wywołuje tylko `RuntimeService.run()` | §16 |
| 17 | Obsługa błędów w Runtime | `continue_on_error`: True → log + kontynuacja; False → przerwanie | §16 |
| 18 | Kalendarz — typ | Statyczny, wewnętrzny | §17.1 |
| 19 | Kalendarz — zakres lat | 2025–2030. Poza → `CalendarExpiredError` → FAILED | §17.6 |
| 20 | Kalendarz — święta GPW | 9 stałych + 3 ruchome (jawne w §17.4) | §17.4 |
| 21 | Kalendarz — święta US | 9 stałych + 1 ruchome + observed holidays (jawne w §17.5) | §17.5 |
| 22 | Kalendarz — struktura danych | `dict[str, dict[int, set[str]]]` w stałej `_HOLIDAYS` | §17.2 |
| 23 | Kalendarz — aktualizacja | Ręczna, przed końcem 2030, z testami | §17.7 |
| 24 | Kalendarz — weryfikacja | Testy pokrywające wszystkie daty 2025–2030 | §17.8, §17.10 |
| 25 | Kalendarz — sesje skrócone | Traktowane jako dni handlowe (True) | §17.4, §17.5 |
| 26 | Kalendarz — wyjątkowe zamknięcia | Nieobsługiwane → retryable → FAILED `"no_data_for_session"` | §17.1 |
| 27 | Mapowanie rynków | Stała `_MARKET_CALENDAR_MAP`: GPW→GPW, NYSE/NASDAQ/US→US | §18.2 |
| 28 | Rynek nieobsługiwany | `ValueError` → SKIPPED `"unknown_market"` | §18.4 |
| 29 | Rynek nieokreślony | Pusty → SKIPPED `"market_not_specified"`, TradingCalendar nie jest wywoływany | §18.5 |
| 30 | Konfigurowalność mapowania | Nie jest konfigurowalne w v1.0 | §18.6 |
| 31 | Retryable błędy | `RateLimitExceededError`, `YahooFinanceError`, brak danych | §20.1 |
| 32 | Non-retryable FAILED | `CalendarExpiredError`, brak obu danych bazowych | §20.2 |
| 33 | Non-retryable SKIPPED | `InvalidSymbolError`, pusty rynek (`market_not_specified`), nieznany rynek (`unknown_market`) | §20.3 |
| 34 | Mapowanie na FAILED/SKIPPED | FAILED = techniczne, SKIPPED = domenowe | §21 |
| 35 | Wpływ na EventOutcome | COMPLETE / FAILED / INVALID wg reguł | §21 |
| 36 | Usuwanie EventOutcome | Zabronione (`ON DELETE RESTRICT`) | §22 |
| 37 | Cascade delete | Nie stosowane | §22 |
| 38 | Osierocony SessionOutcome | `DataIntegrityError`, nie FAILED | §22 |
| 39 | Obsługa wycofanych | `InvalidSymbolError` → SKIPPED dla wszystkich PENDING tickera | §24 |
| 40 | Limit ponowień | `max_retry_attempts = 5` | §25 |
| 41 | Horyzonty | `"+1"`, `"+2"`, `"+3"`, `"+5"` | §28 |
| 42 | Wersja reguł | `"1.0.0"` | §28 |

---

## KONIEC DOKUMENTU

Data utworzenia: 30.07.2026
Wersja: 1.4
Status: Dokument projektowy — WERSJA OSTATECZNA. Wszystkie decyzje architektoniczne zamknięte.

Dokumenty powiązane:
- `docs/FILOZOFIA_EVENTOUTCOME.md`
- `docs/MODEL_EVENTOUTCOME.md`
- `docs/MODEL_SESSIONOUTCOME.md`
- `docs/FILOZOFIA_ALCHEMIKA.md`
- `docs/Kontrakt_Zdarzen_Rynkowych.md`
- `ALCHEMIK_PROJEKT.md`