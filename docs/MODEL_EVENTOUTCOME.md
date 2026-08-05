# ALCHEMIK — MODEL DOMENOWY EventOutcome

## DOKUMENT ARCHITEKTONICZNY — PROJEKT MODELU

Data: 30.07.2026
Wersja: 1.0
Status: Dokument projektowy — nie implementacyjny

---

## SPIS TREŚCI

1. [Cel modelu](#1-cel-modelu)
2. [Kontekst domenowy](#2-kontekst-domenowy)
3. [Odpowiedzialność modelu](#3-odpowiedzialność-modelu)
4. [Granice odpowiedzialności](#4-granice-odpowiedzialności)
5. [Tożsamość i relacja z MarketEvent](#5-tożsamość-i-relacja-z-marketevent)
6. [Struktura logiczna](#6-struktura-logiczna)
7. [Źródła danych](#7-źródła-danych)
8. [Wartości bazowe](#8-wartości-bazowe)
9. [Cykl życia](#9-cykl-życia)
10. [Tabela przejść stanów](#10-tabela-przejść-stanów)
11. [Stopniowe uzupełnianie](#11-stopniowe-uzupełnianie)
12. [Kompletność i jakość danych](#12-kompletność-i-jakość-danych)
13. [Granica względem SessionOutcome](#13-granica-względem-sessionoutcome)
14. [Niezmienniki domenowe](#14-niezmienniki-domenowe)
15. [Przypadki brzegowe](#15-przypadki-brzegowe)
16. [Otwarte decyzje](#16-otwarte-decyzje)

---

## 1. CEL MODELU

EventOutcome jest modelem domenowym reprezentującym **wynik zdarzenia rynkowego po jego wykryciu**.

Model odpowiada na pytanie:

> **Jak zakończyło się to zdarzenie?**

EventOutcome stanowi **jedyne źródło prawdy** dla historycznych rezultatów zdarzeń w systemie ALCHEMIK. Jest oddzielonym modelem domenowym, niezależnym od niezmiennego snapshotu `MarketEvent`.

Dokument definiuje odpowiedzialność, strukturę logiczną, cykl życia, niezmienniki i granice modelu. Nie definiuje implementacji, bazy danych, API ani klas.

---

## 2. KONTEKST DOMENOWY

### 2.1 Miejsce w architekturze

```
MarketEvent                 EventOutcome
(chwila wykrycia)   1:1    (rezultat zdarzenia)
     │                          │
     │ niezmienny snapshot       │ stopniowo uzupełniany
     │ po archiwizacji           │ niezależny cykl życia
     │                          │
     ▼                          ▼
[Archiwizacja]             [Jedyne źródło prawdy
                            dla historycznych wyników]
```

### 2.2 Relacja z innymi elementami architektury

| Element | Relacja z EventOutcome |
|---------|----------------------|
| **MarketEvent** | Źródło wartości bazowych i identyfikatora. Relacja 1:1 |
| **Komponent obliczeniowy** (przyszły) | Tworzy i aktualizuje EventOutcome. Oblicza fakty na podstawie danych rynkowych |
| **SessionOutcome** (przyszły) | Będzie przechowywał szczegółowe wyniki per-horyzont. EventOutcome nie tworzy od niego zależności architektonicznej |
| **AI** | Konsumuje gotowy EventOutcome jako input do interpretacji |
| **Risk** | Wykorzystuje historyczne EventOutcome do oceny ryzyka |
| **Ranking** | Uwzględnia historyczną skuteczność na podstawie EventOutcome |

### 2.3 Dokumenty nadrzędne

Model jest zgodny z:
- `docs/FILOZOFIA_EVENTOUTCOME.md` — filozofia odpowiedzialności EventOutcome
- `docs/FILOZOFIA_ALCHEMIKA.md` — filozofia działania systemu
- `docs/Kontrakt_Zdarzen_Rynkowych.md` — kontrakt MarketEvent
- `docs/Przeplyw_Zdarzen_Rynkowych.md` — cykl życia MarketEvent

W przypadku sprzeczności, dokumenty nadrzędne mają pierwszeństwo.

---

## 3. ODPOWIEDZIALNOŚĆ MODELU

### 3.1 Co EventOutcome reprezentuje

EventOutcome reprezentuje **obiektywny, wyliczony rezultat zdarzenia rynkowego**. Jest kontenerem faktów — nie interpretacji, nie prognoz, nie ocen jakości sygnału.

### 3.2 Za jakie dane odpowiada

- **Tożsamość wyniku** — jednoznaczna identyfikacja w systemie
- **Powiązanie ze zdarzeniem źródłowym** — niezmienne wskazanie MarketEvent
- **Stan cyklu życia** — na jakim etapie obliczeń znajduje się wynik
- **Wartości bazowe** — kontrolowana kopia danych z momentu wykrycia (cena, wolumen, timestamp)
- **Poziom kompletności** — zbiorcza informacja o stanie wyliczeń
- **Informacje o błędach i przyczynach niewyliczalności** — dane do audytu
- **Metadane obliczeń** — timestampy prób, wersja reguł

### 3.3 Czego nie może zawierać

EventOutcome **nie** przechowuje:

- decyzji inwestycyjnej,
- rekomendacji AI (BUY/SELL/HOLD),
- oceny ryzyka (risk_score, risk_level),
- pozycji rankingowej,
- narracyjnej interpretacji rezultatu („sygnał był trafny", „zdarzenie okazało się fałszywe"),
- danych niezwiązanych bezpośrednio z rezultatem konkretnego MarketEvent,
- szczegółowych metryk dla pojedynczych horyzontów sesyjnych (należą do przyszłego SessionOutcome),
- surowych danych rynkowych OHLCV dla przyszłych sesji.

### 3.4 Czym różni się od MarketEvent

| Aspekt | MarketEvent | EventOutcome |
|--------|-------------|--------------|
| **Moment danych** | Chwila wykrycia | Po wykryciu (przyszłość względem zdarzenia) |
| **Charakter danych** | Stan rynku | Rezultat zdarzenia |
| **Niezmienność** | Identyfikacyjna od utworzenia; snapshot zamrożony po archiwizacji | Stopniowo uzupełniany w czasie |
| **Źródło danych** | Detektory, silniki | Komponent obliczeniowy + dane rynkowe dla horyzontów |
| **Pytanie, na które odpowiada** | „Co zostało wykryte?" | „Jak zakończyło się to zdarzenie?" |

### 3.5 Czym różni się od przyszłego SessionOutcome

| Aspekt | EventOutcome | SessionOutcome (przyszły) |
|--------|-------------|--------------------------|
| **Poziom agregacji** | Całe zdarzenie | Pojedynczy horyzont sesyjny |
| **Dane** | Zbiorcze: kompletność, postęp, stan | Szczegółowe: cena, zmiana %, wolumen dla konkretnej sesji |
| **Liczność** | 1 na MarketEvent | wiele na MarketEvent (po jednym na horyzont) |

### 3.6 Czym różni się od interpretacji AI, Risk i Ranking

EventOutcome jest **źródłem danych** dla AI, Risk i Ranking. Żaden z tych komponentów nie modyfikuje EventOutcome. AI interpretuje wyniki, Risk ocenia ryzyko, Ranking porządkuje — wszystkie korzystają z gotowych danych, nie tworzą ich.

---

## 4. GRANICE ODPOWIEDZIALNOŚCI

### 4.1 Tabela granic

| Element | Odpowiedzialność | Czego nie przechowuje ani nie oblicza |
|---------|-----------------|--------------------------------------|
| **MarketEvent** | Zapisuje stan rynku w chwili wykrycia. Dostarcza wartości bazowe | Nie przechowuje przyszłych wyników. Nie zawiera metryk rezultatu |
| **EventOutcome** | Opisuje rezultat całego zdarzenia. Przechowuje informacje zbiorcze o postępie i kompletności | Nie przechowuje metryk per-horyzont. Nie interpretuje. Nie zawiera decyzji inwestycyjnych |
| **SessionOutcome** (przyszły) | Będzie opisywał wynik pojedynczego horyzontu | Zakres zostanie określony w KROKU 3C |
| **Komponent obliczeniowy** (przyszły) | Oblicza fakty: pobiera dane, wylicza zmiany, ustawia statusy | Nie interpretuje wyników. Nie modyfikuje MarketEvent |
| **AI** | Interpretuje gotowy EventOutcome | Nie oblicza zmian cen. Nie modyfikuje EventOutcome |
| **Risk** | Ocenia ryzyko na podstawie EventOutcome | Nie oblicza rezultatów zdarzeń |
| **Ranking** | Porządkuje sygnały na podstawie EventOutcome | Nie tworzy własnych metryk skuteczności |

### 4.2 Zasada jednego źródła prawdy

EventOutcome jest **jedynym źródłem prawdy** o historycznych wynikach zdarzeń. Wszystkie moduły analityczne (AI, Risk, Ranking) korzystają z tego samego EventOutcome. Nie istnieje alternatywna ścieżka obliczania rezultatów.

---

## 5. TOŻSAMOŚĆ I RELACJA Z MarketEvent

### 5.1 Rozstrzygnięcie architektoniczne

**EventOutcome posiada własną tożsamość domenową ORAZ przechowuje identyfikator źródłowego MarketEvent.**

Decyzja opiera się na następujących przesłankach:

1. **Niezależny cykl życia** — EventOutcome powstaje, żyje i osiąga stany końcowe niezależnie od MarketEvent. Własna tożsamość odzwierciedla tę niezależność.

2. **Relacja 1:1 przez referencję** — EventOutcome przechowuje `source_event_id` jako niezmienne wskazanie MarketEvent. To gwarantuje integralność relacji.

3. **Zabezpieczenie przed przepięciem** — identyfikator źródłowego MarketEvent jest ustawiany raz i nigdy nie jest zmieniany. Wynik nie może zostać „przepięty" do innego zdarzenia.

4. **Odporność na brak zdarzenia źródłowego** — EventOutcome nie może istnieć bez wskazania MarketEvent. Próba utworzenia EventOutcome bez poprawnego `source_event_id` jest błędem domenowym.

### 5.2 Reguła 1:1

- Dla jednego MarketEvent może istnieć **najwyżej jeden** EventOutcome.
- EventOutcome nie może istnieć bez wskazania zdarzenia źródłowego.
- Powiązanie jest ustanawiane raz i nigdy nie jest zmieniane.
- Identyfikatorem źródłowym jest `MarketEvent.event_id` (UUID v4).

### 5.3 Tożsamość domenowa

| Element | Opis |
|---------|------|
| **Identyfikator własny** | Unikalny identyfikator EventOutcome, niezależny od MarketEvent. Generowany przy utworzeniu |
| **Identyfikator źródłowy** | `MarketEvent.event_id` — niezmienne wskazanie zdarzenia, którego dotyczy wynik |
| **Unikalność** | Jeden `source_event_id` może występować w najwyżej jednym EventOutcome |

---

## 6. STRUKTURA LOGICZNA

Model jest zorganizowany w logiczne grupy danych. Poniższa tabela definiuje elementy modelu na poziomie domenowym — bez typów implementacyjnych, klas, ORM ani struktur specyficznych dla języka.

| # | Grupa | Element | Znaczenie domenowe | Wymagalność | Źródło danych | Kto uzupełnia | Czy może się zmienić |
|---|-------|---------|-------------------|-------------|---------------|---------------|---------------------|
| **Identyfikacja** |
| 1 | Identyfikacja | Identyfikator własny EventOutcome | Unikalny identyfikator wyniku w systemie. Niezależny od MarketEvent | Zawsze | Generowany przy utworzeniu | Komponent obliczeniowy | NIE |
| 2 | Identyfikacja | Identyfikator źródłowego MarketEvent | Niezmienne powiązanie 1:1 z MarketEvent. `MarketEvent.event_id` | Zawsze | MarketEvent | Komponent obliczeniowy | NIE (ustawiany raz) |
| **Stan cyklu życia** |
| 3 | Stan | Stan cyklu życia | Aktualny stan wyniku: PENDING, PARTIAL, COMPLETE, FAILED, INVALID | Zawsze | Ustalany przy utworzeniu, aktualizowany | Komponent obliczeniowy | TAK (według reguł przejść) |
| **Wartości bazowe** |
| 4 | Wartości bazowe | Cena bazowa | Cena zamknięcia instrumentu w momencie wykrycia zdarzenia (z MarketEvent.price_data.close). Punkt odniesienia dla wszystkich obliczeń zmiany | Zawsze (chyba że INVALID) | MarketEvent | Komponent obliczeniowy (kopia przy utworzeniu) | NIE (zamrożona kopia) |
| 5 | Wartości bazowe | Wolumen bazowy | Wolumen w momencie wykrycia zdarzenia (z MarketEvent.volume_data). Punkt odniesienia dla analizy zmian wolumenu | Warunkowo (jeśli dostępny w MarketEvent) | MarketEvent | Komponent obliczeniowy (kopia przy utworzeniu) | NIE (zamrożona kopia) |
| 6 | Wartości bazowe | Timestamp wykrycia | Moment wykrycia zdarzenia (MarketEvent.timestamp_utc). Wyznacza początek horyzontów czasowych | Zawsze | MarketEvent | Komponent obliczeniowy (kopia przy utworzeniu) | NIE (zamrożona kopia) |
| 7 | Wartości bazowe | Symbol instrumentu | Ticker instrumentu (MarketEvent.ticker). Potrzebny do pobierania przyszłych danych i identyfikacji wizualnej | Zawsze | MarketEvent | Komponent obliczeniowy (kopia przy utworzeniu) | NIE (zamrożona kopia) |
| 8 | Wartości bazowe | Rynek notowań | Rynek instrumentu (MarketEvent.market). Potrzebny do określenia kalendarza sesji | Zawsze | MarketEvent | Komponent obliczeniowy (kopia przy utworzeniu) | NIE (zamrożona kopia) |
| **Kompletność** |
| 9 | Kompletność | Oczekiwana liczba horyzontów | Liczba horyzontów sesyjnych przewidzianych do analizy dla tego zdarzenia. Definiuje, kiedy wynik może stać się COMPLETE | Zawsze | Ustalane przy tworzeniu na podstawie konfiguracji | Komponent obliczeniowy | NIE (ustalane raz) |
| 10 | Kompletność | Liczba wyliczonych horyzontów | Ile horyzontów zostało już pomyślnie przeliczonych. 0 → PENDING, częściowa → PARTIAL, równa oczekiwanej → COMPLETE | Zawsze | Wyliczane przy każdej aktualizacji | Komponent obliczeniowy | TAK (rośnie monotonicznie) |
| 11 | Kompletność | Informacja o brakujących horyzontach | Zbiorcze wskazanie, dla których horyzontów brakuje jeszcze danych (np. identyfikatory horyzontów). Nie zawiera szczegółowych metryk | Warunkowo (gdy stan ≠ COMPLETE) | Wyliczane przy każdej aktualizacji | Komponent obliczeniowy | TAK |
| **Błędy i niewyliczalność** |
| 12 | Błędy | Przyczyna stanu FAILED | Techniczna przyczyna niepowodzenia: błąd połączenia, timeout, brak danych w źródle, błąd walidacji danych. Informacja możliwa do audytu | Warunkowo (gdy stan = FAILED) | Komponent obliczeniowy | Komponent obliczeniowy | NIE (po przejściu w FAILED) |
| 13 | Błędy | Przyczyna stanu INVALID | Domenowa przyczyna niewyliczalności — dlaczego zdarzenie nie podlega analizie rezultatu. Możliwa do audytu. Konkretne reguły biznesowe zostaną określone podczas projektowania logiki | Warunkowo (gdy stan = INVALID) | Ustalane przy tworzeniu EventOutcome | Komponent obliczeniowy | NIE (po przejściu w INVALID) |
| **Metadane obliczeń** |
| 14 | Metadane | Timestamp ostatniej próby obliczenia | Kiedy ostatnio podjęto próbę aktualizacji wyniku. Umożliwia monitorowanie i diagnozowanie opóźnień | Zawsze | Ustawiany przy każdej próbie | Komponent obliczeniowy | TAK |
| 15 | Metadane | Timestamp ostatniej udanej aktualizacji | Kiedy ostatnio pomyślnie zaktualizowano wynik (nowe horyzonty zostały dodane). Różnica między tym a timestampem próby wskazuje na problemy | Warunkowo (gdy była co najmniej jedna udana aktualizacja) | Ustawiany przy udanej aktualizacji | Komponent obliczeniowy | TAK |
| 16 | Metadane | Wersja reguł obliczeniowych | Identyfikator wersji reguł użytych do obliczeń. Umożliwia reprodukowalność i audyt | Zawsze | Konfiguracja komponentu obliczeniowego | Komponent obliczeniowy | TAK (przy zmianie reguł) |
| 17 | Metadane | Identyfikator źródła danych | Wskazanie, które źródło danych rynkowych zostało użyte (np. Yahoo Finance). Do audytu | Zawsze | Konfiguracja komponentu obliczeniowego | Komponent obliczeniowy | TAK (jeśli źródło się zmieni) |

---

## 7. ŹRÓDŁA DANYCH

### 7.1 Dane pochodzące z MarketEvent (kopiowane przy utworzeniu)

| Dane | Pole źródłowe w MarketEvent | Sposób użycia |
|------|---------------------------|---------------|
| Identyfikator zdarzenia źródłowego | `event_id` | Powiązanie 1:1 |
| Cena bazowa | `price_data.close` | Punkt odniesienia do obliczeń zmiany ceny |
| Wolumen bazowy | `volume_data.current_volume` (jeśli dostępne) | Punkt odniesienia do analizy zmian wolumenu |
| Timestamp wykrycia | `timestamp_utc` | Początek horyzontów czasowych |
| Symbol instrumentu | `ticker` | Identyfikacja instrumentu do pobierania przyszłych danych |
| Rynek notowań | `market` | Określenie kalendarza sesji |

### 7.2 Dane pochodzące z rynku (pobierane przez komponent obliczeniowy)

| Dane | Źródło | Sposób użycia |
|------|--------|---------------|
| Ceny zamknięcia dla przyszłych sesji | HunterEngine / YahooFetcher | Podstawa do obliczeń zmian |
| Wolumeny dla przyszłych sesji | HunterEngine / YahooFetcher | Podstawa do analizy zmian wolumenu |
| Kalendarz sesji dla rynku | Konfiguracja / dane rynkowe | Określenie, które dni są sesyjne |

### 7.3 Dane konfiguracyjne

| Dane | Źródło | Sposób użycia |
|------|--------|---------------|
| Lista horyzontów do analizy | Konfiguracja systemu | Określenie oczekiwanej liczby horyzontów |
| Wersja reguł obliczeniowych | Konfiguracja komponentu | Metadane do audytu |

---

## 8. WARTOŚCI BAZOWE

### 8.1 Rozstrzygnięcie architektoniczne

**EventOutcome przechowuje kontrolowaną kopię wartości bazowych z MarketEvent.**

### 8.2 Uzasadnienie

| Wariant | Zalety | Wady |
|---------|--------|------|
| **Referencja do MarketEvent** | Brak duplikacji danych | Zależność od dostępności MarketEvent w pamięci. Ryzyko utraty spójności, jeśli MarketEvent zostałby technicznie zmodyfikowany po archiwizacji. Utrudniona reprodukowalność |
| **Kontrolowana kopia** | Pełna autonomia EventOutcome. Gwarancja historycznej spójności. Reprodukowalność — wynik można zweryfikować mając tylko EventOutcome. Niezależność od cyklu życia MarketEvent | Minimalna redundancja (kilka pól bazowych) |

**Wybrano kontrolowaną kopię.** Chroni to historyczną spójność danych. EventOutcome może istnieć i być audytowany nawet wtedy, gdy oryginalny MarketEvent zostałby z jakiegoś powodu utracony. Koszt redundancji jest znikomy (kilka pól skalarnych).

### 8.3 Zasada

> Źródłem wartości bazowych jest oryginalny MarketEvent. Wartości są kopiowane raz, w momencie utworzenia EventOutcome. Nie wolno pobierać nowej wartości bazowej z rynku podczas późniejszego obliczania wyniku. Wartości bazowe nie są modyfikowane po utworzeniu EventOutcome.

---

## 9. CYKL ŻYCIA

Cykl życia EventOutcome jest **niezależny** od cyklu życia MarketEvent. MarketEvent może być już dawno zarchiwizowany, podczas gdy EventOutcome wciąż znajduje się w stanie PARTIAL.

### 9.1 Stan PENDING

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | EventOutcome został utworzony. Oczekuje na dostępność danych rynkowych dla pierwszego horyzontu czasowego. Żaden horyzont nie został jeszcze obliczony |
| **Warunki wejścia** | Utworzenie EventOutcome po zarchiwizowaniu MarketEvent |
| **Liczba wyliczonych horyzontów** | 0 |
| **Możliwe przejścia** | → PARTIAL (pierwszy horyzont wyliczony) |
| | → FAILED (błąd techniczny przy próbie pobrania danych) |
| | → INVALID (zdarzenie nie podlega analizie — ustalone przy tworzeniu) |
| **Ponowienie** | Tak — komponent obliczeniowy może wielokrotnie podejmować próbę przejścia do PARTIAL |

### 9.2 Stan PARTIAL

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | Część horyzontów została obliczona, część wciąż oczekuje na dane. Analiza jest w toku |
| **Warunki wejścia** | Co najmniej jeden horyzont został pomyślnie wyliczony, ale nie wszystkie oczekiwane |
| **Liczba wyliczonych horyzontów** | > 0 i < oczekiwana liczba |
| **Możliwe przejścia** | → COMPLETE (wszystkie horyzonty wyliczone) |
| | → PARTIAL (kolejne horyzonty wyliczone — ten sam stan, aktualizacja danych) |
| | → FAILED (błąd techniczny uniemożliwiający dokończenie) |
| **Zabronione przejścia** | → PENDING (nie można cofnąć postępu) |
| | → INVALID (decyzja o niewyliczalności zapada przed rozpoczęciem obliczeń) |
| **Ponowienie** | Tak — komponent obliczeniowy regularnie sprawdza dostępność kolejnych horyzontów |

### 9.3 Stan COMPLETE

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | Wszystkie oczekiwane horyzonty zostały pomyślnie obliczone. Analiza rezultatu jest zakończona |
| **Warunki wejścia** | Liczba wyliczonych horyzontów = oczekiwana liczba horyzontów. Wszystkie obliczenia zakończone powodzeniem |
| **Liczba wyliczonych horyzontów** | = oczekiwana liczba |
| **Możliwe przejścia** | Brak — stan końcowy |
| **Zabronione przejścia** | → PARTIAL, PENDING (nie można cofnąć kompletności) |
| | → FAILED (błędy po COMPLETE nie zmieniają stanu — wynik jest kompletny) |

### 9.4 Stan FAILED

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | Obliczenie wyniku nie powiodło się z przyczyn technicznych. Stan jest terminalny w obecnej wersji modelu |
| **Warunki wejścia** | Błąd techniczny: brak połączenia z API, timeout, brak danych w źródle dla wszystkich wymaganych horyzontów, błąd walidacji pobranych danych |
| **Przyczyna** | Zawsze obecna — możliwa do audytu (np. `CONNECTION_TIMEOUT`, `NO_DATA_FOR_TICKER`, `API_ERROR`) |
| **Możliwe przejścia** | Brak — stan końcowy (wersja 1.0) |
| **Zabronione przejścia** | → COMPLETE (nie można uznać za kompletny wyniku, którego nie udało się wyliczyć) |
| **Ponowienie** | Wersja 1.0: FAILED jest terminalny. Przyszłe wersje mogą dopuścić ponowienie po błędzie technicznym — decyzja projektowa do podjęcia |

### 9.5 Stan INVALID

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | Zdarzenie nie podlega analizie rezultatu. Stan jest terminalny |
| **Warunki wejścia** | Ustalane przy tworzeniu EventOutcome na podstawie charakterystyki zdarzenia źródłowego. Model zapewnia mechanizm przechowywania przyczyny — konkretne reguły biznesowe określi logika domenowa |
| **Przyczyna** | Zawsze obecna — możliwa do audytu przyczyna domenowa |
| **Możliwe przejścia** | Brak — stan końcowy |
| **Zabronione przejścia** | Wszystkie — INVALID jest nieodwracalny |

### 9.6 Diagram przejść

```
                    ┌──────────────┐
                    │   PENDING    │
                    │ (0 horyzontów)│
                    └──┬───┬───┬───┘
                       │   │   │
           pierwszy    │   │   │
           horyzont    │   │   │
           wyliczony   │   │   │
                       │   │   │
                    ┌──▼─┐ │   │
                    │PART│ │   │
                    │IAL │ │   │
                    └┬─┬─┘ │   │
         wszystkie    │    │   │
         horyzonty    │    │   │
         wyliczone    │    │   │
                      │    │   │
                   ┌──▼─┐  │   │
                   │COMP│  │   │
                   │LETE│  │   │
                   └────┘  │   │
                           │   │
                    ┌──────▼─┐ │
                    │ FAILED │ │
                    │(błąd)  │ │
                    └────────┘ │
                               │
                        ┌──────▼─┐
                        │INVALID │
                        │(nie    │
                        │podlega)│
                        └────────┘
```

### 9.7 Znaczenie stanów terminalnych

W modelu EventOutcome stany **COMPLETE**, **FAILED** oraz **INVALID** są stanami terminalnymi, co oznacza zakończenie cyklu życia konkretnej instancji modelu.

Terminacja dotyczy wyłącznie bieżącej instancji EventOutcome i nie stanowi ograniczenia dla przyszłego rozwoju architektury systemu.

Jeżeli w kolejnych wersjach ALCHEMIKA zostanie wprowadzony mechanizm ponownego przeliczenia wyników (np. po zmianie algorytmów, korekcie danych historycznych lub świadomym uruchomieniu procesu rekalkulacji), decyzja ta może zostać zrealizowana poprzez utworzenie nowej instancji EventOutcome lub inny mechanizm wersjonowania przewidziany przez przyszłą architekturę.

Model zaprojektowany w KROKU 3B nie definiuje takiego mechanizmu. Na obecnym etapie zakończenie cyklu życia oznacza brak dalszych zmian w istniejącej instancji.

---

## 10. TABELA PRZEJŚĆ STANÓW

| Ze stanu | Do stanu | Dozwolone | Warunek |
|----------|----------|:---------:|---------|
| PENDING | PARTIAL | ✅ TAK | Pierwszy horyzont pomyślnie wyliczony |
| PENDING | FAILED | ✅ TAK | Błąd techniczny uniemożliwiający pobranie danych |
| PENDING | INVALID | ✅ TAK | Zdarzenie nie podlega analizie rezultatu (ustalone przy tworzeniu) |
| PENDING | COMPLETE | ❌ NIE | Nie można pominąć stanu PARTIAL |
| PARTIAL | PARTIAL | ✅ TAK | Aktualizacja — kolejne horyzonty wyliczone (stan bez zmian) |
| PARTIAL | COMPLETE | ✅ TAK | Wszystkie oczekiwane horyzonty wyliczone |
| PARTIAL | FAILED | ✅ TAK | Błąd techniczny dla pozostałych horyzontów |
| PARTIAL | PENDING | ❌ NIE | Nie można cofnąć postępu |
| PARTIAL | INVALID | ❌ NIE | Decyzja o INVALID zapada przed rozpoczęciem obliczeń |
| COMPLETE | jakikolwiek | ❌ NIE | COMPLETE jest stanem końcowym |
| FAILED | jakikolwiek | ❌ NIE | FAILED jest stanem końcowym (wersja 1.0) |
| INVALID | jakikolwiek | ❌ NIE | INVALID jest stanem końcowym |

---

## 11. STOPNIOWE UZUPEŁNIANIE

### 11.1 Zasada stopniowego uzupełniania

EventOutcome jest uzupełniany stopniowo w miarę upływu czasu i dostępności danych rynkowych dla kolejnych horyzontów sesyjnych. Nie tworzy się nowego EventOutcome dla każdego horyzontu — jeden obiekt jest aktualizowany.

### 11.2 Co oznacza częściowa kompletność

Stan PARTIAL oznacza, że:
- Co najmniej jeden horyzont został pomyślnie wyliczony
- Istnieją horyzonty, dla których dane jeszcze nie są dostępne (np. +5 sesji wymaga upływu 5 dni handlowych)
- Model przechowuje informację, które horyzonty są już gotowe, a które oczekują

### 11.3 Kiedy wynik staje się kompletny

Wynik staje się COMPLETE, gdy liczba wyliczonych horyzontów osiągnie oczekiwaną liczbę. Konkretny moment zależy od kalendarza sesji dla danego rynku i najdłuższego wymaganego horyzontu.

### 11.4 Traktowanie przerw giełdowych i dni bez sesji

- Weekendy i święta giełdowe NIE są liczone jako sesje
- Horyzont +N oznacza +N **sesji handlowych**, nie dni kalendarzowych
- Kalendarz sesji jest specyficzny dla rynku (GPW, NYSE, NASDAQ mają różne dni świąteczne)
- Jeśli po upływie czasu rzeczywistego nie upłynęła wymagana liczba sesji — EventOutcome pozostaje w PARTIAL

### 11.5 Reakcja na czasowo niedostępne dane

- Jeśli dane dla danego horyzontu są czasowo niedostępne (np. opóźnienie w API), komponent obliczeniowy może ponowić próbę w kolejnym cyklu
- EventOutcome pozostaje w PARTIAL — timestamp ostatniej próby jest aktualizowany
- Nie przechodzi się do FAILED z powodu pojedynczego, przejściowego błędu

### 11.6 Kiedy błąd jest przejściowy, a kiedy trwały

| Rodzaj błędu | Klasyfikacja | Zachowanie |
|--------------|-------------|------------|
| Timeout API | Przejściowy | Ponowienie w kolejnym cyklu |
| Brak danych dla ostatniej sesji (jeszcze nieopublikowane) | Przejściowy | Oczekiwanie, PARTIAL |
| Brak danych dla sesji, która już powinna być dostępna (> 2 dni opóźnienia) | Trwały | FAILED |
| Wycofanie instrumentu z obrotu | Trwały | FAILED |
| Zawieszenie notowań | Trwały | FAILED |
| Brak tickera w źródle danych | Trwały | FAILED |

---

## 12. KOMPLETNOŚĆ I JAKOŚĆ DANYCH

### 12.1 Sposób reprezentowania postępu

| Aspekt | Reprezentacja |
|--------|--------------|
| **Liczba oczekiwanych horyzontów** | Wartość liczbowa ustalana przy tworzeniu EventOutcome na podstawie konfiguracji systemu. Nie zmienia się |
| **Liczba wyliczonych horyzontów** | Wartość liczbowa aktualizowana przy każdym pomyślnym wyliczeniu horyzontu. Rośnie monotonicznie od 0 do oczekiwanej liczby |
| **Informacja o brakujących horyzontach** | Zbiorcze wskazanie identyfikatorów horyzontów, dla których brakuje danych. Nie zawiera szczegółowych metryk |
| **Stan cyklu życia** | PENDING (0), PARTIAL (część), COMPLETE (wszystkie) |

### 12.2 Rozróżnienie przyczyn braku wyniku

| Typ braku | Stan EventOutcome | Opis |
|-----------|-------------------|------|
| **Dane jeszcze niedostępne** | PENDING lub PARTIAL | Horyzont czasowy jeszcze nie upłynął. Oczekiwanie |
| **Brak danych** (instrument wycofany, brak notowań) | FAILED | Trwały brak możliwości pobrania danych |
| **Błąd techniczny** (API, sieć) | FAILED (po wyczerpaniu ponowień) | Problem infrastrukturalny |
| **Wynik nieważny domenowo** | INVALID | Zdarzenie nie podlega analizie rezultatu |
| **Zakończone obliczenie** | COMPLETE | Wszystkie horyzonty wyliczone |

### 12.3 Metadane dla reprodukowalności

| Element | Cel |
|---------|-----|
| Wersja reguł obliczeniowych | Jeśli reguły obliczeniowe zmienią się w przyszłości, można określić, która wersja wyprodukowała dany wynik |
| Identyfikator źródła danych | Wskazanie, z którego API pochodzą dane (np. Yahoo Finance) |
| Timestampy prób i aktualizacji | Śledzenie historii obliczeń |

---

## 13. GRANICA WZGLĘDEM SessionOutcome

### 13.1 Zasada podziału

| Poziom | Model | Odpowiedzialność |
|--------|-------|-----------------|
| **Zdarzenie** | EventOutcome | Wynik całego zdarzenia. Informacje zbiorcze o kompletności i postępie wyliczeń |
| **Horyzont sesyjny** | SessionOutcome (przyszły) | Wynik dla konkretnego horyzontu. Szczegółowe metryki (+1, +2, +3, +5) |

### 13.2 Co należy do EventOutcome (poziom zdarzenia)

- Identyfikacja wyniku i powiązanie z MarketEvent
- Stan cyklu życia (PENDING → PARTIAL → COMPLETE / FAILED / INVALID)
- Wartości bazowe (cena, wolumen, timestamp z momentu wykrycia)
- Liczba oczekiwanych horyzontów
- Liczba wyliczonych horyzontów
- Zbiorcza informacja o brakujących horyzontach (identyfikatory, nie szczegóły)
- Informacje o błędach ogólnych (dotyczących całego wyniku)
- Metadane obliczeń (timestampy, wersja reguł)

### 13.3 Co zostało świadomie odłożone do przyszłego modelu SessionOutcome

- Cena zamknięcia dla konkretnej sesji (+1, +2, +3, +5)
- Procentowa zmiana ceny dla konkretnego horyzontu
- Maksymalny/minimalny ruch w konkretnym horyzoncie
- Wolumen konkretnej przyszłej sesji
- Status pojedynczego horyzontu (np. "+2: PENDING")
- Błąd dotyczący pojedynczego horyzontu
- Kierunek trendu w momencie konkretnej sesji
- Pełne OHLCV dla przyszłej sesji

### 13.4 Jak uniknąć podwójnego źródła prawdy

- EventOutcome przechowuje wyłącznie dane zbiorcze o kompletności
- SessionOutcome będzie przechowywał szczegóły per-horyzont
- Żadna informacja nie będzie przechowywana w obu modelach jednocześnie
- Współpraca między modelami zostanie zaprojektowana po powstaniu obu modeli (KROK 3C)
- Na obecnym etapie EventOutcome NIE tworzy zależności architektonicznej od SessionOutcome

---

## 14. NIEZMIENNIKI DOMENOWE

Niezmienniki to reguły, które muszą być spełnione zawsze, niezależnie od wersji systemu, konfiguracji czy rozszerzeń.

### N1. Jeden MarketEvent — najwyżej jeden EventOutcome

Dla jednego MarketEvent może istnieć najwyżej jeden EventOutcome. Relacja 1:1 jest nienaruszalna. Próba utworzenia drugiego EventOutcome dla tego samego MarketEvent jest błędem domenowym.

### N2. EventOutcome nie może istnieć bez wskazania zdarzenia źródłowego

Każdy EventOutcome musi wskazywać dokładnie jeden MarketEvent. Identyfikator źródłowy jest polem wymaganym przy utworzeniu.

### N3. Powiązanie z MarketEvent nie może zostać później zmienione

Identyfikator źródłowego MarketEvent jest ustawiany raz przy utworzeniu EventOutcome i nigdy nie jest modyfikowany. Wynik nie może zostać przepięty do innego zdarzenia.

### N4. Wartości bazowe muszą pochodzić z chwili wykrycia

Wartości bazowe są kontrolowaną kopią danych z MarketEvent. Nie wolno pobierać nowej wartości bazowej z rynku podczas późniejszego obliczania wyniku. Punktem odniesienia jest zawsze moment wykrycia zdarzenia.

### N5. Model nie interpretuje rezultatów

EventOutcome przechowuje wyłącznie obiektywnie wyliczone wartości liczbowe i statusy operacyjne. Nie zawiera ocen, interpretacji, rekomendacji ani prognoz.

### N6. Model nie przechowuje decyzji AI, Risk ani Ranking

EventOutcome jest źródłem danych dla tych komponentów — nie przechowuje ich wyników. AI, Risk i Ranking tworzą własne modele wynikowe.

### N7. Aktualizacje nie mogą usuwać wcześniej poprawnie wyliczonych faktów

Dodanie nowego horyzontu jest operacją addytywną. Wartości już wyliczone nie są modyfikowane. Jeśli zachodzi konieczność korekty (np. korekta danych rynkowych), musi ona posiadać możliwą do audytu przyczynę.

### N8. COMPLETE oznacza spełnienie warunku kompletności

Stan COMPLETE jest osiągany wyłącznie wtedy, gdy liczba wyliczonych horyzontów jest równa oczekiwanej liczbie horyzontów. Nie można oznaczyć wyniku jako COMPLETE przedwcześnie.

### N9. FAILED i INVALID muszą posiadać możliwą do audytu przyczynę

Każdy EventOutcome w stanie FAILED lub INVALID zawiera przyczynę (odpowiednio techniczną lub domenową). Stan bez przyczyny jest niedozwolony.

### N10. Dane sesyjne nie mogą mieć dwóch niezależnych źródeł prawdy

Szczegółowe dane per-horyzont będą przechowywane wyłącznie w SessionOutcome. EventOutcome nie duplikuje tych danych — zawiera wyłącznie informacje zbiorcze.

### N11. Ponowne wykonanie tych samych obliczeń na tych samych danych powinno być idempotentne

Przy tych samych wartościach bazowych i tych samych danych rynkowych, wynik obliczeń musi być identyczny. Reprodukowalność jest gwarantowana przez wersję reguł i identyfikator źródła danych.

### N12. Historia wyniku musi być reprodukowalna

Mając EventOutcome (z wartościami bazowymi, metadanymi i identyfikatorem źródła danych) można odtworzyć wynik obliczeń.

### N13. Cykl życia EventOutcome jest niezależny od cyklu życia MarketEvent

EventOutcome ma własny cykl życia. MarketEvent może być zarchiwizowany przed osiągnięciem przez EventOutcome stanu COMPLETE. Stany obu modeli nie są ze sobą sprzężone.

### N14. Liczba wyliczonych horyzontów rośnie monotonicznie

Wartość nie może się zmniejszyć. Każda aktualizacja może jedynie zwiększyć licznik (lub pozostawić bez zmian w przypadku błędu). Nie można „odwyliczyć" horyzontu.

---

## 15. PRZYPADKI BRZEGOWE

### 15.1 Brak danych po jednej sesji

**Scenariusz:** Zdarzenie wykryte, minęła 1 sesja, ale dane OHLCV dla tej sesji nie są jeszcze dostępne.

**Oczekiwane zachowanie:** EventOutcome pozostaje w PENDING. Timestamp ostatniej próby jest aktualizowany. Komponent obliczeniowy ponawia próbę w kolejnym cyklu. Nie przechodzi do FAILED — to normalna sytuacja (dane mogą być publikowane z opóźnieniem).

### 15.2 Zawieszenie notowań

**Scenariusz:** Instrument został zawieszony po wykryciu zdarzenia. Nie ma przyszłych sesji.

**Oczekiwane zachowanie:** Jeśli EventOutcome jest w PENDING → FAILED z przyczyną `trading_suspended`. Jeśli w PARTIAL → FAILED (nie można dokończyć). Przyczyna jest możliwa do audytu.

### 15.3 Wycofanie instrumentu z obrotu

**Scenariusz:** Instrument został wycofany z obrotu (delisting) po wykryciu zdarzenia.

**Oczekiwane zachowanie:** FAILED z przyczyną `instrument_delisted`. Brak możliwości pobrania przyszłych danych.

### 15.4 Split lub reverse split

**Scenariusz:** W trakcie okresu analizy (między wykryciem a +5 sesją) instrument przeszedł split.

**Oczekiwane zachowanie:** Ceny pobierane z Yahoo Finance są automatycznie korygowane (adjusted close). Jeśli korekta nie jest dostępna — FAILED z przyczyną `data_inconsistency`. Wartości bazowe pozostają niezmienione.

### 15.5 Dywidenda

**Scenariusz:** W trakcie okresu analizy instrument miał dzień ustalenia prawa do dywidendy (ex-dividend).

**Oczekiwane zachowanie:** Używana jest cena adjusted close (po korekcie o dywidendę). Jeśli Yahoo Finance dostarcza adjusted close — obliczenia są poprawne bez dodatkowej logiki. Jeśli nie — FAILED z przyczyną `unadjusted_corporate_action`.

### 15.6 Zmiana symbolu

**Scenariusz:** Instrument zmienił ticker między wykryciem zdarzenia a horyzontem +5.

**Oczekiwane zachowanie:** Wartości bazowe przechowują oryginalny ticker z momentu wykrycia. Komponent obliczeniowy musi być w stanie obsłużyć mapowanie starego tickera na nowy. Jeśli mapowanie niedostępne — FAILED z przyczyną `ticker_changed`.

### 15.7 Brak wymaganej ceny bazowej

**Scenariusz:** MarketEvent nie zawiera `price_data` lub `price_data.close` jest None.

**Oczekiwane zachowanie:** Jeśli zdarzenie poza tym podlega analizie — FAILED z przyczyną `missing_base_price`. Alternatywnie, jeśli typ zdarzenia z definicji nie ma ceny bazowej — INVALID z odpowiednią przyczyną.

### 15.8 Zduplikowana próba utworzenia EventOutcome

**Scenariusz:** Komponent obliczeniowy próbuje utworzyć drugi EventOutcome dla tego samego MarketEvent.

**Oczekiwane zachowanie:** Naruszenie niezmiennika N1. Operacja jest odrzucana. Drugi EventOutcome nie powstaje. Zdarzenie jest logowane.

### 15.9 Ponowienie po błędzie technicznym

**Scenariusz:** EventOutcome w stanie PARTIAL. Próba pobrania danych dla horyzontu +3 kończy się timeoutem API.

**Oczekiwane zachowanie:** Timestamp ostatniej próby jest aktualizowany. Stan pozostaje PARTIAL. Komponent obliczeniowy ponawia próbę w kolejnym cyklu. FAILED tylko po przekroczeniu limitu ponowień lub stwierdzeniu trwałego błędu.

### 15.10 Częściowo wyliczony wynik

**Scenariusz:** Horyzonty +1 i +2 wyliczone, +3 i +5 oczekują. EventOutcome jest w PARTIAL.

**Oczekiwane zachowanie:** Model przechowuje liczbę wyliczonych = 2, oczekiwanych = 4. Informacja o brakujących horyzontach wskazuje +3 i +5. AI, Risk i Ranking mogą już częściowo korzystać z dostępnych danych (decyzja tych komponentów, nie EventOutcome).

### 15.11 Korekta danych rynkowych

**Scenariusz:** Yahoo Finance publikuje skorygowane dane dla sesji, która już została użyta do obliczeń.

**Oczekiwane zachowanie:** Wartości już wyliczone nie są automatycznie nadpisywane (N7). Jeśli korekta jest istotna — może zostać wprowadzona jako jawna operacja korekty z możliwą do audytu przyczyną. Decyzja o dopuszczeniu korekt należy do przyszłego projektu komponentu obliczeniowego.

### 15.12 Niezgodność kalendarza sesyjnego

**Scenariusz:** Rynek, dla którego pobierane są dane, ma inny kalendarz niż zakładano (np. nieoczekiwane święto).

**Oczekiwane zachowanie:** Komponent obliczeniowy używa rzeczywistego kalendarza sesji dla danego rynku. Horyzonty są liczone w sesjach handlowych, nie dniach kalendarzowych.

### 15.13 Zdarzenie wykryte poza sesją

**Scenariusz:** MarketEvent ma timestamp z weekendu lub po godzinach handlu.

**Oczekiwane zachowanie:** Timestamp wykrycia jest przechowywany bez zmian. Horyzont +1 oznacza pierwszą sesję handlową po tym timestampie. Model nie koryguje timestampu — to odpowiedzialność komponentu obliczeniowego.

### 15.14 Instrument bez wymaganej liczby przyszłych sesji

**Scenariusz:** Instrument ma tylko 3 przyszłe sesje handlowe przed wycofaniem, ale oczekiwane są 4 horyzonty.

**Oczekiwane zachowanie:** Stan PARTIAL dla wyliczonych horyzontów, następnie FAILED z przyczyną `insufficient_future_sessions`. Nie można osiągnąć COMPLETE.

---

## 16. OTWARTE DECYZJE

Nie pozostawiono otwartych kwestii architektonicznych w zakresie modelu EventOutcome.

Wszystkie decyzje wymagane w KROKU 3B zostały rozstrzygnięte:
- Odpowiedzialność modelu — określona
- Relacja 1:1 z MarketEvent — zdefiniowana
- Struktura logiczna — kompletna (17 elementów w 6 grupach)
- Wartości bazowe — kontrolowana kopia
- Cykl życia — 5 stanów z tabelą przejść
- Zasady stopniowego uzupełniania — określone
- Granica z SessionOutcome — jednoznaczna
- Niezmienniki — 14 zasad
- Przypadki brzegowe — 14 scenariuszy

Kwestie świadomie odłożone do kolejnych kroków:
- Projekt SessionOutcome → KROK 3C
- Projekt komponentu obliczeniowego → KROK 3D
- Konkretne reguły biznesowe dla INVALID → projekt logiki biznesowej
- Integracja z API i bazą danych → KROK 3E

---

## KONIEC DOKUMENTU

Data utworzenia: 30.07.2026
Wersja: 1.0
Status: Dokument projektowy — model domenowy EventOutcome

Dokumenty powiązane:
- `docs/FILOZOFIA_EVENTOUTCOME.md` — filozofia odpowiedzialności EventOutcome
- `docs/MODEL_SESSIONOUTCOME.md` — projekt domenowy SessionOutcome (wynik pojedynczego horyzontu)
- `docs/FILOZOFIA_ALCHEMIKA.md` — filozofia działania systemu
- `docs/Kontrakt_Zdarzen_Rynkowych.md` — kontrakt MarketEvent
- `docs/Przeplyw_Zdarzen_Rynkowych.md` — cykl życia MarketEvent