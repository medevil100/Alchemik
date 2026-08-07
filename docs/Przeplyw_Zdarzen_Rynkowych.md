# ALCHEMIK — PRZEPŁYW WYKRYWANIA ZDARZEŃ RYNKOWYCH

## DOKUMENT PROJEKTOWY — PRZEPŁYW INFORMACJI

Data: 18.07.2026
Wersja: 1.0
Status: Dokument projektowy — nie implementacyjny

---

## SPIS TREŚCI

1. [Pobranie i przygotowanie danych](#1-pobranie-i-przygotowanie-danych)
2. [Uruchamianie detektorów](#2-uruchamianie-detektorów)
3. [Scalanie wykrytych zdarzeń](#3-scalanie-wykrytych-zdarzeń)
4. [Ocena jakości zdarzeń](#4-ocena-jakości-zdarzeń)
5. [Moment pobierania News](#5-moment-pobierania-news)
6. [Moment użycia Tavily](#6-moment-użycia-tavily)
7. [Moment użycia AI](#7-moment-użycia-ai)
8. [MasterEngine](#8-masterengine)
9. [DecisionEngine](#9-decisionengine)
10. [RiskEngine](#10-riskengine)
11. [Telegram](#11-telegram)
12. [Przerwanie analizy](#12-przerwanie-analizy)
13. [Diagram ASCII](#13-diagram-ascii)
14. [Ocena końcowa](#14-ocena-końcowa)

---

## 1. POBRANIE I PRZYGOTOWANIE DANYCH

### 1.1 Pobranie danych

Cykl rozpoczyna się od `RuntimeService.run_cycle()`. System pobiera listę kandydatów (instrumentów) do analizy:

- **Ze skanera rynku** (`MarketScanner`) — gdy jest skonfigurowany. MarketScanner przeszukuje dostępne źródła (np. Yahoo Finance) w poszukiwaniu instrumentów spełniających wstępne kryteria (np. zmiana ceny, zmiana wolumenu powyżej progu).

- **Z HunterEngine bezpośrednio** — gdy MarketScanner nie jest dostępny. HunterEngine otrzymuje dane wejściowe (np. statyczną listę instrumentów) i rozpoczyna proces pozyskiwania danych.

**Źródła danych:**
- Yahoo Finance (`YahooFetcher` → `data/yahoo/`) — OHLCV, dane fundamentalne, dane o spółkach
- News pipeline (`NewsPipeline` → `engines/news/`) — newsy z kanałów informacyjnych
- Tavily API (`data/tavily/`) — wyszukiwanie w czasie rzeczywistym

**Dane pobierane w pierwszej kolejności:**
1. Notowania OHLCV (ceny, wolumen)
2. Podstawowe dane o instrumencie (symbol, nazwa, rynek, sektor)

### 1.2 Walidacja danych

Po pobraniu danych system sprawdza:

- **Kompletność** — czy dane OHLCV zawierają wymagane pola (open, high, low, close, volume)
- **Aktualność** — czy dane są świeże (timestamp w akceptowalnym oknie czasowym)
- **Spójność** — czy high ≥ low, close mieści się w zakresie high-low, wolumen ≥ 0
- **Brak wartości null** — czy kluczowe pola nie zawierają pustych wartości
- **Symbol poprawny** — czy symbol instrumentu jest niepustym stringiem (walidacja w `MasterEngine.run_analysis()`)

**Jeśli walidacja nie przejdzie:**
- Instrument jest odrzucany
- Błąd jest logowany w `CycleReport.errors` jako `CandidateError`
- Cykl przechodzi do następnego kandydata

### 1.3 Klasyfikacja instrumentu

Każdy instrument otrzymuje klasyfikację do jednej z trzech grup:

| Grupa | Oznaczenie | Kryterium |
|-------|-----------|-----------|
| **GPW** | `[GPW]` | Instrument notowany na GPW (rynek główny lub NewConnect) |
| **USA** | `[USA]` | Instrument notowany na giełdach amerykańskich (NYSE, NASDAQ, AMEX) |
| **ETF** | `[ETF]` | Fundusz ETF (niezależnie od giełdy) |

Klasyfikacja determinuje:
- Które detektory będą uruchomione (np. ESPI/EBI tylko dla GPW, Short Interest tylko dla USA)
- Które progi są stosowane (inne dla groszówek, inne dla ETF)
- Które zdarzenia są uznawane za istotne dla danej grupy

### 1.4 Przygotowanie danych dla silników

Dane są przekształcane do formatu wymaganego przez poszczególne silniki:

- **TechnicalEngine** — otrzymuje dane OHLCV w formacie akceptowanym przez `TechnicalEngine.analyze([symbol])`
- **NewsEngine** — otrzymuje symbol do wyszukania newsów przez `NewsPipeline.process([symbol])`
- **HunterEngine** — otrzymuje listę kandydatów z danymi rynkowymi i metadanymi
- **AnalystEngine** — otrzymuje wyniki poprzednich silników

---

## 2. URUCHAMIANIE DETEKTORÓW

### Architektura detektorów

Detektory są logicznymi jednostkami odpowiedzialnymi za wykrywanie konkretnych typów zdarzeń rynkowych. Każdy detektor działa w ramach istniejącego silnika ALCHEMIKA. Detektory opisane poniżej reprezentują **przyszłą strukturę logiczną** — obecnie funkcjonalność detekcyjna jest rozproszona pomiędzy silnikami. Poniższy opis definiuje odpowiedzialności, które zostaną przypisane do dedykowanych detektorów w ramach istniejących silników.

**Mapowanie detektor → istniejący silnik:**
- Price Event Detector → TechnicalEngine
- Volume Event Detector → TechnicalEngine
- Technical Event Detector → TechnicalEngine
- Fundamental Event Detector → AnalystEngine (+ NewsEngine dla danych news-pochodnych)
- Corporate Event Detector → NewsEngine (+ AnalystEngine, AIEngine)
- Regulatory Event Detector → NewsEngine (+ AIEngine)
- Macro Event Detector → NewsEngine (+ AnalystEngine, AIEngine, TechnicalEngine)
- ETF Event Detector → AnalystEngine (+ NewsEngine)
- Derivatives Event Detector → AnalystEngine (+ TechnicalEngine)
- Sentiment & News Event Detector → NewsEngine (+ AIEngine)
- System Event Detector → Wszystkie silniki (Multi-Engine)

---

### 2.1 Price Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | TechnicalEngine |
| **Źródło danych** | Yahoo Finance (OHLCV) |

**Wejście:**
- Dane OHLCV dla instrumentu (co najmniej 2 świece dla zdarzeń bieżących, do 260 świec dziennych dla ekstremów 52-tygodniowych, pełna historia dla ATH/ATL)
- Bieżąca cena i wolumen

**Wyjście:**
- Lista wykrytych zdarzeń cenowych wraz z:
  - Typem zdarzenia (np. `PRICE_SURGE`, `GAP_UP`, `ATH`)
  - Wartością progową (np. +8.5% dla surge)
  - Znacznikiem czasu wykrycia
  - Kontekstem (poprzednia cena, wartość luki, okno pomiaru)

**Odpowiedzialność:**
- Wykrywanie gwałtownych ruchów cenowych (wzrost/spadek o X% w jednej świecy)
- Wykrywanie luk cenowych (gap up / gap down)
- Wykrywanie nowych ekstremów (52-tygodniowe, historyczne)
- Wykrywanie odrzuceń poziomów wsparcia/oporu
- Wykrywanie przekroczeń poziomów psychologicznych

**Zdarzenia (10):**
1.1 Price Surge, 1.2 Price Drop, 1.3 Gap Up, 1.4 Gap Down, 1.5 52-Week High, 1.6 52-Week Low, 1.7 All-Time High, 1.8 All-Time Low, 1.9 Level Rejection, 1.10 Psychological Level Cross

---

### 2.2 Volume Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | TechnicalEngine |
| **Źródło danych** | Yahoo Finance (OHLCV — volume) |

**Wejście:**
- Wolumen z bieżącej świecy
- Średni wolumen z N poprzednich świec (wykorzystuje istniejący wskaźnik RVOL)
- Kierunek świecy (close vs open)

**Wyjście:**
- Lista wykrytych zdarzeń wolumenowych wraz z:
  - Typem zdarzenia (np. `VOLUME_SPIKE`, `HIGH_VOLUME_DOWN_DAYS`)
  - Krotnością odchylenia od średniej
  - Kierunkiem ruchu (dla zdarzeń kierunkowych)

**Odpowiedzialność:**
- Wykrywanie skoku wolumenu (bieżący wolumen przekracza X-krotność średniej)
- Wykrywanie wolumenu bliskiego zeru
- Wykrywanie anomalii wolumenu kumulacyjnego
- Wykrywanie asymetrii wolumenu kierunkowego (przewaga wolumenu na spadkach lub wzrostach)

**Zdarzenia (5):**
2.1 Volume Spike, 2.2 Near-Zero Volume, 2.3 Cumulative Volume Anomaly, 2.4 High Volume on Down Days, 2.5 High Volume on Up Days

---

### 2.3 Technical Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | TechnicalEngine |
| **Źródło danych** | Yahoo Finance (OHLCV) + wskaźniki techniczne |

**Wejście:**
- Dane OHLCV (świece dzienne, zakres zależny od wskaźnika: 14 dla RSI, 20 dla Bollinger, 26 dla MACD, 50+ dla średnich)
- Obliczone wskaźniki techniczne: SMA, EMA, MACD, RSI, Bollinger Bands, ATR, OBV, VWAP, Fibonacci

**Wyjście:**
- Lista wykrytych zdarzeń technicznych wraz z:
  - Typem zdarzenia (np. `RSI_OVERSOLD`, `MACD_CROSSOVER`, `BB_SQUEEZE`)
  - Wartościami wskaźników w momencie wykrycia
  - Opcjonalnym kierunkiem (byczy/niedźwiedzi)

**Odpowiedzialność:**
- **Zmienność:** wzrost/spadek ATR, rozszerzenie/zwężenie wstęg Bollingera
- **Wybicia techniczne:** wybicie powyżej oporu, wybicie poniżej wsparcia, wybicia z formacji (trójkąt, kanał, flaga)
- **Formacje świecowe:** młot, wisielec, objęcia, doji, gwiazdy, żołnierze, kruki, marubozu, harami
- **Trend:** przecięcia średnich kroczących, zmiana nachylenia MA, cena vs MA, serie świec, zmiana struktury trendu
- **Momentum:** RSI wykupienie/wyprzedanie, dywergencja RSI, MACD crossover, MACD zero cross, Stochastic
- **Wskaźniki techniczne:** dywergencja OBV, odchylenie VWAP, ATR expansion, poziomy Fibonacciego

**Zdarzenia (34):**
3.1–3.4 (zmienność), 4.1–4.5 (wybicia), 5.1–5.10 (świece), 6.1–6.5 (trend), 7.1–7.6 (momentum), 8.1–8.4 (wskaźniki)

---

### 2.4 Fundamental Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | AnalystEngine (+ NewsEngine dla danych news-pochodnych) |
| **Źródło danych** | Yahoo Finance (ticker.info, ticker.quarterly_financials), NewsEngine, ESPI/EBI |

**Wejście:**
- Dane fundamentalne z Yahoo Finance: P/E, P/BV, market cap, debt/equity, revenue, net income
- Informacje o publikacjach wyników i raportów z NewsEngine
- Dane o dywidendach, splitach, emisjach i skupach akcji

**Wyjście:**
- Lista wykrytych zdarzeń fundamentalnych wraz z:
  - Typem zdarzenia (np. `EARNINGS_RELEASE`, `REVENUE_CHANGE`, `DIVIDEND_ANNOUNCEMENT`)
  - Wartością wskaźnika przed i po zmianie
  - Procentową zmianą

**Odpowiedzialność:**
- **Wskaźniki finansowe:** zmiana P/E, P/BV, kapitalizacji, zadłużenia, przychodów, zysku netto
- **Wyniki finansowe:** publikacja wyników kwartalnych, earnings beat/miss, korekta prognoz
- **Raporty:** publikacja raportu kwartalnego/rocznego, zmiana polityki rachunkowości
- **Dywidendy:** ogłoszenie dywidendy, zmiana polityki dywidendowej, dywidenda nadzwyczajna, ex-dividend date
- **Splity:** ogłoszenie splitu, wykonanie splitu, reverse split
- **Emisje akcji:** ogłoszenie nowej emisji, emisja z prawem poboru, private placement
- **Skup akcji własnych:** ogłoszenie i realizacja skupu

**Zdarzenia (24):**
9.1–9.6, 10.1–10.4, 11.1–11.3, 14.1–14.4, 15.1–15.3, 16.1–16.3, 17.1–17.2

---

### 2.5 Corporate Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | NewsEngine (+ AnalystEngine, AIEngine) |
| **Źródło danych** | Yahoo Finance (częściowo), NewsEngine, Tavily, ESPI, EBI, SEC |

**Wejście:**
- Dane o insider trading z Yahoo Finance / SEC EDGAR
- Informacje o zmianach akcjonariatu z ESPI
- Rekomendacje analityków i ratingi z serwisów finansowych
- Informacje o fuzjach, kontraktach, pozwach z NewsEngine i Tavily
- Informacje o upadłościach i zmianach zarządu

**Wyjście:**
- Lista wykrytych zdarzeń korporacyjnych wraz z:
  - Typem zdarzenia (np. `INSIDER_BUYING`, `M_AND_A_ANNOUNCEMENT`, `CEO_CHANGE`)
  - Źródłem informacji
  - Istotnością (szczególnie ważne dla groszówek)

**Odpowiedzialność:**
- **Insider Trading:** transakcje insiderów, skup/sprzedaż przez insiderów
- **Zmiany akcjonariatu:** przekroczenie progów, wezwania do sprzedaży, zmiana znaczącego akcjonariusza
- **Rekomendacje i ratingi:** nowa rekomendacja, zmiana ceny docelowej, upgrade/downgrade, zmiana ratingu kredytowego
- **Fuzje i przejęcia:** ogłoszenie M&A, plotki, zakończenie
- **Kontrakty:** podpisanie lub zerwanie znaczącego kontraktu
- **Kwestie prawne:** pozwy, postępowania regulacyjne, kary finansowe, zawieszenie notowań
- **Upadłości:** wniosek o upadłość, restrukturyzacja, upadłość kontrahenta
- **Zmiany zarządu:** zmiana CEO, zarządu, rady nadzorczej, odejście kluczowego pracownika

**Zdarzenia (34):**
18.1–18.3, 19.1–19.3, 20.1–20.3, 21.1–21.2, 22.1–22.3, 23.1–23.2, 24.1–24.2, 25.1–25.3, 26.1–26.3, 27.1–27.4

---

### 2.6 Regulatory Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | NewsEngine (+ AIEngine) |
| **Źródło danych** | ESPI, EBI |
| **Grupa instrumentów** | Wyłącznie [GPW] |

**Wejście:**
- Komunikaty ESPI dla spółek z rynku głównego GPW
- Komunikaty EBI dla spółek z NewConnect

**Wyjście:**
- Lista wykrytych zdarzeń regulacyjnych (tylko dla GPW):
  - `NEW_ESPI_FILING` — nowy komunikat ESPI
  - `ESPI_DELAY` — opóźnienie publikacji
  - `NEW_EBI_FILING` — nowy komunikat EBI

**Odpowiedzialność:**
- Monitorowanie systemu ESPI GPW
- Monitorowanie systemu EBI NewConnect
- Wykrywanie opóźnień w publikacjach
- Klasyfikacja typu komunikatu

**Zdarzenia (3):**
12.1 New ESPI Filing, 12.2 ESPI Filing Delay, 13.1 New EBI Filing

---

### 2.7 Macro Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | NewsEngine (+ AnalystEngine, AIEngine, TechnicalEngine) |
| **Źródło danych** | Yahoo Finance (waluty, surowce), NewsEngine, Tavily, kalendarze ekonomiczne |

**Wejście:**
- Dane makroekonomiczne: PKB, PMI, produkcja przemysłowa, bezrobocie
- Dane o stopach procentowych z banków centralnych
- Dane o inflacji: CPI, PPI
- Kursy walut (OHLCV z Yahoo Finance)
- Ceny surowców (OHLCV z Yahoo Finance)
- Informacje geopolityczne z Tavily i newsów

**Wyjście:**
- Lista wykrytych zdarzeń makro wraz z:
  - Typem zdarzenia (np. `INTEREST_RATE_DECISION`, `CPI_RELEASE`, `FX_MAJOR_MOVE`)
  - Wartością rzeczywistą i odchyleniem od prognoz

**Odpowiedzialność:**
- **Makroekonomia:** publikacja danych makro, zmiana PKB, zmiana bezrobocia
- **Stopy procentowe:** decyzja o stopach, nadzwyczajna zmiana, zmiana forward guidance
- **Inflacja:** publikacja CPI/PPI, zaskoczenie inflacyjne
- **Waluty:** silny ruch walutowy, interwencja walutowa
- **Surowce:** szok cenowy, szok podażowy
- **Geopolityka:** konflikty zbrojne, sankcje, wybory, umowy handlowe

**Zdarzenia (16):**
28.1–28.3, 29.1–29.3, 30.1–30.2, 31.1–31.2, 32.1–32.2, 33.1–33.4

---

### 2.8 ETF Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | AnalystEngine (+ NewsEngine) |
| **Źródło danych** | Yahoo Finance (częściowo), NewsEngine, strony dostawców ETF |
| **Grupa instrumentów** | Wyłącznie [ETF] |

**Wejście:**
- Dane o ETF: skład, NAV, przepływy kapitału
- Informacje o rebalancingu
- Informacje o likwidacji ETF

**Wyjście:**
- Lista wykrytych zdarzeń ETF wraz z typem:
  - `ETF_REBALANCING`
  - `ETF_FLOWS`
  - `ETF_PREMIUM_DISCOUNT`
  - `ETF_CLOSURE`

**Odpowiedzialność:**
- Monitorowanie zmian składu ETF (rebalancing)
- Monitorowanie napływów i odpływów kapitału
- Wykrywanie premii/dyskonta ETF vs NAV
- Wykrywanie likwidacji ETF

**Zdarzenia (4):**
36.1 ETF Rebalancing, 36.2 ETF Flows, 36.3 ETF Premium/Discount, 36.4 ETF Closure

---

### 2.9 Derivatives Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | AnalystEngine (+ TechnicalEngine) |
| **Źródło danych** | Yahoo Finance (częściowo — opcje), zewnętrzne źródła danych |
| **Grupa instrumentów** | Głównie [USA] i [ETF] |

**Wejście:**
- Dane o opcjach: wolumen, open interest, implied volatility, strike
- Dane o short interest
- Dane o dark pool
- Dane o transakcjach blokowych i pakietowych

**Wyjście:**
- Lista wykrytych zdarzeń pochodnych:
  - `UNUSUAL_OPTIONS_ACTIVITY`
  - `IV_CHANGE`
  - `SHORT_SQUEEZE`
  - `DARK_POOL_ACTIVITY`
  - `BLOCK_TRADE`

**Odpowiedzialność:**
- **Opcje:** nietypowa aktywność, zmiana IV, max pain
- **Short Interest:** wzrost, short squeeze, days to cover
- **Dark Pool:** nietypowa aktywność
- **Nietypowe transakcje:** block trade, transakcje pakietowe (GPW)

**Zdarzenia (9):**
37.1–37.3, 38.1–38.3, 39.1, 40.1–40.2

---

### 2.10 Sentiment & News Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | NewsEngine (+ AIEngine, Tavily) |
| **Źródło danych** | Media społecznościowe (API), serwisy finansowe, Tavily, agencje prasowe |

**Wejście:**
- Dane o wzmiankach w social media
- Indeksy sentymentu (Fear & Greed, VIX, Put/Call Ratio)
- Newsy z agencji prasowych
- Wyniki wyszukiwania Tavily

**Wyjście:**
- Lista wykrytych zdarzeń sentymentowych i newsowych:
  - `SOCIAL_MEDIA_SPIKE`
  - `SENTIMENT_SHIFT`
  - `BREAKING_NEWS`
  - `TAVILY_RESULT`

**Odpowiedzialność:**
- **Media społecznościowe:** wzmianki, trendy na Reddit, wzmianki influencerów
- **Sentyment rynku:** zmiana sentymentu, VIX spike, Put/Call Ratio
- **News:** breaking news, artykuły analityczne, wywiady z zarządem
- **Tavily:** wyniki wyszukiwania, zmiana sentymentu w wynikach

**Zdarzenia (11):**
41.1–41.3, 42.1–42.3, 43.1–43.3, 44.1–44.2

---

### 2.11 System Event Detector

| Atrybut | Opis |
|---------|------|
| **Właściciel** | Wszystkie silniki (Multi-Engine) |
| **Źródło danych** | Wszystkie dostępne źródła |

**Wejście:**
- Wszystkie zdarzenia z pozostałych detektorów
- Historia zdarzeń ALCHEMIKA (HistoryRepository)
- Dane międzyinstrumentowe
- Kalendarz

**Wyjście:**
- Zdarzenia systemowe:
  - `COMPOSITE_EVENT` — kombinacja kilku zdarzeń jednocześnie
  - `INSTRUMENT_STATE_CHANGE` — zmiana stanu instrumentu
  - `EVENT_RECURRENCE` — powtórne wykrycie zdarzenia
  - `SECTOR_ROTATION` / `CORRELATION_BREAKDOWN` — zdarzenia międzyinstrumentowe i sektorowe
  - `EARNINGS_SEASON` — zdarzenia kalendarzowe

**Odpowiedzialność:**
- **Alerty własne ALCHEMIKA:** wykrywanie zdarzeń złożonych, zmiana stanu instrumentu, powtórzenia
- **Zdarzenia międzyinstrumentowe:** anomalie spreadu, lider vs followers
- **Zdarzenia sezonowe:** efekt końca miesiąca/kwartału, triple witching, efekt stycznia, sezon wyników
- **Sektor:** rotacja sektorowa, zmiana regulacji, bankructwo lidera
- **Korelacje:** rozpad i wzmocnienie korelacji

**Zdarzenia (12):**
45.1–45.3, 46.1–46.2, 47.1–47.4, 34.1–34.3, 35.1–35.2

---

## 3. SCALANIE WYKRYTYCH ZDARZEŃ

Po uruchomieniu wszystkich detektorów, system scala wykryte zdarzenia w spójną listę. Proces scalania realizowany jest przez **MasterEngine** (koordynator) i **System Event Detector** (łącznik kontekstowy).

### 3.1 Normalizacja

Każde zdarzenie, niezależnie od źródła, otrzymuje ujednoliconą strukturę:

```
Zdarzenie:
  - id: unikalny identyfikator
  - typ: np. PRICE_SURGE, VOLUME_SPIKE
  - instrument: symbol instrumentu
  - grupa: [GPW] | [USA] | [ETF]
  - timestamp: czas wykrycia
  - źródło: TechnicalEngine | AnalystEngine | NewsEngine | AIEngine | ...
  - detektor: Price Event Detector | Volume Event Detector | ...
  - priorytet_surowy: Krytyczny | Wysoki | Średni | Niski (wg Katalogu Zdarzeń)
  - wartości: map[string]float (np. zmiana_procentowa, krotność_wolumen)
  - kontekst: opcjonalny opis okoliczności
```

### 3.2 Usuwanie duplikatów

Duplikaty powstają gdy to samo zdarzenie jest wykryte przez różne detektory lub wielokrotnie w tym samym oknie czasowym.

**Reguły deduplikacji:**

1. **Deduplikacja czasowa** — jeśli ten sam typ zdarzenia dla tego samego instrumentu został wykryty w ciągu ostatnich N minut, tylko pierwsze wystąpienie jest zachowywane. Realizowane przez `OpportunityDeduplicator` z konfigurowalnym oknem czasowym (`deduplication_window_seconds`).

2. **Deduplikacja typów pokrewnych** — zdarzenia częściowo się pokrywające:
   - `VOLATILITY_SPIKE` (3.1) i `ATR_EXPANSION` (8.3) — oba mierzą wzrost zmienności; zachowywane jest zdarzenie o wyższym priorytecie, drugie może być dołączone jako kontekst
   - `BB_EXPANSION` (3.3) i `VOLATILITY_SPIKE` (3.1) — zachowywane jako osobne (BB Expansion niesie dodatkową informację o początku trendu)
   - `ATH` (1.7) i `RESISTANCE_BREAKOUT` (4.1) — zachowywane jako osobne (ATH ma znaczenie psychologiczne wykraczające poza techniczne)

3. **Deduplikacja przez OpportunityDeduplicator** — warstwa aplikacyjna (`application/opportunity_deduplicator.py`):
   - Generuje deterministyczny hash na podstawie symbol + typ rekomendacji + timestamp
   - Sprawdza, czy ten sam hash nie był już przetwarzany w oknie deduplikacji
   - Jeśli był → `should_process()` zwraca `False` → instrument pomijany

### 3.3 Łączenie podobnych zdarzeń

Zdarzenia tego samego typu lub pokrewne, występujące jednocześnie, są łączone w zdarzenia złożone (Composite Events):

**Przykłady łączenia:**
- `PRICE_SURGE` + `VOLUME_SPIKE` → zdarzenie złożone: "Silny wzrost na wysokim wolumenie"
- `EARNINGS_RELEASE` + `PRICE_SURGE` → zdarzenie złożone: "Pozytywna reakcja na wyniki"
- `BREAKING_NEWS` + `PRICE_DROP` → zdarzenie złożone: "Negatywny news powodujący przecenę"

**Reguły łączenia:**
- Zdarzenia muszą dotyczyć tego samego instrumentu
- Odstęp czasowy między zdarzeniami < próg (np. 5 minut)
- Zdarzenie złożone dziedziczy najwyższy priorytet spośród zdarzeń składowych

### 3.4 Przypisanie priorytetów

Końcowy priorytet zdarzenia jest wyliczany jako funkcja:

```
priorytet_końcowy = f(priorytet_surowy, grupa_instrumentu, liczba_zdarzeń_składowych, powtarzalność)
```

- **Priorytet surowy** — zdefiniowany w Katalogu Zdarzeń (Krytyczny / Wysoki / Średni / Niski)
- **Grupa instrumentu** — zdarzenia Krytyczne dla danej grupy (oznaczone ★ w tabeli klasyfikacji) otrzymują podbicie priorytetu
- **Liczba zdarzeń składowych** — zdarzenia złożone (Composite Events) mają wyższy priorytet niż pojedyncze
- **Powtarzalność** — zdarzenie wykryte ponownie w krótkim czasie (Event Recurrence) ma podbity priorytet

### 3.5 Przypisanie źródła wykrycia

Każde zdarzenie ma przypisane jednoznaczne źródło:

| Detektor | Silnik odpowiedzialny |
|----------|----------------------|
| Price Event Detector | TechnicalEngine |
| Volume Event Detector | TechnicalEngine |
| Technical Event Detector | TechnicalEngine |
| Fundamental Event Detector | AnalystEngine (+ NewsEngine) |
| Corporate Event Detector | NewsEngine (+ AnalystEngine, AIEngine) |
| Regulatory Event Detector | NewsEngine (+ AIEngine) |
| Macro Event Detector | NewsEngine (+ AnalystEngine, AIEngine, TechnicalEngine) |
| ETF Event Detector | AnalystEngine (+ NewsEngine) |
| Derivatives Event Detector | AnalystEngine (+ TechnicalEngine) |
| Sentiment & News Event Detector | NewsEngine (+ AIEngine) |
| System Event Detector | Wszystkie silniki |

---

## 4. OCENA JAKOŚCI ZDARZEŃ

Każde zdarzenie po scaleniu otrzymuje ocenę jakości w pięciostopniowej skali.

### 4.1 Skala oceny jakości

| Poziom | Opis | Akcja |
|--------|------|-------|
| **Critical** | Zdarzenie o najwyższym priorytecie, potwierdzone przez wiele źródeł, wymagające natychmiastowej uwagi | Pełna analiza + AI + Tavily + Alert |
| **High** | Istotne zdarzenie, pojedyncze lub złożone, z wysoką wiarygodnością | Analiza rozszerzona + AI (jeśli spełnia kryteria) + potencjalny Alert |
| **Medium** | Umiarkowanie istotne zdarzenie, brak potwierdzenia z innych źródeł | Analiza podstawowa, bez AI (chyba że kryteria spełnione), bez alertu |
| **Low** | Nisko istotne zdarzenie, informacyjne | Rejestracja w historii, brak dalszej analizy |
| **Ignore** | Zdarzenie nieistotne, fałszywy sygnał, szum | Pominięcie, brak rejestracji |

### 4.2 Kryteria przechodzenia pomiędzy poziomami

#### Critical ← High

Zdarzenie **High** staje się **Critical** gdy spełniony jest co najmniej jeden warunek:

- Zdarzenie jest zdarzeniem złożonym (Composite Event) — co najmniej 2 niezależne detektory wykryły zdarzenia dla tego samego instrumentu
- Zdarzenie ma priorytet Krytyczny w Katalogu Zdarzeń (np. Price Surge, Volume Spike, Support Breakdown, Earnings Release, Short Squeeze)
- Zdarzenie dotyczy grupy instrumentów, dla której jest szczególnie istotne (oznaczone ★ — np. Volume Spike dla GPW, Short Squeeze dla USA)
- Ten sam typ zdarzenia został wykryty dla tego instrumentu po raz kolejny w oknie 24h (Event Recurrence)
- Zdarzenie dotyczy instrumentu, który już jest w stanie "monitorowany" lub "alarmowy"

#### High ← Medium

Zdarzenie **Medium** staje się **High** gdy:

- Zdarzenie otrzymało potwierdzenie z innego źródła (np. Price Surge potwierdzony przez Volume Spike)
- Zdarzenie dotyczy grupy instrumentów, dla której jest istotne (oznaczone ✓ w tabeli)
- Wartości przekraczają próg istotności specyficzny dla grupy instrumentu (np. 5% ruch na groszówce GPW może być High, podczas gdy na ETF dopiero 2%)
- Zdarzenie występuje w kontekście innego zdarzenia (np. Gap Up w dniu publikacji wyników)

#### Medium ← Low

Zdarzenie **Low** staje się **Medium** gdy:

- Drugi detektor wykrył osobne (nieskorelowane) zdarzenie dla tego samego instrumentu
- Zdarzenie dotyczy instrumentu, który normalnie jest mało aktywny (ożywienie na nisko-płynnym instrumencie)

#### Ignore ← Low

Zdarzenie **Low** staje się **Ignore** (odrzucane) gdy:

- Wartości są poniżej minimalnego progu (np. ruch 0.1% zamiast 5%)
- Wolumen jest poniżej minimalnego progu płynności
- Instrument jest na liście wykluczeń
- Dane są niekompletne lub błędne
- Zdarzenie jest duplikatem (już przetworzone w oknie deduplikacji)

### 4.3 Agregacja wielu ocen

Gdy dla jednego instrumentu wykryto wiele zdarzeń o różnych poziomach jakości:

- Końcowy poziom = max(poziomy wszystkich zdarzeń) + podbicie za liczbę zdarzeń
- 1 zdarzenie Medium → Medium
- 2 zdarzenia Medium → High
- 1 zdarzenie High + 1 Medium → Critical
- 3+ zdarzeń Medium → High

---

## 5. MOMENT POBIERANIA NEWS

### Kiedy system powinien pobierać wiadomości

System pobiera wiadomości za pośrednictwem `NewsPipeline.process([symbol])` w następujących przypadkach:

1. **Zawsze dla zdarzeń Critical i High** — każde zdarzenie o poziomie Critical lub High automatycznie uruchamia pobranie newsów dla danego instrumentu, aby dostarczyć kontekst i wyjaśnienie przyczyny ruchu.

2. **Dla zdarzeń fundamentalnych** — każde zdarzenie z Fundamental Event Detector (np. Earnings Release, Guidance Update) automatycznie wymaga pobrania newsów w celu weryfikacji i uzupełnienia danych.

3. **Dla zdarzeń korporacyjnych** — Corporate Event Detector opiera się głównie na NewsEngine, więc pobranie newsów jest integralną częścią wykrywania.

4. **Gdy TechnicalEngine wykryje anomalie** — skok ceny, skok wolumenu, wybicie z formacji → potrzebny jest kontekst newsowy do wyjaśnienia przyczyny.

5. **Na żądanie System Event Detector** — gdy system wykryje nietypową kombinację zdarzeń, może zażądać pobrania dodatkowych newsów.

### Kiedy nie ma to sensu

1. **Zdarzenia Low i Ignore** — niska istotność nie uzasadnia kosztu pobierania i przetwarzania newsów.

2. **Brak nowych zdarzeń** — jeśli dla instrumentu nie wykryto żadnych nowych zdarzeń, pobieranie newsów jest zbędne.

3. **Zdarzenia czysto techniczne bez kontekstu** — np. pojedynczy Doji bez innych sygnałów. Sam wzór świecowy rzadko wymaga newsów do interpretacji.

4. **ETF z normalnym zachowaniem** — ETF śledzące indeksy, bez odchyleń od NAV, bez nietypowych przepływów.

5. **Duplikat w oknie deduplikacji** — jeśli instrument był już analizowany w ostatnim oknie czasowym.

6. **Instrument wykluczony** — instrument na liście wykluczeń.

7. **Poza godzinami handlu dla danego rynku** — chyba że zdarzenie dotyczy after-hours (np. earnings release po sesji).

---

## 6. MOMENT UŻYCIA TAVILY

Tavily (`data/tavily/`) wykonuje wyszukiwanie w internecie w czasie rzeczywistym. Jest zasobem zewnętrznym (API), więc jego użycie powinno być uzasadnione.

### Jakie zdarzenia uzasadniają wykonanie wyszukiwania Tavily

1. **Zdarzenia Critical** — każde zdarzenie o poziomie Critical może wymagać szerszego kontekstu, którego nie dostarczają standardowe źródła. Tavily może znaleźć informacje spoza standardowych kanałów (np. lokalne media, blogi, fora).

2. **Zdarzenia korporacyjne wymagające weryfikacji** — np. plotki o fuzji/przejęciu (22.2), odejście kluczowego pracownika (27.4), postępowanie regulacyjne (25.1).

3. **Zdarzenia geopolityczne i makro** — konflikty zbrojne (33.1), sankcje (33.2), wybory (33.3), umowy handlowe (33.4), szoki podażowe (32.2) — Tavily dostarcza najświeższych informacji.

4. **Zdarzenia sentymentowe** — breaking news (43.1), artykuły analityczne (43.2), wywiady z zarządem (43.3).

5. **Gdy NewsEngine nie zwrócił wyników** — jeśli standardowe źródła newsów nie zawierają informacji o zdarzeniu Critical lub High, Tavily jest uruchamiane jako fallback.

6. **Na żądanie AIEngine** — gdy AI w trakcie analizy stwierdzi, że potrzebuje dodatkowych informacji z internetu.

7. **Dla zdarzeń złożonych (Composite Events)** — kombinacja zdarzeń technicznych i fundamentalnych może wymagać wyszukania kontekstu.

### Kiedy Tavily nie powinno być uruchamiane

1. **Zdarzenia Low, Medium, Ignore** — koszt API nieuzasadniony przy niskiej istotności.

2. **Zdarzenia czysto techniczne** — sygnały ze wskaźników technicznych (RSI, MACD, Bollinger) nie wymagają wyszukiwania w internecie.

3. **Gdy NewsEngine dostarczył wystarczający kontekst** — nie ma potrzeby duplikowania informacji.

4. **Dla ETF** — chyba że zdarzenie dotyczy likwidacji ETF lub nietypowego odchylenia od NAV.

5. **Gdy limit API został wyczerpany** — Tavily ma limity, system musi je respektować.

6. **Instrument nieaktywny / niska płynność** — koszt wyszukiwania nieuzasadniony.

---

## 7. MOMENT UŻYCIA AI

AI (Artificial Intelligence) w ALCHEMIKU **nie analizuje wszystkiego**. AI uruchamia się wyłącznie w ściśle określonych przypadkach. Odpowiada za to `DecisionEngine` w `engines/ai/`, który łączy dane z TechnicalEngine i NewsPipeline oraz przekazuje je do PromptBuildera i AIProvidera.

### Filozofia użycia AI

> AI interpretuje zebrane dane, ale nie podejmuje decyzji inwestycyjnych.

AI jest kosztownym zasobem (czas, tokeny, koszt API) i powinno być używane tylko wtedy, gdy rzeczywiście wnosi wartość dodaną ponad analizę matematyczną i techniczną.

### Szczegółowe kryteria uruchomienia AI

AI uruchamia się **wyłącznie** gdy spełnione są **wszystkie** poniższe warunki:

#### A. Zdarzenie ma odpowiedni priorytet

- Poziom jakości zdarzenia: **Critical** LUB **High** (z dodatkowym warunkiem)
  - Dla **Critical**: AI zawsze
  - Dla **High**: AI tylko gdy spełniony jest dodatkowy warunek B, C lub D

#### B. Zdarzenie wymaga interpretacji

AI jest potrzebne gdy charakter zdarzenia wymaga rozumienia kontekstu, a nie tylko analizy liczbowej:

- Zdarzenia typu: Earnings Beat/Miss, Guidance Update, M&A Announcement, CEO Change, Regulatory Investigation
- Zdarzenia złożone (Composite Events) — połączenie sygnałów technicznych z fundamentalnymi
- Zdarzenia, gdzie wartości są na granicy progów i potrzebna jest ocena kontekstowa

**AI NIE jest potrzebne gdy:**
- Zdarzenie jest jednoznacznie liczbowe (np. Price Surge +15% — fakt jest jasny, nie wymaga interpretacji)
- Zdarzenie jest czysto techniczne i potwierdzone przez matematykę (np. MA Crossover + RSI potwierdzenie)

#### C. Zdarzenie wymaga połączenia wielu źródeł

AI jest potrzebne gdy informacje pochodzą z rozproszonych źródeł i muszą być zsyntetyzowane:

- Zdarzenie techniczne + zdarzenie fundamentalne + news → AI łączy w spójną narrację
- Sygnały z różnych detektorów są sprzeczne (np. Price Surge + Bearish Engulfing) → AI ocenia, który sygnał jest silniejszy
- Zdarzenie dotyczy kontekstu makro + spółki (np. decyzja o stopach + wpływ na konkretną spółkę)

#### D. Zdarzenie może wpłynąć na decyzję inwestycyjną

AI jest potrzebne gdy wynik analizy może realnie wpłynąć na decyzję inwestora:

- Zdarzenie zmienia obraz fundamentalny spółki (np. nowy kontrakt, zerwanie kontraktu, pozew)
- Zdarzenie ma charakter precedensowy (np. pierwsze ATH od lat)
- Zdarzenie występuje na instrumencie z już istniejącą historią alertów (kontynuacja narracji)

### Kiedy AI na pewno NIE jest uruchamiane

1. **Zdarzenia Low, Medium, Ignore** — niezależnie od typu
2. **Pojedyncze zdarzenia techniczne bez kontekstu** — np. sam RSI Oversold, sam Doji
3. **Pierwsze wystąpienie zdarzenia bez potwierdzenia** — pojedynczy sygnał z jednego detektora
4. **Zdarzenia na ETF bez istotnych odchyleń** — ETF zachowujący się zgodnie z indeksem
5. **Instrumenty z listy wykluczeń**
6. **Gdy ten sam instrument był już analizowany przez AI w bieżącym oknie** — chyba że pojawiło się nowe zdarzenie Critical

---

## 8. MASTERENGINE

`MasterEngine` (`engines/master/engine.py`) jest centralnym koordynatorem przepływu analizy dla jednego instrumentu. Organizuje sekwencyjne wykonanie wszystkich silników.

### 8.1 Jakie dane otrzymuje

MasterEngine otrzymuje od `RuntimeService`:

- **Symbol instrumentu** (string) — pojedynczy ticker do analizy
- **Wynik MarketScanner / HunterEngine** — pośrednio, poprzez RuntimeService który iteruje po kandydatach z `hunter_result.opportunities`

### 8.2 Jakie decyzje podejmuje

MasterEngine **nie podejmuje decyzji analitycznych**. Jego odpowiedzialnością jest **orkiestracja** — wywołanie silników w odpowiedniej kolejności i przekazanie danych między nimi.

Sekwencja wykonania (`MasterEngine.run_analysis(symbol)`):

```
1. Walidacja symbolu                    → ValueError jeśli niepoprawny
2. TechnicalEngine.analyze([symbol])    → wynik techniczny
3. NewsPipeline.process([symbol])       → wynik newsowy
4. DecisionEngine.process_data(...)     → łączy technical + news → AISignal
5. RankingEngine.calculate_ranking(...) → ocenia ranking
6. RiskEngine.assess_risk(...)          → ocenia ryzyko
7. HunterEngine.scan(...)               → skanuje z metadanymi ryzyka i rankingu
8. AnalystEngine.generate_analysis(...) → generuje końcową analizę
```

### 8.3 Jakie dane przekazuje dalej

MasterEngine zwraca `FinalAnalysisResult` zawierający:
- `symbol` — symbol instrumentu
- `final_rating` — końcowa ocena
- `confidence_level` — poziom pewności
- `recommendation` — rekomendacja (np. STRONG_BUY, BUY)
- `positive_factors` — pozytywne czynniki
- `risk_factors` — czynniki ryzyka
- `warnings` — ostrzeżenia
- `summary` — podsumowanie analizy
- `generated_at` — timestamp

Ten wynik trafia z powrotem do `RuntimeService`, który przekazuje go do:
- `AlertBuilder` (decyzja o alercie)
- `HistoryRepository` (zapis w historii)

---

## 9. DECISIONENGINE

`DecisionEngine` (`engines/ai/decision_engine.py`) jest mostem między analizą techniczną/newsową a AI. **Nie implementuje jeszcze logiki decyzyjnej** — obecnie jest to placeholder.

### 9.1 Kiedy podejmuje decyzję (stan docelowy)

DecisionEngine podejmuje decyzję o uruchomieniu AI na podstawie kryteriów opisanych w sekcji 7:

- Otrzymuje wyniki z TechnicalEngine i NewsPipeline
- Sprawdza priorytet i poziom jakości zdarzeń
- Decyduje, czy przekazać dane do AIProvidera i PromptBuildera

### 9.2 Kiedy kończy analizę

DecisionEngine kończy analizę gdy:

1. **Kryteria AI nie są spełnione** — zwraca wynik bez analizy AI (tylko dane techniczne i newsowe)
2. **AIProvider zwrócił wynik** — łączy wyniki AI z danymi technicznymi/newsowymi
3. **Wystąpił błąd** — zwraca `RuntimeError`

### 9.3 Kiedy przekazuje do RiskEngine

DecisionEngine **nie przekazuje bezpośrednio do RiskEngine**. Przepływ jest następujący:

```
DecisionEngine → AISignal
    → RankingEngine.calculate_ranking(aisignal) → FullRanking
        → RiskEngine.assess_risk(analysis_result, ranking_result) → RiskResult
```

RiskEngine otrzymuje dane po przejściu przez RankingEngine.

---

## 10. RISKENGINE

`RiskEngine` (`engines/risk/engine.py`) ocenia ryzyko związane z instrumentem na podstawie wyników analizy i rankingu.

### 10.1 Kiedy zatwierdza alert

RiskEngine **nie zatwierdza ani nie blokuje alertów bezpośrednio**. Decyzja o wysłaniu alertu jest podejmowana przez `AlertBuilder.should_alert()` na podstawie `FinalAnalysisResult`.

RiskEngine dostarcza **dane o ryzyku**, które są jednym z czynników w `FinalAnalysisResult`:

- `risk_score` — wynik ryzyka (0.0–1.0)
- `risk_level` — LOW / MEDIUM / HIGH / CRITICAL
- `risk_factors` — lista czynników ryzyka
- `max_position_size` — rekomendowana maksymalna wielkość pozycji
- `stop_loss` — sugerowany poziom stop loss
- `take_profit` — sugerowany poziom take profit

Te dane są uwzględniane przez `AnalystEngine` przy generowaniu końcowej rekomendacji.

### 10.2 Kiedy blokuje alert

RiskEngine może pośrednio wpłynąć na blokadę alertu poprzez:

- **risk_level = CRITICAL** → `AnalystEngine` może obniżyć rekomendację do HOLD lub SELL
- **risk_score > próg** → `AlertBuilder` (przy `recommendation not in allowed_recommendations`) nie wyśle alertu
- **risk_factors zawiera dyskwalifikujące czynniki** — np. ryzyko bankructwa, zawieszenie notowań

Bezpośrednia blokada alertu nie jest obecnie implementowana w RiskEngine — należy do `AlertBuilder`.

### 10.3 Kiedy wymaga dodatkowych danych

RiskEngine wymaga dodatkowych danych gdy:

1. **Konfiguracja nie jest załadowana** — `config_path` jest None, używana jest domyślna konfiguracja
2. **Dane wejściowe są niekompletne** — brak `analysis_result` lub `ranking_result`
3. **confidence jest niskie** — gdy pewność oceny jest poniżej akceptowalnego progu, RiskEngine może zwrócić `confidence` < próg, co wpłynie na końcową ocenę `AnalystEngine`

---

## 11. TELEGRAM

Wysyłanie alertów przez Telegram jest realizowane przez:
- `AlertBuilder` (`application/alert_builder.py`) — decyduje, czy alert powinien być wysłany i buduje komunikat
- `AlertDispatcher` (`application/alert_dispatcher.py`) — wysyła komunikat kanałami (w tym Telegram)
- `TelegramChannel` (`application/channels/telegram_channel.py`) — integracja z Telegram API

### 11.1 Warunki wysłania alertu

Alert jest wysyłany gdy spełnione są **wszystkie** poniższe warunki (`AlertBuilder.should_alert()`):

1. **`final_rating ≥ min_final_score`** — końcowa ocena (w skali 0–100) ≥ 70 (domyślnie)
2. **`confidence_level ≥ min_confidence`** — poziom pewności ≥ 70% (domyślnie)
3. **`recommendation in allowed_recommendations`** — rekomendacja to STRONG_BUY lub BUY (domyślnie)

Dodatkowe warunki kontekstowe:

4. **Instrument nie jest na liście wykluczeń**
5. **Alert nie jest duplikatem** — `OpportunityDeduplicator` sprawdza, czy ten sam instrument nie był już alertowany w oknie deduplikacji
6. **Komponenty alertowe są skonfigurowane** — `alert_builder` i `alert_dispatcher` nie są None

### 11.2 Zawartość komunikatu

Komunikat alertu (`AlertBuilder.build_alert()`) zawiera:

```
Symbol: [symbol]
Recommendation: [STRONG_BUY / BUY]
Score: [final_rating]
Confidence: [confidence_level]%
Summary: [podsumowanie analizy]
```

`AlertBuilder.format_message()` formatuje te dane do czytelnej postaci tekstowej.

### 11.3 Kiedy alert nie powinien zostać wysłany

Alert **nie** jest wysyłany w następujących przypadkach:

1. **`final_rating < min_final_score`** — wynik poniżej progu
2. **`confidence_level < min_confidence`** — zbyt niska pewność
3. **`recommendation not in allowed_recommendations`** — rekomendacja to HOLD, SELL, STRONG_SELL
4. **Brak komponentów alertowych** — `alert_builder` lub `alert_dispatcher` jest None
5. **Duplikat** — instrument był już alertowany w oknie deduplikacji
6. **Wynik jest Exception** — błąd w MasterEngine
7. **RiskEngine zwrócił CRITICAL** — domyślnie nie blokuje wysyłki, ale może wpłynąć na recommendation

---

## 12. PRZERWANIE ANALIZY

System może przerwać analizę na różnych etapach cyklu. Poniżej opisano wszystkie przypadki wcześniejszego zakończenia.

### 12.1 Brak danych

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| MarketScanner | Brak kandydatów spełniających kryteria | `candidates_count = 0`, cykl kończy się z `success_count = 0` |
| YahooFetcher | Brak danych OHLCV dla symbolu | Wyjątek → `CandidateError(stage="Master Engine")` |
| YahooFetcher | Dane niekompletne (brak pól OHLCV) | Walidacja nie przechodzi → instrument odrzucony |

### 12.2 Zbyt mały wolumen

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| TechnicalEngine | Wolumen poniżej minimalnego progu płynności | Volume Event Detector może zgłosić Near-Zero Volume, ale instrument nie jest automatycznie odrzucany — decyzja należy do konfiguracji progów |
| Ocena jakości | Wolumen < próg dla danej grupy instrumentu | Poziom jakości obniżony do Low/Ignore |

### 12.3 Brak nowych zdarzeń

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| Wszystkie detektory | Żaden detektor nie wykrył zdarzenia | Pusta lista zdarzeń → ocena jakości = Ignore → instrument pomijany |
| OpportunityDeduplicator | Wszystkie zdarzenia są duplikatami | `should_process()` zwraca False → instrument pomijany |

### 12.4 Duplikat

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| RuntimeService | `deduplicator.should_process(instrument_id)` zwraca False | Instrument pomijany przed wejściem do MasterEngine |
| OpportunityDeduplicator | Ten sam hash w oknie deduplikacji | `is_duplicate()` → True → pominięcie |

### 12.5 Instrument wykluczony

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| Uniwersum | Instrument nie znajduje się w liście dozwolonych | Nie pojawia się jako kandydat |
| Statyczna lista | Instrument na liście wykluczeń | MarketScanner nie zwraca go jako kandydata |

### 12.6 ETF bez istotnych zmian

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| ETF Event Detector | Brak odchylenia od NAV, brak nietypowych przepływów, brak zmian składu | Brak zdarzeń ETF → tylko zdarzenia techniczne mogą uruchomić analizę |
| Ocena jakości | ETF zachowuje się zgodnie z indeksem bazowym | Zdarzenia techniczne obniżone do Medium/Low |

### 12.7 Błędne dane

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| Walidacja | Symbol jest pusty lub nie jest stringiem | `ValueError` w `MasterEngine.run_analysis()` → `CandidateError` |
| Walidacja | Dane OHLCV zawierają wartości null | Instrument odrzucony |
| Walidacja | high < low lub inne niespójności | Instrument odrzucony |
| Silniki | Wyjątek w dowolnym silniku | `CandidateError` z nazwą etapu |

### 12.8 Błędy w silnikach

| Etap | Warunek | Zachowanie |
|------|---------|------------|
| Każdy silnik | Wyjątek podczas przetwarzania | Wyjątek propagowany do `RuntimeService` → `CandidateError` → przejście do następnego kandydata |
| RuntimeService | Wyjątek na poziomie skanera | `CycleReport` z `error_count > 0` |

---

## 13. DIAGRAM ASCII

Poniższy diagram przedstawia kompletny cykl życia zdarzenia rynkowego — od pobrania danych do wysłania alertu Telegram.

```
================================================================================
                    ALCHEMIK — PEŁEN CYKL ŻYCIA ZDARZENIA RYNKOWEGO
================================================================================

[START CYKLU]
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. POBIERANIE DANYCH                                                     │
│    RuntimeService.run_cycle()                                            │
│                                                                          │
│    ┌──────────────────┐     ┌──────────────────┐                         │
│    │  MarketScanner   │ OR  │  HunterEngine    │                         │
│    │  (skanowanie     │     │  (dane statyczne │                         │
│    │   rynku)         │     │   lub wejściowe) │                         │
│    └────────┬─────────┘     └────────┬─────────┘                         │
│             │                        │                                   │
│             └───────────┬────────────┘                                   │
│                         ▼                                                │
│              Lista kandydatów (instrumenty)                              │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 2. WALIDACJA DANYCH                 PRZERWANIE:                          │
│    - Kompletność OHLCV              • Brak danych                        │
│    - Aktualność                     • Błędne dane                        │
│    - Spójność pól                   • Symbol pusty/null                  │
│    - Symbol poprawny                                                    │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 3. KLASYFIKACJA INSTRUMENTU          PRZERWANIE:                          │
│    ┌─────────┐ ┌─────────┐ ┌─────┐  • Instrument wykluczony             │
│    │  [GPW]  │ │  [USA]  │ │[ETF]│                                      │
│    └────┬────┘ └────┬────┘ └──┬──┘                                      │
│         │           │         │                                          │
│         ▼           ▼         ▼                                          │
│    Determinuje, które detektory są uruchamiane                           │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 4. PRZYGOTOWANIE DANYCH DLA SILNIKÓW                                    │
│    - OHLCV → TechnicalEngine                                            │
│    - Symbol → NewsPipeline                                              │
│    - Kandydaci z metadanymi → HunterEngine                              │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 5. URUCHAMIANIE DETEKTORÓW                                              │
│                                                                          │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────┐ │
│  │ Price Event       │  │ Volume Event      │  │ Technical Event      │ │
│  │ Detector          │  │ Detector          │  │ Detector             │ │
│  │ (10 zdarzeń)      │  │ (5 zdarzeń)       │  │ (34 zdarzenia)       │ │
│  │ → TechnicalEngine │  │ → TechnicalEngine │  │ → TechnicalEngine    │ │
│  └────────┬──────────┘  └────────┬──────────┘  └──────────┬───────────┘ │
│           │                      │                        │             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────┐ │
│  │ Fundamental Event │  │ Corporate Event   │  │ Regulatory Event     │ │
│  │ Detector          │  │ Detector          │  │ Detector             │ │
│  │ (24 zdarzenia)    │  │ (34 zdarzenia)    │  │ (3 zdarzenia)        │ │
│  │ → AnalystEngine   │  │ → NewsEngine      │  │ → NewsEngine         │ │
│  └────────┬──────────┘  └────────┬──────────┘  └──────────┬───────────┘ │
│           │                      │                        │             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────┐ │
│  │ Macro Event       │  │ ETF Event         │  │ Derivatives Event    │ │
│  │ Detector          │  │ Detector          │  │ Detector             │ │
│  │ (16 zdarzeń)      │  │ (4 zdarzenia)     │  │ (9 zdarzeń)          │ │
│  │ → NewsEngine      │  │ → AnalystEngine   │  │ → AnalystEngine      │ │
│  └────────┬──────────┘  └────────┬──────────┘  └──────────┬───────────┘ │
│           │                      │                        │             │
│  ┌──────────────────────┐  ┌──────────────────────────────────────────┐ │
│  │ Sentiment & News     │  │ System Event Detector (12 zdarzeń)        │ │
│  │ Event Detector       │  │ → Wszystkie silniki                       │ │
│  │ (11 zdarzeń)         │  │   Zdarzenia złożone, międzyinstrumentowe,  │ │
│  │ → NewsEngine         │  │   sezonowe, sektorowe, korelacje          │ │
│  └──────────┬───────────┘  └──────────────────┬───────────────────────┘ │
│             │                                 │                         │
└─────────────┼─────────────────────────────────┼─────────────────────────┘
              │                                 │
              ▼                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 6. SCALANIE WYKRYTYCH ZDARZEŃ          PRZERWANIE:                       │
│    - Normalizacja struktury            • Brak nowych zdarzeń             │
│    - Usuwanie duplikatów               • Zbyt mały wolumen               │
│    - Łączenie podobnych zdarzeń        • ETF bez istotnych zmian         │
│    - Przypisanie priorytetów           • Duplikat (Deduplicator)         │
│    - Przypisanie źródła wykrycia                                        │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 7. OCENA JAKOŚCI ZDARZEŃ                                                │
│                                                                          │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│    │ CRITICAL │  │  HIGH    │  │ MEDIUM   │  │   LOW    │  │ IGNORE   ││
│    │ Pełna    │  │ Analiza  │  │ Analiza  │  │ Tylko    │  │ Pominię- ││
│    │ analiza  │  │ rozsz.   │  │ podst.   │  │ historia │  │ cie      ││
│    │ + AI     │  │ + pot. AI│  │          │  │          │  │          ││
│    │ + Tavily │  │          │  │          │  │          │  │          ││
│    │ + Alert  │  │          │  │          │  │          │  │          ││
│    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
│         │             │             │             │             │       │
│         ▼             ▼             ▼             ▼             ▼       │
│      [KONTYNUUJ]  [KONTYNUUJ]  [KONTYNUUJ]     [STOP]        [STOP]    │
│                       │             │                                   │
│                       ▼             │                                   │
│              ┌─────────────────┐    │                                   │
│              │ News pobieranie │    │                                   │
│              │ (jeśli potrzebne)│   │                                   │
│              └────────┬────────┘    │                                   │
│                       │             │                                   │
│                       ▼             │                                   │
│              ┌─────────────────┐    │                                   │
│              │ Tavily          │    │                                   │
│              │ (jeśli spełnia  │    │                                   │
│              │  kryteria)      │    │                                   │
│              └────────┬────────┘    │                                   │
│                       │             │                                   │
└───────────────────────┼─────────────┼───────────────────────────────────┘
                        │             │
                        ▼             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 8. MASTERENGINE — ORKIESTRACJA (run_analysis)                            │
│                                                                          │
│    TechnicalEngine → NewsPipeline → DecisionEngine → RankingEngine      │
│    → RiskEngine → HunterEngine.scan() → AnalystEngine                   │
│                                                                          │
│    Wynik: FinalAnalysisResult                                           │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 9. DECISIONENGINE — DECYZJA O UŻYCIU AI                                 │
│                                                                          │
│    Czy zdarzenie ma priorytet Critical/High? ────NIE───→ [Pomiń AI]     │
│    │                                                                     │
│    TAK                                                                   │
│    │                                                                     │
│    Czy wymaga interpretacji / łączenia źródeł / wpływu na decyzję?       │
│    │                                                                     │
│    TAK───→ AIProvider.analyze() → PromptBuilder → AIResponse            │
│    NIE──→ [Pomiń AI]                                                     │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 10. RISKENGINE — OCENA RYZYKA                                            │
│                                                                          │
│     Wejście: AnalysisResult + FullRanking                               │
│     Wyjście: RiskResult (risk_score, risk_level, risk_factors,          │
│                          stop_loss, take_profit, max_position_size)      │
│                                                                          │
│     Ryzyko CRITICAL → może obniżyć rekomendację                         │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 11. ALERT BUILDER — DECYZJA O WYSŁANIU ALERTU                           │
│                                                                          │
│     should_alert(FinalAnalysisResult):                                   │
│       • final_rating >= min_final_score (70)?                           │
│       • confidence_level >= min_confidence (70)?                        │
│       • recommendation in [STRONG_BUY, BUY]?                            │
│       • nie duplikat?                                                    │
│                                                                          │
│     NIE───→ [STOP — brak alertu]                                        │
│     TAK                                                                  │
│       │                                                                  │
│       ▼                                                                  │
│     build_alert() → AlertMessage                                        │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 12. ALERT DISPATCHER — WYSYŁKA ALERTU                                   │
│                                                                          │
│     dispatch(AlertMessage)                                               │
│       │                                                                  │
│       ▼                                                                  │
│     TelegramChannel.send(alert)                                          │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     📱 TELEGRAM ALERT                           │    │
│  │                                                                 │    │
│  │  Symbol: XYZ                                                     │    │
│  │  Recommendation: STRONG_BUY                                     │    │
│  │  Score: 85.3                                                    │    │
│  │  Confidence: 92.0%                                              │    │
│  │  Summary: [podsumowanie analizy]                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 13. ZAPIS DO HISTORII                                                    │
│     HistoryRepository.save_cycle()                                       │
│     - Zapisuje CycleReport                                              │
│     - OpportunityDeduplicator.mark_processed()                           │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
[KONIEC CYKLU] ──────→ [Oczekiwanie na następny cykl (Scheduler)]
```

---

## 14. OCENA KOŃCOWA

### 14.1 Czy obecna architektura wystarcza

**TAK**, z zastrzeżeniami.

Obecna architektura ALCHEMIKA (7 silników: TechnicalEngine, NewsPipeline, DecisionEngine, RankingEngine, RiskEngine, HunterEngine, AnalystEngine + warstwa aplikacyjna z MarketScanner, Deduplicator, AlertBuilder, AlertDispatcher) **jest wystarczająca** do zrealizowania opisanego przepływu zdarzeń.

**Silne strony architektury:**
- Modułowa budowa z luźnym powiązaniem (zgodnie z INSTRUKCJA_DLA_CLINE.md)
- Jasno zdefiniowane Public API dla każdego silnika
- Istniejąca integracja z Yahoo Finance, News, Tavily, AI
- Działający pipeline od danych do alertu Telegram
- Deduplikacja i historia już zaimplementowane

**Zastrzeżenia:**
- DecisionEngine jest obecnie placeholderem — nie implementuje rzeczywistej logiki decyzyjnej
- Detektory zdarzeń (11 jednostek logicznych) nie są wydzielone jako osobne komponenty — ich logika jest rozproszona pomiędzy TechnicalEngine, AnalystEngine, NewsEngine
- Brakuje jawnego etapu "scalania zdarzeń" — obecnie każdy silnik działa sekwencyjnie, a zdarzenia nie są jawnie normalizowane i łączone
- Ocena jakości zdarzeń (Critical/High/Medium/Low/Ignore) nie jest jeszcze zaimplementowana

### 14.2 Czy przepływ jest spójny

**TAK.**

Przepływ od pobrania danych przez detekcję, scalanie, ocenę jakości, analizę, decyzję, ocenę ryzyka, aż do alertu Telegram **tworzy spójną i logiczną całość**.

- Każdy etap ma jasno zdefiniowane wejście i wyjście
- Przerwania analizy są opisane dla każdego etapu
- Kryteria użycia AI i Tavily są precyzyjne i minimalizują zbędne koszty
- System działa 24/7 z niezależnymi cyklami

### 14.3 Czy istnieją miejsca wymagające doprecyzowania przed implementacją

**TAK.** Następujące obszary wymagają doprecyzowania:

1. **DecisionEngine — brak implementacji.** Obecny DecisionEngine nie implementuje żadnej logiki poza placeholderem. Przed implementacją należy określić:
   - Jak dokładnie DecisionEngine otrzymuje informację o zdarzeniach (obecnie nie ma bezpośredniego połączenia z detektorami)?
   - Jak ocenia priorytet zdarzeń do decyzji o użyciu AI?
   - Jak łączy dane z TechnicalEngine i NewsPipeline z kryteriami opisanymi w sekcji 7?

2. **Detektory — struktura logiczna vs implementacja.** Detektory (Price Event, Volume Event, itd.) są zdefiniowane jako jednostki logiczne, ale nie mają wydzielonych komponentów w kodzie. Przed implementacją należy:
   - Zdecydować, czy detektory będą osobnymi klasami, modułami, czy funkcjami w ramach istniejących silników
   - Określić interfejs każdego detektora (wejście/wyjście)
   - Zdecydować o strategii rejestracji i wywoływania detektorów (registry pattern? hardcoded lista?)

3. **Scalanie zdarzeń — brak dedykowanego komponentu.** Etap scalania (normalizacja, deduplikacja, łączenie) jest opisany koncepcyjnie, ale nie ma go w architekturze. Przed implementacją należy:
   - Określić, który komponent jest odpowiedzialny za scalanie (MasterEngine? nowy komponent?)
   - Zdefiniować strukturę danych dla znormalizowanego zdarzenia
   - Określić algorytm łączenia podobnych zdarzeń

4. **Ocena jakości — konfigurowalne progi.** Poziomy jakości i kryteria przechodzenia między nimi wymagają konkretyzacji:
   - Jakie są liczbowe wartości progów dla każdej grupy instrumentów?
   - Gdzie przechowywana jest konfiguracja progów (config/?)
   - Jak aktualizować progi bez zmiany kodu?

5. **Tavily — limity API.** Przed implementacją należy określić:
   - Strategię zarządzania limitami API Tavily
   - Priorytetyzację zapytań (które zdarzenia mają pierwszeństwo gdy limit jest niski)

### 14.4 Czy można rozpocząć implementację bez zmian architektury

**TAK.**

Opisany przepływ może być zaimplementowany **bez modyfikacji istniejącej architektury i Public API silników**. Wszystkie zmiany mieszczą się w ramach:

1. **Rozszerzenia istniejących silników** o nowe metody wykrywające zdarzenia (w ramach ich obecnej odpowiedzialności)
2. **Implementacji DecisionEngine** zgodnie z jego obecnym interfejsem (`process_data(market_data) → AISignal`)
3. **Dodania logiki scalania i oceny jakości** jako nowego komponentu w warstwie `engines/` lub rozszerzenia `MasterEngine`
4. **Konfiguracji progów** w katalogu `config/`

Zasada z `docs/INSTRUKCJA_DLA_CLINE.md` i `docs/Hierarchia_Zdarzen_Rynkowych.md` jest zachowana:
- Nowe funkcjonalności są dodawane jako rozszerzenia
- Public API istniejących silników pozostaje niezmienione
- Komunikacja między silnikami odbywa się wyłącznie przez Public API

---

## KONIEC DOKUMENTU

Data utworzenia: 18.07.2026
Wersja: 1.0
Autor: Zespół ALCHEMIK
Status: Dokument projektowy — przepływ wykrywania zdarzeń rynkowych

Dokumenty powiązane:
- `docs/FILOZOFIA_EVENTOUTCOME.md` — opisuje filozofię odpowiedzialności modelu EventOutcome, który przechowuje rezultaty zdarzeń rynkowych po ich archiwizacji

Bazuje na:
- `docs/FILOZOFIA_ALCHEMIKA.md`
- `docs/Katalog_Zdarzen_Rynkowych.md` v2.0
- `docs/Hierarchia_Zdarzen_Rynkowych.md` v1.0
- `docs/Przeplyw_Danych.md`
- `struktura_alchemik.txt`
