# ALCHEMIK — FORMALNY KONTRAKT DANYCH YAHOO CHART

## 1. METRYKA DOKUMENTU

| Atrybut | Wartość |
|---------|---------|
| Tytuł | ALCHEMIK — Formalny kontrakt danych Yahoo chart |
| Status | PROJEKT KONTRAKTU — NIE ZATWIERDZONY PRZEZ WŁAŚCICIELA |
| Rodzaj zadania | wyłącznie dokumentacyjne |
| Data utworzenia | 15.08.2026 |
| Krok | 1/6 |
| Repozytorium | C:\alchemik |
| Gałąź | master |
| HEAD | 8e4edbd5fe26a4ec8b2b4dbf4540614cf906da24 |
| Plik docelowy | docs/ALCHEMIK_KONTRAKT_DANYCH_YAHOO_CHART.md |

Dokument został utworzony wyłącznie na podstawie:

- obowiązkowych materiałów wskazanych w poleceniu;
- zatwierdzonych ustaleń właściciela zapisanych w poleceniu;
- istniejącej dokumentacji projektu.

Dokument nie powstał na podstawie nowych wywołań sieciowych ani nowych audytów wykonawczych.

---

## 2. STATUS DOKUMENTU

> **PROJEKT FORMALNEGO KONTRAKTU DANYCH YAHOO CHART — CZEKA NA DECYZJĘ WŁAŚCICIELA.**

Niniejszy dokument:

- nie zatwierdza produkcyjnego kontraktu chart;
- nie zatwierdza kontrolowanego audytu sieciowego;
- nie zatwierdza implementacji produkcyjnej;
- nie jest dowodem, że chart spełnia już wymagania pełnego ALCHEMIKA;
- nie jest podstawą do rozpoczęcia żadnego z kolejnych etapów.

Dokument rozdziela:

1. fakty już potwierdzone;
2. decyzje zatwierdzone przez właściciela;
3. projektowany kontrakt do późniejszej akceptacji;
4. zagadnienia nadal nierozstrzygnięte;
5. warunki przyszłego audytu offline i sieciowego.

Decyzja o przyjęciu kontraktu należy wyłącznie do właściciela projektu.

---

## 3. CEL I ZAKRES

Celem dokumentu jest formalne opisanie planowanego kontraktu danych pomiędzy:

- dynamicznym uniwersum Yahoo;
- endpointem Yahoo chart;
- warstwą normalizacji i walidacji;
- Observation;
- Baseline;
- Technical Engine;
- Hunter;
- MasterEngine;
- GPT-4o;
- Telegramem.

Dokument ma charakter wyłącznie projektowy. Nie zatwierdza implementacji ani przebiegu sieciowego.

Zakres dokumentu obejmuje:

- rolę chart w pełnym przepływie ALCHEMIKA;
- wejście z dynamicznego uniwersum;
- kontrakt żądania i odpowiedzi Yahoo chart;
- zasady normalizacji timestampów i OHLCV;
- zasady walidacji metadanych, danych bieżących, historii i jakości serii;
- statusy walidacji i flagi gotowości;
- granice odpowiedzialności architektonicznej;
- wpływ na Observation, Baseline, Technical Engine, Hunter, MasterEngine, GPT-4o i Telegram;
- fakty potwierdzone dotychczasowymi audytami;
- zagadnienia nierozstrzygnięte;
- plan walidacji offline i kontrolowanego audytu sieciowego;
- kryteria przyszłej akceptacji.

---

## 4. KATEGORIE INFORMACJI

Każdy zapisany fakt jest oznaczany jedną z następujących kategorii:

| Kategoria | Znaczenie |
|-----------|-----------|
| **DECYZJA WŁAŚCICIELA** | została jawnie przekazana albo zatwierdzona przez właściciela; |
| **FAKT POTWIERDZONY** | wynika z dotychczasowych audytów opisanych w dokumentacji obowiązkowej; |
| **PROJEKT KONTRAKTU** | projektowany zapis do późniejszej akceptacji właściciela; |
| **NIEROZSTRZYGNIĘTE** | wymaga dalszej decyzji właściciela albo dalszego audytu; |
| **OGRANICZENIE** | wskazuje, czego dany fakt albo decyzja nie dowodzi. |

Nie przedstawia się projektu kontraktu jako faktu potwierdzonego. Nie przedstawia się decyzji właściciela jako wyniku nowego audytu wykonawczego.

---

## 5. ZATWIERDZONE DECYZJE WŁAŚCICIELA

### 5.1. Źródło danych

Kategoria: **DECYZJA WŁAŚCICIELA**.

Produkcyjnym źródłem danych rynkowych ALCHEMIKA pozostaje wyłącznie Yahoo Finance.

Oficjalne źródła GPW i NewConnect mogą służyć wyłącznie jako zamrożona referencja kontrolna do audytu lub etykietowania. Nie dostarczają danych rynkowych do Observation, Baseline ani silników.

### 5.2. Jeden zbiór Yahoo

Kategoria: **DECYZJA WŁAŚCICIELA**.

Yahoo nie udostępnia pola rozróżniającego GPW_MAIN i NewConnect.

ALCHEMIK ma traktować instrumenty zwrócone przez Yahoo jako jeden zbiór polskich instrumentów WSE z symbolami zwróconymi przez Yahoo, zwykle z końcówką `.WA`.

Segment GPW/NC nie jest częścią produkcyjnego kontraktu danych Yahoo.

Nie wolno automatycznie tworzyć symbolu Yahoo przez dopisanie `.WA`, `.PL` ani jakiejkolwiek innej końcówki.

### 5.3. Dynamiczne uniwersum

Kategoria: **DECYZJA WŁAŚCICIELA**.

Custom screener Yahoo jest mechanizmem discovery i wstępnego filtrowania.

Zakres cenowy dynamicznego uniwersum jest zapisany na sztywno:

- minimum: 0,10 PLN;
- maksimum: 10,00 PLN;
- dolna i górna granica są włączone.

Screener może dostarczać między innymi:

- `symbol`;
- `quoteType`;
- `exchange`;
- `market`;
- `currency`;
- `regularMarketPrice`;
- `total`;
- `start` lub `offset`;
- `count`;
- rekordy stron paginacji.

Screener nie jest źródłem historii OHLCV, wskaźników technicznych, Observation ani Baseline.

### 5.4. Rola chart

Kategoria: **DECYZJA WŁAŚCICIELA**.

Yahoo chart jest planowanym centralnym źródłem danych rynkowych dla:

- bieżącej ceny;
- wolumenu;
- timestampów;
- historii OHLCV;
- danych wymaganych przez Observation;
- danych wymaganych przez Baseline;
- wejścia do Technical Engine;
- wejścia do Hunter;
- danych przekazywanych dalej do MasterEngine.

Chart nie może sam przejmować odpowiedzialności RuntimeService, HistoryRepository, Technical Engine, Hunter ani MasterEngine.

### 5.5. Historia krótsza niż 52 tygodnie

Kategoria: **DECYZJA WŁAŚCICIELA**.

Historia krótsza niż 52 tygodnie nie może automatycznie blokować wejścia instrumentu do Observation.

Instrument z krótszą historią może:

- przejść do Observation;
- otrzymać Baseline w zakresie rzeczywiście dostępnych danych;
- mieć ograniczoną gotowość dla części wskaźników technicznych;
- nie przejść do wskaźnika, który wymaga większej liczby punktów niż faktycznie dostępna seria.

Nie wolno wymyślać nowej minimalnej liczby świec. Wymagania długości serii muszą w przyszłości wynikać z rzeczywistych kontraktów i konfiguracji istniejących wskaźników Technical Engine.

### 5.6. Wolumen równy zero

Kategoria: **DECYZJA WŁAŚCICIELA**.

`volume=0` jest prawidłową wartością danych i sam w sobie nie jest błędem.

Zero może oznaczać brak transakcji w danym interwale lub bardzo niską płynność.

Status błędu wolumenu może dotyczyć między innymi:

- braku pola;
- wartości `null`;
- wartości nienumerycznej;
- wartości ujemnej;
- uszkodzonej struktury;
- niezgodnej długości tablic uniemożliwiającej przypisanie wolumenu do świecy.

Nie wolno klasyfikować instrumentu jako `CHART_BAD_VOLUME` wyłącznie dlatego, że wolumen wynosi zero.

### 5.7. AI i Telegram

Kategoria: **DECYZJA WŁAŚCICIELA**.

GPT-4o znajduje się na końcu ścieżki.

AI otrzymuje wyłącznie dane wcześniej pobrane, znormalizowane, zwalidowane i przepuszczone przez system.

AI:

- nie uzupełnia brakujących danych rynkowych;
- nie naprawia historii;
- nie rozstrzyga segmentu GPW/NC;
- nie zgaduje wartości;
- nie zastępuje walidatora danych.

Telegram otrzymuje dopiero wynik końcowego procesu decyzyjnego. Nie jest źródłem danych ani miejscem walidacji.

---

## 6. MIEJSCE CHART W PEŁNYM PRZEPŁYWIE ALCHEMIKA

Kategoria: **DECYZJA WŁAŚCICIELA + PROJEKT KONTRAKTU**.

Zatwierdzony kierunek projektowy podstawowej ścieżki produkcyjnej Yahoo:

```
custom screener Yahoo
→ walidacja rekordów i symboli
→ quote/chart
→ moduły systemowe
→ GPT-4o
```

Miejsce chart w planowanym przepływie:

1. Custom screener Yahoo dostarcza dynamiczne uniwersum oraz pola discovery.
2. Wejściem chart jest wyłącznie dokładny symbol zwrócony przez screener Yahoo.
3. Yahoo chart jest planowanym centralnym źródłem danych rynkowych: bieżącej ceny, wolumenu, timestampów, historii OHLCV.
4. Surowa odpowiedź chart jest przekazywana do warstwy parsera i normalizacji.
5. Znormalizowana seria jest oceniana przez walidator chart.
6. RuntimeService decyduje o przekazaniu poprawnych danych do dalszych etapów zgodnie z zatwierdzonymi kontraktami.
7. Observation i Baseline korzystają ze zwalidowanych danych chart.
8. Technical Engine otrzymuje zwalidowaną serię OHLCV i sam oblicza wskaźniki.
9. Hunter wykorzystuje przygotowane dane, Baseline, zmianę i wyniki techniczne.
10. MasterEngine koordynuje dalszą analizę.
11. GPT-4o otrzymuje wyłącznie dane wcześniej pobrane, znormalizowane, zwalidowane i przepuszczone przez system.
12. Telegram otrzymuje dopiero wynik końcowego procesu decyzyjnego.

Chart nie może sam przejmować odpowiedzialności RuntimeService, HistoryRepository, Technical Engine, Hunter ani MasterEngine.

Chart nie jest źródłem discovery uniwersum. Chart nie zastępuje screenera.

---

## 7. WEJŚCIE Z DYNAMICZNEGO UNIWERSUM

Kategoria: **DECYZJA WŁAŚCICIELA + PROJEKT KONTRAKTU**.

Wejściem chart jest wyłącznie dokładny symbol zwrócony przez screener Yahoo wraz z dostępnymi polami porównawczymi:

- `symbol`;
- `quoteType`;
- `exchange`;
- `market`;
- `currency`;
- `regularMarketPrice`;
- informacja o przynależności do zatwierdzonego zakresu 0,10–10,00 PLN;
- timestamp lub czas snapshotu, jeżeli jest dostępny.

Nie wolno konstruować alternatywnego symbolu. Nie wolno automatycznie tworzyć symbolu Yahoo przez dopisanie `.WA`, `.PL` ani jakiejkolwiek innej końcówki.

Brak instrumentu w screenerze oznacza brak instrumentu w danym cyklu dynamicznego uniwersum. Nie jest to dowód oficjalnego braku instrumentu na GPW lub NewConnect.

Custom screener Yahoo jest mechanizmem discovery i wstępnego filtrowania. Screener nie jest źródłem historii OHLCV, wskaźników technicznych, Observation ani Baseline.

### 7.1. Pola porównawcze z screenera

| Pole | Rola w kontrakcie wejścia |
|------|---------------------------|
| `symbol` | dokładny symbol Yahoo do wywołania chart; |
| `quoteType` | potwierdzenie typu `EQUITY`; |
| `exchange` | potwierdzenie rynku; |
| `market` | potwierdzenie rynku, jeżeli pole występuje; |
| `currency` | potwierdzenie waluty; |
| `regularMarketPrice` | cena bieżąca z screenera do porównania; |
| przynależność do zakresu | kwalifikacja do bieżącego dynamicznego uniwersum; |
| timestamp snapshotu | podstawa porównania różnicy czasu między screenerem a chart. |

### 7.2. Ograniczenia wejścia

- Brak rekordu screenera dla danego instrumentu oznacza brak instrumentu w bieżącym cyklu uniwersum.
- Brak rekordu w screenerze nie jest dowodem oficjalnego braku instrumentu na GPW lub NewConnect.
- Screener nie dostarcza historii OHLCV ani wskaźników technicznych.
- Symbole z screenera mogą reprezentować różne encje; walidacja typu i tożsamości pozostaje obowiązkowa.

---

## 8. KONTRAKT ŻĄDANIA YAHOO CHART

Kategoria: **PROJEKT KONTRAKTU**.

Planowana trasa żądania:

`/v8/finance/chart/{symbol}`

Dokument nie zawiera wartości cookie ani crumb.

### 8.1. Zakres zatwierdzony

Zatwierdzone elementy kontraktu żądania ograniczają się do:

- trasy `/v8/finance/chart/{symbol}`;
- symbolu pochodzącego wyłącznie z dynamicznego uniwersum Yahoo;
- zakazu konstruowania alternatywnych symboli.

### 8.2. Zagadnienia do osobnego zatwierdzenia

Dokładne kombinacje `range` i `interval` nie zostały potwierdzone przez właściciela ani przez istniejący kod projektu.

Dokładne konfiguracje zapytań dla:

- historii dziennej;
- historii intraday;
- danych bieżących;

oznacza się jako zagadnienie do osobnego zatwierdzenia przed audytem sieciowym.

Dokument nie wymyśla limitów Yahoo, retry, fallbacków ani harmonogramów.

### 8.3. Ograniczenia

- Nie zatwierdza się jeszcze dokładnych kombinacji `range` i `interval`.
- Nie ustala się produkcyjnego budżetu wywołań.
- Nie ustala się polityki retry, timeoutów ani cache.
- Sztuczny limit audytowy z wcześniejszych ustaleń nie określa produkcyjnego budżetu wywołań.

---

## 9. KONTRAKT ODPOWIEDZI YAHOO CHART

Kategoria: **PROJEKT KONTRAKTU**.

### 9.1. Metadane

Projektowany kontrakt odpowiedzi chart obejmuje następujące metadane:

- `symbol`;
- `instrumentType`;
- `currency`;
- `exchangeName`;
- `gmtoffset`;
- `timezone`;
- `exchangeTimezoneName`;
- `dataGranularity`;
- `regularMarketPrice`;
- `regularMarketTime`;
- zakres odpowiedzi, jeżeli występuje.

### 9.2. Seria

Projektowany kontrakt odpowiedzi chart obejmuje następujące pola serii:

- `timestamp`;
- `open`;
- `high`;
- `low`;
- `close`;
- `volume`.

Pole `adjclose` oznacza się jako wymagające osobnej decyzji właściciela. Dokument nie zatwierdza samodzielnie użycia `adjclose` przez silniki.

### 9.3. Rodzaje błędów

Kontrakt odpowiedzi rozdziela następujące sytuacje:

- brak odpowiedzi;
- HTTP error;
- błąd parsowania;
- odpowiedź bez wyniku;
- brak wymaganych pól;
- częściową serię;
- konflikt danych;
- serię technicznie niegotową.

HTTP 404, HTTP 401 ani pusta odpowiedź nie są równoważnymi stanami. Nie przedstawia się ich jako tożsamych sytuacji.

---

## 10. NORMALIZACJA TIMESTAMPÓW I OHLCV

Kategoria: **PROJEKT KONTRAKTU**.

Dokument zapisuje następujące zasady normalizacji i walidacji OHLCV:

1. timestampy muszą być przypisane do odpowiadających im wartości OHLCV;
2. seria po normalizacji musi mieć jednoznaczną kolejność czasową;
3. duplikaty timestampów muszą być wykrywane i raportowane;
4. wartości brakujące muszą pozostać jawne;
5. nie wolno cicho tworzyć brakującej świecy;
6. nie wolno cicho kopiować poprzedniej ceny lub wolumenu;
7. weekend albo dzień bez sesji nie jest automatycznie dziurą w danych;
8. brak świecy, świeca z wolumenem zero i brak sesji są trzema różnymi sytuacjami;
9. poprawność OHLC dla kompletnej świecy wymaga:
   - `high` nie może być niższe od `open`, `close` ani `low`;
   - `low` nie może być wyższe od `open`, `close` ani `high`;
10. nie wolno wymyślać tolerancji cenowej między screenerem i chart;
11. różnica ceny między endpointami musi uwzględniać różnicę czasu snapshotów;
12. historyczne ceny poza aktualnym zakresem 0,10–10,00 PLN nie są automatycznie błędem;
13. zakres cenowy dotyczy kwalifikacji do bieżącego dynamicznego uniwersum, a nie usuwania historycznych świec.

### 10.1. Obowiązki parsera i normalizacji

Warstwa parsera i normalizacji odpowiada za:

- odczyt struktury odpowiedzi;
- powiązanie timestampów z wartościami OHLCV;
- normalizację typów;
- zachowanie informacji o brakach;
- brak cichego uzupełniania lub wymyślania wartości.

---

## 11. WALIDACJA METADANYCH

Kategoria: **PROJEKT KONTRAKTU**.

Walidacja metadanych obejmuje ocenę:

- zgodności `symbol` z symbolem wejściowym z dynamicznego uniwersum;
- obecności i zgodności `instrumentType` (oczekiwane `EQUITY`);
- obecności i zgodności `currency` (oczekiwane `PLN` dla polskiego uniwersum);
- obecności `exchangeName` i zgodności z rynkiem WSE;
- poprawności `gmtoffset`, `timezone` i `exchangeTimezoneName`, jeżeli występują;
- obecności `dataGranularity`, jeżeli występuje;
- obecności `regularMarketPrice` i `regularMarketTime`, jeżeli są wymagane dla danych bieżących;
- zakresu odpowiedzi, jeżeli występuje.

Jawna inna wartość pola oznacza konflikt. Brak opcjonalnego pola nie oznacza konfliktu.

---

## 12. WALIDACJA DANYCH BIEŻĄCYCH

Kategoria: **PROJEKT KONTRAKTU**.

Walidacja danych bieżących obejmuje:

- obecność `regularMarketPrice`;
- obecność `regularMarketTime`;
- spójność ceny bieżącej z ostatnią świecą serii, jeżeli obie są dostępne;
- porównanie ceny bieżącej chart z ceną `regularMarketPrice` ze screenera z uwzględnieniem różnicy czasu snapshotów;
- zakaz wymyślania tolerancji cenowej między screenerem i chart;
- zasadę, że różnica ceny między endpointami musi uwzględniać różnicę czasu snapshotów.

Historyczne ceny poza aktualnym zakresem 0,10–10,00 PLN nie są automatycznie błędem.

---

## 13. WALIDACJA HISTORII

Kategoria: **PROJEKT KONTRAKTU**.

Walidacja historii obejmuje:

- obecność tablic `timestamp`, `open`, `high`, `low`, `close`, `volume`;
- zgodną długość tablic umożliwiającą przypisanie wolumenu do świecy;
- jednoznaczną kolejność czasową serii;
- wykrywanie i raportowanie duplikatów timestampów;
- jawne zachowanie wartości brakujących;
- wykrywanie przerw w serii bez automatycznego klasyfikowania dnia bez sesji jako dziury;
- rozróżnienie trzech sytuacji: brak świecy, świeca z wolumenem zero, brak sesji;
- ocenę poprawności relacji OHLC dla kompletnych świec.

Zakres cenowy 0,10–10,00 PLN dotyczy kwalifikacji do bieżącego dynamicznego uniwersum, a nie usuwania historycznych świec.

---

## 14. WALIDACJA JAKOŚCI SERII

Kategoria: **PROJEKT KONTRAKTU**.

Walidacja jakości serii ocenia:

- długość rzeczywiście dostępnej serii;
- kompletność świec;
- obecność duplikatów;
- obecność przerw wymagających interpretacji;
- zgodność długości tablic;
- możliwość przypisania każdego wolumenu do świecy;
- gotowość serii do przekazania do dalszych etapów.

Wymagania długości serii nie są ustalane w tym dokumencie. Muszą w przyszłości wynikać z rzeczywistych kontraktów i konfiguracji istniejących wskaźników Technical Engine.

---

## 15. WOLUMEN RÓWNY ZERO

Kategoria: **DECYZJA WŁAŚCICIELA + PROJEKT KONTRAKTU**.

`volume=0` jest prawidłową wartością danych i sam w sobie nie jest błędem.

Zero może oznaczać brak transakcji w danym interwale lub bardzo niską płynność.

Nie wolno klasyfikować instrumentu jako `CHART_BAD_VOLUME` wyłącznie dlatego, że wolumen wynosi zero.

Status błędu wolumenu może dotyczyć między innymi:

- braku pola;
- wartości `null`;
- wartości nienumerycznej;
- wartości ujemnej;
- uszkodzonej struktury;
- niezgodnej długości tablic uniemożliwiającej przypisanie wolumenu do świecy.

---

## 16. HISTORIA KRÓTSZA NIŻ 52 TYGODNIE

Kategoria: **DECYZJA WŁAŚCICIELA + PROJEKT KONTRAKTU**.

Historia krótsza niż 52 tygodnie nie może automatycznie blokować wejścia instrumentu do Observation.

Instrument z krótszą historią może:

- przejść do Observation;
- otrzymać Baseline w zakresie rzeczywiście dostępnych danych;
- mieć ograniczoną gotowość dla części wskaźników technicznych;
- nie przejść do wskaźnika, który wymaga większej liczby punktów niż faktycznie dostępna seria.

Nie wymyśla się nowej minimalnej liczby świec.

`CHART_HISTORY_TOO_SHORT` nie blokuje automatycznie Observation.

---

## 17. STATUSY WALIDACJI

Kategoria: **DECYZJA WŁAŚCICIELA + PROJEKT KONTRAKTU**.

Zatwierdzone robocze statusy walidacji:

- `CHART_OK`;
- `CHART_NO_DATA`;
- `CHART_INCOMPLETE`;
- `CHART_DUPLICATES`;
- `CHART_BAD_SESSION`;
- `CHART_BAD_VOLUME`;
- `CHART_TYPE_CONFLICT`;
- `CHART_CURRENCY_CONFLICT`;
- `CHART_RANGE_CONFLICT`;
- `CHART_HISTORY_TOO_SHORT`;
- `CHART_SERIES_BROKEN`.

Nie traktuje się wszystkich statusów jako identycznie blokujących.

### 17.1. Obowiązkowe wyjątki

- `CHART_HISTORY_TOO_SHORT` nie blokuje automatycznie Observation;
- `volume=0` nie może samodzielnie spowodować `CHART_BAD_VOLUME`.

### 17.2. Zagadnienia nierozstrzygnięte

Następujące kwestie pozostają jawnie nierozstrzygnięte:

- pełna kolejność pierwszeństwa statusów;
- czy instrument może mieć więcej niż jeden status;
- dokładne warunki `CHART_INCOMPLETE`;
- dokładne warunki `CHART_BAD_SESSION`;
- dokładne warunki `CHART_RANGE_CONFLICT`;
- różnica między `CHART_INCOMPLETE` i `CHART_SERIES_BROKEN`.

Dokument nie podejmuje tych decyzji za właściciela.

### 17.3. Brak statusu transportu

Dokument zauważa potrzebę rozstrzygnięcia statusu dla transportu, HTTP lub parsowania. Nazwa takiego statusu nie jest samodzielnie zatwierdzana. Kwestia pozostaje w sekcji zagadnień otwartych.

---

## 18. FLAGI GOTOWOŚCI MODUŁÓW

Kategoria: **PROJEKT KONTRAKTU — DO PÓŹNIEJSZEJ AKCEPTACJI**.

Dokument projektuje, ale nie zatwierdza implementacyjnie, niezależne flagi gotowości:

- gotowość do Observation;
- gotowość do Baseline;
- gotowość do Technical Engine;
- gotowość do Hunter;
- gotowość do MasterEngine;
- gotowość do GPT-4o;
- gotowość do Telegrama.

Dokument jasno stwierdza:

- instrument może być gotowy do Observation, ale niegotowy do części wskaźników;
- gotowość Technical Engine zależy od rzeczywistej długości i jakości serii wymaganej przez jego wskaźniki;
- brak gotowości technicznej nie może być automatycznie interpretowany jako brak instrumentu;
- dane nieprzepuszczone przez walidację nie mogą trafić do AI;
- AI nie może uzupełniać braków.

Dokument nie projektuje nowych klas Python, sygnatur funkcji, tabel SQLite ani nazw plików kodu. To będzie osobny etap po zatwierdzeniu kontraktu.

---

## 19. GRANICE ODPOWIEDZIALNOŚCI

Dokument zachowuje zatwierdzoną architekturę projektu.

### 19.1. Warstwa Yahoo/chart

Odpowiada wyłącznie za pobranie odpowiedzi chart oraz bezpieczne przekazanie surowych danych do parsera.

### 19.2. Parser i normalizacja

Odpowiadają za:

- odczyt struktury odpowiedzi;
- powiązanie timestampów z wartościami OHLCV;
- normalizację typów;
- zachowanie informacji o brakach;
- brak cichego uzupełniania lub wymyślania wartości.

### 19.3. Walidator chart

Odpowiada za ocenę jakości i utworzenie jawnego wyniku walidacji oraz flag gotowości.

Walidator nie tworzy trwałego Observation i nie zapisuje Baseline.

### 19.4. RuntimeService

RuntimeService pozostaje właścicielem cyklu wykonawczego i cyklu życia Observation.

To RuntimeService decyduje o przekazaniu poprawnych danych do dalszych etapów zgodnie z zatwierdzonymi kontraktami.

### 19.5. HistoryRepository

HistoryRepository pozostaje właścicielem kontraktu trwałego zapisu historii Observation i Baseline.

SQLiteHistoryRepository jest wyłącznie produkcyjną implementacją tego kontraktu.

### 19.6. Technical Engine

Technical Engine:

- otrzymuje zwalidowaną serię OHLCV;
- sam oblicza wskaźniki zgodnie ze swoim kontraktem;
- nie pobiera danych z Yahoo;
- nie zgaduje brakujących świec;
- nie otrzymuje danych bez jawnej informacji o gotowości serii.

### 19.7. Hunter

Hunter wykorzystuje przygotowane dane, Baseline, zmianę i wyniki techniczne.

Hunter nie przechowuje Observation i nie naprawia danych rynkowych.

### 19.8. MasterEngine

MasterEngine koordynuje dalszą analizę, ale nie jest parserem Yahoo ani repozytorium historii.

### 19.9. Modele istniejące

HunterResult pozostaje końcowym modelem kwalifikacji.

MarketEvent, EventOutcome, SessionOutcome i CycleReport nie mogą zostać wykorzystane jako trwały magazyn Observation lub Baseline.

---

## 20. WPŁYW NA OBSERVATION I BASELINE

Kategoria: **PROJEKT KONTRAKTU**.

Planowany wpływ chart na Observation i Baseline:

- Observation otrzymuje dane z chart dopiero po normalizacji i walidacji;
- Baseline jest tworzony w zakresie rzeczywiście dostępnych danych;
- historia krótsza niż 52 tygodnie nie blokuje automatycznie wejścia do Observation;
- pierwszy poprawny odczyt może utworzyć trwały baseline nowej InstrumentObservation zgodnie z zatwierdzonymi zasadami kanonu;
- walidator chart nie tworzy trwałego Observation i nie zapisuje Baseline;
- RuntimeService pozostaje właścicielem cyklu życia Observation;
- HistoryRepository pozostaje właścicielem kontraktu trwałego zapisu;
- poprawna zmieniona treść tego samego timestampu, instrumentu, Observation i źródła jest audytowalną rewizją (`SOURCE_REVISION_ACCEPTED`) z `revision_number` i `supersedes_reading_id`, zachowującą poprzednią wersję, nie tworzącą baseline i nie kończącą Observation;
- nowy, późniejszy timestamp rozpoczyna `revision_number=1`, jego `prev_reading_id` wskazuje efektywną wersję poprzedniego timestampu, a `supersedes_reading_id` pozostaje NULL.

Dokument nie zmienia zatwierdzonych zasad granicy InstrumentReading → InstrumentObservation.

Decyzja właściciela z 2026-08-19, wynikająca z rzeczywistego cyklu Yahoo, rozszerza KANON §13.3 pkt 9 i §13.5 pkt 12 o model rewizji InstrumentReading (wyniki domenowe `save_reading`: `ACCEPTED`, `SOURCE_REVISION_ACCEPTED`, `DUPLICATE_NO_OP`, `CONFLICT`, `STALE_TIMESTAMP`; unikalność `(instrument_id, market_data_timestamp, revision_number)`) i zastępuje wcześniejszy zakaz rewizji.

---

## 21. WPŁYW NA TECHNICAL ENGINE

Kategoria: **PROJEKT KONTRAKTU**.

Planowany wpływ chart na Technical Engine:

- Technical Engine otrzymuje zwalidowaną serię OHLCV;
- Technical Engine sam oblicza wskaźniki zgodnie ze swoim kontraktem;
- Technical Engine nie pobiera danych z Yahoo;
- Technical Engine nie zgaduje brakujących świec;
- Technical Engine nie otrzymuje danych bez jawnej informacji o gotowości serii;
- gotowość Technical Engine zależy od rzeczywistej długości i jakości serii wymaganej przez jego wskaźniki;
- instrument może być gotowy do Observation, ale niegotowy do części wskaźników;
- brak gotowości technicznej nie może być automatycznie interpretowany jako brak instrumentu.

Wymagania długości serii muszą w przyszłości wynikać z rzeczywistych kontraktów i konfiguracji istniejących wskaźników Technical Engine.

---

## 22. WPŁYW NA HUNTER I MASTERENGINE

Kategoria: **PROJEKT KONTRAKTU**.

Planowany wpływ chart na Hunter:

- Hunter wykorzystuje przygotowane dane, Baseline, zmianę i wyniki techniczne;
- Hunter nie przechowuje Observation;
- Hunter nie naprawia danych rynkowych;
- Hunter nie pobiera danych bezpośrednio z Yahoo chart.

Planowany wpływ chart na MasterEngine:

- MasterEngine koordynuje dalszą analizę;
- MasterEngine nie jest parserem Yahoo;
- MasterEngine nie jest repozytorium historii;
- MasterEngine otrzymuje dane przekazane przez wcześniejsze etapy zgodnie z zatwierdzonymi kontraktami.

Dokument nie zmienia otwartych decyzji dotyczących kontraktu Market Hunter → MasterEngine ani sposobu przekazywania OHLCV.

---

## 23. WPŁYW NA GPT-4O I TELEGRAM

Kategoria: **DECYZJA WŁAŚCICIELA + PROJEKT KONTRAKTU**.

GPT-4o znajduje się na końcu ścieżki.

AI otrzymuje wyłącznie dane wcześniej pobrane, znormalizowane, zwalidowane i przepuszczone przez system.

AI:

- nie uzupełnia brakujących danych rynkowych;
- nie naprawia historii;
- nie rozstrzyga segmentu GPW/NC;
- nie zgaduje wartości;
- nie zastępuje walidatora danych.

Dane nieprzepuszczone przez walidację nie mogą trafić do AI.

Telegram otrzymuje dopiero wynik końcowego procesu decyzyjnego. Nie jest źródłem danych ani miejscem walidacji.

---

## 24. FAKTY POTWIERDZONE DOTYCHCZASOWYMI AUDYTAMI

Kategoria: **FAKT POTWIERDZONY**.

Jako fakty historycznych audytów zapisuje się:

- custom screener Yahoo działał jako discovery polskich symboli `.WA`;
- screener zwracał pola discovery, ale nie historię OHLCV;
- chart zwrócił HTTP 200 dla badanych symboli w kontrolowanym przebiegu;
- quoteSummary i zbiorczy quote zwracały HTTP 401 w ostatnim przebiegu;
- HTTP 401 dla mechanizmów pomocniczych nie unieważnia odpowiedzi chart HTTP 200;
- dotychczasowy przebieg nie zbadał formalnie jakości pełnej historii chart;
- nie udowodniono kompletności GPW i NewConnect;
- Yahoo nie dostarcza pola segmentu GPW/NC;
- wynik jednego przebiegu nie dowodzi stabilności 24/7;
- pełny produkcyjny kontrakt chart pozostaje niezatwierdzony.

Dokument nie zapisuje jako faktu, że chart spełnia już wymagania pełnego ALCHEMIKA.

### 24.1. Ograniczenia faktów

- Wyniki audytów są snapshotami konkretnych przebiegów.
- HTTP 200 chart dla badanych symboli nie dowodzi kompletności ani stabilności.
- Nie udowodniono oficjalnej kompletności GPW + NewConnect.
- Nie udowodniono stabilności Yahoo 24/7.
- Nie udowodniono rozróżnienia Głównego Rynku GPW i NewConnect.

---

## 25. ZAGADNIENIA NIEROZSTRZYGNIĘTE

Kategoria: **NIEROZSTRZYGNIĘTE**.

Dokument zawiera co najmniej następujące zagadnienia otwarte:

1. dokładne kombinacje `range` i `interval`;
2. wymagany zakres historii dziennej i intraday;
3. wymagania długości serii dla każdego istniejącego wskaźnika;
4. zasady aktualności `regularMarketTime`;
5. zasady porównania ceny screenera i chart;
6. kalendarz sesji WSE, święta i strefy czasowe;
7. zasady rozpoznania faktycznej dziury w danych;
8. politykę dla częściowo brakujących świec;
9. użycie lub pominięcie `adjclose`;
10. zasady obsługi splitów i innych zdarzeń korporacyjnych;
11. kolejność pierwszeństwa statusów;
12. sposób reprezentacji wielu jednoczesnych problemów;
13. granicę między danymi wystarczającymi dla Observation i Technical Engine;
14. wymagania dla intraday na VPS działającym 24/7;
15. limity i zachowanie Yahoo przy pełnym dynamicznym uniwersum;
16. zasady trwałego zapisu surowych i znormalizowanych danych;
17. sposób odtworzenia Observation po restarcie;
18. dokładny kontrakt przekazania danych do istniejących modułów.

Dodatkowo otwarte pozostają:

- potrzeba rozstrzygnięcia statusu dla transportu, HTTP lub parsowania;
- pełna kolejność pierwszeństwa statusów walidacji;
- warunki `CHART_INCOMPLETE`, `CHART_BAD_SESSION`, `CHART_RANGE_CONFLICT`;
- różnica między `CHART_INCOMPLETE` i `CHART_SERIES_BROKEN`;
- sposób reprezentacji wielu jednoczesnych problemów walidacji.

Dokument nie rozstrzyga tych punktów samodzielnie.

---

## 26. PLAN WALIDACJI OFFLINE

Kategoria: **PROJEKT KONTRAKTU — DO PÓŹNIEJSZEJ AKCEPTACJI**.

Dokument zapisuje zatwierdzoną kolejność etapów:

1. formalny kontrakt chart — bieżący krok;
2. macierz testów;
3. walidacja offline;
4. jeden kontrolowany audyt rzeczywistych danych Yahoo;
5. ocena gotowości Observation, Baseline, Technical Engine i Hunter;
6. dopiero po akceptacji — testy i implementacja produkcyjna.

Walidacja offline ma zostać przeprowadzona bez połączeń sieciowych.

Dokument nie rozpoczyna żadnego z kolejnych etapów.

### 26.1. Zakres przyszłej walidacji offline

Zakres przyszłej walidacji offline obejmować będzie co najmniej:

- testy parsowania odpowiedzi chart na danych sztucznych;
- testy normalizacji timestampów i OHLCV;
- testy powiązania timestampów z wartościami;
- testy wykrywania duplikatów;
- testy jawnego zachowania braków;
- testy walidacji metadanych;
- testy walidacji danych bieżących;
- testy walidacji historii;
- testy walidacji jakości serii;
- testy statusów walidacji;
- testy flag gotowości.

Dokument nie zatwierdza jeszcze konkretnej macierzy testów.

---

## 27. PLAN KONTROLOWANEGO AUDYTU SIECIOWEGO

Kategoria: **PROJEKT KONTRAKTU — DO PÓŹNIEJSZEJ AKCEPTACJI**.

Dokument zapisuje warunki przyszłego kontrolowanego audytu sieciowego:

- audyt sieciowy jest wykonaniem jednego kontrolowanego przebiegu rzeczywistych danych Yahoo;
- audyt sieciowy może nastąpić dopiero po zatwierdzeniu walidacji offline;
- audyt sieciowy wymaga osobnej decyzji właściciela;
- dokładne konfiguracje zapytań chart muszą zostać zatwierdzone przed audytem sieciowym;
- nie wykonano żadnego połączenia sieciowego w ramach bieżącego zadania;
- audyt sieciowy nie został zatwierdzony niniejszym dokumentem.

Dokument nie zatwierdza kontrolowanego audytu sieciowego.

---

## 28. KRYTERIA PRZYSZŁEJ AKCEPTACJI

Kategoria: **PROJEKT KONTRAKTU — DO PÓŹNIEJSZEJ AKCEPTACJI**.

Przyszła akceptacja kontraktu będzie wymagać rozstrzygnięcia co najmniej:

- dokładnych kombinacji `range` i `interval`;
- wymaganego zakresu historii dziennej i intraday;
- wymagań długości serii dla każdego istniejącego wskaźnika;
- zasad aktualności `regularMarketTime`;
- zasad porównania ceny screenera i chart;
- kalendarza sesji WSE, świąt i stref czasowych;
- zasad rozpoznania faktycznej dziury w danych;
- polityki dla częściowo brakujących świec;
- użycia lub pominięcia `adjclose`;
- zasad obsługi splitów i innych zdarzeń korporacyjnych;
- kolejności pierwszeństwa statusów;
- sposobu reprezentacji wielu jednoczesnych problemów;
- granicy między danymi wystarczającymi dla Observation i Technical Engine;
- wymagań dla intraday na VPS działającym 24/7;
- limitów i zachowania Yahoo przy pełnym dynamicznym uniwersum;
- zasad trwałego zapisu surowych i znormalizowanych danych;
- sposobu odtworzenia Observation po restarcie;
- dokładnego kontraktu przekazania danych do istniejących modułów.

Akceptacja kontraktu nie jest równoznaczna z akceptacją implementacji.

---

## 29. OGRANICZENIA

Dokument podlega następującym ograniczeniom:

- Dokument nie zatwierdza produkcyjnego kontraktu chart.
- Dokument nie zatwierdza kontrolowanego audytu sieciowego.
- Dokument nie zatwierdza implementacji produkcyjnej.
- Dokument nie jest dowodem, że chart spełnia już wymagania pełnego ALCHEMIKA.
- Dokument nie potwierdza kompletności GPW ani NewConnect.
- Dokument nie potwierdza stabilności Yahoo 24/7.
- Dokument nie rozstrzyga zagadnień wymienionych w sekcji 25.
- Dokument nie zmienia zamrożonej architektury projektu.
- Dokument nie zmienia żadnego istniejącego pliku.

W bieżącym zadaniu nie wykonano:

- połączeń sieciowych;
- wywołań Yahoo Finance;
- wywołań GPW lub NewConnect;
- użycia XTB;
- Search ani Lookup;
- screenera;
- chart;
- odczytu cookie lub crumb;
- modyfikacji kodu;
- modyfikacji testów;
- modyfikacji konfiguracji;
- modyfikacji `requirements.txt`;
- modyfikacji baz SQLite;
- tworzenia skryptów pomocniczych;
- uruchamiania testów projektu;
- tworzenia implementacji modułu chart;
- tworzenia nowych modeli, klas lub tabel;
- zmiany istniejącej architektury;
- operacji Git zmieniających stan.

---

## 30. KONIEC DOKUMENTU

Data utworzenia: 15.08.2026

Status: PROJEKT FORMALNEGO KONTRAKTU DANYCH YAHOO CHART — NIE ZATWIERDZONY PRZEZ WŁAŚCICIELA.

Dokument czeka na ocenę i decyzję właściciela projektu.

Decyzja o przyjęciu kontraktu należy wyłącznie do właściciela projektu.

