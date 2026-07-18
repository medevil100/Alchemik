# ALCHEMIK — KATALOG ZDARZEŃ RYNKOWYCH

## DOKUMENT PROJEKTOWY — SPECYFIKACJA FUNKCJONALNA

Data: 18.07.2026
Wersja: 2.0

---

## SPIS TREŚCI

1. [Zakres pierwszego etapu](#0-zakres-pierwszego-etapu)
2. [Zdarzenia cenowe](#1-zdarzenia-cenowe)
3. [Zdarzenia wolumenowe](#2-zdarzenia-wolumenowe)
4. [Zdarzenia zmienności](#3-zdarzenia-zmienności)
5. [Wybicia techniczne](#4-wybicia-techniczne)
6. [Formacje świecowe](#5-formacje-świecowe)
7. [Trend](#6-trend)
8. [Momentum](#7-momentum)
9. [Wskaźniki techniczne](#8-wskaźniki-techniczne)
10. [Fundamenty spółki](#9-fundamenty-spółki)
11. [Wyniki finansowe](#10-wyniki-finansowe)
12. [Raporty kwartalne](#11-raporty-kwartalne)
13. [ESPI](#12-espi)
14. [EBI](#13-ebi)
15. [Dywidendy](#14-dywidendy)
16. [Splity](#15-splity)
17. [Emisje akcji](#16-emisje-akcji)
18. [Skup akcji własnych](#17-skup-akcji-własnych)
19. [Insider Trading](#18-insider-trading)
20. [Zmiany akcjonariatu](#19-zmiany-akcjonariatu)
21. [Rekomendacje analityków](#20-rekomendacje-analityków)
22. [Ratingi](#21-ratingi)
23. [Fuzje i przejęcia](#22-fuzje-i-przejęcia)
24. [Nowe kontrakty](#23-nowe-kontrakty)
25. [Pozwy](#24-pozwy)
26. [Problemy prawne](#25-problemy-prawne)
27. [Upadłości i restrukturyzacje](#26-upadłości-i-restrukturyzacje)
28. [Zmiany zarządu](#27-zmiany-zarządu)
29. [Makroekonomia](#28-makroekonomia)
30. [Stopy procentowe](#29-stopy-procentowe)
31. [Inflacja](#30-inflacja)
32. [Waluty](#31-waluty)
33. [Surowce](#32-surowce)
34. [Geopolityka](#33-geopolityka)
35. [Sektor](#34-sektor)
36. [Korelacje](#35-korelacje)
37. [ETF](#36-etf)
38. [Opcje](#37-opcje)
39. [Short Interest](#38-short-interest)
40. [Dark Pool](#39-dark-pool)
41. [Nietypowe transakcje](#40-nietypowe-transakcje)
42. [Media społecznościowe](#41-media-społecznościowe)
43. [Sentyment rynku](#42-sentyment-rynku)
44. [News](#43-news)
45. [Tavily](#44-tavily)
46. [Alerty własne ALCHEMIKA](#45-alerty-własne-alchemika)
47. [Zdarzenia międzyinstrumentowe](#46-zdarzenia-międzyinstrumentowe)
48. [Zdarzenia sezonowe i kalendarzowe](#47-zdarzenia-sezonowe-i-kalendarzowe)
49. [Tabela: Zdarzenia × Źródła danych](#tabela-zdarzenia-×-źródła-danych)
50. [Tabela: Klasyfikacja wg grup instrumentów](#tabela-klasyfikacja-wg-grup-instrumentów)
51. [Tabela: Priorytet wdrożenia](#tabela-priorytet-wdrożenia)

---

## 0. ZAKRES PIERWSZEGO ETAPU

### 0.1 Trzy grupy instrumentów

Pierwszy etap ALCHEMIKA koncentruje się na trzech grupach instrumentów:

| Grupa | Oznaczenie | Opis | Przykładowe instrumenty |
|-------|-----------|------|--------------------------|
| **Groszówki GPW** | `[GPW]` | Akcje notowane na Giełdzie Papierów Wartościowych w Warszawie (rynek główny + NewConnect) o niskiej cenie nominalnej i małej kapitalizacji | Spółki o cenie < 10 PLN, małe i mikro spółki |
| **Groszówki USA** | `[USA]` | Akcje notowane na NYSE, NASDAQ, AMEX o cenie < 5 USD (klasyczne "penny stocks") | Small-cap, micro-cap, spółki o niskim floacie |
| **ETF** | `[ETF]` | Fundusze ETF notowane na giełdach amerykańskich i europejskich | ETF sektorowe, tematyczne, lewarowane, inverse |

### 0.2 Zasada rozszerzalności

ALCHEMIK jest platformą modułową. Katalog zdarzeń zaprojektowano z myślą o przyszłej rozbudowie o:

- Nowe moduły (np. dedykowany moduł kryptowalut)
- Nowe silniki (np. silnik analizy międzyrynkowej)
- Nowe źródła danych (np. Bloomberg API, Refinitiv)
- Nowe rodzaje zdarzeń (np. zdarzenia on-chain dla krypto)
- Nowe giełdy (np. LSE, TSE, XETRA)
- Nowe klasy aktywów (indeksy, surowce, waluty, kryptowaluty, obligacje, opcje, futures)

Obecna architektura rdzenia jest zamrożona — nowe możliwości są projektowane jako rozszerzenia, nie jako modyfikacje istniejących silników i ich Public API.

### 0.3 Legenda klasyfikacji

Każde zdarzenie otrzymuje następujące oznaczenia:

**Grupa instrumentów:**
- `[GPW]` — szczególnie istotne dla groszówek GPW
- `[USA]` — szczególnie istotne dla groszówek USA
- `[ETF]` — szczególnie istotne dla ETF
- `[Universal]` — istotne dla wszystkich trzech grup

**Priorytet wdrożenia:**
- `[v1]` — pierwsza wersja produkcyjna (MVP detektora zdarzeń)
- `[Future]` — do dodania w przyszłych iteracjach

---

## 1. ZDARZENIA CENOWE

### 1.1 Nagły wzrost ceny (Price Surge)
- **Opis**: Cena instrumentu wzrosła o X% w ciągu jednej świecy (lub krótkiego okna czasowego) w stosunku do ceny zamknięcia poprzedniej świecy.
- **Dlaczego ważne**: Może wskazywać na napływ istotnych informacji, rozpoczęcie trendu wzrostowego, short squeeze lub manipulację.
- **Potrzebne dane**: OHLCV — co najmniej dwie kolejne świece (poprzednia i bieżąca).
- **yfinance**: TAK — dane OHLCV z `YahooFetcher`.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (analiza cen) + ewentualnie NewsEngine (przyczyna ruchu).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

### 1.2 Nagły spadek ceny (Price Drop)
- **Opis**: Cena instrumentu spadła o X% w ciągu jednej świecy (lub krótkiego okna czasowego) w stosunku do ceny zamknięcia poprzedniej świecy.
- **Dlaczego ważne**: Może sygnalizować panikę, złe wiadomości, rozpoczęcie trendu spadkowego, stop-loss cascade.
- **Potrzebne dane**: OHLCV — co najmniej dwie kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + NewsEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

### 1.3 Luka cenowa w górę (Gap Up)
- **Opis**: Cena otwarcia bieżącej świecy jest znacząco wyższa niż cena zamknięcia poprzedniej świecy (lub high poprzedniej świecy).
- **Dlaczego ważne**: Wskazuje na silny popyt poza godzinami handlu, reakcję na newsy, potencjalny breakout.
- **Potrzebne dane**: OHLCV — open bieżącej świecy, close/high poprzedniej świecy.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 1.4 Luka cenowa w dół (Gap Down)
- **Opis**: Cena otwarcia bieżącej świecy jest znacząco niższa niż cena zamknięcia poprzedniej świecy (lub low poprzedniej świecy).
- **Dlaczego ważne**: Wskazuje na silną podaż poza godzinami handlu, reakcję na negatywne newsy.
- **Potrzebne dane**: OHLCV — open bieżącej świecy, close/low poprzedniej świecy.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 1.5 Nowe maksimum 52-tygodniowe (52-Week High)
- **Opis**: Cena instrumentu osiągnęła najwyższy poziom w ciągu ostatnich 52 tygodni.
- **Dlaczego ważne**: Sygnał siły, potencjalny breakout, przyciąga uwagę inwestorów i mediów.
- **Potrzebne dane**: OHLCV — 260 świec dziennych (minimum), high z każdej świecy.
- **yfinance**: TAK (260 dni = ~52 tygodnie handlowe).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[USA]` (penny stocks przyciągają uwagę po breakoutach)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 1.6 Nowe minimum 52-tygodniowe (52-Week Low)
- **Opis**: Cena instrumentu osiągnęła najniższy poziom w ciągu ostatnich 52 tygodni.
- **Dlaczego ważne**: Sygnał słabości, potencjalny breakdown, może przyciągać łowców okazji lub sygnalizować problemy fundamentalne.
- **Potrzebne dane**: OHLCV — 260 świec dziennych, low z każdej świecy.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[GPW]` (ryzyko delistingu na NewConnect)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 1.7 Nowe maksimum historyczne (All-Time High)
- **Opis**: Cena instrumentu osiągnęła najwyższy poziom w całej dostępnej historii notowań.
- **Dlaczego ważne**: Silny sygnał byczy, brak oporów technicznych powyżej, przyciąga uwagę rynku.
- **Potrzebne dane**: OHLCV — pełna historia notowań (max dostępne z yfinance).
- **yfinance**: TAK (period="max").
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (ETF na ATH = potwierdzenie trendu sektorowego)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 1.8 Nowe minimum historyczne (All-Time Low)
- **Opis**: Cena instrumentu osiągnęła najniższy poziom w całej dostępnej historii notowań.
- **Dlaczego ważne**: Skrajnie negatywny sygnał, może wskazywać na problemy egzystencjalne spółki.
- **Potrzebne dane**: OHLCV — pełna historia notowań.
- **yfinance**: TAK (period="max").
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie krytyczne dla groszówek (ryzyko bankructwa/delistingu)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

### 1.9 Odrzucenie poziomu (Level Rejection)
- **Opis**: Cena zbliżyła się do istotnego poziomu wsparcia/oporu i gwałtownie się od niego odbiła.
- **Dlaczego ważne**: Potwierdza ważność poziomu technicznego, sygnalizuje potencjalny reversal.
- **Potrzebne dane**: OHLCV + poziomy wsparcia/oporu (obliczone z historycznych danych).
- **yfinance**: TAK (do obliczenia poziomów).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 1.10 Przekroczenie poziomu psychologicznego (Psychological Level Cross)
- **Opis**: Cena przekroczyła okrągły poziom (np. 10, 50, 100, 1000 PLN/USD).
- **Dlaczego ważne**: Poziomy psychologiczne często działają jako wsparcie/opór, ich przekroczenie ma znaczenie psychologiczne dla inwestorów.
- **Potrzebne dane**: OHLCV — bieżąca cena.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[USA]` (poziomy $1, $5 są kluczowe dla penny stocks)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 2. ZDARZENIA WOLUMENOWE

### 2.1 Skok wolumenu (Volume Spike)
- **Opis**: Wolumen bieżącej świecy przekracza X-krotność średniego wolumenu z ostatnich N świec.
- **Dlaczego ważne**: Niezwykły wolumen często poprzedza istotne ruchy cenowe, wskazuje na akumulację lub dystrybucję.
- **Potrzebne dane**: OHLCV — volume z bieżącej świecy + średnia z N poprzednich.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (wykorzystuje istniejący wskaźnik RVOL).
- **Grupa**: `[Universal]` — szczególnie istotne dla `[GPW]` i `[USA]` (nagły wzrost wolumenu na groszówkach często poprzedza duże ruchy)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

### 2.2 Wolumen bliski zeru (Near-Zero Volume)
- **Opis**: Wolumen spadł poniżej minimalnego progu (np. <10% średniej).
- **Dlaczego ważne**: Może wskazywać na brak zainteresowania, potencjalne problemy z płynnością, ryzyko manipulacji.
- **Potrzebne dane**: OHLCV — volume.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[GPW]` — szczególnie istotne dla małych spółek na GPW/NewConnect (niska płynność = ryzyko)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 2.3 Wolumen kumulacyjny (Cumulative Volume Anomaly)
- **Opis**: Suma wolumenu z ostatnich N świec znacząco odbiega od średniej sumy z porównywalnych okresów.
- **Dlaczego ważne**: Wskazuje na długotrwałą akumulację lub dystrybucję, często przed dużymi ruchami.
- **Potrzebne dane**: OHLCV — volume z wielu świec.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 2.4 Wolumen na spadkach (High Volume on Down Days)
- **Opis**: Wolumen na świecach spadkowych jest znacząco wyższy niż na świecach wzrostowych w ostatnim oknie.
- **Dlaczego ważne**: Sygnalizuje dystrybucję — duzi gracze sprzedają na spadkach.
- **Potrzebne dane**: OHLCV — volume + kierunek świecy (close vs open).
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (odpływy z ETF sektorowych)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 2.5 Wolumen na wzrostach (High Volume on Up Days)
- **Opis**: Wolumen na świecach wzrostowych jest znacząco wyższy niż na świecach spadkowych w ostatnim oknie.
- **Dlaczego ważne**: Sygnalizuje akumulację — duzi gracze kupują na wzrostach.
- **Potrzebne dane**: OHLCV — volume + kierunek świecy.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (napływy do ETF sektorowych)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

---

## 3. ZDARZENIA ZMIENNOŚCI

### 3.1 Wzrost zmienności (Volatility Spike)
- **Opis**: Zmienność (mierzona ATR lub odchyleniem standardowym) wzrosła o X% w stosunku do średniej z ostatnich N okresów.
- **Dlaczego ważne**: Wzrost zmienności często poprzedza duże ruchy kierunkowe lub sygnalizuje niepewność.
- **Potrzebne dane**: OHLCV — high, low, close z wielu świec.
- **yfinance**: TAK (ATR już zaimplementowany).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[GPW]` i `[USA]` (groszówki są z natury zmienne, spike = okazja)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 3.2 Spadek zmienności (Volatility Contraction)
- **Opis**: Zmienność spadła poniżej X% średniej — rynek się "ściska".
- **Dlaczego ważne**: Okresy niskiej zmienności często kończą się gwałtownym wybiciem (Bollinger Squeeze).
- **Potrzebne dane**: OHLCV — ATR lub Bollinger Bands width.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 3.3 Rozszerzenie wstęg Bollingera (Bollinger Band Expansion)
- **Opis**: Szerokość wstęg Bollingera (upper - lower) przekroczyła X-krotność średniej szerokości.
- **Dlaczego ważne**: Sygnalizuje początek nowego trendu po okresie konsolidacji.
- **Potrzebne dane**: OHLCV — Bollinger Bands (już zaimplementowane).
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 3.4 Zwężenie wstęg Bollingera (Bollinger Band Squeeze)
- **Opis**: Szerokość wstęg Bollingera spadła poniżej X% średniej — rynek w konsolidacji.
- **Dlaczego ważne**: Zapowiada nadchodzące silne wybicie kierunkowe.
- **Potrzebne dane**: OHLCV — Bollinger Bands.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

---

## 4. WYBICIA TECHNICZNE

### 4.1 Wybicie powyżej oporu (Resistance Breakout)
- **Opis**: Cena zamknięcia przekroczyła zidentyfikowany poziom oporu (np. poprzedni swing high, poziom horyzontalny).
- **Dlaczego ważne**: Sygnał kontynuacji trendu wzrostowego, potencjalny sygnał kupna.
- **Potrzebne dane**: OHLCV — close + historyczne szczyty.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 4.2 Wybicie poniżej wsparcia (Support Breakdown)
- **Opis**: Cena zamknięcia spadła poniżej zidentyfikowanego poziomu wsparcia.
- **Dlaczego ważne**: Sygnał kontynuacji trendu spadkowego, potencjalny sygnał sprzedaży.
- **Potrzebne dane**: OHLCV — close + historyczne dołki.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

### 4.3 Wybicie z formacji trójkąta (Triangle Breakout)
- **Opis**: Cena wybiła się z formacji trójkąta (symetrycznego, zwyżkującego, zniżkującego).
- **Dlaczego ważne**: Formacje trójkąta często poprzedzają silne ruchy kierunkowe.
- **Potrzebne dane**: OHLCV — seria cen do identyfikacji formacji.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 4.4 Wybicie z kanału (Channel Breakout)
- **Opis**: Cena wybiła się powyżej górnej lub poniżej dolnej linii kanału trendowego.
- **Dlaczego ważne**: Sygnalizuje przyspieszenie lub odwrócenie trendu.
- **Potrzebne dane**: OHLCV — seria cen do identyfikacji kanału.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 4.5 Wybicie z flagi/chorągiewki (Flag/Pennant Breakout)
- **Opis**: Cena wybiła się z formacji flagi lub chorągiewki — formacji kontynuacji trendu.
- **Dlaczego ważne**: Silny sygnał kontynuacji trendu po krótkiej konsolidacji.
- **Potrzebne dane**: OHLCV — seria cen.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 5. FORMACJE ŚWIECOWE

### 5.1 Młot / Wisielec (Hammer / Hanging Man)
- **Opis**: Świeca z małym korpusem i długim dolnym cieniem (co najmniej 2× długość korpusu), górny cień bardzo mały lub brak.
- **Dlaczego ważne**: Młot na dole trendu spadkowego = potencjalne odwrócenie w górę. Wisielec na górze trendu wzrostowego = potencjalne odwrócenie w dół.
- **Potrzebne dane**: OHLCV — pojedyncza świeca + kontekst trendu.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 5.2 Spadająca gwiazda / Odwrócony młot (Shooting Star / Inverted Hammer)
- **Opis**: Świeca z małym korpusem i długim górnym cieniem (co najmniej 2× długość korpusu), dolny cień bardzo mały lub brak.
- **Dlaczego ważne**: Spadająca gwiazda na górze trendu = potencjalne odwrócenie w dół. Odwrócony młot na dole = potencjalne odwrócenie w górę.
- **Potrzebne dane**: OHLCV — pojedyncza świeca + kontekst trendu.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 5.3 Formacja objęcia hossy (Bullish Engulfing)
- **Opis**: Świeca wzrostowa całkowicie "pochłania" korpus poprzedniej świecy spadkowej (open < poprzedni close, close > poprzedni open).
- **Dlaczego ważne**: Silny sygnał odwrócenia trendu w górę.
- **Potrzebne dane**: OHLCV — dwie kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 5.4 Formacja objęcia bessy (Bearish Engulfing)
- **Opis**: Świeca spadkowa całkowicie "pochłania" korpus poprzedniej świecy wzrostowej.
- **Dlaczego ważne**: Silny sygnał odwrócenia trendu w dół.
- **Potrzebne dane**: OHLCV — dwie kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 5.5 Doji (Doji)
- **Opis**: Świeca, której cena otwarcia i zamknięcia są prawie identyczne (korpus bardzo mały).
- **Dlaczego ważne**: Sygnalizuje niezdecydowanie rynku, potencjalne odwrócenie trendu.
- **Potrzebne dane**: OHLCV — pojedyncza świeca.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 5.6 Gwiazda poranna / Gwiazda wieczorna (Morning Star / Evening Star)
- **Opis**: Formacja 3-świecowa: (1) duża świeca w kierunku trendu, (2) mała świeca/doji z luką, (3) duża świeca przeciwna.
- **Dlaczego ważne**: Silny sygnał odwrócenia trendu.
- **Potrzebne dane**: OHLCV — trzy kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 5.7 Trzech białych żołnierzy (Three White Soldiers)
- **Opis**: Trzy kolejne świece wzrostowe z coraz wyższymi zamknięciami, każda otwiera się wewnątrz poprzedniego korpusu.
- **Dlaczego ważne**: Silny sygnał kontynuacji lub odwrócenia trendu wzrostowego.
- **Potrzebne dane**: OHLCV — trzy kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 5.8 Trzy czarne kruki (Three Black Crows)
- **Opis**: Trzy kolejne świece spadkowe z coraz niższymi zamknięciami.
- **Dlaczego ważne**: Silny sygnał kontynuacji lub odwrócenia trendu spadkowego.
- **Potrzebne dane**: OHLCV — trzy kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 5.9 Marubozu (Marubozu)
- **Opis**: Świeca bez cieni (lub z bardzo małymi cieniami) — cały korpus, open = low, close = high (lub odwrotnie).
- **Dlaczego ważne**: Wskazuje na skrajną dominację jednej strony rynku.
- **Potrzebne dane**: OHLCV — pojedyncza świeca.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 5.10 Harami (Harami)
- **Opis**: Mała świeca całkowicie zawarta w korpusie poprzedniej, dużej świecy.
- **Dlaczego ważne**: Sygnalizuje potencjalne odwrócenie trendu.
- **Potrzebne dane**: OHLCV — dwie kolejne świece.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (moduł `candle.py`).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 6. TREND

### 6.1 Przecięcie średnich kroczących (Moving Average Crossover)
- **Opis**: Krótsza średnia krocząca (np. SMA 20) przecięła dłuższą (np. SMA 50) od dołu (złoty krzyż) lub od góry (krzyż śmierci).
- **Dlaczego ważne**: Klasyczny sygnał zmiany trendu używany przez szerokie grono inwestorów.
- **Potrzebne dane**: OHLCV — close z minimum 50 świec.
- **yfinance**: TAK (SMA/EMA już zaimplementowane).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 6.2 Zmiana kierunku średniej kroczącej (MA Slope Change)
- **Opis**: Nachylenie średniej kroczącej zmieniło znak (z rosnącego na malejący lub odwrotnie).
- **Dlaczego ważne**: Wczesny sygnał potencjalnej zmiany trendu.
- **Potrzebne dane**: OHLCV — close z minimum N świec.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 6.3 Cena powyżej/poniżej średniej (Price vs MA)
- **Opis**: Cena przekroczyła kluczową średnią kroczącą (np. SMA 200) od dołu lub od góry.
- **Dlaczego ważne**: SMA 200 jest powszechnie uważana za wskaźnik długoterminowego trendu.
- **Potrzebne dane**: OHLCV — close + SMA 200.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 6.4 Seria wzrostowych/spadkowych świec (Consecutive Up/Down Candles)
- **Opis**: N kolejnych świec zamknęło się wyżej/niżej niż poprzednia.
- **Dlaczego ważne**: Wskazuje na silny, jednokierunkowy momentum.
- **Potrzebne dane**: OHLCV — close z N świec.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 6.5 Zmiana struktury trendu (Trend Structure Change)
- **Opis**: Wyższy dołek po serii niższych dołków (lub niższy szczyt po serii wyższych szczytów) — zmiana struktury swingów.
- **Dlaczego ważne**: Fundamentalna zmiana w strukturze rynku, używana przez Price Action traderów.
- **Potrzebne dane**: OHLCV — swing high/low z wielu świec.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

---

## 7. MOMENTUM

### 7.1 RSI — wykupienie (RSI Overbought)
- **Opis**: Wskaźnik RSI przekroczył poziom X (np. 70) — rynek wykupiony.
- **Dlaczego ważne**: Sygnalizuje potencjalne krótkoterminowe odwrócenie lub korektę.
- **Potrzebne dane**: OHLCV — close z 14 świec.
- **yfinance**: TAK (RSI już zaimplementowany).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 7.2 RSI — wyprzedanie (RSI Oversold)
- **Opis**: Wskaźnik RSI spadł poniżej poziomu X (np. 30) — rynek wyprzedany.
- **Dlaczego ważne**: Sygnalizuje potencjalne odbicie.
- **Potrzebne dane**: OHLCV — close z 14 świec.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[GPW]` i `[USA]` (wyprzedane groszówki = potencjalne odbicie)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 7.3 Dywergencja RSI (RSI Divergence)
- **Opis**: Cena robi wyższy szczyt, a RSI niższy szczyt (niedźwiedzia dywergencja) — lub odwrotnie (bycza dywergencja).
- **Dlaczego ważne**: Silny sygnał ostrzegawczy przed odwróceniem trendu.
- **Potrzebne dane**: OHLCV — close + RSI z minimum 20-30 świec.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 7.4 MACD — przecięcie linii (MACD Line Crossover)
- **Opis**: Linia MACD przecięła linię sygnalną od dołu (sygnał byczy) lub od góry (sygnał niedźwiedzi).
- **Dlaczego ważne**: Jeden z najpopularniejszych sygnałów momentum.
- **Potrzebne dane**: OHLCV — close z minimum 26 świec.
- **yfinance**: TAK (MACD już zaimplementowany).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 7.5 MACD — przecięcie zera (MACD Zero Cross)
- **Opis**: Linia MACD przekroczyła poziom zero od dołu lub od góry.
- **Dlaczego ważne**: Sygnalizuje zmianę średnioterminowego trendu.
- **Potrzebne dane**: OHLCV — close + MACD.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 7.6 Stochastic — wykupienie/wyprzedanie (Stochastic Overbought/Oversold)
- **Opis**: Oscylator Stochastic przekroczył 80 (wykupienie) lub spadł poniżej 20 (wyprzedanie).
- **Dlaczego ważne**: Krótkoterminowy sygnał odwrócenia.
- **Potrzebne dane**: OHLCV — high, low, close z 14 świec.
- **yfinance**: TAK (do zaimplementowania — brak w obecnym kodzie).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 8. WSKAŹNIKI TECHNICZNE

### 8.1 OBV — dywergencja (OBV Divergence)
- **Opis**: Cena rośnie, ale OBV (On-Balance Volume) spada — lub odwrotnie.
- **Dlaczego ważne**: Dywergencja OBV sugeruje, że ruch cenowy nie jest potwierdzony przez wolumen.
- **Potrzebne dane**: OHLCV — close + volume.
- **yfinance**: TAK (OBV już zaimplementowany).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 8.2 VWAP — odchylenie (VWAP Deviation)
- **Opis**: Cena znacząco odbiega od VWAP (Volume-Weighted Average Price).
- **Dlaczego ważne**: VWAP jest używany przez instytucje do oceny jakości wykonania; duże odchylenie może sygnalizować nierównowagę.
- **Potrzebne dane**: OHLCV — high, low, close, volume (śród dziennie).
- **yfinance**: TAK (VWAP już zaimplementowany, ale wymaga danych intraday).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 8.3 ATR — wzrost (ATR Expansion)
- **Opis**: ATR wzrósł o X% w stosunku do swojej średniej.
- **Dlaczego ważne**: Wzrost ATR potwierdza siłę ruchu i zwiększa prawdopodobieństwo kontynuacji.
- **Potrzebne dane**: OHLCV — high, low, close z 14 świec.
- **yfinance**: TAK (ATR już zaimplementowany).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Średni**

### 8.4 Fibonacci — zniesienie (Fibonacci Retracement Hit)
- **Opis**: Cena dotarła do kluczowego poziomu zniesienia Fibonacciego (38.2%, 50%, 61.8%) i zareagowała.
- **Dlaczego ważne**: Poziomy Fibonacciego są powszechnie obserwowane przez traderów.
- **Potrzebne dane**: OHLCV — swing high + swing low.
- **yfinance**: TAK (Fibonacci już zaimplementowany).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 9. FUNDAMENTY SPÓŁKI

### 9.1 Zmiana wskaźnika P/E (P/E Ratio Change)
- **Opis**: Wskaźnik Cena/Zysk znacząco się zmienił (wzrósł/spadł o X%).
- **Dlaczego ważne**: Podstawowy wskaźnik wyceny; ekstremalne wartości mogą sygnalizować przewartościowanie lub niedowartościowanie.
- **Potrzebne dane**: Cena akcji + zysk na akcję (EPS).
- **yfinance**: TAK (`ticker.info` zawiera trailingPE, forwardPE).
- **Dodatkowe źródła**: Dane finansowe spółek (dla EPS).
- **Silnik**: AnalystEngine + HunterEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 9.2 Zmiana wskaźnika P/BV (P/BV Ratio Change)
- **Opis**: Wskaźnik Cena/Wartość księgowa znacząco się zmienił.
- **Dlaczego ważne**: Używany do wyceny spółek asset-heavy (banki, ubezpieczyciele).
- **Potrzebne dane**: Cena akcji + wartość księgowa na akcję.
- **yfinance**: TAK (`ticker.info` zawiera priceToBook).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 9.3 Zmiana kapitalizacji rynkowej (Market Cap Change)
- **Opis**: Kapitalizacja rynkowa spółki zmieniła się o X% (poza normalnymi wahaniami ceny — np. po emisji/skupie akcji).
- **Dlaczego ważne**: Zmiana kapitalizacji wpływa na klasyfikację spółki (small/mid/large cap) i zainteresowanie inwestorów instytucjonalnych.
- **Potrzebne dane**: Cena akcji + liczba akcji (shares outstanding).
- **yfinance**: TAK (`ticker.info` zawiera marketCap).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (przekroczenie progów small/micro cap)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 9.4 Zmiana zadłużenia (Debt Change)
- **Opis**: Wskaźnik zadłużenia (Debt/Equity) znacząco wzrósł lub spadł.
- **Dlaczego ważne**: Wysokie zadłużenie zwiększa ryzyko finansowe spółki.
- **Potrzebne dane**: Dane bilansowe spółki.
- **yfinance**: Częściowo (`ticker.info` zawiera debtToEquity).
- **Dodatkowe źródła**: Raporty finansowe, ESPI.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (wysokie zadłużenie = ryzyko bankructwa)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 9.5 Zmiana przychodów (Revenue Change)
- **Opis**: Przychody spółki znacząco wzrosły lub spadły w porównaniu do poprzedniego okresu.
- **Dlaczego ważne**: Wzrost przychodów jest podstawowym wskaźnikiem rozwoju spółki.
- **Potrzebne dane**: Raporty kwartalne/roczne.
- **yfinance**: Częściowo (`ticker.quarterly_financials`).
- **Dodatkowe źródła**: ESPI, EBI, raporty finansowe.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

### 9.6 Zmiana zysku netto (Net Income Change)
- **Opis**: Zysk netto spółki znacząco wzrósł lub spadł.
- **Dlaczego ważne**: Rentowność jest kluczowa dla długoterminowej wartości spółki.
- **Potrzebne dane**: Raporty finansowe.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: ESPI, EBI.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Wysoki**

---

## 10. WYNIKI FINANSOWE

### 10.1 Publikacja wyników kwartalnych (Quarterly Earnings Release)
- **Opis**: Spółka opublikowała wyniki finansowe za ostatni kwartał.
- **Dlaczego ważne**: Wyniki kwartalne często powodują gwałtowne ruchy cenowe.
- **Potrzebne dane**: Kalendarz publikacji + same wyniki.
- **yfinance**: Częściowo (daty earningsów w `ticker.calendar`).
- **Dodatkowe źródła**: ESPI, EBI, strony spółek, kalendarze giełdowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF (ale dotyczy spółek wchodzących w skład ETF)
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

### 10.2 Wyniki powyżej oczekiwań (Earnings Beat)
- **Opis**: Opublikowane wyniki (EPS, przychody) są znacząco wyższe od konsensusu analityków.
- **Dlaczego ważne**: Pozytywne zaskoczenie często prowadzi do silnych wzrostów.
- **Potrzebne dane**: Wyniki rzeczywiste + konsensus analityków.
- **yfinance**: Częściowo (`ticker.earnings` zawiera surprise).
- **Dodatkowe źródła**: Serwisy finansowe, Bloomberg, Reuters.
- **Silnik**: AnalystEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (earnings beat na małej spółce = duży ruch %)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 10.3 Wyniki poniżej oczekiwań (Earnings Miss)
- **Opis**: Opublikowane wyniki są znacząco niższe od konsensusu.
- **Dlaczego ważne**: Negatywne zaskoczenie często prowadzi do silnych spadków.
- **Potrzebne dane**: Wyniki rzeczywiste + konsensus.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Serwisy finansowe.
- **Silnik**: AnalystEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (earnings miss = ryzyko gwałtownej przeceny)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 10.4 Korekta prognoz (Guidance Update)
- **Opis**: Spółka podniosła lub obniżyła prognozy finansowe na przyszłe okresy.
- **Dlaczego ważne**: Zmiana prognoz wpływa na oczekiwania rynku co do przyszłych wyników.
- **Potrzebne dane**: Komunikaty spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, EBI, komunikaty prasowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[v1]`
- **Priorytet**: **Krytyczny**

---

## 11. RAPORTY KWARTALNE

### 11.1 Publikacja raportu kwartalnego (Quarterly Report Filed)
- **Opis**: Spółka złożyła raport kwartalny do odpowiedniego organu (KRS, SEC itp.).
- **Dlaczego ważne**: Raport zawiera szczegółowe dane finansowe, które mogą nie być widoczne w skróconych wynikach.
- **Potrzebne dane**: Informacja o publikacji + link do raportu.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI (GPW), EDGAR (SEC), strony spółek.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 11.2 Publikacja raportu rocznego (Annual Report Filed)
- **Opis**: Spółka opublikowała raport roczny.
- **Dlaczego ważne**: Raport roczny zawiera najbardziej kompletne dane, w tym audytowane sprawozdania finansowe.
- **Potrzebne dane**: Informacja o publikacji.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, EDGAR, strony spółek.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 11.3 Zmiana polityki rachunkowości (Accounting Policy Change)
- **Opis**: Spółka zmieniła politykę rachunkowości, co wpływa na porównywalność wyników.
- **Dlaczego ważne**: Może maskować rzeczywiste problemy finansowe.
- **Potrzebne dane**: Informacja z raportu.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Raporty finansowe, ESPI.
- **Silnik**: AnalystEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 12. ESPI

### 12.1 Nowy komunikat ESPI (New ESPI Filing)
- **Opis**: Spółka notowana na GPW opublikowała nowy komunikat w systemie ESPI.
- **Dlaczego ważne**: ESPI to podstawowe źródło informacji o spółkach na GPW — każdy komunikat może być cenotwórczy.
- **Potrzebne dane**: Treść komunikatu ESPI.
- **yfinance**: NIE.
- **Dodatkowe źródła**: System ESPI GPW (espi.gpw.pl), scraper lub API.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` — wyłącznie dla GPW
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 12.2 ESPI — opóźnienie publikacji (ESPI Filing Delay)
- **Opis**: Spółka nie opublikowała wymaganego raportu w terminie.
- **Dlaczego ważne**: Opóźnienie może sygnalizować problemy wewnętrzne lub potencjalne nieprawidłowości.
- **Potrzebne dane**: Kalendarz publikacji + status.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, kalendarz GPW.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` — wyłącznie dla GPW
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 13. EBI

### 13.1 Nowy komunikat EBI (New EBI Filing)
- **Opis**: Spółka z NewConnect opublikowała nowy komunikat w systemie EBI.
- **Dlaczego ważne**: Odpowiednik ESPI dla rynku NewConnect — kluczowe źródło dla groszówek GPW.
- **Potrzebne dane**: Treść komunikatu EBI.
- **yfinance**: NIE.
- **Dodatkowe źródła**: System EBI (newconnect.pl).
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` — wyłącznie dla GPW (NewConnect)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

---

## 14. DYWIDENDY

### 14.1 Ogłoszenie dywidendy (Dividend Announcement)
- **Opis**: Spółka ogłosiła wypłatę dywidendy.
- **Dlaczego ważne**: Dywidenda wpływa na wycenę akcji i może przyciągnąć inwestorów dywidendowych.
- **Potrzebne dane**: Kwota dywidendy na akcję, data ustalenia prawa, data wypłaty.
- **yfinance**: Częściowo (`ticker.dividends` — dane historyczne).
- **Dodatkowe źródła**: ESPI, EBI, komunikaty spółek.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` `[ETF]` — ETF wypłacają dywidendy od posiadanych akcji
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 14.2 Zmiana polityki dywidendowej (Dividend Policy Change)
- **Opis**: Spółka zmieniła politykę dywidendową (np. zawiesiła dywidendę, zwiększyła payout ratio).
- **Dlaczego ważne**: Sygnalizuje zmianę strategii finansowej spółki.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 14.3 Dywidenda nadzwyczajna (Special Dividend)
- **Opis**: Spółka ogłosiła wypłatę dywidendy nadzwyczajnej (poza standardowym harmonogramem).
- **Dlaczego ważne**: Może sygnalizować nadmiar gotówki, sprzedaż aktywów lub brak pomysłów na reinwestycję.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 14.4 Dzień ustalenia prawa do dywidendy (Ex-Dividend Date)
- **Opis**: Zbliża się lub nadszedł dzień, po którym akcje są notowane bez prawa do dywidendy.
- **Dlaczego ważne**: Cena akcji zazwyczaj spada o wartość dywidendy w dniu ex-dividend.
- **Potrzebne dane**: Kalendarz dywidend.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Kalendarze giełdowe.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` `[ETF]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 15. SPLITY

### 15.1 Ogłoszenie splitu (Stock Split Announcement)
- **Opis**: Spółka ogłosiła planowany split akcji (np. 2:1, 10:1).
- **Dlaczego ważne**: Split zwiększa dostępność akcji dla drobnych inwestorów, często prowadzi do wzrostu ceny.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: Częściowo (`ticker.splits` — dane historyczne).
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` `[ETF]` — ETF również podlegają splitom
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 15.2 Wykonanie splitu (Stock Split Execution)
- **Opis**: Split akcji został zrealizowany — zmiana liczby akcji i ceny.
- **Dlaczego ważne**: Wpływa na dane historyczne i wskaźniki techniczne.
- **Potrzebne dane**: Data i stosunek splitu.
- **yfinance**: TAK (dane historyczne).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine (korekta danych).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 15.3 Rewers splitu (Reverse Split)
- **Opis**: Spółka przeprowadziła scalenie akcji (reverse split, np. 1:10).
- **Dlaczego ważne**: Reverse split często jest sygnałem problemów finansowych (unikanie delistingu) — szczególnie istotne dla groszówek.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie krytyczne dla groszówek (reverse split = sygnał ostrzegawczy)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 16. EMISJE AKCJI

### 16.1 Ogłoszenie nowej emisji (Share Issuance Announcement)
- **Opis**: Spółka ogłosiła emisję nowych akcji.
- **Dlaczego ważne**: Emisja rozwadnia istniejących akcjonariuszy, ale może też finansować rozwój.
- **Potrzebne dane**: Komunikat spółki (liczba akcji, cena emisyjna, cel).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, EBI, komunikaty prasowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (emisje = rozwodnienie = spadek ceny)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 16.2 Emisja z prawem poboru (Rights Offering)
- **Opis**: Spółka ogłosiła emisję z prawem poboru dla istniejących akcjonariuszy.
- **Dlaczego ważne**: Akcjonariusze muszą podjąć decyzję o uczestnictwie; wpływa na wycenę.
- **Potrzebne dane**: Szczegóły emisji.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty spółek.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 16.3 Emisja bez prawa poboru (Private Placement)
- **Opis**: Spółka wyemitowała akcje w ramach subskrypcji prywatnej.
- **Dlaczego ważne**: Rozwadnia akcjonariat, ale może wprowadzać strategicznego inwestora.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, EBI.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 17. SKUP AKCJI WŁASNYCH

### 17.1 Ogłoszenie skupu akcji własnych (Buyback Announcement)
- **Opis**: Spółka ogłosiła program skupu akcji własnych.
- **Dlaczego ważne**: Skup akcji zmniejsza liczbę akcji w obrocie, zwiększa EPS i sygnalizuje, że zarząd uważa akcje za niedowartościowane.
- **Potrzebne dane**: Komunikat spółki (liczba akcji, budżet, okres).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (skup = silny sygnał byczy)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 17.2 Realizacja skupu (Buyback Execution)
- **Opis**: Spółka poinformowała o postępie lub zakończeniu programu skupu.
- **Dlaczego ważne**: Rzeczywisty skup potwierdza intencje zarządu.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 18. INSIDER TRADING

### 18.1 Transakcja insidera (Insider Transaction)
- **Opis**: Osoba z wewnątrz spółki (zarząd, rada nadzorcza) kupiła lub sprzedała akcje spółki.
- **Dlaczego ważne**: Insiderzy mają najlepszą wiedzę o spółce; ich transakcje są silnym sygnałem.
- **Potrzebne dane**: Dane o transakcji (osoba, liczba akcji, cena, data).
- **yfinance**: Częściowo (`ticker.insider_transactions` — dane dla USA).
- **Dodatkowe źródła**: ESPI (GPW — obowiązek raportowania), SEC EDGAR (USA).
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (insiderzy w małych spółkach mają największą przewagę informacyjną)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 18.2 Skup akcji przez insiderów (Insider Buying Cluster)
- **Opis**: Kilku insiderów kupiło akcje w krótkim okresie czasu.
- **Dlaczego ważne**: Skoncentrowane zakupy insiderów są silnym sygnałem byczym.
- **Potrzebne dane**: Wiele transakcji insiderów.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: ESPI, SEC.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 18.3 Sprzedaż akcji przez insiderów (Insider Selling Cluster)
- **Opis**: Kilku insiderów sprzedało akcje w krótkim okresie.
- **Dlaczego ważne**: Skoordynowana sprzedaż może sygnalizować problemy.
- **Potrzebne dane**: Wiele transakcji insiderów.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: ESPI, SEC.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 19. ZMIANY AKCJONARIATU

### 19.1 Przekroczenie progu (Threshold Crossing)
- **Opis**: Akcjonariusz przekroczył próg 5%, 10%, 15%, 20%, 25%, 33%, 50%, 66%, 75% głosów.
- **Dlaczego ważne**: Obowiązek raportowania na GPW; zmiana układu sił w akcjonariacie.
- **Potrzebne dane**: Komunikat ESPI.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` — specyficzne dla GPW (progi wynikające z ustawy o ofercie publicznej)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 19.2 Wezwanie do sprzedaży akcji (Tender Offer)
- **Opis**: Podmiot ogłosił wezwanie do sprzedaży akcji spółki.
- **Dlaczego ważne**: Wezwanie często wiąże się z premią wobec ceny rynkowej.
- **Potrzebne dane**: Komunikat ESPI (cena, liczba akcji, warunki).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` — specyficzne dla GPW
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 19.3 Zmiana znaczącego akcjonariusza (Major Shareholder Change)
- **Opis**: Znaczący akcjonariusz (np. fundusz emerytalny, TFI) zwiększył lub zmniejszył zaangażowanie.
- **Dlaczego ważne**: Ruchy dużych inwestorów instytucjonalnych są śledzone przez rynek.
- **Potrzebne dane**: Zgłoszenia do KNF, ESPI.
- **yfinance**: Częściowo (`ticker.major_holders` — USA).
- **Dodatkowe źródła**: ESPI, rejestry KNF.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 20. REKOMENDACJE ANALITYKÓW

### 20.1 Nowa rekomendacja (New Analyst Rating)
- **Opis**: Analityk wydał nową rekomendację dla spółki (Kupuj, Trzymaj, Sprzedaj).
- **Dlaczego ważne**: Rekomendacje wpływają na decyzje inwestorów instytucjonalnych i detalicznych.
- **Potrzebne dane**: Rekomendacja, cena docelowa, autor, data.
- **yfinance**: Częściowo (`ticker.recommendations` — dane historyczne).
- **Dodatkowe źródła**: Serwisy finansowe (Bloomberg, Reuters, Bankier.pl).
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (rzadko pokrywane przez analityków, więc każda rekomendacja jest istotna)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 20.2 Zmiana ceny docelowej (Price Target Change)
- **Opis**: Analityk zmienił cenę docelową dla spółki.
- **Dlaczego ważne**: Zmiana ceny docelowej odzwierciedla zmienione oczekiwania co do przyszłości spółki.
- **Potrzebne dane**: Stara i nowa cena docelowa.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 20.3 Podniesienie/obniżenie rekomendacji (Upgrade/Downgrade)
- **Opis**: Analityk podniósł (np. z Trzymaj do Kupuj) lub obniżył rekomendację.
- **Dlaczego ważne**: Zmiana rekomendacji ma silniejszy wpływ niż sama rekomendacja.
- **Potrzebne dane**: Stara i nowa rekomendacja.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 21. RATINGI

### 21.1 Zmiana ratingu kredytowego (Credit Rating Change)
- **Opis**: Agencja ratingowa (S&P, Moody's, Fitch) zmieniła rating kredytowy spółki.
- **Dlaczego ważne**: Rating wpływa na koszt finansowania i zaufanie kontrahentów.
- **Potrzebne dane**: Komunikat agencji ratingowej.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Komunikaty agencji ratingowych, serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 21.2 Zmiana perspektywy ratingu (Rating Outlook Change)
- **Opis**: Agencja zmieniła perspektywę ratingu (stabilna → negatywna lub pozytywna).
- **Dlaczego ważne**: Perspektywa zapowiada przyszłą zmianę ratingu.
- **Potrzebne dane**: Komunikat agencji.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Agencje ratingowe, serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 22. FUZJE I PRZEJĘCIA

### 22.1 Ogłoszenie fuzji/przejęcia (M&A Announcement)
- **Opis**: Spółka ogłosiła zamiar połączenia z inną spółką lub przejęcia innej spółki.
- **Dlaczego ważne**: Fuzje i przejęcia fundamentalnie zmieniają wartość i profil spółki.
- **Potrzebne dane**: Komunikat spółki (warunki, cena, synergia).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe, serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (M&A = największy potencjalny catalyst)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 22.2 Plotki o fuzji/przejęciu (M&A Rumors)
- **Opis**: W mediach pojawiły się spekulacje o potencjalnej fuzji lub przejęciu.
- **Dlaczego ważne**: Plotki często powodują ruchy cenowe przed oficjalnym ogłoszeniem.
- **Potrzebne dane**: Artykuły prasowe, newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Tavily, serwisy finansowe.
- **Silnik**: NewsEngine + Tavily.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 22.3 Zakończenie fuzji/przejęcia (M&A Completion/Failure)
- **Opis**: Fuzja lub przejęcie zostało sfinalizowane lub odwołane.
- **Dlaczego ważne**: Finalizacja zmienia strukturę spółki; odwołanie może powodzić gwałtowne ruchy.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

---

## 23. NOWE KONTRAKTY

### 23.1 Podpisanie znaczącego kontraktu (Major Contract Signed)
- **Opis**: Spółka podpisała kontrakt o znaczącej wartości (np. >10% przychodów rocznych).
- **Dlaczego ważne**: Duże kontrakty bezpośrednio przekładają się na przyszłe przychody.
- **Potrzebne dane**: Komunikat spółki (wartość, kontrahent, okres).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, EBI, komunikaty prasowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (jeden duży kontrakt może transformować małą spółkę)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 23.2 Zerwanie kontraktu (Contract Termination)
- **Opis**: Istotny kontrakt został zerwany lub nie został przedłużony.
- **Dlaczego ważne**: Utrata dużego klienta może znacząco wpłynąć na wyniki.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, EBI.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (utrata jedynego dużego klienta = zagrożenie)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

---

## 24. POZWY

### 24.1 Pozew przeciwko spółce (Lawsuit Against Company)
- **Opis**: Złożono pozew przeciwko spółce (zbiorowy, odszkodowawczy, regulacyjny).
- **Dlaczego ważne**: Pozwy mogą prowadzić do znaczących kosztów i utraty reputacji.
- **Potrzebne dane**: Informacje o pozwie (strony, kwota, przedmiot).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (pozew może zniszczyć małą spółkę)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 24.2 Pozew złożony przez spółkę (Lawsuit Filed by Company)
- **Opis**: Spółka złożyła pozew przeciwko innemu podmiotowi (np. o ochronę patentów).
- **Dlaczego ważne**: Może chronić przewagi konkurencyjne lub generować przychody z odszkodowań.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, media.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 25. PROBLEMY PRAWNE

### 25.1 Postępowanie regulacyjne (Regulatory Investigation)
- **Opis**: Organ regulacyjny (KNF, SEC, UOKiK) wszczął postępowanie wobec spółki.
- **Dlaczego ważne**: Może prowadzić do kar finansowych, ograniczeń działalności lub utraty licencji.
- **Potrzebne dane**: Komunikat organu lub spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty regulatorów, media.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (KNF/SEC może zawiesić notowania)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 25.2 Kara finansowa (Financial Penalty)
- **Opis**: Na spółkę nałożono karę finansową przez organ regulacyjny.
- **Dlaczego ważne**: Bezpośredni wpływ na wyniki finansowe i reputację.
- **Potrzebne dane**: Komunikat o karze (kwota, powód).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, media.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 25.3 Zawieszenie notowań (Trading Suspension)
- **Opis**: Notowania spółki zostały zawieszone przez giełdę lub regulatora.
- **Dlaczego ważne**: Uniemożliwia handel, często poprzedza poważne problemy.
- **Potrzebne dane**: Komunikat giełdy/regulatora.
- **yfinance**: NIE.
- **Dodatkowe źródła**: GPW, ESPI, media.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie krytyczne dla groszówek (zawieszenie = brak możliwości wyjścia z pozycji)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

---

## 26. UPADŁOŚCI I RESTRUKTURYZACJE

### 26.1 Wniosek o upadłość (Bankruptcy Filing)
- **Opis**: Spółka złożyła wniosek o upadłość.
- **Dlaczego ważne**: Skrajnie negatywny sygnał — akcje mogą stracić prawie całą wartość.
- **Potrzebne dane**: Komunikat spółki lub sądu.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, media, Monitor Sądowy.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie krytyczne dla groszówek (największe ryzyko)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 26.2 Restrukturyzacja (Restructuring Announcement)
- **Opis**: Spółka ogłosiła plan restrukturyzacji (zwolnienia grupowe, sprzedaż aktywów, zmiana profilu).
- **Dlaczego ważne**: Restrukturyzacja może oznaczać zarówno problemy (zwolnienia), jak i szansę na poprawę efektywności.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, media.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 26.3 Upadłość kontrahenta (Counterparty Bankruptcy)
- **Opis**: Istotny kontrahent lub partner biznesowy spółki ogłosił upadłość.
- **Dlaczego ważne**: Może wpłynąć na łańcuch dostaw, należności i przyszłe przychody.
- **Potrzebne dane**: Informacje rynkowe.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 27. ZMIANY ZARZĄDU

### 27.1 Zmiana prezesa/CEO (CEO Change)
- **Opis**: Spółka ogłosiła zmianę na stanowisku prezesa zarządu lub CEO.
- **Dlaczego ważne**: Zmiana CEO często oznacza zmianę strategii i może znacząco wpłynąć na kurs.
- **Potrzebne dane**: Komunikat spółki (kto odchodzi, kto przychodzi, powód).
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI, komunikaty prasowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (CEO ma kluczowe znaczenie w małych spółkach)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 27.2 Zmiana w zarządzie (Management Board Change)
- **Opis**: Zmiana w składzie zarządu (inna niż CEO).
- **Dlaczego ważne**: Może sygnalizować zmiany w obszarach funkcjonalnych (finanse, operacje, sprzedaż).
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 27.3 Zmiana w radzie nadzorczej (Supervisory Board Change)
- **Opis**: Zmiana w składzie rady nadzorczej.
- **Dlaczego ważne**: Rada nadzorcza kontroluje zarząd; zmiany mogą wpływać na ład korporacyjny.
- **Potrzebne dane**: Komunikat spółki.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ESPI.
- **Silnik**: NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 27.4 Odejście kluczowego pracownika (Key Employee Departure)
- **Opis**: Kluczowy pracownik (np. dyrektor techniczny, szef sprzedaży) odszedł ze spółki.
- **Dlaczego ważne**: W małych spółkach technologicznych utrata kluczowych osób może być krytyczna.
- **Potrzebne dane**: Informacje medialne, LinkedIn.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily, social media.
- **Silnik**: NewsEngine + Tavily.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (małe zespoły = każda osoba kluczowa)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 28. MAKROEKONOMIA

### 28.1 Publikacja danych makro (Macro Data Release)
- **Opis**: Opublikowano istotne dane makroekonomiczne (PKB, PMI, produkcja przemysłowa, sprzedaż detaliczna).
- **Dlaczego ważne**: Dane makro wpływają na cały rynek i sentyment inwestorów.
- **Potrzebne dane**: Kalendarz makro + wartości.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Kalendarze ekonomiczne (Investing.com, ForexFactory), serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (ETF sektorowe reagują na dane makro)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 28.2 Zmiana PKB (GDP Change)
- **Opis**: PKB kraju/regionu znacząco odbiega od prognoz.
- **Dlaczego ważne**: PKB jest najszerszym wskaźnikiem kondycji gospodarki.
- **Potrzebne dane**: Dane GUS, Eurostat, BEA.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Serwisy ekonomiczne.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 28.3 Zmiana bezrobocia (Unemployment Change)
- **Opis**: Stopa bezrobocia znacząco wzrosła lub spadła.
- **Dlaczego ważne**: Wpływa na konsumpcję, politykę fiskalną i nastroje społeczne.
- **Potrzebne dane**: Dane GUS, BLS.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Serwisy ekonomiczne.
- **Silnik**: NewsEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 29. STOPY PROCENTOWE

### 29.1 Decyzja o stopach procentowych (Interest Rate Decision)
- **Opis**: Bank centralny (NBP, Fed, EBC) ogłosił decyzję o stopach procentowych.
- **Dlaczego ważne**: Stopy procentowe wpływają na koszt kapitału, wyceny akcji i przepływy kapitałowe.
- **Potrzebne dane**: Komunikat banku centralnego.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Strony banków centralnych, serwisy finansowe.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (ETF obligacji, ETF sektorowe wrażliwe na stopy)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 29.2 Zmiana stóp poza posiedzeniem (Emergency Rate Change)
- **Opis**: Bank centralny zmienił stopy procentowe poza standardowym harmonogramem posiedzeń.
- **Dlaczego ważne**: Nadzwyczajna zmiana sygnalizuje kryzys lub wyjątkowe okoliczności.
- **Potrzebne dane**: Komunikat banku centralnego.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Strony banków centralnych, media.
- **Silnik**: NewsEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 29.3 Zmiana forward guidance (Forward Guidance Change)
- **Opis**: Bank centralny zmienił język komunikatu (jastrzębi/gołębi zwrot).
- **Dlaczego ważne**: Rynek reaguje na oczekiwania co do przyszłych stóp, nie tylko na bieżące decyzje.
- **Potrzebne dane**: Komunikat + analiza językowa.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Banki centralne, AI (analiza sentymentu).
- **Silnik**: AIEngine + NewsEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 30. INFLACJA

### 30.1 Publikacja danych o inflacji (CPI/PPI Release)
- **Opis**: Opublikowano dane o inflacji konsumenckiej (CPI) lub producenckiej (PPI).
- **Dlaczego ważne**: Inflacja wpływa na decyzje banków centralnych i realną wartość aktywów.
- **Potrzebne dane**: Dane GUS, BLS, Eurostat.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Serwisy ekonomiczne.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 30.2 Inflacja powyżej/poniżej oczekiwań (Inflation Surprise)
- **Opis**: Inflacja znacząco odbiega od konsensusu rynkowego.
- **Dlaczego ważne**: Zaskoczenie inflacyjne powoduje gwałtowne ruchy na rynkach.
- **Potrzebne dane**: Dane rzeczywiste + konsensus.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Serwisy ekonomiczne.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

---

## 31. WALUTY

### 31.1 Silny ruch walutowy (Major FX Move)
- **Opis**: Kurs istotnej pary walutowej (np. EUR/USD, USD/PLN) zmienił się o >X% w krótkim czasie.
- **Dlaczego ważne**: Kursy walut wpływają na eksporterów, importerów i spółki z długiem walutowym.
- **Potrzebne dane**: Kursy walut (OHLCV).
- **yfinance**: TAK (pary walutowe dostępne w yfinance, np. EURPLN=X).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[GPW]` (USD/PLN kluczowy dla polskich eksporterów/importerów) i `[ETF]` (ETF walutowe)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 31.2 Interwencja walutowa (FX Intervention)
- **Opis**: Bank centralny przeprowadził interwencję na rynku walutowym.
- **Dlaczego ważne**: Interwencje powodują gwałtowne i często nieprzewidywalne ruchy.
- **Potrzebne dane**: Komunikat banku centralnego lub obserwacja rynku.
- **yfinance**: Częściowo (dane cenowe).
- **Dodatkowe źródła**: Komunikaty banków centralnych, media.
- **Silnik**: NewsEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 32. SUROWCE

### 32.1 Silny ruch cen surowca (Commodity Price Shock)
- **Opis**: Cena kluczowego surowca (ropa, miedź, złoto, gaz) zmieniła się o >X%.
- **Dlaczego ważne**: Wpływa na spółki wydobywcze, transportowe, produkcyjne.
- **Potrzebne dane**: Ceny surowców (OHLCV).
- **yfinance**: TAK (kontrakty futures na surowce, np. CL=F, GC=F).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (ETF surowcowe) i `[GPW]` (spółki wydobywcze na GPW)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 32.2 Szok podażowy (Supply Shock)
- **Opis**: Ograniczenie podaży kluczowego surowca (np. decyzja OPEC, katastrofa naturalna).
- **Dlaczego ważne**: Wpływa na całe sektory gospodarki.
- **Potrzebne dane**: Newsy, komunikaty.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 33. GEOPOLITYKA

### 33.1 Konflikt zbrojny / eskalacja (Armed Conflict / Escalation)
- **Opis**: Wybuch lub eskalacja konfliktu zbrojnego mającego wpływ na rynki.
- **Dlaczego ważne**: Wojny i konflikty powodują ucieczkę od ryzyka, sankcje, przerwanie łańcuchów dostaw.
- **Potrzebne dane**: Newsy, komunikaty rządowe.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media międzynarodowe, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[GPW]` (Polska przy granicy z Ukrainą)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 33.2 Sankcje (Sanctions Announcement)
- **Opis**: Ogłoszono nowe sankcje gospodarcze wobec kraju lub podmiotu.
- **Dlaczego ważne**: Sankcje wpływają na spółki prowadzące działalność w objętych nimi krajach.
- **Potrzebne dane**: Komunikaty rządowe, newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 33.3 Wybory / zmiana władzy (Elections / Regime Change)
- **Opis**: Wyniki wyborów lub zmiana rządu w istotnym gospodarczo kraju.
- **Dlaczego ważne**: Zmiana władzy może oznaczać zmianę polityki gospodarczej, podatkowej, regulacyjnej.
- **Potrzebne dane**: Wyniki wyborów, newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 33.4 Umowa handlowa (Trade Agreement/Dispute)
- **Opis**: Podpisanie lub zerwanie istotnej umowy handlowej między krajami.
- **Dlaczego ważne**: Wpływa na cła, dostęp do rynków, łańcuchy dostaw.
- **Potrzebne dane**: Newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 34. SEKTOR

### 34.1 Rotacja sektorowa (Sector Rotation)
- **Opis**: Kapitał przepływa z jednego sektora do drugiego (np. z technologii do value).
- **Dlaczego ważne**: Rotacja sektorowa może powodować spadki w jednych sektorach i wzrosty w innych.
- **Potrzebne dane**: Dane sektorowe, ETF sektorowe.
- **yfinance**: TAK (ETF sektorowe).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[ETF]` — szczególnie istotne dla ETF (rotacja sektorowa = przepływy między ETF-ami)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 34.2 Zmiana regulacji sektorowych (Sector Regulation Change)
- **Opis**: Wprowadzono nowe regulacje dotyczące całego sektora (np. energetyka, banki, technologie).
- **Dlaczego ważne**: Regulacje mogą fundamentalnie zmienić rentowność sektora.
- **Potrzebne dane**: Akty prawne, newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Dzienniki ustaw, media branżowe, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (regulacje sektorowe = wpływ na ETF sektorowe)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 34.3 Bankructwo lidera sektorowego (Sector Leader Bankruptcy)
- **Opis**: Lider sektora ogłosił upadłość lub poważne problemy finansowe.
- **Dlaczego ważne**: Może oznaczać szansę dla konkurentów lub problemy systemowe w sektorze.
- **Potrzebne dane**: Newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 35. KORELACJE

### 35.1 Rozpad korelacji (Correlation Breakdown)
- **Opis**: Dwa instrumenty, które historycznie były skorelowane, nagle przestały się poruszać razem.
- **Dlaczego ważne**: Rozpad korelacji może sygnalizować zmianę fundamentalną w jednym z instrumentów.
- **Potrzebne dane**: OHLCV dla obu instrumentów.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[ETF]` — szczególnie istotne dla ETF (korelacja ETF vs indeks bazowy)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 35.2 Wzmocnienie korelacji (Correlation Strengthening)
- **Opis**: Korelacja między instrumentami znacząco wzrosła.
- **Dlaczego ważne**: Może sygnalizować wspólny czynnik ryzyka (np. sektorowy, makro).
- **Potrzebne dane**: OHLCV dla obu instrumentów.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[ETF]` — szczególnie istotne dla ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Niski**

---

## 36. ETF

### 36.1 Zmiana składu ETF (ETF Rebalancing)
- **Opis**: ETF dokonał zmiany składu (rebalancing), co wpływa na popyt/podaż instrumentów.
- **Dlaczego ważne**: Duże ETF-y mogą powodować znaczące przepływy przy rebalancingu.
- **Potrzebne dane**: Informacje o ETF, daty rebalancingu.
- **yfinance**: Częściowo (dane o ETF).
- **Dodatkowe źródła**: Strony dostawców ETF, serwisy finansowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[ETF]` — wyłącznie dla ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 36.2 Napływy/odpływy z ETF (ETF Flows)
- **Opis**: Znaczące napływy lub odpływy kapitału z ETF-ów sektorowych lub tematycznych.
- **Dlaczego ważne**: Wskazuje na sentyment inwestorów instytucjonalnych.
- **Potrzebne dane**: Dane o przepływach ETF.
- **yfinance**: NIE.
- **Dodatkowe źródła**: ETF.com, Bloomberg, serwisy finansowe.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[ETF]` — wyłącznie dla ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 36.3 Premia/dyskonto ETF (ETF Premium/Discount)
- **Opis**: Cena ETF znacząco odbiega od NAV (Net Asset Value).
- **Dlaczego ważne**: Duże dyskonto może być okazją, duża premia sygnalizuje przegrzanie.
- **Potrzebne dane**: Cena rynkowa ETF + NAV.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Strony dostawców ETF.
- **Silnik**: AnalystEngine.
- **Grupa**: `[ETF]` — wyłącznie dla ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 36.4 Likwidacja ETF (ETF Closure/Liquidation)
- **Opis**: Dostawca ETF ogłosił zamknięcie i likwidację funduszu.
- **Dlaczego ważne**: Wymusza sprzedaż pozycji przez inwestorów, wpływa na instrumenty bazowe.
- **Potrzebne dane**: Komunikat dostawcy ETF.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Strony dostawców ETF, media.
- **Silnik**: NewsEngine.
- **Grupa**: `[ETF]` — wyłącznie dla ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 37. OPCJE

### 37.1 Nietypowa aktywność na opcjach (Unusual Options Activity)
- **Opis**: Znaczący wzrost wolumenu lub open interest na opcjach (szczególnie out-of-the-money).
- **Dlaczego ważne**: Duże pozycje na opcjach mogą wskazywać na oczekiwania dużych graczy co do przyszłych ruchów.
- **Potrzebne dane**: Dane o opcjach (wolumen, open interest, implied volatility).
- **yfinance**: Częściowo (`ticker.options` — łańcuch opcji).
- **Dodatkowe źródła**: Serwisy opcyjne (CBOE, MarketChameleon).
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[USA]` — głównie dla rynku USA (opcje na groszówki USA są dostępne)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 37.2 Zmiana implied volatility (IV Change)
- **Opis**: Implied volatility na opcjach znacząco wzrosła lub spadła.
- **Dlaczego ważne**: IV odzwierciedla oczekiwania rynku co do przyszłej zmienności.
- **Potrzebne dane**: Dane o opcjach.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Serwisy opcyjne.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[USA]` `[ETF]` — ETF mają płynne łańcuchy opcji
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 37.3 Max Pain (Max Pain Level)
- **Opis**: Cena instrumentu zbliża się do poziomu max pain (cena, przy której najwięcej opcji wygasa bez wartości).
- **Dlaczego ważne**: Teoria max pain sugeruje, że cena grawituje do tego poziomu przy wygasaniu opcji.
- **Potrzebne dane**: Open interest dla wszystkich strike'ów.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Serwisy opcyjne.
- **Silnik**: TechnicalEngine.
- **Grupa**: `[USA]` `[ETF]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Niski**

---

## 38. SHORT INTEREST

### 38.1 Wzrost short interest (Short Interest Increase)
- **Opis**: Short interest (liczba akcji sprzedanych krótko) znacząco wzrósł.
- **Dlaczego ważne**: Wysoki short interest może prowadzić do short squeeze lub sygnalizować negatywne oczekiwania.
- **Potrzebne dane**: Dane o short interest.
- **yfinance**: Częściowo (`ticker.info` zawiera shortRatio, shortPercentOfFloat — dane dla USA).
- **Dodatkowe źródła**: Serwisy finansowe, raporty giełdowe.
- **Silnik**: AnalystEngine.
- **Grupa**: `[USA]` — głównie dla rynku USA (dane o short interest są publicznie dostępne)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 38.2 Short squeeze (Short Squeeze)
- **Opis**: Gwałtowny wzrost ceny przy wysokim short interest — krótcy sprzedający są zmuszeni odkupować akcje.
- **Dlaczego ważne**: Short squeeze może powodować ekstremalne wzrosty cen — szczególnie istotne dla groszówek.
- **Potrzebne dane**: Cena + short interest + wolumen.
- **yfinance**: TAK (cena i wolumen) + częściowo (short interest).
- **Dodatkowe źródła**: Dane o short interest.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[USA]` — szczególnie istotne dla groszówek USA (największy potencjał short squeeze)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 38.3 Days to Cover
- **Opis**: Wskaźnik "days to cover" (short interest / średni dzienny wolumen) przekroczył krytyczny poziom.
- **Dlaczego ważne**: Wysoki days-to-cover zwiększa ryzyko short squeeze.
- **Potrzebne dane**: Short interest + średni wolumen.
- **yfinance**: Częściowo.
- **Dodatkowe źródła**: Serwisy finansowe.
- **Silnik**: AnalystEngine.
- **Grupa**: `[USA]` — głównie dla rynku USA
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 39. DARK POOL

### 39.1 Nietypowa aktywność w Dark Pool (Dark Pool Activity)
- **Opis**: Znaczący wzrost wolumenu transakcji w dark poolach dla danego instrumentu.
- **Dlaczego ważne**: Dark poole są używane przez duże instytucje do ukrywania dużych zleceń; wzrost aktywności może sygnalizować akumulację/dystrybucję.
- **Potrzebne dane**: Dane o dark pool (wolumen, cena).
- **yfinance**: NIE.
- **Dodatkowe źródła**: Serwisy śledzące dark pool (np. DarkPool Prints, FlowAlgo).
- **Silnik**: AnalystEngine.
- **Grupa**: `[USA]` — głównie dla rynku USA
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 40. NIETYPOWE TRANSAKCJE

### 40.1 Duży blokowy trade (Block Trade)
- **Opis**: Zarejestrowano transakcję o nietypowo dużym wolumenie (block trade) poza standardowym obrotem.
- **Dlaczego ważne**: Block trade'y są realizowane przez instytucje i mogą sygnalizować zmianę pozycji.
- **Potrzebne dane**: Dane o transakcjach blokowych.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Serwisy giełdowe, Bloomberg Terminal.
- **Silnik**: AnalystEngine.
- **Grupa**: `[USA]` — głównie dla rynku USA
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 40.2 Transakcja pakietowa (Package Trade)
- **Opis**: Zarejestrowano transakcję pakietową na GPW (transakcja poza sesją, duży pakiet akcji).
- **Dlaczego ważne**: Transakcje pakietowe często oznaczają zmianę w akcjonariacie.
- **Potrzebne dane**: Dane GPW o transakcjach pakietowych.
- **yfinance**: NIE.
- **Dodatkowe źródła**: GPW, ESPI.
- **Silnik**: NewsEngine + AnalystEngine.
- **Grupa**: `[GPW]` — specyficzne dla GPW
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 41. MEDIA SPOŁECZNOŚCIOWE

### 41.1 Wzmianki w social media (Social Media Mentions Spike)
- **Opis**: Liczba wzmianek o spółce w mediach społecznościowych (Twitter/X, Reddit, StockTwits) gwałtownie wzrosła.
- **Dlaczego ważne**: Social media coraz częściej napędzają ruchy cenowe (meme stocks, WSB).
- **Potrzebne dane**: Dane o wzmiankach (liczba, sentyment).
- **yfinance**: NIE.
- **Dodatkowe źródła**: API social media (Twitter/X API, Reddit API), serwisy analityczne.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[USA]` — szczególnie istotne dla groszówek USA (meme stock phenomenon)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 41.2 Trend na Reddit (Reddit Trend)
- **Opis**: Spółka stała się popularnym tematem na Reddit (szczególnie r/WallStreetBets, r/pennystocks).
- **Dlaczego ważne**: Społeczność Reddit wielokrotnie powodowała masowe ruchy cenowe na groszówkach.
- **Potrzebne dane**: Dane z Reddit API.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Reddit API, serwisy śledzące (SwaggyStocks, ApeWisdom).
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[USA]` — szczególnie istotne dla groszówek USA
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 41.3 Wzmianka przez influencera (Influencer Mention)
- **Opis**: Znany influencer finansowy wspomniał o spółce w mediach społecznościowych.
- **Dlaczego ważne**: Pojedynczy tweet lub post może wywołać gwałtowny ruch cenowy.
- **Potrzebne dane**: Monitoring social media.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Twitter/X API, monitoring mediów.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[USA]` — szczególnie istotne dla groszówek USA
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 42. SENTYMENT RYNKU

### 42.1 Zmiana sentymentu (Sentiment Shift)
- **Opis**: Zagregowany sentyment rynkowy (np. Fear & Greed Index) zmienił się o >X punktów.
- **Dlaczego ważne**: Ekstremalny sentyment często sygnalizuje punkty zwrotne rynku.
- **Potrzebne dane**: Indeksy sentymentu.
- **yfinance**: NIE.
- **Dodatkowe źródła**: CNN Fear & Greed Index, VIX, AAII Sentiment Survey.
- **Silnik**: AnalystEngine + AIEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (sentyment napędza przepływy ETF)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 42.2 VIX — wzrost (VIX Spike)
- **Opis**: Indeks zmienności VIX (lub odpowiednik lokalny) wzrósł powyżej krytycznego poziomu.
- **Dlaczego ważne**: VIX jest nazywany "indeksem strachu"; jego wzrost sygnalizuje panikę na rynku.
- **Potrzebne dane**: VIX lub podobny indeks.
- **yfinance**: TAK (^VIX, ^VXN).
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[Universal]` — szczególnie istotne dla `[ETF]` (VIX = kluczowy wskaźnik dla ETF)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 42.3 Put/Call Ratio
- **Opis**: Stosunek wolumenu opcji put do call osiągnął ekstremalny poziom.
- **Dlaczego ważne**: Ekstremalny put/call ratio sygnalizuje skrajny pesymizm (kontrariański sygnał kupna) lub optymizm.
- **Potrzebne dane**: Dane o opcjach.
- **yfinance**: NIE.
- **Dodatkowe źródła**: CBOE, serwisy opcyjne.
- **Silnik**: AnalystEngine.
- **Grupa**: `[USA]` `[ETF]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 43. NEWS

### 43.1 Breaking news (Breaking News)
- **Opis**: Pojawił się nagły news związany ze spółką (np. wypadek, katastrofa, przełomowe odkrycie).
- **Dlaczego ważne**: Breaking news powodują natychmiastowe i gwałtowne ruchy cen.
- **Potrzebne dane**: Newsy z agencji prasowych.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Agencje prasowe (Reuters, Bloomberg, PAP), Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 43.2 Artykuł analityczny (Analyst Article)
- **Opis**: Opublikowano istotny artykuł analityczny o spółce (np. śledztwo dziennikarskie, analiza short-sellera).
- **Dlaczego ważne**: Artykuły śledcze mogą ujawnić nieprawidłowości i spowodować załamanie kursu.
- **Potrzebne dane**: Artykuły, newsy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Tavily, media.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (krótkie raporty short-sellerów)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 43.3 Wywiad z zarządem (Management Interview)
- **Opis**: Członek zarządu udzielił wywiadu, w którym padły istotne deklaracje.
- **Dlaczego ważne**: Wypowiedzi zarządu mogą sygnalizować przyszłe decyzje strategiczne.
- **Potrzebne dane**: Transkrypcja lub artykuł.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Media, Tavily.
- **Silnik**: NewsEngine + AIEngine.
- **Grupa**: `[GPW]` `[USA]` — nie dotyczy ETF
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 44. TAVILY

### 44.1 Wynik wyszukiwania Tavily (Tavily Search Result)
- **Opis**: Tavily zwrócił nowe, istotne informacje o spółce, których nie ma w standardowych źródłach.
- **Dlaczego ważne**: Tavily przeszukuje internet w czasie rzeczywistym, znajdując informacje spoza standardowych kanałów.
- **Potrzebne dane**: Zapytanie do Tavily API.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Tavily API.
- **Silnik**: Tavily (integracja przez NewsEngine).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

### 44.2 Zmiana sentymentu w wynikach Tavily (Tavily Sentiment Change)
- **Opis**: Sentyment artykułów zwracanych przez Tavily dla danej spółki zmienił się znacząco.
- **Dlaczego ważne**: Zmiana sentymentu w mediach często poprzedza ruchy cenowe.
- **Potrzebne dane**: Wyniki Tavily + analiza sentymentu.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Tavily API + AI (analiza sentymentu).
- **Silnik**: AIEngine + Tavily.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 45. ALERTY WŁASNE ALCHEMIKA

### 45.1 Wykrycie zdarzenia złożonego (Composite Event Detected)
- **Opis**: ALCHEMIK wykrył kombinację kilku zdarzeń jednocześnie (np. skok wolumenu + wybicie + pozytywny news).
- **Dlaczego ważne**: Zdarzenia złożone mają znacznie wyższą wartość predykcyjną niż pojedyncze sygnały.
- **Potrzebne dane**: Wszystkie źródła danych.
- **yfinance**: TAK (jako jedno ze źródeł).
- **Dodatkowe źródła**: Wszystkie dostępne.
- **Silnik**: Wszystkie silniki + AIEngine (agregacja).
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 45.2 Zmiana stanu instrumentu (Instrument State Change)
- **Opis**: Instrument zmienił stan z "normalny" na "monitorowany" lub "alarmowy" na podstawie skumulowanych sygnałów.
- **Dlaczego ważne**: System sam kategoryzuje instrumenty według poziomu uwagi wymaganej od inwestora.
- **Potrzebne dane**: Wszystkie źródła + historia stanów.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Wszystkie dostępne.
- **Silnik**: Wszystkie silniki + AIEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Krytyczny**

### 45.3 Powtórne wykrycie zdarzenia (Event Recurrence)
- **Opis**: To samo zdarzenie zostało wykryte dla tego samego instrumentu po raz kolejny w krótkim czasie.
- **Dlaczego ważne**: Powtarzalność sygnału zwiększa jego wiarygodność.
- **Potrzebne dane**: Historia zdarzeń.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Wewnętrzna historia ALCHEMIKA.
- **Silnik**: Wszystkie silniki.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## 46. ZDARZENIA MIĘDZYINSTRUMENTOWE

### 46.1 Spread między instrumentami (Instrument Spread Anomaly)
- **Opis**: Spread między dwoma powiązanymi instrumentami (np. akcja vs ETF sektorowy) znacząco odbiega od normy.
- **Dlaczego ważne**: Anomalia spreadu może wskazywać na okazję arbitrażową lub błędną wycenę.
- **Potrzebne dane**: OHLCV dla obu instrumentów.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[ETF]` — szczególnie istotne dla ETF (spread ETF vs NAV, ETF vs indeks)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 46.2 Lider vs followers (Leader-Lag Analysis)
- **Opis**: Lider sektora wykonał ruch, a pozostali jeszcze nie zareagowali.
- **Dlaczego ważne**: Opóźniona reakcja followerów może być okazją inwestycyjną.
- **Potrzebne dane**: OHLCV dla wielu instrumentów z sektora.
- **yfinance**: TAK.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: TechnicalEngine + AnalystEngine.
- **Grupa**: `[Universal]`
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

---

## 47. ZDARZENIA SEZONOWE I KALENDARZOWE

### 47.1 Efekt końca miesiąca/kwartału (Month/Quarter End Effect)
- **Opis**: Zbliża się koniec miesiąca lub kwartału — okres window dressing przez fundusze.
- **Dlaczego ważne**: Fundusze instytucjonalne często dostosowują portfele na koniec okresów.
- **Potrzebne dane**: Kalendarz.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Kalendarz.
- **Silnik**: AnalystEngine.
- **Grupa**: `[ETF]` — szczególnie istotne dla ETF (rebalancing funduszy)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Niski**

### 47.2 Dzień wygasania instrumentów pochodnych (Triple Witching)
- **Opis**: Dzień jednoczesnego wygasania opcji, futures i innych instrumentów pochodnych.
- **Dlaczego ważne**: Zwiększona zmienność i wolumen w tych dniach.
- **Potrzebne dane**: Kalendarz giełdowy.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Kalendarze giełdowe.
- **Silnik**: AnalystEngine.
- **Grupa**: `[USA]` `[ETF]` — głównie rynek USA
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Średni**

### 47.3 Efekt stycznia (January Effect)
- **Opis**: Początek roku kalendarzowego — historycznie okres wzrostów na małych spółkach.
- **Dlaczego ważne**: Sezonowy wzorzec obserwowany na rynkach, szczególnie istotny dla groszówek.
- **Potrzebne dane**: Kalendarz.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Nie wymagane.
- **Silnik**: AnalystEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (small-cap effect)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Niski**

### 47.4 Sezon wyników (Earnings Season)
- **Opis**: Rozpoczął się sezon publikacji wyników kwartalnych.
- **Dlaczego ważne**: Zwiększona zmienność i liczba okazji w sezonie wyników.
- **Potrzebne dane**: Kalendarz.
- **yfinance**: NIE.
- **Dodatkowe źródła**: Kalendarze giełdowe.
- **Silnik**: AnalystEngine + NewsEngine.
- **Grupa**: `[GPW]` `[USA]` — szczególnie istotne dla groszówek (wyniki = największy catalyst)
- **Wdrożenie**: `[Future]`
- **Priorytet**: **Wysoki**

---

## TABELA: ZDARZENIA × ŹRÓDŁA DANYCH

| Zdarzenie | yfinance | News | Tavily | AI | Inny silnik |
|-----------|----------|------|--------|----|-------------|
| **1.1** Nagły wzrost ceny | ✓ | ○ | - | - | TechnicalEngine |
| **1.2** Nagły spadek ceny | ✓ | ○ | - | - | TechnicalEngine |
| **1.3** Luka w górę | ✓ | - | - | - | TechnicalEngine |
| **1.4** Luka w dół | ✓ | - | - | - | TechnicalEngine |
| **1.5** Nowe max 52-tyg | ✓ | - | - | - | TechnicalEngine |
| **1.6** Nowe min 52-tyg | ✓ | - | - | - | TechnicalEngine |
| **1.7** All-Time High | ✓ | - | - | - | TechnicalEngine |
| **1.8** All-Time Low | ✓ | - | - | - | TechnicalEngine |
| **1.9** Odrzucenie poziomu | ✓ | - | - | - | TechnicalEngine |
| **1.10** Poziom psychologiczny | ✓ | - | - | - | TechnicalEngine |
| **2.1** Skok wolumenu | ✓ | - | - | - | TechnicalEngine |
| **2.2** Wolumen bliski zeru | ✓ | - | - | - | TechnicalEngine |
| **2.3** Wolumen kumulacyjny | ✓ | - | - | - | TechnicalEngine |
| **2.4** Wolumen na spadkach | ✓ | - | - | - | TechnicalEngine |
| **2.5** Wolumen na wzrostach | ✓ | - | - | - | TechnicalEngine |
| **3.1** Wzrost zmienności | ✓ | - | - | - | TechnicalEngine |
| **3.2** Spadek zmienności | ✓ | - | - | - | TechnicalEngine |
| **3.3** BB Expansion | ✓ | - | - | - | TechnicalEngine |
| **3.4** BB Squeeze | ✓ | - | - | - | TechnicalEngine |
| **4.1** Wybicie oporu | ✓ | - | - | - | TechnicalEngine |
| **4.2** Wybicie wsparcia | ✓ | - | - | - | TechnicalEngine |
| **4.3** Trójkąt breakout | ✓ | - | - | - | TechnicalEngine |
| **4.4** Kanał breakout | ✓ | - | - | - | TechnicalEngine |
| **4.5** Flaga breakout | ✓ | - | - | - | TechnicalEngine |
| **5.1** Młot/Wisielec | ✓ | - | - | - | TechnicalEngine |
| **5.2** Shooting Star | ✓ | - | - | - | TechnicalEngine |
| **5.3** Bullish Engulfing | ✓ | - | - | - | TechnicalEngine |
| **5.4** Bearish Engulfing | ✓ | - | - | - | TechnicalEngine |
| **5.5** Doji | ✓ | - | - | - | TechnicalEngine |
| **5.6** Morning/Evening Star | ✓ | - | - | - | TechnicalEngine |
| **5.7** Three White Soldiers | ✓ | - | - | - | TechnicalEngine |
| **5.8** Three Black Crows | ✓ | - | - | - | TechnicalEngine |
| **5.9** Marubozu | ✓ | - | - | - | TechnicalEngine |
| **5.10** Harami | ✓ | - | - | - | TechnicalEngine |
| **6.1** MA Crossover | ✓ | - | - | - | TechnicalEngine |
| **6.2** MA Slope Change | ✓ | - | - | - | TechnicalEngine |
| **6.3** Price vs MA | ✓ | - | - | - | TechnicalEngine |
| **6.4** Seria świec | ✓ | - | - | - | TechnicalEngine |
| **6.5** Trend Structure Change | ✓ | - | - | - | TechnicalEngine |
| **7.1** RSI Overbought | ✓ | - | - | - | TechnicalEngine |
| **7.2** RSI Oversold | ✓ | - | - | - | TechnicalEngine |
| **7.3** RSI Divergence | ✓ | - | - | - | TechnicalEngine |
| **7.4** MACD Crossover | ✓ | - | - | - | TechnicalEngine |
| **7.5** MACD Zero Cross | ✓ | - | - | - | TechnicalEngine |
| **7.6** Stochastic | ✓ | - | - | - | TechnicalEngine |
| **8.1** OBV Divergence | ✓ | - | - | - | TechnicalEngine |
| **8.2** VWAP Deviation | ✓ | - | - | - | TechnicalEngine |
| **8.3** ATR Expansion | ✓ | - | - | - | TechnicalEngine |
| **8.4** Fibonacci Hit | ✓ | - | - | - | TechnicalEngine |
| **9.1** P/E Change | ✓ | - | - | - | AnalystEngine |
| **9.2** P/BV Change | ✓ | - | - | - | AnalystEngine |
| **9.3** Market Cap Change | ✓ | - | - | - | AnalystEngine |
| **9.4** Debt Change | ○ | - | - | - | AnalystEngine |
| **9.5** Revenue Change | ○ | - | - | - | AnalystEngine |
| **9.6** Net Income Change | ○ | - | - | - | AnalystEngine |
| **10.1** Earnings Release | ○ | ✓ | ○ | ○ | AnalystEngine |
| **10.2** Earnings Beat | ○ | ✓ | ○ | ✓ | AnalystEngine + AI |
| **10.3** Earnings Miss | ○ | ✓ | ○ | ✓ | AnalystEngine + AI |
| **10.4** Guidance Update | - | ✓ | ○ | ✓ | NewsEngine + AI |
| **11.1** Quarterly Report | - | ✓ | - | - | NewsEngine |
| **11.2** Annual Report | - | ✓ | - | - | NewsEngine |
| **11.3** Accounting Change | - | ✓ | - | ✓ | AnalystEngine + AI |
| **12.1** ESPI Filing | - | ✓ | - | ✓ | NewsEngine + AI |
| **12.2** ESPI Delay | - | ✓ | - | - | NewsEngine |
| **13.1** EBI Filing | - | ✓ | - | ✓ | NewsEngine + AI |
| **14.1** Dividend Announcement | ○ | ✓ | - | - | NewsEngine + Analyst |
| **14.2** Dividend Policy Change | - | ✓ | - | - | NewsEngine + Analyst |
| **14.3** Special Dividend | - | ✓ | - | - | NewsEngine + Analyst |
| **14.4** Ex-Dividend Date | ○ | - | - | - | AnalystEngine |
| **15.1** Split Announcement | ○ | ✓ | - | - | NewsEngine |
| **15.2** Split Execution | ✓ | - | - | - | TechnicalEngine |
| **15.3** Reverse Split | ○ | ✓ | - | - | NewsEngine + Analyst |
| **16.1** Share Issuance | - | ✓ | - | - | NewsEngine + Analyst |
| **16.2** Rights Offering | - | ✓ | - | - | NewsEngine + Analyst |
| **16.3** Private Placement | - | ✓ | - | - | NewsEngine + Analyst |
| **17.1** Buyback Announcement | - | ✓ | - | - | NewsEngine + Analyst |
| **17.2** Buyback Execution | - | ✓ | - | - | NewsEngine |
| **18.1** Insider Transaction | ○ | ✓ | - | - | NewsEngine + Analyst |
| **18.2** Insider Buying Cluster | ○ | ✓ | - | - | AnalystEngine |
| **18.3** Insider Selling Cluster | ○ | ✓ | - | - | AnalystEngine |
| **19.1** Threshold Crossing | - | ✓ | - | - | NewsEngine + Analyst |
| **19.2** Tender Offer | - | ✓ | - | - | NewsEngine + Analyst |
| **19.3** Major Shareholder Change | ○ | ✓ | - | - | NewsEngine + Analyst |
| **20.1** New Analyst Rating | ○ | ✓ | ○ | ✓ | NewsEngine + AI |
| **20.2** Price Target Change | ○ | ✓ | ○ | ✓ | NewsEngine + AI |
| **20.3** Upgrade/Downgrade | ○ | ✓ | ○ | ✓ | NewsEngine + AI |
| **21.1** Credit Rating Change | - | ✓ | ○ | ✓ | NewsEngine + AI |
| **21.2** Rating Outlook Change | - | ✓ | ○ | ✓ | NewsEngine + AI |
| **22.1** M&A Announcement | - | ✓ | - | ✓ | NewsEngine + AI |
| **22.2** M&A Rumors | - | ✓ | ✓ | ✓ | NewsEngine + Tavily |
| **22.3** M&A Completion/Failure | - | ✓ | - | - | NewsEngine |
| **23.1** Major Contract | - | ✓ | - | ✓ | NewsEngine + AI |
| **23.2** Contract Termination | - | ✓ | - | ✓ | NewsEngine + AI |
| **24.1** Lawsuit Against | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **24.2** Lawsuit Filed By | - | ✓ | - | - | NewsEngine |
| **25.1** Regulatory Investigation | - | ✓ | ○ | ✓ | NewsEngine + AI |
| **25.2** Financial Penalty | - | ✓ | - | - | NewsEngine + Analyst |
| **25.3** Trading Suspension | - | ✓ | - | - | NewsEngine |
| **26.1** Bankruptcy Filing | - | ✓ | - | - | NewsEngine |
| **26.2** Restructuring | - | ✓ | - | - | NewsEngine + Analyst |
| **26.3** Counterparty Bankruptcy | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **27.1** CEO Change | - | ✓ | - | ✓ | NewsEngine + AI |
| **27.2** Management Change | - | ✓ | - | - | NewsEngine |
| **27.3** Supervisory Board Change | - | ✓ | - | - | NewsEngine |
| **27.4** Key Employee Departure | - | ✓ | ✓ | - | NewsEngine + Tavily |
| **28.1** Macro Data Release | - | ✓ | - | ✓ | NewsEngine + AI |
| **28.2** GDP Change | - | ✓ | - | ✓ | NewsEngine + AI |
| **28.3** Unemployment Change | - | ✓ | - | - | NewsEngine |
| **29.1** Interest Rate Decision | - | ✓ | - | ✓ | NewsEngine + AI |
| **29.2** Emergency Rate Change | - | ✓ | - | - | NewsEngine |
| **29.3** Forward Guidance Change | - | ✓ | - | ✓ | AIEngine + News |
| **30.1** CPI/PPI Release | - | ✓ | - | ✓ | NewsEngine + AI |
| **30.2** Inflation Surprise | - | ✓ | - | ✓ | NewsEngine + AI |
| **31.1** Major FX Move | ✓ | - | - | - | TechnicalEngine + Analyst |
| **31.2** FX Intervention | ○ | ✓ | - | - | NewsEngine |
| **32.1** Commodity Price Shock | ✓ | - | - | - | TechnicalEngine + Analyst |
| **32.2** Supply Shock | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **33.1** Armed Conflict | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **33.2** Sanctions | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **33.3** Elections | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **33.4** Trade Agreement | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **34.1** Sector Rotation | ✓ | - | - | - | TechnicalEngine + Analyst |
| **34.2** Sector Regulation | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **34.3** Sector Leader Bankruptcy | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **35.1** Correlation Breakdown | ✓ | - | - | - | TechnicalEngine + Analyst |
| **35.2** Correlation Strengthening | ✓ | - | - | - | TechnicalEngine + Analyst |
| **36.1** ETF Rebalancing | ○ | ✓ | - | - | NewsEngine + Analyst |
| **36.2** ETF Flows | - | ✓ | - | - | NewsEngine + Analyst |
| **36.3** ETF Premium/Discount | ○ | - | - | - | AnalystEngine |
| **36.4** ETF Closure | - | ✓ | - | - | NewsEngine |
| **37.1** Unusual Options Activity | ○ | - | - | - | TechnicalEngine + Analyst |
| **37.2** IV Change | ○ | - | - | - | TechnicalEngine |
| **37.3** Max Pain | ○ | - | - | - | TechnicalEngine |
| **38.1** Short Interest Increase | ○ | - | - | - | AnalystEngine |
| **38.2** Short Squeeze | ✓ | - | - | - | TechnicalEngine + Analyst |
| **38.3** Days to Cover | ○ | - | - | - | AnalystEngine |
| **39.1** Dark Pool Activity | - | - | - | - | AnalystEngine (zewn.) |
| **40.1** Block Trade | - | - | - | - | AnalystEngine (zewn.) |
| **40.2** Package Trade | - | ✓ | - | - | NewsEngine + Analyst |
| **41.1** Social Media Mentions | - | - | - | ✓ | NewsEngine + AI (zewn.) |
| **41.2** Reddit Trend | - | - | - | ✓ | NewsEngine + AI (zewn.) |
| **41.3** Influencer Mention | - | - | - | ✓ | NewsEngine + AI (zewn.) |
| **42.1** Sentiment Shift | - | - | - | ✓ | AnalystEngine + AI |
| **42.2** VIX Spike | ✓ | - | - | - | TechnicalEngine + Analyst |
| **42.3** Put/Call Ratio | - | - | - | - | AnalystEngine (zewn.) |
| **43.1** Breaking News | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **43.2** Analyst Article | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **43.3** Management Interview | - | ✓ | ✓ | ✓ | NewsEngine + AI |
| **44.1** Tavily Search Result | - | - | ✓ | ✓ | Tavily + NewsEngine |
| **44.2** Tavily Sentiment Change | - | - | ✓ | ✓ | AIEngine + Tavily |
| **45.1** Composite Event | ✓ | ✓ | ✓ | ✓ | Wszystkie silniki |
| **45.2** Instrument State Change | ✓ | ✓ | ✓ | ✓ | Wszystkie silniki |
| **45.3** Event Recurrence | ✓ | ✓ | ✓ | ✓ | Wszystkie silniki |
| **46.1** Spread Anomaly | ✓ | - | - | - | TechnicalEngine + Analyst |
| **46.2** Leader-Lag | ✓ | - | - | - | TechnicalEngine + Analyst |
| **47.1** Month/Quarter End | - | - | - | - | AnalystEngine |
| **47.2** Triple Witching | - | - | - | - | AnalystEngine |
| **47.3** January Effect | - | - | - | - | AnalystEngine |
| **47.4** Earnings Season | - | ✓ | - | - | AnalystEngine + News |

Legenda:
- **✓** = główne źródło
- **○** = częściowe/pomocnicze źródło
- **-** = nie dotyczy / nie jest źródłem
- **zewn.** = wymaga zewnętrznego źródła danych spoza obecnej architektury

---

## TABELA: KLASYFIKACJA WG GRUP INSTRUMENTÓW

| Zdarzenie | GPW groszówki | USA groszówki | ETF | Universal | v1 / Future |
|-----------|:---:|:---:|:---:|:---:|:-----------:|
| **1.1** Nagły wzrost ceny | ✓ | ✓ | ✓ | ✓ | **v1** |
| **1.2** Nagły spadek ceny | ✓ | ✓ | ✓ | ✓ | **v1** |
| **1.3** Luka w górę | ✓ | ✓ | ✓ | ✓ | **v1** |
| **1.4** Luka w dół | ✓ | ✓ | ✓ | ✓ | **v1** |
| **1.5** Nowe max 52-tyg | ✓ | ★ | ✓ | ✓ | **v1** |
| **1.6** Nowe min 52-tyg | ★ | ✓ | ✓ | ✓ | **v1** |
| **1.7** All-Time High | ✓ | ✓ | ★ | ✓ | **v1** |
| **1.8** All-Time Low | ★ | ★ | - | - | **v1** |
| **1.9** Odrzucenie poziomu | ✓ | ✓ | ✓ | ✓ | Future |
| **1.10** Poziom psychologiczny | ✓ | ★ | ✓ | ✓ | Future |
| **2.1** Skok wolumenu | ★ | ★ | ✓ | ✓ | **v1** |
| **2.2** Wolumen bliski zeru | ★ | ✓ | - | - | Future |
| **2.3** Wolumen kumulacyjny | ✓ | ✓ | ✓ | ✓ | Future |
| **2.4** Wolumen na spadkach | ✓ | ✓ | ★ | ✓ | **v1** |
| **2.5** Wolumen na wzrostach | ✓ | ✓ | ★ | ✓ | **v1** |
| **3.1** Wzrost zmienności | ★ | ★ | ✓ | ✓ | **v1** |
| **3.2** Spadek zmienności | ✓ | ✓ | ✓ | ✓ | Future |
| **3.3** BB Expansion | ✓ | ✓ | ✓ | ✓ | **v1** |
| **3.4** BB Squeeze | ✓ | ✓ | ✓ | ✓ | **v1** |
| **4.1** Wybicie oporu | ✓ | ✓ | ✓ | ✓ | **v1** |
| **4.2** Wybicie wsparcia | ✓ | ✓ | ✓ | ✓ | **v1** |
| **4.3** Trójkąt breakout | ✓ | ✓ | ✓ | ✓ | Future |
| **4.4** Kanał breakout | ✓ | ✓ | ✓ | ✓ | Future |
| **4.5** Flaga breakout | ✓ | ✓ | ✓ | ✓ | Future |
| **5.1** Młot/Wisielec | ✓ | ✓ | ✓ | ✓ | **v1** |
| **5.2** Shooting Star | ✓ | ✓ | ✓ | ✓ | **v1** |
| **5.3** Bullish Engulfing | ✓ | ✓ | ✓ | ✓ | **v1** |
| **5.4** Bearish Engulfing | ✓ | ✓ | ✓ | ✓ | **v1** |
| **5.5** Doji | ✓ | ✓ | ✓ | ✓ | Future |
| **5.6** Morning/Evening Star | ✓ | ✓ | ✓ | ✓ | Future |
| **5.7** Three White Soldiers | ✓ | ✓ | ✓ | ✓ | Future |
| **5.8** Three Black Crows | ✓ | ✓ | ✓ | ✓ | Future |
| **5.9** Marubozu | ✓ | ✓ | ✓ | ✓ | Future |
| **5.10** Harami | ✓ | ✓ | ✓ | ✓ | Future |
| **6.1** MA Crossover | ✓ | ✓ | ✓ | ✓ | **v1** |
| **6.2** MA Slope Change | ✓ | ✓ | ✓ | ✓ | Future |
| **6.3** Price vs MA | ✓ | ✓ | ✓ | ✓ | **v1** |
| **6.4** Seria świec | ✓ | ✓ | ✓ | ✓ | Future |
| **6.5** Trend Structure Change | ✓ | ✓ | ✓ | ✓ | **v1** |
| **7.1** RSI Overbought | ✓ | ✓ | ✓ | ✓ | **v1** |
| **7.2** RSI Oversold | ★ | ★ | ✓ | ✓ | **v1** |
| **7.3** RSI Divergence | ✓ | ✓ | ✓ | ✓ | Future |
| **7.4** MACD Crossover | ✓ | ✓ | ✓ | ✓ | **v1** |
| **7.5** MACD Zero Cross | ✓ | ✓ | ✓ | ✓ | Future |
| **7.6** Stochastic | ✓ | ✓ | ✓ | ✓ | Future |
| **8.1** OBV Divergence | ✓ | ✓ | ✓ | ✓ | Future |
| **8.2** VWAP Deviation | ✓ | ✓ | ✓ | ✓ | Future |
| **8.3** ATR Expansion | ✓ | ✓ | ✓ | ✓ | **v1** |
| **8.4** Fibonacci Hit | ✓ | ✓ | ✓ | ✓ | Future |
| **9.1** P/E Change | ✓ | ✓ | - | - | **v1** |
| **9.2** P/BV Change | ✓ | ✓ | - | - | Future |
| **9.3** Market Cap Change | ★ | ★ | - | - | Future |
| **9.4** Debt Change | ★ | ★ | - | - | Future |
| **9.5** Revenue Change | ✓ | ✓ | - | - | **v1** |
| **9.6** Net Income Change | ✓ | ✓ | - | - | **v1** |
| **10.1** Earnings Release | ★ | ★ | - | - | **v1** |
| **10.2** Earnings Beat | ★ | ★ | - | - | Future |
| **10.3** Earnings Miss | ★ | ★ | - | - | Future |
| **10.4** Guidance Update | ★ | ★ | - | - | **v1** |
| **11.1** Quarterly Report | ✓ | ✓ | - | - | Future |
| **11.2** Annual Report | ✓ | ✓ | - | - | Future |
| **11.3** Accounting Change | ✓ | ✓ | - | - | Future |
| **12.1** ESPI Filing | ★ | - | - | - | Future |
| **12.2** ESPI Delay | ★ | - | - | - | Future |
| **13.1** EBI Filing | ★ | - | - | - | Future |
| **14.1** Dividend Announcement | ✓ | ✓ | ✓ | - | Future |
| **14.2** Dividend Policy Change | ✓ | ✓ | - | - | Future |
| **14.3** Special Dividend | ✓ | ✓ | - | - | Future |
| **14.4** Ex-Dividend Date | ✓ | ✓ | ✓ | - | Future |
| **15.1** Split Announcement | ✓ | ✓ | ✓ | - | Future |
| **15.2** Split Execution | ✓ | ✓ | ✓ | ✓ | Future |
| **15.3** Reverse Split | ★ | ★ | - | - | Future |
| **16.1** Share Issuance | ★ | ★ | - | - | Future |
| **16.2** Rights Offering | ★ | ★ | - | - | Future |
| **16.3** Private Placement | ✓ | ✓ | - | - | Future |
| **17.1** Buyback Announcement | ★ | ★ | - | - | Future |
| **17.2** Buyback Execution | ✓ | ✓ | - | - | Future |
| **18.1** Insider Transaction | ★ | ★ | - | - | Future |
| **18.2** Insider Buying Cluster | ★ | ★ | - | - | Future |
| **18.3** Insider Selling Cluster | ★ | ★ | - | - | Future |
| **19.1** Threshold Crossing | ★ | - | - | - | Future |
| **19.2** Tender Offer | ★ | - | - | - | Future |
| **19.3** Major Shareholder Change | ✓ | ✓ | - | - | Future |
| **20.1** New Analyst Rating | ★ | ★ | - | - | Future |
| **20.2** Price Target Change | ✓ | ✓ | - | - | Future |
| **20.3** Upgrade/Downgrade | ✓ | ✓ | - | - | Future |
| **21.1** Credit Rating Change | ✓ | ✓ | - | - | Future |
| **21.2** Rating Outlook Change | ✓ | ✓ | - | - | Future |
| **22.1** M&A Announcement | ★ | ★ | - | - | Future |
| **22.2** M&A Rumors | ✓ | ✓ | - | - | Future |
| **22.3** M&A Completion/Failure | ✓ | ✓ | - | - | Future |
| **23.1** Major Contract | ★ | ★ | - | - | Future |
| **23.2** Contract Termination | ★ | ★ | - | - | Future |
| **24.1** Lawsuit Against | ★ | ★ | - | - | Future |
| **24.2** Lawsuit Filed By | ✓ | ✓ | - | - | Future |
| **25.1** Regulatory Investigation | ★ | ★ | - | - | Future |
| **25.2** Financial Penalty | ✓ | ✓ | - | - | Future |
| **25.3** Trading Suspension | ★ | ★ | - | - | Future |
| **26.1** Bankruptcy Filing | ★ | ★ | - | - | Future |
| **26.2** Restructuring | ✓ | ✓ | - | - | Future |
| **26.3** Counterparty Bankruptcy | ✓ | ✓ | - | - | Future |
| **27.1** CEO Change | ★ | ★ | - | - | Future |
| **27.2** Management Change | ✓ | ✓ | - | - | Future |
| **27.3** Supervisory Board Change | ✓ | ✓ | - | - | Future |
| **27.4** Key Employee Departure | ★ | ★ | - | - | Future |
| **28.1** Macro Data Release | ✓ | ✓ | ★ | ✓ | Future |
| **28.2** GDP Change | ✓ | ✓ | ★ | ✓ | Future |
| **28.3** Unemployment Change | ✓ | ✓ | ✓ | ✓ | Future |
| **29.1** Interest Rate Decision | ✓ | ✓ | ★ | ✓ | Future |
| **29.2** Emergency Rate Change | ✓ | ✓ | ✓ | ✓ | Future |
| **29.3** Forward Guidance Change | ✓ | ✓ | ✓ | ✓ | Future |
| **30.1** CPI/PPI Release | ✓ | ✓ | ★ | ✓ | Future |
| **30.2** Inflation Surprise | ✓ | ✓ | ★ | ✓ | Future |
| **31.1** Major FX Move | ★ | ✓ | ★ | ✓ | Future |
| **31.2** FX Intervention | ✓ | ✓ | ✓ | ✓ | Future |
| **32.1** Commodity Price Shock | ★ | ✓ | ★ | ✓ | Future |
| **32.2** Supply Shock | ✓ | ✓ | ✓ | ✓ | Future |
| **33.1** Armed Conflict | ★ | ✓ | ✓ | ✓ | Future |
| **33.2** Sanctions | ✓ | ✓ | ✓ | ✓ | Future |
| **33.3** Elections | ✓ | ✓ | ✓ | ✓ | Future |
| **33.4** Trade Agreement | ✓ | ✓ | ✓ | ✓ | Future |
| **34.1** Sector Rotation | - | - | ★ | - | Future |
| **34.2** Sector Regulation | ✓ | ✓ | ★ | ✓ | Future |
| **34.3** Sector Leader Bankruptcy | ✓ | ✓ | ✓ | ✓ | Future |
| **35.1** Correlation Breakdown | - | - | ★ | - | Future |
| **35.2** Correlation Strengthening | - | - | ★ | - | Future |
| **36.1** ETF Rebalancing | - | - | ★ | - | Future |
| **36.2** ETF Flows | - | - | ★ | - | Future |
| **36.3** ETF Premium/Discount | - | - | ★ | - | Future |
| **36.4** ETF Closure | - | - | ★ | - | Future |
| **37.1** Unusual Options Activity | - | ★ | - | - | Future |
| **37.2** IV Change | - | ✓ | ★ | - | Future |
| **37.3** Max Pain | - | ✓ | ✓ | - | Future |
| **38.1** Short Interest Increase | - | ★ | - | - | Future |
| **38.2** Short Squeeze | - | ★ | - | - | Future |
| **38.3** Days to Cover | - | ★ | - | - | Future |
| **39.1** Dark Pool Activity | - | ★ | - | - | Future |
| **40.1** Block Trade | - | ★ | - | - | Future |
| **40.2** Package Trade | ★ | - | - | - | Future |
| **41.1** Social Media Mentions | - | ★ | - | - | Future |
| **41.2** Reddit Trend | - | ★ | - | - | Future |
| **41.3** Influencer Mention | - | ★ | - | - | Future |
| **42.1** Sentiment Shift | ✓ | ✓ | ★ | ✓ | Future |
| **42.2** VIX Spike | ✓ | ✓ | ★ | ✓ | Future |
| **42.3** Put/Call Ratio | - | ✓ | ✓ | - | Future |
| **43.1** Breaking News | ✓ | ✓ | ✓ | ✓ | Future |
| **43.2** Analyst Article | ★ | ★ | - | - | Future |
| **43.3** Management Interview | ✓ | ✓ | - | - | Future |
| **44.1** Tavily Search Result | ✓ | ✓ | ✓ | ✓ | Future |
| **44.2** Tavily Sentiment Change | ✓ | ✓ | ✓ | ✓ | Future |
| **45.1** Composite Event | ✓ | ✓ | ✓ | ✓ | Future |
| **45.2** Instrument State Change | ✓ | ✓ | ✓ | ✓ | Future |
| **45.3** Event Recurrence | ✓ | ✓ | ✓ | ✓ | Future |
| **46.1** Spread Anomaly | - | - | ★ | - | Future |
| **46.2** Leader-Lag | ✓ | ✓ | ✓ | ✓ | Future |
| **47.1** Month/Quarter End | - | - | ★ | - | Future |
| **47.2** Triple Witching | - | ✓ | ★ | - | Future |
| **47.3** January Effect | ★ | ★ | - | - | Future |
| **47.4** Earnings Season | ★ | ★ | - | - | Future |

Legenda:
- **★** = szczególnie istotne dla tej grupy
- **✓** = istotne dla tej grupy
- **-** = nie dotyczy tej grupy
- **v1** = pierwsza wersja produkcyjna
- **Future** = do dodania w przyszłości

---

## TABELA: PRIORYTET WDROŻENIA

### Etap 1 — Fundament (MVP detektora zdarzeń) — `[v1]`

Wszystkie zdarzenia wykrywalne wyłącznie z yfinance (OHLCV), możliwe do implementacji w oparciu o istniejący TechnicalEngine.

| Kategoria | Zdarzenia v1 | Liczba |
|-----------|-------------|--------|
| Zdarzenia cenowe | 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8 | 8 |
| Zdarzenia wolumenowe | 2.1, 2.4, 2.5 | 3 |
| Zdarzenia zmienności | 3.1, 3.3, 3.4 | 3 |
| Wybicia techniczne | 4.1, 4.2 | 2 |
| Formacje świecowe | 5.1, 5.2, 5.3, 5.4 | 4 |
| Trend | 6.1, 6.3, 6.5 | 3 |
| Momentum | 7.1, 7.2, 7.4 | 3 |
| Wskaźniki techniczne | 8.3 | 1 |
| Fundamenty spółki | 9.1, 9.5, 9.6 | 3 |
| Wyniki finansowe | 10.1, 10.4 | 2 |
| **RAZEM v1** | | **32 zdarzenia** |

**Charakterystyka Etapu 1:**
- Wszystkie zdarzenia oparte na istniejącym TechnicalEngine + yfinance
- Pokrycie wszystkich trzech grup instrumentów (GPW, USA, ETF)
- Czas wdrożenia: najkrótszy — wykorzystanie istniejącej infrastruktury
- Zdarzenia techniczne stanowią trzon systemu

### Etap 2 — Rozszerzenie (źródła zewnętrzne) — `[Future]`

Zdarzenia wymagające NewsEngine + dodatkowych źródeł (ESPI, EBI, newsy, Tavily).

| Kategoria | Zdarzenia | Liczba |
|-----------|----------|--------|
| Raporty kwartalne | 11.1, 11.2, 11.3 | 3 |
| ESPI | 12.1, 12.2 | 2 |
| EBI | 13.1 | 1 |
| Dywidendy | 14.1, 14.2, 14.3, 14.4 | 4 |
| Splity | 15.1, 15.2, 15.3 | 3 |
| Emisje akcji | 16.1, 16.2, 16.3 | 3 |
| Skup akcji własnych | 17.1, 17.2 | 2 |
| Insider Trading | 18.1, 18.2, 18.3 | 3 |
| Zmiany akcjonariatu | 19.1, 19.2, 19.3 | 3 |
| Rekomendacje analityków | 20.1, 20.2, 20.3 | 3 |
| Ratingi | 21.1, 21.2 | 2 |
| Fuzje i przejęcia | 22.1, 22.2, 22.3 | 3 |
| Nowe kontrakty | 23.1, 23.2 | 2 |
| Pozwy | 24.1, 24.2 | 2 |
| Problemy prawne | 25.1, 25.2, 25.3 | 3 |
| Upadłości | 26.1, 26.2, 26.3 | 3 |
| Zmiany zarządu | 27.1, 27.2, 27.3, 27.4 | 4 |
| Makroekonomia | 28.1, 28.2, 28.3 | 3 |
| Stopy procentowe | 29.1, 29.2, 29.3 | 3 |
| Inflacja | 30.1, 30.2 | 2 |
| Waluty | 31.1, 31.2 | 2 |
| Surowce | 32.1, 32.2 | 2 |
| Sektor | 34.2 | 1 |
| Short Interest | 38.1, 38.2, 38.3 | 3 |
| Sentyment rynku | 42.2 | 1 |
| News | 43.1, 43.2, 43.3 | 3 |
| Tavily | 44.1, 44.2 | 2 |
| Alerty własne | 45.1, 45.2, 45.3 | 3 |
| Sezon wyników | 47.4 | 1 |
| **RAZEM Etap 2** | | **~70 zdarzeń** |

### Etap 3 — Zaawansowane (analityka i AI) — `[Future]`

Zdarzenia wymagające zaawansowanej analizy AI, Tavily, lub zewnętrznych API.

| Kategoria | Zdarzenia | Liczba |
|-----------|----------|--------|
| Zdarzenia cenowe | 1.9, 1.10 | 2 |
| Zdarzenia wolumenowe | 2.2, 2.3 | 2 |
| Zdarzenia zmienności | 3.2 | 1 |
| Wybicia techniczne | 4.3, 4.4, 4.5 | 3 |
| Formacje świecowe | 5.5, 5.6, 5.7, 5.8, 5.9, 5.10 | 6 |
| Trend | 6.2, 6.4 | 2 |
| Momentum | 7.3, 7.5, 7.6 | 3 |
| Wskaźniki techniczne | 8.1, 8.2, 8.4 | 3 |
| Fundamenty spółki | 9.2, 9.3, 9.4 | 3 |
| Wyniki finansowe | 10.2, 10.3 | 2 |
| Geopolityka | 33.1, 33.2, 33.3, 33.4 | 4 |
| Sektor | 34.1, 34.3 | 2 |
| Korelacje | 35.1 | 1 |
| ETF | 36.1, 36.2, 36.3, 36.4 | 4 |
| Opcje | 37.1, 37.2 | 2 |
| Nietypowe transakcje | 40.1, 40.2 | 2 |
| Media społecznościowe | 41.1, 41.2 | 2 |
| Sentyment rynku | 42.1 | 1 |
| Zdarzenia międzyinstrumentowe | 46.1 | 1 |
| **RAZEM Etap 3** | | **~46 zdarzeń** |

### Etap 4 — Kompletne (dane alternatywne i niszowe) — `[Future]`

Zdarzenia wymagające specjalistycznych, trudno dostępnych danych.

| Kategoria | Zdarzenia | Liczba |
|-----------|----------|--------|
| Opcje | 37.3 | 1 |
| Dark Pool | 39.1 | 1 |
| Media społecznościowe | 41.3 | 1 |
| Sentyment rynku | 42.3 | 1 |
| Korelacje | 35.2 | 1 |
| Zdarzenia międzyinstrumentowe | 46.2 | 1 |
| Zdarzenia sezonowe | 47.1, 47.2, 47.3 | 3 |
| **RAZEM Etap 4** | | **~9 zdarzeń** |

---

## PODSUMOWANIE: MAPOWANIE GRUP INSTRUMENTÓW NA ETAPY

| Grupa instrumentów | v1 (Etap 1) | Future (Etapy 2-4) | Łącznie |
|-------------------|:-----------:|:------------------:|:-------:|
| **GPW groszówki** | 32 | 95 | 127 |
| **USA groszówki** | 32 | 100 | 132 |
| **ETF** | 30 | 65 | 95 |
| **Universal (wszystkie 3)** | 28 | 45 | 73 |

*Uwaga: Liczby są orientacyjne — niektóre zdarzenia należą do wielu grup jednocześnie.*

---

## ZASADY ROZBUDOWY KATALOGU

1. **Nowe zdarzenia** dodawane są jako nowe podsekcje w istniejących kategoriach (jeśli pasują tematycznie) lub jako nowe kategorie (jeśli reprezentują nowy obszar).
2. **Nowe źródła danych** są integrowane przez HunterEngine bez modyfikacji istniejących silników.
3. **Nowe silniki** mogą być dodawane jako rozszerzenia — MasterEngine wspiera dependency injection.
4. **Nowe grupy instrumentów** (indeksy, surowce, waluty, kryptowaluty, obligacje, opcje, futures) otrzymają własne kolumny w tabeli klasyfikacji.
5. **Public API istniejących silników pozostaje niezmienione** — nowe funkcjonalności dodawane są przez nowe metody lub nowe silniki.

---

## KONIEC DOKUMENTU

Data utworzenia: 18.07.2026
Wersja: 2.0
Autor: Zespół ALCHEMIK
Status: Dokument projektowy — specyfikacja funkcjonalna

Zmiany w wersji 2.0:
- Dodano sekcję 0 (Zakres pierwszego etapu) z opisem trzech grup instrumentów
- Dodano klasyfikację `[GPW]`, `[USA]`, `[ETF]`, `[Universal]` dla każdego zdarzenia
- Dodano klasyfikację `[v1]` / `[Future]` dla każdego zdarzenia
- Dodano tabelę klasyfikacji wg grup instrumentów (sekcja 50)
- Zaktualizowano tabelę priorytetu wdrożenia z podziałem na 4 etapy
- Dodano podsumowanie mapowania grup instrumentów na etapy
- Dodano sekcję "Zasady rozbudowy katalogu"
- Dodano nowe zdarzenia ETF: 36.3 (ETF Premium/Discount), 36.4 (ETF Closure)
- Doprecyzowano istotność zdarzeń dla poszczególnych grup instrumentów