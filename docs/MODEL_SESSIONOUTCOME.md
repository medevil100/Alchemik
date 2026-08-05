# ALCHEMIK — MODEL DOMENOWY SessionOutcome

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
5. [Tożsamość i relacje](#5-tożsamość-i-relacje)
6. [Struktura logiczna](#6-struktura-logiczna)
7. [Źródła danych](#7-źródła-danych)
8. [Wartości bazowe](#8-wartości-bazowe)
9. [Cykl życia](#9-cykl-życia)
10. [Tabela przejść stanów](#10-tabela-przejść-stanów)
11. [Kompletność danych](#11-kompletność-danych)
12. [Granica względem EventOutcome](#12-granica-względem-eventoutcome)
13. [Niezmienniki domenowe](#13-niezmienniki-domenowe)
14. [Przypadki brzegowe](#14-przypadki-brzegowe)
15. [Otwarte decyzje](#15-otwarte-decyzje)

---

## 1. CEL MODELU

SessionOutcome jest modelem domenowym reprezentującym **wynik pojedynczego horyzontu sesyjnego** należącego do jednego EventOutcome.

Model odpowiada na pytanie:

> **Jak zachował się rynek w konkretnym horyzoncie po zdarzeniu?**

SessionOutcome przechowuje szczegółowe, obiektywnie wyliczone metryki dla jednej przyszłej sesji handlowej. Jest modelem per-horyzont — dla jednego EventOutcome może istnieć wiele instancji SessionOutcome (po jednej na każdy horyzont).

Dokument definiuje odpowiedzialność, strukturę logiczną, cykl życia, niezmienniki i granice modelu. Nie definiuje implementacji, bazy danych, API ani klas.

---

## 2. KONTEKST DOMENOWY

### 2.1 Miejsce w architekturze

```
MarketEvent ─── 1:1 ──→ EventOutcome ─── 1:N ──→ SessionOutcome
(chwila                    (rezultat                (wynik pojedynczego
 wykrycia)                  całego zdarzenia)        horyzontu sesyjnego)

SessionOutcome(+1)   SessionOutcome(+2)   SessionOutcome(+3)   SessionOutcome(+5)
```

### 2.2 Relacja z innymi elementami architektury

| Element | Relacja z SessionOutcome |
|---------|------------------------|
| **EventOutcome** | Kontener nadrzędny. Jeden EventOutcome posiada wiele SessionOutcome. SessionOutcome wskazuje swój EventOutcome przez `event_outcome_id` |
| **MarketEvent** | Relacja pośrednia przez EventOutcome. SessionOutcome nie zna bezpośrednio MarketEvent |
| **Komponent obliczeniowy** (przyszły) | Tworzy i aktualizuje SessionOutcome. Pobiera dane rynkowe dla konkretnego horyzontu |
| **AI** | Konsumuje dane z SessionOutcome przez EventOutcome. Nie ma bezpośredniej zależności od SessionOutcome |
| **Risk** | Wykorzystuje dane z SessionOutcome przez EventOutcome |
| **Ranking** | Wykorzystuje dane z SessionOutcome przez EventOutcome |

### 2.3 Dokumenty nadrzędne

Model jest zgodny z:
- `docs/FILOZOFIA_EVENTOUTCOME.md` — filozofia odpowiedzialności EventOutcome i podziału na horyzonty
- `docs/MODEL_EVENTOUTCOME.md` — projekt domenowy EventOutcome, definiuje granicę obu modeli
- `docs/FILOZOFIA_ALCHEMIKA.md` — filozofia działania systemu
- `docs/Kontrakt_Zdarzen_Rynkowych.md` — kontrakt MarketEvent

W przypadku sprzeczności, dokumenty nadrzędne mają pierwszeństwo.

---

## 3. ODPOWIEDZIALNOŚĆ MODELU

### 3.1 Co SessionOutcome reprezentuje

SessionOutcome reprezentuje **obiektywny, wyliczony rezultat dla pojedynczego horyzontu sesyjnego**. Jest kontenerem faktów — nie interpretacji, nie prognoz, nie ocen.

### 3.2 Za jakie dane odpowiada

- **Tożsamość wyniku sesyjnego** — jednoznaczna identyfikacja w systemie
- **Powiązanie z EventOutcome** — niezmienne wskazanie nadrzędnego wyniku zdarzenia
- **Identyfikator horyzontu** — który horyzont (+1, +2, +3, +5) reprezentuje
- **Stan cyklu życia** — na jakim etapie znajduje się wynik dla tego horyzontu
- **Szczegółowe metryki cenowe** — cena zamknięcia, zmiana procentowa i absolutna dla tego horyzontu
- **Szczegółowe metryki wolumenowe** — wolumen sesji horyzontu, zmiana względem wolumenu bazowego
- **Metryki wewnątrz-horyzontalne** — maksymalna i minimalna cena osiągnięta podczas sesji horyzontu
- **Informacje o błędach** — przyczyna niepowodzenia dla tego konkretnego horyzontu
- **Metadane obliczeń** — timestamp obliczenia, wersja reguł

### 3.3 Czego nie może zawierać

SessionOutcome **nie** przechowuje:

- decyzji inwestycyjnej,
- rekomendacji AI (BUY/SELL/HOLD),
- oceny ryzyka (risk_score, risk_level),
- pozycji rankingowej,
- narracyjnej interpretacji rezultatu,
- wartości bazowych z MarketEvent (te należą do EventOutcome),
- informacji zbiorczych o kompletności wszystkich horyzontów (to EventOutcome),
- danych innych horyzontów — każdy SessionOutcome dotyczy dokładnie jednego horyzontu,
- danych OHLCV dla sesji innych niż horyzont, którego dotyczy.

### 3.4 Czym różni się od EventOutcome

| Aspekt | EventOutcome | SessionOutcome |
|--------|-------------|----------------|
| **Poziom** | Całe zdarzenie | Pojedynczy horyzont sesyjny |
| **Liczność** | 1 na MarketEvent | wiele na EventOutcome (po jednym na horyzont) |
| **Dane** | Zbiorcze: kompletność, postęp, stan ogólny | Szczegółowe: cena, zmiana %, wolumen dla konkretnej sesji |
| **Wartości bazowe** | Przechowuje kopię z MarketEvent | Nie przechowuje — odwołuje się do EventOutcome |
| **Agregacja** | Agreguje postęp wszystkich horyzontów | Nie agreguje — dotyczy jednego horyzontu |

### 3.5 Czym różni się od MarketEvent

SessionOutcome nie ma bezpośredniej relacji z MarketEvent. Korzysta z wartości bazowych przechowywanych w EventOutcome. MarketEvent opisuje chwilę wykrycia — SessionOutcome opisuje stan rynku w konkretnej przyszłej sesji.

---

## 4. GRANICE ODPOWIEDZIALNOŚCI

### 4.1 Tabela granic

| Element | Odpowiedzialność | Czego nie przechowuje ani nie oblicza |
|---------|-----------------|--------------------------------------|
| **MarketEvent** | Zapisuje stan rynku w chwili wykrycia | Nie przechowuje wyników dla horyzontów |
| **EventOutcome** | Opisuje rezultat całego zdarzenia. Przechowuje wartości bazowe i informacje zbiorcze | Nie przechowuje szczegółowych metryk per-horyzont |
| **SessionOutcome** | Opisuje wynik pojedynczego horyzontu sesyjnego. Przechowuje szczegółowe metryki dla konkretnej sesji | Nie przechowuje wartości bazowych. Nie agreguje wielu horyzontów. Nie interpretuje |
| **Komponent obliczeniowy** (przyszły) | Oblicza fakty: pobiera dane rynkowe, wylicza metryki per-horyzont, ustawia statusy | Nie interpretuje wyników. Nie modyfikuje MarketEvent ani EventOutcome (poza aktualizacją liczników) |
| **AI** | Interpretuje dane przez EventOutcome | Nie oblicza metryk per-horyzont |
| **Risk** | Ocenia ryzyko na podstawie danych z EventOutcome | Nie oblicza metryk per-horyzont |
| **Ranking** | Porządkuje sygnały na podstawie danych z EventOutcome | Nie oblicza metryk per-horyzont |

---

## 5. TOŻSAMOŚĆ I RELACJE

### 5.1 Rozstrzygnięcie architektoniczne

**SessionOutcome posiada własną tożsamość domenową ORAZ przechowuje identyfikator nadrzędnego EventOutcome.**

Decyzja opiera się na przesłankach:

1. **Niezależny cykl życia per-horyzont** — każdy horyzont może osiągnąć swój stan w innym momencie. Własna tożsamość odzwierciedla tę niezależność.

2. **Relacja N:1 z EventOutcome** — wiele SessionOutcome należy do jednego EventOutcome. Każdy SessionOutcome wskazuje swój EventOutcome przez identyfikator.

3. **Zabezpieczenie przed przepięciem** — identyfikator EventOutcome jest ustawiany raz i nigdy nie jest zmieniany.

4. **Brak bezpośredniej relacji z MarketEvent** — SessionOutcome nie przechowuje `market_event_id`. Wartości bazowe (cena, wolumen, timestamp wykrycia) są pobierane z EventOutcome, nie z MarketEvent.

### 5.2 Reguły liczności

- Jeden EventOutcome może posiadać **wiele** SessionOutcome (jeden na każdy horyzont).
- Jeden SessionOutcome należy do **dokładnie jednego** EventOutcome.
- Kombinacja (`event_outcome_id`, `horizon_id`) jest unikalna — nie mogą istnieć dwa SessionOutcome dla tego samego horyzontu tego samego EventOutcome.
- SessionOutcome nie może istnieć bez wskazania EventOutcome.

### 5.3 Tożsamość domenowa

| Element | Opis |
|---------|------|
| **Identyfikator własny** | Unikalny identyfikator SessionOutcome. Generowany przy utworzeniu |
| **Identyfikator EventOutcome** | `EventOutcome.event_outcome_id` — niezmienne wskazanie nadrzędnego wyniku |
| **Identyfikator horyzontu** | Który horyzont sesyjny reprezentuje (np. `+1`, `+2`, `+3`, `+5`) |
| **Unikalność** | Para (`event_outcome_id`, `horizon_id`) jest unikalna w systemie |

### 5.4 Horyzonty sesyjne

| Horyzont | Znaczenie |
|----------|----------|
| `+1` | Pierwsza sesja handlowa po wykryciu zdarzenia |
| `+2` | Druga sesja handlowa po wykryciu zdarzenia |
| `+3` | Trzecia sesja handlowa po wykryciu zdarzenia |
| `+5` | Piąta sesja handlowa po wykryciu zdarzenia |

Horyzonty są liczone w **sesjach handlowych**, nie dniach kalendarzowych. Kalendarz sesji zależy od rynku notowań instrumentu (przechowywanego w EventOutcome).

---

## 6. STRUKTURA LOGICZNA

| # | Grupa | Element | Znaczenie domenowe | Wymagalność | Źródło danych | Kto uzupełnia | Czy może się zmienić |
|---|-------|---------|-------------------|-------------|---------------|---------------|---------------------|
| **Identyfikacja** |
| 1 | Identyfikacja | Identyfikator własny SessionOutcome | Unikalny identyfikator wyniku horyzontu w systemie | Zawsze | Generowany przy utworzeniu | Komponent obliczeniowy | NIE |
| 2 | Identyfikacja | Identyfikator nadrzędnego EventOutcome | Niezmienne powiązanie z EventOutcome | Zawsze | EventOutcome | Komponent obliczeniowy | NIE (ustawiany raz) |
| 3 | Identyfikacja | Identyfikator horyzontu | Który horyzont sesyjny reprezentuje: +1, +2, +3, +5 | Zawsze | Ustalany przy tworzeniu na podstawie konfiguracji | Komponent obliczeniowy | NIE (ustawiany raz) |
| **Stan cyklu życia** |
| 4 | Stan | Stan cyklu życia | Aktualny stan wyniku horyzontu: PENDING, CALCULATED, FAILED, SKIPPED | Zawsze | Ustalany przy utworzeniu, aktualizowany | Komponent obliczeniowy | TAK (według reguł przejść) |
| **Metryki cenowe** |
| 5 | Metryki | Cena zamknięcia w horyzoncie | Cena close instrumentu w sesji horyzontu. Podstawa do obliczeń zmiany | Warunkowo (gdy stan = CALCULATED) | Dane rynkowe (Yahoo Finance) | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| 6 | Metryki | Zmiana ceny — procentowa | (cena_horyzontu - cena_bazowa) / cena_bazowa × 100%. Wyrażona jako wartość procentowa | Warunkowo (gdy stan = CALCULATED) | Obliczane na podstawie ceny bazowej z EventOutcome i ceny horyzontu | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| 7 | Metryki | Zmiana ceny — absolutna | cena_horyzontu - cena_bazowa. Wyrażona w jednostkach waluty | Warunkowo (gdy stan = CALCULATED) | Obliczane | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| **Metryki wolumenowe** |
| 8 | Metryki | Wolumen w horyzoncie | Wolumen sesji horyzontu | Warunkowo (gdy stan = CALCULATED i dane dostępne) | Dane rynkowe (Yahoo Finance) | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| 9 | Metryki | Zmiana wolumenu — procentowa | (wolumen_horyzontu - wolumen_bazowy) / wolumen_bazowy × 100%. Względem wolumenu bazowego z EventOutcome | Warunkowo (gdy stan = CALCULATED i wolumen bazowy dostępny) | Obliczane | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| **Metryki wewnątrz-horyzontalne** |
| 10 | Metryki | Maksymalna cena w horyzoncie | Najwyższa cena (high) osiągnięta podczas sesji horyzontu | Warunkowo (gdy stan = CALCULATED) | Dane rynkowe (Yahoo Finance) | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| 11 | Metryki | Minimalna cena w horyzoncie | Najniższa cena (low) osiągnięta podczas sesji horyzontu | Warunkowo (gdy stan = CALCULATED) | Dane rynkowe (Yahoo Finance) | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| **Błędy** |
| 12 | Błędy | Przyczyna stanu FAILED | Techniczna przyczyna niepowodzenia dla tego horyzontu: błąd połączenia, brak danych, timeout. Możliwa do audytu | Warunkowo (gdy stan = FAILED) | Komponent obliczeniowy | Komponent obliczeniowy | NIE (po przejściu w FAILED) |
| 13 | Błędy | Przyczyna stanu SKIPPED | Dlaczego horyzont został pominięty. Możliwa do audytu przyczyna domenowa. Szczegółowe reguły kwalifikacji są definiowane poza modelem domenowym | Warunkowo (gdy stan = SKIPPED) | Komponent obliczeniowy | Komponent obliczeniowy | NIE (po przejściu w SKIPPED) |
| **Metadane obliczeń** |
| 14 | Metadane | Timestamp obliczenia | Kiedy horyzont został pomyślnie przeliczony | Warunkowo (gdy stan = CALCULATED) | Ustawiany przy wyliczeniu | Komponent obliczeniowy | NIE (ustawiany raz) |
| 15 | Metadane | Wersja reguł obliczeniowych | Identyfikator wersji reguł użytych do obliczeń. Do audytu i reprodukowalności | Warunkowo (gdy stan = CALCULATED) | Konfiguracja komponentu obliczeniowego | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |
| 16 | Metadane | Identyfikator źródła danych | Źródło danych rynkowych (np. Yahoo Finance). Do audytu | Warunkowo (gdy stan = CALCULATED) | Konfiguracja komponentu obliczeniowego | Komponent obliczeniowy | NIE (zamrożona po wyliczeniu) |

---

## 7. ŹRÓDŁA DANYCH

### 7.1 Dane pochodzące z EventOutcome (referencja, nie kopia)

| Dane | Element w EventOutcome | Sposób użycia |
|------|----------------------|---------------|
| Identyfikator EventOutcome | Identyfikator własny EventOutcome | Powiązanie nadrzędne |
| Cena bazowa | Cena bazowa | Punkt odniesienia do obliczeń zmiany ceny |
| Wolumen bazowy | Wolumen bazowy | Punkt odniesienia do obliczeń zmiany wolumenu |
| Symbol instrumentu | Symbol instrumentu | Identyfikacja do pobrania danych |
| Rynek notowań | Rynek notowań | Określenie kalendarza sesji |

### 7.2 Dane pochodzące z rynku (pobierane przez komponent obliczeniowy)

| Dane | Źródło | Sposób użycia |
|------|--------|---------------|
| Cena open sesji horyzontu | HunterEngine / YahooFetcher | Obliczenie kierunku ruchu |
| Cena high sesji horyzontu | HunterEngine / YahooFetcher | Maksymalna cena w horyzoncie |
| Cena low sesji horyzontu | HunterEngine / YahooFetcher | Minimalna cena w horyzoncie |
| Cena close sesji horyzontu | HunterEngine / YahooFetcher | Podstawa obliczeń zmiany |
| Wolumen sesji horyzontu | HunterEngine / YahooFetcher | Podstawa analizy wolumenu |

---

## 8. WARTOŚCI BAZOWE

### 8.1 Rozstrzygnięcie architektoniczne

**SessionOutcome NIE przechowuje własnej kopii wartości bazowych. Korzysta z wartości bazowych przechowywanych w EventOutcome.**

### 8.2 Uzasadnienie

Wartości bazowe (cena zamknięcia, wolumen, timestamp wykrycia) są już przechowywane jako kontrolowana kopia w EventOutcome. Duplikowanie ich w każdym SessionOutcome byłoby naruszeniem zasady jednego źródła prawdy (N10 w MODEL_EVENTOUTCOME.md) i prowadziłoby do redundancji.

SessionOutcome przechowuje:
- **Metryki horyzontu** — dane z konkretnej przyszłej sesji (cena, wolumen, high, low)
- **Metryki pochodne** — zmiana procentowa i absolutna obliczone na podstawie wartości bazowych z EventOutcome

Przy obliczaniu metryk pochodnych komponent obliczeniowy odczytuje wartości bazowe z EventOutcome, wykonuje obliczenia i zapisuje wyniki w SessionOutcome. Wartości bazowe nie są kopiowane.

### 8.3 Zasada

> SessionOutcome nie duplikuje wartości bazowych. Korzysta z wartości przechowywanych w EventOutcome. Obliczenia zmiany (procentowej i absolutnej) są wykonywane na podstawie tych wartości, a wyniki są przechowywane w SessionOutcome.

---

## 9. CYKL ŻYCIA

Cykl życia SessionOutcome jest **niezależny per horyzont**. Każdy SessionOutcome ma własny cykl — jeden horyzont może być już CALCULATED, podczas gdy inny wciąż PENDING.

### 9.1 Stan PENDING

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | SessionOutcome utworzony. Oczekuje na dane rynkowe dla swojego horyzontu. Horyzont jeszcze nie został osiągnięty lub dane nie są jeszcze dostępne |
| **Warunki wejścia** | Utworzenie SessionOutcome wraz z utworzeniem EventOutcome (dla każdego skonfigurowanego horyzontu) |
| **Możliwe przejścia** | → CALCULATED (dane pobrane, metryki wyliczone) |
| | → FAILED (błąd techniczny przy próbie pobrania danych) |
| | → SKIPPED (horyzont nie ma zastosowania — np. instrument wycofany przed tą sesją) |
| **Ponowienie** | Tak — komponent obliczeniowy może wielokrotnie próbować pobrać dane dla horyzontu |

### 9.2 Stan CALCULATED

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | Dane rynkowe dla horyzontu zostały pobrane, wszystkie metryki zostały pomyślnie wyliczone |
| **Warunki wejścia** | Udało się pobrać dane OHLCV dla sesji horyzontu. Wszystkie metryki wyliczone bez błędów. Cena bazowa dostępna w EventOutcome |
| **Możliwe przejścia** | Brak — stan końcowy |
| **Zabronione przejścia** | → PENDING (nie można cofnąć wyliczenia) |
| | → FAILED (nie można uznać za błędny poprawnie wyliczonego horyzontu) |
| **Zawartość** | Wszystkie metryki (cena, zmiana %, zmiana abs, wolumen, high, low) są wypełnione |

### 9.3 Stan FAILED

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | Nie udało się obliczyć metryk dla tego horyzontu z przyczyn technicznych |
| **Warunki wejścia** | Błąd pobrania danych: timeout API, brak danych dla sesji mimo upływu czasu, błąd walidacji danych |
| **Przyczyna** | Zawsze obecna — możliwa do audytu |
| **Możliwe przejścia** | Brak — stan końcowy (wersja 1.0) |
| **Ponowienie** | Wersja 1.0: FAILED jest terminalny. Przyszłe wersje mogą dopuścić ponowienie |

### 9.4 Stan SKIPPED

| Aspekt | Opis |
|--------|------|
| **Znaczenie** | SKIPPED oznacza, że dla danego horyzontu obliczenie nie zostanie wykonane z przyczyn domenowych, które nie są błędem technicznym. Szczegółowe reguły kwalifikacji są definiowane poza modelem domenowym |
| **Warunki wejścia** | Ustalane poza modelem — mogą obejmować sytuacje takie jak wycofanie instrumentu z obrotu, zawieszenie notowań lub niewystarczającą liczbę przyszłych sesji (przykłady niewiążące) |
| **Przyczyna** | Zawsze obecna — możliwa do audytu przyczyna domenowa |
| **Możliwe przejścia** | Brak — stan końcowy |

### 9.5 Diagram przejść

```
                    ┌──────────────┐
                    │   PENDING    │
                    │(oczekiwanie) │
                    └──┬───┬───┬───┘
                       │   │   │
           dane        │   │   │
           pobrane,    │   │   │
           metryki     │   │   │
           wyliczone   │   │   │
                       │   │   │
                    ┌──▼─┐ │   │
                    │CALC│ │   │
                    │ULA │ │   │
                    │TED │ │   │
                    └────┘ │   │
                           │   │
                    ┌──────▼─┐ │
                    │ FAILED │ │
                    │(błąd)  │ │
                    └────────┘ │
                               │
                        ┌──────▼─┐
                        │SKIPPED │
                        │(pominię│
                        │ty)     │
                        └────────┘
```

### 9.6 Znaczenie stanów terminalnych

Stany **CALCULATED**, **FAILED** oraz **SKIPPED** są stanami terminalnymi, co oznacza zakończenie cyklu życia konkretnej instancji SessionOutcome.

Terminacja dotyczy wyłącznie bieżącej instancji i nie stanowi ograniczenia dla przyszłego rozwoju architektury. Mechanizm ponownego przeliczenia może zostać wprowadzony w przyszłych wersjach poprzez utworzenie nowej instancji SessionOutcome lub inny mechanizm wersjonowania.

Model zaprojektowany w KROKU 3C nie definiuje takiego mechanizmu.

---

## 10. TABELA PRZEJŚĆ STANÓW

| Ze stanu | Do stanu | Dozwolone | Warunek |
|----------|----------|:---------:|---------|
| PENDING | CALCULATED | ✅ TAK | Dane pobrane, metryki wyliczone pomyślnie |
| PENDING | FAILED | ✅ TAK | Błąd techniczny uniemożliwiający pobranie danych |
| PENDING | SKIPPED | ✅ TAK | Horyzont nie ma zastosowania (instrument wycofany, zawieszony) |
| CALCULATED | jakikolwiek | ❌ NIE | CALCULATED jest stanem końcowym |
| FAILED | jakikolwiek | ❌ NIE | FAILED jest stanem końcowym (wersja 1.0) |
| SKIPPED | jakikolwiek | ❌ NIE | SKIPPED jest stanem końcowym |

---

## 11. KOMPLETNOŚĆ DANYCH

### 11.1 Kiedy horyzont jest kompletny

Horyzont jest kompletny, gdy osiągnie stan **CALCULATED**. Wszystkie wymagane metryki są wypełnione.

### 11.2 Częściowa dostępność danych

Jeśli dla horyzontu udało się pobrać tylko część danych (np. cenę, ale nie wolumen):

- Jeśli brakujące dane są opcjonalne (np. wolumen) → stan CALCULATED, brakujące pola pozostają puste
- Jeśli brakujące dane są wymagane (np. cena close) → stan FAILED z odpowiednią przyczyną

### 11.3 Rozróżnienie przyczyn braku wyniku

| Typ braku | Stan SessionOutcome | Opis |
|-----------|---------------------|------|
| **Dane jeszcze niedostępne** | PENDING | Horyzont czasowy jeszcze nie upłynął |
| **Błąd pobrania danych** | FAILED | Problem techniczny z API lub źródłem danych |
| **Horyzont nieosiągalny** | SKIPPED | Instrument przestał istnieć przed tym horyzontem |
| **Dane wyliczone** | CALCULATED | Wszystkie metryki dostępne |

---

## 12. GRANICA WZGLĘDEM EventOutcome

### 12.1 Zasada podziału

| Poziom | Model | Odpowiedzialność |
|--------|-------|-----------------|
| **Zdarzenie** | EventOutcome | Wynik całego zdarzenia. Wartości bazowe. Informacje zbiorcze o postępie |
| **Horyzont** | SessionOutcome | Wynik pojedynczego horyzontu. Szczegółowe metryki |

### 12.2 Co należy do SessionOutcome (poziom horyzontu)

- Identyfikacja horyzontu i powiązanie z EventOutcome
- Stan cyklu życia (PENDING → CALCULATED / FAILED / SKIPPED)
- Cena zamknięcia w horyzoncie
- Zmiana ceny (procentowa i absolutna) względem ceny bazowej
- Wolumen w horyzoncie i jego zmiana
- Maksymalna i minimalna cena w horyzoncie
- Przyczyny FAILED i SKIPPED dla tego horyzontu
- Metadane obliczeń (timestamp, wersja reguł, źródło danych)

### 12.3 Co należy do EventOutcome (nie jest duplikowane)

- Wartości bazowe (cena, wolumen, timestamp) — SessionOutcome ich nie kopiuje
- Oczekiwana i wyliczona liczba horyzontów
- Zbiorcza informacja o brakujących horyzontach
- Stan ogólny (PENDING / PARTIAL / COMPLETE / FAILED / INVALID)

### 12.4 Związek między stanami

| Stan EventOutcome | Możliwe stany SessionOutcome | Znaczenie |
|-------------------|------------------------------|-----------|
| PENDING | Wszystkie PENDING | Żaden horyzont jeszcze nie wyliczony |
| PARTIAL | Mieszanka PENDING, CALCULATED, FAILED, SKIPPED | Niektóre horyzonty gotowe, inne oczekują |
| COMPLETE | Wszystkie CALCULATED (lub mieszanka CALCULATED + SKIPPED dla pominiętych) | Wszystkie osiągalne horyzonty wyliczone |
| FAILED | Co najmniej jeden FAILED, pozostałe PENDING/SKIPPED | Ogólny błąd uniemożliwiający kompletność |
| INVALID | Wszystkie SKIPPED (lub brak SessionOutcome) | Zdarzenie nie podlega analizie |

---

## 13. NIEZMIENNIKI DOMENOWE

### N1. Jeden horyzont — jeden SessionOutcome

Dla danego EventOutcome i danego horyzontu może istnieć najwyżej jeden SessionOutcome. Kombinacja (`event_outcome_id`, `horizon_id`) jest unikalna.

### N2. SessionOutcome nie może istnieć bez EventOutcome

Każdy SessionOutcome musi wskazywać dokładnie jeden EventOutcome. Identyfikator nadrzędny jest polem wymaganym przy utworzeniu.

### N3. Powiązanie z EventOutcome nie może zostać zmienione

Identyfikator nadrzędnego EventOutcome jest ustawiany raz i nigdy nie jest modyfikowany. Wynik horyzontu nie może zostać przepięty do innego zdarzenia.

### N4. SessionOutcome nie przechowuje wartości bazowych

Wartości bazowe (cena, wolumen, timestamp wykrycia) są przechowywane wyłącznie w EventOutcome. SessionOutcome odwołuje się do nich przez EventOutcome.

### N5. Model nie interpretuje rezultatów

SessionOutcome przechowuje wyłącznie obiektywnie wyliczone wartości liczbowe i statusy operacyjne. Nie zawiera ocen, interpretacji, rekomendacji ani prognoz.

### N6. Model nie przechowuje decyzji AI, Risk ani Ranking

SessionOutcome jest źródłem danych — nie przechowuje wyników tych komponentów.

### N7. Metryki są zamrożone po wyliczeniu

Po przejściu w stan CALCULATED metryki nie są modyfikowane. Jeśli zachodzi konieczność korekty, wymaga ona utworzenia nowej instancji lub jawnego mechanizmu korekty z możliwą do audytu przyczyną.

### N8. FAILED i SKIPPED muszą posiadać możliwą do audytu przyczynę

Każdy SessionOutcome w stanie FAILED lub SKIPPED zawiera przyczynę. Stan bez przyczyny jest niedozwolony.

### N9. Horyzont dotyczy jednej sesji handlowej

Każdy SessionOutcome reprezentuje dokładnie jedną sesję handlową. Nie agreguje wielu sesji.

### N10. Metryki pochodne są spójne z wartościami bazowymi

Zmiana procentowa i absolutna są obliczane na podstawie wartości bazowych z EventOutcome. Niezależne obliczenie z tych samych danych musi dać identyczny wynik (idempotentność).

---

## 14. PRZYPADKI BRZEGOWE

### 14.1 Horyzont jeszcze nie nadszedł

**Scenariusz:** SessionOutcome dla +5 utworzony, ale minęła dopiero 1 sesja.

**Oczekiwane zachowanie:** Stan PENDING. Komponent obliczeniowy czeka, aż upłynie odpowiednia liczba sesji handlowych.

### 14.2 Brak danych dla pojedynczej sesji

**Scenariusz:** Sesja horyzontu już się odbyła, ale Yahoo Finance nie zwraca danych.

**Oczekiwane zachowanie:** FAILED z przyczyną `no_data_for_session`. Pozostałe horyzonty nie są dotknięte.

### 14.3 Instrument wycofany przed horyzontem

**Scenariusz:** Instrument wycofany po +1 sesji. SessionOutcome dla +2, +3, +5 nie mogą być wyliczone.

**Oczekiwane zachowanie:** +1 → CALCULATED (jeśli dane dostępne). +2, +3, +5 → SKIPPED z przyczyną `instrument_delisted`.

### 14.4 Zawieszenie notowań przed horyzontem

**Scenariusz:** Notowania zawieszone przed osiągnięciem horyzontu +3.

**Oczekiwane zachowanie:** +1, +2 → CALCULATED (jeśli dane dostępne). +3, +5 → SKIPPED z przyczyną `trading_suspended`.

### 14.5 Split w trakcie horyzontu

**Scenariusz:** W sesji horyzontu +2 nastąpił split.

**Oczekiwane zachowanie:** Cena pobierana jako adjusted close. Jeśli adjusted close niedostępne → FAILED z przyczyną `unadjusted_corporate_action`.

### 14.6 Dywidenda w sesji horyzontu

**Scenariusz:** Ex-dividend date wypada w sesji horyzontu.

**Oczekiwane zachowanie:** Używana cena adjusted close. Metryki odzwierciedlają rzeczywistą zmianę wartości po korekcie o dywidendę.

### 14.7 Sesja horyzontu pokrywa się ze świętem

**Scenariusz:** Kalendarz sesji wskazuje, że w dniu, w którym oczekiwano horyzontu, giełda jest zamknięta.

**Oczekiwane zachowanie:** Horyzont przesuwa się na następną sesję handlową. SessionOutcome pozostaje PENDING do czasu rzeczywistej sesji.

### 14.8 Cena bazowa niedostępna w EventOutcome

**Scenariusz:** EventOutcome nie zawiera ceny bazowej (np. została utracona).

**Oczekiwane zachowanie:** FAILED z przyczyną `base_price_unavailable`. Metryki pochodne (zmiana %) nie mogą być obliczone.

### 14.9 Zduplikowana próba utworzenia SessionOutcome

**Scenariusz:** Próba utworzenia drugiego SessionOutcome dla tego samego EventOutcome i tego samego horyzontu.

**Oczekiwane zachowanie:** Naruszenie niezmiennika N1. Operacja odrzucana. Drugi SessionOutcome nie powstaje.

### 14.10 Wolumen bazowy niedostępny

**Scenariusz:** MarketEvent nie zawierał danych wolumenowych, więc EventOutcome nie ma wolumenu bazowego.

**Oczekiwane zachowanie:** Metryki wolumenowe (zmiana wolumenu) pozostają puste. Metryki cenowe są wyliczane normalnie. Stan CALCULATED — wolumen jest opcjonalny.

---

## 15. OTWARTE DECYZJE

Nie pozostawiono otwartych kwestii architektonicznych w zakresie modelu SessionOutcome.

Wszystkie decyzje wymagane w KROKU 3C zostały rozstrzygnięte:
- Odpowiedzialność modelu — określona
- Relacja z EventOutcome — N:1, zdefiniowana
- Relacja z MarketEvent — pośrednia przez EventOutcome, bez bezpośredniego powiązania
- Struktura logiczna — kompletna (16 elementów w 7 grupach)
- Wartości bazowe — referencja do EventOutcome, bez duplikacji
- Cykl życia — 4 stany z tabelą przejść
- Niezmienniki — 10 zasad
- Przypadki brzegowe — 10 scenariuszy

Kwestie świadomie odłożone do kolejnych kroków:
- Projekt komponentu obliczeniowego → KROK 3D
- Integracja z API i bazą danych → KROK 3E

---

## KONIEC DOKUMENTU

Data utworzenia: 30.07.2026
Wersja: 1.0
Status: Dokument projektowy — model domenowy SessionOutcome

Dokumenty powiązane:
- `docs/MODEL_EVENTOUTCOME.md` — projekt domenowy EventOutcome
- `docs/FILOZOFIA_EVENTOUTCOME.md` — filozofia odpowiedzialności modeli wynikowych
- `docs/FILOZOFIA_ALCHEMIKA.md` — filozofia działania systemu
- `docs/Kontrakt_Zdarzen_Rynkowych.md` — kontrakt MarketEvent