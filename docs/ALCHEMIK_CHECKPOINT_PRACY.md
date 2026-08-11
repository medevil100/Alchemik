# ALCHEMIK_CHECKPOINT_PRACY

## KRÓTKI, FAKTYCZNY STAN PROJEKTU NA DZIEŃ WYKONANIA ZADANIA

Data utworzenia: 08.08.2026
Data aktualizacji: 10.08.2026
Status: Zatwierdzone decyzje właściciela (pkt 1–6 zadania) zapisane w Kanonie i Checkpoincie 08.08.2026. Commit trwałości i dokumentacji wykonany 09.08.2026. Commit K6A usunięcia `raw_input` wykonany 10.08.2026. Repozytorium nie jest deklarowane jako GREEN w tym zadaniu dokumentacyjnym.

---

## 0. PRZEJRZYSTY STATUS PROJEKTU

| Obszar | Stan | Dowód lub źródło | Najbliższa dozwolona czynność |
|--------|------|-----------------|------------------------------|
| Proponowany kanon (`docs/00_ALCHEMIK_KANON_NAPRAWY.md`) | częściowo zatwierdzony | Dokument zaktualizowany 10.08.2026 | Implementacja po decyzjach właściciela |
| Checkpoint (`docs/ALCHEMIK_CHECKPOINT_PRACY.md`) | zatwierdzony | Dokument zaktualizowany 10.08.2026 | — |
| Cztery zmiany Market Huntera | commitowane | Lokalny commit `ee4a918` (`fix(hunter): remove raw_input from HunterResult`), 4 pliki: `data/models/hunter_result.py`, `engines/hunter/engine.py`, `tests/test_hunter_engine.py`, `tests/test_runtime.py`; po commicie Git czysty (staging pusty, brak unstaged i untracked); `git push` nie został wykonany | — |
| Automatyczne uniwersum groszówek GPW i USA | niewdrożone | `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §10 pkt 1 | Osobne ustalenie definicji uniwersum przez właściciela |
| Trwałość i restore InstrumentReading / InstrumentObservation | niewdrożone | `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §4.3, §4.4 — oznaczone jako docelowe, niewdrożone | Projekt kontraktu trwałości po akceptacji kanonu |
| Porównanie odczytów i Market Hunter oparty na obserwacji | niewdrożone | `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §3, §5.1 — zdefiniowane jako architektura docelowa | Implementacja po zatwierdzeniu kontraktów |
| Kontrakt Market Hunter → MasterEngine | otwarta decyzja | `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §10 pkt 2–3 | Decyzja właściciela |
| Audyt MasterEngine → Hunter pojedynczego tickera | niepotwierdzone | Niezależna weryfikacja nie została wykonana | Audyt po akceptacji kanonu |
| Rzeczywiste GPT-4.0, Tavily i Telegram | niepotwierdzone | Adapter Tavily i wcześniejsza integracja istnieją; nie jest potwierdzone produkcyjne wpięcie Tavily oraz rzeczywiste wykonanie pełnej ścieżki end-to-end. Rzeczywiste GPT-4.0 pozostaje nieudowodnione (AI jest placeholderem). Rzeczywiste dostarczenie Telegramem pozostaje nieudowodnione | Weryfikacja produkcyjna po decyzji właściciela |
| Baseline pierwszego odczytu | zatwierdzone | `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §4.1, §12 — pierwszy poprawny odczyt (w tym PARTIAL) tworzy trwały baseline nowej InstrumentObservation | Decyzja zatwierdzona 08.08.2026 — implementacja niewdrożona |
| Zasada AI | proponowane | `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §7.2 — AI uruchamiana dla każdego wykrytego zdarzenia spełniającego zatwierdzone kryteria, bez wpisywania progów liczbowych | Decyzja właściciela o kryteriach |
| Aktualny wynik testów | zweryfikowane | 1600 tests collected, 1600 passed, 41 subtests passed, niezależnie potwierdzone przez właściciela w PowerShell 10.08.2026 | — |
| Stan repozytorium | czysty po commicie K6A | `git status --porcelain=v1` pusty; staging pusty; brak untracked; `git push` nie wykonany | — |

---

## 1. DATA UTWORZENIA CHECKPOINTU

08.08.2026

---

## 2. STATUS DOKUMENTÓW

| Dokument | Status |
|----------|--------|
| `docs/00_ALCHEMIK_KANON_NAPRAWY.md` | **Częściowo zatwierdzony** — §12 zatwierdzony przez właściciela; §4.7 zaktualizowany 10.08.2026 po commicie K6A. Pozostałe sekcje pozostają proponowane. |
| `docs/ALCHEMIK_CHECKPOINT_PRACY.md` | **Zatwierdzony** — niniejszy dokument zaktualizowany 10.08.2026 po commicie K6A. |
| Uwaga | Oba dokumenty zostały zaktualizowane wyłącznie na podstawie jawnych decyzji właściciela. Jedyną osobą uprawnioną do dalszych zmian jest właściciel. |

---

## 3. FAKTYCZNY STAN GIT — POTWIERDZONY NIEZALEŻNIE

### 3.1 Stan na 08.08.2026 (potwierdzony przez właściciela w PowerShell)

```
git status --porcelain=v1:
 M data/models/hunter_result.py         (unstaged — tylko working tree)
 M engines/hunter/engine.py             (unstaged — tylko working tree)
 M tests/test_hunter_engine.py          (unstaged — tylko working tree)
 M tests/test_runtime.py                (unstaged — tylko working tree)
?? docs/00_ALCHEMIK_KANON_NAPRAWY.md   (untracked)
?? docs/ALCHEMIK_CHECKPOINT_PRACY.md   (untracked)

Staging area: PUSTA (git diff --cached --name-status, --stat, --numstat są puste)
git diff --cached --check: czysty
git diff --check: czysty
```

| Kategoria | Pliki |
|-----------|-------|
| **Staged** | Brak (staging area jest pusta) |
| **Unstaged** (working tree) | `data/models/hunter_result.py`, `engines/hunter/engine.py`, `tests/test_hunter_engine.py`, `tests/test_runtime.py` |
| **Untracked** | `docs/00_ALCHEMIK_KANON_NAPRAWY.md`, `docs/ALCHEMIK_CHECKPOINT_PRACY.md` |

### 3.2 HEAD

```
git rev-parse HEAD: 44abfb1a585db8f49650c72db409d3f5a4ee72b8
Branch: master
```

### 3.3 Pliki utworzone przez to zadanie

| Plik | Opis |
|------|------|
| `docs/00_ALCHEMIK_KANON_NAPRAWY.md` | Kanon architektoniczny — utworzony 08.08.2026; zaktualizowany po decyzjach właściciela |
| `docs/ALCHEMIK_CHECKPOINT_PRACY.md` | Checkpoint pracy — utworzony 08.08.2026; zaktualizowany po decyzjach właściciela |

**Żaden inny plik nie został utworzony, zmodyfikowany ani usunięty.**

---

## 4. WYNIK TESTÓW — POTWIERDZONY NIEZALEŻNIE

| Atrybut | Wartość |
|---------|---------|
| **Kolekcja** | 1600 tests collected |
| **Regresja** | 1600 passed, 41 subtests passed |
| **Skipped** | 0 |
| **Failed/Error** | 0 |
| **Data weryfikacji** | 10.08.2026 |
| **Źródło** | Niezależnie potwierdzone przez właściciela w PowerShell |
| **Uwaga** | Testów nie uruchamiano w ramach zadania dokumentacyjnego |

---

## 5. ROZRÓŻNIENIE WYNIKU FUNKCYJNEGO TESTÓW I STANU GREEN

| Pojęcie | Znaczenie | Stan na 10.08.2026 |
|---------|----------|-------------------|
| **Funkcjonalny wynik testów** | Wszystkie testy przechodzą (PASSED) — 1600/1600, 41 subtests | ✅ 1600 passed |
| **Stan GREEN repozytorium** | Czysty Git (brak niezatwierdzonych zmian ORAZ brak untracked) ORAZ wszystkie testy przechodzą | Nie deklarowany w tym zadaniu dokumentacyjnym |

Formalny GREEN i decyzja o push nie są deklarowane w tym zadaniu dokumentacyjnym.

---

## 6. ZAMROŻONY OBSZAR

### 6.1 Stan zmian według Git (stan rzeczywisty na 10.08.2026 po commicie K6A)

Cztery pliki K6A zostały commitowane w `ee4a918`. Repozytorium jest czyste — brak zmian unstaged, staged lub untracked.

### 6.2 Zasada

Commit `ee4a918` jest ostatecznym stanem K6A. Nie wolno modyfikować, rozszerzać ani scalać zmian K6A bez jawnej decyzji właściciela.

---

## 7. NAJBLIŻSZA DOZWOLONA PRACA

Po zatwierdzeniu decyzji dotyczących granicy `InstrumentReading → InstrumentObservation` przez właściciela (08.08.2026), najbliższą dozwoloną pracą jest:

1. **Zaprojektowanie kontraktu trwałości `HistoryRepository → SQLiteHistoryRepository`, bez implementacji** — zaprojektowanie docelowego interfejsu repozytorium dla InstrumentReading i InstrumentObservation w ramach HistoryRepository oraz schematu trwałości dla SQLiteHistoryRepository, bez implementowania kodu produkcyjnego, migracji ani testów.

2. **Audyt aktualnego kodu względem zatwierdzonego kanonu** — porównanie istniejącej implementacji z zasadami zapisanymi w `docs/00_ALCHEMIK_KANON_NAPRAWY.md`. Identyfikacja niezgodności.

3. **Osobne ustalenie pozostałych kontraktów danych przed implementacją** — przed jakąkolwiek zmianą kodu należy zaprojektować i zatwierdzić kontrakty danych dla:
   - Market Hunter → MasterEngine
   - InstrumentObservation → Market Hunter

4. **Brak zgody na:**
   - Poprawianie zmian K6A w commicie `ee4a918`.
   - Tworzenie nowych modeli bez odrębnej decyzji właściciela.
   - Zmianę istniejących modeli objętych zakazami zatwierdzonego kanonu.
   - Scalanie (`git merge`, `git rebase`) zmian K6A.

---

## 8. ZATWIERDZONE DECYZJE — GRANICA INSTRUMENTREADING → INSTRUMENTOBSERVATION

Poniższe decyzje zostały zatwierdzone przez właściciela 08.08.2026. Ich implementacja pozostaje **niewdrożona**.

| # | Decyzja | Status implementacji |
|---|---------|---------------------|
| 1 | Pierwszy poprawny `InstrumentReading` może mieć `data_completeness=PARTIAL` i tworzy trwały baseline nowej `InstrumentObservation`. | niewdrożone |
| 2 | Pierwszy zaakceptowany Reading ma `prev_reading_id=None`; RuntimeService tworzy ACTIVE Observation i przyjmuje ten Reading jako jedną operację logiczną. | niewdrożone |
| 3 | Dokładny duplikat — ponowne dostarczenie faktu o identycznej treści (tylko open, high, low, close, volume, data_completeness, source) jest idempotentnym no-op: nie tworzy nowego Readingu, nie zmienia Observation i nie jest błędem integralności. | niewdrożone |
| 4 | Starszy, wcześniej nieznany timestamp — Reading ze starszym `market_data_timestamp` jest odrzucany z rejestracją operacyjną, bez zmiany Readingów i Observation. Nie przechodzi do INTEGRITY_BREACHED. | niewdrożone |
| 5 | Konflikt tej samej tożsamości z inną treścią — ta sama globalna tożsamość `(instrument_id, market_data_timestamp)` z inną treścią faktu nie zapisuje nowego Readingu; atomowo przełącza bieżącą ACTIVE InstrumentObservation do INTEGRITY_BREACHED; zapisuje jawny `termination_reason`. Przejście jest trwałe i nieodwracalne. Operacyjna rejestracja konfliktu nie może cofnąć tego przejścia. | niewdrożone |
| 6 | Definicja „tej samej treści faktu" dla istniejącej tożsamości obejmuje wyłącznie: open, high, low, close, volume, data_completeness, source. Nie obejmuje: reading_id, observation_id, prev_reading_id, scan_timestamp. | niewdrożone |
| 7 | „Ostatni zaakceptowany Reading" w sekwencji Observation jest określany wyłącznie przez największy `market_data_timestamp`. `scan_timestamp` i kolejność fizycznego zapisu nie definiują kolejności faktów rynkowych. | niewdrożone |
| 8 | Dla jednego `instrument_id` może istnieć najwyżej jedna Observation w stanie ACTIVE. Po osiągnięciu stanu terminalnego przyszły poprawny Reading może rozpocząć nową Observation. | niewdrożone |
| 9 | Jawny restore RuntimeService dostarcza do bieżącej pracy Observation w stanie ACTIVE wraz z jej ostatnim zaakceptowanym Readingiem. Nie ładuje automatycznie całej historii Readingów do pamięci roboczej. | niewdrożone |
| 10 | Atomowość dotyczy trwałego stanu Observation i Readingów. Zaakceptowany Reading oraz związana z nim aktualizacja Observation są zapisywane atomowo. Przejście do INTEGRITY_BREACHED jest trwałym przejściem stanu Observation. | niewdrożone |
| 11 | Nie tworzyć modelu, klasy, tabeli ani nazwy technicznej `IntegrityEvent`. Dokumenty mają mówić wyłącznie o rejestracji operacyjnej lub konflikcie integralności. | niewdrożone |
| 12 | Lifecycle Observation nie zawiera `INACTIVE` ani ogólnego `TERMINATED`. Dozwolone stany: ACTIVE, TERMINATED_DOMAIN, TERMINATED_TECHNICAL, INTEGRITY_BREACHED. | niewdrożone |
| 13 | `RuntimeService` pozostaje właścicielem lifecycle i jawnego restore. `HistoryRepository` pozostaje właścicielem kontraktu trwałości, a `SQLiteHistoryRepository` jego implementacją. | niewdrożone |
| 14 | `HunterResult`, `MarketEvent`, `EventOutcome`, `SessionOutcome` i `CycleReport` nie są baseline'em ani stanem Observation. | niewdrożone |

Decyzje te zostały zapisane również w `docs/00_ALCHEMIK_KANON_NAPRAWY.md` §12 jako zatwierdzone zasady architektoniczne.

---

## 9. STATUS KOREKTY TRWAŁOŚCI (08.08.2026)

Korekta zabezpieczeń trwałości InstrumentReading i InstrumentObservation została wykonana. Nowe wyniki testów są wstępne i wymagają niezależnej weryfikacji właściciela.

### 9.1 Pliki zmodyfikowane w korekcie

| Plik | Status |
|------|--------|
| `application/history_repository.py` | Zmodyfikowany — implementacja pamięciowa 3 operacji |
| `application/sqlite_history_repository.py` | Zmodyfikowany — usunięcie `INSERT OR REPLACE`, dodanie `idx_one_active_observation`, selektywna obsługa `IntegrityError`, atomowość |
| `tests/test_observation_persistence.py` | Rozszerzony — 45 testów (było 39, dodano 6 testów zabezpieczeń) |
| `docs/00_ALCHEMIK_KANON_NAPRAWY.md` | Dodany §13 — Zabezpieczenia trwałości |
| `docs/ALCHEMIK_CHECKPOINT_PRACY.md` | Zaktualizowany — niniejsza sekcja |

### 9.2 Usunięte naruszenia

1. **Destrukcyjny `INSERT OR REPLACE`** dla `instrument_observations` — zastąpiony `INSERT OR IGNORE` z kontrolą `rowcount` i selektywną detekcją drugiej ACTIVE Observation.
2. **Fałszywe `IntegrityError → CONFLICT`** — wprowadzona selektywna obsługa: tylko `idx_readings_identity` i `idx_one_active_observation` są obsługiwane domenowo; pozostałe błędy propagują jako wyjątki techniczne.
3. **Możliwość dwóch ACTIVE Observation** — dodany `CREATE UNIQUE INDEX idx_one_active_observation ON instrument_observations(instrument_id) WHERE state = 'ACTIVE'`.

### 9.3 Wyniki testów (wstępne — do potwierdzenia przez właściciela)

| Faza | Wynik |
|------|-------|
| Testy dedykowane (`test_observation_persistence.py`) | 45 passed |
| Zgodność trwałości (3 pliki testowe) | 119 passed |
| Pełna regresja | 1575 passed, 41 subtests passed |

### 9.4 Stan repozytorium

Repozytorium NIE jest GREEN. Wyniki testów Cline są wstępne. Użytkownik niezależnie potwierdził wcześniejsze 1569 passed we własnym bloku PowerShell. Nowe wyniki 1575 passed po korekcie oczekują na niezależną weryfikację właściciela.

### 9.5 Obowiązująca semantyka trwałości

1. Normalne wyniki `save_reading` są dokładnie cztery:
   - `ACCEPTED`
   - `DUPLICATE_NO_OP`
   - `CONFLICT`
   - `STALE_TIMESTAMP`
   Żaden piąty wynik domenowy nie istnieje. `ValueError` jest wyjątkiem, nie wynikiem domenowym.

2. `CONFLICT` dotyczy wyłącznie:
   - tej samej globalnej tożsamości `(instrument_id, market_data_timestamp)`;
   - innej treści jednego z siedmiu pól: `open`, `high`, `low`, `close`, `volume`, `data_completeness`, `source`;
   - bez zapisu nowego Readingu;
   - z atomowym przejściem ACTIVE Observation → `INTEGRITY_BREACHED`.

3. Terminalna Observation:
   - próba zapisu Readingu rzuca `ValueError`;
   - nie jest `CONFLICT`;
   - nie zmienia Observation ani Readingów.

4. Druga ACTIVE Observation dla tego samego instrumentu:
   - rzuca `ValueError`;
   - nie jest `CONFLICT`;
   - nie zapisuje drugiej Observation ani osieroconego Readingu.

5. Po kolizji globalnej tożsamości Readingu:
   - istniejący rekord jest ponownie odczytywany w czystym stanie;
   - identyczna treść daje `DUPLICATE_NO_OP`;
   - różna treść daje `CONFLICT`;
   - brak rekordu przy ponownym odczycie jest błędem technicznym;
   - propagowany jest oryginalny `sqlite3.IntegrityError`;
   - nie ma `CONFLICT` ani terminalizacji Observation.

6. Migracja testów została zatwierdzona przez właściciela:
   - historyczny test 40 `test_terminal_observation_not_replaced_by_same_obs_id` zastąpiony przez `test_terminal_observation_raises_value_error`;
   - historyczny test 41 `test_reading_not_added_to_terminal_observation` zastąpiony przez `test_terminal_state_preserved_after_value_error`;
   - test 45 zachował nazwę `test_two_repos_cannot_create_two_active_observations`, ale oczekiwanie zmieniono na `pytest.raises(ValueError)`;
   - jest to korekta semantyki, nie utrata pokrycia.

7. Obecny status:
   - bieżące wyniki testów Cline są wstępne;
   - testów nie uruchamiano w ramach tego zadania;
   - brak nowej niezależnej weryfikacji właściciela;
   - repozytorium nie jest GREEN;
   - RuntimeService, Market Hunter, MasterEngine i test pionowy nadal pozostają poza zakresem tej korekty.

---

## 10. REGUŁA WZNOWIENIA

### 10.1 Początek każdej następnej rozmowy

Każda następna rozmowa i każde następne polecenie dla Cline **zaczyna się od lektury**:

1. `docs/00_ALCHEMIK_KANON_NAPRAWY.md`
2. `docs/ALCHEMIK_CHECKPOINT_PRACY.md`

### 10.2 Aktualizacja checkpointu

Po zakończeniu zatwierdzonego zadania **aktualizowany jest checkpoint** (`docs/ALCHEMIK_CHECKPOINT_PRACY.md`). Aktualizacja obejmuje:

- Nową datę.
- Aktualny stan Git (po wykonanym zadaniu).
- Listę zmienionych/utworzonych plików.
- Status zamrożonych obszarów.

### 10.3 Zmiana kanonu

Zatwierdzony kanon (`docs/00_ALCHEMIK_KANON_NAPRAWY.md`) zmienia się **wyłącznie po jawnej decyzji właściciela**. Cline nie może samodzielnie modyfikować kanonu.

---

## 11. STAN BIEŻĄCEJ SESJI I PLAN NASTĘPNEJ SESJI

Data: 10.08.2026

### 11.A Co zostało wykonane i pozostaje do zachowania

- Zatwierdzona semantyka trwałości jest zapisana w Kanonie i Checkpoincie:
  `CONFLICT` tylko dla tej samej tożsamości Readingu z inną treścią;
  terminalna Observation → `ValueError`;
  druga ACTIVE Observation → `ValueError`;
  brak rekordu po rollbacku kolizji → techniczny `sqlite3.IntegrityError`.
- Migracja testów 40, 41 i 45 została zatwierdzona przez właściciela i jest częścią aktualnego kontraktu.
- Trwałość Observation/Reading została zaimplementowana w `HistoryRepository` i `SQLiteHistoryRepository`, lecz integracja z RuntimeService pozostaje niewdrożona.
- Commit K6A wykonany: `ee4a918` (`fix(hunter): remove raw_input from HunterResult`).
  `raw_input` został usunięty z `HunterResult` i `HunterEngine`.
  `HunterResult` nie przenosi surowego OHLCV.
  Po commicie Git jest czysty.

### 11.B Status wyników

**Historyczne wyniki (09.08.2026):**

- 09.08.2026 właściciel niezależnie uruchomił pełny blok PowerShell w `C:\alchemik`.
- `tests/test_observation_persistence.py`: 48 passed.
- Trzy testy zgodności trwałości: 122 passed.
- Kolekcja: 1578 tests collected.
- Pełna regresja: 1578 passed, 41 subtests passed.

**Aktualny wynik referencyjny — niezależna weryfikacja właściciela z 10.08.2026:**

- `tests/test_runtime_observation_integration.py`: 22 passed.
- Trzy testy trwałości: 122 passed.
- Kolekcja: 1600 tests collected.
- Pełna regresja: 1600 passed, 41 subtests passed.
- Staging pusty przed i po testach.
- Stan Git identyczny przed i po testach.
- `git diff --check` oraz `git diff --cached --check` czyste.
- Wynik funkcjonalny jest niezależnie potwierdzony przez właściciela.
- Stan Git dla opisanego etapu pozostaje zapisany w §11.C jako historyczny snapshot.

### 11.C Faktyczny stan repozytorium — stan bezpośrednio po pierwszym commicie kodu, przed commitem dokumentacyjnym (10.08.2026)

- pierwszy ograniczony lokalny commit kodu Runtime → Observation wykonany:
  hash `fb32064795a28c28f3acb8fd1e400b2a325f9cfb`,
  komunikat `feat(runtime): persist observations before hunter`,
  zawiera dokładnie trzy pliki:
  `application/runtime.py`,
  `application/entrypoint.py`,
  `tests/test_runtime_observation_integration.py`;
- staging pusty;
- sześć plików unstaged:
  `data/models/hunter_result.py`,
  `docs/00_ALCHEMIK_KANON_NAPRAWY.md`,
  `docs/ALCHEMIK_CHECKPOINT_PRACY.md`,
  `engines/hunter/engine.py`,
  `tests/test_hunter_engine.py`,
  `tests/test_runtime.py`;
- brak plików untracked;
- repozytorium nadal NIE GREEN — istnieje 6 zmian unstaged;
- cztery pliki K6A pozostają zamrożone i niezatwierdzone architektonicznie:
  `data/models/hunter_result.py`,
  `engines/hunter/engine.py`,
  `tests/test_hunter_engine.py`,
  `tests/test_runtime.py`.

### 11.D Plan następnej sesji — obowiązująca kolejność

1. Właściciel uruchamia niezależny blok PowerShell właściwym interpreterem `.venv`:
   - dedykowany test trwałości;
   - testy zgodności trwałości;
   - `--collect-only`;
   - pełną regresję;
   - pełny audyt Git.
2. Po wklejeniu wyników właściciela wykonujemy wyłącznie końcowy audyt odczytowy:
   - pełne SHA-256;
   - dokładne linie dokumentów;
   - zgodność kodu, testów, Kanonu i Checkpointu;
   - rozdzielenie wyniku testów od GREEN repozytorium.
3. Dopiero po zaakceptowaniu niezależnej weryfikacji właściciel podejmie decyzję o dalszym porządkowaniu Git.
4. Nie rozpoczynać RuntimeService, Market Huntera, MasterEngine ani testu pionowego przed tymi trzema punktami.

---

## 12. ZATWIERDZONE DECYZJE — GRANICA RUNTIMESERVICE → TRWAŁOŚĆ

Poniższe decyzje zostały zatwierdzone przez właściciela 09.08.2026.

| # | Decyzja | Status |
|---|---------|--------|
| 1 | Jeden poprawny kandydat rynku może utworzyć jeden `InstrumentReading` wyłącznie z najnowszego dostępnego `MarketData`, określonego przez największy źródłowy `market_data_timestamp`. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 2 | Pełna lista OHLCV pobrana przez Yahoo Finance, w tym kontekst historyczny do 52 tygodni, pozostaje kontekstem analitycznym. Nie jest automatycznie zamieniana na wiele nowych Readingów podczas każdego skanu i nie jest przenoszona przez `HunterResult`. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 3 | `NO_DATA`, `SOURCE_ERROR` i timeout nie tworzą `InstrumentReading`, nie tworzą Observation oraz nie kończą aktywnej Observation. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 4 | `RuntimeService` jest właścicielem lifecycle Observation. Restore jest jawną operacją startową wykonywaną przez entrypoint przed pierwszym `run_cycle()` danej instancji RuntimeService. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 5 | Restore nie może być ukryty w konstruktorze RuntimeService i nie może być automatycznie wykonywany na początku każdego `run_cycle()`. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 6 | Pierwsza przyszła integracja Runtime z trwałością ma ograniczony zakres: poprawny kandydat ma przejść przez warstwę Observation przed Market Hunterem, lecz ta integracja nie definiuje jeszcze żadnego nowego filtra, progu, triggera, `UNKNOWN`, `CHANGED`, `NOT_TRIGGERED` ani `TRIGGERED`. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 7 | W pierwszej integracji wynik zapisu Readingu nie może samodzielnie zmienić obecnej reguły przekazywania kandydatów do Market Huntera lub MasterEngine. Kontrakt Market Hunter → MasterEngine i sposób przekazywania OHLCV nadal pozostają otwartymi decyzjami właściciela. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 8 | Dopiero po niezależnej weryfikacji tej ograniczonej integracji właściciel podejmie decyzję, jak porównanie Observation wpływa na Market Huntera i na możliwość przekazania instrumentu do MasterEngine. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |
| 9 | `CHANGED` nie jest równoznaczne z `TRIGGERED`. | Zatwierdzone architektonicznie — ograniczona implementacja Runtime → Observation utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` i funkcjonalnie zweryfikowana 10.08.2026 |

### 12.1 Podsumowanie stanu

- Decyzje są zatwierdzone architektonicznie.
- Ograniczona implementacja Runtime → Observation została utrwalona lokalnie w commicie `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` o komunikacie `feat(runtime): persist observations before hunter` i funkcjonalnie zweryfikowana przez niezależną weryfikację właściciela 10.08.2026.
- Pierwszy commit kodu zawiera dokładnie trzy pliki: `application/runtime.py`, `application/entrypoint.py`, `tests/test_runtime_observation_integration.py`.
- Nie zmieniono kontraktu Market Hunter → MasterEngine.

---

## 13. BLOKADA KOREKTY RUNTIME → OBSERVATION I ZATWIERDZONY PLAN

Data: 09.08.2026 | Status: **Wykonane i zweryfikowane 10.08.2026**

### 13.A Historyczny stan bieżący

- Cline wykrył, że dotychczasowa persistencja Readingu została umieszczona po `hunter_engine.scan(candidates)`, a więc nie spełnia zatwierdzonej kolejności `Scanner → Observation → Hunter → MasterEngine`.
- Cline wykrył, że `application/entrypoint.py` nie zawierał na dysku jawnego wywołania `runtime.restore_active_observations()` między `build_runtime_service()` i `runtime.run_cycle()`.
- Dedykowany test kontraktu kolejności nie osiągnął GREEN: raport Cline wskazał `1 FAILED, 21 passed`.
- Raport Cline równocześnie podał pełną regresję `1590 passed`, co jest niespójne z porażką testu należącego do tej samej kolekcji. Wynik nie jest akceptowany ani zweryfikowany przez właściciela.
- Bieżące zmiany Runtime i testu pozostają zamrożone, niezatwierdzone i nie mogą być commitowane.

### 13.B Cztery zatwierdzone kroki korekty — WYKONANE

1. ✅ **Test kolejności** — wykonany. Test używa analizy AST rzeczywistych wywołań w `RuntimeService.run_cycle()`, dowodząc kolejności `persist Observation → hunter_engine.scan(candidates)`.

2. ✅ **Weryfikacja stanu Git i entrypointu** — wykonana. Potwierdzono faktyczny stan Git oraz faktyczną zawartość `application/entrypoint.py`. Produkcyjna kolejność startupu: `build_runtime_service() → runtime.restore_active_observations() → runtime.run_cycle()`.

3. ✅ **Testy SOURCE_ERROR i timeout** — wykonane. Używają wyłącznie dopuszczalnego test double granicy Yahoo / ScanProvider. Dowodzą, że nie powstaje Reading ani Observation i że ACTIVE Observation nie zostaje zmieniona. Nie zaprojektowano nowej polityki obsługi błędów.

4. ✅ **Kryteria funkcjonalnej weryfikacji spełnione** — 0 failed w dedykowanym pliku testowym; spójny wynik pełnej regresji (1600 passed, 41 subtests passed); pełny niezależny blok PowerShell wykonany przez właściciela 10.08.2026; osobny audyt Git potwierdzony.

Repozytorium nadal NIE GREEN, ponieważ working tree nie jest czysty.

### 13.C Zakres — zrealizowany

- wyłącznie `application/runtime.py`, `application/entrypoint.py` i istniejący `tests/test_runtime_observation_integration.py`;
- bez zmian Kanonu, modeli, repozytoriów trwałości, Market Huntera, MasterEngine, K6A, AI, Tavily, Telegrama, triggerów i selekcji;
- pierwszy ograniczony lokalny commit kodu wykonany: `fb32064795a28c28f3acb8fd1e400b2a325f9cfb` (`feat(runtime): persist observations before hunter`); weryfikacja zakończona pomyślnie.

---

## KONIEC DOKUMENTU

Data utworzenia: 08.08.2026
Data aktualizacji: 10.08.2026
Status: Decyzje właściciela (pkt 1–6 zadania) zatwierdzone i zapisane w Kanonie (§12) oraz Checkpoincie (§8) 08.08.2026. Commit trwałości i dokumentacji wykonany 09.08.2026. Granica RuntimeService → trwałość (§12) zatwierdzona 09.08.2026. Commit K6A usunięcia `raw_input` wykonany 10.08.2026. Repozytorium nie jest deklarowane jako GREEN w tym zadaniu dokumentacyjnym. Sekcja §11 zaktualizowana 10.08.2026. Sekcja §13 — blokada korekty Runtime → Observation i zatwierdzony plan — dodana 09.08.2026.

Checkpoint odzwierciedla zatwierdzone decyzje właściciela i stan projektu na dzień aktualizacji.
