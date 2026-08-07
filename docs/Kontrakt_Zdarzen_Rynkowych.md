# ALCHEMIK — KONTRAKT ZDARZEŃ RYNKOWYCH

## DOKUMENT PROJEKTOWY — STANDARD WYMIANY DANYCH

Data: 18.07.2026
Wersja: 1.0
Status: Dokument projektowy — specyfikacja kontraktu

---

## SPIS TREŚCI

1. [Model zdarzenia rynkowego](#1-model-zdarzenia-rynkowego)
2. [Cykl życia zdarzenia](#2-cykl-życia-zdarzenia)
3. [Odpowiedzialność modułów](#3-odpowiedzialność-modułów)
4. [Niezmienniki](#4-niezmienniki)
5. [Historia zdarzenia](#5-historia-zdarzenia)
6. [Wersjonowanie](#6-wersjonowanie)
7. [Diagram ASCII — przepływ zdarzenia przez system](#7-diagram-ascii--przepływ-zdarzenia-przez-system)
8. [Ocena końcowa](#8-ocena-końcowa)

---

## 1. MODEL ZDARZENIA RYNKOWEGO

### 1.1 Definicja obiektu `MarketEvent`

Pojedyncze zdarzenie rynkowe jest reprezentowane przez wspólny obiekt przesyłany pomiędzy wszystkimi modułami systemu ALCHEMIK. Obiekt ten jest jedynym nośnikiem informacji o zdarzeniu — każdy moduł czyta z niego i zapisuje do niego wyłącznie w ramach swojej odpowiedzialności.

### 1.2 Tabela pól

| Lp. | Pole | Znaczenie | Typ danych | Wymagane | Uzupełnia |
|-----|------|-----------|------------|----------|-----------|
| 1 | `event_id` | Unikalny, niezmienny identyfikator zdarzenia generowany w momencie utworzenia. Służy jako klucz główny we wszystkich operacjach (deduplikacja, historia, logowanie). | `string` (UUID v4) | **TAK** | Detektor (w momencie wykrycia) |
| 2 | `timestamp_utc` | Znacznik czasu wykrycia zdarzenia w UTC. Reprezentuje moment, w którym detektor zarejestrował zdarzenie (nie moment wystąpienia zjawiska rynkowego). | `datetime` (ISO 8601, UTC) | **TAK** | Detektor |
| 3 | `ticker` | Symbol instrumentu finansowego, którego dotyczy zdarzenie. Format zgodny z Yahoo Finance (np. `PKN.ORLEN.WA`, `AAPL`, `SPY`). Pole niezmienne po ustawieniu. | `string` | **TAK** | MarketScanner / HunterEngine |
| 4 | `market` | Rynek notowań instrumentu. Określa giełdę lub platformę obrotu. | `string` (np. `"GPW"`, `"NYSE"`, `"NASDAQ"`, `"AMEX"`, `"LSE"`, `"XETRA"`) | **TAK** | MarketScanner / HunterEngine (na podstawie danych Yahoo Finance) |
| 5 | `instrument_type` | Typ instrumentu finansowego. Deterministycznie określa, które detektory są uruchamiane i jakie progi są stosowane. | `enum`: `STOCK_GPW`, `STOCK_USA`, `ETF` | **TAK** | MarketScanner / HunterEngine (na podstawie klasyfikacji) |
| 6 | `event_family` | Rodzina zdarzeń — najwyższy poziom klasyfikacji logicznej. Odpowiada nazwie detektora odpowiedzialnego za wykrycie. | `enum`: `PRICE`, `VOLUME`, `TECHNICAL`, `FUNDAMENTAL`, `CORPORATE`, `REGULATORY`, `MACRO`, `ETF`, `DERIVATIVES`, `SENTIMENT`, `SYSTEM` | **TAK** | Detektor |
| 7 | `event_category` | Kategoria zdarzenia — podgrupa w ramach rodziny. Umożliwia grupowanie pokrewnych typów zdarzeń. | `string` (np. `"Cenowe"`, `"Wolumenowe"`, `"Formacje świecowe"`, `"Trend"`, `"Momentum"`, `"Insider Trading"`, `"Fuzje i przejęcia"`) | **TAK** | Detektor |
| 8 | `event_subcategory` | Podkategoria — drobniejszy podział wewnątrz kategorii. Opcjonalny, używany gdy kategoria zawiera logicznie odrębne grupy. | `string` lub `null` (np. `"Luki"`, `"Świece pojedyncze"`, `"Świece podwójne"`) | NIE | Detektor |
| 9 | `event_type` | Konkretny typ zdarzenia — najdokładniejszy identyfikator. Odpowiada jednoznacznie jednemu zdarzeniu z Katalogu Zdarzeń Rynkowych. | `string` (np. `"PRICE_SURGE"`, `"VOLUME_SPIKE"`, `"RSI_OVERSOLD"`, `"EARNINGS_RELEASE"`, `"M_AND_A_ANNOUNCEMENT"`) | **TAK** | Detektor |
| 10 | `priority_raw` | Surowy priorytet zdarzenia — stała wartość zdefiniowana w Katalogu Zdarzeń Rynkowych. Nie zmienia się podczas przechodzenia przez system. | `enum`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | **TAK** | Detektor (na podstawie Katalogu) |
| 11 | `priority_final` | Końcowy priorytet zdarzenia po uwzględnieniu kontekstu (grupa instrumentu, liczba zdarzeń składowych, powtarzalność). Obliczany na etapie scalania. | `enum`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `IGNORE` | **TAK** | Etap scalania (MasterEngine / dedykowany komponent) |
| 12 | `confidence_level` | Poziom pewności detekcji — liczbowa ocena wiarygodności zdarzenia (0.0–1.0). Wyższa wartość oznacza większą pewność, że zdarzenie nie jest fałszywym sygnałem. | `float` (0.0–1.0) | **TAK** | Detektor (wstępna) → Etap oceny jakości (ostateczna) |
| 13 | `detection_source` | Źródło wykrycia — nazwa detektora, który jako pierwszy wykrył zdarzenie. **Pole niezmienne po ustawieniu.** | `string` (np. `"Price Event Detector"`, `"Volume Event Detector"`, `"Corporate Event Detector"`) | **TAK** | Detektor |
| 14 | `event_owner` | Właściciel zdarzenia — silnik ALCHEMIKA odpowiedzialny za wykrycie i wstępną analizę. | `enum`: `TechnicalEngine`, `AnalystEngine`, `NewsEngine`, `AIEngine`, `Multi-Engine` | **TAK** | Detektor (na podstawie mapowania rodzin) |
| 15 | `price_data` | Dane cenowe związane ze zdarzeniem. Zawiera wartości OHLCV z bieżącej i poprzednich świec istotnych dla zdarzenia. | `object` (struktura z polami: `open`, `high`, `low`, `close`, `prev_close`, `change_pct`, `change_abs`) | NIE (wymagane dla rodzin PRICE, VOLUME, TECHNICAL) | TechnicalEngine |
| 16 | `volume_data` | Dane wolumenowe związane ze zdarzeniem. Zawiera wolumen bieżący, średni oraz krotność odchylenia. | `object` (struktura z polami: `current_volume`, `avg_volume`, `volume_ratio`, `direction`) | NIE (wymagane dla rodziny VOLUME) | TechnicalEngine |
| 17 | `technical_context` | Kontekst techniczny — wartości wskaźników technicznych w momencie wykrycia zdarzenia. | `object` (mapa nazwa_wskaźnika → wartość, np. `{"RSI": 28.5, "MACD_line": -0.32, "BB_upper": 105.2}`) | NIE (wymagane dla rodziny TECHNICAL) | TechnicalEngine |
| 18 | `fundamental_context` | Kontekst fundamentalny — wartości wskaźników fundamentalnych w momencie wykrycia zdarzenia. | `object` (mapa nazwa_wskaźnika → wartość, np. `{"PE_ratio": 12.5, "market_cap": 1.2e9, "revenue": 5e8}`) | NIE (wymagane dla rodziny FUNDAMENTAL) | AnalystEngine |
| 19 | `news_context` | Kontekst informacyjny — lista newsów powiązanych ze zdarzeniem. Każdy news zawiera nagłówek, źródło, timestamp i fragment treści. | `array[NewsItem]` (lista obiektów z polami: `headline`, `source`, `url`, `published_at`, `snippet`) | NIE | NewsEngine |
| 20 | `ai_context` | Kontekst AI — wynik analizy AI, jeśli została uruchomiona. Zawiera interpretację, sentyment i rekomendację wygenerowaną przez AI. | `object` (struktura z polami: `summary`, `sentiment`, `key_points`, `risk_assessment`, `ai_model`, `ai_timestamp`) | NIE | AIEngine / DecisionEngine |
| 21 | `tavily_context` | Kontekst Tavily — wyniki wyszukiwania Tavily, jeśli zostało uruchomione. | `object` (struktura z polami: `query`, `results_count`, `top_results`, `sentiment`) | NIE | Tavily (poprzez data/tavily) |
| 22 | `metadata` | Metadane — dodatkowe informacje techniczne i operacyjne. | `object` (mapa klucz → wartość, dowolny typ) | NIE | Każdy moduł (dodaje własne wpisy) |
| 23 | `composite_events` | Lista identyfikatorów zdarzeń składowych, jeśli to zdarzenie jest zdarzeniem złożonym (Composite Event). Puste dla zdarzeń prostych. | `array[string]` (lista `event_id`) | NIE | Etap scalania |
| 24 | `is_composite` | Flaga wskazująca, czy zdarzenie jest zdarzeniem złożonym (agregacją kilku zdarzeń prostych). | `boolean` | **TAK** | Etap scalania |
| 25 | `quality_level` | Poziom jakości zdarzenia — końcowa ocena istotności po przejściu przez etap oceny jakości. Określa dalsze traktowanie zdarzenia. | `enum`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `IGNORE` | **TAK** | Etap oceny jakości |
| 26 | `history` | Historia zmian zdarzenia — chronologiczna lista wpisów opisujących każdą modyfikację obiektu. | `array[HistoryEntry]` (lista obiektów: `timestamp`, `module`, `action`, `field_changes`) | **TAK** | Każdy moduł (dopisuje wpis przy modyfikacji) |
| 27 | `schema_version` | Wersja schematu kontraktu danych — umożliwia obsługę wielu wersji obiektu w systemie. | `string` (np. `"1.0"`, `"1.1"`, `"2.0"`) | **TAK** | Detektor (ustawia na aktualną wersję w momencie utworzenia) |

### 1.3 Podsumowanie pól

| Kategoria pól | Liczba pól | Pola zawsze wymagane |
|---------------|:----------:|----------------------|
| Identyfikacja i klasyfikacja | 9 (1–9) | 8 (wszystkie oprócz event_subcategory) |
| Priorytet i pewność | 3 (10–12) | 3 |
| Źródło i własność | 2 (13–14) | 2 |
| Dane kontekstowe | 8 (15–22) | 0 (wymagane warunkowo w zależności od rodziny) |
| Agregacja | 2 (23–24) | 1 (is_composite) |
| Jakość i historia | 2 (25–26) | 2 |
| Wersjonowanie | 1 (27) | 1 |
| **RAZEM** | **27** | **17 zawsze + warunkowo** |

---

## 2. CYKL ŻYCIA ZDARZENIA

### 2.1 Etapy przetwarzania

Obiekt zdarzenia przechodzi przez następujące etapy, na każdym z nich jest wzbogacany o nowe dane lub modyfikowany w ramach odpowiedzialności danego modułu.

### 2.2 Szczegółowy opis etapów

```
ETAP 1: UTWORZENIE (MarketScanner / HunterEngine)
├── Dodawane pola:
│   ├── event_id          ← generowany UUID v4
│   ├── timestamp_utc     ← datetime.utcnow()
│   ├── ticker            ← z danych wejściowych
│   ├── market            ← na podstawie danych Yahoo Finance
│   ├── instrument_type   ← klasyfikacja GPW/USA/ETF
│   └── schema_version    ← aktualna wersja kontraktu
├── Modyfikowane pola:
│   └── history           ← wpis: "Utworzenie zdarzenia"
└── Pola niezmienne:
    └── (brak — to jest początek życia obiektu)

        │
        ▼

ETAP 2: DETEKCJA (Detektory w ramach silników)
├── Dodawane pola:
│   ├── event_family      ← rodzina (PRICE/VOLUME/TECHNICAL/...)
│   ├── event_category    ← kategoria
│   ├── event_subcategory ← podkategoria (opcjonalnie)
│   ├── event_type        ← konkretny typ (np. PRICE_SURGE)
│   ├── priority_raw      ← priorytet z Katalogu
│   ├── confidence_level  ← wstępna ocena pewności (0.0–1.0)
│   ├── detection_source  ← nazwa detektora
│   ├── event_owner       ← właściciel (silnik)
│   └── (kontekst)        ← price_data / volume_data / technical_context /
│                           fundamental_context — w zależności od rodziny
├── Modyfikowane pola:
│   ├── confidence_level  ← może być skorygowane przez detektor
│   └── history           ← wpis: "Wykrycie zdarzenia przez [detektor]"
└── Pola niezmienne:
    ├── event_id
    ├── timestamp_utc (pierwotny — nie zmienia się; czas detekcji może być
    │                  zapisany w metadata)
    ├── ticker
    ├── market
    └── instrument_type

        │
        ▼

ETAP 3: NORMALIZACJA (Etap scalania — MasterEngine / komponent scalający)
├── Dodawane pola:
│   ├── is_composite      ← true/false
│   └── composite_events  ← lista event_id (jeśli złożone)
├── Modyfikowane pola:
│   ├── priority_final    ← obliczony z priority_raw + kontekst
│   ├── confidence_level  ← może być uśredniony dla Composite Events
│   └── history           ← wpis: "Normalizacja i scalanie"
└── Pola niezmienne:
    ├── event_id
    ├── ticker
    ├── market
    ├── instrument_type
    ├── detection_source
    ├── event_owner
    └── priority_raw

        │
        ▼

ETAP 4: DEDUPLIKACJA (OpportunityDeduplicator)
├── Dodawane pola:
│   └── metadata.dedup_hash       ← hash deduplikacyjny
├── Modyfikowane pola:
│   ├── quality_level    ← może być ustawione na IGNORE dla duplikatów
│   └── history          ← wpis: "Deduplikacja — [unikalny / duplikat — pominięto]"
└── Pola niezmienne:
    └── (wszystkie pozostałe)

    UWAGA: Jeśli zdarzenie jest duplikatem, dalsze przetwarzanie jest PRZERYWANE.
           Obiekt NIE jest niszczony — trafia do historii ze statusem IGNORE.

        │
        ▼

ETAP 5: OCENA JAKOŚCI (Etap oceny jakości)
├── Dodawane pola:
│   └── (brak nowych pól obiektowych — dane pomocnicze w metadata)
├── Modyfikowane pola:
│   ├── quality_level    ← ostateczna ocena: CRITICAL / HIGH / MEDIUM / LOW / IGNORE
│   ├── confidence_level ← może być skorygowany
│   ├── priority_final   ← może być skorygowany
│   └── history          ← wpis: "Ocena jakości — poziom: [X]"
└── Pola niezmienne:
    ├── event_id
    ├── ticker
    ├── detection_source
    ├── event_owner
    └── priority_raw

        │
        ▼

    ┌── quality_level == IGNORE ──→ PRZERWANIE (zapis do historii)
    │
    ▼ (CONTINUE)

ETAP 6: NEWS ENGINE (NewsPipeline)
├── Dodawane pola:
│   └── news_context     ← lista powiązanych newsów
├── Modyfikowane pola:
│   ├── metadata         ← dodane meta-dane o źródłach newsów
│   └── history          ← wpis: "Pobranie newsów — [N] znalezionych"
└── Pola niezmienne:
    ├── event_id
    ├── quality_level
    ├── priority_raw
    ├── priority_final
    ├── detection_source
    └── event_owner

        │
        ▼

    ┌── quality_level ∈ {LOW, MEDIUM} ──→ POMINIĘCIE Tavily i AI
    │
    ▼ (quality_level ∈ {CRITICAL, HIGH})

ETAP 7: TAVILY (data/tavily)
├── Dodawane pola:
│   └── tavily_context   ← wyniki wyszukiwania
├── Modyfikowane pola:
│   ├── metadata         ← meta-dane o zapytaniu Tavily
│   └── history          ← wpis: "Wyszukiwanie Tavily — [N] wyników"
└── Pola niezmienne:
    ├── event_id
    ├── quality_level
    ├── priority_raw
    ├── detection_source
    └── event_owner

        │
        ▼

ETAP 8: MASTERENGINE — ORKIESTRACJA
├── Dodawane pola:
│   └── (brak — MasterEngine koordynuje, nie wzbogaca bezpośrednio)
├── Modyfikowane pola:
│   ├── metadata         ← dodane informacje o przebiegu orkiestracji
│   └── history          ← wpis: "MasterEngine — analiza zlecona"
└── Pola niezmienne:
    └── (wszystkie dane analityczne)

        │
        ▼

ETAP 9: DECISIONENGINE — DECYZJA O AI
├── Dodawane pola:
│   └── ai_context       ← wynik analizy AI (jeśli uruchomiona)
├── Modyfikowane pola:
│   ├── metadata         ← flaga: ai_triggered = true/false
│   └── history          ← wpis: "DecisionEngine — AI [uruchomiona / pominięta]"
└── Pola niezmienne:
    ├── event_id
    ├── ticker
    ├── detection_source
    ├── event_owner
    └── priority_raw

        │
        ▼

ETAP 10: RISKENGINE — OCENA RYZYKA
├── Dodawane pola:
│   └── (brak — RiskEngine nie modyfikuje zdarzenia; tworzy RiskResult)
├── Modyfikowane pola:
│   ├── metadata.risk_assessment  ← wskaźnik ryzyka
│   └── history                  ← wpis: "RiskEngine — ocena ryzyka: [risk_level]"
└── Pola niezmienne:
    └── (wszystkie dane zdarzenia)

        │
        ▼

ETAP 11: DECYZJA O ALERCIE (AlertBuilder)
├── Dodawane pola:
│   └── metadata.alert_decision  ← true/false + powód
├── Modyfikowane pola:
│   └── history          ← wpis: "AlertBuilder — alert [wysłany / niewysłany]: [powód]"
└── Pola niezmienne:
    └── (wszystkie dane zdarzenia i analizy)

        │
        ▼

    ┌── alert NIE wysłany ──→ tylko zapis do historii
    │
    ▼ (alert wysłany)

ETAP 12: WYSYŁKA ALERTU (AlertDispatcher → TelegramChannel)
├── Dodawane pola:
│   └── metadata.telegram_message_id  ← ID wiadomości Telegram
├── Modyfikowane pola:
│   └── history          ← wpis: "Telegram — alert wysłany [message_id]"
└── Pola niezmienne:
    └── (wszystkie dane zdarzenia)

        │
        ▼

ETAP 13: ARCHIWIZACJA (HistoryRepository)
├── Dodawane pola:
│   └── metadata.archived_at  ← timestamp archiwizacji
├── Modyfikowane pola:
│   └── history          ← wpis: "Archiwizacja — zapisano w repozytorium"
└── Pola niezmienne:
    └── (wszystkie pola — obiekt zostaje zamrożony)
```

### 2.3 Tabela podsumowująca cykl życia

| Etap | Moduł | Pola dodawane | Pola modyfikowane | Pola niezmienne |
|------|-------|---------------|-------------------|-----------------|
| 1. Utworzenie | MarketScanner / HunterEngine | `event_id`, `timestamp_utc`, `ticker`, `market`, `instrument_type`, `schema_version` | `history` | — |
| 2. Detekcja | Detektory | `event_family`, `event_category`, `event_subcategory`, `event_type`, `priority_raw`, `confidence_level`, `detection_source`, `event_owner`, kontekst (price/volume/technical/fundamental) | `confidence_level`, `history` | `event_id`, `timestamp_utc`, `ticker`, `market`, `instrument_type` |
| 3. Normalizacja | Etap scalania | `is_composite`, `composite_events` | `priority_final`, `confidence_level`, `history` | `event_id`, `ticker`, `market`, `instrument_type`, `detection_source`, `event_owner`, `priority_raw` |
| 4. Deduplikacja | OpportunityDeduplicator | `metadata.dedup_hash` | `quality_level`, `history` | wszystkie pozostałe |
| 5. Ocena jakości | Etap oceny jakości | — | `quality_level`, `confidence_level`, `priority_final`, `history` | `event_id`, `ticker`, `detection_source`, `event_owner`, `priority_raw` |
| 6. News | NewsPipeline | `news_context` | `metadata`, `history` | `event_id`, `quality_level`, `priority_raw`, `priority_final`, `detection_source`, `event_owner` |
| 7. Tavily | data/tavily | `tavily_context` | `metadata`, `history` | `event_id`, `quality_level`, `priority_raw`, `detection_source`, `event_owner` |
| 8. Orkiestracja | MasterEngine | — | `metadata`, `history` | wszystkie dane analityczne |
| 9. AI | DecisionEngine | `ai_context` | `metadata`, `history` | `event_id`, `ticker`, `detection_source`, `event_owner`, `priority_raw` |
| 10. Ryzyko | RiskEngine | — | `metadata.risk_assessment`, `history` | wszystkie dane zdarzenia |
| 11. Decyzja alertu | AlertBuilder | `metadata.alert_decision` | `history` | wszystkie dane zdarzenia i analizy |
| 12. Wysyłka | AlertDispatcher / Telegram | `metadata.telegram_message_id` | `history` | wszystkie dane zdarzenia |
| 13. Archiwizacja | HistoryRepository | `metadata.archived_at` | `history` | wszystkie pola (obiekt zamrożony) |

---

## 3. ODPOWIEDZIALNOŚĆ MODUŁÓW

### 3.1 MarketScanner / HunterEngine

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Surową listę instrumentów (z konfiguracji, skanera rynku lub danych statycznych) |
| **Może zmienić** | Nic — tworzy nowy obiekt `MarketEvent` |
| **Nie może zmieniać** | Nie dotyczy (jest twórcą obiektu) |
| **Przekazuje dalej** | Obiekt `MarketEvent` z polami: `event_id`, `timestamp_utc`, `ticker`, `market`, `instrument_type`, `schema_version`, `history[0]` |

### 3.2 Detektory (Price, Volume, Technical, Fundamental, Corporate, Regulatory, Macro, ETF, Derivatives, Sentiment, System)

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` po utworzeniu (krok 1) + dane źródłowe (OHLCV, dane fundamentalne, newsy — zależnie od detektora) |
| **Może zmienić** | `event_family`, `event_category`, `event_subcategory`, `event_type`, `priority_raw`, `confidence_level` (wstępnie), `detection_source`, `event_owner`, pola kontekstowe (price_data, volume_data, technical_context, fundamental_context), `history` |
| **Nie może zmieniać** | `event_id`, `timestamp_utc`, `ticker`, `market`, `instrument_type`, `schema_version` |
| **Przekazuje dalej** | Wzbogacony obiekt `MarketEvent` z określonym typem zdarzenia, priorytetem i danymi kontekstowymi |

### 3.3 Etap scalania (normalizacja, deduplikacja, ocena jakości)

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Listę obiektów `MarketEvent` od wszystkich detektorów |
| **Może zmienić** | `is_composite`, `composite_events`, `priority_final`, `confidence_level`, `quality_level`, `history` |
| **Nie może zmieniać** | `event_id`, `ticker`, `market`, `instrument_type`, `detection_source`, `event_owner`, `priority_raw`, `event_type`, `event_family` |
| **Przekazuje dalej** | Znormalizowaną, odduplikowaną listę `MarketEvent` z przypisanym `quality_level` |
| **Dodatkowa odpowiedzialność** | Usuwanie duplikatów, łączenie zdarzeń w Composite Events, przypisywanie końcowego priorytetu i poziomu jakości |

### 3.4 NewsEngine (NewsPipeline)

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` z quality_level ∈ {CRITICAL, HIGH} (dla MEDIUM — warunkowo) |
| **Może zmienić** | `news_context`, `metadata` (meta-dane o źródłach), `history` |
| **Nie może zmieniać** | `event_id`, `ticker`, `quality_level`, `priority_raw`, `priority_final`, `detection_source`, `event_owner`, wszystkie pola kontekstowe ustawione przez detektory |
| **Przekazuje dalej** | Obiekt `MarketEvent` z dodanym `news_context` |

### 3.5 Tavily (data/tavily)

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` z quality_level ∈ {CRITICAL, HIGH} (gdy NewsEngine nie dostarczył wystarczającego kontekstu lub zdarzenie wymaga szerszego wyszukiwania) |
| **Może zmienić** | `tavily_context`, `metadata`, `history` |
| **Nie może zmieniać** | Tak samo jak NewsEngine — wszystkie pola identyfikacyjne, priorytetowe i kontekstowe |
| **Przekazuje dalej** | Obiekt `MarketEvent` z dodanym `tavily_context` |

### 3.6 MasterEngine

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` + dane pomocnicze (TechnicalResult, NewsResult) |
| **Może zmienić** | `metadata` (informacje o przebiegu orkiestracji), `history` |
| **Nie może zmieniać** | Wszystkie pola analityczne, priorytetowe i identyfikacyjne |
| **Przekazuje dalej** | Obiekt `MarketEvent` (bez zmian analitycznych) do DecisionEngine, RankingEngine, RiskEngine, AnalystEngine |

### 3.7 DecisionEngine / AIEngine

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` + dane z TechnicalEngine i NewsPipeline |
| **Może zmienić** | `ai_context`, `metadata` (flaga: ai_triggered), `history` |
| **Nie może zmieniać** | `event_id`, `ticker`, `detection_source`, `event_owner`, `priority_raw`, `priority_final`, `quality_level` |
| **Przekazuje dalej** | Obiekt `MarketEvent` z dodanym `ai_context` (lub bez, jeśli AI nie zostało uruchomione) |

### 3.8 RiskEngine

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` + AnalysisResult + FullRanking |
| **Może zmienić** | `metadata.risk_assessment`, `history` |
| **Nie może zmieniać** | Wszystkie dane zdarzenia i analizy — RiskEngine tworzy osobny `RiskResult`, nie modyfikuje `MarketEvent` bezpośrednio |
| **Przekazuje dalej** | Obiekt `MarketEvent` + `RiskResult` (jako osobny obiekt, nie jako pole zdarzenia) |

### 3.9 AlertBuilder

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` + `FinalAnalysisResult` |
| **Może zmienić** | `metadata.alert_decision`, `history` |
| **Nie może zmieniać** | Wszystkie dane analityczne, priorytetowe i identyfikacyjne |
| **Przekazuje dalej** | Obiekt `MarketEvent` + decyzja `should_alert()` (true/false) |

### 3.10 AlertDispatcher / TelegramChannel

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` z decyzją `should_alert() == true` |
| **Może zmienić** | `metadata.telegram_message_id`, `history` |
| **Nie może zmieniać** | Wszystkie dane |
| **Przekazuje dalej** | Obiekt `MarketEvent` z potwierdzeniem wysyłki |

### 3.11 HistoryRepository

| Aspekt | Opis |
|--------|------|
| **Otrzymuje** | Obiekt `MarketEvent` po zakończeniu przetwarzania |
| **Może zmienić** | `metadata.archived_at`, `history` |
| **Nie może zmieniać** | Wszystkie pola (obiekt zostaje zamrożony przy archiwizacji) |
| **Przekazuje dalej** | Nic — koniec cyklu życia |

---

## 4. NIEZMIENNIKI

Niezmienniki to zasady, które **muszą być spełnione zawsze**, niezależnie od etapu przetwarzania, wersji systemu czy konfiguracji. Każdy moduł musi je respektować.

### N1. Identyfikator zdarzenia nigdy się nie zmienia

`event_id` jest generowany raz, w momencie utworzenia zdarzenia. Żaden moduł nie może go nadpisać, zmodyfikować ani zastąpić. Służy jako klucz główny w całym systemie.

### N2. Źródło wykrycia nie może zostać nadpisane

`detection_source` jest ustawiane przez detektor, który jako pierwszy wykrył zdarzenie. Żaden późniejszy moduł nie może zmienić tego pola. W przypadku Composite Events — pole pozostaje puste, a źródła składowe są w `composite_events`.

### N3. Historia zmian jest zachowywana

Każda modyfikacja obiektu `MarketEvent` musi być odnotowana w polu `history`. Wpis zawiera: timestamp operacji, nazwę modułu, opis akcji oraz listę zmienionych pól. Historia jest rosnąca chronologicznie — nowe wpisy są dopisywane na koniec.

### N4. Każde zdarzenie ma właściciela

`event_owner` musi być ustawione przez detektor. Żaden moduł nie może zmienić właściciela zdarzenia. Właściciel określa, który silnik jest odpowiedzialny za dalszą analizę.

### N5. Każde zdarzenie posiada poziom pewności

`confidence_level` musi być ustawione przez detektor (wstępna wartość). Może być później skorygowane przez etap oceny jakości, ale nigdy nie może pozostać puste.

### N6. Surowy priorytet jest niezmienny

`priority_raw` jest stałą wartością zdefiniowaną w Katalogu Zdarzeń Rynkowych. Odzwierciedla istotność typu zdarzenia niezależnie od kontekstu. Żaden moduł nie może go zmienić.

### N7. Ticker i rynek są niezmienne po ustawieniu

`ticker` i `market` są ustawiane na etapie tworzenia zdarzenia i nigdy nie są modyfikowane. Zapewnia to spójność identyfikacji instrumentu w całym systemie.

### N8. Wersja schematu jest deklarowana przy utworzeniu

`schema_version` jest ustawiane raz, w momencie utworzenia zdarzenia. Informuje wszystkie moduły o formacie danych. Moduły używają tej informacji do wyboru odpowiedniego parsera/deserializatora.

### N9. Kontekst nie nadpisuje identyfikacji

Dodanie danych kontekstowych (news_context, ai_context, tavily_context) nie może zmienić pól identyfikacyjnych, priorytetowych ani źródła wykrycia. Kontekst jedynie wzbogaca zdarzenie.

### N10. Composite Event dziedziczy najwyższy priorytet

`priority_final` dla zdarzenia złożonego jest równy `max(priorities of component events)`. Zdarzenie złożone nie może mieć niższego priorytetu niż jego składowe.

### N11. Poziom jakości determinuje dalsze przetwarzanie

`quality_level == IGNORE` → natychmiastowe przerwanie przetwarzania (tylko archiwizacja).
`quality_level == LOW` → tylko archiwizacja, bez dalszej analizy.
Żaden moduł downstream nie może przetwarzać zdarzeń z tymi poziomami jakości.

### N12. Deduplikacja poprzedza analizę

Sprawdzenie duplikatu (`OpportunityDeduplicator`) następuje przed uruchomieniem kosztownych zasobów (News, Tavily, AI). Duplikaty są archiwizowane, ale nie analizowane.

### N13. Sposób wyliczania confidence_level może być różny dla poszczególnych rodzin zdarzeń

Dokumentacja definiuje zakres (0.0–1.0), znaczenie (poziom pewności detekcji) oraz odpowiedzialność za ustawienie (detektor → etap oceny jakości). Nie definiuje natomiast algorytmu wyliczania `confidence_level`.

Sposób wyliczania `confidence_level` może być różny dla poszczególnych rodzin zdarzeń (PRICE, VOLUME, TECHNICAL, FUNDAMENTAL, CORPORATE, REGULATORY, MACRO, ETF, DERIVATIVES, SENTIMENT, SYSTEM), o ile pozostaje zgodny z kontraktem danych:
- Wartość zawsze w zakresie 0.0–1.0
- Wyższa wartość oznacza większą pewność
- Pole nigdy nie może pozostać puste
- Końcowa korekta przez etap oceny jakości jest dopuszczalna


## 5. HISTORIA ZDARZENIA

### 5.1 Struktura wpisu historii

Każdy wpis w polu `history` ma następującą strukturę:

```
HistoryEntry:
├── timestamp: datetime (ISO 8601, UTC) — moment modyfikacji
├── module: string — nazwa modułu dokonującego zmiany
├── action: string — opis wykonanej akcji
├── fields_changed: array[string] — lista nazw pól, które zostały zmodyfikowane
└── details: object (opcjonalny) — dodatkowe szczegóły zmiany
```

### 5.2 Ścieżka chronologiczna

```
Utworzenie
    │
    ▼
Detekcja (przez detektor — ustawienie typu, priorytetu, kontekstu)
    │
    ▼
Normalizacja (scalanie — utworzenie Composite Events, obliczenie priority_final)
    │
    ▼
Deduplikacja (sprawdzenie unikalności)
    │
    ├── Duplikat → koniec ścieżki (status IGNORE w historii)
    │
    ▼
Ocena jakości (przypisanie quality_level)
    │
    ├── IGNORE / LOW → koniec ścieżki
    │
    ▼
Pobranie News (jeśli quality_level ≥ MEDIUM i kryteria spełnione)
    │
    ▼
Tavily (jeśli quality_level ∈ {CRITICAL, HIGH} i kryteria spełnione)
    │
    ▼
MasterEngine — orkiestracja
    │
    ▼
DecisionEngine — decyzja o AI
    │
    ├── AI pominięte → przejście dalej bez ai_context
    │
    ▼
RiskEngine — ocena ryzyka
    │
    ▼
AlertBuilder — decyzja o alercie
    │
    ├── Alert niewysłany → tylko archiwizacja
    │
    ▼
Wysłanie alertu (Telegram)
    │
    ▼
Archiwizacja (HistoryRepository — obiekt zamrożony)
```

### 5.3 Przykładowa historia

```
history: [
  {
    "timestamp": "2026-07-18T14:32:05Z",
    "module": "MarketScanner",
    "action": "Utworzenie zdarzenia dla instrumentu XYZ.WA",
    "fields_changed": ["event_id", "timestamp_utc", "ticker", "market", "instrument_type", "schema_version"]
  },
  {
    "timestamp": "2026-07-18T14:32:06Z",
    "module": "Price Event Detector (TechnicalEngine)",
    "action": "Wykrycie zdarzenia: PRICE_SURGE (+12.3%)",
    "fields_changed": ["event_family", "event_category", "event_type", "priority_raw", "confidence_level", "detection_source", "event_owner", "price_data"]
  },
  {
    "timestamp": "2026-07-18T14:32:07Z",
    "module": "Volume Event Detector (TechnicalEngine)",
    "action": "Wykrycie zdarzenia: VOLUME_SPIKE (4.2x avg)",
    "fields_changed": ["event_family", "event_category", "event_type", "priority_raw", "confidence_level", "detection_source", "event_owner", "volume_data"]
  },
  {
    "timestamp": "2026-07-18T14:32:08Z",
    "module": "Scalanie (MasterEngine)",
    "action": "Połączenie zdarzeń w Composite Event: PRICE_SURGE + VOLUME_SPIKE",
    "fields_changed": ["is_composite", "composite_events", "priority_final", "history"]
  },
  {
    "timestamp": "2026-07-18T14:32:08Z",
    "module": "OpportunityDeduplicator",
    "action": "Deduplikacja — zdarzenie unikalne",
    "fields_changed": ["metadata.dedup_hash"]
  },
  {
    "timestamp": "2026-07-18T14:32:09Z",
    "module": "Ocena jakości",
    "action": "Ocena jakości — poziom: CRITICAL (Composite Event + Krytyczny priorytet)",
    "fields_changed": ["quality_level"]
  },
  {
    "timestamp": "2026-07-18T14:32:12Z",
    "module": "NewsPipeline",
    "action": "Pobranie newsów — 3 znalezione",
    "fields_changed": ["news_context"]
  },
  {
    "timestamp": "2026-07-18T14:32:25Z",
    "module": "DecisionEngine",
    "action": "AI uruchomiona — analiza zakończona",
    "fields_changed": ["ai_context"]
  },
  {
    "timestamp": "2026-07-18T14:32:26Z",
    "module": "AlertBuilder",
    "action": "Alert wysłany — spełnione kryteria (score: 87, confidence: 91%)",
    "fields_changed": ["metadata.alert_decision"]
  },
  {
    "timestamp": "2026-07-18T14:32:27Z",
    "module": "TelegramChannel",
    "action": "Alert wysłany przez Telegram — message_id: 12345",
    "fields_changed": ["metadata.telegram_message_id"]
  },
  {
    "timestamp": "2026-07-18T14:32:28Z",
    "module": "HistoryRepository",
    "action": "Archiwizacja — zapisano w repozytorium",
    "fields_changed": ["metadata.archived_at"]
  }
]
```

---

## 6. WERSJONOWANIE

### 6.1 Zasada rozszerzalności

Model danych `MarketEvent` został zaprojektowany z myślą o przyszłej rozbudowie. Nowe pola mogą być dodawane bez naruszania zgodności z istniejącymi modułami.

### 6.2 Reguły wersjonowania

| Reguła | Opis |
|--------|------|
| **R1. Wersja schematu w obiekcie** | Każdy obiekt `MarketEvent` zawiera pole `schema_version` określające wersję kontraktu, w której został utworzony. |
| **R2. Kompatybilność wsteczna** | Nowe wersje kontraktu NIE usuwają istniejących pól. Pola mogą być jedynie dodawane lub oznaczane jako przestarzałe (`deprecated`). |
| **R3. Pola opcjonalne jako mechanizm rozszerzeń** | Wszystkie nowe pola są dodawane jako opcjonalne (`NIE` w kolumnie "Wymagane"). Moduły, które nie znają nowego pola, po prostu je ignorują. |
| **R4. Niezmienność istniejących pól** | Znaczenie, typ i wymagalność istniejących pól nie zmieniają się w nowych wersjach. Zmiana typu lub znaczenia istniejącego pola wymaga nowej wersji głównej (major). |
| **R5. Pola przestarzałe** | Pole może zostać oznaczone jako `deprecated` w nowej wersji. Przez co najmniej 2 kolejne wersje minor pozostaje dostępne, zanim zostanie usunięte w następnej wersji major. |
| **R6. Walidacja wersji** | Każdy moduł przed przetworzeniem obiektu sprawdza `schema_version`. Jeśli wersja jest nowsza niż obsługiwana przez moduł, moduł przetwarza tylko znane mu pola, ignorując pozostałe. |
| **R7. Konwersja między wersjami** | Jeśli to konieczne, system może zawierać adaptery konwertujące obiekty między wersjami. Adaptery te nie modyfikują oryginalnego obiektu — tworzą nowy. |

### 6.3 Strategia numeracji wersji

```
Wersja: MAJOR.MINOR

MAJOR — zwiększany gdy:
  - Zmiana typu istniejącego pola
  - Usunięcie istniejącego pola
  - Zmiana znaczenia istniejącego pola
  - Zmiana wymagalności istniejącego pola

MINOR — zwiększany gdy:
  - Dodanie nowego pola (opcjonalnego)
  - Oznaczenie pola jako deprecated
  - Dodanie nowej wartości do istniejącego enum
```

### 6.4 Przykład rozszerzenia

**Wersja 1.0** (obecna):
```
Pola: event_id, timestamp_utc, ticker, ... (27 pól wg specyfikacji)
```

**Wersja 1.1** (przyszła — dodanie obsługi kryptowalut):
```
Nowe pole: on_chain_context: object | NIE (opcjonalne)
  - Zawiera dane on-chain: whale_alerts, exchange_flows, hash_rate, fork_events

Wszystkie istniejące pola bez zmian.
Moduły nieobsługujące kryptowalut ignorują on_chain_context.
```

**Wersja 2.0** (przyszła — zmiana typu pola):
```
Zmiana: instrument_type rozszerzony o CRYPTO, FOREX, INDEX
  - To jest zmiana typu enum → MAJOR version bump
  - Wymaga aktualizacji wszystkich modułów
```

### 6.5 Macierz kompatybilności

| Moduł \ Wersja obiektu | 1.0 | 1.1 | 2.0 |
|------------------------|:---:|:---:|:---:|
| TechnicalEngine v1.0 | ✅ Pełna | ✅ Częściowa (ignoruje nowe pola) | ❌ Wymaga aktualizacji |
| NewsEngine v1.0 | ✅ Pełna | ✅ Częściowa | ❌ Wymaga aktualizacji |
| DecisionEngine v1.0 | ✅ Pełna | ✅ Częściowa | ❌ Wymaga aktualizacji |

---

## 7. DIAGRAM ASCII — PRZEPŁYW ZDARZENIA PRZEZ SYSTEM

Poniższy diagram przedstawia ścieżkę **jednego zdarzenia** od momentu powstania do archiwizacji. Każdy blok pokazuje moduł przetwarzający, dane wejściowe/wyjściowe oraz punkty decyzyjne.

```
═══════════════════════════════════════════════════════════════════════════════════════
                ALCHEMIK — PRZEPŁYW POJEDYNCZEGO ZDARZENIA RYNKOWEGO
                       (MarketEvent Lifecycle — Single Event)
═══════════════════════════════════════════════════════════════════════════════════════

  [KONFIGURACJA / UNIWERSUM / SKANER RYNKU]
       │
       │ Lista kandydatów
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ① UTWORZENIE ZDARZENIA                                    │
│                        MarketScanner / HunterEngine                              │
│                                                                                  │
│  WE:  ticker, dane rynkowe (OHLCV)                                              │
│  WY:  MarketEvent {                                                             │
│         event_id      ← UUID v4                                                  │
│         timestamp_utc ← teraz()                                                  │
│         ticker        ← "XYZ.WA"                                                 │
│         market        ← "GPW"                                                    │
│         instrument_type ← STOCK_GPW                                              │
│         schema_version ← "1.0"                                                   │
│         history[0]    ← "Utworzenie zdarzenia"                                   │
│       }                                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       │ Obiekt MarketEvent (pusty kontekst)
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ② DETEKCJA                                                │
│              Wszystkie detektory (11 rodzin — ok. 157 typów zdarzeń)             │
│                                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐ │
│  │ PRICE (TechnicalEng)│  │ VOLUME (TechnicalEng│  │ TECHNICAL (TechnicalEng)│ │
│  │ 10 zdarzeń          │  │ 5 zdarzeń           │  │ 34 zdarzenia            │ │
│  └─────────┬───────────┘  └─────────┬───────────┘  └───────────┬─────────────┘ │
│            │                        │                          │               │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐ │
│  │ FUNDAMENTAL         │  │ CORPORATE           │  │ REGULATORY (NewsEng)    │ │
│  │ (AnalystEng)        │  │ (NewsEng)           │  │ 3 zdarzenia             │ │
│  │ 24 zdarzenia        │  │ 34 zdarzenia        │  │                         │ │
│  └─────────┬───────────┘  └─────────┬───────────┘  └───────────┬─────────────┘ │
│            │                        │                          │               │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐ │
│  │ MACRO (NewsEng)     │  │ ETF (AnalystEng)    │  │ DERIVATIVES (AnalystEng)│ │
│  │ 16 zdarzeń          │  │ 4 zdarzenia         │  │ 9 zdarzeń               │ │
│  └─────────┬───────────┘  └─────────┬───────────┘  └───────────┬─────────────┘ │
│            │                        │                          │               │
│  ┌─────────────────────┐  ┌──────────────────────────────────────────────────┐ │
│  │ SENTIMENT/NEWS      │  │ SYSTEM (Multi-Engine)                             │ │
│  │ (NewsEng)           │  │ 12 zdarzeń (złożone, międzyinstrumentowe,         │ │
│  │ 11 zdarzeń          │  │ sezonowe, sektorowe, korelacje)                   │ │
│  └─────────┬───────────┘  └────────────────────┬─────────────────────────────┘ │
│            │                                   │                                │
│  WE:  MarketEvent + dane źródłowe                                              │
│  WY:  MarketEvent + {                                                          │
│         event_family, event_category, event_type,                               │
│         priority_raw, confidence_level (wstępny),                               │
│         detection_source, event_owner,                                          │
│         price_data | volume_data | technical_context | fundamental_context      │
│       }                                                                         │
│                                                                                  │
│  ⚠ Każdy detektor tworzy OSOBNY obiekt MarketEvent dla każdego wykrytego       │
│    zdarzenia. Jeden instrument może wygenerować wiele zdarzeń.                   │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       │ Lista MarketEvent (od wszystkich detektorów)
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ③ NORMALIZACJA I SCALANIE                                    │
│                        Etap scalania                                             │
│                                                                                  │
│  WE:  Lista MarketEvent (wiele zdarzeń, możliwie różne typy)                    │
│                                                                                  │
│  KROKI:                                                                          │
│  3a. Normalizacja struktury (ujednolicenie formatu)                              │
│  3b. Identyfikacja zdarzeń pokrewnych (ten sam instrument, bliski timestamp)    │
│  3c. Łączenie w Composite Events (PRICE_SURGE + VOLUME_SPIKE → Composite)       │
│  3d. Obliczenie priority_final                                                  │
│                                                                                  │
│  WY:  Lista MarketEvent (znormalizowana, ze scalonymi Composite Events)         │
│       + priority_final                                                           │
│       + is_composite / composite_events                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ④ DEDUPLIKACJA                                               │
│                   OpportunityDeduplicator                                        │
│                                                                                  │
│  WE:  MarketEvent                                                                │
│                                                                                  │
│  Czy hash(symbol + event_type + timestamp) istnieje w oknie deduplikacji?       │
│       │                                                                          │
│       ├── TAK ──→ quality_level = IGNORE ──→ [PRZERWANIE — tylko archiwizacja]  │
│       │                                                                          │
│       └── NIE ──→ KONTYNUUJ                                                      │
│                                                                                  │
│  WY:  MarketEvent (z dedup_hash w metadata)                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       │ (tylko unikalne zdarzenia)
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑤ OCENA JAKOŚCI                                              │
│                        Etap oceny jakości                                         │
│                                                                                  │
│  WE:  MarketEvent (unikalne)                                                     │
│                                                                                  │
│  Wyznaczenie quality_level na podstawie:                                         │
│    - priority_raw                                                                │
│    - priority_final (dla Composite: max składowych)                              │
│    - grupa instrumentu (GPW/USA/ETF)                                             │
│    - liczba zdarzeń składowych                                                   │
│    - powtarzalność                                                               │
│                                                                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐                       │
│  │ CRITICAL │   HIGH   │  MEDIUM  │   LOW    │  IGNORE  │                       │
│  │ ▼        │   ▼      │   ▼      │   ▼      │   ▼      │                       │
│  │ pełna    │ analiza  │ analiza  │ tylko    │ pominię- │                       │
│  │ analiza  │ rozsz.   │ podst.   │ historia │ cie      │                       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘                       │
│       │          │          │          │          │                              │
│       ▼          ▼          ▼          ▼          ▼                              │
│    [DALEJ]   [DALEJ]   [DALEJ]    [STOP]     [STOP]                             │
│                                     │          │                                 │
│                                     └────┬─────┘                                 │
│                                          ▼                                        │
│                                   [ARCHIWIZACJA]                                  │
│                                                                                  │
│  WY:  MarketEvent + quality_level                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       │ quality_level ∈ {CRITICAL, HIGH, MEDIUM}
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑥ NEWS ENGINE                                                │
│                        NewsPipeline                                              │
│                                                                                  │
│  WE:  MarketEvent + quality_level                                                │
│                                                                                  │
│  Czy quality_level ∈ {CRITICAL, HIGH}?                                           │
│       │                                                                          │
│       ├── TAK ──→ Pobierz newsy (NewsPipeline.process(symbol))                  │
│       │                                                                          │
│       └── NIE (MEDIUM) ──→ Pomiń (chyba że zdarzenie fundamentalne/korporacyjne)│
│                                                                                  │
│  WY:  MarketEvent + news_context (lista powiązanych newsów)                      │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑦ TAVILY (WYSZUKIWANIE W CZASIE RZECZYWISTYM)               │
│                        data/tavily                                               │
│                                                                                  │
│  WE:  MarketEvent + quality_level                                                │
│                                                                                  │
│  Czy quality_level ∈ {CRITICAL, HIGH} ORAZ spełnione kryteria Tavily?           │
│       │                                                                          │
│       ├── TAK ──→ Wyszukaj Tavily                                                │
│       │                                                                          │
│       └── NIE ──→ Pomiń                                                          │
│                                                                                  │
│  WY:  MarketEvent + tavily_context (wyniki wyszukiwania)                         │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑧ MASTERENGINE — ORKIESTRACJA                               │
│                        engines/master/engine.py                                  │
│                                                                                  │
│  WE:  MarketEvent + dane z silników                                              │
│                                                                                  │
│  Sekwencja:                                                                      │
│    TechnicalEngine.analyze() → TechnicalResult                                   │
│    NewsPipeline.process()    → NewsResult                                        │
│    DecisionEngine.process()  → AISignal (z/bez AI)                               │
│    RankingEngine.calculate() → FullRanking                                       │
│    RiskEngine.assess()       → RiskResult                                        │
│    AnalystEngine.generate()  → FinalAnalysisResult                               │
│                                                                                  │
│  WY:  MarketEvent (wzbogacony o metadata) + FinalAnalysisResult                  │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑨ DECISIONENGINE — DECYZJA O AI                             │
│                        engines/ai/decision_engine.py                             │
│                                                                                  │
│  WE:  MarketEvent + TechnicalResult + NewsResult                                 │
│                                                                                  │
│  Czy quality_level ∈ {CRITICAL, HIGH}?                                           │
│       │                                                                          │
│       ├── NIE ──→ [Pomiń AI]                                                     │
│       │                                                                          │
│       └── TAK                                                                     │
│            │                                                                      │
│            Czy wymaga interpretacji / łączenia źródeł / wpływu na decyzję?       │
│                 │                                                                 │
│                 ├── TAK ──→ AIProvider.analyze() → ai_context                    │
│                 │                                                                 │
│                 └── NIE ──→ [Pomiń AI]                                           │
│                                                                                  │
│  WY:  MarketEvent + ai_context (lub bez) + AISignal                              │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑩ RISKENGINE — OCENA RYZYKA                                 │
│                        engines/risk/engine.py                                    │
│                                                                                  │
│  WE:  MarketEvent + AnalysisResult + FullRanking                                 │
│                                                                                  │
│  WY:  MarketEvent + RiskResult {                                                 │
│         risk_score, risk_level (LOW/MEDIUM/HIGH/CRITICAL),                       │
│         risk_factors, stop_loss, take_profit, max_position_size                  │
│       }                                                                          │
│                                                                                  │
│  ⚠ RiskEngine NIE modyfikuje MarketEvent — tworzy osobny RiskResult             │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑪ ALERT BUILDER — DECYZJA O ALERCIE                         │
│                        application/alert_builder.py                              │
│                                                                                  │
│  WE:  MarketEvent + FinalAnalysisResult                                          │
│                                                                                  │
│  should_alert():                                                                 │
│    • final_rating ≥ 70?                                                          │
│    • confidence_level ≥ 70%?                                                     │
│    • recommendation ∈ {STRONG_BUY, BUY}?                                         │
│    • nie duplikat?                                                               │
│       │                                                                          │
│       ├── NIE ──→ [STOP — tylko archiwizacja]                                   │
│       │                                                                          │
│       └── TAK ──→ build_alert() → AlertMessage                                  │
│                                                                                  │
│  WY:  MarketEvent + decyzja alertu (metadata.alert_decision)                     │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       │ (jeśli alert wysłany)
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑫ WYSYŁKA ALERTU                                             │
│                   AlertDispatcher → TelegramChannel                              │
│                                                                                  │
│  WE:  AlertMessage                                                               │
│                                                                                  │
│  TelegramChannel.send(alert)                                                     │
│       │                                                                          │
│       ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                         📱 TELEGRAM                                       │  │
│  │                                                                           │  │
│  │  🚨 ALCHEMIK ALERT                                                       │  │
│  │  Symbol: XYZ.WA                                                           │  │
│  │  Zdarzenie: PRICE_SURGE (+12.3%) + VOLUME_SPIKE (4.2x)                   │  │
│  │  Priorytet: CRITICAL                                                     │  │
│  │  Rekomendacja: STRONG_BUY                                                │  │
│  │  Score: 87.3  |  Confidence: 91%                                         │  │
│  │  Podsumowanie: [analiza AI]                                              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  WY:  MarketEvent + metadata.telegram_message_id                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ⑬ ARCHIWIZACJA                                               │
│                        HistoryRepository                                         │
│                                                                                  │
│  WE:  MarketEvent (końcowy, po wszystkich etapach)                               │
│                                                                                  │
│  Zapis do repozytorium:                                                          │
│    - CycleReport (meta-dane cyklu)                                               │
│    - MarketEvent (pełna historia + wszystkie konteksty)                          │
│    - OpportunityDeduplicator.mark_processed()                                    │
│                                                                                  │
│  Obiekt zostaje ZAMROŻONY — żadne dalsze modyfikacje nie są dozwolone.          │
└─────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
  [KONIEC CYKLU ŻYCIA ZDARZENIA]
       │
       ▼
  [OCZEKIWANIE NA NASTĘPNY CYKL — Scheduler]
```

---

## 8. OCENA KOŃCOWA

### 8.1 Czy kontrakt jest kompletny?

**TAK.** Kontrakt obejmuje:

- **27 pól** wspólnego obiektu `MarketEvent` — każde z określonym znaczeniem, typem, wymagalnością i odpowiedzialnością za uzupełnienie
- **13 etapów** cyklu życia zdarzenia — od utworzenia przez detekcję, normalizację, deduplikację, ocenę jakości, wzbogacanie kontekstem (News, Tavily, AI), orkiestrację, decyzję o alercie, wysyłkę, aż po archiwizację
- **11 modułów** z jasno określoną odpowiedzialnością — co otrzymują, co mogą zmienić, czego nie mogą zmieniać, co przekazują dalej
- **13 niezmienników** — zasad, które muszą być spełnione zawsze, gwarantujących integralność danych
- **Mechanizm historii** — chronologiczne śledzenie każdej modyfikacji obiektu
- **System wersjonowania** — umożliwiający przyszłą rozbudowę bez naruszania kompatybilności

Kontrakt bazuje na istniejących dokumentach projektowych ALCHEMIKA i jest z nimi spójny:
- Zgodny z Katalogiem Zdarzeń Rynkowych (157 typów zdarzeń)
- Zgodny z Hierarchią Zdarzeń Rynkowych (11 rodzin, klasyfikacja Podstawowe/Pochodne)
- Zgodny z Przepływem Zdarzeń Rynkowych (13 etapów cyklu życia)
- Zgodny z Przepływem Danych (7 silników + warstwa aplikacyjna)
- Zgodny z Filozofią ALCHEMIKA (AI interpretuje, nie decyduje)
- Zgodny z INSTRUKCJA_DLA_CLINE (modułowość, Public API)

### 8.2 Czy wszystkie moduły mogą korzystać z jednego modelu danych?

**TAK.** Wspólny obiekt `MarketEvent` został zaprojektowany tak, aby każdy moduł systemu mógł:

- **Odczytać** tylko te pola, które są dla niego istotne (dzięki kategoryzacji pól)
- **Zapisać** tylko te pola, za które odpowiada (jasno określona odpowiedzialność)
- **Ignorować** pola, których nie zna lub nie potrzebuje (dzięki polom opcjonalnym i wersjonowaniu)

Model jest neutralny wobec:
- **Typu instrumentu** — to samo pole `instrument_type` rozróżnia GPW/USA/ETF
- **Typu zdarzenia** — pola `event_family`, `event_category`, `event_type` zapewniają pełną klasyfikację
- **Źródła danych** — pola kontekstowe (`price_data`, `volume_data`, `technical_context`, `fundamental_context`, `news_context`, `ai_context`, `tavily_context`) są warunkowe — wypełniane tylko gdy dane źródło jest dostępne
- **Priorytetu** — `priority_raw` (stały, z Katalogu) i `priority_final` (obliczany, zależny od kontekstu) zapewniają dwupoziomową ocenę istotności

### 8.3 Czy kontrakt umożliwia przyszłą rozbudowę systemu bez zmian w rdzeniu?

**TAK.** Kontrakt został zaprojektowany z myślą o rozszerzalności:

1. **Nowe rodzaje zdarzeń** — dodanie nowego typu zdarzenia nie wymaga zmiany modelu; wystarczy nowa wartość `event_type` i ewentualnie nowa `event_category`/`event_subcategory`
2. **Nowe rodziny zdarzeń** — dodanie nowej rodziny (np. `CRYPTO` dla kryptowalut) wymaga tylko dodania nowej wartości enum `event_family` i nowego detektora
3. **Nowe źródła danych** — dodanie nowego pola kontekstowego (np. `on_chain_context`) jako opcjonalnego nie narusza istniejących modułów
4. **Nowe grupy instrumentów** — rozszerzenie `instrument_type` o `CRYPTO`, `FOREX`, `INDEX` jest możliwe w nowej wersji major
5. **Nowe moduły** — każdy nowy moduł otrzymuje ten sam obiekt `MarketEvent` i działa zgodnie z tymi samymi zasadami (co może zmienić, czego nie może)
6. **Nowe kanały powiadomień** — dodanie nowego kanału (np. Discord, Email) nie wymaga zmiany modelu; nowy kanał jedynie odczytuje istniejące dane
7. **Zmiana progów i konfiguracji** — wartości progów dla priorytetów i oceny jakości są konfigurowalne, nie zakodowane w modelu

Zasada z `docs/FILOZOFIA_ALCHEMIKA.md` i `docs/INSTRUKCJA_DLA_CLINE.md` jest zachowana:
> "Obecna architektura rdzenia jest zamrożona — nowe możliwości są projektowane jako rozszerzenia, nie jako modyfikacje istniejących silników i ich Public API."

---

## KONIEC DOKUMENTU

Data utworzenia: 18.07.2026
Wersja: 1.0
Autor: Zespół ALCHEMIK
Status: Dokument projektowy — kontrakt wymiany danych pomiędzy modułami

Dokumenty powiązane:
- `docs/FILOZOFIA_EVENTOUTCOME.md` — opisuje filozofię odpowiedzialności modelu EventOutcome, który przechowuje rezultaty zdarzeń rynkowych (MarketEvent)

Bazuje na:
- `docs/FILOZOFIA_ALCHEMIKA.md`
- `docs/Katalog_Zdarzen_Rynkowych.md` v2.0
- `docs/Hierarchia_Zdarzen_Rynkowych.md` v1.0
- `docs/Przeplyw_Zdarzen_Rynkowych.md` v1.0
- `docs/Przeplyw_Danych.md`
- `docs/INSTRUKCJA_DLA_CLINE.md`
- `struktura_alchemik.txt`
- `README.md`
