# 00_ALCHEMIK_KANON_NAPRAWY

## DOKUMENT ARCHITEKTONICZNY — PROPONOWANY KANON ARCHITEKTONICZNY

Data: 08.08.2026
Wersja: 1.1
Status: Proponowany kanon architektoniczny — oczekuje na jawne zatwierdzenie właściciela.

Do czasu akceptacji właściciela treść niniejszego dokumentu nie jest obowiązująca ani niepodlegająca zmianie.

---

## SPIS TREŚCI

1. [Cel ALCHEMIKA](#1-cel-alchemika)
2. [Kanoniczny przepływ](#2-kanoniczny-przepływ)
3. [Trzy pytania analityczne](#3-trzy-pytania-analityczne)
4. [Granice modeli](#4-granice-modeli)
5. [Dwie role HunterEngine](#5-dwie-role-hunterengine)
6. [Powstanie MarketEvent](#6-powstanie-marketevent)
7. [AI, Tavily i Telegram](#7-ai-tavily-i-telegram)
8. [Zakres operacyjny](#8-zakres-operacyjny)
9. [Aktualny stan i zakazy](#9-aktualny-stan-i-zakazy)
10. [Otwarte decyzje właściciela](#10-otwarte-decyzje-właściciela)
11. [Zasada procesu przed każdą zmianą kodu](#11-zasada-procesu-przed-każdą-zmianą-kodu)
12. [Zatwierdzone zasady — granica InstrumentReading → InstrumentObservation](#12-zatwierdzone-zasady--granica-instrumentreading--instrumentobservation)

---

## 1. CEL ALCHEMIKA

ALCHEMIK realizuje następujące cele architektoniczne, uznane za obowiązujące i niepodlegające zmianie bez jawnej decyzji właściciela:

- Automatyczne, ciągłe monitorowanie groszówek GPW i USA.
- Yahoo Finance jako źródło danych rynkowych.
- Brak ręcznej watchlisty — instrumenty pochodzą z automatycznego uniwersum.
- Duże spółki są wykluczane zgodnie z przyszłą, zatwierdzoną definicją automatycznego uniwersum; AAPL jest przykładem instrumentu poza zakresem.
- Wykrywanie wczesnej nietypowej aktywności, nie automatyczne podejmowanie decyzji inwestycyjnej.
- Historia około 52 tygodni jako kontekst indywidualnego zachowania instrumentu.

System **nie jest botem inwestycyjnym**. Nie wydaje rekomendacji BUY, SELL ani HOLD. Jest narzędziem wspomagania decyzji inwestora.

---

## 2. PROPONOWANY PRZEPŁYW

Proponowany przepływ wynikający z dotychczasowych decyzji właściciela:

```
automatyczne uniwersum → Yahoo Finance → InstrumentReading → InstrumentObservation
→ porównanie bieżącego stanu z poprzednim stanem i historią instrumentu
→ Market Hunter → MasterEngine → MarketEvent → analiza → Tavily → AI → Telegram
→ EventOutcome / SessionOutcome
```

Po jawnej akceptacji właściciela przepływ staje się obowiązującym punktem odniesienia. Każda zmiana przepływu, kolejności lub odpowiedzialności wymaga jawnej decyzji właściciela.

---

## 3. TRZY PYTANIA ANALITYCZNE

Architektura ALCHEMIKA opiera się na ścisłym rozdzieleniu trzech odrębnych pytań, na które odpowiadają trzy osobne mechanizmy:

| Pytanie | Mechanizm | Odpowiedzialność |
|---------|-----------|-----------------|
| „Co zmieniło się teraz?" | Poprzedni odczyt (prev_reading_id) | InstrumentReading — porównanie bieżącego odczytu z poprzednim |
| „Czy ta zmiana jest nietypowa dla tej spółki?" | Historia instrumentu | InstrumentObservation — sekwencja odczytów i lifecycle instrumentu |
| „Jak kończyły się wcześniejsze wykryte zdarzenia?" | EventOutcome / SessionOutcome | Modele wynikowe — historyczne rezultaty zdarzeń |

Żaden z tych mechanizmów nie zastępuje innego. Nie wolno łączyć odpowiedzialności trzech pytań w jednym modelu ani pomijać żadnego z nich.

---

## 4. GRANICE MODELI

### 4.1 InstrumentReading

InstrumentReading jest **niezmiennym faktem rynkowym**. Reprezentuje pojedynczy odczyt danych OHLCV z Yahoo Finance dla jednego instrumentu w konkretnym `market_data_timestamp`.

- `source` jest zawsze `"YahooFinance"` — jedyne dopuszczalne źródło.
- `data_completeness` przyjmuje wartości `COMPLETE` (open, high, low, close wypełnione) lub `PARTIAL` (tylko close wypełnione).
- Wszystkie pola danych są niezmienne po utworzeniu (immutable).
- `canonical_identity()` zwraca parę `(instrument_id, market_data_timestamp)` — jednoznaczny fakt rynkowy.
- `prev_reading_id` — opcjonalna relacja do poprzedniego odczytu tego samego instrumentu.

**Baseline i pierwszy odczyt (zatwierdzone — patrz §12):**
- Pierwszy poprawny InstrumentReading (w tym PARTIAL) tworzy trwały baseline nowej InstrumentObservation.
- Pierwszy zaakceptowany Reading ma `prev_reading_id=None`; RuntimeService tworzy ACTIVE Observation i przyjmuje ten Reading jako jedną operację logiczną.
- Kolejne poprawne odczyty są porównywane z poprzednim stanem i historią obserwacji.
- Dokładna semantyka UNKNOWN, TRIGGERED i NOT_TRIGGERED pozostaje otwartą decyzją właściciela.

### 4.2 InstrumentObservation

InstrumentObservation jest **trwałą sekwencją i lifecycle instrumentu**. Reprezentuje obserwację instrumentu z własną niezmienną tożsamością `observation_id`.

- Stany: `ACTIVE` → `TERMINATED_DOMAIN` / `TERMINATED_TECHNICAL` / `INTEGRITY_BREACHED`.
- Przejścia terminalne są nieodwracalne — po osiągnięciu stanu terminalnego nie można go zmienić.
- `observation_id` i `instrument_id` są niezmienne po utworzeniu.
- Każde przejście terminalne wymaga jawnego powodu (`termination_reason`).

### 4.3 RuntimeService

RuntimeService docelowo odpowiada za lifecycle obserwacji i jawny restore. Obecnie odpowiada za:

- Cykl życia Runtime (run_cycle).
- Koordynację MarketScanner, HunterEngine, MasterEngine.
- Deduplikację, alerty, persystencję MarketEvent.
- Obsługę OutcomeComputer (inicjalizacja EventOutcome i obliczanie SessionOutcome).

Trwałość InstrumentReading i InstrumentObservation oraz restore nie są jeszcze wdrożone w aktualnym pipeline.

### 4.4 HistoryRepository

HistoryRepository jest **właścicielem kontraktu trwałości**. Definiuje interfejs zapisu i odczytu cykli oraz MarketEvent. SQLiteHistoryRepository jest obecną produkcyjną implementacją HistoryRepository. Docelowo HistoryRepository ma obejmować trwałość obserwacji — nie jest to jeszcze wdrożone.

### 4.4a Granice obserwacji

- Każdy InstrumentReading należy jawnie do dokładnie jednej InstrumentObservation (przez `observation_id`).
- `NO_DATA`, `SOURCE_ERROR` i timeout są zdarzeniami operacyjnymi i nie tworzą InstrumentReading.
- Nie wolno automatycznie wybierać „nowszego" odczytu jako sposobu naprawy naruszenia integralności.

### 4.5 MarketEvent

MarketEvent jest **snapshotem konkretnego wykrytego zdarzenia**, nie baseline'em ani obserwacją wieloskanową. Historyczny kontrakt MarketEvent obejmuje 27 pól i 13 etapów cyklu życia — po akceptacji kanonu zakres ten wymaga dalszego harmonizowania z przepływem obserwacji.

MarketEvent **nie jest**:
- Obserwacją instrumentu (tę rolę pełni InstrumentObservation).
- Baseline'em do porównań historycznych.
- Agregacją wyników wielu skanów.

### 4.6 EventOutcome i SessionOutcome

EventOutcome i SessionOutcome **nie zastępują obserwacji ani historii instrumentu**. Są modelami wynikowymi przechowującymi rezultaty zdarzeń rynkowych po ich wykryciu:

- **EventOutcome** — wynik całego zdarzenia (poziom zbiorczy, kompletność, postęp).
- **SessionOutcome** — wynik pojedynczego horyzontu sesyjnego (+1, +2, +3, +5).

Żaden z tych modeli nie przechowuje decyzji inwestycyjnych, rekomendacji AI (BUY/SELL/HOLD), oceny ryzyka ani pozycji rankingowej.

### 4.7 HunterResult

HunterResult jest **wyłącznie wynikiem końcowej kwalifikacji** i nie może przenosić:

- Surowych danych OHLCV.
- `raw_input` jako trwałego elementu architektury — `raw_input` jest niezatwierdzonym eksperymentalnym mechanizmem obecnym w zamrożonych zmianach. Nie stanowi architektury docelowej, nie może być używany jako wzorzec kontraktu i wymaga osobnej decyzji właściciela.
- Stanu obserwacji (InstrumentObservation).

---

## 5. DWIE ROLE HUNTERENGINE

HunterEngine występuje w dwóch odrębnych rolach, których odpowiedzialności są ściśle rozdzielone:

### 5.1 Market Hunter (poziom rynku)

Market Hunter wydaje decyzję selekcyjną dotyczącą dalszej analizy instrumentu. Jego obowiązujące cechy:

- Nie wymaga rankingu, ryzyka ani confidence.
- Nie przejmuje odpowiedzialności AI, Tavily, RankingEngine, RiskEngine ani AnalystEngine.
- `CHANGED` nie oznacza automatycznie `TRIGGERED` — zmiana stanu instrumentu nie jest tożsama z wygenerowaniem MarketEvent.
- Dokładny kontrakt danych i sposób przekazania kontekstu do MasterEngine pozostają otwartą decyzją właściciela.

### 5.2 Hunter pojedynczego tickera

Hunter pojedynczego tickera kwalifikuje instrument po otrzymaniu wymaganych wyników technicznych, rankingu i ryzyka. Działa w kontekście MasterEngine, nie wykonuje ponownego skanowania rynku. Dokładna kolejność AI względem tej kwalifikacji pozostaje częścią zatwierdzanego kontraktu orkiestracji.

### 5.3 Stan UNKNOWN

`UNKNOWN` wymaga jawnej obsługi określonej przez zatwierdzony kontrakt; nie wolno go domyślnie akceptować ani odrzucać.

---

## 6. POWSTANIE MARKETEVENT

### 6.1 Reguła powstania

- **Kandydat rynku nie jest jeszcze MarketEvent.** Market Hunter identyfikuje instrumenty — nie tworzy zdarzeń.
- **MarketEvent powstaje dopiero po wykryciu konkretnego zdarzenia przez właściwy detektor** (Price Event Detector, Volume Event Detector, Technical Event Detector itd.).
- Katalog i hierarchia zdarzeń (`docs/Katalog_Zdarzen_Rynkowych.md`, `docs/Hierarchia_Zdarzen_Rynkowych.md`) pozostają źródłem klasyfikacji zdarzeń po ich wykryciu.

### 6.2 Zastąpiony zapis historyczny

Wszelkie historyczne zapisy (kod, dokumentacja, komentarze) stwierdzające, że MarketScanner lub HunterEngine tworzy MarketEvent bezpośrednio po skanowaniu, **wymagają oznaczenia jako zastąpione przez obowiązujący przepływ obserwacji**. Nie stanowią one podstawy do implementacji.

---

## 7. AI, TAVILY I TELEGRAM

### 7.1 Tavily

Tavily służy **wyłącznie do świeżego kontekstu** — wyszukiwania informacji mogących wyjaśnić bieżący ruch rynkowy. Domyślny zakres analizy: maksymalnie ostatnie 24 godziny.

Tavily **nie służy** do:
- Budowania historii instrumentu.
- Zastępowania analizy historycznej wykonywanej przez wcześniejsze moduły.
- Generowania baseline'u dla porównań.

### 7.2 AI

AI jest **końcową warstwą interpretacji** pełnego kontekstu. Jej obowiązujące cechy:

- Otrzymuje komplet informacji przygotowanych przez wcześniejsze moduły.
- **Rozdziela fakty, interpretacje, hipotezy, scenariusze, ryzyka i ograniczenia.**
- **Nie wydaje rekomendacji BUY, SELL ani HOLD.**
- Nie rozpoczyna analizy od zera.
- Placeholder AI nie jest uznawany za działającą integrację GPT-4.0.
- AI jest uruchamiana dla każdego wykrytego zdarzenia spełniającego kryteria zatwierdzone przez właściciela. AI działa po zebraniu pełnego kontekstu i pozostaje końcową warstwą interpretacji. Dokument nie definiuje ani nie wymyśla progów liczbowych tych kryteriów.

### 7.3 Telegram

Telegram **przekazuje raport dla inwestora**, a nie automatyczną decyzję inwestycyjną. Wiadomość Telegram zawiera:

- Symbol instrumentu.
- Opis wykrytego zdarzenia.
- Kontekst analityczny.
- Interpretację AI (fakty, hipotezy, scenariusze, ryzyka).
- **Nie zawiera rekomendacji BUY/SELL/HOLD.**

---

## 8. ZAKRES OPERACYJNY

### 8.1 Aktywny zakres

Aktywny zakres automatyczny obejmuje **groszówki GPW i USA**. Są to instrumenty objęte bieżącą architekturą i naprawą.

### 8.2 ETF

ETF pozostaje elementem **historycznego katalogu i możliwym przyszłym rozszerzeniem**, lecz nie jest aktywnym zakresem obecnej naprawy. Kod i konfiguracja dotyczące ETF nie są przedmiotem obecnych zmian bez osobnej decyzji właściciela.

### 8.3 Progi

Wartości progów z historycznych dokumentów (np. `docs/Przeplyw_Zdarzen_Rynkowych.md`, pliki `config/`) **nie stają się automatycznie obowiązującą konfiguracją** bez osobnej decyzji właściciela lub potwierdzenia na rzeczywistych danych.

---

## 9. AKTUALNY STAN I ZAKAZY

### 9.1 Zamrożone zmiany

Cztery niezatwierdzone zmiany dotyczące Market Huntera (Krok 6A) pozostają **zamrożone do czasu osobnej decyzji właściciela**:

- `data/models/hunter_result.py` — modyfikacja (unstaged)
- `engines/hunter/engine.py` — modyfikacja (unstaged)
- `tests/test_hunter_engine.py` — modyfikacja (unstaged)
- `tests/test_runtime.py` — modyfikacja (unstaged)

Nie wolno modyfikować, rozszerzać ani scalać tych zmian bez jawnej decyzji właściciela.

### 9.2 Zakazy architektoniczne

- **Nie wolno uznawać rozwiązania z `HunterResult.raw_input` i opcjonalnymi scoringami za architekturę docelową.** Jest to mechanizm tymczasowy, który zostanie zastąpiony.
- **Funkcjonalny wynik testów nie oznacza GREEN repozytorium.** Przechodzące testy są warunkiem koniecznym, ale niewystarczającym do uznania repozytorium za GREEN — GREEN oznacza czysty Git (brak niezatwierdzonych zmian) oraz przechodzące testy.
- **Wewnętrzne komponenty ALCHEMIKA nie mogą być zastępowane mockami w testach integracyjnych.** Mocki są dopuszczalne wyłącznie na granicach systemu: Yahoo Finance, Tavily, dostawca AI.
- Nie wolno uznawać rozwiązania tymczasowego za architekturę docelową bez jawnej decyzji właściciela.

---

## 10. OTWARTE DECYZJE WŁAŚCICIELA

Następujące decyzje pozostają otwarte i wymagają jawnego rozstrzygnięcia przez właściciela przed przystąpieniem do implementacji:

1. **Definicja automatycznego uniwersum groszówek GPW i USA** — jakie kryteria (kapitalizacja, cena, płynność) definiują groszówki GPW i USA.

2. **Dokładny kontrakt danych Market Hunter → MasterEngine** — jaka struktura danych jest przekazywana z Market Huntera do MasterEngine po usunięciu `raw_input`.

3. **Sposób przekazywania OHLCV bez używania HunterResult** — jak dane OHLCV mają być dostarczane do MasterEngine bez pośrednictwa pola `raw_input` w HunterResult.

4. **Semantyka UNKNOWN, TRIGGERED i NOT_TRIGGERED w InstrumentObservation** — precyzyjne definicje stanów i przejść (semantyka baseline'u pierwszego odczytu została zatwierdzona — patrz §12).

5. **Kryteria uruchomienia AI i Telegrama** — dokładne warunki, przy których AI i Telegram są uruchamiane (jakościowe i ilościowe).

6. **Zasada utrwalania informacji o wysyłce Telegrama** — gdzie i w jaki sposób przechowywać informację o wysłanym powiadomieniu Telegram (dedykowany model, rozszerzenie MarketEvent, osobna tabela).

---

## 11. ZASADA PROCESU PRZED KAŻDĄ ZMIANĄ KODU

Przed każdą zmianą kodu w projekcie ALCHEMIK obowiązuje następująca procedura:

1. **Przeczytaj kanon i checkpoint:**
   - `docs/00_ALCHEMIK_KANON_NAPRAWY.md`
   - `docs/ALCHEMIK_CHECKPOINT_PRACY.md`

2. **Wskaż dotykaną granicę danych:**
   - Który model, silnik lub moduł jest zmieniany.
   - Jakie dane wchodzą, jakie wychodzą.
   - Który kontrakt danych jest modyfikowany.

3. **Wskaż modele i moduły objęte zakazem zmiany:**
   - Wyraźnie wymień, których modeli i modułów **nie wolno** zmieniać w ramach tej zmiany.
   - Uzasadnij, dlaczego nie są one dotykane.

4. **Określ test dowodzący zgodności kontraktu:**
   - Jakie testy (istniejące lub nowe) udowodnią, że zmiana nie narusza kontraktu danych.
   - Jakie testy udowodnią, że zakazane moduły nie zostały naruszone.

---

## 12. ZATWIERDZONE ZASADY — GRANICA INSTRUMENTREADING → INSTRUMENTOBSERVATION

Następujące zasady zostały zatwierdzone przez właściciela 08.08.2026 i przechodzą z otwartych decyzji do obowiązującego kanonu architektonicznego. Ich implementacja pozostaje niewdrożona.

### 12.1 Baseline i pierwszy odczyt

1. Pierwszy poprawny `InstrumentReading` może mieć `data_completeness=PARTIAL` i tworzy trwały baseline nowej `InstrumentObservation`.
2. Pierwszy zaakceptowany Reading ma `prev_reading_id=None`; RuntimeService tworzy ACTIVE Observation i przyjmuje ten Reading jako jedną operację logiczną.

### 12.2 Idempotentność, integralność i konflikt

Reguła rozstrzygania dla istniejącej tożsamości `(instrument_id, market_data_timestamp)`:

3. **Dokładny duplikat** — ponowne dostarczenie faktu o identycznej treści (zgodnie z §12.2a) jest idempotentnym no-op: nie tworzy nowego Readingu, nie zmienia Observation i nie jest błędem integralności.

4. **Starszy, wcześniej nieznany timestamp** — Reading ze starszym `market_data_timestamp`, wcześniej nieznany dla danego instrumentu, jest odrzucany z rejestracją operacyjną, bez zmiany Readingów i Observation. Nie przechodzi do INTEGRITY_BREACHED.

5. **Konflikt tej samej tożsamości z inną treścią** — ta sama globalna tożsamość `(instrument_id, market_data_timestamp)` z inną treścią faktu (zgodnie z §12.2a) jest konfliktem integralności: nowy fakt jest odrzucany; nie zapisuje nowego Readingu; nie zmienia istniejących Readingów; atomowo przełącza bieżącą ACTIVE InstrumentObservation do INTEGRITY_BREACHED; zapisuje jawny `termination_reason`. Przejście do INTEGRITY_BREACHED jest trwałe i nieodwracalne. Operacyjna rejestracja konfliktu nie może decydować o powodzeniu ani cofnięciu tego trwałego przejścia.

### 12.2a Definicja „tej samej treści faktu"

Dla istniejącej tożsamości `(instrument_id, market_data_timestamp)` ta sama treść faktu obejmuje wyłącznie pola danych rynkowych:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `data_completeness`
- `source`

Nie obejmuje pól tożsamościowych i technicznych:

- `reading_id`
- `observation_id`
- `prev_reading_id`
- `scan_timestamp`

### 12.3 Kolejność Readingów w Observation

6. „Ostatni zaakceptowany Reading" w sekwencji Observation jest określany wyłącznie przez największy `market_data_timestamp`. `scan_timestamp` i kolejność fizycznego zapisu nie definiują kolejności faktów rynkowych.

### 12.4 Jedna ACTIVE Observation per instrument

7. Dla jednego `instrument_id` może istnieć najwyżej jedna Observation w stanie ACTIVE. Po osiągnięciu stanu terminalnego (`TERMINATED_DOMAIN`, `TERMINATED_TECHNICAL` lub `INTEGRITY_BREACHED`) przyszły poprawny Reading może rozpocząć nową Observation.

### 12.5 Jawny restore

8. Jawny restore RuntimeService dostarcza do bieżącej pracy Observation w stanie ACTIVE wraz z jej ostatnim zaakceptowanym Readingiem (zgodnie z §12.3). Nie ładuje automatycznie całej historii Readingów do pamięci roboczej. Stany terminalne pozostają trwałą historią, ale nie są przywracane do bieżącej pracy.

### 12.6 Atomowość trwałego stanu

9. Atomowość dotyczy trwałego stanu Observation i Readingów. Zaakceptowany Reading oraz związana z nim aktualizacja Observation są zapisywane atomowo. Przejście do INTEGRITY_BREACHED w wyniku konfliktu (pkt 5) jest trwałym przejściem stanu Observation.

10. Nie tworzyć modelu, klasy, tabeli ani nazwy technicznej `IntegrityEvent`. Dokumenty mają mówić wyłącznie o rejestracji operacyjnej lub konflikcie integralności.

### 12.7 Dozwolone stany lifecycle

11. Lifecycle Observation nie zawiera `INACTIVE` ani ogólnego `TERMINATED`. Dozwolone stany pozostają wyłącznie:
   - `ACTIVE`
   - `TERMINATED_DOMAIN`
   - `TERMINATED_TECHNICAL`
   - `INTEGRITY_BREACHED`

### 12.8 Konsekwencje INTEGRITY_BREACHED

12. `INTEGRITY_BREACHED` kończy wyłącznie bieżącą InstrumentObservation. Instrument pozostaje w automatycznym uniwersum i może utworzyć nową Observation po przyszłym poprawnym Readingu.

### 12.9 Własność komponentów

13. `RuntimeService` pozostaje właścicielem lifecycle i jawnego restore. `HistoryRepository` pozostaje właścicielem kontraktu trwałości, a `SQLiteHistoryRepository` jego implementacją.

### 12.10 Modele niebędące baseline'em

14. `HunterResult`, `MarketEvent`, `EventOutcome`, `SessionOutcome` i `CycleReport` nie są baseline'em ani stanem Observation.

---

## 13. ZABEZPIECZENIA TRWAŁOŚCI — ZATWIERDZONE ZASADY

Następujące zasady zostały zatwierdzone przez właściciela 08.08.2026 po korekcie implementacji trwałości. Są one obowiązujące przy każdej dalszej zmianie kontraktu trwałości.

### 13.1 Niedestrukcyjny zapis Observation

1. Observation terminalna nie może zostać nadpisana, zastąpiona ani reaktywowana przez ponowne użycie tego samego `observation_id`. Próba zapisu Readingu do terminalnej Observation rzuca `ValueError`. Stan terminalny, `termination_reason` i istniejące Readingi pozostają niezmienione.
2. Zapis Observation używa zwykłego `INSERT INTO` dla nowych `observation_id`, z jawną obsługą `IntegrityError` dla częściowego UNIQUE indeksu jednej ACTIVE Observation. Dla istniejącego `observation_id` nie są modyfikowane kolumny stanu ani przyczyny terminalizacji. `INSERT OR REPLACE` oraz `INSERT OR IGNORE` są niedopuszczalne w ścieżce persystencji `instrument_observations`.
3. Dozwolone przejścia lifecycle są wykonywane wyłącznie kontrolowaną, niedestrukcyjną aktualizacją `UPDATE … SET state = … WHERE … AND state = …`.

### 13.2 Fizyczne wymuszenie „maksymalnie jedna ACTIVE Observation"

4. Dla jednego `instrument_id` może istnieć najwyżej jedna Observation w stanie ACTIVE. Niezmiennik jest wymuszany na granicy trwałości przez mechanizm SQLite.
5. Zastosowany mechanizm: częściowy indeks UNIQUE `CREATE UNIQUE INDEX … ON instrument_observations(instrument_id) WHERE state = 'ACTIVE'`. Mechanizm uniemożliwia fizyczne wstawienie drugiej ACTIVE Observation, ale dopuszcza wiele terminalnych Observation oraz utworzenie nowej ACTIVE po terminalizacji poprzedniej.
6. Próba utworzenia drugiej ACTIVE Observation dla tego samego instrumentu rzuca `ValueError`. Nie jest to konflikt treści Readingu — jest to odrębne naruszenie niezmiennika. Nie zwraca `CONFLICT`, nie zapisuje drugiej Observation ani osieroconego Readingu.

### 13.3 Błąd techniczny SQLite nie jest konfliktem domenowym

7. Fizyczna kolizja globalnej tożsamości Readingu `(instrument_id, market_data_timestamp)` jest rozpoznawana po naruszeniu `idx_readings_identity`. Po wycofaniu transakcji (`rollback`) istniejący rekord jest ponownie odczytywany: identyczna treść siedmiu pól daje `DUPLICATE_NO_OP`, różna treść daje `CONFLICT`. Brak rekordu przy ponownym odczycie jest błędem technicznym — propagowany jest oryginalny `sqlite3.IntegrityError`, bez zwracania `CONFLICT` i bez terminalizacji Observation.
8. Każdy inny `sqlite3.IntegrityError`, `OperationalError` lub błąd trwałości jest przekazywany do wywołującego jako wyjątek techniczny po jawnym `rollback`. Nie jest maskowany jako `CONFLICT`. Nie dodaje się nowych statusów domenowych do jego obsługi.
9. Cztery wyniki domenowe `save_reading` pozostają wyłącznie: `ACCEPTED`, `DUPLICATE_NO_OP`, `CONFLICT`, `STALE_TIMESTAMP`. Żaden piąty wynik nie jest wprowadzany. `ValueError` jest wyjątkiem, nie wynikiem domenowym.

### 13.4 Atomowość zapisu Readingu i Observation

10. Zapis Readingu oraz utworzenie/aktualizacja Observation stanowią jedną atomową transakcję. Przejście ACTIVE → INTEGRITY_BREACHED przy konflikcie również jest objęte tą samą transakcją.
11. W razie błędu technicznego podczas zapisu całość jest wycofywana. Nie może pozostać częściowo zapisany Reading, częściowo utworzona Observation ani zmieniony lifecycle.

### 13.5 Globalna unikalność tożsamości Readingu

12. Fizyczne wymuszenie `UNIQUE` na `(instrument_id, market_data_timestamp)` przez `CREATE UNIQUE INDEX idx_readings_identity` jest obowiązujące. Nie wystarcza samo sprawdzenie aplikacyjne.

### 13.6 Zakres niewdrożony

13. RuntimeService, Market Hunter, MasterEngine i test pionowy pozostają niewdrożone. Niniejsze zasady dotyczą wyłącznie granicy trwałości `HistoryRepository → SQLiteHistoryRepository`.

### 13.7 Migracja testów (zatwierdzona przez właściciela 08.08.2026)

14. Historyczny test 40 `test_terminal_observation_not_replaced_by_same_obs_id` został zastąpiony przez `test_terminal_observation_raises_value_error`.
15. Historyczny test 41 `test_reading_not_added_to_terminal_observation` został zastąpiony przez `test_terminal_state_preserved_after_value_error`.
16. Test 45 `test_two_repos_cannot_create_two_active_observations` zachował nazwę, ale oczekiwanie zmieniono na `pytest.raises(ValueError)`.
17. Migracja nie oznacza utraty pokrycia — testy dostosowano do obowiązującego kontraktu: terminalna Observation oraz druga ACTIVE Observation kończą się `ValueError`, nie `CONFLICT`.

---

## 14. ZATWIERDZONA GRANICA RUNTIMESERVICE → INSTRUMENTOBSERVATION

Następujące zasady zostały zatwierdzone przez właściciela 09.08.2026 i przechodzą z otwartych decyzji do obowiązującego kanonu architektonicznego.

**Stan implementacji (10.08.2026):**

- Kod i test integracyjny zostały utrwalone lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` o komunikacie `feat(runtime): persist observations before hunter`.
- Ograniczona implementacja Runtime → Observation została funkcjonalnie potwierdzona przez niezależną weryfikację właściciela z 10.08.2026.
- Kontrakt Market Hunter → MasterEngine pozostaje poza zakresem tej integracji i nie został zmieniony.
- Repozytorium po pierwszym commicie kodu nadal nie jest GREEN — dokumentacja i pliki K6A pozostają niecommitowane.

### 14.1 Jeden Reading z najnowszego MarketData

1. Jeden poprawny kandydat rynku może utworzyć jeden `InstrumentReading` wyłącznie z najnowszego dostępnego `MarketData`, określonego przez największy źródłowy `market_data_timestamp`.

### 14.2 Historyczny kontekst OHLCV

2. Pełna lista OHLCV pobrana przez Yahoo Finance, w tym kontekst historyczny do 52 tygodni, pozostaje kontekstem analitycznym. Nie jest automatycznie zamieniana na wiele nowych Readingów podczas każdego skanu i nie jest przenoszona przez `HunterResult`.

### 14.3 NO_DATA, SOURCE_ERROR i timeout

3. `NO_DATA`, `SOURCE_ERROR` i timeout nie tworzą `InstrumentReading`, nie tworzą Observation oraz nie kończą aktywnej Observation.

### 14.4 Własność lifecycle i jawny restore

4. `RuntimeService` jest właścicielem lifecycle Observation. Restore jest jawną operacją startową wykonywaną przez entrypoint przed pierwszym `run_cycle()` danej instancji RuntimeService.

5. Restore nie może być ukryty w konstruktorze RuntimeService i nie może być automatycznie wykonywany na początku każdego `run_cycle()`.

### 14.5 Pierwsza integracja — ograniczony zakres

6. Pierwsza przyszła integracja Runtime z trwałością ma ograniczony zakres: poprawny kandydat ma przejść przez warstwę Observation przed Market Hunterem, lecz ta integracja nie definiuje jeszcze żadnego nowego filtra, progu, triggera, `UNKNOWN`, `CHANGED`, `NOT_TRIGGERED` ani `TRIGGERED`.

7. W pierwszej integracji wynik zapisu Readingu nie może samodzielnie zmienić obecnej reguły przekazywania kandydatów do Market Huntera lub MasterEngine. Kontrakt Market Hunter → MasterEngine i sposób przekazywania OHLCV nadal pozostają otwartymi decyzjami właściciela.

8. Dopiero po niezależnej weryfikacji tej ograniczonej integracji właściciel podejmie decyzję, jak porównanie Observation wpływa na Market Huntera i na możliwość przekazania instrumentu do MasterEngine.

### 14.6 CHANGED ≠ TRIGGERED

9. `CHANGED` nie jest równoznaczne z `TRIGGERED`.

---

## KONIEC DOKUMENTU

Data utworzenia: 08.08.2026
Data aktualizacji: 09.08.2026
Wersja: 1.3
Status: Częściowo zatwierdzony — decyzje dotyczące granicy InstrumentReading → InstrumentObservation (§12), zabezpieczenia trwałości (§13) oraz granicy RuntimeService → InstrumentObservation (§14) zatwierdzone przez właściciela 08–09.08.2026. Pozostałe treści pozostają proponowane.

Kanon zmienia się wyłącznie po jawnej decyzji właściciela. Zatwierdzone zasady §12, §13 i §14 są obowiązujące; pozostałe sekcje pozostają proponowane do czasu akceptacji właściciela.
