# ALCHEMIK — FORMALNA MACIERZ TESTÓW KONTRAKTU YAHOO CHART

## 1. METRYKA DOKUMENTU

| Atrybut | Wartość |
|---------|---------|
| Tytuł | ALCHEMIK — Formalna macierz testów kontraktu Yahoo chart |
| Rodzaj zadania | wyłącznie dokumentacyjne |
| Krok | 2/6 |
| Data utworzenia | 15.08.2026 |
| Repozytorium | C:\alchemik |
| Gałąź | master |
| HEAD | 8e4edbd5fe26a4ec8b2b4dbf4540614cf906da24 |
| Plik docelowy | docs/ALCHEMIK_MACIERZ_TESTOW_YAHOO_CHART.md |
| Dokument źródłowy nadrzędny | docs/ALCHEMIK_KONTRAKT_DANYCH_YAHOO_CHART.md |
| SHA-256 kontraktu chart | 929c2e8870d5988441e610c5c45c72debb6f83187edcf686c334fba90f87f1f4 |
| Kanoniczna liczba linii kontraktu chart | 949 |
| Podstawa przyszłego kroku | Krok 3/6 — walidacja offline na sztucznym transporcie |

---

## 2. STATUS DOKUMENTU

> **PROJEKT MACIERZY TESTÓW — DO ODRĘBNEJ AKCEPTACJI WŁAŚCICIELA**

Niniejszy dokument:

- nie zatwierdza wykonania żadnego przypadku testowego;
- nie zatwierdza rozpoczęcia Kroku 3/6;
- nie zatwierdza kontrolowanego audytu sieciowego;
- nie zatwierdza implementacji produkcyjnej;
- nie zmienia zatwierdzonego kontraktu danych Yahoo chart.

Dokument czeka na ocenę i decyzję właściciela projektu.

---

## 3. CEL I ZAKRES

Celem dokumentu jest przełożenie zatwierdzonego kontraktu danych Yahoo chart na jednoznaczne przypadki testowe, rozdzielone na:

- testy offline (`OFFLINE_READY`),
- przyszłe testy sieciowe (`NETWORK_LATER`),
- późniejsze testy integracyjne (`INTEGRATION_LATER`),
- przypadki zablokowane decyzją właściciela (`BLOCKED_BY_OWNER_DECISION`).

Macierz wskazuje oczekiwane statusy walidacji chart, flagi gotowości danych dla kolejnych modułów oraz ujawnia przypadki, których oczekiwany wynik nadal wymaga decyzji właściciela.

Macierz nie rozstrzyga samodzielnie żadnej otwartej decyzji i nie udaje, że jakikolwiek test został już wykonany.

---

## 4. ŹRÓDŁA I PODSTAWA KONTRAKTOWA

Podstawą treści macierzy jest wyłącznie:

1. `.clinerules`
2. `docs/00_ALCHEMIK_KANON_NAPRAWY.md`
3. `docs/ALCHEMIK_CHECKPOINT_PRACY.md`
4. `docs/FILOZOFIA_ALCHEMIKA.md`
5. `docs/ZASADY_PROJEKTU.md`
6. `docs/INSTRUKCJA_DLA_CLINE.md`
7. `docs/ALCHEMIK_AUDYT_YAHOO_FINANCE.md`
8. `docs/ALCHEMIK_CHECKPOINT_2026-08-14_PLAN_2026-08-15.md`
9. `docs/ALCHEMIK_KONTRAKT_DANYCH_YAHOO_CHART.md`

Źródłem nadrzędnym dla treści przypadków testowych jest dokument kontraktu chart.

Nie odczytano `.streamlit/secrets.toml`, cookie, crumb, kluczy API, tokenów, haseł ani baz cookie yfinance.

---

## 5. ZATWIERDZONE ZASADY WŁAŚCICIELA

Macierz respektuje następujące zatwierdzone zasady:

1. Yahoo Finance jest jedynym produkcyjnym źródłem danych rynkowych.
2. Screener jest mechanizmem discovery i filtrem wstępnym.
3. Chart jest źródłem danych rynkowych i historii OHLCV.
4. Istnieje jeden zbiór symboli Yahoo/WSE bez produkcyjnego rozróżnienia GPW i NewConnect.
5. Zakazane jest automatyczne dopisywanie `.WA`, `.PL` lub innej końcówki.
6. Bieżący zakres dynamicznego uniwersum wynosi od 0,10 PLN do 10,00 PLN, z obiema granicami włącznie.
7. Historia krótsza niż 52 tygodnie jest dopuszczalna do Observation.
8. Możliwa jest ograniczona gotowość Technical Engine przy krótszej historii.
9. `volume=0` jest prawidłową wartością.
10. Zakazane jest ciche uzupełnianie brakujących danych.
11. RuntimeService jest właścicielem cyklu Observation.
12. HistoryRepository jest właścicielem kontraktu trwałego zapisu.
13. Technical Engine jest właścicielem obliczania wskaźników.
14. GPT-4o działa wyłącznie na końcu zwalidowanej ścieżki.

---

## 6. MODEL PRZYPADKU TESTOWEGO

Każdy przypadek testowy zawiera następujące pola:

| Pole | Znaczenie |
|------|-----------|
| ID | unikalny identyfikator przypadku |
| obszar | obszar kontraktu objęty przypadkiem |
| etap wykonania | `OFFLINE_READY`, `NETWORK_LATER`, `INTEGRATION_LATER` albo `BLOCKED_BY_OWNER_DECISION` |
| warunek wejściowy | dane wejściowe lub stan początkowy |
| scenariusz | przebieg testu |
| oczekiwana obserwacja | co walidator musi zaobserwować |
| oczekiwany status chart | zatwierdzony status albo `NIEROZSTRZYGNIĘTE` |
| Observation ready | gotowość danych do Observation |
| Baseline ready | gotowość danych do Baseline |
| Technical Engine ready | gotowość danych do Technical Engine |
| Hunter ready | gotowość danych do Hunter |
| MasterEngine ready | gotowość danych do MasterEngine |
| GPT-4o ready | gotowość danych do GPT-4o |
| zakres blokady | co jest blokowane, gdy przypadek nie przejdzie |
| podstawa w kontrakcie | sekcja kontraktu chart |
| stan decyzji | czy wynik jest rozstrzygnięty, czy wymaga decyzji właściciela |
| uwagi | dodatkowe objaśnienia |

Dozwolone wartości gotowości: `TAK`, `NIE`, `WARUNKOWO`, `NIE DOTYCZY`, `NIEROZSTRZYGNIĘTE`.

Nie występują puste komórki. Jeżeli kontrakt nie rozstrzyga wyniku, wpisano `NIEROZSTRZYGNIĘTE` albo `BLOCKED_BY_OWNER_DECISION`.

---

## 7. IDENTYFIKATORY I ETAPY TESTÓW

### 7.1. Prefiksy obszarów

| Prefiks | Obszar |
|---------|--------|
| `CH-IN-*` | wejście z discovery |
| `CH-TR-*` | transport i struktura odpowiedzi |
| `CH-META-*` | metadane |
| `CH-CUR-*` | dane bieżące |
| `CH-OHLCV-*` | struktura i spójność świec |
| `CH-VOL-*` | wolumen |
| `CH-TIME-*` | timestampy, kolejność i sesje |
| `CH-HIST-*` | długość i kompletność historii |
| `CH-CROSS-*` | zgodność screener–chart |
| `CH-READY-*` | gotowość modułów |
| `CH-BOUND-*` | granice odpowiedzialności |
| `CH-SEC-*` | brak sekretów i bezpieczne artefakty |
| `CH-NET-*` | przyszłe zachowanie sieciowe |
| `CH-INT-*` | późniejsza integracja |

### 7.2. Etapy wykonania

| Etap | Znaczenie |
|------|-----------|
| `OFFLINE_READY` | dający się wykonać w Kroku 3/6 na sztucznym transporcie bez sieci |
| `NETWORK_LATER` | wymagający rzeczywistego wywołania Yahoo w kontrolowanym audycie |
| `INTEGRATION_LATER` | wymagający zintegrowanych modułów systemu |
| `BLOCKED_BY_OWNER_DECISION` | wymagający odrębnej decyzji właściciela |

Każdy identyfikator występuje tylko raz. Liczba przypadków wynika z pełnego pokrycia kontraktu.

---

## 8. MACIERZ WEJŚCIA Z DISCOVERY

### CH-IN-001 — dokładny symbol otrzymany ze screenera

| Pole | Wartość |
|------|---------|
| ID | CH-IN-001 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord screenera zawiera dokładny symbol Yahoo |
| scenariusz | przekazano symbol ze screenera jako wejście wywołania chart |
| oczekiwana obserwacja | chart otrzymuje dokładnie ten symbol, bez żadnej modyfikacji |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — poprawny symbol wejściowy |
| podstawa w kontrakcie | 5.2, 6, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | symbol jest używany wyłącznie w postaci zwróconej przez screener |

### CH-IN-002 — próba automatycznego dopisania końcówki — zablokowana

| Pole | Wartość |
|------|---------|
| ID | CH-IN-002 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | symbol bazowy bez końcówki albo symbol z częściową końcówką |
| scenariusz | próba automatycznego dopisania `.WA`, `.PL` lub innej końcówki |
| oczekiwana obserwacja | próba jest odrzucona; żaden symbol nie został skonstruowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wywołania chart dla skonstruowanego symbolu |
| podstawa w kontrakcie | 5.2, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | automatyczne konstruowanie symbolu jest zakazane; status nie jest tu przypisany, bo żadne wywołanie nie może powstać |

### CH-IN-003 — brak symbolu

| Pole | Wartość |
|------|---------|
| ID | CH-IN-003 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord screenera bez pola symbolu |
| scenariusz | próba wywołania chart bez symbolu |
| oczekiwana obserwacja | wywołanie nie powstaje; rekord jest odrzucony jako niekompletny |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wywołania chart i brak dalszej ścieżki |
| podstawa w kontrakcie | 7, 7.2 |
| stan decyzji | rozstrzygnięty |
| uwagi | status chart nie jest przypisany, bo żądanie chart nie może powstać |

### CH-IN-004 — pusty symbol

| Pole | Wartość |
|------|---------|
| ID | CH-IN-004 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord screenera z pustym łańcuchem symbolu |
| scenariusz | próba wywołania chart z pustym symbolem |
| oczekiwana obserwacja | wywołanie nie powstaje; rekord jest odrzucony |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wywołania chart i brak dalszej ścieżki |
| podstawa w kontrakcie | 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | status chart nie jest przypisany; nie powstaje żądanie |

### CH-IN-005 — rekord spoza bieżącego snapshotu

| Pole | Wartość |
|------|---------|
| ID | CH-IN-005 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | symbol nieobecny w bieżącym snapshotcie dynamicznego uniwersum |
| scenariusz | próba użycia symbolu spoza bieżącego cyklu |
| oczekiwana obserwacja | symbol nie jest traktowany jako wejście bieżącego cyklu |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wywołania chart dla symbolu spoza snapshotu |
| podstawa w kontrakcie | 5.3, 7.2 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak instrumentu w screenerze oznacza brak instrumentu w cyklu uniwersum |

### CH-IN-006 — cena dokładnie na dolnej granicy

| Pole | Wartość |
|------|---------|
| ID | CH-IN-006 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena screenera równa 0,10 PLN |
| scenariusz | kwalifikacja rekordu do zakresu |
| oczekiwana obserwacja | rekord jest dopuszczony; dolna granica jest włączona |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — cena na granicy jest dopuszczalna |
| podstawa w kontrakcie | 5.3, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | dolna granica włącznie |

### CH-IN-007 — cena dokładnie na górnej granicy

| Pole | Wartość |
|------|---------|
| ID | CH-IN-007 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena screenera równa 10,00 PLN |
| scenariusz | kwalifikacja rekordu do zakresu |
| oczekiwana obserwacja | rekord jest dopuszczony; górna granica jest włączona |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — cena na granicy jest dopuszczalna |
| podstawa w kontrakcie | 5.3, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | górna granica włącznie |

### CH-IN-008 — cena poniżej zakresu

| Pole | Wartość |
|------|---------|
| ID | CH-IN-008 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena screenera poniżej 0,10 PLN |
| scenariusz | kwalifikacja rekordu do zakresu |
| oczekiwana obserwacja | rekord nie wchodzi do bieżącego dynamicznego uniwersum |
| oczekiwany status chart | CHART_RANGE_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | wykluczenie z bieżącego cyklu uniwersum |
| podstawa w kontrakcie | 5.3, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | zakres dotyczy kwalifikacji do uniwersum, nie usuwania świec historycznych |

### CH-IN-009 — cena powyżej zakresu

| Pole | Wartość |
|------|---------|
| ID | CH-IN-009 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena screenera powyżej 10,00 PLN |
| scenariusz | kwalifikacja rekordu do zakresu |
| oczekiwana obserwacja | rekord nie wchodzi do bieżącego dynamicznego uniwersum |
| oczekiwany status chart | CHART_RANGE_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | wykluczenie z bieżącego cyklu uniwersum |
| podstawa w kontrakcie | 5.3, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | zakres dotyczy kwalifikacji do uniwersum |

### CH-IN-010 — brak regularMarketPrice

| Pole | Wartość |
|------|---------|
| ID | CH-IN-010 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord screenera bez pola regularMarketPrice |
| scenariusz | kwalifikacja rekordu bez ceny |
| oczekiwana obserwacja | brak ceny nie jest traktowany jako automatyczne wykluczenie bez decyzji |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak ceny uniemożliwia kwalifikację cenową i porównanie; dalsza ścieżka nierozstrzygnięta |
| podstawa w kontrakcie | 5.3, 7 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | kwalifikacja cenowa bez ceny pozostaje otwarta |

### CH-IN-011 — brak czasu snapshotu

| Pole | Wartość |
|------|---------|
| ID | CH-IN-011 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord screenera bez timestampu snapshotu |
| scenariusz | porównanie ceny screenera i chart bez czasu snapshotu |
| oczekiwana obserwacja | brak porównywalnego czasu nie jest traktowany jako wymyślony próg |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | porównanie ceny między endpointami wymaga porównywalnego czasu |
| podstawa w kontrakcie | 7, 10, 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | zasady aktualności regularMarketTime pozostają nierozstrzygnięte |

### CH-IN-012 — brak pola opcjonalnego nieuniemożliwiającego identyfikacji symbolu

| Pole | Wartość |
|------|---------|
| ID | CH-IN-012 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord screenera bez pola opcjonalnego, ale z obecnym symbolem |
| scenariusz | użycie symbolu mimo braku pola opcjonalnego |
| oczekiwana obserwacja | brak pola opcjonalnego nie blokuje identyfikacji symbolu |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — brak opcjonalnego pola nie jest konfliktem |
| podstawa w kontrakcie | 7.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak opcjonalnego pola nie oznacza konfliktu |

### CH-IN-013 — zakaz używania segmentu GPW/NC jako pola wymaganego od Yahoo

| Pole | Wartość |
|------|---------|
| ID | CH-IN-013 |
| obszar | wejście z discovery |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord bez pola segmentu GPW/NC |
| scenariusz | próba wymagania pola segmentu GPW/NC od Yahoo |
| oczekiwana obserwacja | segment GPW/NC nie jest wymagany ani używany jako pole produkcyjne |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — Yahoo nie dostarcza i nie jest pytane o segment GPW/NC |
| podstawa w kontrakcie | 5.2, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak pola segmentu nie jest konfliktem |

---

## 9. MACIERZ TRANSPORTU I STRUKTURY ODPOWIEDZI

### CH-TR-001 — HTTP 200 z prawidłowym wynikiem

| Pole | Wartość |
|------|---------|
| ID | CH-TR-001 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | NETWORK_LATER |
| warunek wejściowy | kontrolowane wywołanie chart dla symbolu z uniwersum |
| scenariusz | Yahoo zwraca HTTP 200 z prawidłowym chart.result |
| oczekiwana obserwacja | odpowiedź jest poprawnie odczytana i przekazana do parsera |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak zatwierdzonego statusu transportu |
| podstawa w kontrakcie | 9, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla samego transportu HTTP 200 |

### CH-TR-002 — HTTP 200 bez chart.result

| Pole | Wartość |
|------|---------|
| ID | CH-TR-002 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | sztuczna odpowiedź HTTP 200 bez pola chart.result |
| scenariusz | parsowanie odpowiedzi bez chart.result |
| oczekiwana obserwacja | brak chart.result jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wyniku blokuje interpretację danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla transportu/parsowania bez wyniku |

### CH-TR-003 — HTTP 200 z pustym result

| Pole | Wartość |
|------|---------|
| ID | CH-TR-003 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | sztuczna odpowiedź HTTP 200 z pustym chart.result |
| scenariusz | parsowanie pustego wyniku |
| oczekiwana obserwacja | pusty wynik jest jawnie raportowany jako brak danych |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wyniku blokuje interpretację danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | pusty result nie ma samodzielnie zatwierdzonego statusu |

### CH-TR-004 — odpowiedź zawierająca obiekt błędu

| Pole | Wartość |
|------|---------|
| ID | CH-TR-004 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | odpowiedź zawiera jawny obiekt błędu |
| scenariusz | parsowanie odpowiedzi z obiektem błędu |
| oczekiwana obserwacja | obiekt błędu jest rozpoznany i raportowany, bez mylenia z pustym wynikiem |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | błąd odpowiedzi blokuje interpretację danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla obiektu błędu |

### CH-TR-005 — HTTP inny niż oczekiwany

| Pole | Wartość |
|------|---------|
| ID | CH-TR-005 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | NETWORK_LATER |
| warunek wejściowy | Yahoo zwraca HTTP inny niż 200 |
| scenariusz | obsługa nieoczekiwanego HTTP |
| oczekiwana obserwacja | nieoczekiwany HTTP jest raportowany bez retry i fallbacku |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | błąd HTTP blokuje interpretację danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | HTTP 404, 401 i pusty wynik nie są sobą; brak zatwierdzonego statusu HTTP |

### CH-TR-006 — odpowiedź niebędąca prawidłowym JSON

| Pole | Wartość |
|------|---------|
| ID | CH-TR-006 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | odpowiedź nie jest prawidłowym JSON |
| scenariusz | parsowanie nieprawidłowego JSON |
| oczekiwana obserwacja | błąd parsowania jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | błąd parsowania blokuje interpretację danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla błędu parsowania |

### CH-TR-007 — brak wymaganej części meta

| Pole | Wartość |
|------|---------|
| ID | CH-TR-007 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | odpowiedź bez części meta |
| scenariusz | parsowanie odpowiedzi bez meta |
| oczekiwana obserwacja | brak meta jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak metadanych blokuje walidację i dalszą ścieżkę |
| podstawa w kontrakcie | 9, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak metadanych nie ma zatwierdzonego statusu |

### CH-TR-008 — brak timestamp

| Pole | Wartość |
|------|---------|
| ID | CH-TR-008 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | odpowiedź bez tablicy timestamp |
| scenariusz | parsowanie odpowiedzi bez timestamp |
| oczekiwana obserwacja | brak timestamp jest jawnie raportowany; seria nie może być przypisana do świec |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak timestamp blokuje porządek czasowy i dalszą ścieżkę |
| podstawa w kontrakcie | 9.2, 10 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak statusu jednoznacznie przypisanego do braku timestamp |

### CH-TR-009 — brak indicators.quote

| Pole | Wartość |
|------|---------|
| ID | CH-TR-009 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | odpowiedź bez indicators.quote |
| scenariusz | parsowanie odpowiedzi bez indicators.quote |
| oczekiwana obserwacja | brak indicators.quote jest jawnie raportowany; brak danych OHLC |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak indicators.quote blokuje OHLCV i dalszą ścieżkę |
| podstawa w kontrakcie | 9.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak statusu jednoznacznie przypisanego do braku indicators.quote |

### CH-TR-010 — więcej niż jeden nieoczekiwany wynik

| Pole | Wartość |
|------|---------|
| ID | CH-TR-010 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | odpowiedź zawiera więcej niż jeden wynik, gdy oczekiwano jednego |
| scenariusz | parsowanie wielu nieoczekiwanych wyników |
| oczekiwana obserwacja | nadmiar wyników jest jawnie raportowany; nie wybiera się cicho jednego z nich |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | niejednoznaczny wynik blokuje dalszą ścieżkę |
| podstawa w kontrakcie | 7.2, 9 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | nie zatwierdzono reguły wyboru wyniku przy nadmiarze |

### CH-TR-011 — błąd przed wysłaniem żądania

| Pole | Wartość |
|------|---------|
| ID | CH-TR-011 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | błąd powstaje przed wysłaniem żądania |
| scenariusz | próba wysłania żądania kończy się błędem lokalnym |
| oczekiwana obserwacja | błąd jest raportowany bez retry i fallbacku |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak żądania oznacza brak danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla błędu transportu |

### CH-TR-012 — błąd po otrzymaniu odpowiedzi

| Pole | Wartość |
|------|---------|
| ID | CH-TR-012 |
| obszar | transport i struktura odpowiedzi |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | błąd powstaje po otrzymaniu odpowiedzi, przed ukończeniem parsowania |
| scenariusz | odpowiedź dotarła, ale przetwarzanie kończy się błędem |
| oczekiwana obserwacja | błąd jest raportowany; częściowe dowody pozostają jawne |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | błąd po odpowiedzi blokuje interpretację danych |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla błędu po odpowiedzi |

### CH-NET-001 — rzeczywiste wywołanie chart dla symbolu z uniwersum

| Pole | Wartość |
|------|---------|
| ID | CH-NET-001 |
| obszar | przyszłe zachowanie sieciowe |
| etap wykonania | NETWORK_LATER |
| warunek wejściowy | jeden kontrolowany przebieg rzeczywistych danych Yahoo |
| scenariusz | realizacja wywołania chart przy zatwierdzonym SHA-256 |
| oczekiwana obserwacja | odpowiedź jest zachowana jako surowy dowód |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | audyt sieciowy wymaga zatwierdzenia 3A i decyzji właściciela |
| podstawa w kontrakcie | 27 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | Kroku 3B nie zatwierdzono |

### CH-NET-002 — rzeczywista liczba żądań zgodna z dynamicznym limitem

| Pole | Wartość |
|------|---------|
| ID | CH-NET-002 |
| obszar | przyszłe zachowanie sieciowe |
| etap wykonania | NETWORK_LATER |
| warunek wejściowy | kontrolowany przebieg sieciowy |
| scenariusz | rozliczenie faktycznie wysłanych żądań |
| oczekiwana obserwacja | każde żądanie jest zliczone i zgodne z limitem |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | rozliczalność audytu sieciowego |
| podstawa w kontrakcie | 27 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak retry i fallbacku |

---

## 10. MACIERZ METADANYCH

### CH-META-001 — zgodny symbol

| Pole | Wartość |
|------|---------|
| ID | CH-META-001 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.symbol zgodny z symbolem wejściowym |
| scenariusz | porównanie symbolu meta z symbolem wejściowym |
| oczekiwana obserwacja | symbol jest zgodny i potwierdzony |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — symbol zgodny |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | zgodność symbolu jest wymagana |

### CH-META-002 — inny symbol niż wejściowy

| Pole | Wartość |
|------|---------|
| ID | CH-META-002 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.symbol różny od symbolu wejściowego |
| scenariusz | porównanie symbolu meta z symbolem wejściowym |
| oczekiwana obserwacja | konflikt symbolu jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt symbolu blokuje przyjęcie danych |
| podstawa w kontrakcie | 11 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla konfliktu symbolu |

### CH-META-003 — instrumentType=EQUITY

| Pole | Wartość |
|------|---------|
| ID | CH-META-003 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.instrumentType=EQUITY |
| scenariusz | walidacja typu instrumentu |
| oczekiwana obserwacja | typ EQUITY jest potwierdzony |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — typ zgodny |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | oczekiwany typ to EQUITY |

### CH-META-004 — konflikt typu instrumentu

| Pole | Wartość |
|------|---------|
| ID | CH-META-004 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.instrumentType różny od EQUITY |
| scenariusz | walidacja typu instrumentu |
| oczekiwana obserwacja | jawny konflikt typu jest raportowany |
| oczekiwany status chart | CHART_TYPE_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt typu blokuje przyjęcie jako akcja |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | typ inny niż EQUITY oznacza konflikt |

### CH-META-005 — currency=PLN

| Pole | Wartość |
|------|---------|
| ID | CH-META-005 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.currency=PLN |
| scenariusz | walidacja waluty |
| oczekiwana obserwacja | waluta PLN jest potwierdzona |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — waluta zgodna |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | oczekiwana waluta to PLN |

### CH-META-006 — konflikt waluty

| Pole | Wartość |
|------|---------|
| ID | CH-META-006 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.currency różna od PLN |
| scenariusz | walidacja waluty |
| oczekiwana obserwacja | jawny konflikt waluty jest raportowany |
| oczekiwany status chart | CHART_CURRENCY_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt waluty blokuje przyjęcie danych |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | jawna inna waluta oznacza konflikt |

### CH-META-007 — zgodny exchangeName

| Pole | Wartość |
|------|---------|
| ID | CH-META-007 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.exchangeName zgodny z rynkiem WSE |
| scenariusz | walidacja exchangeName |
| oczekiwana obserwacja | exchangeName jest zgodny i potwierdzony |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — exchange zgodny |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | oczekiwany rynek to WSE |

### CH-META-008 — brak exchangeName

| Pole | Wartość |
|------|---------|
| ID | CH-META-008 |
| obszar | metadane |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | meta bez pola exchangeName |
| scenariusz | walidacja bez exchangeName |
| oczekiwana obserwacja | brak exchangeName jest raportowany jako brak metadanych |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak exchangeName blokuje potwierdzenie rynku |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak metadanych nie ma zatwierdzonego statusu |

### CH-META-009 — nieoczekiwany exchangeName

| Pole | Wartość |
|------|---------|
| ID | CH-META-009 |
| obszar | metadane |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | meta.exchangeName różny od oczekiwanego rynku WSE |
| scenariusz | walidacja nieoczekiwanego exchangeName |
| oczekiwana obserwacja | konflikt giełdy jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt giełdy blokuje przyjęcie danych |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | konflikt giełdy nie ma zatwierdzonego statusu |

### CH-META-010 — obecny i poprawny gmtoffset

| Pole | Wartość |
|------|---------|
| ID | CH-META-010 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.gmtoffset obecny i poprawny |
| scenariusz | walidacja gmtoffset |
| oczekiwana obserwacja | gmtoffset jest poprawny i zachowany |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — gmtoffset poprawny |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | gmtoffset może występować opcjonalnie |

### CH-META-011 — brak gmtoffset

| Pole | Wartość |
|------|---------|
| ID | CH-META-011 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta bez pola gmtoffset |
| scenariusz | walidacja bez gmtoffset |
| oczekiwana obserwacja | brak gmtoffset nie jest traktowany jako konflikt |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — brak opcjonalnego pola nie jest konfliktem |
| podstawa w kontrakcie | 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | gmtoffset jest opcjonalny |

### CH-META-012 — obecna strefa czasowa

| Pole | Wartość |
|------|---------|
| ID | CH-META-012 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.timezone lub exchangeTimezoneName obecna i poprawna |
| scenariusz | walidacja strefy czasowej |
| oczekiwana obserwacja | strefa czasowa jest obecna i zachowana |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — strefa czasowa poprawna |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | strefa czasowa jest opcjonalna |

### CH-META-013 — brak strefy czasowej

| Pole | Wartość |
|------|---------|
| ID | CH-META-013 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta bez strefy czasowej |
| scenariusz | walidacja bez strefy czasowej |
| oczekiwana obserwacja | brak strefy czasowej nie jest traktowany jako konflikt |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — brak opcjonalnego pola nie jest konfliktem |
| podstawa w kontrakcie | 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | interpretacja sesji bez strefy czasowej pozostaje zależna od kalendarza sesji |

### CH-META-014 — obecne dataGranularity

| Pole | Wartość |
|------|---------|
| ID | CH-META-014 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.dataGranularity obecne |
| scenariusz | walidacja dataGranularity |
| oczekiwana obserwacja | dataGranularity jest obecne i zachowane |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — dataGranularity obecne |
| podstawa w kontrakcie | 9.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | dataGranularity jest opcjonalne; jego dokładna wartość nie jest tu zatwierdzana |

### CH-META-015 — brak dataGranularity

| Pole | Wartość |
|------|---------|
| ID | CH-META-015 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta bez pola dataGranularity |
| scenariusz | walidacja bez dataGranularity |
| oczekiwana obserwacja | brak dataGranularity nie jest traktowany jako konflikt |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — brak opcjonalnego pola nie jest konfliktem |
| podstawa w kontrakcie | 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | dokładne kombinacje range i interval pozostają nierozstrzygnięte |

### CH-META-016 — konflikt metadanych pomiędzy discovery i chart

| Pole | Wartość |
|------|---------|
| ID | CH-META-016 |
| obszar | metadane |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | metadane discovery i chart różnią się jawnie |
| scenariusz | porównanie metadanych discovery i chart |
| oczekiwana obserwacja | konflikt metadanych jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt metadanych blokuje przyjęcie danych |
| podstawa w kontrakcie | 11, 7 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | konflikt dotyczy symbolu lub giełdy; typ i waluta mają odrębne przypadki |

---

## 11. MACIERZ DANYCH BIEŻĄCYCH

### CH-CUR-001 — obecny regularMarketPrice

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-001 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.regularMarketPrice obecna i numeryczna |
| scenariusz | walidacja ceny bieżącej |
| oczekiwana obserwacja | cena bieżąca jest poprawnie zachowana |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — cena bieżąca obecna |
| podstawa w kontrakcie | 9.1, 12 |
| stan decyzji | rozstrzygnięty |
| uwagi | cena bieżąca jest częścią danych bieżących |

### CH-CUR-002 — brak ceny bieżącej

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-002 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta bez regularMarketPrice |
| scenariusz | walidacja bez ceny bieżącej |
| oczekiwana obserwacja | brak ceny bieżącej jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak ceny bieżącej blokuje dane bieżące |
| podstawa w kontrakcie | 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak ceny bieżącej nie ma zatwierdzonego statusu |

### CH-CUR-003 — cena nienumeryczna

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-003 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.regularMarketPrice nienumeryczna |
| scenariusz | walidacja ceny bieżącej |
| oczekiwana obserwacja | cena nienumeryczna jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | cena nienumeryczna blokuje dane bieżące |
| podstawa w kontrakcie | 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla ceny nienumerycznej |

### CH-CUR-004 — cena poza zatwierdzonym zakresem bieżącego cyklu

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-004 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena bieżąca poza 0,10–10,00 PLN |
| scenariusz | walidacja ceny bieżącej względem zakresu |
| oczekiwana obserwacja | cena poza zakresem jest jawnie raportowana |
| oczekiwany status chart | CHART_RANGE_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | cena poza zakresem wyklucza z bieżącego cyklu |
| podstawa w kontrakcie | 5.3, 12 |
| stan decyzji | rozstrzygnięty |
| uwagi | historyczne ceny poza zakresem nie są automatycznym błędem |

### CH-CUR-005 — obecny regularMarketTime

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-005 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta.regularMarketTime obecny |
| scenariusz | walidacja czasu bieżącej ceny |
| oczekiwana obserwacja | czas bieżącej ceny jest poprawnie zachowany |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — czas bieżącej ceny obecny |
| podstawa w kontrakcie | 9.1, 12 |
| stan decyzji | rozstrzygnięty |
| uwagi | aktualność regularMarketTime pozostaje nierozstrzygnięta |

### CH-CUR-006 — brak czasu bieżącej ceny

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-006 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | meta bez regularMarketTime |
| scenariusz | walidacja bez czasu bieżącej ceny |
| oczekiwana obserwacja | brak czasu bieżącej ceny jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak czasu uniemożliwia porównywalność czasową |
| podstawa w kontrakcie | 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | zasady aktualności regularMarketTime nierozstrzygnięte |

### CH-CUR-007 — cena i czas pochodzące z różnych snapshotów

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-007 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena i czas bieżącej ceny z różnych snapshotów |
| scenariusz | sprawdzenie spójności pary cena–czas |
| oczekiwana obserwacja | niespójność pary jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | niespójna para cena–czas blokuje dane bieżące |
| podstawa w kontrakcie | 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonej reguły dla niespójności pary |

### CH-CUR-008 — różnica ceny screenera i chart bez porównywalnego czasu

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-008 |
| obszar | dane bieżące |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | różne ceny screenera i chart, bez porównywalnego czasu |
| scenariusz | porównanie ceny bez porównywalnego czasu |
| oczekiwana obserwacja | różnica nie jest traktowana jako konflikt bez porównywalnego czasu |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak porównywalnego czasu blokuje ocenę różnicy |
| podstawa w kontrakcie | 10, 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | nie wymaga się dokładnej równości cen bez porównywalnego czasu |

### CH-CUR-009 — brak zatwierdzonej tolerancji ceny

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-009 |
| obszar | dane bieżące |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | próba porównania ceny z użyciem progu |
| scenariusz | użycie jakiegokolwiek progu tolerancji ceny |
| oczekiwana obserwacja | żadna tolerancja ceny nie zostaje wymyślona |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | zakaz wymyślania tolerancji ceny |
| podstawa w kontrakcie | 10, 12 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | próg tolerancji ceny nie istnieje w kontrakcie |

### CH-CUR-010 — bieżąca cena z ostatniej kompletnej świecy jako zagadnienie nierozstrzygnięte

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-010 |
| obszar | dane bieżące |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | cena bieżąca ma być uzyskana z ostatniej kompletnej świecy |
| scenariusz | wyprowadzenie ceny bieżącej z ostatniej świecy |
| oczekiwana obserwacja | jest to nierozstrzygnięte; nie zatwierdzono tej reguły |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | wyprowadzenie ceny z ostatniej świecy wymaga decyzji |
| podstawa w kontrakcie | 12, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | zagadnienie otwarte; nie zgaduje się wartości |

---

## 12. MACIERZ STRUKTURY OHLCV

### CH-OHLCV-001 — kompletna poprawna świeca

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-001 |
| obszar | struktura i spójność świec |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | świeca z kompletem open, high, low, close, volume i poprawnymi relacjami |
| scenariusz | walidacja kompletnej świecy |
| oczekiwana obserwacja | świeca jest zaakceptowana jako poprawna |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — świeca poprawna |
| podstawa w kontrakcie | 9.2, 10 |
| stan decyzji | rozstrzygnięty |
| uwagi | high nie niższe od open, close ani low; low nie wyższe od open, close ani high |

### CH-OHLCV-002 — zgodne długości tablic

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-002 |
| obszar | struktura i spójność świec |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | tablice timestamp, open, high, low, close, volume o zgodnych długościach |
| scenariusz | walidacja zgodności długości tablic |
| oczekiwana obserwacja | serie dają się przypisać do tych samych świec |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — długości zgodne |
| podstawa w kontrakcie | 13 |
| stan decyzji | rozstrzygnięty |
| uwagi | zgodność długości umożliwia przypisanie wolumenu do świecy |

### CH-OHLCV-003 — niezgodne długości tablic

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-003 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | tablice OHLCV o niezgodnych długościach |
| scenariusz | walidacja niezgodnych długości |
| oczekiwana obserwacja | niezgodność jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | niezgodne długości uniemożliwiają przypisanie wolumenu do świecy |
| podstawa w kontrakcie | 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | różnica między CHART_INCOMPLETE i CHART_SERIES_BROKEN nierozstrzygnięta |

### CH-OHLCV-004 — brak open

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-004 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | tablica open nieobecna |
| scenariusz | walidacja bez pola open |
| oczekiwana obserwacja | brak open jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak open blokuje pełną świecę |
| podstawa w kontrakcie | 9.2, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak pola nie ma jednoznacznego statusu |

### CH-OHLCV-005 — brak high

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-005 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | tablica high nieobecna |
| scenariusz | walidacja bez pola high |
| oczekiwana obserwacja | brak high jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak high blokuje pełną świecę |
| podstawa w kontrakcie | 9.2, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak pola nie ma jednoznacznego statusu |

### CH-OHLCV-006 — brak low

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-006 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | tablica low nieobecna |
| scenariusz | walidacja bez pola low |
| oczekiwana obserwacja | brak low jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak low blokuje pełną świecę |
| podstawa w kontrakcie | 9.2, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak pola nie ma jednoznacznego statusu |

### CH-OHLCV-007 — brak close

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-007 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | tablica close nieobecna |
| scenariusz | walidacja bez pola close |
| oczekiwana obserwacja | brak close jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak close blokuje pełną świecę |
| podstawa w kontrakcie | 9.2, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak pola nie ma jednoznacznego statusu |

### CH-OHLCV-008 — brak volume

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-008 |
| obszar | struktura i spójność świec |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | tablica volume nieobecna |
| scenariusz | walidacja bez pola volume |
| oczekiwana obserwacja | brak volume jest jawnie raportowany jako błąd wolumenu |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wolumenu blokuje serię |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak pola volume może dawać CHART_BAD_VOLUME |

### CH-OHLCV-009 — wartość null w pojedynczym polu

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-009 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | jedno pole OHLC (nie volume) jest null |
| scenariusz | walidacja pojedynczego null |
| oczekiwana obserwacja | null jest jawnie zachowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | częściowy rekord wymaga oceny |
| podstawa w kontrakcie | 10, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | różnica INCOMPLETE/SERIES_BROKEN nierozstrzygnięta |

### CH-OHLCV-010 — wszystkie pola świecy null

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-010 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | wszystkie pola OHLC świecy są null |
| scenariusz | walidacja w pełni pustej świecy |
| oczekiwana obserwacja | pełna pustka świecy jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | świeca w pełni pusta blokuje serię |
| podstawa w kontrakcie | 10, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status nieprzypisany jednoznacznie |

### CH-OHLCV-011 — high niższe od jednego z wymaganych pól

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-011 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | high niższe od open, close lub low |
| scenariusz | walidacja relacji high |
| oczekiwana obserwacja | naruszenie relacji OHLC jest jawnie raportowane |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | niepoprawna relacja OHLC blokuje pełną świecę |
| podstawa w kontrakcie | 10.9, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | naruszenie poprawności OHLC; status niejednoznaczny |

### CH-OHLCV-012 — low wyższe od jednego z wymaganych pól

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-012 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | low wyższe od open, close lub high |
| scenariusz | walidacja relacji low |
| oczekiwana obserwacja | naruszenie relacji OHLC jest jawnie raportowane |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | niepoprawna relacja OHLC blokuje pełną świecę |
| podstawa w kontrakcie | 10.9, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | naruszenie poprawności OHLC; status niejednoznaczny |

### CH-OHLCV-013 — wartość nienumeryczna

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-013 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | pole OHLC jest nienumeryczne |
| scenariusz | walidacja wartości nienumerycznej |
| oczekiwana obserwacja | wartość nienumeryczna jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | wartość nienumeryczna blokuje serię |
| podstawa w kontrakcie | 10, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status niejednoznaczny |

### CH-OHLCV-014 — wartość ujemna

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-014 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | pole OHLC (nie volume) jest ujemne |
| scenariusz | walidacja wartości ujemnej |
| oczekiwana obserwacja | wartość ujemna jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | wartość ujemna blokuje serię |
| podstawa w kontrakcie | 10, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | cena ujemna nie ma jednoznacznego statusu |

### CH-OHLCV-015 — brak cichego kopiowania poprzedniej wartości

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-015 |
| obszar | struktura i spójność świec |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | brakująca wartość w serii |
| scenariusz | próba cichego skopiowania poprzedniej wartości |
| oczekiwana obserwacja | kopiowanie poprzedniej wartości jest zabronione |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | zakaz cichego uzupełniania braków |
| podstawa w kontrakcie | 10.6, 10.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | status nie dotyczy pozytywnego zakazu; brak pozostaje jawny |

### CH-OHLCV-016 — brak tworzenia sztucznej świecy

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-016 |
| obszar | struktura i spójność świec |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | brakująca świeca w serii |
| scenariusz | próba cichego utworzenia sztucznej świecy |
| oczekiwana obserwacja | tworzenie sztucznej świecy jest zabronione |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | zakaz tworzenia brakującej świecy |
| podstawa w kontrakcie | 10.5, 10.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | zakaz cichego uzupełniania serii |

### CH-OHLCV-017 — zachowanie jawnej informacji o częściowym rekordzie

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-017 |
| obszar | struktura i spójność świec |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | częściowy rekord świecy |
| scenariusz | zachowanie jawnej informacji o częściowym rekordzie |
| oczekiwana obserwacja | częściowość rekordu jest jawnie zachowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | częściowość rekordu pozostaje jawna |
| podstawa w kontrakcie | 10.4, 10.1 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | polityka dla częściowo brakujących świec nierozstrzygnięta |

### CH-OHLCV-019 — częściowa seria z zachowaniem jawnych braków

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-019 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | seria zawiera częściowe rekordy OHLC zachowane jawnie |
| scenariusz | walidacja serii z częściowymi rekordami |
| oczekiwana obserwacja | częściowość pozostaje jawna i jest raportowana |
| oczekiwany status chart | CHART_INCOMPLETE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | dokładne warunki CHART_INCOMPLETE wymagają decyzji właściciela |
| podstawa w kontrakcie | 10.4, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status nazwany, ale reguła wyzwalania pozostaje otwarta |

### CH-OHLCV-020 — uszkodzona seria OHLC

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-020 |
| obszar | struktura i spójność świec |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | seria z naruszonymi relacjami OHLC i niezgodnościami strukturalnymi |
| scenariusz | walidacja serii z uszkodzeniami OHLC |
| oczekiwana obserwacja | uszkodzenia są jawnie raportowane |
| oczekiwany status chart | CHART_SERIES_BROKEN |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | dokładne warunki CHART_SERIES_BROKEN wymagają decyzji właściciela |
| podstawa w kontrakcie | 10.9, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | różnica względem CHART_INCOMPLETE pozostaje nierozstrzygnięta |

---

## 13. MACIERZ WOLUMENU

### CH-VOL-001 — dodatni wolumen

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-001 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | volume dodatni numeryczny |
| scenariusz | walidacja dodatniego wolumenu |
| oczekiwana obserwacja | dodatni wolumen jest poprawnie zachowany |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — wolumen poprawny |
| podstawa w kontrakcie | 9.2, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | wartości dodatnie są normalne |

### CH-VOL-002 — volume=0

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-002 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | pojedyncza świeca z volume=0 |
| scenariusz | walidacja wolumenu zero |
| oczekiwana obserwacja | zero jest zachowane jako prawidłowa wartość |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — zero nie jest błędem |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | zakaz automatycznego CHART_BAD_VOLUME i odrzucenia Observation |

### CH-VOL-003 — kilka kolejnych świec z volume=0

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-003 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | kilka kolejnych świec z volume=0 |
| scenariusz | walidacja ciągu zer |
| oczekiwana obserwacja | każde zero jest zachowane jako prawidłowa wartość |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — zero nie jest błędem |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | zakaz automatycznego CHART_BAD_VOLUME |

### CH-VOL-004 — mieszanina świec z wolumenem dodatnim i zerowym

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-004 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | mieszanina wolumenu dodatniego i zerowego |
| scenariusz | walidacja mieszaniny wolumenu |
| oczekiwana obserwacja | wartości dodatnie i zera są zachowane oddzielnie |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — zero nie jest błędem |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | zero nie psuje serii |

### CH-VOL-005 — brak pola wolumenu

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-005 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | tablica volume nieobecna |
| scenariusz | walidacja bez pola volume |
| oczekiwana obserwacja | brak pola volume jest jawnie raportowany jako błąd wolumenu |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wolumenu blokuje serię |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak pola to błąd wolumenu |

### CH-VOL-006 — volume=null

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-006 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | volume null |
| scenariusz | walidacja volume null |
| oczekiwana obserwacja | null jest jawnie raportowany jako błąd wolumenu |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | volume null blokuje serię |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | null to błąd wolumenu |

### CH-VOL-007 — wolumen nienumeryczny

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-007 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | volume nienumeryczny |
| scenariusz | walidacja wolumenu nienumerycznego |
| oczekiwana obserwacja | wartość nienumeryczna jest jawnie raportowana jako błąd wolumenu |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | wolumen nienumeryczny blokuje serię |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | wartość nienumeryczna to błąd wolumenu |

### CH-VOL-008 — wolumen ujemny

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-008 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | volume ujemny |
| scenariusz | walidacja wolumenu ujemnego |
| oczekiwana obserwacja | wartość ujemna jest jawnie raportowana jako błąd wolumenu |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | wolumen ujemny blokuje serię |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | wartość ujemna to błąd wolumenu |

### CH-VOL-009 — tablica wolumenu o niewłaściwej długości

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-009 |
| obszar | wolumen |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | tablica volume o długości niezgodnej z pozostałymi |
| scenariusz | walidacja długości tablicy wolumenu |
| oczekiwana obserwacja | niezgodna długość uniemożliwia przypisanie wolumenu do świecy |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | niezgodna długość blokuje przypisanie wolumenu |
| podstawa w kontrakcie | 5.6, 15 |
| stan decyzji | rozstrzygnięty |
| uwagi | niezgodna długość uniemożliwia przypisanie |

---

## 14. MACIERZ TIMESTAMPÓW I SESJI

### CH-TIME-001 — timestampy rosnące

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-001 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | timestampy rosnące i jednoznaczne |
| scenariusz | walidacja kolejności czasowej |
| oczekiwana obserwacja | jednoznaczna kolejność czasowa jest potwierdzona |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — kolejność poprawna |
| podstawa w kontrakcie | 10, 13 |
| stan decyzji | rozstrzygnięty |
| uwagi | seria po normalizacji ma jednoznaczną kolejność |

### CH-TIME-002 — timestampy w odwrotnej kolejności

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-002 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | timestampy malejące |
| scenariusz | walidacja odwrotnej kolejności |
| oczekiwana obserwacja | odwrotna kolejność jest jawnie raportowana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak jednoznacznej kolejności blokuje serię |
| podstawa w kontrakcie | 10, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status niejednoznaczny |

### CH-TIME-003 — duplikaty timestampów

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-003 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | co najmniej jeden duplikat timestampu |
| scenariusz | walidacja duplikatów |
| oczekiwana obserwacja | duplikaty są wykrywane i raportowane |
| oczekiwany status chart | CHART_DUPLICATES |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | duplikaty blokują jednoznaczną serię |
| podstawa w kontrakcie | 10.3, 13 |
| stan decyzji | rozstrzygnięty |
| uwagi | duplikaty mają status CHART_DUPLICATES |

### CH-TIME-004 — nieprawidłowy timestamp

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-004 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | timestamp nienumeryczny albo spoza poprawnego zakresu |
| scenariusz | walidacja nieprawidłowego timestampu |
| oczekiwana obserwacja | nieprawidłowy timestamp jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | nieprawidłowy timestamp blokuje porządek czasowy |
| podstawa w kontrakcie | 10, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status niejednoznaczny |

### CH-TIME-005 — brak timestampu dla świecy

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-005 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | świeca bez powiązanego timestampu |
| scenariusz | walidacja przypisania timestampu |
| oczekiwana obserwacja | brak timestampu jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak timestampu blokuje przypisanie świecy |
| podstawa w kontrakcie | 10, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status niejednoznaczny |

### CH-TIME-006 — timestamp bez odpowiadającego rekordu OHLCV

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-006 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | timestamp bez powiązanego rekordu OHLCV |
| scenariusz | walidacja powiązania timestampu z OHLCV |
| oczekiwana obserwacja | osierocony timestamp jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | osierocony timestamp blokuje spójność serii |
| podstawa w kontrakcie | 10, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status niejednoznaczny |

### CH-TIME-007 — rekord OHLCV bez odpowiadającego timestampu

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-007 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | rekord OHLCV bez powiązanego timestampu |
| scenariusz | walidacja powiązania OHLCV z timestampem |
| oczekiwana obserwacja | osierocony rekord OHLCV jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | osierocony rekord blokuje spójność serii |
| podstawa w kontrakcie | 10, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | status niejednoznaczny |

### CH-TIME-008 — nieregularny odstęp wymagający oceny

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-008 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | nieregularne odstępy między timestampami |
| scenariusz | ocena nieregularnych odstępów |
| oczekiwana obserwacja | nieregularność jest raportowana; nie zatwierdza się tolerancji interwałów |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | tolerancja interwałów i kalendarz wymagają decyzji |
| podstawa w kontrakcie | 13, 14, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | nie zatwierdza się tolerancji interwałów |

### CH-TIME-009 — brak danych w weekend

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-009 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | brak świec w dniach weekendowych |
| scenariusz | ocena braku danych w weekend |
| oczekiwana obserwacja | weekend nie jest automatycznie dziurą w danych |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | kalendarz sesji WSE wymaga decyzji |
| podstawa w kontrakcie | 10.7, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | weekend albo dzień bez sesji nie jest automatycznie dziurą |

### CH-TIME-010 — brak danych w święto

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-010 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | brak świec w dniu świątecznym |
| scenariusz | ocena braku danych w święto |
| oczekiwana obserwacja | dzień bez sesji nie jest automatycznie dziurą |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | kalendarz świąt wymaga decyzji |
| podstawa w kontrakcie | 10.7, 13 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | kalendarz WSE nie jest zatwierdzony |

### CH-TIME-011 — brak sesji

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-011 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | brak sesji w dniu roboczym |
| scenariusz | ocena braku sesji |
| oczekiwana obserwacja | brak sesji nie jest automatycznie dziurą ani błędem |
| oczekiwany status chart | CHART_BAD_SESSION |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | warunki CHART_BAD_SESSION wymagają decyzji |
| podstawa w kontrakcie | 10.8, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | dokładne warunki CHART_BAD_SESSION nierozstrzygnięte |

### CH-TIME-012 — świeca poza oczekiwaną sesją

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-012 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | świeca oznaczona czasem poza oczekiwaną sesją |
| scenariusz | ocena świecy poza sesją |
| oczekiwana obserwacja | świeca poza sesją jest raportowana |
| oczekiwany status chart | CHART_BAD_SESSION |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | warunki CHART_BAD_SESSION wymagają decyzji |
| podstawa w kontrakcie | 10.8, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | kalendarz sesji nie jest zatwierdzony |

### CH-TIME-013 — zmiana czasu letniego i zimowego

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-013 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | seria obejmuje zmianę czasu letniego/zimowego |
| scenariusz | ocena zmiany czasu |
| oczekiwana obserwacja | zmiana czasu jest rozpoznana bez wymyślania tolerancji |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | zasady stref czasowych i sesji wymagają decyzji |
| podstawa w kontrakcie | 13, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | strefy czasowe i zmiany czasu nie są zatwierdzone |

### CH-TIME-014 — konflikt strefy czasowej

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-014 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | strefa czasowa metadanych stoi w konflikcie z timestampami |
| scenariusz | ocena konfliktu strefy czasowej |
| oczekiwana obserwacja | konflikt strefy jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | interpretacja strefy wymaga decyzji |
| podstawa w kontrakcie | 11, 13, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | konflikt strefy nie ma zatwierdzonego statusu |

### CH-TIME-015 — rozróżnienie braku sesji, braku świecy i świecy z zerowym wolumenem

| Pole | Wartość |
|------|---------|
| ID | CH-TIME-015 |
| obszar | timestampy, kolejność i sesje |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | seria zawiera brak sesji, brak świecy oraz świecę z volume=0 |
| scenariusz | rozróżnienie trzech sytuacji |
| oczekiwana obserwacja | trzy sytuacje pozostają rozróżnione |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | rozpoznanie braku sesji zależy od kalendarza |
| podstawa w kontrakcie | 10.8, 13 |
| stan decyzji | częściowo wymaga decyzji właściciela |
| uwagi | rozróżnienie strukturalne jest offline; kalendarz sesji nie jest zatwierdzony |

---

## 15. MACIERZ DŁUGOŚCI I KOMPLETNOŚCI HISTORII

### CH-HIST-001 — pełna dostępna historia obejmująca co najmniej 52 tygodnie

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-001 |
| obszar | długość i kompletność historii |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | historia dzienna co najmniej 52 tygodnie, poprawna |
| scenariusz | walidacja pełnej historii |
| oczekiwana obserwacja | pełna historia jest uznana za wystarczający kontekst |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — historia wystarczająca |
| podstawa w kontrakcie | 14, 16 |
| stan decyzji | rozstrzygnięty |
| uwagi | 52 tygodnie to zatwierdzony kontekst |

### CH-HIST-002 — historia krótsza niż 52 tygodnie, ale zawierająca poprawne dane

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-002 |
| obszar | długość i kompletność historii |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | poprawna historia krótsza niż 52 tygodnie |
| scenariusz | walidacja krótkiej, poprawnej historii |
| oczekiwana obserwacja | instrument wchodzi do Observation; brak automatycznego odrzucenia |
| oczekiwany status chart | CHART_HISTORY_TOO_SHORT |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | CHART_HISTORY_TOO_SHORT nie blokuje Observation |
| podstawa w kontrakcie | 5.5, 16, 17.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | Baseline w zakresie rzeczywiście dostępnych danych |

### CH-HIST-003 — historia krótsza niż wymaganie konkretnego wskaźnika

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-003 |
| obszar | długość i kompletność historii |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | seria krótsza niż wymaganie wskaźnika |
| scenariusz | ocena gotowości wskaźnika |
| oczekiwana obserwacja | wskaźnik nie otrzymuje danych, jeżeli seria jest za krótka |
| oczekiwany status chart | CHART_HISTORY_TOO_SHORT |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | wskaźnik wymagający dłuższej serii nie jest gotowy |
| podstawa w kontrakcie | 5.5, 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | wymagania długości wynikają z rzeczywistych kontraktów wskaźników |

### CH-HIST-004 — historia wystarczająca dla jednego wskaźnika i niewystarczająca dla innego

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-004 |
| obszar | długość i kompletność historii |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | seria wystarcza dla wskaźnika A, nie wystarcza dla wskaźnika B |
| scenariusz | indywidualna ocena gotowości wskaźników |
| oczekiwana obserwacja | gotowość dotyczy indywidualnych wskaźników, nie całego instrumentu |
| oczekiwany status chart | CHART_HISTORY_TOO_SHORT |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | brak gotowości technicznej nie jest brakiem instrumentu |
| podstawa w kontrakcie | 5.5, 18, 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | ocena wskaźników indywidualnie |

### CH-HIST-005 — pojedyncza poprawna świeca

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-005 |
| obszar | długość i kompletność historii |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | seria zawiera jedną poprawną świecę |
| scenariusz | walidacja pojedynczej świecy |
| oczekiwana obserwacja | seria jest poprawna, ale ograniczona do jednej świecy |
| oczekiwany status chart | CHART_HISTORY_TOO_SHORT |
| Observation ready | TAK |
| Baseline ready | WARUNKOWO |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | gotowość techniczna ograniczona dla większości wskaźników |
| podstawa w kontrakcie | 5.5, 16, 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | Baseline w zakresie dostępnych danych |

### CH-HIST-006 — pusta historia

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-006 |
| obszar | długość i kompletność historii |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | brak jakiejkolwiek świecy |
| scenariusz | walidacja pustej historii |
| oczekiwana obserwacja | pusta historia jest raportowana jako brak danych |
| oczekiwany status chart | CHART_NO_DATA |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak danych blokuje całą ścieżkę |
| podstawa w kontrakcie | 9.3, 14 |
| stan decyzji | rozstrzygnięty |
| uwagi | pusta seria to brak danych |

### CH-HIST-007 — historia zawierająca częściowe świece

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-007 |
| obszar | długość i kompletność historii |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | seria zawiera częściowe świece |
| scenariusz | walidacja częściowych świec |
| oczekiwana obserwacja | częściowość pozostaje jawna |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | polityka dla częściowych świec wymaga decyzji |
| podstawa w kontrakcie | 10.4, 14, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | polityka dla częściowo brakujących świec nierozstrzygnięta |

### CH-HIST-008 — historia z duplikatami

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-008 |
| obszar | długość i kompletność historii |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | historia zawiera duplikaty timestampów |
| scenariusz | walidacja duplikatów w historii |
| oczekiwana obserwacja | duplikaty są wykrywane i raportowane |
| oczekiwany status chart | CHART_DUPLICATES |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | duplikaty blokują jednoznaczną serię |
| podstawa w kontrakcie | 14, 13 |
| stan decyzji | rozstrzygnięty |
| uwagi | duplikaty mają status CHART_DUPLICATES |

### CH-HIST-009 — historia z lukami wymagającymi kalendarza sesji

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-009 |
| obszar | długość i kompletność historii |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | przerwy w serii wymagające kalendarza sesji |
| scenariusz | odróżnienie luki od dnia bez sesji |
| oczekiwana obserwacja | przerwa jest raportowana bez wymyślania kalendarza |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | kalendarz sesji wymaga decyzji |
| podstawa w kontrakcie | 13, 14, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | zasady rozpoznania faktycznej dziury nierozstrzygnięte |

### CH-HIST-010 — dostępna historia dzienna bez intraday

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-010 |
| obszar | długość i kompletność historii |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | historia dzienna obecna, intraday nieobecna |
| scenariusz | ocena posiadania wyłącznie historii dziennej |
| oczekiwana obserwacja | brak intraday nie jest automatycznym błędem |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | wymagany zakres intraday wymaga decyzji |
| podstawa w kontrakcie | 8.2, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | dokładne kombinacje range i interval nierozstrzygnięte |

### CH-HIST-011 — dostępna historia intraday bez wystarczającej historii dziennej

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-011 |
| obszar | długość i kompletność historii |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | historia intraday obecna, dzienna niewystarczająca |
| scenariusz | ocena braku wystarczającej historii dziennej |
| oczekiwana obserwacja | brak wystarczającej historii dziennej jest raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | wymagany zakres dzienny wymaga decyzji |
| podstawa w kontrakcie | 8.2, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | wymagany zakres historii dziennej nierozstrzygnięty |

### CH-HIST-012 — brak zatwierdzonego range i interval

| Pole | Wartość |
|------|---------|
| ID | CH-HIST-012 |
| obszar | długość i kompletność historii |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | próba użycia konkretnej konfiguracji range/interval |
| scenariusz | wybór range i interval |
| oczekiwana obserwacja | żadna konfiguracja range/interval nie jest wymyślana |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | konfiguracja range i interval wymaga decyzji |
| podstawa w kontrakcie | 8.2, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | dokładne kombinacje range i interval nierozstrzygnięte |

---

## 16. MACIERZ ZGODNOŚCI SCREENER–CHART

### CH-CROSS-001 — zgodny symbol

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-001 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | symbol screenera i chart zgodny |
| scenariusz | porównanie symbolu screenera i chart |
| oczekiwana obserwacja | symbol jest spójny |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — symbol zgodny |
| podstawa w kontrakcie | 7, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | spójność symbolu potwierdzona |

### CH-CROSS-002 — konflikt symbolu

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-002 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | symbol screenera i chart różny |
| scenariusz | porównanie symbolu |
| oczekiwana obserwacja | konflikt symbolu jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt symbolu blokuje przyjęcie |
| podstawa w kontrakcie | 11, 7 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak zatwierdzonego statusu dla konfliktu symbolu |

### CH-CROSS-003 — zgodny typ

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-003 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | typ screenera i chart zgodny jako EQUITY |
| scenariusz | porównanie typu |
| oczekiwana obserwacja | typ EQUITY jest spójny |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — typ zgodny |
| podstawa w kontrakcie | 7.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | typ spójny |

### CH-CROSS-004 — konflikt typu

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-004 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | typ screenera i chart różny albo inny niż EQUITY |
| scenariusz | porównanie typu |
| oczekiwana obserwacja | konflikt typu jest jawnie raportowany |
| oczekiwany status chart | CHART_TYPE_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt typu blokuje przyjęcie jako akcja |
| podstawa w kontrakcie | 7.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | typ inny niż EQUITY to konflikt |

### CH-CROSS-005 — zgodna waluta

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-005 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | waluta screenera i chart zgodna jako PLN |
| scenariusz | porównanie waluty |
| oczekiwana obserwacja | waluta PLN jest spójna |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — waluta zgodna |
| podstawa w kontrakcie | 7.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | waluta spójna |

### CH-CROSS-006 — konflikt waluty

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-006 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | waluta screenera i chart różna |
| scenariusz | porównanie waluty |
| oczekiwana obserwacja | konflikt waluty jest jawnie raportowany |
| oczekiwany status chart | CHART_CURRENCY_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt waluty blokuje przyjęcie |
| podstawa w kontrakcie | 7.1, 11 |
| stan decyzji | rozstrzygnięty |
| uwagi | jawna inna waluta to konflikt |

### CH-CROSS-007 — zgodna bieżąca cena przy porównywalnym czasie

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-007 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | cena screenera i chart zgodna przy porównywalnym czasie |
| scenariusz | porównanie ceny przy porównywalnym czasie |
| oczekiwana obserwacja | cena jest spójna przy porównywalnym czasie |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — cena spójna |
| podstawa w kontrakcie | 10, 12 |
| stan decyzji | rozstrzygnięty |
| uwagi | nie wymaga dokładnej równości bez zatwierdzonej tolerancji |

### CH-CROSS-008 — różna cena przy różnym czasie snapshotu

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-008 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | ceny różne przy różnym czasie snapshotu |
| scenariusz | porównanie ceny przy różnym czasie |
| oczekiwana obserwacja | różnica uwzględnia różnicę czasu, bez konfliktu |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | ocena różnicy wymaga porównywalnego czasu |
| podstawa w kontrakcie | 10, 12, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | zasady porównania ceny nierozstrzygnięte |

### CH-CROSS-009 — brak ceny po jednej stronie

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-009 |
| obszar | zgodność screener–chart |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | cena obecna w screenerze, brak w chart, albo odwrotnie |
| scenariusz | porównanie ceny przy braku po jednej stronie |
| oczekiwana obserwacja | brak ceny po jednej stronie jest jawnie raportowany |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak ceny po jednej stronie wymaga oceny |
| podstawa w kontrakcie | 10, 12, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | zasady porównania ceny nierozstrzygnięte |

### CH-CROSS-010 — instrument obecny w screenerze, ale bez danych chart

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-010 |
| obszar | zgodność screener–chart |
| etap wykonania | NETWORK_LATER |
| warunek wejściowy | symbol w screenerze, chart bez użytecznych danych |
| scenariusz | ocena braku danych chart |
| oczekiwana obserwacja | brak danych chart jest raportowany bez odrzucenia screenera |
| oczekiwany status chart | CHART_NO_DATA |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak danych chart blokuje dalszą ścieżkę, nie sam screener |
| podstawa w kontrakcie | 6, 9.3 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak chart nie unieważnia discovery screenera |

### CH-CROSS-011 — dane chart dla symbolu, którego nie ma w bieżącym dynamicznym uniwersum

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-011 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | dane chart dla symbolu spoza bieżącego uniwersum |
| scenariusz | przyjęcie chart dla symbolu spoza uniwersum |
| oczekiwana obserwacja | symbol spoza uniwersum nie jest przyjęty jako wejście cyklu |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | symbol spoza uniwersum nie wchodzi do cyklu |
| podstawa w kontrakcie | 5.3, 6, 7.2 |
| stan decyzji | rozstrzygnięty |
| uwagi | wejście chart wyłącznie z bieżącego uniwersum |

### CH-CROSS-012 — brak pola segmentu GPW/NC po obu stronach

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-012 |
| obszar | zgodność screener–chart |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | brak pola segmentu GPW/NC w screenerze i chart |
| scenariusz | weryfikacja braku segmentu po obu stronach |
| oczekiwana obserwacja | brak segmentu nie jest konfliktem i nie jest wymagany |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — segment nie jest częścią kontraktu |
| podstawa w kontrakcie | 5.2, 7 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak segmentu po obu stronach nie jest błędem |

---

## 17. MACIERZ GOTOWOŚCI MODUŁÓW

### CH-READY-001 — pełna poprawna seria

| Pole | Wartość |
|------|---------|
| ID | CH-READY-001 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | pełna poprawna seria OHLCV z poprawnymi metadanymi |
| scenariusz | ocena gotowości wszystkich modułów |
| oczekiwana obserwacja | wszystkie flagi gotowości ustawione jako TAK |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — pełna gotowość |
| podstawa w kontrakcie | 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | pełna zwalidowana seria |

### CH-READY-002 — poprawne dane bieżące z krótką historią

| Pole | Wartość |
|------|---------|
| ID | CH-READY-002 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | poprawne dane bieżące, historia krótsza niż 52 tygodnie |
| scenariusz | ocena gotowości przy krótkiej historii |
| oczekiwana obserwacja | Observation gotowe, Technical Engine warunkowo |
| oczekiwany status chart | CHART_HISTORY_TOO_SHORT |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | gotowość techniczna ograniczona, nie cały instrument |
| podstawa w kontrakcie | 5.5, 16, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak automatycznego odrzucenia instrumentu |

### CH-READY-003 — poprawna historia bez bieżącej ceny

| Pole | Wartość |
|------|---------|
| ID | CH-READY-003 |
| obszar | gotowość modułów |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | poprawna historia, brak regularMarketPrice |
| scenariusz | ocena gotowości bez ceny bieżącej |
| oczekiwana obserwacja | brak ceny bieżącej jest zachowany jako fakt |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak ceny bieżącej wymaga decyzji |
| podstawa w kontrakcie | 12, 18, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak ceny bieżącej nie ma zatwierdzonej reguły gotowości |

### CH-READY-004 — bieżąca cena bez użytecznej historii

| Pole | Wartość |
|------|---------|
| ID | CH-READY-004 |
| obszar | gotowość modułów |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | poprawna cena bieżąca, brak albo pusta historia |
| scenariusz | ocena gotowości bez użytecznej historii |
| oczekiwana obserwacja | brak użytecznej historii jest zachowany jako fakt |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | brak użytecznej historii wymaga decyzji |
| podstawa w kontrakcie | 14, 18, 25 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | granica między danymi dla Observation i Technical Engine nierozstrzygnięta |

### CH-READY-005 — konflikt typu

| Pole | Wartość |
|------|---------|
| ID | CH-READY-005 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | typ instrumentu inny niż EQUITY |
| scenariusz | ocena gotowości przy konflikcie typu |
| oczekiwana obserwacja | wszystkie flagi gotowości ustawione jako NIE |
| oczekiwany status chart | CHART_TYPE_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt typu blokuje całą ścieżkę |
| podstawa w kontrakcie | 11, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | dane nie przechodzą do modułów |

### CH-READY-006 — konflikt waluty

| Pole | Wartość |
|------|---------|
| ID | CH-READY-006 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | waluta inna niż PLN |
| scenariusz | ocena gotowości przy konflikcie waluty |
| oczekiwana obserwacja | wszystkie flagi gotowości ustawione jako NIE |
| oczekiwany status chart | CHART_CURRENCY_CONFLICT |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | konflikt waluty blokuje całą ścieżkę |
| podstawa w kontrakcie | 11, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | dane nie przechodzą do modułów |

### CH-READY-007 — brak danych

| Pole | Wartość |
|------|---------|
| ID | CH-READY-007 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | brak danych chart |
| scenariusz | ocena gotowości przy braku danych |
| oczekiwana obserwacja | wszystkie flagi gotowości ustawione jako NIE |
| oczekiwany status chart | CHART_NO_DATA |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak danych blokuje całą ścieżkę |
| podstawa w kontrakcie | 9.3, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak danych nie tworzy obserwacji |

### CH-READY-008 — częściowa seria

| Pole | Wartość |
|------|---------|
| ID | CH-READY-008 |
| obszar | gotowość modułów |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | seria częściowa |
| scenariusz | ocena gotowości przy częściowej serii |
| oczekiwana obserwacja | częściowość jest zachowana jako fakt |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | polityka dla częściowych serii wymaga decyzji |
| podstawa w kontrakcie | 14, 18, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | warunki CHART_INCOMPLETE nierozstrzygnięte |

### CH-READY-009 — duplikaty

| Pole | Wartość |
|------|---------|
| ID | CH-READY-009 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | seria z duplikatami timestampów |
| scenariusz | ocena gotowości przy duplikatach |
| oczekiwana obserwacja | duplikaty blokują gotowość, wszystkie flagi NIE |
| oczekiwany status chart | CHART_DUPLICATES |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | duplikaty blokują całą ścieżkę |
| podstawa w kontrakcie | 14, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | duplikaty dają CHART_DUPLICATES |

### CH-READY-010 — volume=0

| Pole | Wartość |
|------|---------|
| ID | CH-READY-010 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | seria zawiera volume=0 |
| scenariusz | ocena gotowości przy wolumenie zerowym |
| oczekiwana obserwacja | zero nie blokuje gotowości |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak — zero nie jest błędem |
| podstawa w kontrakcie | 5.6, 15, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | zero nie daje CHART_BAD_VOLUME |

### CH-READY-011 — brak wolumenu

| Pole | Wartość |
|------|---------|
| ID | CH-READY-011 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | brak pola wolumenu |
| scenariusz | ocena gotowości bez wolumenu |
| oczekiwana obserwacja | brak wolumenu blokuje gotowość |
| oczekiwany status chart | CHART_BAD_VOLUME |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | brak wolumenu blokuje całą ścieżkę |
| podstawa w kontrakcie | 5.6, 15, 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | brak wolumenu to błąd wolumenu |

### CH-READY-012 — niewystarczająca historia dla części wskaźników

| Pole | Wartość |
|------|---------|
| ID | CH-READY-012 |
| obszar | gotowość modułów |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | seria wystarcza dla części wskaźników |
| scenariusz | indywidualna ocena gotowości wskaźników |
| oczekiwana obserwacja | gotowość techniczna jest warunkowa, bez odrzucenia instrumentu |
| oczekiwany status chart | CHART_HISTORY_TOO_SHORT |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | tylko wskaźniki wymagające dłuższej serii |
| podstawa w kontrakcie | 5.5, 18, 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | ocena indywidualna według wymagań wskaźników |

### CH-READY-013 — dane niezwalidowane

| Pole | Wartość |
|------|---------|
| ID | CH-READY-013 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | dane nieprzepuszczone przez walidację |
| scenariusz | próba przekazania danych do modułów |
| oczekiwana obserwacja | dane niezwalidowane nie trafiają do żadnego modułu |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | dane niezwalidowane blokują całą ścieżkę |
| podstawa w kontrakcie | 18, 23 |
| stan decyzji | rozstrzygnięty |
| uwagi | dane nieprzepuszczone przez walidację nie mogą trafić do AI |

### CH-READY-014 — dane zwalidowane tylko dla wcześniejszego etapu

| Pole | Wartość |
|------|---------|
| ID | CH-READY-014 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | dane zwalidowane dla Observation, ale nie dla Technical Engine |
| scenariusz | przekazanie dalej bez pełnej walidacji |
| oczekiwana obserwacja | dane nie trafiają dalej bez wymaganej walidacji |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | moduły wymagające wyższego etapu walidacji |
| podstawa w kontrakcie | 18, 21, 23 |
| stan decyzji | rozstrzygnięty |
| uwagi | AI i Telegram nie otrzymują danych bez wymaganych wcześniejszych etapów |

### CH-READY-015 — rozdzielna gotowość Observation

| Pole | Wartość |
|------|---------|
| ID | CH-READY-015 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | dane po normalizacji i walidacji chart |
| scenariusz | oddzielna flaga gotowości do Observation |
| oczekiwana obserwacja | flaga Observation jest niezależna od pozostałych |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak przy pełnej poprawności |
| podstawa w kontrakcie | 18 |
| stan decyzji | rozstrzygnięty |
| uwagi | niezależne flagi gotowości |

### CH-READY-016 — rozdzielna gotowość Baseline

| Pole | Wartość |
|------|---------|
| ID | CH-READY-016 |
| obszar | gotowość modułów |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | zwalidowana seria dla Baseline |
| scenariusz | oddzielna flaga gotowości do Baseline |
| oczekiwana obserwacja | flaga Baseline jest niezależna |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak przy pełnej poprawności |
| podstawa w kontrakcie | 18, 20 |
| stan decyzji | rozstrzygnięty |
| uwagi | Baseline w zakresie rzeczywiście dostępnych danych |

### CH-READY-017 — rozdzielna gotowość Technical Engine

| Pole | Wartość |
|------|---------|
| ID | CH-READY-017 |
| obszar | gotowość modułów |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | zwalidowana seria OHLCV o wystarczającej długości |
| scenariusz | flaga gotowości do Technical Engine |
| oczekiwana obserwacja | flaga zależy od długości i jakości serii |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak przy wystarczającej serii |
| podstawa w kontrakcie | 18, 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | gotowość zależy od rzeczywistych wymagań wskaźników |

### CH-READY-018 — rozdzielna gotowość Hunter

| Pole | Wartość |
|------|---------|
| ID | CH-READY-018 |
| obszar | gotowość modułów |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | przygotowane dane, Baseline, zmiana i wyniki techniczne |
| scenariusz | flaga gotowości do Hunter |
| oczekiwana obserwacja | flaga Hunter zależy od wcześniejszych etapów |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak przy pełnej poprawności |
| podstawa w kontrakcie | 18, 22 |
| stan decyzji | rozstrzygnięty |
| uwagi | Hunter wykorzystuje przygotowane dane |

### CH-READY-019 — rozdzielna gotowość MasterEngine

| Pole | Wartość |
|------|---------|
| ID | CH-READY-019 |
| obszar | gotowość modułów |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | dane przekazane przez wcześniejsze etapy |
| scenariusz | flaga gotowości do MasterEngine |
| oczekiwana obserwacja | flaga MasterEngine zależy od wcześniejszych etapów |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | brak przy pełnej poprawności |
| podstawa w kontrakcie | 18, 22 |
| stan decyzji | rozstrzygnięty |
| uwagi | MasterEngine koordynuje dalszą analizę |

### CH-READY-020 — rozdzielna gotowość GPT-4o

| Pole | Wartość |
|------|---------|
| ID | CH-READY-020 |
| obszar | gotowość modułów |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | pełny zwalidowany kontekst |
| scenariusz | flaga gotowości do GPT-4o |
| oczekiwana obserwacja | GPT-4o otrzymuje wyłącznie zwalidowane dane |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | AI na końcu ścieżki |
| podstawa w kontrakcie | 5.7, 18, 23 |
| stan decyzji | rozstrzygnięty |
| uwagi | AI nie uzupełnia braków |

### CH-READY-021 — rozdzielna gotowość Telegrama

| Pole | Wartość |
|------|---------|
| ID | CH-READY-021 |
| obszar | gotowość modułów |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | wynik końcowego procesu decyzyjnego |
| scenariusz | flaga gotowości do Telegrama |
| oczekiwana obserwacja | Telegram otrzymuje dopiero wynik końcowy |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | Telegram na końcu procesu |
| podstawa w kontrakcie | 5.7, 23 |
| stan decyzji | rozstrzygnięty |
| uwagi | Telegram nie jest miejscem walidacji |

---

## 18. MACIERZ GRANIC ODPOWIEDZIALNOŚCI

### CH-BOUND-001 — warstwa chart tylko pobiera dane

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-001 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | wywołanie chart |
| scenariusz | sprawdzenie odpowiedzialności warstwy chart |
| oczekiwana obserwacja | warstwa chart nie przejmuje obowiązków innych modułów |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | brak — własność potwierdzona |
| podstawa w kontrakcie | 5.4, 19.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | warstwa chart pobiera i bezpiecznie przekazuje surowe dane |

### CH-BOUND-002 — parser nie zgaduje wartości

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-002 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | parsowanie odpowiedzi chart |
| scenariusz | sprawdzenie braku zgadywania |
| oczekiwana obserwacja | parser nie wymyśla ani nie uzupełnia wartości |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | brak zgadywania wartości |
| podstawa w kontrakcie | 10.1, 19.2 |
| stan decyzji | rozstrzygnięty |
| uwagi | parser zachowuje braki jawnie |

### CH-BOUND-003 — walidator nie zapisuje Observation

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-003 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | wynik walidacji chart |
| scenariusz | sprawdzenie, że walidator nie tworzy trwałej Observation |
| oczekiwana obserwacja | walidator nie zapisuje Observation ani Baseline |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | oddzielenie walidacji od trwałości |
| podstawa w kontrakcie | 19.3, 20 |
| stan decyzji | rozstrzygnięty |
| uwagi | walidator tworzy wynik i flagi, nie Observation |

### CH-BOUND-004 — RuntimeService zarządza cyklem Observation

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-004 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | cykl życia Observation |
| scenariusz | sprawdzenie własności cyklu Observation |
| oczekiwana obserwacja | RuntimeService pozostaje właścicielem cyklu |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | własność cyklu pozostaje po stronie RuntimeService |
| podstawa w kontrakcie | 5.4, 19.4, 20 |
| stan decyzji | rozstrzygnięty |
| uwagi | RuntimeService decyduje o przekazaniu poprawnych danych |

### CH-BOUND-005 — HistoryRepository odpowiada za kontrakt zapisu

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-005 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | trwały zapis historii |
| scenariusz | sprawdzenie własności kontraktu zapisu |
| oczekiwana obserwacja | HistoryRepository jest właścicielem kontraktu zapisu |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | własność kontraktu zapisu |
| podstawa w kontrakcie | 5.4, 19.5, 20 |
| stan decyzji | rozstrzygnięty |
| uwagi | HistoryRepository właścicielem trwałego zapisu |

### CH-BOUND-006 — SQLiteHistoryRepository jest implementacją

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-006 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | implementacja trwałego zapisu |
| scenariusz | sprawdzenie roli SQLiteHistoryRepository |
| oczekiwana obserwacja | jest wyłącznie produkcyjną implementacją kontraktu |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | rola implementacji, nie właściciel kontraktu |
| podstawa w kontrakcie | 19.5 |
| stan decyzji | rozstrzygnięty |
| uwagi | HistoryRepository definiuje kontrakt, SQLite implementuje |

### CH-BOUND-007 — Technical Engine oblicza wskaźniki

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-007 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | zwalidowana seria OHLCV |
| scenariusz | sprawdzenie roli Technical Engine |
| oczekiwana obserwacja | Technical Engine sam oblicza wskaźniki, nie pobiera Yahoo |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | Technical Engine nie pobiera i nie zgaduje danych |
| podstawa w kontrakcie | 5.4, 19.6, 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | Technical Engine nie zgaduje brakujących świec |

### CH-BOUND-008 — Hunter nie przechowuje Observation

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-008 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | praca Huntera |
| scenariusz | sprawdzenie, że Hunter nie przechowuje Observation |
| oczekiwana obserwacja | Hunter nie jest magazynem Observation |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | oddzielenie Huntera od trwałości Observation |
| podstawa w kontrakcie | 19.7, 22 |
| stan decyzji | rozstrzygnięty |
| uwagi | Hunter nie naprawia danych rynkowych |

### CH-BOUND-009 — MasterEngine nie parsuje Yahoo

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-009 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | koordynacja analizy |
| scenariusz | sprawdzenie, że MasterEngine nie parsuje Yahoo |
| oczekiwana obserwacja | MasterEngine nie jest parserem Yahoo |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | oddzielenie MasterEngine od parsowania |
| podstawa w kontrakcie | 19.8, 22 |
| stan decyzji | rozstrzygnięty |
| uwagi | MasterEngine nie jest repozytorium historii |

### CH-BOUND-010 — GPT-4o nie uzupełnia braków

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-010 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | kontekst AI |
| scenariusz | sprawdzenie, że GPT-4o nie uzupełnia braków |
| oczekiwana obserwacja | AI nie uzupełnia brakujących danych rynkowych |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | AI nie naprawia historii ani nie zgaduje |
| podstawa w kontrakcie | 5.7, 23 |
| stan decyzji | rozstrzygnięty |
| uwagi | AI zastępuje żadnego walidatora |

### CH-BOUND-011 — Telegram nie wykonuje walidacji

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-011 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | przekazanie wyniku do Telegrama |
| scenariusz | sprawdzenie, że Telegram nie waliduje danych |
| oczekiwana obserwacja | Telegram nie jest miejscem walidacji |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | Telegram poza ścieżką walidacji |
| podstawa w kontrakcie | 5.7, 23 |
| stan decyzji | rozstrzygnięty |
| uwagi | Telegram otrzymuje wynik końcowy |

### CH-BOUND-012 — HunterResult nie staje się magazynem stanu

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-012 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | wynik Huntera |
| scenariusz | sprawdzenie, że HunterResult nie przenosi stanu |
| oczekiwana obserwacja | HunterResult nie przenosi surowego OHLCV ani Observation |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | HunterResult nie jest magazynem stanu |
| podstawa w kontrakcie | 19.9, 22 |
| stan decyzji | rozstrzygnięty |
| uwagi | HunterResult pozostaje modelem końcowej kwalifikacji |

### CH-BOUND-013 — MarketEvent, EventOutcome, SessionOutcome i CycleReport nie są Baseline

| Pole | Wartość |
|------|---------|
| ID | CH-BOUND-013 |
| obszar | granice odpowiedzialności |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | modele wynikowe |
| scenariusz | sprawdzenie, że modele nie są Baseline |
| oczekiwana obserwacja | modele nie są używane jako baseline ani Observation |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | oddzielenie modeli wynikowych od baseline |
| podstawa w kontrakcie | 19.9 |
| stan decyzji | rozstrzygnięty |
| uwagi | modele wynikowe nie są baseline'em ani stanem Observation |

---

## 19. MACIERZ BEZPIECZEŃSTWA I ARTEFAKTÓW

### CH-SEC-001 — brak wartości cookie w artefaktach

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-001 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | artefakty po walidacji |
| scenariusz | kontrola braku cookie |
| oczekiwana obserwacja | żaden artefakt nie zawiera wartości cookie |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | bezpieczeństwo artefaktów |
| podstawa w kontrakcie | 8, 29 |
| stan decyzji | rozstrzygnięty |
| uwagi | wartość cookie nie jest zapisywana |

### CH-SEC-002 — brak wartości crumb w artefaktach

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-002 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | artefakty po walidacji |
| scenariusz | kontrola braku crumb |
| oczekiwana obserwacja | żaden artefakt nie zawiera wartości crumb |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | bezpieczeństwo artefaktów |
| podstawa w kontrakcie | 8, 29 |
| stan decyzji | rozstrzygnięty |
| uwagi | wartość crumb nie jest zapisywana |

### CH-SEC-003 — brak sekretów

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-003 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | artefakty po walidacji |
| scenariusz | kontrola braku sekretów |
| oczekiwana obserwacja | żaden artefakt nie zawiera kluczy ani tokenów |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | bezpieczeństwo artefaktów |
| podstawa w kontrakcie | 29 |
| stan decyzji | rozstrzygnięty |
| uwagi | bez sekretów OpenAI, Tavily, Telegrama |

### CH-SEC-004 — bezpieczne parametry żądań

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-004 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | konstrukcja żądania chart |
| scenariusz | kontrola parametrów żądania |
| oczekiwana obserwacja | parametry nie zawierają sekretów ani konstrukcji symbolu |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | bezpieczeństwo żądania |
| podstawa w kontrakcie | 8.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | wyłącznie trasa /v8/finance/chart/{symbol} |

### CH-SEC-005 — oddzielenie surowej odpowiedzi od podsumowania

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-005 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | surowa odpowiedź i podsumowanie |
| scenariusz | oddzielenie surowej odpowiedzi od podsumowania |
| oczekiwana obserwacja | surowa odpowiedź jest przechowywana osobno |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | zachowanie surowego dowodu |
| podstawa w kontrakcie | 10.1, 26.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | surowa odpowiedź nie jest zastępowana podsumowaniem |

### CH-SEC-006 — brak nadpisania surowego dowodu przez podsumowanie

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-006 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | surowa odpowiedź i podsumowanie |
| scenariusz | próba nadpisania surowego dowodu |
| oczekiwana obserwacja | surowy dowód nie jest nadpisywany |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | zachowanie dowodu |
| podstawa w kontrakcie | 10.1, 26.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | surowy dowód pozostaje nienaruszony |

### CH-SEC-007 — zapis częściowych dowodów po kontrolowanym błędzie

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-007 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | kontrolowany błąd w trakcie przetwarzania |
| scenariusz | zapis częściowych dowodów |
| oczekiwana obserwacja | częściowe dowody są zachowane |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | zachowanie dowodów po błędzie |
| podstawa w kontrakcie | 9.3, 26.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | błąd nie usuwa zachowanych dowodów |

### CH-SEC-008 — poprawne UTF-8

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-008 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | zapis artefaktów |
| scenariusz | kontrola kodowania UTF-8 |
| oczekiwana obserwacja | artefakty są zapisane w poprawnym UTF-8 |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | poprawność kodowania |
| podstawa w kontrakcie | 26.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | ścisłe UTF-8, bez NUL i trailing whitespace |

### CH-SEC-009 — ponowny odczyt artefaktów

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-009 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | zapisane artefakty |
| scenariusz | ponowny odczyt artefaktów |
| oczekiwana obserwacja | artefakty dają się odczytać i są nienaruszone |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | odtwarzalność dowodów |
| podstawa w kontrakcie | 26.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | wynik możliwy do odtworzenia |

### CH-SEC-010 — liczba faktycznie wysłanych żądań zgodna z tabelą

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-010 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | OFFLINE_READY |
| warunek wejściowy | sztuczny transport zliczający żądania |
| scenariusz | porównanie liczby wysłanych żądań z tabelą |
| oczekiwana obserwacja | liczba żądań jest rozliczona zgodnie z tabelą |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | rozliczalność wywołań |
| podstawa w kontrakcie | 26.1 |
| stan decyzji | rozstrzygnięty |
| uwagi | każde faktycznie wysłane żądanie jest zliczone |

### CH-SEC-011 — brak retry i fallbacku bez osobnej zgody

| Pole | Wartość |
|------|---------|
| ID | CH-SEC-011 |
| obszar | brak sekretów i bezpieczne artefakty |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | błąd transportu lub HTTP |
| scenariusz | próba retry albo fallbacku |
| oczekiwana obserwacja | retry i fallback nie występują bez osobnej zgody |
| oczekiwany status chart | NIE DOTYCZY |
| Observation ready | NIE DOTYCZY |
| Baseline ready | NIE DOTYCZY |
| Technical Engine ready | NIE DOTYCZY |
| Hunter ready | NIE DOTYCZY |
| MasterEngine ready | NIE DOTYCZY |
| GPT-4o ready | NIE DOTYCZY |
| zakres blokady | polityka retry i fallbacku wymaga decyzji |
| podstawa w kontrakcie | 8.2, 29 |
| stan decyzji | rozstrzygnięty |
| uwagi | polityka retry, timeoutów i cache nie jest ustalona |

---

## 20. PRZYPADKI WIELOPROBLEMOWE

Poniższe przypadki zawierają więcej niż jeden jednoczesny problem. Pełna kolejność pierwszeństwa statusów nie została zatwierdzona, dlatego oczekiwany status pozostaje `NIEROZSTRZYGNIĘTE`, a przypadek wymaga decyzji właściciela. Walidator musi zachować wszystkie fakty równocześnie.

### CH-CROSS-013 — konflikt typu i brak historii

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-013 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | konflikt typu instrumentu oraz brak historii |
| scenariusz | łączna ocena konfliktu typu i braku historii |
| oczekiwana obserwacja | oba fakty zachowane równocześnie |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | pierwszeństwo statusów wymaga decyzji |
| podstawa w kontrakcie | 11, 14, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | CHART_TYPE_CONFLICT i brak historii muszą być zachowane |

### CH-CROSS-014 — konflikt waluty i duplikaty

| Pole | Wartość |
|------|---------|
| ID | CH-CROSS-014 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | konflikt waluty oraz duplikaty timestampów |
| scenariusz | łączna ocena konfliktu waluty i duplikatów |
| oczekiwana obserwacja | oba fakty zachowane równocześnie |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | pierwszeństwo statusów wymaga decyzji |
| podstawa w kontrakcie | 11, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | CHART_CURRENCY_CONFLICT i CHART_DUPLICATES muszą być zachowane |

### CH-CUR-011 — brak bieżącej ceny i krótka historia

| Pole | Wartość |
|------|---------|
| ID | CH-CUR-011 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | brak regularMarketPrice oraz historia krótsza niż 52 tygodnie |
| scenariusz | łączna ocena braku ceny i krótkiej historii |
| oczekiwana obserwacja | oba fakty zachowane równocześnie |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIEROZSTRZYGNIĘTE |
| Baseline ready | NIEROZSTRZYGNIĘTE |
| Technical Engine ready | NIEROZSTRZYGNIĘTE |
| Hunter ready | NIEROZSTRZYGNIĘTE |
| MasterEngine ready | NIEROZSTRZYGNIĘTE |
| GPT-4o ready | NIEROZSTRZYGNIĘTE |
| zakres blokady | pierwszeństwo statusów wymaga decyzji |
| podstawa w kontrakcie | 12, 16, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak ceny i CHART_HISTORY_TOO_SHORT muszą być zachowane |

### CH-VOL-010 — brak wolumenu i uszkodzona seria

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-010 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | brak wolumenu oraz uszkodzona seria OHLC |
| scenariusz | łączna ocena braku wolumenu i uszkodzeń |
| oczekiwana obserwacja | oba fakty zachowane równocześnie |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | pierwszeństwo statusów wymaga decyzji |
| podstawa w kontrakcie | 15, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | CHART_BAD_VOLUME i uszkodzenie OHLC muszą być zachowane |

### CH-TR-013 — HTTP error przed możliwością walidacji danych

| Pole | Wartość |
|------|---------|
| ID | CH-TR-013 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | NETWORK_LATER |
| warunek wejściowy | HTTP error uniemożliwia walidację |
| scenariusz | błąd HTTP przed oceną danych |
| oczekiwana obserwacja | błąd HTTP jest zachowany przed jakąkolwiek walidacją |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | status transportu wymaga decyzji |
| podstawa w kontrakcie | 9.3, 17.3 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | brak statusu transportu/HTTP |

### CH-OHLCV-018 — poprawne metadane, ale niepoprawne OHLC

| Pole | Wartość |
|------|---------|
| ID | CH-OHLCV-018 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | poprawne metadane, naruszone relacje OHLC |
| scenariusz | łączna ocena poprawnych meta i złych OHLC |
| oczekiwana obserwacja | oba fakty zachowane równocześnie |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | NIE |
| Baseline ready | NIE |
| Technical Engine ready | NIE |
| Hunter ready | NIE |
| MasterEngine ready | NIE |
| GPT-4o ready | NIE |
| zakres blokady | pierwszeństwo statusów wymaga decyzji |
| podstawa w kontrakcie | 11, 13, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | poprawne meta nie unieważnia złego OHLC |

### CH-VOL-011 — volume=0 razem z krótką historią

| Pole | Wartość |
|------|---------|
| ID | CH-VOL-011 |
| obszar | przypadki wieloproblemowe |
| etap wykonania | BLOCKED_BY_OWNER_DECISION |
| warunek wejściowy | volume=0 oraz historia krótsza niż 52 tygodnie |
| scenariusz | łączna ocena zera i krótkiej historii |
| oczekiwana obserwacja | zero pozostaje poprawne, krótka historia nie blokuje Observation |
| oczekiwany status chart | NIEROZSTRZYGNIĘTE |
| Observation ready | TAK |
| Baseline ready | WARUNKOWO |
| Technical Engine ready | WARUNKOWO |
| Hunter ready | WARUNKOWO |
| MasterEngine ready | WARUNKOWO |
| GPT-4o ready | WARUNKOWO |
| zakres blokady | łączny status wymaga pierwszeństwa statusów |
| podstawa w kontrakcie | 5.6, 16, 17.2 |
| stan decyzji | wymaga decyzji właściciela |
| uwagi | volume=0 nie daje CHART_BAD_VOLUME |

### CH-INT-001 — przekazanie zwalidowanej serii do Technical Engine

| Pole | Wartość |
|------|---------|
| ID | CH-INT-001 |
| obszar | późniejsza integracja |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | zwalidowana seria OHLCV z flagą gotowości |
| scenariusz | przekazanie serii do Technical Engine |
| oczekiwana obserwacja | Technical Engine otrzymuje wyłącznie zwalidowane dane |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | integracja po zatwierdzeniu kontraktu |
| podstawa w kontrakcie | 21 |
| stan decyzji | rozstrzygnięty |
| uwagi | kontrakt przekazania do modułów pozostaje otwarty |

### CH-INT-002 — trwały zapis Observation przez HistoryRepository

| Pole | Wartość |
|------|---------|
| ID | CH-INT-002 |
| obszar | późniejsza integracja |
| etap wykonania | INTEGRATION_LATER |
| warunek wejściowy | RuntimeService decyduje o zapisie Observation |
| scenariusz | trwały zapis Observation zgodnie z kontraktem |
| oczekiwana obserwacja | HistoryRepository wykonuje kontrakt zapisu |
| oczekiwany status chart | CHART_OK |
| Observation ready | TAK |
| Baseline ready | TAK |
| Technical Engine ready | TAK |
| Hunter ready | TAK |
| MasterEngine ready | TAK |
| GPT-4o ready | TAK |
| zakres blokady | integracja po zatwierdzeniu kontraktu |
| podstawa w kontrakcie | 19.4, 19.5, 20 |
| stan decyzji | rozstrzygnięty |
| uwagi | Sposób odtworzenia Observation po restarcie pozostaje nierozstrzygnięty |

---

## 21. MAPOWANIE STATUSÓW

Macierz używa wyłącznie zatwierdzonych roboczych statusów. Każdy zatwierdzony status występuje co najmniej raz.

| Status | Znaczenie | Występuje w przypadkach |
|--------|-----------|--------------------------|
| `CHART_OK` | poprawna seria lub poprawne metadane | CH-IN-001, CH-IN-006, CH-IN-007, CH-IN-012, CH-IN-013, CH-META-001, CH-META-003, CH-META-005, CH-META-007, CH-META-010, CH-META-011, CH-META-012, CH-META-013, CH-META-014, CH-META-015, CH-CUR-001, CH-CUR-005, CH-OHLCV-001, CH-OHLCV-002, CH-VOL-001, CH-VOL-002, CH-VOL-003, CH-VOL-004, CH-TIME-001, CH-HIST-001, CH-CROSS-001, CH-CROSS-003, CH-CROSS-005, CH-CROSS-007, CH-CROSS-012, CH-READY-001, CH-READY-010, CH-READY-015, CH-READY-016, CH-READY-017, CH-READY-018, CH-READY-019, CH-READY-020, CH-READY-021, CH-INT-001, CH-INT-002 |
| `CHART_NO_DATA` | brak danych albo pusty wynik | CH-HIST-006, CH-CROSS-010, CH-READY-007 |
| `CHART_INCOMPLETE` | częściowa seria — warunki nierozstrzygnięte | CH-OHLCV-019 |
| `CHART_DUPLICATES` | duplikaty timestampów | CH-TIME-003, CH-HIST-008, CH-READY-009 |
| `CHART_BAD_SESSION` | nieprawidłowa sesja — warunki nierozstrzygnięte | CH-TIME-011, CH-TIME-012 |
| `CHART_BAD_VOLUME` | błąd wolumenu | CH-OHLCV-008, CH-VOL-005, CH-VOL-006, CH-VOL-007, CH-VOL-008, CH-VOL-009, CH-READY-011 |
| `CHART_TYPE_CONFLICT` | konflikt typu instrumentu | CH-META-004, CH-CROSS-004, CH-READY-005 |
| `CHART_CURRENCY_CONFLICT` | konflikt waluty | CH-META-006, CH-CROSS-006, CH-READY-006 |
| `CHART_RANGE_CONFLICT` | konflikt zakresu | CH-IN-008, CH-IN-009, CH-CUR-004 |
| `CHART_HISTORY_TOO_SHORT` | zbyt krótka historia | CH-HIST-002, CH-HIST-003, CH-HIST-004, CH-HIST-005, CH-READY-002, CH-READY-012 |
| `CHART_SERIES_BROKEN` | uszkodzona seria — warunki nierozstrzygnięte | CH-OHLCV-020 |

`CHART_INCOMPLETE` i `CHART_SERIES_BROKEN` nie mają w kontrakcie zatwierdzonych dokładnych warunków ani rozstrzygniętej różnicy. Przypadki, które mogłyby je wywołać, oznaczone są jako `NIEROZSTRZYGNIĘTE` z etapem `BLOCKED_BY_OWNER_DECISION`, dopóki właściciel nie rozstrzygnie warunków. Oba statusy występują jednak w macierzy jako zatwierdzone nazwy do przyszłego mapowania.

Przypadki dotyczące transportu, HTTP, parsowania, braku metadanych albo konfliktu giełdy/symbolu nie mają zatwierdzonego statusu i oznaczono je jako `NIEROZSTRZYGNIĘTE` z etapem `BLOCKED_BY_OWNER_DECISION`.

---

## 22. PRZYPADKI ZABLOKOWANE DECYZJĄ WŁAŚCICIELA

Przypadki oznaczone etapem `BLOCKED_BY_OWNER_DECISION` wymagają osobnej decyzji właściciela przed implementacją.

| ID | Powód blokady |
|----|----------------|
| CH-META-008 | brak exchangeName — brak zatwierdzonego statusu dla braku metadanych |
| CH-META-009 | nieoczekiwany exchangeName — brak zatwierdzonego statusu dla konfliktu giełdy |
| CH-META-002 | inny symbol niż wejściowy — brak zatwierdzonego statusu dla konfliktu symbolu |
| CH-TR-002 | HTTP 200 bez chart.result — brak statusu transportu/parsowania |
| CH-TR-003 | HTTP 200 z pustym result — brak statusu transportu |
| CH-TR-004 | obiekt błędu — brak statusu |
| CH-TR-005 | HTTP inny niż oczekiwany — brak statusu HTTP |
| CH-TR-006 | nieprawidłowy JSON — brak statusu parsowania |
| CH-TR-007 | brak meta — brak statusu dla braku metadanych |
| CH-TR-008 | brak timestamp — brak jednoznacznego statusu |
| CH-TR-009 | brak indicators.quote — brak jednoznacznego statusu |
| CH-TR-010 | nadmiar wyników — brak reguły wyboru |
| CH-TR-011 | błąd przed żądaniem — brak statusu transportu |
| CH-TR-012 | błąd po odpowiedzi — brak statusu |
| CH-TR-013 | HTTP error przed walidacją — brak statusu HTTP |
| CH-CUR-002 | brak ceny bieżącej — brak statusu |
| CH-CUR-003 | cena nienumeryczna — brak statusu |
| CH-CUR-006 | brak czasu bieżącej ceny — brak statusu |
| CH-CUR-007 | cena i czas z różnych snapshotów — brak reguły |
| CH-CUR-008 | różnica ceny bez porównywalnego czasu — brak reguły |
| CH-CUR-009 | brak zatwierdzonej tolerancji ceny |
| CH-CUR-010 | cena z ostatniej świecy nierozstrzygnięta |
| CH-CUR-011 | brak ceny i krótka historia — pierwszeństwo statusów |
| CH-OHLCV-003 | niezgodne długości — INCOMPLETE/SERIES_BROKEN nierozstrzygnięte |
| CH-OHLCV-004 | brak open — brak statusu |
| CH-OHLCV-005 | brak high — brak statusu |
| CH-OHLCV-006 | brak low — brak statusu |
| CH-OHLCV-007 | brak close — brak statusu |
| CH-OHLCV-009 | null w pojedynczym polu — brak statusu |
| CH-OHLCV-010 | wszystkie pola null — brak statusu |
| CH-OHLCV-011 | high za niskie — brak statusu |
| CH-OHLCV-012 | low za wysokie — brak statusu |
| CH-OHLCV-013 | wartość nienumeryczna — brak statusu |
| CH-OHLCV-014 | wartość ujemna — brak statusu |
| CH-OHLCV-017 | częściowy rekord — polityka nierozstrzygnięta |
| CH-OHLCV-018 | poprawne meta, złe OHLC — pierwszeństwo statusów |
| CH-OHLCV-019 | częściowa seria — warunki CHART_INCOMPLETE nierozstrzygnięte |
| CH-OHLCV-020 | uszkodzona seria — warunki CHART_SERIES_BROKEN nierozstrzygnięte |
| CH-VOL-010 | brak wolumenu i uszkodzona seria — pierwszeństwo statusów |
| CH-VOL-011 | volume=0 i krótka historia — pierwszeństwo statusów |
| CH-TIME-002 | timestampy odwrotne — brak statusu |
| CH-TIME-004 | nieprawidłowy timestamp — brak statusu |
| CH-TIME-005 | brak timestampu dla świecy — brak statusu |
| CH-TIME-006 | timestamp bez OHLCV — brak statusu |
| CH-TIME-007 | OHLCV bez timestampu — brak statusu |
| CH-TIME-008 | nieregularny odstęp — kalendarz i tolerancja nierozstrzygnięte |
| CH-TIME-009 | weekend — kalendarz sesji nierozstrzygnięty |
| CH-TIME-010 | święto — kalendarz świąt nierozstrzygnięty |
| CH-TIME-011 | brak sesji — warunki CHART_BAD_SESSION nierozstrzygnięte |
| CH-TIME-012 | świeca poza sesją — warunki CHART_BAD_SESSION nierozstrzygnięte |
| CH-TIME-013 | zmiana czasu — strefy czasowe nierozstrzygnięte |
| CH-TIME-014 | konflikt strefy czasowej — brak statusu |
| CH-TIME-015 | rozróżnienie braku sesji — częściowo zależne od kalendarza |
| CH-HIST-007 | częściowe świece — polityka nierozstrzygnięta |
| CH-HIST-009 | luki wymagające kalendarza sesji |
| CH-HIST-010 | historia dzienna bez intraday — zakres nierozstrzygnięty |
| CH-HIST-011 | intraday bez dziennej — zakres nierozstrzygnięty |
| CH-HIST-012 | brak zatwierdzonego range i interval |
| CH-CROSS-002 | konflikt symbolu — brak statusu |
| CH-CROSS-008 | różna cena przy różnym czasie — reguła porównania nierozstrzygnięta |
| CH-CROSS-009 | brak ceny po jednej stronie — reguła porównania nierozstrzygnięta |
| CH-READY-003 | poprawna historia bez ceny — reguła nierozstrzygnięta |
| CH-READY-004 | cena bez historii — reguła nierozstrzygnięta |
| CH-READY-008 | częściowa seria — warunki CHART_INCOMPLETE nierozstrzygnięte |
| CH-CROSS-013 | konflikt typu i brak historii — pierwszeństwo statusów |
| CH-CROSS-014 | konflikt waluty i duplikaty — pierwszeństwo statusów |

Decyzje blokujące (jawne):

- zatwierdzenie statusu transportu, HTTP i parsowania;
- rozstrzygnięcie statusu dla braku metadanych (np. exchangeName);
- rozstrzygnięcie statusu dla konfliktu symbolu i konfliktu giełdy;
- rozstrzygnięcie dokładnych warunków `CHART_INCOMPLETE`;
- rozstrzygnięcie dokładnych warunków `CHART_BAD_SESSION`;
- rozstrzygnięcie dokładnych warunków `CHART_RANGE_CONFLICT`;
- rozstrzygnięcie różnicy między `CHART_INCOMPLETE` i `CHART_SERIES_BROKEN`;
- zatwierdzenie pełnej kolejności pierwszeństwa statusów;
- rozstrzygnięcie sposobu reprezentacji wielu jednoczesnych problemów;
- zatwierdzenie kalendarza sesji WSE, świąt i stref czasowych;
- zatwierdzenie konfiguracji `range` i `interval`;
- zatwierdzenie zasad porównania ceny screenera i chart oraz aktualności `regularMarketTime`.

---

## 23. POKRYCIE KONTRAKTU

Mapowanie wymagań kontraktu na przypadki testowe.

| Wymaganie kontraktu | Sekcja źródłowa kontraktu | Identyfikatory przypadków | Pokrycie |
|---------------------|---------------------------|---------------------------|----------|
| Yahoo jako jedyne produkcyjne źródło danych rynkowych | 5.1 | CH-SEC-003, CH-BOUND-001 | kompletne offline |
| Jeden zbiór Yahoo/WSE bez rozróżnienia GPW/NC | 5.2 | CH-IN-013, CH-CROSS-012 | kompletne offline |
| Zakaz automatycznego dopisywania końcówki | 5.2, 7 | CH-IN-002 | kompletne offline |
| Zakres dynamicznego uniwersum 0,10–10,00 PLN | 5.3 | CH-IN-006, CH-IN-007, CH-IN-008, CH-IN-009 | kompletne offline |
| Screenner jako discovery, nie źródło historii ani Observation | 5.3 | CH-IN-001, CH-BOUND-001 | kompletne offline |
| Chart jako centralne źródło danych rynkowych i OHLCV | 5.4 | CH-TR-001, CH-NET-001 | wymaga sieci |
| Historia krótsza niż 52 tygodnie dopuszczalna do Observation | 5.5, 16 | CH-HIST-002, CH-HIST-003, CH-HIST-004, CH-HIST-005, CH-READY-002, CH-READY-012 | kompletne offline |
| volume=0 jako prawidłowa wartość | 5.6, 15 | CH-VOL-002, CH-VOL-003, CH-VOL-004, CH-READY-010 | kompletne offline |
| GPT-4o na końcu zwalidowanej ścieżki | 5.7, 23 | CH-READY-013, CH-READY-020, CH-BOUND-010 | kompletne offline + integracja |
| Wejście chart wyłącznie z dokładnego symbolu screenera | 6, 7 | CH-IN-001, CH-IN-002, CH-IN-003, CH-IN-004, CH-IN-005 | kompletne offline |
| Pola porównawcze screenera | 7.1 | CH-IN-010, CH-IN-012 | kompletne offline |
| Ograniczenia wejścia | 7.2 | CH-IN-005, CH-CROSS-011 | kompletne offline |
| Trasa żądania /v8/finance/chart/{symbol} | 8.1 | CH-SEC-004 | kompletne offline |
| Brak zatwierdzonych range i interval | 8.2 | CH-HIST-012 | zablokowane decyzją właściciela |
| Metadane odpowiedzi | 9.1 | CH-META-001 do CH-META-016 | kompletne offline + decyzje |
| Seria odpowiedzi | 9.2 | CH-OHLCV-001 do CH-OHLCV-017 | kompletne offline + decyzje |
| Rodzaje błędów odpowiedzi | 9.3 | CH-TR-002 do CH-TR-012 | kompletne offline + sieci |
| Zasady normalizacji timestampów i OHLCV | 10 | CH-TIME-001 do CH-TIME-015, CH-OHLCV-011 do CH-OHLCV-016 | kompletne offline + decyzje |
| Obowiązki parsera i normalizacji | 10.1 | CH-BOUND-002, CH-OHLCV-015, CH-OHLCV-016 | integracja |
| Walidacja metadanych | 11 | CH-META-001 do CH-META-016 | kompletne offline + decyzje |
| Walidacja danych bieżących | 12 | CH-CUR-001 do CH-CUR-010 | kompletne offline + decyzje |
| Walidacja historii | 13 | CH-HIST-001 do CH-HIST-012, CH-TIME-001 do CH-TIME-015 | kompletne offline + decyzje |
| Walidacja jakości serii | 14 | CH-HIST-001 do CH-HIST-012 | kompletne offline + decyzje |
| Statusy walidacji | 17 | CH-* (mapowanie w sekcji 21) | kompletne offline + decyzje |
| Obowiązkowe wyjątki statusów | 17.1 | CH-HIST-002, CH-VOL-002 | kompletne offline |
| Zagadnienia nierozstrzygnięte statusów | 17.2 | CH-CROSS-013, CH-CROSS-014, CH-VOL-010, CH-VOL-011, CH-OHLCV-018 | zablokowane decyzją właściciela |
| Brak statusu transportu | 17.3 | CH-TR-002 do CH-TR-013 | zablokowane decyzją właściciela |
| Flagi gotowości modułów | 18 | CH-READY-001 do CH-READY-021 | kompletne offline + integracja |
| Granice odpowiedzialności | 19 | CH-BOUND-001 do CH-BOUND-013 | integracja |
| Wpływ na Observation i Baseline | 20 | CH-BOUND-003, CH-BOUND-004, CH-BOUND-005, CH-INT-002 | integracja |
| Model rewizji InstrumentReading (`SOURCE_REVISION_ACCEPTED`, `revision_number`, `supersedes_reading_id`, unikalność `(instrument_id, market_data_timestamp, revision_number)`) | 20 | CH-BOUND-003, CH-BOUND-004, CH-BOUND-005, CH-INT-002 | integracja + decyzja właściciela 2026-08-19 |
| Wpływ na Technical Engine | 21 | CH-BOUND-007, CH-INT-001 | integracja |
| Wpływ na Hunter i MasterEngine | 22 | CH-BOUND-008, CH-BOUND-009, CH-BOUND-012 | integracja |
| Wpływ na GPT-4o i Telegram | 23 | CH-BOUND-010, CH-BOUND-011, CH-READY-020, CH-READY-021 | integracja |
| Fakty potwierdzone audytami | 24 | CH-NET-001 | wymaga sieci |
| Plan walidacji offline | 26, 26.1 | CH-SEC-001 do CH-SEC-010 | kompletne offline |
| Plan kontrolowanego audytu sieciowego | 27 | CH-NET-001, CH-NET-002 | wymaga sieci |

Kontrakt kontrolnego E2E offline (Krok 7B/8, decyzja właściciela 2026-08-20): pokrycie `tests/test_step7b_controlled_validation_safety.py`, `tests/test_step7b_controlled_e2e_offline.py` oraz rozszerzonego `tests/test_point7_controlled_e2e.py` — wybór efektywnego najnowszego Readingu (najnowszy `market_data_timestamp`, najwyższy `revision_number`, wolumen DESC, symbol ASC), overlay `close=previous×1.04` + minimalne `high=max(real_high, controlled_close)` przed produkcyjną walidacją, budżety przekraczane → `BLOCKED_BY_BUDGET`, dokładnie jedno `RuntimeService.run_cycle()` — etap wykonania OFFLINE_READY (bez sieci), z zachowaniem domyślnego trybu produkcyjnego bez zmian.

Żadne wymaganie kontraktu nie znika bez adnotacji. Wymagania zależne od otwartych decyzji są oznaczone jako zablokowane decyzją właściciela.

Decyzja właściciela z 2026-08-19, wynikająca z rzeczywistego cyklu Yahoo, rozszerza KANON §13.3 pkt 9 i §13.5 pkt 12 o model rewizji InstrumentReading (wyniki domenowe `save_reading`: `ACCEPTED`, `SOURCE_REVISION_ACCEPTED`, `DUPLICATE_NO_OP`, `CONFLICT`, `STALE_TIMESTAMP`; unikalność `(instrument_id, market_data_timestamp, revision_number)`) i zastępuje wcześniejszy zakaz rewizji.

### 23a. Przyszła macierz testów trajektorii świecy 1h (Krok 7C, decyzja właściciela 2026-08-21)

Kategoria: **PROJEKT MACIERZY — DO PÓŹNIEJSZEJ AKCEPTACJI**.

Wymagania test-first dla kontraktu świecy 1h monitorowanej co 15 minut:

1. tożsamość Readingu rozdziela interwały 5m, 30m i 1h przy tym samym symbolu i timestampie;
2. stany OPEN po 15, 30 i 45 minutach są zapisywane jako uporządkowane rewizje tej samej świecy 1h;
3. przejście OPEN → CLOSED jest zapisywane jako `CANDLE_PROGRESS_ACCEPTED`;
4. następna świeca 1h rozpoczyna `revision_number=1`, a jej `prev_reading_id` wskazuje efektywną końcową wersję poprzedniej świecy;
5. `SOURCE_REVISION_ACCEPTED` występuje dopiero po CLOSED (późniejsza korekta źródłowa świecy zamkniętej);
6. porównanie z poprzednim close (kotwica) i poprzednim stanem bieżącej świecy;
7. zachowanie kolejności ruchów wewnątrz godziny;
8. przekazanie trajektorii do kontekstu AI (wraz z danymi Huntera, Technical Engine, MasterEngine, Tavily i pozostałych silników);
9. brak Telegrama przed decyzją AI i przejściem naturalnych bramek;
10. pełna etykieta kontrolna bez duplikacji:
    - `ALCHEMIK — CONTROLLED_VALIDATION_ONLY`;
    - `TO NIE JEST SYGNAŁ INWESTYCYJNY.`;
11. brak overlayu, gdy nie istnieje otwarta świeca 1h (przebieg zatrzymuje się naturalnie);
12. pełnosystemowy test na prawdziwym RuntimeService i tymczasowej SQLite (jedno `RuntimeService.run_cycle()`).

#### 23a.1 Uzupełnienie decyzji właściciela 2026-08-21 — separacja timeframe i status RETIRED_TIMEFRAME (Wariant A+C zatwierdzony)

- Observation są rozdzielone per `(instrument_id, timeframe)`;
- baseline jest rozdzielony per `(instrument_id, timeframe)`;
- historia 5m pozostaje zachowana jako archiwum;
- 327 historycznych Readingów: późniejszy backfill `timeframe="5m"`, `candle_state="LEGACY_UNKNOWN"`;
- 171 historycznych ACTIVE Observation 5m: późniejsza kontrolowana migracja do `RETIRED_TIMEFRAME`;
- 1 Observation `INTEGRITY_BREACHED` pozostaje bez zmian;
- brak kasowania i nadpisywania historii;
- pierwsza Observation 1h rozpoczyna niezależny łańcuch;
- pierwsza kotwica 1h to poprzednia zamknięta świeca `CLOSED`;
- bieżąca świeca jest osobnym Readingiem `OPEN`;
- żaden `prev_reading_id`, baseline ani restore 1h nie może wskazywać danych 5m;
- `CANDLE_PROGRESS_ACCEPTED` oznacza postęp otwartej świecy i przejście OPEN → CLOSED;
- `SOURCE_REVISION_ACCEPTED` pozostaje korektą źródłową świecy już zamkniętej;
- szczegóły tabeli baseline oraz implementacja migracji nie są jeszcze opisane w tym dokumencie.

---

## 24. WARUNKI WEJŚCIA DO KROKU 3/6

Krok 3/6 może rozpocząć się dopiero po:

1. zatwierdzeniu macierzy przez właściciela;
2. rozstrzygnięciu tylko tych decyzji, które są niezbędne dla walidacji offline;
3. wskazaniu przypadków wykonywanych w pierwszej wersji offline;
4. zamrożeniu SHA-256 macierzy;
5. osobnym poleceniu właściciela.

Utworzenie macierzy nie zatwierdza Kroku 3/6.

---

## 25. OGRANICZENIA

- Macierz nie zatwierdza wykonania żadnego przypadku testowego.
- Macierz nie rozstrzyga otwartych decyzji właściciela.
- Macierz nie zatwierdza konfiguracji `range` ani `interval`.
- Macierz nie zatwierdza kalendarza sesji WSE, świąt ani stref czasowych.
- Macierz nie wprowadza progów cenowych, wolumenu, tolerancji, liczby świec, limitów czasu, opóźnień, braków, duplikatów, limitów żądań, retry ani fallbacków.
- Dopuszczalne wartości ograniczają się do zatwierdzonych: 0,10–10,00 PLN, kontekst 52 tygodni oraz `volume=0` jako prawidłowa wartość.
- Macierz nie zmienia zatwierdzonego kontraktu danych Yahoo chart.
- Macierz nie udaje, że testy zostały wykonane.
- Macierz nie zawiera sekretów, cookie ani crumb.

---

## 26. KONIEC DOKUMENTU

Data utworzenia: 15.08.2026

Status: PROJEKT MACIERZY TESTÓW — DO ODRĘBNEJ AKCEPTACJI WŁAŚCICIELA.

Dokument czeka na ocenę i decyzję właściciela projektu.

Krok 3/6 pozostaje zablokowany do osobnego polecenia właściciela.