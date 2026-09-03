# ALCHEMIK — AKTUALNY STAN I PLAN DALSZEJ BUDOWY

**Wersja:** 1.0  
**Data:** 2026-09-02  
**Status:** OWNER_APPROVED — aktualny checkpoint projektu  
**Projekt:** `C:\Alchemik`  
**Repozytorium:** `https://github.com/medevil100/Alchemik.git`  
**Branch:** `main`  
**HEAD:** `8f773bbeed915ba38531bd3f0a1a79f3ce26c79e`

---

## 1. Cel dokumentu

Dokument utrwala faktyczny stan ALCHEMIKA na koniec 2026-09-02 oraz kolejność dalszych prac.

Jest punktem wznowienia pracy na następny dzień.

Dokument:

- nie zmienia kodu;
- nie zatwierdza zmian niewymienionych wprost;
- nie zastępuje testów ani rzeczywistego przebiegu;
- oddziela elementy potwierdzone od elementów wymagających audytu lub decyzji właściciela;
- uwzględnia docelową pracę ALCHEMIKA przez 24 godziny na dobę i 7 dni w tygodniu na VPS Hetzner.

---

## 2. Zasady zarządzania projektem

| Obszar | Zasada |
|---|---|
| Właściciel | Właściciel projektu podejmuje wszystkie decyzje i wyznacza kierunek. |
| Asystent | Analizuje, przedstawia rozwiązania i przygotowuje polecenia. |
| Cline | Wykonuje wyłącznie zakres zatwierdzony przez właściciela. |
| Zmiany | Każda zmiana kodu, dokumentacji, środowiska lub Git wymaga wcześniejszej zgody właściciela. |
| Brak decyzji | Jeżeli brakuje informacji, należy zapytać zamiast przyjmować własne założenie. |
| Zakres zadania | Jedno zadanie obejmuje jeden jasno określony zakres. |
| Aktywne zadanie | Nie doklejamy dodatkowych poleceń do trwającego zadania Cline. |
| Weryfikacja | Testy, stan repozytorium i rzeczywisty przepływ są oceniane oddzielnie. |
| GREEN | Sam wynik testów nie wystarcza do uznania repozytorium za GREEN. |
| Git | Bez `git add`, `git commit` i `git push` bez osobnej zgody właściciela. |

---

## 3. Jedyny aktywny projekt

| Element | Aktualna wartość |
|---|---|
| Katalog projektu | `C:\Alchemik` |
| Repozytorium GitHub | `medevil100/Alchemik` |
| Branch | `main` |
| HEAD | `8f773bbeed915ba38531bd3f0a1a79f3ce26c79e` |
| Origin | `https://github.com/medevil100/Alchemik.git` |
| Środowisko | `C:\Alchemik\.venv` |
| Interpreter | `C:\Alchemik\.venv\Scripts\python.exe` |
| Python | `3.13.13` |
| Baza runtime | `C:\Alchemik\data\runtime\alchemik_runtime.db` |

Nie obowiązują wcześniejsze katalogi robocze:

- `C:\alchemia`;
- `C:\Alchemik_audyt_GitHub`.

Dalsza praca dotyczy wyłącznie `C:\Alchemik`.

---

## 4. Środowisko Python

Utworzono jedno środowisko projektu:

`C:\Alchemik\.venv`

Potwierdzony interpreter:

`C:\Alchemik\.venv\Scripts\python.exe`

Potwierdzona wersja:

`Python 3.13.13`

Do środowiska zainstalowano:

- pełny zestaw zależności z `requirements.txt`;
- `pytest`, którego nie było w `requirements.txt`.

Pełna kolekcja testów działa w tym środowisku.

Polecenia Python, pip i pytest muszą jawnie używać interpretera projektu. Aktywna etykieta Conda `base` w terminalu nie zmienia używanego interpretera, jeżeli polecenie wskazuje pełną ścieżkę do `C:\Alchemik\.venv\Scripts\python.exe`.

---

## 5. Stan Git

Repozytorium posiada dwie niestage'owane zmiany:

| Status | Plik | Cel zmiany |
|---|---|---|
| `M` | `application/sqlite_history_repository.py` | Dodanie `db_path` do `get_storage_summary()` i aktualizacja docstringa. |
| `M` | `tests/test_sqlite_history_repository.py` | Test obecności, typu i wartości `db_path`. |

Potwierdzony stan:

- staging: pusty;
- pliki nieśledzone: brak;
- konflikty: brak;
- nie wykonano commit ani push dotyczących tej poprawki.

Zmiany pozostają robocze do osobnej decyzji właściciela.

---

## 6. Naprawa `KeyError: 'db_path'`

### Zakres wykonanej zmiany

W `SQLiteHistoryRepository.get_storage_summary()` dodano:

`"db_path": str(self.db_path)`

Docstring został ujednolicony z rzeczywistym wynikiem metody:

- `db_path`;
- `journal_mode`;
- `schema_version`.

Test sprawdza:

- obecność klucza `db_path`;
- typ `str`;
- zgodność wartości z rzeczywistą ścieżką repozytorium.

### Potwierdzenie testowe

| Kontrola | Wynik |
|---|---|
| Test `get_storage_summary()` | `1 passed` |
| Testy `test_sqlite_history_repository.py` | `25 passed` |
| Pełna kolekcja | `2050 tests collected` |
| Pełna regresja | `2050 passed` |
| Subtesty | `41 passed` |
| Błędy | `0` |

### Potwierdzenie rzeczywistym przebiegiem

Końcowe logowanie wykonało się prawidłowo:

`Storage: 4 cycles, 29 MarketEvents in data\runtime\alchemik_runtime.db`

`KeyError: 'db_path'` nie wystąpił.

Naprawa jest potwierdzona funkcjonalnie i pełną regresją. Pozostaje niezatwierdzona w Git.

---

## 7. Potwierdzony rzeczywisty przepływ

Wykonano rzeczywisty cykl produkcyjnego entrypointa:

`C:\Alchemik\.venv\Scripts\python.exe -m application.entrypoint`

Potwierdzony wynik:

| Element | Wynik |
|---|---|
| RuntimeService | Uruchomiony |
| Yahoo Finance | Odpowiedziało |
| Kandydaci | `10` |
| Sukcesy | `10` |
| Błędy | `0` |
| Zdarzenia rynkowe | Utworzone przez rzeczywiste detektory |
| SQLite | Zapis wykonany |
| Stan storage po cyklu | `4 cycles`, `29 MarketEvents` |

Przebieg potwierdził rzeczywistą ścieżkę:

`Yahoo → RuntimeService → detektory → SQLite`

Nie ma podstaw do uznania, że Yahoo jest niedostępne. Wcześniejsze raporty Cline o braku dostępu do Yahoo wynikały z limitu obserwacji procesu i nie zawierały dowodu błędu Yahoo.

---

## 8. Drugi cykl z załadowanymi sekretami

Sekrety znajdują się w globalnym pliku Streamlit:

`C:\Users\szela\.streamlit\secrets.toml`

Potwierdzone nazwy konfiguracji:

- `OPENAI_API_KEY`;
- `TAVILY_API_KEY`;
- klucz tokena Telegramu;
- `TELEGRAM_CHAT_ID`.

Wartości sekretów nie mogą być zapisywane w dokumentacji, logach ani repozytorium.

Wykonano kolejny rzeczywisty cykl po załadowaniu sekretów wyłącznie do pamięci procesu:

| Element | Wynik |
|---|---|
| RuntimeService | Uruchomiony |
| Cykl | Zakończony |
| Kandydaci | `0` |
| Sukcesy | `0` |
| Błędy | `0` |
| Storage | `5 cycles`, `29 MarketEvents` |
| `KeyError` | Nie wystąpił |

Ponieważ cykl nie przekazał żadnego kandydata dalej:

- Tavily nie zostało potwierdzone w tym cyklu;
- OpenAI nie zostało potwierdzone w tym cyklu;
- Telegram nie został potwierdzony w tym cyklu;
- liczba MarketEvents pozostała bez zmian.

Nie wolno określać tego cyklu jako pełnego potwierdzenia Yahoo → Tavily → OpenAI → Telegram.

---

## 9. Universe i zapisane instrumenty

Odczyt przez `SQLiteHistoryRepository.get_current_universe()` potwierdził:

| Element | Wynik |
|---|---|
| Liczba instrumentów | `169` |
| Status instrumentów | `ACTIVE` |
| Chart | `SUCCESS` |
| `last_reading_id` | Obecny dla każdego instrumentu |
| Baseline | `PENDING_BASELINE` dla wszystkich 169 instrumentów |

Instrumenty są przechowywane w:

- `universe_snapshots`;
- `universe_instruments`;
- `universe_snapshot_members`.

Trwałe są obecnie:

- ticker;
- status instrumentu;
- status Chart;
- diagnostyka liczby świec;
- status baseline;
- identyfikator ostatniego odczytu;
- `first_seen_at`;
- `last_seen_at`.

### Potwierdzone braki danych universe

| Pole | Aktualny stan |
|---|---|
| Nazwa spółki | Nie jest zapisywana |
| Cena Discovery | `regular_market_price` zapisywane jako `None` |
| `quote_type` | Wpisane na stałe `EQUITY` |
| `exchange` | Wpisane na stałe `WSE` |
| `market` | Wpisane na stałe `pl_market` |
| `currency` | Wpisane na stałe `PLN` |

Nie wolno traktować wartości wpisanych na stałe jako rzeczywistych danych otrzymanych z Yahoo.

---

## 10. Nierozstrzygnięte problemy

### 10.1 Baseline

Wszystkie 169 instrumentów ma status:

`PENDING_BASELINE`

Wymaga ustalenia:

- czy baseline nie jest tworzony;
- czy baseline jest tworzony, ale status nie jest aktualizowany;
- czy istnieje przerwanie pomiędzy InstrumentReading i InstrumentObservation;
- czy stan zostaje prawidłowo odtworzony po restarcie.

Bez rozstrzygnięcia tego punktu nie można uznać matrycy produkcyjnej za kompletną.

### 10.2 Aktualizacja `last_seen_at`

Odczyt universe wskazał `last_seen_at` kończący się na wcześniejszym cyklu, mimo wykonania późniejszych cykli.

Wymaga ustalenia:

- czy każdy pełny Discovery tworzy snapshot;
- czy pusty wynik kandydatów pomija zapis snapshotu;
- czy `last_seen_at` jest aktualizowane dla wszystkich aktywnych instrumentów;
- czy ścieżka standardowa i produkcyjna zapisują różny zakres danych.

### 10.3 Znaczenie `0 candidates`

Aktualne raporty nie dają jednego potwierdzonego wyjaśnienia wyniku `0 candidates`.

Możliwe przyczyny muszą zostać ustalone na podstawie kodu i diagnostyki rzeczywistego cyklu. Nie wolno uznawać bez dowodu, że oznacza to brak instrumentów albo błąd Yahoo.

### 10.4 Pełny przepływ zewnętrzny

Nie został w bieżącej sesji potwierdzony pełny przebieg:

`Yahoo → Tavily → OpenAI → Telegram`

Wymaga potwierdzenia na rzeczywistym zdarzeniu bez sztucznego wymuszania kandydata.

### 10.5 Placeholder AI

Audyt statyczny wykazał ścieżkę `DecisionEngine.process_event()`, która może zwrócić `AISignal` z `confidence=0.0`, gdy rzeczywisty provider OpenAI nie jest dostępny.

Należy odróżnić:

- jawny status niedostępności AI;
- rzeczywistą analizę OpenAI;
- sztuczny wynik udający analizę.

Zmiana zachowania wymaga osobnej decyzji właściciela.

### 10.6 Mocki i fake'i

Mocki oraz fake'i nadal istnieją w testach, w tym na granicach Yahoo, Tavily i przepływów E2E.

Nie zostały użyte w potwierdzonym rzeczywistym cyklu Yahoo → RuntimeService → detektory → SQLite.

Przed ich usunięciem wymagany jest pełny audyt:

- gdzie występują;
- które testy chronią;
- które zastępują wyłącznie zewnętrzną granicę;
- które maskują niedziałający wewnętrzny przepływ;
- czym zostaną zastąpione bez utraty pokrycia regresyjnego.

Nie usuwamy ich zbiorczo bez analizy wpływu na cały projekt.

### 10.7 Brak odczytu universe przez API

Istnieją metody repozytorium:

- `get_current_universe()`;
- `get_latest_snapshot()`;
- `get_instrument(symbol)`.

Nie istnieje jednak metoda Read Service ani endpoint API pozwalający właścicielowi wyświetlić pełne universe bez uruchamiania kodu Python.

---

## 11. Aktualnie potwierdzony zakres działania

| Obszar | Status |
|---|---|
| Uruchomienie aplikacji | POTWIERDZONE |
| Yahoo Discovery | POTWIERDZONE |
| Yahoo Chart | POTWIERDZONE |
| Universe 169 instrumentów | POTWIERDZONE |
| InstrumentReading | POTWIERDZONE przez `last_reading_id` |
| Detektory | POTWIERDZONE |
| MarketEvents | POTWIERDZONE |
| SQLite | POTWIERDZONE |
| `db_path` | NAPRAWIONE I POTWIERDZONE |
| Pełna regresja | `2050 passed`, `41 subtests passed` |
| Baseline | NIEPOTWIERDZONE — `PENDING_BASELINE` |
| Aktualizacja snapshotu w każdym cyklu | NIEPOTWIERDZONA |
| Tavily w aktualnym przepływie | NIEPOTWIERDZONE |
| OpenAI w aktualnym przepływie | NIEPOTWIERDZONE |
| Telegram w aktualnym przepływie | NIEPOTWIERDZONE |
| Odczyt universe przez API/UI | BRAK |
| Gotowość 24/7 | NIEPOTWIERDZONA |
| Gotowość VPS | NIEPOTWIERDZONA |

---

## 12. Plan dalszej pracy

Każdy krok wymaga osobnego polecenia i wcześniejszej zgody właściciela.

### Krok 1 — zamknięcie poprawki `db_path`

1. Sprawdzić końcowy diff dwóch zmienionych plików.
2. Sprawdzić końcowy stan Git i brak artefaktów.
3. Właściciel podejmuje decyzję o przyjęciu zmiany.
4. Dopiero po osobnej zgodzie wykonać commit.
5. Nie wykonywać push bez oddzielnej zgody.

### Krok 2 — audyt cyklu baseline

1. Odtworzyć statycznie ścieżkę tworzenia baseline.
2. Ustalić warunek przejścia z `PENDING_BASELINE`.
3. Ustalić, czy zapis baseline jest wykonywany dla wszystkich 169 instrumentów.
4. Sprawdzić relację InstrumentReading → InstrumentObservation → baseline.
5. Sprawdzić odtwarzanie baseline po restarcie.
6. Przedstawić przyczynę bez zmiany kodu.

### Krok 3 — audyt snapshotów i `last_seen_at`

1. Ustalić, dlaczego późniejsze cykle nie są widoczne w `last_seen_at`.
2. Porównać ścieżkę `run_cycle()` z `_run_production_cycle()`.
3. Ustalić, kiedy zapisywane są `universe_snapshots` i ich członkowie.
4. Ustalić znaczenie `0 candidates` na każdym etapie.
5. Nie zmieniać filtrów ani logiki przed raportem i decyzją właściciela.

### Krok 4 — kompletność danych Discovery

1. Przenieść rzeczywiste pola Yahoo przez cały zatwierdzony kontrakt.
2. Zapisywać nazwę spółki.
3. Zapisywać `regular_market_price`.
4. Zapisywać rzeczywiste `quote_type`, `exchange`, `market` i `currency`.
5. Usunąć wpisywanie tych danych na stałe dopiero po zatwierdzeniu projektu zmiany.
6. Dodać diagnostykę braków i odrzuceń bez ich maskowania.

### Krok 5 — odczyt universe

1. Zaprojektować metodę Read Service dla universe.
2. Zaprojektować odczytowe endpointy API:
   - bieżące universe;
   - ostatni snapshot;
   - szczegóły instrumentu;
   - diagnostyka Chart i baseline.
3. Nie udostępniać bezpośredniego dostępu do SQLite.
4. Dopiero po zatwierdzeniu podłączyć widok w interfejsie.

### Krok 6 — pełny przepływ Tavily, OpenAI i Telegram

1. Sprawdzić statycznie sposób tworzenia i przekazywania adapterów.
2. Potwierdzić, że klucze są pobierane bez ujawniania wartości.
3. Usunąć rozbieżność nazw klucza Telegramu przez zatwierdzoną konfigurację.
4. Potwierdzić Tavily na rzeczywistym zdarzeniu.
5. Potwierdzić OpenAI na rzeczywistym zdarzeniu.
6. Przed wysyłką Telegram potwierdzić rzeczywistego odbiorcę.
7. Wykonać jeden kontrolowany pełny cykl bez sztucznego kandydata.

### Krok 7 — audyt mocków, fake'ów i placeholderów

1. Utworzyć pełną listę wystąpień.
2. Oddzielić testowe granice zewnętrzne od elementów wewnętrznych.
3. Wskazać miejsca maskujące rzeczywisty przepływ.
4. Zaprojektować zastąpienie ich rzeczywistymi komponentami albo jawnym statusem niedostępności.
5. Usuwać dopiero po zapewnieniu równoważnego pokrycia testowego.
6. Po każdej zatwierdzonej zmianie uruchamiać pełną regresję.

### Krok 8 — ciągłość pracy po restarcie

1. Potwierdzić odtworzenie universe, baseline, obserwacji i ostatnich świec z SQLite.
2. Potwierdzić brak ponownego tworzenia baseline po restarcie.
3. Potwierdzić brak podwójnego zapisu tej samej rewizji.
4. Potwierdzić kontynuację cyklu po kontrolowanym restarcie.
5. Potwierdzić odporność na przerwę sieciową i wznowienie Yahoo.

### Krok 9 — gotowość runtime 24/7

1. Potwierdzić cykl co 15 minut.
2. Potwierdzić blokadę nakładających się cykli.
3. Potwierdzić timeouty i ograniczone ponowienia połączeń.
4. Potwierdzić brak narastania pamięci i procesów potomnych.
5. Potwierdzić rotację logów.
6. Potwierdzić health check runtime.
7. Potwierdzić zapis diagnostyki każdego cyklu.
8. Potwierdzić poprawną pracę podczas zamknięcia rynku i weekendu.

### Krok 10 — przygotowanie VPS Hetzner

1. Ustalić system operacyjny i wersję Pythona na VPS.
2. Utworzyć jedno izolowane środowisko produkcyjne.
3. Przenieść sekrety do bezpiecznej konfiguracji VPS poza repozytorium.
4. Skonfigurować usługę systemową uruchamiającą ALCHEMIKA po restarcie serwera.
5. Skonfigurować automatyczny restart po awarii.
6. Skonfigurować katalog danych i uprawnienia.
7. Skonfigurować kopie zapasowe SQLite.
8. Skonfigurować logi i ich retencję.
9. Skonfigurować monitoring procesu, cykli, Yahoo, AI, Telegramu i miejsca na dysku.
10. Ograniczyć dostęp sieciowy i administracyjny do niezbędnego minimum.

### Krok 11 — kontrolowane wdrożenie

1. Wykonać test uruchomienia na VPS bez uruchamiania wielu instancji.
2. Potwierdzić Discovery i Chart na VPS.
3. Potwierdzić trwały zapis universe i baseline.
4. Potwierdzić analizę techniczną i detektory.
5. Potwierdzić Tavily i OpenAI na rzeczywistym zdarzeniu.
6. Potwierdzić jedną wiadomość Telegram do zatwierdzonego odbiorcy.
7. Potwierdzić restart usługi i odtworzenie stanu.
8. Potwierdzić kolejny cykl na granicy 15 minut.

### Krok 12 — odbiór produkcyjny

Warunki odbioru:

- wszystkie zatwierdzone testy przechodzą;
- rzeczywisty przepływ działa od Yahoo do Telegrama;
- universe, baseline, odczyty, obserwacje i zdarzenia są trwałe;
- restart nie powoduje utraty ani podwójnego zapisu danych;
- scheduler działa przez 24 godziny na dobę i 7 dni w tygodniu;
- monitoring wykrywa brak cyklu i awarię procesu;
- SQLite posiada sprawdzoną procedurę kopii zapasowej i odtworzenia;
- repozytorium nie zawiera sekretów, cache ani przypadkowych artefaktów;
- stan Git, dokumentacja i kod są zgodne;
- właściciel zatwierdza gotowość produkcyjną.

---

## 13. Kolejność na następny dzień

Pracę należy rozpocząć od:

1. końcowego audytu i decyzji dotyczącej dwóch zmian `db_path`;
2. odczytowego audytu przyczyny `PENDING_BASELINE` dla 169 instrumentów;
3. odczytowego audytu aktualizacji `last_seen_at` i wyniku `0 candidates`;
4. przedstawienia właścicielowi raportu przed jakąkolwiek kolejną zmianą.

Nie rozpoczynamy równocześnie prac nad AI, API, mockami ani VPS, dopóki trwały fundament danych nie zostanie potwierdzony.

---

## 14. Punkt wznowienia

Następna rozmowa rozpoczyna się od zdania:

`Wracamy do ALCHEMIKA w C:\Alchemik. Rozpoczynamy od zamknięcia zmian db_path, a następnie audytu PENDING_BASELINE dla 169 instrumentów.`

---

## 15. Stan końcowy dnia

| Obszar | Stan |
|---|---|
| Projekt | `C:\Alchemik` |
| Python | `3.13.13` |
| Testy | `2050 passed`, `41 subtests passed` |
| Universe | `169` aktywnych instrumentów |
| Rzeczywisty Yahoo | Działa |
| Rzeczywisty RuntimeService | Działa |
| Rzeczywiste detektory | Działają |
| SQLite | Działa |
| `db_path` | Naprawione, przetestowane, niezatwierdzone w Git |
| Baseline | `PENDING_BASELINE` dla 169 instrumentów |
| Tavily | Klucz dostępny; bieżący przebieg niepotwierdzony |
| OpenAI | Klucz dostępny; bieżący przebieg niepotwierdzony |
| Telegram | Konfiguracja dostępna; bieżący przebieg niepotwierdzony |
| Gotowość 24/7 | Niepotwierdzona |
| Gotowość VPS Hetzner | Niepotwierdzona |
| Następny krok | Zamknięcie `db_path`, następnie audyt baseline |

**Koniec dokumentu.**
