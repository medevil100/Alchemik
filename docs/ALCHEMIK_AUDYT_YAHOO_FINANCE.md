# ALCHEMIK — KANONICZNY DOKUMENT AUDYTÓW YAHOO FINANCE

## METRYKA DOKUMENTU

| Atrybut | Wartość |
|---------|---------|
| Tytuł | ALCHEMIK — Kanoniczny dokument audytów Yahoo Finance |
| Status | KANONICZNY DOKUMENT DOWODOWY — NIE ZATWIERDZA IMPLEMENTACJI |
| Data utworzenia | 13.08.2026 |
| Python użyty w historycznych audytach | 3.13.13 |
| yfinance | 1.5.2 |
| Repozytorium | C:\alchemik |
| Gałąź historycznych audytów | master |
| Historyczny HEAD | 8e4edbd5fe26a4ec8b2b4dbf4540614cf906da24 |

Historyczne wyniki wykonawcze pochodzą z raportów przekazanych przez właściciela w ramach polecenia. Przed utworzeniem niniejszego dokumentu raporty Yahoo nie istniały w repozytorium i wcześniej znajdowały się poza nim.

---

## STATUS I ROLE

> KANONICZNY DOKUMENT DOWODOWY — NIE ZATWIERDZA IMPLEMENTACJI

Zapisane role i zasady decyzyjności:

- Właściciel projektu jest jedyną osobą zatwierdzającą wyniki i kolejne kroki.
- Asystent i Cline analizują oraz przygotowują raporty, ale nie zatwierdzają architektury ani implementacji.
- Nie wolno zgadywać brakujących faktów.

Utworzenie niniejszego dokumentu nie zatwierdza:

- przyszłych wywołań Yahoo;
- dynamicznego uniwersum;
- produkcyjnego InstrumentSource;
- kompletności GPW + NewConnect;
- gotowości 24/7.

Dokument utworzono na podstawie:

- lokalnego kodu projektu i yfinance 1.5.2;
- historycznych raportów wykonawczych przekazanych przez właściciela;
- decyzji właściciela.

---

## KATEGORIE INFORMACJI

Każdy zapisany fakt jest oznaczany jedną z następujących kategorii:

- **DECYZJA WŁAŚCICIELA** — została jawnie przekazana albo zatwierdzona przez właściciela.
- **DOWÓD STATYCZNY** — wynika z lokalnego kodu yfinance 1.5.2.
- **WYNIK RAPORTU WYKONAWCZEGO PRZEKAZANEGO PRZEZ WŁAŚCICIELA** — wynika z historycznego raportu rzeczywistego wywołania Yahoo, przekazanego przez właściciela.
- **OGRANICZENIE** — wskazuje, czego wynik nie dowodzi.
- **OTWARTE** — wymaga dalszego audytu albo decyzji właściciela.

Nie przedstawia się informacji właściciela jako dowodu odczytanego z repozytorium. Nie przedstawia się wniosku statycznego jako wyniku wykonawczego. Nie przedstawia się braku pola w lokalnym kodzie jako dowodu, że Yahoo nigdy takiego pola nie zwraca.

---

## ZAKRES PROJEKTOWY

Poniższe decyzje są oznaczone jako **DECYZJA WŁAŚCICIELA**.

Początkowy zakres obejmuje:

- akcje GPW;
- akcje NewConnect.

Zakres ceny:

- 0,10 PLN <= cena <= 10,00 PLN
- Obie granice są włączne.

Pozostałe obowiązujące decyzje:

- Uniwersum ma być automatyczne (odkrywane automatycznie).
- Jedynym źródłem danych rynkowych pozostaje Yahoo Finance.

Zakazane bez nowej decyzji właściciela:

- drugi dostawca;
- scraping;
- ręczna watchlista;
- twardo wpisana produkcyjna lista tickerów;
- most_actives jako źródło polskiego uniwersum.

Rynek USA jest odłożony (poza obecnym zakresem).

GPT-4o, Tavily i Telegram pozostają poza obecnym audytem Yahoo.

Dokument nie może zawierać sekretów ani wartości sesyjnych (w tym kluczy, tokenów, wartości cookie ani crumb).

---

## ŚRODOWISKO HISTORYCZNYCH AUDYTÓW

| Atrybut | Wartość |
|---------|---------|
| Repozytorium | C:\alchemik |
| Python | 3.13.13 |
| yfinance | 1.5.2 |
| Gałąź historycznych audytów | master |
| Historyczny HEAD | 8e4edbd5fe26a4ec8b2b4dbf4540614cf906da24 |

Historyczne audyty nie zmieniły tego HEAD. Przed utworzeniem niniejszego dokumentu raporty Yahoo nie istniały w repozytorium.

---

## CHRONOLOGIA AUDYTÓW

| Krok / pytanie | Charakter | Cel | Wykonane operacje | Najważniejszy wynik | Klasyfikacja | Ograniczenia | Status decyzji właściciela | Źródło dowodu |
|---|---|---|---|---|---|---|---|---|
| Pytania planistyczne (6 pytań) | planistyczny | Ustalenie zakresu i metodyki audytu Yahoo | Analiza planistyczna pytań o uniwersum, cenę, źródło i powtarzalność | Ustalenie pytań badawczych | — | Wynik planistyczny, nie wykonawczy | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Raport w rozmowie przekazany przez właściciela |
| Pełna paginacja region='pl' | wykonawczy | Sprawdzenie kompletnego pobrania stron region='pl' | Dwie strony bazowego screenera (offset 0 i 250) | total=429; 429 unikalnych symboli .WA; strony rozłączne, suma zgodna z total | potwierdzone (snapshot) | Nie dowodzi oficjalnej kompletności GPW + NewConnect ani rozróżnienia segmentu | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Wynik raportu wykonawczego przekazanego przez właściciela |
| Zakres cenowy 0,10–10,00 PLN | wykonawczy | Sprawdzenie filtra cenowego GTE + LTE | Jedna strona cenowa screenera | total=172; min 0.116; max 9.54; 0 naruszeń; 0 na granicy | potwierdzone (snapshot) | Nie dowodzi oficjalnej kompletności GPW + NewConnect | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Wynik raportu wykonawczego przekazanego przez właściciela |
| Dwa powtarzalne przejścia A i B | wykonawczy | Sprawdzenie powtarzalności dwóch bezpośrednich przejść | 6 kontrolowanych wywołań Yahoo (2 bazy A + 1 cena A + 2 bazy B + 1 cena B), bez sztucznego opóźnienia | Wyniki A i B identyczne (total, zbiory, kolejność, strony, rozkłady, ceny min/max) | potwierdzone (wyłącznie powtarzalność dwóch przejść) | Nie dowodzi stabilności godzinowej, dziennej ani 24/7 | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Wynik raportu wykonawczego przekazanego przez właściciela |
| Krok 3 — pierwszy audyt endpointów | wykonawczy | Kontrolowany bootstrap cookie/crumb | GET https://fc.yahoo.com/ (HTTP 404) | Audyt zatrzymany po 404; 1 żądanie cookie, 0 crumb, 0 merytorycznych | D — nierozstrzygnięte | Nie uzyskano danych instrumentów; Search nie został rozpoczęty | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Wynik raportu wykonawczego przekazanego przez właściciela |
| Krok 3B — poprawiony cookie bootstrap | wykonawczy | Poprawiony bootstrap z akceptacją użytecznego cookie A3 | 1 cookie + 1 crumb + 2 merytoryczne (Search po 2 ISIN) | 4MS.WA rozwiązane; 7LEVELS bez rozwiązania (STOP); D — nierozstrzygnięte | D — nierozstrzygnięte | Pusty Search nie dowodzi braku 7LEVELS ani NewConnect w Yahoo | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Wynik raportu wykonawczego przekazanego przez właściciela |
| Krok 3C — skorygowana mapa statyczna | statyczny | Statyczna mapa mechanizmów yfinance 1.5.2 | Analiza lokalnego kodu yfinance | 25 tras Yahoo; 24 mechanizmy; 13 top-level wejść; BusinessInsider wykluczony | statyczny | Statyczny skan nie dowodzi kompletności endpointów Yahoo poza biblioteką | Brak jednoznacznego zatwierdzenia wyniku w dostępnej treści. | Lokalny kod yfinance 1.5.2 |

---

## WYNIK SCREENERA BAZOWEGO

Kategoria: **WYNIK RAPORTU WYKONAWCZEGO PRZEKAZANEGO PRZEZ WŁAŚCICIELA**.

Zapytanie:

- region='pl'

Strona pierwsza:

- offset=0;
- size=250;
- total=429;
- count=250;
- len(quotes)=250.

Strona druga:

- offset=250;
- size=250;
- total=429;
- count=179;
- len(quotes)=179.

Łącznie:

- 429 prawidłowych symboli;
- 429 symboli unikalnych;
- 0 rekordów bez symbolu;
- 0 duplikatów;
- 0 wspólnych symboli pomiędzy stronami;
- strony rozłączne;
- suma unikalnych symboli zgodna z total.

Rozkład wszystkich 429 rekordów:

- quoteType=EQUITY;
- exchange=WSE;
- market=pl_market;
- currency=PLN.

Wszystkie symbole były niepuste, unikalne i zakończone .WA.

Ograniczenia:

- Wynik nie dowodzi oficjalnej kompletności GPW + NewConnect.
- Wynik nie dowodzi rozróżnienia Głównego Rynku GPW i NewConnect.
- Wynik jest historycznym snapshotem, a nie gwarancją stabilności 24/7.

---

## WYNIK SCREENERA CENOWEGO

Kategoria: **WYNIK RAPORTU WYKONAWCZEGO PRZEKAZANEGO PRZEZ WŁAŚCICIELA**.

Zapytanie:

- region='pl';
- intradayprice >= 0.10;
- intradayprice <= 10.00;
- operatory GTE + LTE.

Granice były włączne.

Wynik:

- total=172;
- start=0;
- count=172;
- len(quotes)=172.

172 prawidłowe i unikalne symbole.

- 0 rekordów bez symbolu;
- 0 duplikatów.

Wszystkie ceny były liczbowe.

- Minimalna cena: 0.116 PLN.
- Maksymalna cena: 9.54 PLN.
- 0 naruszeń zakresu.
- 0 instrumentów dokładnie na granicy 0.10.
- 0 instrumentów dokładnie na granicy 10.00.

Wszystkie rekordy:

- EQUITY;
- WSE;
- pl_market;
- PLN.

Ograniczenie:

- Wynik nie dowodzi oficjalnej kompletności GPW + NewConnect.

---

## POWTARZALNOŚĆ DWÓCH PRZEJŚĆ

Kategoria: **WYNIK RAPORTU WYKONAWCZEGO PRZEKAZANEGO PRZEZ WŁAŚCICIELA**.

- Wykonano dwa bezpośrednio następujące po sobie pełne przejścia A i B.
- Wykonano dokładnie 6 kontrolowanych wywołań Yahoo:
  - dwie strony bazy w przejściu A;
  - jedna strona cenowa w przejściu A;
  - dwie strony bazy w przejściu B;
  - jedna strona cenowa w przejściu B.
- Nie wprowadzono sztucznego opóźnienia.

Wyniki A i B były identyczne w zakresie:

- total;
- zbiorów symboli;
- kolejności symboli;
- przynależności do stron;
- liczby rekordów;
- duplikatów;
- rozkładów pól;
- minimalnej i maksymalnej ceny.

Ograniczenia:

- Wynik dowodzi jedynie powtarzalności dwóch bezpośrednich przejść.
- Wynik nie dowodzi stabilności godzinowej, dziennej ani 24/7.

---

## KROK 3 — PIERWSZY KONTROLOWANY AUDYT ENDPOINTÓW

Kategoria: **WYNIK RAPORTU WYKONAWCZEGO PRZEKAZANEGO PRZEZ WŁAŚCICIELA**.

- Użyto świeżej sesji i świeżego cache.
- Nie użyto istniejącego cookies.db.
- SHA-256 skryptu: 4c786c67205c9e473d6e4f73198cae35f265ca3f4f4f0615ed048d6aa54923ad

Pierwsze żądanie:

- GET https://fc.yahoo.com/
- Status: HTTP 404.
- Brak przekierowania.

Audyt zatrzymano zgodnie z ówczesną, zbyt rygorystyczną regułą STOP dla każdego HTTP 4xx.

Wysłano:

- 1 żądanie cookie;
- 0 żądań crumb;
- 0 żądań merytorycznych.

Klasyfikacja: D — nierozstrzygnięte.

Nie uzyskano danych instrumentów.

Ten przebieg pozostaje oddzielnym historycznym wynikiem i nie jest zastępowany przez Krok 3B. Nie nazywa się go nieudanym wywołaniem Search — Search nie został rozpoczęty.

---

## KROK 3B — POPRAWIONY COOKIE BOOTSTRAP

Kategoria: **WYNIK RAPORTU WYKONAWCZEGO PRZEKAZANEGO PRZEZ WŁAŚCICIELA**.

- SHA-256 skryptu: 5910c5353dbc4f2dd947e1ce3c2f7b3adfd3fd889ae77845a1d4016bb389b7dc
- Świeża sesja była pusta przed siecią.
- Użyto świeżego cache poza istniejącym py-yfinance.

GET https://fc.yahoo.com/:

- HTTP 404;
- brak przekierowania;
- odpowiedź ustawiła jedno cookie A3;
- domena .yahoo.com;
- ścieżka /;
- termin ważności obecny.

Nie zapisuje się wartości cookie.

Crumb:

- GET query1.finance.yahoo.com/v1/test/getcrumb;
- HTTP 200.

Search PL4MASS00011:

- HTTP 200;
- jednoznacznie rozwiązano 4MS.WA;
- shortname=4MASS;
- quoteType=EQUITY;
- exchange=WSE;
- typeDisp=Equity;
- exchDisp=WSE.

Search PL7LVLS00017:

- HTTP 200;
- equity_total=0;
- total=0;
- nie rozwiązano symbolu;
- warunek STOP tej gałęzi.

Faktyczne liczniki:

- attempts=4;
- sent=4;
- blocked=0;
- cookie_sent=1;
- crumb_sent=1;
- substantive_sent=2;
- redirects=0.

Rozróżnienie operacji:

- wykonane operacje merytoryczne: 2;
- operacje zakończone jednoznacznym rozwiązaniem: 1;
- operacje zakończone STOP: 1;
- operacje 3–7: nierozpoczęte.

Klasyfikacja: D — nierozstrzygnięte.

Pusty Search po ISIN nie dowodzi:

- braku 7LEVELS w Yahoo;
- braku NewConnect w Yahoo;
- braku instrumentu w screenerze;
- braku instrumentu w innych mechanizmach.

7LV.WA nie został potwierdzony. 7LV pozostaje oficjalnym skrótem referencyjnym przekazanym przez właściciela, a nie potwierdzonym symbolem Yahoo.

Informacja właściciela o braku 7LEVELS na niektórych platformach, np. XTB, jest wyłącznie obserwacją różnicy pokrycia platform. Nie wnioskuje się o przyczynie braku w XTB.

---

## KROK 3C — SKORYGOWANA MAPA STATYCZNA MECHANIZMÓW

Kategoria: **DOWÓD STATYCZNY**.

Lokalny zakres: yfinance 1.5.2.

Zidentyfikowano:

- 25 unikalnych tras Yahoo według klucza metoda + host + znormalizowana ścieżka;
- 7 tras technicznych;
- 18 tras danych;
- 1 zewnętrzną trasę niebędącą Yahoo;
- 24 logiczne mechanizmy;
- 13 publicznych top-level wejść sieciowych.

Nie zapisuje się ≈30 publicznych metod Ticker jako dokładnego licznika.

Domain:

- abstrakcyjna klasa bazowa;
- nie jest publicznym top-level punktem wejścia.

Sector i Industry:

- publiczne mechanizmy;
- technicznie spełniają rolę DISCOVERY;
- wymagają klucza sektora albo branży;
- zwracają ograniczone zbiory „top";
- nie zapewniają kompletnego uniwersum GPW + NewConnect.

Custom screener:

- jest jedynym lokalnie znalezionym kandydatem do pełnego polskiego DISCOVERY;
- nie wymaga wcześniejszej znajomości symbolu ani klucza domenowego;
- operand region='pl' mapuje do WSE;
- parametr lokalizacyjny URL może nadal mieć region=US i nie jest tym samym co operand zapytania.

Predefined screeners:

- są ograniczone;
- nie są zatwierdzonym źródłem polskiego uniwersum.

Search i Lookup:

- są mechanizmami RESOLUTION;
- są od siebie niezależne;
- niepowodzenie jednego nie powinno blokować drugiego ani screenera.

Lookup:

- technicznie wysyła start;
- lokalna implementacja ustawia start=0;
- publiczne API nie pozwala zmienić start;
- publiczne API nie zapewnia paginacji;
- zmiana count jest zmianą rozmiaru pierwszej strony, nie paginacją.

quoteSummary, /v7/finance/quote i chart:

- wymagają jednoznacznie rozwiązanego symbolu;
- nie są mechanizmami pełnego discovery.

Nie znaleziono w lokalnym kodzie jawnego pola ani wartości rozróżniającej:

- Główny Rynek GPW;
- NewConnect.

Brak literalnego pola w lokalnym kodzie nie dowodzi, że pole nie może wystąpić w surowej odpowiedzi Yahoo.

Statyczny skan lokalnego yfinance nie dowodzi kompletności endpointów Yahoo istniejących poza biblioteką.

Ticker.get_isin korzysta z:

- markets.businessinsider.com

Ten mechanizm jest niezgodny z zasadą Yahoo-only i wykluczony z przyszłego produkcyjnego źródła uniwersum.

Sformułowanie „według przesłanek regulatora" poprawia się na: „według informacji właściciela".

---

## OFICJALNA REFERENCJA KONTROLNA — STATUS 7LEVELS NA 2026-08-13

Kategoria: **OFICJALNA ZAMROŻONA REFERENCJA KONTROLNA — WYNIK ODCZYTOWEGO SPRAWDZENIA PRZYJĘTY PRZEZ WŁAŚCICIELA**

- Data odczytowego sprawdzenia: 2026-08-13.
- Instrument: 7LEVELS SPÓŁKA AKCYJNA.
- Oficjalny ticker giełdowy: 7LV.
- ISIN: PL7LVLS00017.
- Oficjalna karta spółki NewConnect przedstawiała instrument jako 7LEVELS:
  https://newconnect.pl/spolka?isin=PL7LVLS00017
- Oficjalna tabela notowań NC Base zawierała 7LEVELS wraz z danymi sesyjnymi:
  https://newconnect.pl/notowania?segment=NC_Base
- Załącznik do Uchwały GPW nr 503/2026, odnoszący się do stanu od 2026-04-01, zawierał:
  7LEVELS;
  7LV;
  PL7LVLS00017.
- Adres dokumentu:
  https://newconnect.pl/pub/NEWCONNECT/uchwaly/2026/503_2026_zal.pdf

Wynik stanowi dodatni dowód, że na dzień sprawdzenia 7LEVELS był instrumentem NewConnect i nie powinien być traktowany jako delisted.

7LEVELS może pozostać referencyjnym instrumentem NewConnect w audycie.

Brak 7LEVELS w XTB jest wyłącznie informacją o różnicy pokrycia platform. Dokładnej przyczyny braku w XTB nie ustalono.

Ten wynik nie jest przedstawiany jako dane produkcyjne ALCHEMIKA, jako wynik Yahoo, jako wynik ponownie sprawdzony przez Cline, jako potwierdzenie symbolu Yahoo ani jako zgoda na drugi produkcyjny dostawca danych.

### OBOWIĄZKOWE OGRANICZENIA

- Oficjalna referencja nie potwierdza obecności 7LEVELS w Yahoo.
- Oficjalna referencja nie potwierdza symbolu Yahoo 7LV.WA.
- 7LV jest potwierdzonym oficjalnym tickerem NewConnect, ale nie jest automatycznie potwierdzonym symbolem Yahoo.
- Pusty Search Yahoo po ISIN nadal dowodzi wyłącznie braku wyniku tego mechanizmu w konkretnym przebiegu.
- Sprawdzenie nie dowodzi kompletności uniwersum Yahoo.
- Sprawdzenie nie dowodzi rozróżnienia GPW i NewConnect przez Yahoo.
- Sprawdzenie nie zmienia zasady Yahoo-only.
- Oficjalne strony GPW/NewConnect są wyłącznie zamrożoną referencją kontrolną.
- Produkcyjnym źródłem danych ALCHEMIKA pozostaje wyłącznie Yahoo Finance.
- Wynik jest datowanym snapshotem i nie stanowi gwarancji przyszłego statusu instrumentu.

---

## KOREKTY METODYCZNE

| Pierwotne sformułowanie / błąd | Poprawne sformułowanie | Wpływ na wynik | Status korekty |
|---|---|---|---|
| HTTP 404 z fc.yahoo.com traktowany automatycznie jak błąd endpointu danych | HTTP 404 z fc.yahoo.com może być prawidłowym cookie bootstrap, jeżeli odpowiedź ustawiła użyteczne cookie A3 | Zmiana interpretacji bootstrapu; Krok 3 zastąpiony poprawionym Krokiem 3B (historycznie oddzielne wyniki) | Wprowadzona |
| Search 7LEVELS jako nierozpoczęty | Search 7LEVELS został wykonany i zakończył się STOP | Poprawne rozliczenie operacji merytorycznych | Wprowadzona |
| W Kroku 3B niejasna liczba operacji merytorycznych | W Kroku 3B wykonano 2 operacje merytoryczne, z czego 1 zakończyła się rozwiązaniem | Poprawne rozliczenie (1 rozwiązanie, 1 STOP) | Wprowadzona |
| Sztuczny test „dziesiątej próby" | Nie stosować sztucznego testu „dziesiątej próby" | Usunięcie nierzeczywistego progu ponowień | Wprowadzona |
| Zakładanie minimalnej/maksymalnej liczby przyszłych żądań | Nie zakładać minimalnej ani maksymalnej liczby przyszłych żądań | Brak sztucznych limitów w przyszłym audycie | Wprowadzona |
| Równoległe wykonywanie logicznie niezależnych gałęzi | Logicznie niezależne gałęzie wykonywać fizycznie sekwencyjnie | Kontrolowane, deterministyczne wykonanie | Wprowadzona |
| Lookup jako posiadający paginację | Lookup nie ma publicznej paginacji (mimo technicznego start=0) | Poprawna klasyfikacja Lookup jako RESOLUTION bez paginacji | Wprowadzona |
| Custom screener jako jedyny techniczny DISCOVERY | Custom screener nie jest jedynym technicznym DISCOVERY, lecz jest jedynym lokalnie znalezionym kandydatem do pełnego polskiego uniwersum | Poprawne rozróżnienie „jedyny kandydat" od „jedyny mechanizm" | Wprowadzona |
| ≈30 jako dokładny licznik | Nie używać ≈30 jako dokładnego licznika | Usunięcie nieprecyzyjnej wartości | Wprowadzona |
| Cytowanie zdania o wykonaniu siedmiu operacji przy niepełnym przebiegu | Przy niepełnym przebiegu nie cytować zdania o wykonaniu siedmiu operacji | Zgodność opisu z rzeczywistym przebiegiem | Wprowadzona |

---

## AKTUALNY STAN DOWODOWY

| Zagadnienie | Status | Dowód | Ograniczenie | Następny wymagany krok |
|---|---|---|---|---|
| Techniczna możliwość paginacji screenera | potwierdzone (snapshot) | Pełne pobranie dwóch stron region='pl' (offset 0 i 250) z total=429 | Snapshot historyczny; nie dowodzi stabilności 24/7 | Dalszy audyt właściciela po decyzji o zakresie |
| Historyczna zgodność dwóch stron z total | potwierdzone (snapshot) | Suma 250 + 179 = 429, strony rozłączne, 0 duplikatów | Snapshot historyczny | — |
| Filtr cenowy GTE + LTE | potwierdzone (snapshot) | total=172, min 0.116, max 9.54, 0 naruszeń | Snapshot historyczny | — |
| Powtarzalność dwóch bezpośrednich przejść | potwierdzone (snapshot) | 6 wywołań; wyniki A i B identyczne | Nie dowodzi stabilności godzinowej, dziennej ani 24/7 | Dalszy audyt w dłuższych horyzontach |
| Oficjalna kompletność GPW | niepotwierdzone | Brak dowodu w wynikach | Screener nie dowodzi kompletności | Decyzja właściciela o kryterium kompletności |
| Oficjalna kompletność NewConnect | niepotwierdzone | Brak dowodu w wynikach | Screener nie dowodzi objęcia NewConnect | Wykonawcze sprawdzenie objęcia NewConnect przez region='pl' |
| Rozróżnienie segmentu (Główny Rynek / NewConnect) | niepotwierdzone | Brak pola rozróżniającego w lokalnym kodzie; brak dowodu wykonawczego | Brak literalnego pola nie dowodzi braku pola w surowej odpowiedzi | Dalszy audyt surowych odpowiedzi |
| Obecność 7LEVELS w Yahoo | nierozstrzygnięte | Search PL7LVLS00017: total=0, STOP | Pusty Search nie dowodzi braku 7LEVELS | Dalszy audyt po decyzji właściciela |
| Status 7LEVELS na NewConnect | potwierdzony referencyjnie na 2026-08-13 | Oficjalna karta NewConnect, tabela NC Base i załącznik do Uchwały GPW nr 503/2026 | Nie potwierdza obecności ani symbolu w Yahoo | Wykorzystać wyłącznie jako referencję kontrolną przyszłego audytu Yahoo |
| Lookup | częściowo potwierdzone (statycznie) | DOWÓD STATYCZNY: mechanizm RESOLUTION, start=0, brak publicznej paginacji | Brak wykonawczego audytu Lookup | Wykonawczy audyt po decyzji właściciela |
| quoteSummary | częściowo potwierdzone (statycznie) | DOWÓD STATYCZNY: mechanic DETAIL/ENRICHMENT, wymaga symbolu | Brak wykonawczego audytu quoteSummary | Wykonawczy audyt z modułami price, quoteType, summaryDetail |
| /v7/finance/quote | częściowo potwierdzone (statycznie) | DOWÓD STATYCZNY: wymaga jednoznacznie rozwiązanego symbolu | Brak wykonawczego audytu | Wykonawczy audyt po decyzji właściciela |
| chart metadata | częściowo potwierdzone (statycznie) | DOWÓD STATYCZNY: mechanizm PRICE/HISTORY, wymaga symbolu | Brak wykonawczego audytu | Wykonawczy audyt po decyzji właściciela |
| Semantyka COMPLETE/PARTIAL/ERROR | nierozstrzygnięte | Brak definicji zatwierdzonej przez właściciela | Nie zdefiniowano kryteriów | Decyzja właściciela o definicji |
| Gotowość produkcyjna 24/7 | niepotwierdzone | Brak dowodu stabilności czasowej | Wyniki są snapshotami | Dalszy audyt stabilności po decyzji właściciela |
| Implementacja dynamicznego InstrumentSource | niepotwierdzone / niewdrożone | Brak decyzji wdrożeniowej | Dokument nie zatwierdza implementacji | Zgoda właściciela na implementację |

---

## OTWARTE DECYZJE WŁAŚCICIELA

Kategoria: **OTWARTE**.

Otwarte decyzje wymagające jawnego rozstrzygnięcia właściciela:

- zatwierdzenie custom screenera jako podstawowego mechanizmu DISCOVERY;
- zakres następnego audytu wykonawczego;
- warianty (kategorie zapytań) Search i Lookup;
- kryterium jednoznacznego powiązania rekordu screenera z instrumentem;
- wykonawcze potwierdzenie objęcia NewConnect przez region='pl';
- użycie quoteSummary z modułami:
  - price;
  - quoteType;
  - summaryDetail;
- użycie /v7/finance/quote;
- użycie chart metadata;
- definicja COMPLETE/PARTIAL/ERROR;
- obsługa:
  - pustej strony;
  - zmiany total;
  - duplikatów;
  - brakującego symbolu;
  - częściowego wyniku;
  - błędu strony;
- zgoda na implementację dynamicznego uniwersum.

Nie podejmuje się tych decyzji w niniejszym dokumencie.

---

## STATUS PROJEKTU PRZYSZŁEGO AUDYTU (PROPOZYCJA — NIEZATWIERDZONA)

Poniższy opis jest wyłącznie niezatwierdzoną propozycją, nie zatwierdzonym planem:

- gałęzie logicznie niezależne;
- wykonanie fizycznie sekwencyjne;
- custom screener bazowy;
- screener cenowy:
  - GTE 0.10;
  - LTE 10.00;
- Search i Lookup jako niezależne resolution;
- operacje szczegółowe wyłącznie po rozwiązaniu symbolu;
- quoteSummary:
  - price, quoteType, summaryDetail;
- /v7/finance/quote;
- chart metadata;
- bez retry;
- bez fallbacku;
- bez sztucznego limitu żądań;
- bez zakładania 7LV.WA;
- bez zastępczego instrumentu NewConnect;
- bez użycia XTB jako źródła.

---

## OGRANICZENIA KOŃCOWE

Dokument jednoznacznie stwierdza:

- Nie udowodniono oficjalnej kompletności GPW + NewConnect.
- Nie udowodniono stabilności Yahoo 24/7.
- Nie udowodniono rozróżnienia Głównego Rynku GPW i NewConnect.
- Nie udowodniono obecności 7LEVELS w Yahoo.
- Nie udowodniono kompletności endpointów Yahoo poza lokalnym yfinance 1.5.2.
- Wyniki wykonawcze są snapshotami konkretnych przebiegów.
- Dokument nie jest podstawą do wdrożenia bez dalszych decyzji właściciela.
- Dokument nie zatwierdza implementacji.

---

## KONIEC DOKUMENTU

Data utworzenia: 13.08.2026

Status: KANONICZNY DOKUMENT DOWODOWY — NIE ZATWIERDZA IMPLEMENTACJI

Dokument czeka na ocenę i decyzję właściciela projektu.