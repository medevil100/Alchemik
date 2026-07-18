# ZASADY PROJEKTU ALCHEMIK

## 1. Fazy projektu

Projekt realizowany jest etapami:

- Projektowanie
- Akceptacja
- Zamrożenie
- Implementacja
- Testy
- Rozwój

Przejście do kolejnego etapu wymaga akceptacji właściciela projektu.

---

## 2. Zatwierdzanie dokumentacji

Po zaakceptowaniu przez właściciela projektu dokument staje się obowiązującą częścią dokumentacji ALCHEMIKA.

Od tego momentu dokument nie jest rozwijany ani przebudowywany podczas implementacji.

Ewentualne zmiany wymagają świadomej decyzji projektowej i są wprowadzane wyłącznie jako nowa rewizja dokumentacji.

---

## 3. Zamrożenie architektury

Po zakończeniu fazy projektowej architektura zostaje zamrożona.

Podczas implementacji nie wolno:

- zmieniać architektury,
- zmieniać odpowiedzialności modułów,
- zmieniać kontraktów danych,
- zmieniać Public API,
- dodawać nowych modułów bez świadomej decyzji projektowej.

---

## 4. Implementacja

Implementacja realizuje wyłącznie zatwierdzoną dokumentację.

Nie projektuje nowych rozwiązań.

Nie przebudowuje istniejącej architektury.

Jeżeli podczas implementacji zostanie zauważony problem projektowy, należy opisać go w raporcie, ale nie wolno samodzielnie zmieniać projektu.

---

## 5. Rewizje dokumentacji

Każda zmiana zatwierdzonej dokumentacji wymaga nowej rewizji.

Historia zmian musi zostać zachowana.

---

## 6. Punkty kontrolne Git

Projekt posiada kontrolowane punkty kontrolne.

Po zakończeniu każdego dużego etapu wykonywany jest commit Git.

Commit oznacza:

- spójny stan projektu,
- kompletną dokumentację dla danego etapu,
- możliwość dalszego rozwoju bez naruszania wcześniejszych decyzji.

Nie wykonuje się commitów dla zmian nieukończonych lub niespójnych.

---

## 7. Pierwszy punkt kontrolny projektu

Obecny stan projektu należy uznać za pierwszy oficjalny punkt kontrolny ALCHEMIKA.

Stan ten obejmuje:

- kompletną architekturę systemu,
- kompletny przepływ danych,
- kompletną dokumentację silników,
- kompletną dokumentację systemu zdarzeń,
- kompletny kontrakt wymiany danych,
- zamrożenie architektury,
- przygotowanie projektu do etapu implementacji.

Od tego momentu repozytorium Git powinno przedstawiać kompletny, spójny i działający projekt na zakończonym etapie projektowym.

Każde przyszłe rozszerzenie projektu powinno rozpoczynać się od tego punktu kontrolnego.