# ALCHEMIK — STEP 7 AKCEPTACJA I PLAN KROKU 8

**Status: STEP7_ACCEPTANCE_DOCUMENTED_READY_FOR_CHECKPOINT**
Data utworzenia: 2026-08-24 (Europe/Berlin, UTC+2)
Zakres: trwałe zamknięcie Kroku 7 oraz plan Kroku 8

---

## 1. Potwierdzone warunki startowe (przed zmianą)

| Warunek | Wynik |
|---|---|
| Katalog roboczy | `C:\alchemik` |
| Branch | `master` |
| HEAD | `cf8bc437c20e32fa4a47d8bc3090f9af51f4d844` |
| `git status --porcelain` | pusty |
| Staging (łączny wynik wg reguły 16: `--cached --raw`, `--cached --name-status`, `--cached --stat`, `--cached --quiet`) | czysty (`git diff --cached --quiet` — exit 0) |
| Produkcyjna baza `data\runtime\alchemik_runtime.db` (Get-Item / Get-FileHash / Test-Path) | istnieje; rozmiar 2 355 200 B; SHA-256 `C17B8485EF9593DC5CB771E53D4B80897BB7B1BA285CE82A9CD8C7CAB0B6FE53` |
| Sidecary `-wal` / `-shm` przy bazie produkcyjnej | brak (Test-Path: WAL_EXISTS=False, SHM_EXISTS=False) |
| SQLite na produkcyjnej bazie | zakazany — nie uruchamiano |

---

## 2. Potwierdzone fakty Kroku 7

Fakty oznaczone jako potwierdzone przez właściciela w zleceniu z 2026-08-24 oraz udokumentowane w końcowych raportach i artefaktach z katalogów `%TEMP%`.

### 2.1 Checkpointy Git Kroku 7

| Skrót | Komunikat |
|---|---|
| `74f3606...` | 7C: timeframe/1h migration, candle lifecycle, baseline per timeframe i kontrolowana walidacja E2E |
| `a76a9f0...` | 7F: fix controlled 1h overlay anchor and trace semantics |
| `cf8bc43...` | 7: persist sanitized controlled validation trace (HEAD) |

### 2.2 Regresja testów

- Pełna regresja: **2027 passed + 41 subtests** (fakt potwierdzony przez właściciela w zleceniu).

### 2.3 Realny pipeline Yahoo → RuntimeService → SQLite (przebiegi 7E i 7F)

- Przebieg `alchemik_step7e_real_run_20260822`:
  - `step7e_exit_code.txt` = `0`;
  - `step7e_stdout.txt` = `STATUS: COMPLETE_E2E`, `TRACE overall: SUCCESS`;
  - `MARKER_EXISTS=True` w `step7e_post_run_summary.txt`;
  - izolowana baza: 2 482 176 B, SHA-256 `D3FA72629DF57317E310F1158F2570220D9C066F60FFDA1BC70800D00774E100`.
- Przebieg `alchemik_step7f_corrected_real_run_20260824`:
  - `step7e_exit_code.txt` = `0`;
  - `step7e_stdout.txt` = `STATUS: COMPLETE_E2E`, `TRACE overall: SUCCESS`;
  - `MARKER_EXISTS=True` w `step7e_post_run_summary.txt`;
  - izolowana baza: 2 490 368 B, SHA-256 `5214CAD7B6D9E8E1E53C45043381A74BEC30BF771BD2FF101C33D0F5FC31CFE9`.
- Potwierdzone fakty przebiegu (przez właściciela w zleceniu): realne dane Yahoo → RuntimeService → SQLite na izolowanej kopii; poprawne stany **OPEN/CLOSED świecy 1h**; poprawna **kotwica poprzedniej zamkniętej świecy CLOSED 1h**; **naturalny stop: `candidates=0` bez MarketEvent**; wewnętrzny pełny pipeline potwierdzony offline (**COMPLETE_E2E**, `TRACE overall: SUCCESS`).

### 2.4 Rzeczywiste granice zewnętrzne (attempt2, przebieg 2026-08-24T15:55:08–15:55:22 UTC)

Źródło: `%TEMP%\alchemik_step7_external_boundaries_attempt2_ready_20260824\STEP7_EXTERNAL_BOUNDARIES_ATTEMPT2_RESULT.md` oraz `%TEMP%\alchemik_step7_external_boundaries_attempt2_run_20260824\alchemik_step7_external_boundaries_attempt2_result.json`.

| Granica | Status | attempts | real_sent | Dowód kontraktowy |
|---|---|---|---|---|
| Tavily | **PASS** | 1 | 1 | `results_count=19`; poprawna odpowiedź kontraktowa (bez pełnej treści) |
| OpenAI | **PASS** | 1 | 1 | `model=gpt-4o`; odpowiedź zgodna z kontraktem (pełna treść nie publikowana) |
| Telegram | **PASS** | 1 | 1 | `successful_channels=[GuardedTelegramChannel]`; `final_message_hash=911cf798e16c93be7a75333969d73d4441126ab18b08790ea07e0183affc356d`; dokładnie jeden pełny prefiks kontrolny, „TECHNICZNY TEST ŁĄCZNOŚCI", „TO NIE JEST SYGNAŁ INWESTYCYJNY" |

- Kolejność: `tavily, openai, telegram`; `process_runs=1`; `overall_status=PASS`.
- Brak sekretów w stdout, stderr i artefaktach (`NO_SECRET_PATTERNS_IN_ATTEMPT2_ARTIFACTS`).
- Właściciel potwierdził odebranie kontrolnej wiadomości Telegram (potwierdzenie właściciela w zleceniu).
- Warstwowa akceptacja (overlay kontrolowany) **nie była naturalnym sygnałem inwestycyjnym** — zgodnie z kanonem (`TO NIE JEST SYGNAŁ INWESTYCYJNY`).
- Wynik raportu: `STEP7_EXTERNAL_BOUNDARIES_ACCEPTED_READY_FOR_VPS`.

### 2.5 Produkcyjna baza — zachowanie treści

- Baza produkcyjna zachowała identyczną treść: rozmiar 2 355 200 B, SHA-256 `C17B8485EF9593DC5CB771E53D4B80897BB7B1BA285CE82A9CD8C7CAB0B6FE53`, brak WAL/SHM; nie otwierana przez SQLite (audyt attempt2, 2026-08-24).

### 2.6 Incydent proceduralny SQLite i zamrożona reguła

- Podczas audytu przebiegu 7F wykonano read-only połączenie SQLite do produkcyjnej bazy; SQLite utworzył sidecary `-wal` (0 B) i `-shm` (32 768 B); sidecary usunięto; główny plik pozostał bitowo identyczny; naruszono procedurę kontroli bazy.
- **Zamrożona reguła:** produkcyjną bazę kontrolujemy wyłącznie metrykami pliku (`Get-Item`, `Get-FileHash`, `Test-Path`). Wszystkie zapytania SQLite, `PRAGMA`, `integrity_check`, `foreign_key_check` i liczniki wykonujemy wyłącznie na świeżej bitowej kopii poza repozytorium. Bezwzględny zakaz otwierania produkcyjnej bazy przez `sqlite3`, repository, `PRAGMA` lub jakikolwiek connection string.

---

## 3. Manifest niesekretnych artefaktów i finalne SHA

| Artefakt | SHA-256 | Źródło |
|---|---|---|
| External harness (`alchemik_step7_external_boundaries_once.py`, attempt2) | `f86ff4600af21b1c8447b1f0da94616d0c583887f8d2ce318c99e3a1dc2bf0e3` | plik `alchemik_step7_external_boundaries_attempt2_once.sha256` |
| Secrets bridge (`LOAD_SECRETS_AND_RUN_EXTERNAL_ACCEPTANCE_ONCE.py`, attempt2) | `0f28c1a4a52776b778aa1c9018fdc40d6ded693b12d519cacff1bd0effe02194` | plik `LOAD_SECRETS_AND_RUN_EXTERNAL_ACCEPTANCE_ONCE.sha256` |
| Finalna wiadomość Telegram (hash treści kontrolnej) | `911cf798e16c93be7a75333969d73d4441126ab18b08790ea07e0183affc356d` | `alchemik_step7_external_boundaries_attempt2_result.json` |

Zasady: nie kopiowano `response_id`, kluczy ani treści odpowiedzi usług. Sekrety nie są częścią niniejszego dokumentu ani artefaktów repo.

---

## 4. Plan Kroku 8

Krok 8 jest planowany etapami. Dla każdego etapu podano: cel, warunek wejścia, dowód zakończenia, rollback i zakazy. Parametry VPS i domena **nie są wybierane w tym dokumencie** — wymagają osobnej decyzji właściciela.

### Etap 8.1 — Checkpoint dokumentu i zabezpieczenie kodu

- **Cel:** zamrożenie stanu Kroku 7 w repozytorium (checkpoint) oraz utrwalenie niniejszego dokumentu akceptacji; przygotowanie czystej, odtwarzalnej bazy kodu pod kolejne etapy.
- **Warunek wejścia:** zatwierdzenie niniejszego dokumentu przez właściciela; Git czysty; HEAD zgodny z `cf8bc437c20e32fa4a47d8bc3090f9af51f4d844`; brak niezamkniętych zadań Kroku 7.
- **Dowód zakończenia:** pełny unified diff dokumentu pokazany właścicielowi; staging zawiera wyłącznie zatwierdzony zakres; commit checkpoint po jawnej zgodzie właściciela; `git status` czysty; brak zmian poza zakresem.
- **Rollback:** brak zmian kodowych w tym etapie — rollback oznacza brak commita przy braku zgody właściciela.
- **Zakazy:** bez `git push`; bez zmian kodu; bez scalania niezatwierdzonych zmian; bez nowych testów; bez otwierania produkcyjnej bazy.

### Etap 8.2 — Bitowa kopia, rollback i kontrolowana migracja produkcyjnej bazy

- **Cel:** uzyskanie bitowej kopii produkcyjnej bazy poza repozytorium; wdrożenie procedury rollback; przeprowadzenie ewentualnej migracji schematu wyłącznie na świeżej kopii poza repo, a następnie kontrolowane zastosowanie na produkcyjnej bazie po jawnej zgodzie właściciela.
- **Warunek wejścia:** Etap 8.1 zamknięty; właściciel zatwierdził zakres migracji; wykonano bitową kopię i zweryfikowano jej SHA z bazą źródłową; brak procesów ALCHEMIKA zapisujących do bazy.
- **Dowód zakończenia:** bitowa kopia poza repo z potwierdzonym rozmiarem i SHA; test migracji na kopii (zapytania i `PRAGMA` wyłącznie na kopii); porównanie manifestu domenowego przed/po na kopii; brak WAL/SHM przy kopii po zamknięciu; produkcyjna baza po migracji ma nowy, zapisany SHA i rozmiar; rollback przetestowany z kopii na bazie testowej.
- **Rollback:** przywrócenie bitowej kopii na miejsce bazy produkcyjnej i ponowna weryfikacja SHA; procedura opisana i przetestowana przed migracją produkcyjną.
- **Zakazy:** zakaz otwierania produkcyjnej bazy przez SQLite/`PRAGMA` (wyłącznie metryki pliku); zakaz migracji bez jawnej zgody właściciela; zakaz kasowania kopii; zakaz `git push`; zakaz migracji na działającym schedulerze.

### Etap 8.3 — Scheduler 15 minut + CycleLock

- **Cel:** uruchomienie cyklicznego monitorowania świecy 1h co 15 minut z wyłącznością wykonania (CycleLock) i jawnym zapisem cykli (CycleTrace) na osobnej kopii bazy.
- **Warunek wejścia:** Etap 8.2 zamknięty; scheduler działa na osobnej kopii bazy; CycleLock zweryfikowany w testach; kontrakt trajektorii 1h (kanon §14.8) obowiązujący.
- **Dowód zakończenia:** scheduler wywołuje `run_cycle()` co 15 minut (logi); CycleLock zapobiega równoległemu uruchomieniu (test + obserwacja logów); CycleTrace zapisuje komplet śladów; brak nakładania się cykli; baza osobnej kopii rośnie zgodnie z kontraktem; brak MarketEvent przy naturalnym stopie.
- **Rollback:** zatrzymanie schedulera; przywrócenie poprzedniej konfiguracji z backupu; brak zmian w produkcyjnej bazie.
- **Zakazy:** zakaz uruchamiania schedulera bez CycleLock; zakaz zapisu do produkcyjnej bazy przed Etapem 8.2; zakaz wysyłki Telegrama bez naturalnych bramek; zakaz pracy na bazie produkcyjnej bez kopii.

**Zatwierdzona realizacja schedulera 15 minut (po decyzji właściciela z 2026-08-24, korekta kontraktu po `STOP_STEP8_3_CYCLELOCK_CONTRACT_GAP`):**

- **Podział odpowiedzialności:** `RuntimeService.run_cycle()` pozostaje jedynym właścicielem przejęcia i zwolnienia `CycleLock` (dekorator `_cycle_lock_guard`). Scheduler nie otrzymuje i nie przejmuje `CycleLock`. Scheduler wywołuje wyłącznie publiczne, już chronione `run_cycle()`.
- **Pierwszy cykl:** wykonywany natychmiast po uruchomieniu schedulera (przed pierwszym oczekiwaniem).
- **Interwał produkcyjny:** dokładnie 900 sekund (15 minut); kolejne próby rozpoczynają się dopiero 900 sekund po zakończeniu poprzedniej próby; oczekiwanie jest przerwalne (`_stop_event.wait(900)`), bez `time.sleep(900)`.
- **Zajęty CycleLock:** chronione `run_cycle()` zgłasza `CycleAlreadyRunningError`; scheduler mapuje go na jawny status `SKIPPED_OVERLAP`; `run_cycle()` nie jest wywoływane ponownie przed upływem oczekiwania; brak kolejki, retry, catch-up i nadrabiania pominiętych cykli.
- **Sukces:** jawny status `EXECUTED`; blokada jest zwalniana przez `_cycle_lock_guard` w `finally` (także po wyjątku).
- **Błąd cyklu:** pojedynczy błąd nie kończy całej usługi; scheduler rejestruje go bez sekretów (status `CYCLE_ERROR` przy `continue_on_error=True`) i przechodzi do oczekiwania 900 sekund; brak natychmiastowego retry.
- **Brak równoległości:** maksymalnie jeden aktywny `RuntimeService.run_cycle()` — gwarancja przez istniejący `_cycle_lock_guard` na `run_cycle()` (nie przez scheduler).
- **Graceful stop:** `stop()` ustawia zdarzenie; zatrzymanie podczas oczekiwania kończy pętlę bez uruchamiania kolejnego cyklu; `SIGTERM` oraz `KeyboardInterrupt` wywołują `scheduler.stop()`.
- **Uruchomienie:** jawne przez `python -m application.entrypoint --scheduler` (tryb blokujący, proces nie kończy się po utworzeniu wątku). Uruchomienie bez flagi `--scheduler` zachowuje dotychczasową semantykę pojedynczego cyklu.

### Etap 8.4 — Lokalny backend API i dashboard na osobnej kopii bazy

- **Cel:** udostępnienie lokalnego backendu API (read-only względem osobnej kopii bazy) oraz dashboardu (frontend) do podglądu cykli, śladów i zdarzeń — bez zapisu do bazy produkcyjnej.
- **Warunek wejścia:** Etap 8.3 zamknięty; osobna kopia bazy zawiera dane z realnych cykli; interfejs API zdefiniowany i zatwierdzony; dashboard działa lokalnie.
- **Dowód zakończenia:** lokalny backend odpowiada na endpointy read-only; dashboard renderuje dane z osobnej kopii; testy API przechodzą; brak zapisów do bazy produkcyjnej (metryki pliku bez zmian); dokumentacja API zaktualizowana.
- **Realizacja Kroku 8.4B (same-origin proxy):** frontend używa wyłącznie względnego prefiksu `/api/v1` i osobnej trasy `/health`; lokalny Vite `server.proxy` oraz `preview.proxy` przekazują `/api` oraz `/health` do lokalnego FastAPI **bez rewrite** (backend otrzymuje pełne `/api/v1/...`); target proxy pochodzi z niesekretnej zmiennej `ALCHEMIK_API_PROXY_TARGET` (domyślnie `http://127.0.0.1:8000`) i nie trafia do produkcyjnego bundle; produkcyjnie `/api` zostanie obsłużone przez Nginx; backend pozostaje bez CORS; żaden adres localhost nie jest zaszyty w produkcyjnym bundle.
- **Rollback:** zatrzymanie lokalnego backendu/dashboardu; przywrócenie wcześniejszej wersji bez wpływu na bazę i scheduler.
- **Zakazy:** zakaz endpointów zapisujących do bazy produkcyjnej; zakaz udostępniania sekretów przez API; zakaz wdrożenia backendu poza lokalną maszyną przed Etapem 8.5; zakaz `git push`.

### Etap 8.5 — Hetzner, sekrety procesowe, systemd, domena i HTTPS

- **Cel:** przygotowanie środowiska docelowego: VPS (parametry wybierze właściciel), sekrety dostępne wyłącznie jako zmienne procesowe (bez plików sekretów w repo), usługi systemd dla workera/backend/frontend, domena (wybór właściciela) i HTTPS.
- **Warunek wejścia:** Etap 8.4 zamknięty; właściciel wybrał parametry VPS i domenę; procedury backupu i restartu opisane; sekrety przygotowane poza repo.
- **Dowód zakończenia:** maszyna VPS skonfigurowana; usługi systemd działają i restartują się po awarii; dostęp HTTPS działa na domenie (certyfikat ważny); sekrety niewidoczne w procesach poza zmiennymi środowiskowymi; brak sekretów w repo i logach; test dostępu z zewnątrz.
- **Rollback:** powrót do lokalnego backendu/dashboardu z Etapu 8.4; wyłączenie usług systemd; przywrócenie poprzedniej domeny/HTTPS przy problemach.
- **Zakazy:** zakaz wyboru parametrów VPS/domeny bez decyzji właściciela; zakaz zapisu sekretów do repo/logów; zakaz uruchamiania workera bez CycleLock; zakaz bezpośredniego dostępu do produkcyjnej bazy przez internet.

### Etap 8.6 — Etapowe wdrożenie worker/backend/frontend

- **Cel:** wdrożenie w kolejności: worker (scheduler + cycle), backend API, frontend dashboard — każdy etap osobno weryfikowany na środowisku docelowym; pełne uruchomienie produkcyjnego pipeline.
- **Warunek wejścia:** Etap 8.5 zamknięty; wszystkie komponenty działają lokalnie; testy akceptacyjne wykonane; właściciel zatwierdził kolejność i zakres wdrożenia.
- **Dowód zakończenia:** worker działa na VPS i zapisuje cykle do docelowej bazy (metryki pliku + logi); backend API odpowiada na domenie; frontend dashboard dostępny przez HTTPS; monitoring potwierdza brak błędów; rollback każdego etapu przetestowany.
- **Rollback:** zatrzymanie ostatnio wdrożonego komponentu i przywrócenie poprzedniego stanu (kolejność odwrotna do wdrożenia); przywrócenie bazy z bitowej kopii w razie potrzeby.
- **Zakazy:** zakaz wdrażania dwóch komponentów naraz; zakaz wdrożenia bez testów akceptacyjnych; zakaz wysyłki Telegrama bez naturalnych bramek; zakaz `git push` bez osobnej zgody; zakaz modyfikacji produkcyjnej bazy bez kopii i rollbacku.

### Etap 8.7 — Monitoring, backup, restart resilience i dowód pierwszego naturalnego sygnału

- **Cel:** ciągły monitoring (logi, metryki, alerty), regularny backup, odporność na restarty oraz późniejszy dowód pierwszego naturalnego sygnału inwestycyjnego (MarketEvent bez overlayu kontrolnego).
- **Warunek wejścia:** Etap 8.6 zamknięty i stabilny; monitoring i backup skonfigurowane; procedury restartu przetestowane.
- **Dowód zakończenia:** monitoring działa przez założony okres obserwacji; backup wykonany i zweryfikowany (SHA kopii); restart workera po awarii automatyczny; pierwszy naturalny sygnał udokumentowany (pełny łańcuch: Yahoo → Readingi 1h → detekcja → AI → Telegram z oznaczeniami naturalnymi); brak wątpliwości co do naturalności sygnału.
- **Rollback:** przywrócenie ostatniego dobrego backupu; zatrzymanie workera; powrót do Etapu 8.6 przy powtarzających się awariach.
- **Zakazy:** zakaz uznania sygnału za naturalny bez pełnego łańcucha dowodów; zakaz wysyłki Telegrama bez naturalnych bramek; zakaz pracy bez backupu; zakaz `git push` bez osobnej zgody właściciela.

---

## 5. Reguły obowiązujące dla całego Kroku 8

- Produkcyjna baza: wyłącznie metryki pliku (`Get-Item`, `Get-FileHash`, `Test-Path`); zapytania SQLite i `PRAGMA` wyłącznie na świeżej bitowej kopii poza repozytorium.
- Brak operacji Git bez jawnej zgody właściciela (`git add`, `git commit`, `git push`, `git reset`, `git restore`, `git checkout` i inne wg reguły 22).
- Brak sieci, testów i migracji bez jawnego polecenia właściciela — chyba że etap Kroku 8 wyraźnie tego wymaga i został zatwierdzony.
- Sekrety wyłącznie jako zmienne procesowe; nigdy w repo, logach ani artefaktach.
- Nie wybrano parametrów VPS ani domeny — decyzje należą do właściciela.
- Wewnętrzne komponenty ALCHEMIKA nie mogą być zastępowane mockami; mocki wyłącznie na granicach systemu (Yahoo Finance, Tavily, dostawca AI).

---

## 6. Audyt końcowy bieżącego zadania

- Utworzono dokładnie jeden plik: `docs/ALCHEMIK_STEP7_AKCEPTACJA_I_PLAN_KROKU8_2026-08-24.md`.
- Jedyną zmianą w repozytorium jest nowy dokument; staging pusty.
- Bez sieci, testów, SQLite na produkcyjnej bazie oraz bez `git add`/`git commit`/`git push`.
- Dokument zapisany jako UTF-8 bez BOM; brak znaków NUL; brak trailing whitespace; zweryfikowano pełny diff przed zakończeniem.
- Status końcowy: **STEP7_ACCEPTANCE_DOCUMENTED_READY_FOR_CHECKPOINT**.