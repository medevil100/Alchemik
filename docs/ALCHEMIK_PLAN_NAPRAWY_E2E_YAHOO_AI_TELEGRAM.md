# ALCHEMIK — PLAN NAPRAWY E2E YAHOO → AI → TELEGRAM (PUNKTY 1–7)

## METRYKA DOKUMENTU

| Atrybut | Wartość |
|---------|---------|
| Tytuł | ALCHEMIK — Plan naprawy E2E Yahoo → AI → Telegram (punkty 1–7) |
| Rodzaj zadania | wyłącznie dokumentacyjne — aktywacja planu naprawy i czasowe odmrożenie modułów |
| Data utworzenia | 15.08.2026 |
| Repozytorium | C:\alchemik |
| Gałąź | master |
| HEAD | 8e4edbd5fe26a4ec8b2b4dbf4540614cf906da24 |
| Plik docelowy | docs/ALCHEMIK_PLAN_NAPRAWY_E2E_YAHOO_AI_TELEGRAM.md |

Dokument formalnie odblokowuje implementację i kończy etap samych audytów.

---

## STATUS

OWNER_APPROVED — ACTIVE

---

## STATUS I DECYZJA WŁAŚCICIELA

Zapisuje się jednoznacznie:

1. Adam jest właścicielem i konstruktorem projektu ALCHEMIK.
2. Właściciel zatwierdza rozpoczęcie implementacji pełnego przepływu E2E.
3. Etap samych audytów zostaje zakończony.
4. Wszystkie moduły ALCHEMIKA zostają czasowo odmrożone wyłącznie w zakresie koniecznym do wykonania planu naprawy 1–7.
5. Odmrożenie nie jest zgodą na dowolny redesign.
6. Każda zmiana musi mieć bezpośredni związek z osiągnięciem pełnego przepływu Yahoo → AI → Telegram.
7. Po zakończeniu, testach i akceptacji E2E moduły zostaną ponownie zamrożone.
8. Najnowsza decyzja właściciela superseduje wcześniejsze zapisy mówiące, że dynamiczne uniwersum, rzeczywiste AI albo Telegram pozostają nierozstrzygnięte.

---

## ZATWIERDZONE DECYZJE ARCHITEKTONICZNE

Zapisuje się jako obowiązujące:

1. Produkcyjnym źródłem danych rynkowych pozostaje wyłącznie Yahoo Finance.
2. Yahoo jest traktowane jako jeden zbiór WSE bez pola rozróżniającego GPW i NewConnect.
3. Nie tworzy się w Yahoo osobnego segmentu NC.
4. Custom screener Yahoo jest podstawowym mechanizmem discovery.
5. Zamrożona lista dokładnych symboli Yahoo jest dopuszczonym wariantem awaryjnym, jeżeli screener okaże się niestabilny.
6. Nie wolno automatycznie dopisywać .WA, .NC, .PL ani innej końcówki.
7. Chart jest źródłem bieżących danych rynkowych i historii OHLCV.
8. volume=0 jest poprawną wartością danych.
9. Historia krótsza niż 52 tygodnie nie blokuje Observation; gotowość Technical Engine pozostaje warunkowa.
10. Dane mają przechodzić przez istniejące moduły produkcyjne.
11. AI ma być rzeczywistą integracją, nie placeholderem.
12. Tavily ma pozostać w zatwierdzonym miejscu istniejącej ścieżki.
13. Telegram ma otrzymywać rzeczywisty końcowy alert.
14. Każdy cykl ma mieć obserwowalny ślad danych.
15. AI pozostaje na końcu ścieżki i nie uzupełnia brakujących danych rynkowych.

---

## ZAKRES NAPRAWY 1–7

Plan naprawy pełnego przepływu:

Yahoo Finance → Observation/Baseline → wszystkie silniki → rzeczywiste AI → rzeczywisty Telegram.

Zapisuje się dokładnie następujący plan:

### 1. Produkcyjne Yahoo discovery i chart

Podłączyć produkcyjny custom screener Yahoo oraz chart daily/intraday. Usunąć zależność produkcyjnego startu od błędnego wywołania StaticInstrumentSource() bez listy. Zachować statyczną, zatwierdzoną listę dokładnych symboli Yahoo jako wariant awaryjny, a nie główne źródło.

### 2. Podłączenie danych do RuntimeService i repozytoriów

Znormalizowane dane Yahoo mają trafiać do istniejącego RuntimeService, HistoryRepository i SQLiteHistoryRepository. Observation oraz trwały baseline mają powstawać albo być odtwarzane zgodnie z zatwierdzonym kontraktem.

### 3. Pełny przepływ przez silniki

Dane mają przejść przez rzeczywiste istniejące moduły, bez wewnętrznych mocków: Technical Engine, detektory, HunterEngine, AnalystEngine, RankingEngine, RiskEngine, MasterEngine i DecisionEngine. Każde odrzucenie albo zatrzymanie musi mieć jawny powód.

### 4. Rzeczywiste AI i Tavily

Zastąpić placeholder AISignal(confidence=0.0) rzeczywistą integracją istniejącego AIProvider/AIPipeline albo minimalną zgodną implementacją dostawcy AI. Podłączyć istniejący tavily_adapter w jego zatwierdzonym miejscu. Nie zmieniać AI w generator BUY/SELL.

### 5. Rzeczywisty Telegram

Podłączyć TelegramChannel do composition root, RuntimeService i AlertDispatcher. Naprawić brakujące zależności, w tym brak importu datetime. Końcowy zatwierdzony wynik ma prowadzić do rzeczywistej wiadomości Telegram.

### 6. Obserwowalny ślad cyklu

Każdy cykl ma pokazywać: źródło danych, liczbę instrumentów, status chart, Observation, Baseline, wejście i wyjście każdego silnika, wynik AI, wynik Telegrama, powody SKIP i ERROR oraz czas każdego etapu. Ślad ma być dostępny w terminalu i trwałym raporcie cyklu bez sekretów.

### 7. Testy i rzeczywisty przebieg E2E

Dodać testy kontraktowe i integracyjne, uruchomić pełną regresję, zweryfikować stan repozytorium, a następnie wykonać jeden zatwierdzony rzeczywisty przebieg:

Yahoo → Observation/Baseline → wszystkie moduły → AI → Telegram.

Zadanie nie może zostać uznane za zakończone wyłącznie na podstawie testów offline.

---

## KOLEJNOŚĆ IMPLEMENTACJI

Plan będzie wykonywany kolejno od punktu 1 do punktu 7.

Nie wolno omijać wcześniejszej rzeczywistej granicy i naprawiać późniejszego modułu w oderwaniu od przepływu.

Pierwszym zadaniem implementacyjnym po utworzeniu dokumentu będzie punkt 1: produkcyjne Yahoo discovery i chart.

---

## KRYTERIUM KOŃCOWE

Plan zostaje zamknięty wyłącznie wtedy, gdy:

1. produkcyjny RuntimeService uruchamia się bez błędu;
2. dane są pobierane z Yahoo;
3. powstają Observation i Baseline;
4. dane przechodzą przez wszystkie wymagane silniki;
5. wykonywane jest rzeczywiste AI;
6. wysyłana jest rzeczywista wiadomość Telegram;
7. pełny ślad cyklu jest dostępny;
8. testy i regresja przechodzą;
9. repozytorium jest w pełni rozliczone;
10. właściciel zatwierdzi wynik.

Jest to jednocześnie kryterium ponownego zamrożenia: po zakończeniu, testach i akceptacji E2E moduły zostaną ponownie zamrożone, a czasowe odmrożenie wygasa.

---

## OGRANICZENIA ODMROŻENIA

Odmrożenie modułów:

1. obowiązuje tylko dla planu 1–7;
2. nie pozwala usuwać istniejących modułów;
3. nie pozwala zmieniać ich odpowiedzialności bez konieczności wynikającej z realnego kontraktu;
4. nie pozwala zmieniać zatwierdzonych progów;
5. nie pozwala dodawać drugiego źródła danych rynkowych;
6. nie pozwala ukrywać placeholderów ani błędów;
7. wymaga testów przed zamknięciem każdego punktu;
8. wygasa po akceptacji pełnego E2E przez właściciela.

---

## KONIEC DOKUMENTU

Data utworzenia: 15.08.2026

Status: OWNER_APPROVED — ACTIVE

Po tym zadaniu aktywnym następnym krokiem jest implementacja punktu 1: produkcyjne Yahoo discovery i chart.