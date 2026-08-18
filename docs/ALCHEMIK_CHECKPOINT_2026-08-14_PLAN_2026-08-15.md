# ALCHEMIK — checkpoint pracy z 14.08.2026 i punkt startowy na 15.08.2026

## 1. Status dokumentu

- Rodzaj: projektowy punkt wznowienia pracy.
- Data podsumowania: 14.08.2026.
- Planowany dzień kontynuacji: 15.08.2026.
- Zakres: uporządkowanie wyników audytów Yahoo Finance, ustalenie roli mechanizmów pomocniczych oraz zamknięcie testów wariantów symboli dla POLTRONIC i NEW TECH VENTURE.
- Decyzja właściciela: końcowy wniosek z testów `PTN`/`NTV` został zatwierdzony.
- Decyzja właściciela: Krok 1/6 audytu pokrycia NewConnect oraz osiem instrumentów zamrożonej referencji testowej zostały zatwierdzone.
- Decyzja właściciela: kontrakt statusów i warunków dopasowania Kroku 2/6 został zatwierdzony.
- Decyzja właściciela: plan wykonawczy Kroku 3/6, z rozdzieleniem na 3A offline i 3B sieciowy, został zatwierdzony.
- Stan implementacji: nie rozpoczęto implementacji dynamicznego uniwersum i nie udzielono na nią zgody.

Ten dokument nie zastępuje kanonicznego audytu Yahoo Finance. Jest checkpointem roboczym wskazującym, co zostało ustalone i od czego rozpocząć kolejną sesję.

## 2. Role i sposób podejmowania decyzji

1. Adam jest właścicielem i konstruktorem projektu ALCHEMIK.
2. Właściciel zatwierdza albo odrzuca wnioski, zakres kolejnych kroków i implementację.
3. Asystent jest asystentem technicznym. Przedstawia fakty, różnice, ryzyka, ograniczenia i możliwe następstwa, ale nie podejmuje decyzji za właściciela.
4. Jeżeli brakuje danych albo decyzji, należy zapytać właściciela. Nie wolno zgadywać.
5. Bez jednoznacznej zgody właściciela nie wolno implementować, rozszerzać zakresu ani zmieniać architektury.
6. Wynik raportu Cline nie staje się automatycznie decyzją projektu. Wymaga oceny i zatwierdzenia właściciela.

## 3. Stały kontekst projektu

- Projekt początkowo dotyczy akcji Głównego Rynku GPW oraz NewConnect.
- Początkowy zakres cenowy wynosi od `0,10 PLN` do `10,00 PLN`, z obiema granicami włącznie.
- Uniwersum ma być tworzone automatycznie, bez stałej watchlisty i bez ręcznie wpisanych tickerów.
- Produkcyjnym źródłem danych rynkowych pozostaje wyłącznie Yahoo Finance.
- Oficjalne materiały GPW i NewConnect mogą być używane wyłącznie jako datowana, zamrożona referencja kontrolna. Nie są drugim źródłem produkcyjnym.
- System docelowo ma działać 24/7 na serwerze VPS Hetzner.
- Strona WWW ma być responsywna i dostępna na komputerze, laptopie, tablecie oraz telefonie.
- Docelowym modelem AI jest `gpt-4o`.
- AI znajduje się na końcu ścieżki. Otrzymuje wyłącznie dane wcześniej przepuszczone przez reguły i moduły systemu.
- GPT-4o nie służy do odkrywania uniwersum ani zastępowania walidacji danych rynkowych.
- Tavily i Telegram nie należą do bieżącej ścieżki odkrywania instrumentów Yahoo.
- Sekretów OpenAI, Tavily i Telegrama nie wolno odczytywać, ujawniać ani zapisywać w raportach.

## 4. Ustalenia zatwierdzone przez właściciela

### 4.1. Podstawowa ścieżka produkcyjna Yahoo

Przyjęty kierunek projektowy:

`custom screener Yahoo → walidacja rekordów i symboli → quote/chart → moduły systemowe → GPT-4o`

Znaczenie poszczególnych etapów:

1. Custom screener Yahoo jest podstawowym mechanizmem odkrywania symboli.
2. System przyjmuje wyłącznie symbole rzeczywiście zwrócone przez Yahoo w zbiorze akcji.
3. Rekord musi przejść walidację typu instrumentu i pól rynku przed dalszym użyciem.
4. Endpointy symbolowe, w szczególności quote i chart, służą do potwierdzenia tożsamości i pobrania danych dla symboli odkrytych przez screener.
5. Moduły systemowe filtrują, obliczają i oceniają dane przed przekazaniem ich do AI.
6. GPT-4o działa na końcu i nie otrzymuje niezweryfikowanego strumienia Yahoo.

### 4.2. Search i Lookup

- Yahoo Search i Yahoo Lookup zostały uznane za mechanizmy pomocnicze oraz diagnostyczne.
- Nie są produkcyjnym źródłem uniwersum.
- Nie mogą być obowiązkową bramką dopuszczającą symbol odkryty przez custom screener.
- Brak wyniku Search albo Lookup nie może samodzielnie odrzucić poprawnego rekordu zwróconego przez screener.
- Wynik Search albo Lookup nie może samodzielnie zatwierdzić mechanicznie skonstruowanego symbolu.

### 4.3. Sztuczny limit wywołań

- Yahoo Finance jest wykorzystywane jako bezpłatne źródło danych.
- Sztuczny limit wywołań został przyjęty dla kontrolowanych audytów.
- Limit nie jest kosztem AI ani ograniczeniem biznesowym dla dwóch spółek.
- Jego funkcją jest ochrona metody badawczej: blokada nieplanowanych retry, fallbacków, pętli i dodatkowych żądań, a także możliwość rozliczenia każdego wywołania.
- Limit audytowy nie określa jeszcze produkcyjnego budżetu wywołań systemu 24/7.

### 4.4. Zakaz konstruowania symboli

- Nie wolno tworzyć symbolu Yahoo przez automatyczne dopisanie `.WA`, `.PL` ani innej końcówki do oficjalnego tickera.
- Nie wolno uznawać samego zgodnego tekstu symbolu za dowód tożsamości spółki.
- Końcówka `.WA`, `exchange=WSE`, `market=pl_market` i waluta `PLN` nie dowodzą samodzielnie, że rekord jest właściwą akcją ani że należy do Głównego Rynku albo NewConnect.
- Pole `quoteType` lub `instrumentType` musi potwierdzać `EQUITY`. Instrument typu `MUTUALFUND`, `ECNQUOTE` albo innego typu nie może zostać przyjęty jako akcja tylko dlatego, że symbol wygląda poprawnie.

## 5. Dzisiejszy zakres pracy

### 5.1. Dokument kanoniczny audytu Yahoo

- Utworzono i zweryfikowano dokument `docs/ALCHEMIK_AUDYT_YAHOO_FINANCE.md`.
- Zweryfikowany stan dokumentu: 593 linie, SHA-256 `e1212f6c9b1c76c40a897980d22b231d82181869b2c65c3ae765255aa732d984`.
- Dokument pozostawał jedynym plikiem untracked w raportowanym stanie repozytorium.
- Do dokumentu dodano zamrożoną oficjalną referencję statusu 7LEVELS na NewConnect z datą 13.08.2026.
- Oficjalny ticker `7LV` nie został utożsamiony z niepotwierdzonym symbolem Yahoo `7LV.WA`.
- Obecność 7LEVELS w Yahoo pozostaje nierozstrzygnięta.

### 5.2. Stan screenerów Yahoo w badanych snapshotach

Wcześniejszy pełny przebieg wykazał:

- zbiór bazowy: `429` unikalnych rekordów;
- zbiór cenowy `0,10–10,00 PLN`: `172` unikalne rekordy.

Późniejsze snapshoty z 13.08.2026 wykazały:

- zbiór bazowy: `427` unikalnych rekordów;
- zbiór cenowy `0,10–10,00 PLN`: `171` unikalnych rekordów.

Różnica jest zmianą pomiędzy datowanymi odpowiedziami Yahoo. Nie należy nadpisywać nią wyników historycznych ani przedstawiać liczby 427 lub 171 jako stałej.

W badanych snapshotach rekordy screenera spełniały wspólny profil:

- `quoteType=EQUITY`;
- `exchange=WSE`;
- `market=pl_market`;
- `currency=PLN`;
- symbol zakończony `.WA`.

Nie udowodniono, że zbiór Yahoo jest kompletną oficjalną listą GPW + NewConnect. Nie znaleziono również jawnego pola rozróżniającego segment Głównego Rynku GPW od NewConnect.

### 5.3. Dodatnie kontrole STX.WA i MIR.WA

- `STX.WA` i `MIR.WA` zostały znalezione w bazowym i cenowym custom screenerze.
- Screener, quoteSummary, zbiorczy quote oraz chart zgodnie rozpoznały oba instrumenty jako polskie akcje `EQUITY` na WSE, w PLN.
- Mechanizmy downstream działały poprawnie dla symboli faktycznie odkrytych w screenerze.
- Search i Lookup okazały się niestabilne jako mechanizm rozwiązywania tożsamości: skrócone nazwy i rygorystyczne dopasowanie powodowały brak rozwiązania mimo poprawnych symboli w screenerze.
- Wynik potwierdza rolę Search i Lookup jako narzędzi pomocniczych, a nie bramki produkcyjnej.
- Krok 4C nie badał instrumentu NewConnect i nie dowodzi kompletności tego segmentu w Yahoo.

### 5.4. 4MASS i 7LEVELS

- Dla 4MASS mechanizmy pomocnicze wskazały `4MS.WA`, a endpointy symbolowe działały.
- Dla 7LEVELS Search i Lookup nie zwróciły rozwiązania; Yahoo pozostaje nierozstrzygnięte.
- Oficjalna obecność 7LEVELS na NewConnect w zamrożonej referencji nie jest dowodem obecności w Yahoo.
- Nie wolno wyprowadzać `7LV.WA` wyłącznie z oficjalnego tickera `7LV`.

### 5.5. Krok 5 — kandydaci PTN.WA i NTV.WA

Zamrożone referencje kontrolne:

| Spółka | Oficjalny ticker | ISIN | Rynek |
| --- | --- | --- | --- |
| POLTRONIC S.A. | `PTN` | `PLPLTRN00018` | NewConnect |
| NEW TECH VENTURE S.A. | `NTV` | `PLSTCKI00016` | NewConnect |

Wynik Yahoo:

| Kandydat | Wynik endpointów symbolowych | Obecność w screenerze EQUITY | Wniosek |
| --- | --- | --- | --- |
| `PTN.WA` | `MUTUALFUND` | brak | nie jest akcją POLTRONIC |
| `NTV.WA` | `MUTUALFUND` | brak | nie jest akcją NEW TECH VENTURE |

Oba symbole wskazują w Yahoo fundusze albo błędnie zmapowane encje funduszowe. Nie wolno ich używać w ALCHEMIKU jako akcji referencyjnych spółek NewConnect.

### 5.6. Krok 5A — warianty bez `.WA`

Zbadano dokładnie cztery warianty: `PTN`, `PTN.PL`, `NTV`, `NTV.PL`.

| Wariant | Faktyczny wynik Yahoo | Końcowa klasyfikacja zatwierdzona przez właściciela |
| --- | --- | --- |
| `PTN` | Palatin Technologies, Inc.; Nasdaq; USD; `EQUITY` | `OTHER_INSTRUMENT` — inna spółka, nie POLTRONIC |
| `PTN.PL` | HTTP 404 / brak instrumentu | `NOT_FOUND` |
| `NTV` | NeoTV Group Ltd; Nasdaq; USD; `ECNQUOTE` | `OTHER_INSTRUMENT` — inna spółka i inny typ instrumentu |
| `NTV.PL` | HTTP 404 / brak instrumentu | `NOT_FOUND` |

Korekta przyjęta przez właściciela:

- klasyfikacja `PTN` jako `UNRESOLVED` w raporcie wykonawczym była zbyt słaba;
- Yahoo rozwiązało `PTN` jednoznacznie, ale do innej spółki, dlatego poprawną klasyfikacją jest `OTHER_INSTRUMENT`;
- POLTRONIC oraz NEW TECH VENTURE mają końcową klasyfikację `COMPANY_NOT_FOUND_IN_TESTED_VARIANTS`.

Łączny wynik wszystkich sześciu przetestowanych wariantów:

| Spółka referencyjna | Wariant | Wynik |
| --- | --- | --- |
| POLTRONIC | `PTN.WA` | fundusz `MUTUALFUND`, nie akcja spółki |
| POLTRONIC | `PTN` | Palatin Technologies, inna spółka |
| POLTRONIC | `PTN.PL` | brak |
| NEW TECH VENTURE | `NTV.WA` | fundusz `MUTUALFUND`, nie akcja spółki |
| NEW TECH VENTURE | `NTV` | NeoTV Group, inna encja `ECNQUOTE` |
| NEW TECH VENTURE | `NTV.PL` | brak |

Decyzja właściciela: testowanie wariantów PTN/NTV zostaje zamknięte. Żaden z sześciu wariantów nie może być produkcyjnym symbolem tych dwóch spółek w ALCHEMIKU.

## 6. Kanoniczne wnioski projektowe do pamięci

1. Uniwersum produkcyjne ma zaczynać się od rzeczywistych wyników custom screenera Yahoo, a nie od oficjalnego tickera z mechanicznie dopisaną końcówką.
2. Akceptowane są tylko rekordy będące akcjami `EQUITY` i przechodzące walidację rynku, waluty, ceny oraz tożsamości.
3. Search i Lookup są mechanizmami pomocniczymi oraz diagnostycznymi. Nie stanowią bramki produkcyjnej.
4. Quote i chart są mechanizmami potwierdzającymi oraz dostarczającymi dane dla symboli odkrytych przez screener.
5. GPT-4o działa dopiero po filtrach i modułach systemowych. Nie odkrywa symboli i nie naprawia błędnych encji Yahoo.
6. Oficjalna lista GPW/NewConnect jest wyłącznie referencją kontrolną. Yahoo pozostaje jedynym źródłem produkcyjnym.
7. Symbol wyglądający poprawnie może oznaczać inną spółkę, fundusz albo inny rodzaj instrumentu. Walidacja typu i tożsamości jest obowiązkowa.
8. Nie wolno automatycznie dopisywać `.WA`, `.PL` ani innego sufiksu.
9. `PTN.WA`, `PTN`, `PTN.PL`, `NTV.WA`, `NTV` i `NTV.PL` są zamkniętymi, odrzuconymi wariantami dla referencyjnych spółek POLTRONIC i NEW TECH VENTURE.
10. Brak referencyjnej spółki w przetestowanych wariantach Yahoo nie dowodzi, że nie istnieje ona na NewConnect. Dowodzi wyłącznie braku poprawnej reprezentacji w zbadanej części Yahoo.
11. Nie udowodniono oficjalnej kompletności GPW + NewConnect ani stabilności Yahoo 24/7.
12. Nie zatwierdzono jeszcze implementacji dynamicznego uniwersum.

## 7. Co pozostaje nierozstrzygnięte

1. Czy właściciel akceptuje zakres produkcyjny jako „polskie akcje odkryte i poprawnie zwalidowane w Yahoo”, mimo że Yahoo może nie obejmować całego NewConnect?
2. Jak system ma komunikować instrumenty oficjalnie obecne na GPW/NewConnect, których Yahoo nie zwraca jako poprawnych akcji?
3. Czy brak jawnego pola segmentu oznacza, że wersja startowa ma działać na wspólnym uniwersum WSE bez technicznego rozdzielenia Głównego Rynku i NewConnect?
4. Jak często produkcyjny system ma odświeżać pełne uniwersum i jak długo może używać ostatniego poprawnego snapshotu po błędzie Yahoo?
5. Jaka ma być produkcyjna polityka limitów, retry, timeoutów, cache i ochrony przed pętlą? Sztuczny limit audytowy nie rozstrzyga tych wartości.
6. Jakie minimalne pola quote i chart są wymagane przed dopuszczeniem symbolu do modułów analitycznych?

## 8. Punkt startowy na 15.08.2026

### Decyzja właściciela o kolejności prac

Przed rozstrzyganiem zakresu produkcyjnego należy najpierw sprawdzić, czy proponowany audyt pokrycia NewConnect działa poprawnie. `audyt_nc_coverage` pozostaje na tym etapie niezależnym, kontrolowanym audytem poza runtime ALCHEMIKA.

Obowiązuje następująca, zatwierdzona kolejność:

1. Ustalić zamrożoną referencję testową GPW/NC.
2. Zdefiniować jednoznaczne statusy i warunki dopasowania.
3. Przeprowadzić mały, kontrolowany proof of concept poza runtime projektu.
4. Ocenić, czy dwukierunkowe porównanie referencji z Yahoo rzeczywiście działa i daje rozstrzygalne wyniki.
5. Dopiero po pozytywnej ocenie PoC zdecydować o pełnym audycie aktualnego snapshotu Yahoo.
6. Integrację z ALCHEMIKIEM rozważać dopiero po zatwierdzeniu pełnego wyniku audytu przez właściciela.

### Ograniczenia zatwierdzonej sekwencji

- Nie tworzyć jeszcze katalogu `modules/audit_nc` ani innej struktury produkcyjnej.
- Nie zmieniać RuntimeService, MasterEngine ani pozostałej zamrożonej architektury.
- Nie wdrażać procesu 24/7.
- Nie wykonywać pełnego audytu setek instrumentów przed zatwierdzeniem PoC.
- Nie traktować oficjalnej referencji GPW/NC jako drugiego źródła cen rynkowych.
- Nie rozpoczynać implementacji bez osobnej decyzji właściciela.

### Krok 1/6 — ZAMKNIĘTY I ZATWIERDZONY

Data zamrożenia referencji testowej: `2026-08-14`.

| Segment referencyjny | Oficjalny ticker | ISIN | Oficjalna nazwa | Rola kontrolna |
| --- | --- | --- | --- | --- |
| `GPW_MAIN` | `STX` | `PLSTLEX00019` | STALEXPORT AUTOSTRADY S.A. | znana dodatnia kontrola Głównego Rynku |
| `GPW_MAIN` | `MIR` | `PLKLSTN00017` | MIRACULUM S.A. | znana dodatnia kontrola Głównego Rynku |
| `NEWCONNECT` | `LUG` | `PLLUG0000010` | LUG S.A. | oficjalna kontrola NewConnect do zbadania w Yahoo |
| `NEWCONNECT` | `TRX` | `PLAUXLM00026` | TREX S.A. | oficjalna kontrola NewConnect do zbadania w Yahoo |
| `NEWCONNECT` | `SUN` | `PLSNTCH00012` | SUNTECH S.A. | oficjalna kontrola NewConnect do zbadania w Yahoo |
| `NEWCONNECT` | `PTN` | `PLPLTRN00018` | POLTRONIC S.A. | znany przypadek kolizji symbolu Yahoo |
| `NEWCONNECT` | `NTV` | `PLSTCKI00016` | NEW TECH VENTURE S.A. | znany przypadek kolizji symbolu Yahoo |
| `NEWCONNECT` | `7LV` | `PL7LVLS00017` | 7LEVELS S.A. | znany przypadek nierozstrzygnięty w Yahoo |

Oficjalne źródła referencji:

- `STX`: `https://www.gpw.pl/spolka?isin=PLSTLEX00019`
- `MIR`: `https://www.gpw.pl/spolka?isin=PLKLSTN00017`
- `LUG`: `https://newconnect.pl/spolka?isin=PLLUG0000010`
- `TRX`: `https://newconnect.pl/spolka?isin=PLAUXLM00026`
- `SUN`: `https://newconnect.pl/spolka?isin=PLSNTCH00012`
- `PTN`: `https://newconnect.pl/spolka?isin=PLPLTRN00018`
- `NTV`: `https://newconnect.pl/spolka?isin=PLSTCKI00016`
- `7LV`: `https://newconnect.pl/spolka?isin=PL7LVLS00017`

Kontrakt rekordu referencyjnego:

- `snapshot_date`;
- `official_ticker`;
- `isin`;
- `official_name`;
- `segment_ref`;
- `official_source_url`;
- `reference_status`.

Obowiązkowe ograniczenia Kroku 1:

- `segment_ref` pochodzi wyłącznie z oficjalnej referencji GPW/NewConnect, a nie z Yahoo;
- Yahoo nie zwraca oznaczenia `NC` ani `GPW_MAIN`;
- `.WA` jest wspólnym oznaczeniem Yahoo dla instrumentów warszawskich i nie rozróżnia Głównego Rynku od NewConnect;
- ISIN pozostaje podstawowym identyfikatorem oficjalnej referencji, ale Yahoo nie zapewnia potwierdzonego, kompletnego i niezawodnego kontraktu `ISIN → symbol Yahoo`;
- relacja `referencyjny ISIN → symbol Yahoo` ma być wynikiem przyszłego audytu, a nie założeniem wejściowym;
- przykład `Lookup(PL4MASS00011) → 4MS.WA` dowodzi, że niektóre zapytania ISIN mogą działać, dlatego nie wolno twierdzić, że Yahoo nigdy nie rozwiązuje ISIN;
- VIVID GAMES nie należy do referencji NewConnect: na dzień zamrożenia oficjalna karta umieszcza spółkę na Głównym Rynku GPW, z ISIN `PLVVDGM00014` i skrótem `VVD`;
- referencja nie zawiera założonych symboli Yahoo, wyników Yahoo, cen ani oczekiwanej klasyfikacji końcowej;
- Krok 1 nie wykonał żadnego wywołania Yahoo i nie zatwierdził implementacji.

### Krok 2/6 — ZAMKNIĘTY I ZATWIERDZONY

#### Rozdzielenie danych

Każdy wynik audytu zachowuje osobno:

- `segment_ref` — wyłącznie z oficjalnej referencji;
- `yahoo_symbol` — wyłącznie symbol faktycznie zwrócony przez Yahoo;
- pola screenera;
- pola quoteSummary;
- pola chart;
- pola `/v7/finance/quote`;
- statusy poszczególnych endpointów;
- końcową klasyfikację audytu.

Yahoo nie otrzymuje pola `NC` i nie jest pytane o segment.

#### Dopasowanie symbolu

1. Potwierdzić, że symbol pochodzi z rzeczywistego snapshotu screenera.
2. Usunąć `.WA` wyłącznie roboczo w celu porównania z `official_ticker`.
3. Nie tworzyć symbolu Yahoo przez dopisanie `.WA` do oficjalnego tickera.
4. Porównać rdzeń rzeczywistego symbolu Yahoo z `official_ticker`.
5. Zweryfikować nazwę przy użyciu dostępnych pól `shortName` i `longName`.
6. Jeżeli Yahoo udostępni ISIN, porównać go bezpośrednio, ale nie wymagać jego obecności.

#### Status tożsamości

`IDENTITY_CONFIRMED` wymaga:

- symbolu pochodzącego ze screenera;
- zgodności rdzenia symbolu z oficjalnym tickerem;
- zgodności dostępnej nazwy Yahoo z nazwą oficjalną;
- braku dowodu wskazującego inną spółkę;
- braku więcej niż jednego możliwego dopasowania.

`IDENTITY_CONFLICT` występuje, gdy:

- symbol wskazuje inną nazwę spółki;
- ISIN jest różny, jeżeli oba ISIN-y są dostępne;
- ticker koliduje z zagraniczną spółką;
- symbol wskazuje fundusz albo inny instrument zamiast referencyjnej akcji.

`IDENTITY_AMBIGUOUS` występuje, gdy:

- ticker jest zgodny, ale brakuje danych o nazwie;
- nazwa jest zbyt skrócona, aby potwierdzić tożsamość;
- więcej niż jedna referencja może pasować;
- dane są niewystarczające, ale nie ma bezpośredniego konfliktu.

Nie stosować liczbowego progu podobieństwa nazw bez osobnej decyzji właściciela.

#### Walidacja typu i rynku

Dla prawidłowej akcji oczekuje się zgodności dostępnych pól:

- screener: `quoteType=EQUITY`;
- quoteSummary: `quoteType=EQUITY`;
- chart: `instrumentType=EQUITY`;
- exchange: `WSE` albo równoważne jawne pole Warsaw;
- currency: `PLN`;
- market: `pl_market`, jeżeli pole występuje.

Brak opcjonalnego pola nie oznacza konfliktu. Jawna inna wartość oznacza konflikt.

#### Status pojedynczego endpointu

| Status | Znaczenie |
| --- | --- |
| `ENDPOINT_OK` | odpowiedź poprawna i zawiera oczekiwany rekord |
| `ENDPOINT_NOT_FOUND` | kontrolowany brak rekordu albo potwierdzone 404 |
| `ENDPOINT_MISSING_FIELDS` | rekord istnieje, ale brakuje wymaganych danych |
| `ENDPOINT_TYPE_CONFLICT` | zwrócono inny typ instrumentu |
| `ENDPOINT_IDENTITY_CONFLICT` | zwrócono inną spółkę |
| `ENDPOINT_HTTP_ERROR` | błąd HTTP inny niż kontrolowany brak |
| `ENDPOINT_PARSE_ERROR` | odpowiedzi nie można wiarygodnie odczytać |
| `ENDPOINT_NOT_EXECUTED` | endpoint nie został wykonany zgodnie z planem |

Błąd techniczny nie jest dowodem nieobecności instrumentu.

#### Końcowe statusy instrumentu

| Status | Warunek |
| --- | --- |
| `MATCHED_EQUITY` | tożsamość potwierdzona, typ `EQUITY`, rynek i waluta zgodne, wymagane endpointy zgodne |
| `TYPE_CONFLICT` | przynajmniej jeden wiarygodny wynik wskazuje fundusz, ETF, ECNQUOTE albo inny typ |
| `IDENTITY_CONFLICT` | symbol wskazuje inną spółkę lub inny ISIN |
| `DOWNSTREAM_PARTIAL` | screener i tożsamość są zgodne, ale część endpointów nie dostarczyła pełnego potwierdzenia |
| `DOWNSTREAM_NOT_FOUND` | symbol był w screenerze, ale żaden endpoint downstream nie zwrócił użytecznego rekordu |
| `AMBIGUOUS` | dowody nie pozwalają potwierdzić ani odrzucić tożsamości |
| `NOT_IN_SCREENER_SNAPSHOT` | oficjalny instrument referencyjny nie został dopasowany do żadnego rekordu aktualnego snapshotu |
| `YAHOO_EQUITY_UNMATCHED_REFERENCE` | rekord Yahoo `EQUITY` nie został dopasowany do oficjalnej referencji |
| `AUDIT_ERROR` | błąd techniczny uniemożliwił klasyfikację |

#### Kolejność pierwszeństwa

1. `AUDIT_ERROR`, jeżeli nie można ocenić dowodów.
2. `IDENTITY_CONFLICT`, jeżeli wskazano inną spółkę.
3. `TYPE_CONFLICT`, jeżeli wskazano inny typ instrumentu.
4. `AMBIGUOUS`, jeżeli tożsamość pozostaje nierozstrzygnięta.
5. `DOWNSTREAM_NOT_FOUND`.
6. `DOWNSTREAM_PARTIAL`.
7. `MATCHED_EQUITY`.

Konflikt ma pierwszeństwo przed brakującym polem albo wynikiem częściowym.

#### Raport NewConnect i cena

Raport NewConnect powstaje przez filtr `segment_ref == NEWCONNECT`, a następnie grupowanie według statusu końcowego. Nie używać statusu `MISMATCH_SEGMENT`, ponieważ Yahoo nie zwraca segmentu.

Zakres `0,10–10,00 PLN` jest osobną cechą:

- `price_eligible=true`;
- `price_eligible=false`;
- `price_eligibility_unknown`.

Cena nie decyduje o tożsamości ani pokryciu Yahoo.

Krok 2 nie wykonał żadnego wywołania Yahoo i nie zatwierdził implementacji.

### Krok 3/6 — PLAN ZATWIERDZONY, WYKONANIE NIEZAKOŃCZONE

Krok 3 dzieli się obowiązkowo na:

- `3A` — przygotowanie i pełna walidacja offline, bez sieci;
- `3B` — jeden kontrolowany przebieg Yahoo dopiero po zatwierdzeniu wyniku 3A przez właściciela.

#### Zakres referencji PoC

PoC używa dokładnie ośmiu zamrożonych instrumentów:

- `GPW_MAIN`: `STX`, `MIR`;
- `NEWCONNECT`: `LUG`, `TRX`, `SUN`, `PTN`, `NTV`, `7LV`.

Referencja jest niepełnym zbiorem testowym. Nie wolno klasyfikować pozostałych rekordów Yahoo jako `YAHOO_EQUITY_UNMATCHED_REFERENCE`. Rekordy spoza ośmiu referencji otrzymują techniczne oznaczenie `OUT_OF_POC_SCOPE`. Status `YAHOO_EQUITY_UNMATCHED_REFERENCE` może zostać użyty dopiero w pełnym audycie opartym na kompletnej referencji.

#### Dwa tory PoC

Tor A — discovery ze screenera:

1. Pełny bazowy screener `region='pl'`.
2. Pełny screener cenowy `0,10–10,00 PLN` z granicami włącznie.
3. Wyszukanie ośmiu referencji w rzeczywistych rekordach Yahoo.
4. Dla odnalezionych symboli wykonanie quoteSummary, chart i zbiorczego `/v7/finance/quote`.
5. Klasyfikacja według zatwierdzonego kontraktu Kroku 2.

Nie tworzyć symboli przez dopisywanie `.WA`.

Tor B — znane kolizje:

- dopuszczone są wyłącznie `PTN.WA` i `NTV.WA`, rzeczywiście zaobserwowane we wcześniejszym audycie Yahoo;
- pochodzenie obu symboli zapisać jako `PRIOR_YAHOO_AUDIT_OBSERVED_SYMBOL`;
- dla obu wykonać quoteSummary, chart i `/v7/finance/quote`;
- nie generować ani nie wykonywać `7LV.WA`, ponieważ nie został potwierdzony jako symbol Yahoo.

#### Deterministyczne dopasowanie nazw

Dozwolona normalizacja:

- zmiana wielkości liter;
- usunięcie interpunkcji;
- ujednolicenie polskich znaków;
- usunięcie form prawnych, np. `S.A.` i `SPÓŁKA AKCYJNA`;
- redukcja wielokrotnych spacji.

Nie stosować fuzzy matching ani liczbowego progu podobieństwa. Dopasowanie powstaje, gdy rdzeń rzeczywistego symbolu Yahoo odpowiada `official_ticker` albo znormalizowana pełna nazwa jest dokładnie zgodna. Sama niewystarczająca nazwa skrócona daje `AMBIGUOUS`.

#### Dozwolone i zabronione operacje

Dozwolone:

- cookie bootstrap;
- crumb;
- custom screener;
- quoteSummary;
- chart;
- zbiorczy `/v7/finance/quote`.

Zabronione:

- Search;
- Lookup;
- XTB i drugi dostawca danych;
- Tavily;
- GPT-4o;
- Telegram;
- scraping;
- dodatkowe warianty symboli;
- retry i fallback;
- równoległe żądania.

#### Batch quote

Lista symboli może być dzielona na paczki liczące nie więcej niż cztery symbole, ponieważ taki rozmiar został sprawdzony we wcześniejszym audycie. Nie zakładać, że cały zbiór można przesłać w jednym żądaniu.

#### Dynamiczny limit żądań

`LIMIT = 2 + P_base + P_price + 2 × (R + C) + B`

gdzie:

- `2` — cookie i crumb;
- `P_base` — rzeczywista liczba stron screenera bazowego;
- `P_price` — rzeczywista liczba stron screenera cenowego;
- `R` — liczba symboli referencyjnych faktycznie odnalezionych w screenerze;
- `C=2` — dwa wcześniej zaobserwowane symbole kolizyjne;
- `B` — rzeczywista liczba paczek `/v7/finance/quote`, maksymalnie po cztery symbole.

Każde faktycznie wysłane żądanie musi zostać zliczone.

#### Obsługa błędów

- `fc.yahoo.com` HTTP 404 można zaakceptować wyłącznie wtedy, gdy świeża sesja otrzyma użyteczne cookie `A3`.
- Kontrolowane 404 quoteSummary albo chart daje `ENDPOINT_NOT_FOUND` i nie przerywa całego PoC.
- Brak symbolu w odpowiedzi batch jest wynikiem endpointu, a nie błędem transportowym.
- Nieoczekiwane 3xx, 5xx, błąd transportu albo naruszenie limitu kończą przebieg bez retry.
- Wynik końcowy to `COMPLETE`, `PARTIAL` albo `ERROR`, zgodnie z rzeczywistym wykonaniem.

#### Podkrok 3A — aktywny zakres

Przed jakimkolwiek połączeniem sieciowym wymagane są:

- `ast.parse`;
- `compile`;
- import;
- zakaz tworzenia `.pyc`;
- sztuczny transport;
- symulacja wszystkich statusów endpointów;
- symulacja wszystkich statusów końcowych;
- pełna paginacja sztucznych odpowiedzi;
- dwukierunkowe dopasowanie ośmiu referencji;
- obsługa `OUT_OF_POC_SCOPE`;
- podział batchy;
- kontrola dynamicznego limitu;
- zapis i ponowny odczyt artefaktów;
- UTF-8;
- brak sekretów;
- pełny raport Git i artefaktów przed i po.

Po 3A należy podać SHA-256 niezmiennego skryptu. Bez osobnego zatwierdzenia właściciela skrypt nie może połączyć się z siecią.

#### Podkrok 3B — zablokowany

Po zatwierdzeniu 3A właściciel może dopuścić dokładnie jeden przebieg sieciowy niezmienionego skryptu o zatwierdzonym SHA-256. Wymagane będą świeża sesja i cache tymczasowy, pełna tabela żądań, zachowanie surowych odpowiedzi, klasyfikacja ośmiu referencji, osobna klasyfikacja dwóch kolizji oraz kontrola repozytorium przed i po.

3B pozostaje zablokowany do odrębnej decyzji właściciela.

#### Kryterium powodzenia PoC

PoC działa, jeżeli:

- wszystkie osiem referencji zostanie rozliczonych;
- żaden symbol Yahoo nie zostanie skonstruowany;
- oba kierunki dopasowania dadzą deterministyczny wynik;
- kolizje pozostaną oddzielone od discovery;
- każdy endpoint otrzyma osobny status;
- klasyfikacja końcowa będzie wynikała wyłącznie z kontraktu Kroku 2;
- wynik będzie możliwy do odtworzenia z zachowanych dowodów;
- repozytorium i sekrety pozostaną nienaruszone.

`COMPLETE` oznacza kompletne wykonanie PoC, a nie kompletność NewConnect w Yahoo.

## 9. Stan repozytorium i dokumentów

Stan raportowany przez Cline na końcu audytów:

- repozytorium: `C:\alchemik`;
- gałąź: `master`;
- HEAD: `8e4edbd5fe26a4ec8b2b4dbf4540614cf906da24`;
- dokładnie jeden plik untracked: `docs/ALCHEMIK_AUDYT_YAHOO_FINANCE.md`;
- staging pusty;
- brak zmian w śledzonych plikach;
- kanoniczny dokument audytu nie był zmieniany podczas późniejszych testów;
- nie wykonano operacji Git zmieniającej stan.

Niniejszy checkpoint jest nowym dokumentem przygotowanym poza dostępną kopią repozytorium `C:\alchemik`. Docelowa ścieżka w projekcie:

`docs/ALCHEMIK_CHECKPOINT_2026-08-14_PLAN_2026-08-15.md`

Przed dodaniem do repozytorium należy zweryfikować aktualny stan Git i upewnić się, że nie nadpisuje istniejącego pliku.

## 10. Oświadczenia końcowe

- Zapisano dzisiejsze ustalenia i punkt wznowienia pracy.
- Nie wykonano nowego wywołania Yahoo Finance.
- Nie wykonano wywołania XTB ani innego dostawcy danych.
- Nie użyto GPT-4o, Tavily ani Telegrama.
- Nie odczytano ani nie zapisano żadnego sekretu.
- Testów projektu nie uruchamiano.
- Nie wykonano implementacji.
- Nie zmieniono kodu ani konfiguracji projektu.
- Nie wykonano operacji Git zmieniającej stan.
- Nie zmieniono kanonicznego dokumentu audytu Yahoo Finance.
- Dokument nie zatwierdza implementacji dynamicznego uniwersum.
- Następna decyzja należy wyłącznie do właściciela projektu.
