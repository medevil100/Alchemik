# ALCHEMIK — HIERARCHIA ZDARZEŃ RYNKOWYCH

## DOKUMENT ARCHITEKTONICZNY

Data: 18.07.2026
Wersja: 1.0
Status: Dokument projektowy — nie implementacyjny

---

## SPIS TREŚCI

1. [Cel dokumentu](#1-cel-dokumentu)
2. [Metodologia klasyfikacji](#2-metodologia-klasyfikacji)
3. [Drzewo hierarchii zdarzeń](#3-drzewo-hierarchii-zdarzeń)
4. [Szczegółowa klasyfikacja każdego zdarzenia](#4-szczegółowa-klasyfikacja-każdego-zdarzenia)
5. [Mapowanie rodzin na przyszłe moduły](#5-mapowanie-rodzin-na-przyszłe-moduły)
6. [Tabela rodzin zdarzeń](#6-tabela-rodzin-zdarzeń)
7. [Analiza potencjału współdzielenia algorytmów](#7-analiza-potencjału-współdzielenia-algorytmów)
8. [Ocena katalogu](#8-ocena-katalogu)

---

## 1. CEL DOKUMENTU

Niniejszy dokument wprowadza **logiczną hierarchię** dla wszystkich zdarzeń rynkowych zdefiniowanych w `docs/Katalog_Zdarzen_Rynkowych.md` (wersja 2.0, ~157 zdarzeń).

**Nie tworzymy nowych zdarzeń.** Porządkujemy istniejące.

Hierarchia umożliwia:
- przypisanie każdego zdarzenia do **rodziny** (grupy logicznej),
- przypisanie rodziny do **przyszłego detektora** (modułu odpowiedzialnego za wykrywanie),
- identyfikację zdarzeń **podstawowych** (wykrywanych bezpośrednio z danych) i **pochodnych** (bazujących na innych zdarzeniach),
- identyfikację zdarzeń **współdzielących algorytmy**,
- określenie **właściciela** każdego zdarzenia w istniejącej architekturze silników ALCHEMIKA.

---

## 2. METODOLOGIA KLASYFIKACJI

Każde zdarzenie otrzymuje następujące atrybuty:

| Atrybut | Opis | Możliwe wartości |
|---------|------|------------------|
| **Rodzina** | Grupa logiczna zdarzeń | PRICE, VOLUME, TECHNICAL, FUNDAMENTAL, CORPORATE, REGULATORY, MACRO, ETF, DERIVATIVES, SENTIMENT, SYSTEM |
| **Kategoria** | Podgrupa w ramach rodziny | np. "Cenowe", "Wolumenowe", "Formacje świecowe" |
| **Podkategoria** | Jeszcze drobniejszy podział | np. "Luki", "Poziomy", "Świece pojedyncze" |
| **Podstawowe/Pochodne** | Czy zdarzenie jest wykrywane bezpośrednio z danych, czy wynika z innych zdarzeń | `podstawowe` / `pochodne` |
| **Współdzielony algorytm** | Czy zdarzenie może korzystać z tego samego algorytmu wykrywania co inne | Tak / Nie + wskazanie grupy |
| **Właściciel (silnik)** | Istniejący silnik ALCHEMIKA odpowiedzialny za wykrycie | TechnicalEngine, AnalystEngine, NewsEngine, AIEngine, HunterEngine, Multi-Engine |

---

## 3. DRZEWO HIERARCHII ZDARZEŃ

```
ZDARZENIA RYNKOWE (157)
│
├── PRICE (10)                              → Price Event Detector
│   ├── Nagły wzrost ceny (Price Surge)             [1.1]
│   ├── Nagły spadek ceny (Price Drop)              [1.2]
│   ├── Luka cenowa w górę (Gap Up)                 [1.3]
│   ├── Luka cenowa w dół (Gap Down)                [1.4]
│   ├── Nowe maksimum 52-tygodniowe (52W High)       [1.5]
│   ├── Nowe minimum 52-tygodniowe (52W Low)         [1.6]
│   ├── Nowe maksimum historyczne (ATH)              [1.7]
│   ├── Nowe minimum historyczne (ATL)               [1.8]
│   ├── Odrzucenie poziomu (Level Rejection)         [1.9]
│   └── Przekroczenie poziomu psychologicznego       [1.10]
│
├── VOLUME (5)                              → Volume Event Detector
│   ├── Skok wolumenu (Volume Spike)                 [2.1]
│   ├── Wolumen bliski zeru (Near-Zero Volume)       [2.2]
│   ├── Wolumen kumulacyjny (Cumulative Vol Anomaly) [2.3]
│   ├── Wolumen na spadkach (High Vol Down Days)     [2.4]
│   └── Wolumen na wzrostach (High Vol Up Days)      [2.5]
│
├── TECHNICAL (34)                          → Technical Event Detector
│   │
│   ├── ZMIENNOŚĆ (4)
│   │   ├── Wzrost zmienności (Volatility Spike)     [3.1]
│   │   ├── Spadek zmienności (Volatility Contraction)[3.2]
│   │   ├── Rozszerzenie wstęg Bollingera (BB Expand)[3.3]
│   │   └── Zwężenie wstęg Bollingera (BB Squeeze)   [3.4]
│   │
│   ├── WYBICIA TECHNICZNE (5)
│   │   ├── Wybicie powyżej oporu (Resistance Breakout)  [4.1]
│   │   ├── Wybicie poniżej wsparcia (Support Breakdown) [4.2]
│   │   ├── Wybicie z formacji trójkąta (Triangle)       [4.3]
│   │   ├── Wybicie z kanału (Channel Breakout)          [4.4]
│   │   └── Wybicie z flagi/chorągiewki (Flag/Pennant)   [4.5]
│   │
│   ├── FORMACJE ŚWIECOWE (10)
│   │   ├── Świece pojedyncze (4)
│   │   │   ├── Młot / Wisielec (Hammer/Hanging Man)     [5.1]
│   │   │   ├── Spadająca gwiazda / Odwrócony młot       [5.2]
│   │   │   ├── Doji                                       [5.5]
│   │   │   └── Marubozu                                   [5.9]
│   │   │
│   │   ├── Świece podwójne (2)
│   │   │   ├── Formacja objęcia hossy (Bullish Engulfing)[5.3]
│   │   │   └── Formacja objęcia bessy (Bearish Engulfing)[5.4]
│   │   │
│   │   └── Świece potrójne / złożone (4)
│   │       ├── Gwiazda poranna / wieczorna (Morning/Evening Star) [5.6]
│   │       ├── Trzech białych żołnierzy (Three White Soldiers)    [5.7]
│   │       ├── Trzy czarne kruki (Three Black Crows)              [5.8]
│   │       └── Harami                                              [5.10]
│   │
│   ├── TREND (5)
│   │   ├── Przecięcie średnich kroczących (MA Crossover)  [6.1]
│   │   ├── Zmiana kierunku MA (MA Slope Change)           [6.2]
│   │   ├── Cena powyżej/poniżej MA (Price vs MA)          [6.3]
│   │   ├── Seria wzrostowych/spadkowych świec              [6.4]
│   │   └── Zmiana struktury trendu (Trend Structure Change)[6.5]
│   │
│   ├── MOMENTUM (6)
│   │   ├── RSI — wykupienie (RSI Overbought)              [7.1]
│   │   ├── RSI — wyprzedanie (RSI Oversold)               [7.2]
│   │   ├── Dywergencja RSI (RSI Divergence)               [7.3]
│   │   ├── MACD — przecięcie linii (MACD Line Crossover)   [7.4]
│   │   ├── MACD — przecięcie zera (MACD Zero Cross)        [7.5]
│   │   └── Stochastic — wykupienie/wyprzedanie             [7.6]
│   │
│   └── WSKAŹNIKI TECHNICZNE (4)
│       ├── OBV — dywergencja (OBV Divergence)             [8.1]
│       ├── VWAP — odchylenie (VWAP Deviation)             [8.2]
│       ├── ATR — wzrost (ATR Expansion)                   [8.3]
│       └── Fibonacci — zniesienie (Fibonacci Hit)          [8.4]
│
├── FUNDAMENTAL (24)                        → Fundamental Event Detector
│   │
│   ├── WSKAŹNIKI FINANSOWE (6)
│   │   ├── Zmiana wskaźnika P/E (P/E Ratio Change)        [9.1]
│   │   ├── Zmiana wskaźnika P/BV (P/BV Ratio Change)      [9.2]
│   │   ├── Zmiana kapitalizacji rynkowej (Market Cap)      [9.3]
│   │   ├── Zmiana zadłużenia (Debt Change)                [9.4]
│   │   ├── Zmiana przychodów (Revenue Change)             [9.5]
│   │   └── Zmiana zysku netto (Net Income Change)         [9.6]
│   │
│   ├── WYNIKI FINANSOWE (4)
│   │   ├── Publikacja wyników kwartalnych (Earnings Release)[10.1]
│   │   ├── Wyniki powyżej oczekiwań (Earnings Beat)        [10.2]
│   │   ├── Wyniki poniżej oczekiwań (Earnings Miss)        [10.3]
│   │   └── Korekta prognoz (Guidance Update)              [10.4]
│   │
│   ├── RAPORTY (3)
│   │   ├── Publikacja raportu kwartalnego                  [11.1]
│   │   ├── Publikacja raportu rocznego                     [11.2]
│   │   └── Zmiana polityki rachunkowości                   [11.3]
│   │
│   ├── DYWIDENDY (4)
│   │   ├── Ogłoszenie dywidendy                            [14.1]
│   │   ├── Zmiana polityki dywidendowej                    [14.2]
│   │   ├── Dywidenda nadzwyczajna                          [14.3]
│   │   └── Dzień ustalenia prawa do dywidendy              [14.4]
│   │
│   ├── SPLITY (3)
│   │   ├── Ogłoszenie splitu                               [15.1]
│   │   ├── Wykonanie splitu                                [15.2]
│   │   └── Rewers splitu (Reverse Split)                   [15.3]
│   │
│   ├── EMISJE AKCJI (3)
│   │   ├── Ogłoszenie nowej emisji                         [16.1]
│   │   ├── Emisja z prawem poboru                          [16.2]
│   │   └── Emisja bez prawa poboru (Private Placement)     [16.3]
│   │
│   └── SKUP AKCJI WŁASNYCH (2)
│       ├── Ogłoszenie skupu akcji własnych                 [17.1]
│       └── Realizacja skupu                                [17.2]
│
├── CORPORATE (34)                          → Corporate Event Detector
│   │
│   ├── INSIDER TRADING (3)
│   │   ├── Transakcja insidera                             [18.1]
│   │   ├── Skup akcji przez insiderów                      [18.2]
│   │   └── Sprzedaż akcji przez insiderów                  [18.3]
│   │
│   ├── ZMIANY AKCJONARIATU (3)
│   │   ├── Przekroczenie progu                             [19.1]
│   │   ├── Wezwanie do sprzedaży akcji                     [19.2]
│   │   └── Zmiana znaczącego akcjonariusza                 [19.3]
│   │
│   ├── REKOMENDACJE I RATINGI (5)
│   │   ├── Nowa rekomendacja                               [20.1]
│   │   ├── Zmiana ceny docelowej                           [20.2]
│   │   ├── Podniesienie/obniżenie rekomendacji             [20.3]
│   │   ├── Zmiana ratingu kredytowego                      [21.1]
│   │   └── Zmiana perspektywy ratingu                      [21.2]
│   │
│   ├── FUZJE I PRZEJĘCIA (3)
│   │   ├── Ogłoszenie fuzji/przejęcia                      [22.1]
│   │   ├── Plotki o fuzji/przejęciu                        [22.2]
│   │   └── Zakończenie fuzji/przejęcia                     [22.3]
│   │
│   ├── KONTRAKTY (2)
│   │   ├── Podpisanie znaczącego kontraktu                 [23.1]
│   │   └── Zerwanie kontraktu                              [23.2]
│   │
│   ├── KWESTIE PRAWNE (8)
│   │   ├── Pozwy (2)
│   │   │   ├── Pozew przeciwko spółce                      [24.1]
│   │   │   └── Pozew złożony przez spółkę                  [24.2]
│   │   │
│   │   ├── Problemy regulacyjne (3)
│   │   │   ├── Postępowanie regulacyjne                    [25.1]
│   │   │   ├── Kara finansowa                              [25.2]
│   │   │   └── Zawieszenie notowań                         [25.3]
│   │   │
│   │   └── Upadłości i restrukturyzacje (3)
│   │       ├── Wniosek o upadłość                          [26.1]
│   │       ├── Restrukturyzacja                            [26.2]
│   │       └── Upadłość kontrahenta                        [26.3]
│   │
│   └── ZMIANY ZARZĄDU (4)
│       ├── Zmiana prezesa/CEO                              [27.1]
│       ├── Zmiana w zarządzie                              [27.2]
│       ├── Zmiana w radzie nadzorczej                      [27.3]
│       └── Odejście kluczowego pracownika                  [27.4]
│
├── REGULATORY (3)                           → Regulatory Event Detector
│   ├── Nowy komunikat ESPI                                [12.1]
│   ├── ESPI — opóźnienie publikacji                       [12.2]
│   └── Nowy komunikat EBI                                 [13.1]
│
├── MACRO (16)                               → Macro Event Detector
│   │
│   ├── MAKROEKONOMIA (3)
│   │   ├── Publikacja danych makro                         [28.1]
│   │   ├── Zmiana PKB                                     [28.2]
│   │   └── Zmiana bezrobocia                              [28.3]
│   │
│   ├── STOPY PROCENTOWE (3)
│   │   ├── Decyzja o stopach procentowych                  [29.1]
│   │   ├── Zmiana stóp poza posiedzeniem                   [29.2]
│   │   └── Zmiana forward guidance                         [29.3]
│   │
│   ├── INFLACJA (2)
│   │   ├── Publikacja danych o inflacji (CPI/PPI)          [30.1]
│   │   └── Inflacja powyżej/poniżej oczekiwań              [30.2]
│   │
│   ├── WALUTY (2)
│   │   ├── Silny ruch walutowy                             [31.1]
│   │   └── Interwencja walutowa                            [31.2]
│   │
│   ├── SUROWCE (2)
│   │   ├── Silny ruch cen surowca                          [32.1]
│   │   └── Szok podażowy                                   [32.2]
│   │
│   └── GEOPOLITYKA (4)
│       ├── Konflikt zbrojny / eskalacja                    [33.1]
│       ├── Sankcje                                         [33.2]
│       ├── Wybory / zmiana władzy                          [33.3]
│       └── Umowa handlowa                                  [33.4]
│
├── ETF (4)                                  → ETF Event Detector
│   ├── Zmiana składu ETF (ETF Rebalancing)                [36.1]
│   ├── Napływy/odpływy z ETF (ETF Flows)                  [36.2]
│   ├── Premia/dyskonto ETF (ETF Premium/Discount)         [36.3]
│   └── Likwidacja ETF (ETF Closure/Liquidation)           [36.4]
│
├── DERIVATIVES & ALTERNATIVE DATA (9)      → Derivatives Event Detector
│   │
│   ├── OPCJE (3)
│   │   ├── Nietypowa aktywność na opcjach                  [37.1]
│   │   ├── Zmiana implied volatility (IV Change)           [37.2]
│   │   └── Max Pain                                        [37.3]
│   │
│   ├── SHORT INTEREST (3)
│   │   ├── Wzrost short interest                           [38.1]
│   │   ├── Short squeeze                                   [38.2]
│   │   └── Days to Cover                                   [38.3]
│   │
│   ├── DARK POOL (1)
│   │   └── Nietypowa aktywność w Dark Pool                 [39.1]
│   │
│   └── NIETYPOWE TRANSAKCJE (2)
│       ├── Duży blokowy trade (Block Trade)                [40.1]
│       └── Transakcja pakietowa (Package Trade)            [40.2]
│
├── SENTIMENT & NEWS (11)                    → Sentiment & News Event Detector
│   │
│   ├── MEDIA SPOŁECZNOŚCIOWE (3)
│   │   ├── Wzmianki w social media                         [41.1]
│   │   ├── Trend na Reddit                                 [41.2]
│   │   └── Wzmianka przez influencera                      [41.3]
│   │
│   ├── SENTYMENT RYNKU (3)
│   │   ├── Zmiana sentymentu                               [42.1]
│   │   ├── VIX — wzrost (VIX Spike)                        [42.2]
│   │   └── Put/Call Ratio                                  [42.3]
│   │
│   └── NEWS & TAVILY (5)
│       ├── Breaking news                                   [43.1]
│       ├── Artykuł analityczny                             [43.2]
│       ├── Wywiad z zarządem                               [43.3]
│       ├── Wynik wyszukiwania Tavily                       [44.1]
│       └── Zmiana sentymentu w wynikach Tavily             [44.2]
│
└── SYSTEM & CONTEXT (12)                     → System Event Detector
    │
    ├── ALERTY WŁASNE ALCHEMIKA (3)
    │   ├── Wykrycie zdarzenia złożonego (Composite Event)  [45.1]
    │   ├── Zmiana stanu instrumentu                        [45.2]
    │   └── Powtórne wykrycie zdarzenia                     [45.3]
    │
    ├── ZDARZENIA MIĘDZYINSTRUMENTOWE (2)
    │   ├── Spread między instrumentami                     [46.1]
    │   └── Lider vs followers                              [46.2]
    │
    ├── ZDARZENIA SEZONOWE I KALENDARZOWE (4)
    │   ├── Efekt końca miesiąca/kwartału                   [47.1]
    │   ├── Dzień wygasania instrumentów pochodnych         [47.2]
    │   ├── Efekt stycznia                                  [47.3]
    │   └── Sezon wyników                                   [47.4]
    │
    ├── SEKTOR (3)
    │   ├── Rotacja sektorowa                               [34.1]
    │   ├── Zmiana regulacji sektorowych                    [34.2]
    │   └── Bankructwo lidera sektorowego                   [34.3]
    │
    └── KORELACJE (2)
        ├── Rozpad korelacji                                [35.1]
        └── Wzmocnienie korelacji                           [35.2]
```

---

## 4. SZCZEGÓŁOWA KLASYFIKACJA KAŻDEGO ZDARZENIA

### 4.1 PRICE (10 zdarzeń)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 1.1 | Price Surge | Cenowe | Ruchy kierunkowe | Podstawowe | Tak — Price Move Detector (1.1, 1.2) | TechnicalEngine |
| 1.2 | Price Drop | Cenowe | Ruchy kierunkowe | Podstawowe | Tak — Price Move Detector (1.1, 1.2) | TechnicalEngine |
| 1.3 | Gap Up | Cenowe | Luki | Podstawowe | Tak — Gap Detector (1.3, 1.4) | TechnicalEngine |
| 1.4 | Gap Down | Cenowe | Luki | Podstawowe | Tak — Gap Detector (1.3, 1.4) | TechnicalEngine |
| 1.5 | 52-Week High | Cenowe | Ekstrema | Podstawowe | Tak — Extrema Detector (1.5, 1.6, 1.7, 1.8) | TechnicalEngine |
| 1.6 | 52-Week Low | Cenowe | Ekstrema | Podstawowe | Tak — Extrema Detector (1.5, 1.6, 1.7, 1.8) | TechnicalEngine |
| 1.7 | All-Time High | Cenowe | Ekstrema | Pochodne (od 1.5) | Tak — Extrema Detector | TechnicalEngine |
| 1.8 | All-Time Low | Cenowe | Ekstrema | Pochodne (od 1.6) | Tak — Extrema Detector | TechnicalEngine |
| 1.9 | Level Rejection | Cenowe | Poziomy | Podstawowe | Tak — Level Detector (1.9, 4.1, 4.2) | TechnicalEngine |
| 1.10 | Psychological Level Cross | Cenowe | Poziomy | Podstawowe | Nie — unikalny algorytm | TechnicalEngine |

### 4.2 VOLUME (5 zdarzeń)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 2.1 | Volume Spike | Wolumenowe | Odchylenie od średniej | Podstawowe | Tak — Volume Anomaly Detector (2.1, 2.2, 2.3) | TechnicalEngine |
| 2.2 | Near-Zero Volume | Wolumenowe | Odchylenie od średniej | Podstawowe | Tak — Volume Anomaly Detector | TechnicalEngine |
| 2.3 | Cumulative Volume Anomaly | Wolumenowe | Odchylenie od średniej | Podstawowe | Tak — Volume Anomaly Detector | TechnicalEngine |
| 2.4 | High Volume on Down Days | Wolumenowe | Wolumen kierunkowy | Podstawowe | Tak — Directional Volume Detector (2.4, 2.5) | TechnicalEngine |
| 2.5 | High Volume on Up Days | Wolumenowe | Wolumen kierunkowy | Podstawowe | Tak — Directional Volume Detector (2.4, 2.5) | TechnicalEngine |

### 4.3 TECHNICAL (34 zdarzenia)

#### Zmienność (4)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 3.1 | Volatility Spike | Zmienność | Odchylenie ATR | Podstawowe | Tak — Volatility Detector (3.1, 3.2, 8.3) | TechnicalEngine |
| 3.2 | Volatility Contraction | Zmienność | Odchylenie ATR | Podstawowe | Tak — Volatility Detector | TechnicalEngine |
| 3.3 | BB Expansion | Zmienność | Wstęgi Bollingera | Podstawowe | Tak — BB Detector (3.3, 3.4) | TechnicalEngine |
| 3.4 | BB Squeeze | Zmienność | Wstęgi Bollingera | Podstawowe | Tak — BB Detector (3.3, 3.4) | TechnicalEngine |

#### Wybicia techniczne (5)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 4.1 | Resistance Breakout | Wybicia | Poziomy S/R | Podstawowe | Tak — Breakout Detector (4.1, 4.2) | TechnicalEngine |
| 4.2 | Support Breakdown | Wybicia | Poziomy S/R | Podstawowe | Tak — Breakout Detector (4.1, 4.2) | TechnicalEngine |
| 4.3 | Triangle Breakout | Wybicia | Formacje geometryczne | Podstawowe | Tak — Pattern Breakout Detector (4.3, 4.4, 4.5) | TechnicalEngine |
| 4.4 | Channel Breakout | Wybicia | Formacje geometryczne | Podstawowe | Tak — Pattern Breakout Detector | TechnicalEngine |
| 4.5 | Flag/Pennant Breakout | Wybicia | Formacje geometryczne | Podstawowe | Tak — Pattern Breakout Detector | TechnicalEngine |

#### Formacje świecowe (10)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 5.1 | Hammer / Hanging Man | Świece | Pojedyncze | Podstawowe | Tak — Single Candle Detector (5.1, 5.2, 5.5, 5.9) | TechnicalEngine |
| 5.2 | Shooting Star / Inv. Hammer | Świece | Pojedyncze | Podstawowe | Tak — Single Candle Detector | TechnicalEngine |
| 5.3 | Bullish Engulfing | Świece | Podwójne | Podstawowe | Tak — Double Candle Detector (5.3, 5.4, 5.10) | TechnicalEngine |
| 5.4 | Bearish Engulfing | Świece | Podwójne | Podstawowe | Tak — Double Candle Detector | TechnicalEngine |
| 5.5 | Doji | Świece | Pojedyncze | Podstawowe | Tak — Single Candle Detector | TechnicalEngine |
| 5.6 | Morning/Evening Star | Świece | Potrójne/złożone | Podstawowe | Tak — Triple Candle Detector (5.6, 5.7, 5.8) | TechnicalEngine |
| 5.7 | Three White Soldiers | Świece | Potrójne/złożone | Podstawowe | Tak — Triple Candle Detector | TechnicalEngine |
| 5.8 | Three Black Crows | Świece | Potrójne/złożone | Podstawowe | Tak — Triple Candle Detector | TechnicalEngine |
| 5.9 | Marubozu | Świece | Pojedyncze | Podstawowe | Tak — Single Candle Detector | TechnicalEngine |
| 5.10 | Harami | Świece | Podwójne | Podstawowe | Tak — Double Candle Detector | TechnicalEngine |

#### Trend (5)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 6.1 | MA Crossover | Trend | Średnie kroczące | Podstawowe | Tak — MA Detector (6.1, 6.2, 6.3) | TechnicalEngine |
| 6.2 | MA Slope Change | Trend | Średnie kroczące | Pochodne (od 6.1) | Tak — MA Detector | TechnicalEngine |
| 6.3 | Price vs MA | Trend | Średnie kroczące | Podstawowe | Tak — MA Detector | TechnicalEngine |
| 6.4 | Consecutive Up/Down Candles | Trend | Seria świec | Podstawowe | Nie — unikalny algorytm | TechnicalEngine |
| 6.5 | Trend Structure Change | Trend | Struktura swingu | Podstawowe | Nie — unikalny algorytm | TechnicalEngine |

#### Momentum (6)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 7.1 | RSI Overbought | Momentum | RSI | Podstawowe | Tak — RSI Detector (7.1, 7.2, 7.3) | TechnicalEngine |
| 7.2 | RSI Oversold | Momentum | RSI | Podstawowe | Tak — RSI Detector | TechnicalEngine |
| 7.3 | RSI Divergence | Momentum | RSI | Pochodne (od 7.1/7.2) | Tak — RSI Detector | TechnicalEngine |
| 7.4 | MACD Line Crossover | Momentum | MACD | Podstawowe | Tak — MACD Detector (7.4, 7.5) | TechnicalEngine |
| 7.5 | MACD Zero Cross | Momentum | MACD | Pochodne (od 7.4) | Tak — MACD Detector | TechnicalEngine |
| 7.6 | Stochastic Overbought/Oversold | Momentum | Stochastic | Podstawowe | Nie — unikalny algorytm | TechnicalEngine |

#### Wskaźniki techniczne (4)

| ID | Nazwa | Kategoria | Podkategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-------------|-----|----------------------|------------|
| 8.1 | OBV Divergence | Wskaźniki | OBV | Podstawowe | Nie | TechnicalEngine |
| 8.2 | VWAP Deviation | Wskaźniki | VWAP | Podstawowe | Nie | TechnicalEngine |
| 8.3 | ATR Expansion | Wskaźniki | ATR | Podstawowe | Tak — Volatility Detector (3.1, 3.2, 8.3) | TechnicalEngine |
| 8.4 | Fibonacci Retracement Hit | Wskaźniki | Fibonacci | Podstawowe | Nie | TechnicalEngine |

### 4.4 FUNDAMENTAL (24 zdarzenia)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 9.1 | P/E Ratio Change | Wskaźniki finansowe | Podstawowe | Tak — Ratio Change Detector (9.1, 9.2) | AnalystEngine |
| 9.2 | P/BV Ratio Change | Wskaźniki finansowe | Podstawowe | Tak — Ratio Change Detector | AnalystEngine |
| 9.3 | Market Cap Change | Wskaźniki finansowe | Podstawowe | Nie | AnalystEngine |
| 9.4 | Debt Change | Wskaźniki finansowe | Podstawowe | Nie | AnalystEngine |
| 9.5 | Revenue Change | Wskaźniki finansowe | Podstawowe | Tak — Financial Change Detector (9.5, 9.6) | AnalystEngine |
| 9.6 | Net Income Change | Wskaźniki finansowe | Podstawowe | Tak — Financial Change Detector | AnalystEngine |
| 10.1 | Earnings Release | Wyniki finansowe | Podstawowe | Nie | NewsEngine + AnalystEngine |
| 10.2 | Earnings Beat | Wyniki finansowe | Pochodne (od 10.1) | Tak — Earnings Surprise Detector (10.2, 10.3) | AnalystEngine + AIEngine |
| 10.3 | Earnings Miss | Wyniki finansowe | Pochodne (od 10.1) | Tak — Earnings Surprise Detector | AnalystEngine + AIEngine |
| 10.4 | Guidance Update | Wyniki finansowe | Podstawowe | Nie | NewsEngine + AIEngine |
| 11.1 | Quarterly Report Filed | Raporty | Podstawowe | Tak — Report Detector (11.1, 11.2) | NewsEngine |
| 11.2 | Annual Report Filed | Raporty | Podstawowe | Tak — Report Detector | NewsEngine |
| 11.3 | Accounting Policy Change | Raporty | Podstawowe | Nie | AnalystEngine + AIEngine |
| 14.1 | Dividend Announcement | Dywidendy | Podstawowe | Tak — Dividend Detector (14.1, 14.2, 14.3) | NewsEngine + AnalystEngine |
| 14.2 | Dividend Policy Change | Dywidendy | Podstawowe | Tak — Dividend Detector | NewsEngine + AnalystEngine |
| 14.3 | Special Dividend | Dywidendy | Podstawowe | Tak — Dividend Detector | NewsEngine + AnalystEngine |
| 14.4 | Ex-Dividend Date | Dywidendy | Podstawowe | Nie | AnalystEngine |
| 15.1 | Split Announcement | Splity | Podstawowe | Tak — Split Detector (15.1, 15.3) | NewsEngine |
| 15.2 | Split Execution | Splity | Podstawowe | Nie | TechnicalEngine |
| 15.3 | Reverse Split | Splity | Podstawowe | Tak — Split Detector | NewsEngine + AnalystEngine |
| 16.1 | Share Issuance Announcement | Emisje akcji | Podstawowe | Tak — Issuance Detector (16.1, 16.2, 16.3) | NewsEngine + AnalystEngine |
| 16.2 | Rights Offering | Emisje akcji | Podstawowe | Tak — Issuance Detector | NewsEngine + AnalystEngine |
| 16.3 | Private Placement | Emisje akcji | Podstawowe | Tak — Issuance Detector | NewsEngine + AnalystEngine |
| 17.1 | Buyback Announcement | Skup akcji | Podstawowe | Tak — Buyback Detector (17.1, 17.2) | NewsEngine + AnalystEngine |
| 17.2 | Buyback Execution | Skup akcji | Pochodne (od 17.1) | Tak — Buyback Detector | NewsEngine |

### 4.5 CORPORATE (34 zdarzenia)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 18.1 | Insider Transaction | Insider Trading | Podstawowe | Tak — Insider Detector (18.1, 18.2, 18.3) | NewsEngine + AnalystEngine |
| 18.2 | Insider Buying Cluster | Insider Trading | Pochodne (od 18.1) | Tak — Insider Cluster Detector | AnalystEngine |
| 18.3 | Insider Selling Cluster | Insider Trading | Pochodne (od 18.1) | Tak — Insider Cluster Detector | AnalystEngine |
| 19.1 | Threshold Crossing | Zmiany akcjonariatu | Podstawowe | Nie | NewsEngine + AnalystEngine |
| 19.2 | Tender Offer | Zmiany akcjonariatu | Podstawowe | Nie | NewsEngine + AnalystEngine |
| 19.3 | Major Shareholder Change | Zmiany akcjonariatu | Podstawowe | Tak — Shareholder Detector (19.1, 19.3) | NewsEngine + AnalystEngine |
| 20.1 | New Analyst Rating | Rekomendacje | Podstawowe | Tak — Rating Detector (20.1, 20.2, 20.3) | NewsEngine + AIEngine |
| 20.2 | Price Target Change | Rekomendacje | Podstawowe | Tak — Rating Detector | NewsEngine + AIEngine |
| 20.3 | Upgrade/Downgrade | Rekomendacje | Pochodne (od 20.1) | Tak — Rating Detector | NewsEngine + AIEngine |
| 21.1 | Credit Rating Change | Ratingi | Podstawowe | Tak — Credit Rating Detector (21.1, 21.2) | NewsEngine + AIEngine |
| 21.2 | Rating Outlook Change | Ratingi | Podstawowe | Tak — Credit Rating Detector | NewsEngine + AIEngine |
| 22.1 | M&A Announcement | Fuzje i przejęcia | Podstawowe | Tak — M&A Detector (22.1, 22.3) | NewsEngine + AIEngine |
| 22.2 | M&A Rumors | Fuzje i przejęcia | Podstawowe | Nie | NewsEngine + Tavily |
| 22.3 | M&A Completion/Failure | Fuzje i przejęcia | Pochodne (od 22.1) | Tak — M&A Detector | NewsEngine |
| 23.1 | Major Contract Signed | Kontrakty | Podstawowe | Tak — Contract Detector (23.1, 23.2) | NewsEngine + AIEngine |
| 23.2 | Contract Termination | Kontrakty | Podstawowe | Tak — Contract Detector | NewsEngine + AIEngine |
| 24.1 | Lawsuit Against Company | Pozwy | Podstawowe | Tak — Legal Detector (24.1, 24.2, 25.1, 25.2) | NewsEngine + AIEngine |
| 24.2 | Lawsuit Filed by Company | Pozwy | Podstawowe | Tak — Legal Detector | NewsEngine |
| 25.1 | Regulatory Investigation | Problemy prawne | Podstawowe | Tak — Legal Detector | NewsEngine + AIEngine |
| 25.2 | Financial Penalty | Problemy prawne | Podstawowe | Tak — Legal Detector | NewsEngine + AnalystEngine |
| 25.3 | Trading Suspension | Problemy prawne | Podstawowe | Nie | NewsEngine |
| 26.1 | Bankruptcy Filing | Upadłości | Podstawowe | Tak — Bankruptcy Detector (26.1, 26.3) | NewsEngine |
| 26.2 | Restructuring | Upadłości | Podstawowe | Nie | NewsEngine + AnalystEngine |
| 26.3 | Counterparty Bankruptcy | Upadłości | Podstawowe | Tak — Bankruptcy Detector | NewsEngine + AIEngine |
| 27.1 | CEO Change | Zmiany zarządu | Podstawowe | Tak — Management Detector (27.1, 27.2, 27.3) | NewsEngine + AIEngine |
| 27.2 | Management Board Change | Zmiany zarządu | Podstawowe | Tak — Management Detector | NewsEngine |
| 27.3 | Supervisory Board Change | Zmiany zarządu | Podstawowe | Tak — Management Detector | NewsEngine |
| 27.4 | Key Employee Departure | Zmiany zarządu | Podstawowe | Nie | NewsEngine + Tavily |

### 4.6 REGULATORY (3 zdarzenia)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 12.1 | New ESPI Filing | ESPI | Podstawowe | Tak — Regulatory Filing Detector (12.1, 13.1) | NewsEngine + AIEngine |
| 12.2 | ESPI Filing Delay | ESPI | Pochodne (od 12.1) | Nie | NewsEngine |
| 13.1 | New EBI Filing | EBI | Podstawowe | Tak — Regulatory Filing Detector | NewsEngine + AIEngine |

### 4.7 MACRO (16 zdarzeń)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 28.1 | Macro Data Release | Makroekonomia | Podstawowe | Tak — Macro Data Detector (28.1, 28.2, 28.3, 30.1) | NewsEngine + AIEngine |
| 28.2 | GDP Change | Makroekonomia | Podstawowe | Tak — Macro Data Detector | NewsEngine + AIEngine |
| 28.3 | Unemployment Change | Makroekonomia | Podstawowe | Tak — Macro Data Detector | NewsEngine |
| 29.1 | Interest Rate Decision | Stopy procentowe | Podstawowe | Tak — Rate Decision Detector (29.1, 29.2, 29.3) | NewsEngine + AIEngine |
| 29.2 | Emergency Rate Change | Stopy procentowe | Podstawowe | Tak — Rate Decision Detector | NewsEngine |
| 29.3 | Forward Guidance Change | Stopy procentowe | Podstawowe | Tak — Rate Decision Detector | AIEngine + NewsEngine |
| 30.1 | CPI/PPI Release | Inflacja | Podstawowe | Tak — Macro Data Detector | NewsEngine + AIEngine |
| 30.2 | Inflation Surprise | Inflacja | Pochodne (od 30.1) | Nie | NewsEngine + AIEngine |
| 31.1 | Major FX Move | Waluty | Podstawowe | Tak — Price Move Detector (1.1, 1.2, 31.1) | TechnicalEngine + AnalystEngine |
| 31.2 | FX Intervention | Waluty | Podstawowe | Nie | NewsEngine |
| 32.1 | Commodity Price Shock | Surowce | Podstawowe | Tak — Price Move Detector | TechnicalEngine + AnalystEngine |
| 32.2 | Supply Shock | Surowce | Podstawowe | Nie | NewsEngine + AIEngine |
| 33.1 | Armed Conflict / Escalation | Geopolityka | Podstawowe | Tak — Geopolitical Detector (33.1, 33.2, 33.3, 33.4) | NewsEngine + AIEngine |
| 33.2 | Sanctions | Geopolityka | Podstawowe | Tak — Geopolitical Detector | NewsEngine + AIEngine |
| 33.3 | Elections / Regime Change | Geopolityka | Podstawowe | Tak — Geopolitical Detector | NewsEngine + AIEngine |
| 33.4 | Trade Agreement/Dispute | Geopolityka | Podstawowe | Tak — Geopolitical Detector | NewsEngine + AIEngine |

### 4.8 ETF (4 zdarzenia)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 36.1 | ETF Rebalancing | ETF | Podstawowe | Nie | NewsEngine + AnalystEngine |
| 36.2 | ETF Flows | ETF | Podstawowe | Nie | NewsEngine + AnalystEngine |
| 36.3 | ETF Premium/Discount | ETF | Podstawowe | Nie | AnalystEngine |
| 36.4 | ETF Closure/Liquidation | ETF | Podstawowe | Nie | NewsEngine |

### 4.9 DERIVATIVES & ALTERNATIVE DATA (9 zdarzeń)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 37.1 | Unusual Options Activity | Opcje | Podstawowe | Tak — Options Detector (37.1, 37.2) | TechnicalEngine + AnalystEngine |
| 37.2 | IV Change | Opcje | Podstawowe | Tak — Options Detector | TechnicalEngine |
| 37.3 | Max Pain | Opcje | Podstawowe | Nie | TechnicalEngine |
| 38.1 | Short Interest Increase | Short Interest | Podstawowe | Tak — Short Interest Detector (38.1, 38.3) | AnalystEngine |
| 38.2 | Short Squeeze | Short Interest | Pochodne (od 38.1 + 1.1) | Nie — zdarzenie złożone | TechnicalEngine + AnalystEngine |
| 38.3 | Days to Cover | Short Interest | Podstawowe | Tak — Short Interest Detector | AnalystEngine |
| 39.1 | Dark Pool Activity | Dark Pool | Podstawowe | Nie | AnalystEngine (zewn.) |
| 40.1 | Block Trade | Nietypowe transakcje | Podstawowe | Nie | AnalystEngine (zewn.) |
| 40.2 | Package Trade | Nietypowe transakcje | Podstawowe | Nie | NewsEngine + AnalystEngine |

### 4.10 SENTIMENT & NEWS (11 zdarzeń)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 41.1 | Social Media Mentions Spike | Media społecznościowe | Podstawowe | Tak — Social Media Detector (41.1, 41.2) | NewsEngine + AIEngine |
| 41.2 | Reddit Trend | Media społecznościowe | Podstawowe | Tak — Social Media Detector | NewsEngine + AIEngine |
| 41.3 | Influencer Mention | Media społecznościowe | Podstawowe | Nie | NewsEngine + AIEngine |
| 42.1 | Sentiment Shift | Sentyment rynku | Podstawowe | Nie | AnalystEngine + AIEngine |
| 42.2 | VIX Spike | Sentyment rynku | Podstawowe | Tak — Price Move Detector (1.1, 1.2, 31.1, 32.1, 42.2) | TechnicalEngine + AnalystEngine |
| 42.3 | Put/Call Ratio | Sentyment rynku | Podstawowe | Nie | AnalystEngine (zewn.) |
| 43.1 | Breaking News | News | Podstawowe | Tak — News Detector (43.1, 43.2, 43.3) | NewsEngine + AIEngine |
| 43.2 | Analyst Article | News | Podstawowe | Tak — News Detector | NewsEngine + AIEngine |
| 43.3 | Management Interview | News | Podstawowe | Tak — News Detector | NewsEngine + AIEngine |
| 44.1 | Tavily Search Result | Tavily | Podstawowe | Tak — Tavily Detector (44.1, 44.2) | Tavily + NewsEngine |
| 44.2 | Tavily Sentiment Change | Tavily | Pochodne (od 44.1) | Tak — Tavily Detector | AIEngine + Tavily |

### 4.11 SYSTEM & CONTEXT (12 zdarzeń)

| ID | Nazwa | Kategoria | Typ | Współdzielony algorytm | Właściciel |
|----|-------|-----------|-----|----------------------|------------|
| 45.1 | Composite Event Detected | Alerty własne | Pochodne (agregacja) | Nie | Wszystkie silniki + AIEngine |
| 45.2 | Instrument State Change | Alerty własne | Pochodne (od 45.1) | Nie | Wszystkie silniki + AIEngine |
| 45.3 | Event Recurrence | Alerty własne | Pochodne (od dowolnego) | Nie | Wszystkie silniki |
| 46.1 | Instrument Spread Anomaly | Międzyinstrumentowe | Podstawowe | Tak — Spread Detector (46.1, 35.1) | TechnicalEngine + AnalystEngine |
| 46.2 | Leader-Lag Analysis | Międzyinstrumentowe | Podstawowe | Nie | TechnicalEngine + AnalystEngine |
| 47.1 | Month/Quarter End Effect | Sezonowe | Podstawowe | Tak — Calendar Detector (47.1, 47.2, 47.3, 47.4) | AnalystEngine |
| 47.2 | Triple Witching | Sezonowe | Podstawowe | Tak — Calendar Detector | AnalystEngine |
| 47.3 | January Effect | Sezonowe | Podstawowe | Tak — Calendar Detector | AnalystEngine |
| 47.4 | Earnings Season | Sezonowe | Podstawowe | Tak — Calendar Detector | AnalystEngine + NewsEngine |
| 34.1 | Sector Rotation | Sektor | Podstawowe | Tak — Sector Detector (34.1, 34.3, 35.1, 35.2) | TechnicalEngine + AnalystEngine |
| 34.2 | Sector Regulation Change | Sektor | Podstawowe | Nie | NewsEngine + AIEngine |
| 34.3 | Sector Leader Bankruptcy | Sektor | Podstawowe | Tak — Sector Detector | NewsEngine + AIEngine |
| 35.1 | Correlation Breakdown | Korelacje | Podstawowe | Tak — Correlation Detector (35.1, 35.2) | TechnicalEngine + AnalystEngine |
| 35.2 | Correlation Strengthening | Korelacje | Podstawowe | Tak — Correlation Detector | TechnicalEngine + AnalystEngine |

---

## 5. MAPOWANIE RODZIN NA PRZYSZŁE MODUŁY

```
Rodzina zdarzeń              → Przyszły moduł odpowiedzialny (Detektor)
═══════════════════════════════════════════════════════════════════════

PRICE                        → Price Event Detector
  (10 zdarzeń)                 Wykrywa: ruchy cenowe, luki, ekstrema, odrzucenia poziomów
  Właściciel: TechnicalEngine

VOLUME                       → Volume Event Detector
  (5 zdarzeń)                  Wykrywa: anomalie wolumenowe, wolumen kierunkowy
  Właściciel: TechnicalEngine

TECHNICAL                    → Technical Event Detector
  (34 zdarzenia)               Wykrywa: zmienność, wybicia, formacje świecowe, trend,
  Właściciel: TechnicalEngine  momentum, sygnały ze wskaźników technicznych

FUNDAMENTAL                  → Fundamental Event Detector
  (24 zdarzenia)               Wykrywa: zmiany wskaźników finansowych, wyniki kwartalne,
  Właściciel: AnalystEngine    raporty, dywidendy, splity, emisje, skup akcji własnych
                               (+ NewsEngine dla news-pochodnych)

CORPORATE                    → Corporate Event Detector
  (34 zdarzenia)               Wykrywa: insider trading, zmiany akcjonariatu, rekomendacje,
  Właściciel: NewsEngine       ratingi, fuzje i przejęcia, kontrakty, kwestie prawne,
  (+ AnalystEngine, AIEngine)  upadłości, zmiany zarządu

REGULATORY                   → Regulatory Event Detector
  (3 zdarzenia)                Wykrywa: komunikaty ESPI i EBI
  Właściciel: NewsEngine

MACRO                        → Macro Event Detector
  (16 zdarzeń)                 Wykrywa: dane makro, decyzje o stopach, inflacja,
  Właściciel: NewsEngine       ruchy walutowe, surowce, geopolityka
  (+ AnalystEngine, AIEngine,
   TechnicalEngine)

ETF                          → ETF Event Detector
  (4 zdarzenia)                Wykrywa: zmiany składu ETF, przepływy, premia/dyskonto,
  Właściciel: AnalystEngine    likwidacje ETF
  (+ NewsEngine)

DERIVATIVES & ALTERNATIVE    → Derivatives Event Detector
  DATA (9 zdarzeń)             Wykrywa: nietypowa aktywność na opcjach, short interest,
  Właściciel: AnalystEngine    dark pool, nietypowe transakcje
  (+ TechnicalEngine)

SENTIMENT & NEWS             → Sentiment & News Event Detector
  (11 zdarzeń)                 Wykrywa: wzmianki w social media, zmiany sentymentu,
  Właściciel: NewsEngine       newsy, wyniki Tavily
  (+ AIEngine, Tavily)

SYSTEM & CONTEXT             → System Event Detector
  (12 zdarzeń)                 Wykrywa: zdarzenia złożone, zmiany stanu, zdarzenia
  Właściciel: Multi-Engine     międzyinstrumentowe, sezonowe, sektorowe, korelacje
  (wszystkie silniki)
```

---

## 6. TABELA RODZIN ZDARZEŃ

| Rodzina | Liczba zdarzeń | Priorytet | Etap wdrożenia | Główne silniki |
|---------|:---:|-----------|:--------------:|----------------|
| **PRICE** | 10 | Krytyczny | Etap 1 (v1) | TechnicalEngine |
| **VOLUME** | 5 | Krytyczny | Etap 1 (v1) | TechnicalEngine |
| **TECHNICAL** | 34 | Krytyczny | Etap 1: 15 / Etap 2-3: 19 | TechnicalEngine |
| **FUNDAMENTAL** | 24 | Wysoki | Etap 1: 5 / Etap 2-3: 19 | AnalystEngine, NewsEngine |
| **CORPORATE** | 34 | Wysoki | Etap 2-3: 34 | NewsEngine, AnalystEngine, AIEngine |
| **REGULATORY** | 3 | Wysoki | Etap 2: 3 | NewsEngine, AIEngine |
| **MACRO** | 16 | Wysoki | Etap 2-3: 16 | NewsEngine, AnalystEngine, AIEngine, TechnicalEngine |
| **ETF** | 4 | Średni | Etap 2-3: 4 | AnalystEngine, NewsEngine |
| **DERIVATIVES & ALT** | 9 | Średni-Wysoki | Etap 2-4: 9 | AnalystEngine, TechnicalEngine |
| **SENTIMENT & NEWS** | 11 | Wysoki | Etap 2-3: 11 | NewsEngine, AIEngine |
| **SYSTEM & CONTEXT** | 12 | Średni | Etap 2-4: 12 | Multi-Engine |
| **RAZEM** | **~157** | | Etap 1: ~32 / Etap 2-4: ~125 | |

---

## 7. ANALIZA POTENCJAŁU WSPÓŁDZIELENIA ALGORYTMÓW

### 7.1 Algorytmy współdzielone między wieloma zdarzeniami

| Grupa algorytmiczna | Liczba zdarzeń | Opis wspólnego algorytmu |
|---------------------|:---:|--------------------------|
| **Price Move Detector** | 5 | Wykrywanie procentowej zmiany ceny względem poprzedniej świecy — dla 1.1, 1.2, 31.1, 32.1, 42.2 |
| **Gap Detector** | 2 | Wykrywanie luki między open a poprzednim close — dla 1.3, 1.4 |
| **Extrema Detector** | 4 | Wykrywanie nowych ekstremów w oknie czasowym — dla 1.5, 1.6, 1.7, 1.8 |
| **Level Detector** | 3 | Wykrywanie reakcji ceny na poziomy S/R — dla 1.9, 4.1, 4.2 |
| **Volume Anomaly Detector** | 3 | Porównanie wolumenu do średniej — dla 2.1, 2.2, 2.3 |
| **Directional Volume Detector** | 2 | Porównanie wolumenu na świecach wzrostowych vs spadkowych — dla 2.4, 2.5 |
| **Volatility Detector** | 3 | Porównanie ATR/zmienności do średniej — dla 3.1, 3.2, 8.3 |
| **BB Detector** | 2 | Pomiar szerokości wstęg Bollingera — dla 3.3, 3.4 |
| **Breakout Detector** | 2 | Wykrywanie przekroczenia poziomów S/R — dla 4.1, 4.2 |
| **Pattern Breakout Detector** | 3 | Wykrywanie wybicia z formacji geometrycznej — dla 4.3, 4.4, 4.5 |
| **Single Candle Detector** | 4 | Analiza pojedynczej świecy (cienie, korpus) — dla 5.1, 5.2, 5.5, 5.9 |
| **Double Candle Detector** | 3 | Analiza relacji dwóch świec — dla 5.3, 5.4, 5.10 |
| **Triple Candle Detector** | 3 | Analiza trzech świec — dla 5.6, 5.7, 5.8 |
| **MA Detector** | 3 | Analiza przecięć i nachyleń średnich — dla 6.1, 6.2, 6.3 |
| **RSI Detector** | 3 | Analiza poziomów RSI — dla 7.1, 7.2, 7.3 |
| **MACD Detector** | 2 | Analiza przecięć MACD — dla 7.4, 7.5 |
| **Ratio Change Detector** | 2 | Wykrywanie zmiany wskaźnika finansowego — dla 9.1, 9.2 |
| **Financial Change Detector** | 2 | Wykrywanie zmiany przychodów/zysków — dla 9.5, 9.6 |
| **Earnings Surprise Detector** | 2 | Porównanie wyniku do konsensusu — dla 10.2, 10.3 |
| **Report Detector** | 2 | Wykrywanie publikacji raportu — dla 11.1, 11.2 |
| **Dividend Detector** | 3 | Wykrywanie zdarzeń dywidendowych — dla 14.1, 14.2, 14.3 |
| **Split Detector** | 2 | Wykrywanie ogłoszeń splitu — dla 15.1, 15.3 |
| **Issuance Detector** | 3 | Wykrywanie emisji akcji — dla 16.1, 16.2, 16.3 |
| **Buyback Detector** | 2 | Wykrywanie skupu akcji — dla 17.1, 17.2 |
| **Insider Detector** | 3 | Wykrywanie transakcji insiderów — dla 18.1, 18.2, 18.3 |
| **Shareholder Detector** | 2 | Wykrywanie zmian akcjonariatu — dla 19.1, 19.3 |
| **Rating Detector** | 3 | Wykrywanie rekomendacji analityków — dla 20.1, 20.2, 20.3 |
| **Credit Rating Detector** | 2 | Wykrywanie zmian ratingu — dla 21.1, 21.2 |
| **M&A Detector** | 2 | Wykrywanie fuzji i przejęć — dla 22.1, 22.3 |
| **Contract Detector** | 2 | Wykrywanie kontraktów — dla 23.1, 23.2 |
| **Legal Detector** | 4 | Wykrywanie zdarzeń prawnych — dla 24.1, 24.2, 25.1, 25.2 |
| **Bankruptcy Detector** | 2 | Wykrywanie upadłości — dla 26.1, 26.3 |
| **Management Detector** | 3 | Wykrywanie zmian w zarządzie — dla 27.1, 27.2, 27.3 |
| **Regulatory Filing Detector** | 2 | Wykrywanie komunikatów ESPI/EBI — dla 12.1, 13.1 |
| **Macro Data Detector** | 4 | Wykrywanie publikacji danych makro — dla 28.1, 28.2, 28.3, 30.1 |
| **Rate Decision Detector** | 3 | Wykrywanie decyzji o stopach — dla 29.1, 29.2, 29.3 |
| **Geopolitical Detector** | 4 | Wykrywanie zdarzeń geopolitycznych — dla 33.1, 33.2, 33.3, 33.4 |
| **Options Detector** | 2 | Wykrywanie anomalii opcyjnych — dla 37.1, 37.2 |
| **Short Interest Detector** | 2 | Wykrywanie zmian short interest — dla 38.1, 38.3 |
| **Social Media Detector** | 2 | Wykrywanie trendów w social media — dla 41.1, 41.2 |
| **News Detector** | 3 | Wykrywanie istotnych newsów — dla 43.1, 43.2, 43.3 |
| **Tavily Detector** | 2 | Przetwarzanie wyników Tavily — dla 44.1, 44.2 |
| **Calendar Detector** | 4 | Wykrywanie zdarzeń kalendarzowych — dla 47.1, 47.2, 47.3, 47.4 |
| **Sector Detector** | 3 | Wykrywanie zdarzeń sektorowych — dla 34.1, 34.3, 35.1*, 35.2* |
| **Correlation Detector** | 2 | Wykrywanie zmian korelacji — dla 35.1, 35.2 |
| **Spread Detector** | 2 | Wykrywanie anomalii spreadów — dla 46.1, 35.1* |

**Łącznie: 46 grup algorytmicznych obsługujących ~131 zdarzeń (~83% wszystkich zdarzeń)**

Zdarzenia **bez możliwości współdzielenia** (unikalny algorytm): 1.10, 6.4, 6.5, 7.6, 8.1, 8.2, 8.4, 9.3, 9.4, 10.1, 10.4, 11.3, 14.4, 15.2, 19.2, 22.2, 25.3, 26.2, 27.4, 12.2, 30.2, 31.2, 32.2, 36.1, 36.2, 36.3, 36.4, 37.3, 38.2, 39.1, 40.1, 40.2, 41.3, 42.1, 42.3, 45.1, 45.2, 45.3, 46.2, 34.2 — razem ~26 zdarzeń (~17%).

### 7.2 Redukcja liczby detektorów dzięki wspólnej logice

Zaproponowane 11 detektorów (rodzin) może zostać zredukowanych **do 8 detektorów** poprzez następujące połączenia:

| Połączone detektory | Nowy detektor | Uzasadnienie |
|---------------------|---------------|-------------|
| Price (10) + Volume (5) | **Price & Volume Event Detector** | Oba opierają się wyłącznie na OHLCV z yfinance; wspólny pipeline przetwarzania danych; ten sam właściciel (TechnicalEngine) |
| Technical (34) | **Technical Event Detector** | Już skonsolidowany — zawiera zmienność, wybicia, świece, trend, momentum, wskaźniki |
| Fundamental (24) | **Fundamental Event Detector** | Bez zmian |
| Corporate (34) + Regulatory (3) | **Corporate & Regulatory Event Detector** | Oba opierają się na NewsEngine; ESPI/EBI to podzbiór zdarzeń korporacyjnych |
| Macro (16) | **Macro Event Detector** | Bez zmian |
| ETF (4) + Derivatives & Alt (9) | **Specialized Instruments Event Detector** | Łączy instrumenty pochodne, ETF i alternatywne źródła danych |
| Sentiment & News (11) | **Sentiment & News Event Detector** | Bez zmian |
| System & Context (12) | **System Event Detector** | Bez zmian |

---

## 8. OCENA KATALOGU

### 8.1 Czy katalog jest kompletny?

**Ocena: Katalog jest obszerny i dobrze pokrywa spektrum zdarzeń rynkowych, ale nie jest w pełni kompletny.**

**Mocne strony:**
- Bardzo dobre pokrycie zdarzeń technicznych (34 zdarzenia — pełne spektrum od cenowych po wskaźniki)
- Solidne pokrycie zdarzeń fundamentalnych i korporacyjnych (58 zdarzeń)
- Dobre pokrycie makro (16 zdarzeń)
- Uwzględnienie specyfiki GPW (ESPI, EBI, transakcje pakietowe)

**Potencjalne luki:**
1. **Brak zdarzeń dla kryptowalut** — on-chain metrics (aktywność portfeli, przepływy na giełdy, hash rate), fork events, whale alerts
2. **Brak zdarzeń dla rynku Forex poza głównymi parami** — carry trade unwinding, emerging market currency crises
3. **Brak zdarzeń związanych z ESG** — zmiany ratingów ESG, kontrowersje ekologiczne, nowe regulacje klimatyczne
4. **Brak zdarzeń typu "technical failure"** — błędy w notowaniach, awarie giełd, flash crash detection
5. **Brak zdarzeń związanych z IPO** — debiuty giełdowe, lock-up expiry
6. **Brak zdarzeń związanych z indeksami** — zmiany w składzie indeksów (np. WIG20, S&P 500)

### 8.2 Czy istnieją zdarzenia dublujące się?

**Ocena: Istnieje kilka przypadków częściowego nakładania się zdarzeń.**

| Zdarzenia | Rodzaj dublowania | Rekomendacja |
|-----------|-------------------|-------------|
| 3.1 (Volatility Spike) ↔ 8.3 (ATR Expansion) | Oba mierzą wzrost zmienności przez ATR. 3.1 jest ogólniejszy, 8.3 specyficzny dla ATR | Połączyć w jedno zdarzenie "Volatility Expansion" z konfigurowalną metodą pomiaru (ATR, odchylenie std) |
| 3.3 (BB Expansion) ↔ 3.1 (Volatility Spike) | BB Expansion jest szczególnym przypadkiem wzrostu zmienności | Zachować jako osobne — BB Expansion wskazuje dodatkowo na początek trendu |
| 4.1 (Resistance Breakout) ↔ 1.7 (ATH) | ATH jest szczególnym przypadkiem wybicia oporu (gdy opór = poprzednie ATH) | Zachować jako osobne — ATH ma znaczenie psychologiczne wykraczające poza techniczne |
| 6.1 (MA Crossover) ↔ 7.4 (MACD Crossover) | MACD Crossover jest technicznie przecięciem średnich (12/26 EMA) | Zachować jako osobne — różne zastosowania i interpretacje |
| 43.1 (Breaking News) ↔ 44.1 (Tavily Search Result) | Tavily może być źródłem breaking news | Zachować jako osobne — różne źródła i metody detekcji |

### 8.3 Czy można uprościć katalog?

**Ocena: Tak, istnieje potencjał uproszczenia bez utraty wartości informacyjnej.**

**Propozycje konsolidacji:**

| Obecny stan | Propozycja | Oszczędność |
|-------------|-----------|:---:|
| 3.1 (Volatility Spike) + 8.3 (ATR Expansion) | **Połączyć** w "Volatility Expansion" z parametrem metody | -1 |
| 5.1 (Hammer) + 5.2 (Shooting Star) | **Połączyć** w "Hammer/Shooting Star Pattern" — ta sama logika, różny kontekst | -1 |
| 5.3 (Bullish Engulfing) + 5.4 (Bearish Engulfing) | **Połączyć** w "Engulfing Pattern" | -1 |
| 5.7 (Three White Soldiers) + 5.8 (Three Black Crows) | **Połączyć** w "Three Soldiers/Crows Pattern" | -1 |
| 7.1 (RSI Overbought) + 7.2 (RSI Oversold) | **Połączyć** w "RSI Extreme" | -1 |
| 10.2 (Earnings Beat) + 10.3 (Earnings Miss) | **Połączyć** w "Earnings Surprise" | -1 |
| 11.1 (Quarterly Report) + 11.2 (Annual Report) | **Połączyć** w "Report Filed" z parametrem typu raportu | -1 |
| 15.1 (Split Announcement) + 15.3 (Reverse Split) | **Połączyć** w "Split Event" z kierunkiem | -1 |
| 16.1 + 16.2 + 16.3 (emisje) | **Połączyć** w "Share Issuance" z parametrem typu emisji | -2 |
| 24.1 + 24.2 (pozwy) | **Połączyć** w "Lawsuit Event" z kierunkiem | -1 |
| 29.1 + 29.2 (stopy) | **Połączyć** w "Interest Rate Change" z trybem (regularne/nadzwyczajne) | -1 |
| 34.1 + 46.1 + 46.2 + 35.1 + 35.2 | **Przegrupować** — rotacja sektorowa, korelacje i relacje międzyinstrumentowe mogą być jednym detektorem "Relative Strength & Correlation" | -2 |
| 41.1 + 41.2 + 41.3 | **Połączyć** w "Social Media Signal" z parametrem źródła | -2 |

**Potencjalna redukcja: z ~157 do ~139 zdarzeń (-18, ok. 11%)**

**Zalecenie:** Nie konsolidować na poziomie katalogu. Zamiast tego:
- Zachować szczegółowe zdarzenia w katalogu (czytelność, dokumentacja)
- Konsolidować na poziomie **algorytmów** — jeden algorytm może generować wiele typów zdarzeń z różnymi parametrami
- Użyć systemu tagów/metadanych do grupowania, zamiast redukować liczbę zdarzeń

### 8.4 Czy można zmniejszyć liczbę detektorów dzięki wspólnej logice?

**Ocena: Tak. Z 11 detektorów można zejść do 8 (redukcja o 27%).**

| Obecny detektor | Po scaleniu | Nowa nazwa | Liczba zdarzeń |
|-----------------|-------------|-----------|:---:|
| PRICE + VOLUME | → | **Price & Volume Event Detector** | 15 |
| TECHNICAL | → | **Technical Event Detector** | 34 |
| FUNDAMENTAL | → | **Fundamental Event Detector** | 24 |
| CORPORATE + REGULATORY | → | **Corporate Event Detector** | 37 |
| MACRO | → | **Macro Event Detector** | 16 |
| ETF + DERIVATIVES & ALT | → | **Specialized Instruments Detector** | 13 |
| SENTIMENT & NEWS | → | **Sentiment & News Event Detector** | 11 |
| SYSTEM & CONTEXT | → | **System Event Detector** | 12 |

**Klucz do redukcji:**
1. **Price + Volume** — oba korzystają z tego samego źródła (OHLCV), tego samego silnika (TechnicalEngine), tego samego pipeline'u danych
2. **Corporate + Regulatory** — ESPI/EBI to po prostu specyficzne dla GPW kanały komunikacji korporacyjnej; logika wykrywania jest analogiczna (monitorowanie źródła → parsowanie → klasyfikacja)
3. **ETF + Derivatives & Alt** — oba dotyczą specjalistycznych instrumentów wymagających niestandardowych źródeł danych spoza podstawowego OHLCV

**Uwaga:** Redukcja liczby detektorów **nie oznacza** redukcji liczby zdarzeń. Jeden detektor może wykrywać wiele typów zdarzeń.

---

## KONIEC DOKUMENTU

Data utworzenia: 18.07.2026
Wersja: 1.0
Autor: Zespół ALCHEMIK
Status: Dokument architektoniczny — hierarchia zdarzeń rynkowych
Bazuje na: `docs/Katalog_Zdarzen_Rynkowych.md` v2.0

Następny krok po zatwierdzeniu hierarchii: specyfikacja interfejsów dla każdego detektora.