# ALCHEMIK — FILOZOFIA EventOutcome

## DOKUMENT ARCHITEKTONICZNY — ODPOWIEDZIALNOŚĆ DOMENOWA

Data: 30.07.2026
Wersja: 1.0
Status: Dokument architektoniczny — nie implementacyjny

---

## SPIS TREŚCI

1. [Cel dokumentu](#1-cel-dokumentu)
2. [MarketEvent — chwila wykrycia](#2-marketevent--chwila-wykrycia)
3. [EventOutcome — rezultat zdarzenia](#3-eventoutcome--rezultat-zdarzenia)
4. [Obliczanie faktów — komponent odpowiedzialny za wyliczanie EventOutcome](#4-obliczanie-faktów--komponent-odpowiedzialny-za-wyliczanie-eventoutcome)
5. [AI — interpretacja faktów](#5-ai--interpretacja-faktów)
6. [Jedno źródło prawdy](#6-jedno-źródło-prawdy)
7. [Rozszerzalność architektury](#7-rozszerzalność-architektury)
8. [Podział odpowiedzialności](#8-podział-odpowiedzialności)
9. [Relacja MarketEvent → EventOutcome](#9-relacja-marketevent--eventoutcome)
10. [Cykl życia EventOutcome](#10-cykl-życia-eventoutcome)
11. [Niezmienniki architektoniczne](#11-niezmienniki-architektoniczne)

---

## 1. CEL DOKUMENTU

Niniejszy dokument definiuje filozofię i odpowiedzialności architektoniczne nowego elementu domeny ALCHEMIKA: **EventOutcome**.

EventOutcome jest modelem domenowym opisującym rezultat zdarzenia rynkowego (`MarketEvent`). Dokument nie opisuje implementacji, bazy danych, API ani klas. Określa wyłącznie:

- odpowiedzialność każdego komponentu uczestniczącego w procesie analizy wyników,
- relację między MarketEvent a EventOutcome,
- granice między obliczaniem faktów a ich interpretacją,
- zasady rozszerzalności modelu,
- stany cyklu życia EventOutcome.

---

## 2. MarketEvent — CHWILA WYKRYCIA

### Zasada 1

**MarketEvent jest niezmiennym zapisem sytuacji rynkowej w momencie wykrycia zdarzenia.**

MarketEvent odpowiada wyłącznie na pytanie:

> **Co zostało wykryte?**

Po zapisaniu MarketEvent nie jest rozszerzany o informacje dotyczące przyszłych wyników. Nie przechowuje danych o tym, jak zachował się rynek po wystąpieniu zdarzenia. Jego odpowiedzialność kończy się w momencie archiwizacji — zawiera wyłącznie dane znane w chwili wykrycia i w trakcie późniejszego wzbogacania kontekstem (News, Tavily, AI).

MarketEvent **nie** odpowiada na pytania:

- Czy zdarzenie było trafnym sygnałem?
- Jak zmieniła się cena po +1, +2, +3, +5 sesjach?
- Jaki był zysk lub strata z hipotetycznej pozycji?

Te pytania należą do odpowiedzialności EventOutcome.

---

## 3. EventOutcome — REZULTAT ZDARZENIA

### Zasada 2

**EventOutcome jest osobnym modelem domenowym.**

EventOutcome:

- **nie opisuje rynku** — nie zawiera danych OHLCV, wskaźników technicznych ani kontekstu fundamentalnego;
- **nie opisuje spółki** — nie przechowuje danych o instrumentach, sektorach ani kategoriach;
- **opisuje wyłącznie rezultat konkretnego MarketEvent.**

Odpowiada na pytanie:

> **Jak zakończyło się to zdarzenie?**

### Zakres odpowiedzialności

EventOutcome zawiera obiektywne, wyliczone dane dotyczące wyniku zdarzenia. Są to fakty — nie interpretacje, nie prognozy, nie oceny jakości sygnału.

Przykładowe dane przechowywane w EventOutcome (pierwsza wersja):

- zmiana ceny po +1 sesji,
- zmiana ceny po +2 sesjach,
- zmiana ceny po +3 sesjach,
- zmiana ceny po +5 sesjach,
- zmiana wolumenu w tych samych horyzontach,
- kierunek trendu w momencie analizy,
- status ukończenia analizy dla każdego horyzontu.

EventOutcome **nie** zawiera:

- oceny, czy sygnał był dobry czy zły,
- rekomendacji inwestycyjnej,
- interpretacji przyczyn wyniku,
- porównania z innymi zdarzeniami.

---

## 4. OBLICZANIE FAKTÓW — KOMPONENT ODPOWIEDZIALNY ZA WYLICZANIE EVENTOUTCOME

### Zasada 3

**Komponent odpowiedzialny za wyliczanie EventOutcome działa według ściśle określonych reguł:**

Mechanizm ten działa według ściśle określonych reguł:

| Co robi | Czego nie robi |
|---------|----------------|
| pobiera dane rynkowe dla zadanego horyzontu | nie interpretuje wyniku |
| oblicza zmianę ceny w procentach i wartościach bezwzględnych | nie prognozuje przyszłych wyników |
| oblicza zmianę wolumenu | nie podejmuje decyzji |
| określa kierunek trendu na podstawie obiektywnych kryteriów | nie ocenia jakości sygnału |
| ustawia status ukończenia analizy | nie porównuje zdarzeń między sobą |

### Dane wejściowe i wyjściowe

**Wejście:**

- `MarketEvent` — identyfikator zdarzenia, ticker, timestamp wykrycia, dane cenowe z momentu wykrycia,
- dane rynkowe dla horyzontów sesyjnych — pozyskane przez HunterEngine (YahooFetcher) po upływie wymaganego czasu.

**Wyjście:**

- `EventOutcome` — obiekt zawierający wyłącznie obiektywnie wyliczone dane.

### Moment uruchomienia

Mechanizm wyliczający EventOutcome nie działa w momencie wykrycia zdarzenia. Jego uruchomienie następuje po upływie czasu potrzebnego do zebrania danych dla wszystkich wymaganych horyzontów. Jest to proces asynchroniczny względem pipeline'u detekcji.

---

## 5. AI — INTERPRETACJA FAKTÓW

### Zasada 4

**AI nie oblicza rezultatów zdarzenia. AI korzysta z gotowego EventOutcome.**

Role są ściśle rozdzielone:

| Komponent | Odpowiedzialność |
|-----------|-----------------|
| **Mechanizm wyliczający EventOutcome** | oblicza fakty (cena, wolumen, trend, status) |
| **AI** | interpretuje fakty na podstawie gotowego EventOutcome |

AI otrzymuje EventOutcome jako dane wejściowe. Nie ma dostępu do surowych danych rynkowych w celu samodzielnego wyliczania rezultatów. Nie powiela logiki mechanizmu wyliczającego EventOutcome.

Interpretacja AI może obejmować:

- ocenę trafności sygnału na podstawie wyników liczbowych,
- analizę wzorców w historycznych EventOutcome,
- identyfikację warunków, w których podobne zdarzenia kończyły się pozytywnie lub negatywnie,
- formułowanie wniosków w języku naturalnym.

AI **nie** może:

- samodzielnie obliczać zmiany ceny,
- podmieniać wartości wyliczonych przez mechanizm wyliczający EventOutcome,
- tworzyć równoległej ścieżki obliczania rezultatów.

---

## 6. JEDNO ŹRÓDŁO PRAWDY

### Zasada 5

**Wszystkie moduły analityczne korzystają z tego samego EventOutcome.**

Moduły konsumujące EventOutcome:

- **RiskEngine** — ocenia ryzyko na podstawie historycznych rezultatów zdarzeń,
- **Ranking** — ustala priorytet sygnałów z uwzględnieniem ich historycznej skuteczności,
- **AI** — interpretuje wyniki i generuje wnioski,
- **przyszłe moduły analityczne** — wszystkie nowe komponenty analityczne korzystają z EventOutcome jako jedynego źródła danych o rezultatach.

Zasada jednego źródła prawdy oznacza:

> **Nie powstają równoległe implementacje obliczania rezultatów.**

Każdy moduł, który potrzebuje informacji o tym, jak zakończyło się zdarzenie, pobiera je z EventOutcome. Żaden moduł nie oblicza rezultatów samodzielnie na podstawie surowych danych rynkowych.

EventOutcome stanowi **jedyne źródło prawdy** dla analizy historycznych wyników zdarzeń.

---

## 7. ROZSZERZALNOŚĆ ARCHITEKTURY

### Zasada 6

**Model od początku musi umożliwiać dalszą rozbudowę.**

### Pierwsza wersja — horyzonty sesyjne

Pierwsza implementacja obejmuje analizę w następujących horyzontach:

- +1 sesja,
- +2 sesje,
- +3 sesje,
- +5 sesji.

Każdy horyzont zawiera własny zestaw metryk oraz własny status ukończenia analizy.

### Planowane kierunki rozbudowy

Model musi od początku przewidywać dodanie:

- kolejnych horyzontów sesyjnych (np. +10, +15, +21 sesji),
- analizy tygodniowej (wynik po +1W, +2W, +4W),
- analizy miesięcznej (wynik po +1M, +3M, +6M),
- analizy intraday (wynik po +5min, +15min, +30min, +1h, +4h),
- nowych metryk (np. maksymalna korzystna/niekorzystna zmiana w horyzoncie, zmienność w horyzoncie, stosunek zysku do ryzyka).

### Zasada rozszerzeń

Rozszerzenia **nie wymagają zmiany filozofii modelu**. Dodanie nowego horyzontu lub metryki jest operacją addytywną — nie modyfikuje istniejących danych ani nie zmienia odpowiedzialności komponentów.

---

## 8. PODZIAŁ ODPOWIEDZIALNOŚCI

### Zasada 7

**Architektura projektu opiera się na jednoznacznym podziale odpowiedzialności. Żaden komponent nie przejmuje odpowiedzialności innego komponentu.**

| Komponent | Odpowiedzialność | Dane wejściowe | Dane wyjściowe |
|-----------|-----------------|----------------|----------------|
| **YahooFetcher** | pobiera surowe dane rynkowe | ticker, zakres dat | OHLCV |
| **TechnicalEngine** | analizuje dane techniczne | OHLCV | wskaźniki techniczne, kontekst |
| **Detektory** | wykrywają zdarzenia rynkowe | dane rynkowe, wskaźniki | MarketEvent (częściowy) |
| **MarketEvent** | zapisuje stan wykrycia | dane z detektorów | zamrożony obiekt zdarzenia |
| **Mechanizm wyliczający EventOutcome** | wylicza rezultat zdarzenia | MarketEvent + dane rynkowe dla horyzontów | EventOutcome |
| **EventOutcome** | przechowuje rezultat | dane z mechanizmu wyliczającego EventOutcome | obiektywne metryki wyniku |
| **AI** | interpretuje rezultat | EventOutcome + kontekst | interpretacja, wnioski |
| **RiskEngine** | ocenia ryzyko | EventOutcome + dane rynkowe | ocena ryzyka |
| **Ranking** | ustala priorytet | EventOutcome + metadane | ranking sygnałów |

### Granice odpowiedzialności

- **YahooFetcher** nie analizuje danych — jedynie je pobiera.
- **TechnicalEngine** nie wykrywa zdarzeń — jedynie przygotowuje dane techniczne.
- **Detektory** nie obliczają rezultatów — jedynie identyfikują wystąpienie zdarzenia.
- **MarketEvent** nie przechowuje wyników — jedynie stan w momencie wykrycia.
- **Mechanizm wyliczający EventOutcome** nie interpretuje — jedynie oblicza.
- **EventOutcome** nie ocenia — jedynie przechowuje fakty.
- **AI** nie oblicza — jedynie interpretuje gotowe dane.
- **RiskEngine** nie ustala priorytetów — jedynie ocenia ryzyko.
- **Ranking** nie ocenia ryzyka — jedynie porządkuje sygnały.

---

## 9. RELACJA MarketEvent → EventOutcome

### Relacja 1 : 1

```
MarketEvent
      │
      │ 1 : 1
      ▼
EventOutcome
```

**Każdy MarketEvent posiada dokładnie jeden EventOutcome.**

Nie istnieje MarketEvent bez EventOutcome. Nie istnieje EventOutcome bez powiązanego MarketEvent. Relacja jest kardynalna: jeden do jednego.

### Uzasadnienie

- MarketEvent opisuje, co zostało wykryte.
- EventOutcome opisuje, jak to się zakończyło.
- Te dwie perspektywy są nierozłączne — każde zdarzenie ma swój wynik, a każdy wynik należy do konkretnego zdarzenia.

Relacja 1:1 jest świadomą decyzją architektoniczną. Eliminuje ona:

- niejednoznaczność przypisania wyniku do zdarzenia,
- możliwość powstania osieroconych wyników,
- ryzyko wielokrotnego obliczania wyniku dla tego samego zdarzenia.

---

## 10. CYKL ŻYCIA EventOutcome

EventOutcome posiada własny cykl życia, niezależny od cyklu życia MarketEvent.

### Stany EventOutcome

| Stan | Opis | Znaczenie |
|------|------|-----------|
| **PENDING** | EventOutcome utworzony, oczekuje na dane rynkowe dla pierwszego horyzontu | Analiza jeszcze się nie rozpoczęła. Brakuje danych dla nawet najkrótszego horyzontu. |
| **PARTIAL** | Część horyzontów została obliczona, część wciąż oczekuje na dane | Analiza w toku. Niektóre horyzonty są już dostępne (np. +1 sesja), inne wymagają więcej czasu (np. +5 sesji). |
| **COMPLETE** | Wszystkie wymagane horyzonty zostały obliczone | Analiza zakończona. Wszystkie metryki dostępne. |
| **FAILED** | Obliczenie nie powiodło się z przyczyn technicznych | Brak możliwości pobrania danych rynkowych dla wymaganych horyzontów. Przyczyny mogą obejmować: zawieszenie notowań, brak danych w źródle, błąd połączenia. |
| **INVALID** | Zdarzenie nie podlega analizie Outcome | MarketEvent został oznaczony jako IGNORE, jest duplikatem lub reprezentuje typ zdarzenia, dla którego analiza rezultatów nie ma zastosowania. |

### Przejścia między stanami

```
PENDING ──────► PARTIAL ──────► COMPLETE
   │                │
   │                │
   ▼                ▼
FAILED / INVALID  FAILED / INVALID
```

- **PENDING → PARTIAL**: upłynął minimalny czas dla pierwszego horyzontu, mechanizm wyliczający EventOutcome obliczył dostępne metryki.
- **PARTIAL → COMPLETE**: upłynął czas dla wszystkich wymaganych horyzontów, wszystkie metryki zostały obliczone pomyślnie.
- **PENDING → FAILED**: nie udało się pobrać danych dla żadnego horyzontu.
- **PARTIAL → FAILED**: nie udało się pobrać danych dla pozostałych horyzontów.
- **PENDING → INVALID**: zdarzenie zostało oznaczone jako niepodlegające analizie przed rozpoczęciem obliczeń.
- **PARTIAL → INVALID**: zdarzenie zostało retrospektywnie uznane za niepodlegające analizie (rzadki przypadek).

### Niezależność cyklów życia

Cykl życia EventOutcome jest **niezależny** od cyklu życia MarketEvent. MarketEvent może być już dawno zarchiwizowany, podczas gdy EventOutcome wciąż znajduje się w stanie PARTIAL (oczekując na dane dla dłuższych horyzontów). Stan COMPLETE EventOutcome może zostać osiągnięty godziny, dni lub tygodnie po zarchiwizowaniu MarketEvent — w zależności od najdłuższego wymaganego horyzontu.

---

## 11. NIEZMIENNIKI ARCHITEKTONICZNE

Niezmienniki to zasady, które muszą być spełnione zawsze, niezależnie od wersji systemu, konfiguracji czy rozszerzeń modelu.

### N1. Jeden MarketEvent — jeden EventOutcome

Relacja 1:1 jest nienaruszalna. Każdy MarketEvent ma dokładnie jeden EventOutcome. Każdy EventOutcome jest powiązany z dokładnie jednym MarketEvent.

### N2. EventOutcome przechowuje wyłącznie fakty

EventOutcome nie zawiera interpretacji, ocen, rekomendacji ani prognoz. Zawiera wyłącznie obiektywnie wyliczone wartości liczbowe oraz statusy operacyjne.

### N3. Mechanizm wyliczający EventOutcome nie interpretuje

Mechanizm wyliczający EventOutcome wykonuje wyłącznie operacje matematyczne na danych rynkowych. Nie stosuje heurystyk oceny jakości sygnału. Nie porównuje wyników między zdarzeniami.

### N4. AI nie oblicza rezultatów

AI otrzymuje EventOutcome jako niezmienny input. Nie ma możliwości modyfikacji wartości w EventOutcome. Nie może uruchomić własnego procesu obliczania zmiany ceny.

### N5. Jedno źródło prawdy

Wszystkie moduły analityczne korzystają z EventOutcome jako jedynego źródła danych o historycznych wynikach zdarzeń. Nie istnieje alternatywna ścieżka obliczania rezultatów.

### N6. Rozszerzenia są addytywne

Dodanie nowego horyzontu czasowego lub nowej metryki nie modyfikuje istniejących danych. Nowe dane są dodawane obok istniejących, bez nadpisywania ich.

### N7. Cykl życia EventOutcome jest niezależny

EventOutcome ma własny cykl życia, niezależny od MarketEvent. MarketEvent może być zarchiwizowany przed osiągnięciem przez EventOutcome stanu COMPLETE.

### N8. Stan FAILED i INVALID są terminalne

Po przejściu EventOutcome w stan FAILED lub INVALID nie następuje ponowna próba obliczenia. Decyzja o zakończeniu analizy jest ostateczna.

---

## KONIEC DOKUMENTU

Data utworzenia: 30.07.2026
Wersja: 1.0
Autor: Zespół ALCHEMIK
Status: Dokument architektoniczny — filozofia EventOutcome

Dokumenty powiązane:
- `docs/MODEL_EVENTOUTCOME.md` — projekt domenowy modelu EventOutcome (struktura, cykl życia, niezmienniki)
- `docs/Kontrakt_Zdarzen_Rynkowych.md` — definiuje kontrakt MarketEvent, którego rezultaty opisuje EventOutcome.
