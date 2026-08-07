# FILOZOFIA DZIAŁANIA ALCHEMIKA

## Cel projektu
ALCHEMIK ma na celu zapewnienie inwestorom przewagi czasowej poprzez ciągłe monitorowanie rynku i wykrywanie nietypowych zdarzeń.

## Dlaczego powstał ALCHEMIK
Projekt powstał w odpowiedzi na potrzebę nieustannego śledzenia rynku, co jest niemożliwe do wykonania ręcznie przez inwestora ze względu na liczbę spółek.

## Misja projektu
Misją ALCHEMIKA jest dostarczanie inwestorom aktualnych i istotnych informacji o rynku w czasie rzeczywistym.

## Główne założenia działania
- Ciągłe monitorowanie rynku 24/7
- Wykrywanie nietypowych zdarzeń
- Szybka reakcja i analiza
- Dostarczanie kompleksowych raportów

## Monitoring rynku 24/7
System nieprzerwanie monitoruje rynek, wykrywając wszelkie nietypowe ruchy.

## Wykrywanie zdarzeń rynkowych
ALCHEMIK identyfikuje zdarzenia, które mogą być istotne dla inwestora.

## Znaczenie czasu reakcji
Czas jest kluczowy - szybkie wykrycie i poinformowanie inwestora daje przewagę.

## Analiza matematyczna
System przeprowadza analizę matematyczną wykrytych zdarzeń.

## Analiza techniczna
ALCHEMIK analizuje wykresy i wskaźniki techniczne.

## Analiza fundamentalna
System sprawdza dane fundamentalne spółek.

## Wyszukiwanie aktualnych informacji
ALCHEMIK wyszukuje aktualne informacje mogące wyjaśnić przyczynę ruchu.

## Rola Tavily
Tavily jest wykorzystywany do wyszukiwania aktualnych informacji.

## Rola AI
AI interpretuje zebrane dane, ale nie podejmuje decyzji inwestycyjnych.

Szczegółowy podział odpowiedzialności pomiędzy obliczaniem rezultatów zdarzeń (komponentu odpowiedzialnego za wyliczanie EventOutcome) a ich interpretacją (AI) opisany jest w dokumencie `docs/FILOZOFIA_EVENTOUTCOME.md`.

## Powiadomienia Telegram
Telegram służy do natychmiastowego powiadamiania inwestora.

## Rola inwestora
Ostateczna decyzja inwestycyjna zawsze należy do inwestora.

## Podsumowanie filozofii projektu
ALCHEMIK nie jest botem inwestycyjnym, lecz inteligentnym szperaczem giełdowym, który dostarcza informacje, ale nie podejmuje decyzji.

## Status systemu
ALCHEMIK jest systemem wspomagania decyzji inwestycyjnych.

ALCHEMIK NIE podejmuje decyzji za inwestora.

System NIE wydaje rekomendacji:
- BUY
- SELL

System przedstawia kompletny obraz sytuacji.

Końcowa decyzja zawsze należy do użytkownika.

## Pytania, na które odpowiada ALCHEMIK
ALCHEMIK odpowiada na pytania:
- Co się dzieje?
- Dlaczego się dzieje?
- Czy podobna sytuacja występowała wcześniej?
- Jak zakończyły się podobne sytuacje?
- Czy istnieją nowe informacje?
- Jakie scenariusze są najbardziej prawdopodobne?

ALCHEMIK NIE odpowiada automatycznie:
"Kup"
lub
"Sprzedaj"

## Wczesne wykrywanie zmian
Zadaniem ALCHEMIKA jest jak najwcześniejsze wykrycie zmian zachodzących na rynku.

Największą wartość posiadają sygnały pojawiające się we wczesnej fazie ruchu.

System nie jest projektowany pod wykrywanie wyłącznie ekstremalnych zmian.

## Łączna analiza ceny i wolumenu
Cena i wolumen są analizowane łącznie.

Żaden z tych parametrów samodzielnie nie stanowi pełnej podstawy oceny sytuacji.

Interpretacja zawsze odbywa się z uwzględnieniem kontekstu.

## Indywidualna charakterystyka instrumentu
Każdy instrument posiada własną charakterystykę.

ALCHEMIK nie powinien opierać się wyłącznie na sztywnych progach wspólnych dla wszystkich spółek.

W przyszłości system powinien wykorzystywać historię zachowania konkretnego instrumentu.

## Minimalizacja czasu analizy
Rolą ALCHEMIKA jest możliwie maksymalne skrócenie czasu potrzebnego inwestorowi do zebrania informacji.

System powinien automatycznie prezentować między innymi:
- analizę ceny,
- analizę wolumenu,
- analizę techniczną,
- historię podobnych zdarzeń,
- wybicia ważnych poziomów,
- informacje fundamentalne,
- wiadomości,
- ocenę AI,
- możliwe scenariusze rozwoju sytuacji.

## Przepływ logiczny
1. Monitoring rynku 24/7
2. Wykrycie nietypowego zdarzenia
3. Analiza matematyczna
4. Analiza techniczna
5. Analiza fundamentalna
6. Wyszukiwanie aktualnych informacji
7. Tavily
8. Interpretacja AI
9. Przygotowanie raportu
10. Wysłanie raportu na Telegram
11. Decyzja inwestora

## Filozofia wieloetapowej analizy

ALCHEMIK został zaprojektowany jako system wieloetapowy. Każdy etap analizy odpowiada za własny obszar i przekazuje wyniki kolejnym warstwom. Decyzje podejmowane są stopniowo, na podstawie coraz pełniejszego kontekstu.

### Zasada nieeliminowania potencjalnych okazji

ALCHEMIK nie eliminuje potencjalnych okazji inwestycyjnych wyłącznie dlatego, że klasyczne wskaźniki techniczne nie potwierdzają jeszcze ruchu.

Wczesna faza rozwijającej się okazji często nie spełnia kryteriów dojrzałych formacji technicznych. Wskaźniki takie jak RSI, MACD czy średnie kroczące mogą jeszcze nie sygnalizować zmiany trendu, podczas gdy inne sygnały — na przykład zmiana wolumenu, nietypowa aktywność rynku lub pojawienie się nowych informacji — już wskazują na potencjalnie istotną sytuację.

System ma obowiązek przekazać kandydata do dalszych etapów analizy, nawet jeżeli pojedynczy silnik nie znajduje potwierdzenia w swoim obszarze odpowiedzialności.

### Odpowiedzialność Huntera rynku

Hunter rynku odpowiada za możliwie najwcześniejsze wykrywanie nietypowych zachowań na całym rynku groszówek GPW i USA.

Jego zadaniem jest przekazanie potencjalnych okazji do dalszej analizy, a nie podejmowanie końcowej decyzji inwestycyjnej.

Hunter rynku działa jako pierwszy filtr — identyfikuje instrumenty, których zachowanie odbiega od normalnego, i przekazuje je dalej. Nie ocenia, czy okazja jest dobra czy zła. Nie przypisuje sztucznych scoringów opartych na danych, które jeszcze nie powstały.

### Warstwy analityczne po wykryciu kandydata

Po wykryciu kandydata przez Huntera rynku kolejne warstwy systemu analizują go etapami. Obejmuje to między innymi:

- analizę techniczną — wskaźniki, formacje świecowe, wybicia, trendy, momentum,
- analizę historycznych zachowań danej spółki — jak instrument zachowywał się wcześniej w podobnych sytuacjach,
- analizę powtarzalności podobnych ruchów — czy dany wzorzec występował wielokrotnie,
- analizę wyników wcześniejszych zdarzeń — jak kończyły się poprzednie sytuacje tego typu,
- analizę kontekstu rynkowego — sytuacja sektora, rynku, otoczenia makroekonomicznego.

Każda warstwa dodaje własny kontekst, wzbogacając obraz sytuacji bez eliminowania instrumentu na podstawie niepełnych informacji.

### Rozpoznawanie powtarzalnych zachowań spółek

System powinien rozpoznawać powtarzalne zachowania konkretnych spółek.

Jeżeli dana spółka cyklicznie wykonuje podobne ruchy — na przykład co 2–3 miesiące — informacja ta stanowi istotny element dalszej analizy i musi zostać przekazana do kolejnych etapów pipeline.

Znajomość indywidualnej charakterystyki instrumentu pozwala odróżnić sytuację nietypową od rutynowego zachowania danej spółki. To rozróżnienie jest kluczowe dla prawidłowej oceny okazji.

### Rola Tavily — wyłącznie świeże informacje

Tavily nie służy do budowania historii spółki.

Jego zadaniem jest wyszukiwanie wyłącznie świeżych informacji mogących wyjaśnić bieżący ruch rynkowy. Domyślny zakres analizy obejmuje maksymalnie ostatnie 24 godziny.

Tavily odpowiada na pytanie: "Czy w ciągu ostatnich 24 godzin pojawiła się informacja wyjaśniająca obecny ruch?" — nie zastępuje historycznej analizy instrumentu, którą wykonują wcześniejsze moduły systemu.

### Rola AI — interpretacja, nie odkrywanie

AI nie rozpoczyna analizy od zera.

Otrzymuje komplet informacji przygotowanych przez wcześniejsze moduły, obejmujących:

- dane rynkowe,
- analizę techniczną,
- analizę historyczną,
- wyniki wcześniejszych silników,
- aktualny kontekst z Tavily.

Zadaniem AI jest interpretacja zgromadzonych informacji, ocena możliwych scenariuszy oraz przygotowanie uzasadnionego raportu dla inwestora.

AI nie podejmuje decyzji inwestycyjnych. Nie wydaje rekomendacji BUY/SELL. Jej rolą jest synteza dostępnych danych w czytelną, użyteczną formę.

### Końcowa decyzja inwestora

Ostateczna decyzja inwestycyjna zawsze należy do użytkownika.

ALCHEMIK dostarcza pełny kontekst analityczny — od wczesnego wykrycia przez Huntera rynku, przez analizę techniczną i historyczną, aż po interpretację AI — ale nie zastępuje decyzji inwestora.

System jest narzędziem wspomagania decyzji. Jego wartością jest szybkość, kompletność i wieloetapowość analizy, a nie automatyczne podejmowanie decyzji za człowieka.

## Cel sztucznej inteligencji w ALCHEMIKU

Podstawowym zadaniem AI nie jest przewidywanie przyszłości ani podejmowanie decyzji inwestycyjnych za użytkownika.

Rolą AI jest przeprowadzenie możliwie najpełniejszej analizy całego dostępnego kontekstu i przedstawienie inwestorowi uzasadnionej oceny potencjalnej okazji inwestycyjnej wraz z:

- argumentami,
- poziomem niepewności,
- ograniczeniami analizy,
- możliwymi scenariuszami dalszego rozwoju sytuacji.

Ostateczna decyzja inwestycyjna zawsze należy do użytkownika.

## Rola AI w systemie ALCHEMIK

### Czym AI nie jest

AI nie jest generatorem sygnałów BUY ani SELL.

AI nie jest wyrocznią podejmującą decyzje inwestycyjne.

AI nie rozpoczyna analizy od zera — nie eksploruje rynku samodzielnie, nie wyszukuje instrumentów i nie zastępuje wcześniejszych etapów pipeline'u.

### Czym AI jest

AI jest końcową warstwą analityczną systemu.

Do AI trafia kompletny kontekst przygotowany przez wcześniejsze moduły systemu. AI otrzymuje dane już przefiltrowane, przeanalizowane i wzbogacone o wyniki wszystkich poprzednich etapów.

AI analizuje wyłącznie zdarzenia, które wcześniejsze etapy uznały za wymagające pogłębionej interpretacji. AI nie analizuje całego rynku.

### Kontekst przekazywany do AI

AI otrzymuje między innymi:

- przebieg obserwacji instrumentu w kolejnych skanach — jak zmieniało się zachowanie instrumentu w czasie,
- dane rynkowe — cena, wolumen, OHLCV,
- analizę techniczną — wskaźniki, formacje świecowe, wybicia, trendy, momentum,
- analizę historyczną — jak instrument zachowywał się wcześniej w podobnych sytuacjach,
- wykrytą powtarzalność zachowania — czy dany wzorzec występował wielokrotnie,
- informacje z Tavily — wyniki wyszukiwania świeżych informacji z ostatnich 24 godzin,
- wyniki wcześniejszych silników — TechnicalEngine, QualityEngine, DecisionEngine, RankingEngine, RiskEngine, HunterEngine,
- ocenę jakości zdarzeń,
- priorytety i klasyfikacje przypisane przez wcześniejsze etapy pipeline'u.

### Zadania AI

Zadaniem AI jest:

1. **Wskazanie najbardziej prawdopodobnego wyjaśnienia** aktualnego zachowania instrumentu — odpowiedź na pytanie: dlaczego instrument zachowuje się w ten sposób właśnie teraz?

2. **Oddzielenie faktów od hipotez** — jednoznaczne rozróżnienie, które informacje są potwierdzonymi faktami, które są interpretacją danych, a które pozostają hipotezami wymagającymi dalszej obserwacji.

3. **Uzasadnienie, dlaczego AI doszło do takich wniosków** — przedstawienie łańcucha rozumowania: jakie dane zostały wzięte pod uwagę, jakie zależności między nimi wykryto i dlaczego prowadzą one do przedstawionych konkluzji.

4. **Wskazanie alternatywnych możliwych scenariuszy** — opisanie, jakie inne wyjaśnienia są możliwe, nawet jeżeli AI uznaje je za mniej prawdopodobne.

5. **Wskazanie ryzyk związanych z każdym scenariuszem** — dla każdego scenariusza (głównego i alternatywnych) wskazanie potencjalnych ryzyk i czynników, które mogłyby zmienić ocenę sytuacji.

6. **Wskazanie, jakie informacje miały największy wpływ na ocenę** — które elementy kontekstu były kluczowe dla sformułowania wniosków, a które miały znaczenie drugorzędne.

### Wyjaśnialność ocen AI

ALCHEMIK nie generuje arbitralnych wartości liczbowych.

Jeżeli AI przedstawia ocenę liczbową (np. prawdopodobieństwo, poziom ryzyka lub ocenę scenariusza), każda wartość liczbowa musi wynikać z:

- rzeczywistego modelu AI,
- rzeczywistych danych wejściowych,
- rzeczywistej analizy wykonanej przez model.

System nie stosuje ręcznie definiowanych progów ani sztucznie przypisanych wartości liczbowych.

Jeżeli model nie potrafi wiarygodnie wyliczyć wartości liczbowej, AI powinno stosować ocenę jakościową, np.:

- bardzo niski poziom ryzyka,
- niski poziom ryzyka,
- umiarkowany poziom ryzyka,
- podwyższony poziom ryzyka,
- wysoki poziom ryzyka,
- bardzo wysoki poziom ryzyka.

Każda ocena jakościowa musi zostać uzasadniona poprzez wskazanie argumentów wynikających z analizy danych.

### Wyjaśnialność decyzji

Każdy wniosek wygenerowany przez AI musi być możliwy do wyjaśnienia.

Raport AI powinien wskazywać:

- jakie dane zostały wykorzystane,
- które argumenty przemawiają za daną oceną,
- które argumenty przemawiają przeciw,
- jakie są ograniczenia analizy,
- jakie informacje zwiększają niepewność,
- których danych brakuje do pełniejszej oceny.

### Forma odpowiedzi AI

AI nie powinno zwracać wyłącznie odpowiedzi typu:

- BUY,
- SELL,
- HOLD.

Każda rekomendacja musi być uzasadniona pełnym kontekstem zebranym wcześniej przez system.

Sama etykieta kierunkowa bez uzasadnienia nie stanowi wartościowej informacji dla inwestora. Inwestor potrzebuje zrozumieć, co stoi za daną oceną, aby podjąć własną świadomą decyzję.

### AI a wyniki Tavily

Jeżeli Tavily nie znalazło żadnych nowych informacji, AI powinno uwzględnić ten fakt w uzasadnieniu. Brak świeżych informacji jest sam w sobie informacją — może oznaczać, że ruch rynkowy wynika z czynników technicznych, a nie z konkretnego wydarzenia.

Jeżeli wykryto nowe informacje — na przykład:

- decyzje regulatora,
- raporty finansowe,
- zmiany ratingów,
- zmiany zarządu,
- nowe produkty,
- inne istotne wydarzenia,

AI powinno wyjaśnić ich możliwy wpływ na zachowanie instrumentu. Powinno wskazać, czy informacja wyjaśnia obserwowany ruch, czy jest z nim sprzeczna, czy też dostarcza dodatkowego kontekstu wykraczającego poza bieżącą sytuację.

### Rozdzielenie faktów od interpretacji

Każdy raport AI musi jednoznacznie rozdzielać:

**Fakty**

Obiektywne dane pochodzące z systemu, między innymi:

- dane Yahoo Finance,
- analiza techniczna,
- wiadomości,
- dane fundamentalne,
- historia instrumentu,
- historia podobnych sytuacji,
- wcześniejsze wyniki obserwacji,
- pozostałe zweryfikowane dane wejściowe.

**Interpretacja AI**

Ocena przygotowana przez model AI, obejmująca:

- ocenę jakości okazji inwestycyjnej,
- poziom ryzyka,
- możliwe scenariusze,
- argumenty za,
- argumenty przeciw,
- elementy niepewności.

Raport musi umożliwiać użytkownikowi odróżnienie faktów od interpretacji modelu.

### Źródła informacji — hierarchia pewności

AI powinno jasno wskazywać:

- **które informacje są faktami** — dane liczbowe, potwierdzone komunikaty, opublikowane raporty, zarejestrowane transakcje,
- **które są interpretacją** — wnioski wyciągnięte z analizy technicznej, ocena sentymentu, porównania historyczne,
- **które pozostają hipotezą wymagającą dalszej obserwacji** — przypuszczenia, przewidywania, scenariusze oparte na niepełnych danych.

Taka hierarchia pozwala inwestorowi ocenić, na ile może polegać na poszczególnych elementach analizy.

### AI jako doradca analityczny

AI wspiera proces podejmowania decyzji inwestycyjnych, ale nie zastępuje decyzji inwestora.

AI ma pomagać użytkownikowi zrozumieć zachowanie instrumentu.

Celem AI nie jest zastąpienie inwestora, lecz dostarczenie mu możliwie pełnego i przejrzystego obrazu sytuacji. AI syntetyzuje informacje, które inwestor musiałby zbierać i analizować samodzielnie — skracając czas potrzebny do podjęcia świadomej decyzji.

Każdy raport powinien umożliwiać użytkownikowi samodzielną ocenę sytuacji poprzez przedstawienie pełnego kontekstu oraz uzasadnienia wszystkich wniosków.

AI przedstawia:
- co się dzieje z instrumentem,
- dlaczego prawdopodobnie się dzieje,
- jakie są alternatywne wyjaśnienia,
- jakie ryzyka wiążą się z każdym scenariuszem,
- na jakich przesłankach oparto wnioski.

AI nie podejmuje decyzji. Nie wydaje poleceń. Nie zastępuje osądu inwestora.

### Ograniczenia wiedzy AI

ALCHEMIK nie przedstawia przypuszczeń, domysłów ani hipotez jako faktów.

Jeżeli dostępne dane są niewystarczające, sprzeczne lub nie pozwalają na przygotowanie wiarygodnej oceny, AI ma obowiązek jednoznacznie to zakomunikować.

Brak możliwości wydania jednoznacznej oceny jest poprawnym wynikiem analizy i nie jest traktowany jako błąd systemu.

W takim przypadku AI powinno wskazać:

- których informacji brakuje,
- które dane są wzajemnie sprzeczne,
- które wnioski mają niski poziom pewności,
- jakie dodatkowe informacje mogłyby zwiększyć wiarygodność analizy,
- które elementy wymagają dalszej obserwacji.

AI nie może ukrywać niepewności ani zastępować brakujących informacji przypuszczeniami.

Użytkownik powinien zawsze wiedzieć:

- co jest potwierdzonym faktem,
- co jest oceną AI,
- czego AI nie jest w stanie obecnie ocenić.

Pokora analityczna jest jedną z podstawowych zasad działania ALCHEMIKA i buduje zaufanie do systemu.

### Granica odpowiedzialności AI

Ostateczna decyzja inwestycyjna zawsze należy do użytkownika.

AI jest narzędziem analitycznym — jednym z ogniw łańcucha przetwarzania informacji w systemie ALCHEMIK. Jego wartością jest zdolność do szybkiej syntezy złożonego, wielowymiarowego kontekstu w czytelną i użyteczną formę.

Inwestor otrzymuje od AI nie gotową odpowiedź, lecz uporządkowany materiał do podjęcia własnej decyzji.
