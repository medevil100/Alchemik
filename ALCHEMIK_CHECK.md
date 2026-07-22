# ALCHEMIK — CHECK POINT

## Status projektu

| Atrybut | Wartość |
|---------|---------|
| Status projektu | **AKTYWNY** |
| Aktualny etap | **ETAP 5** (ukończony, zamrożony) |
| Ukończone etapy | ETAP 1, ETAP 2, ETAP 3, ETAP 4, ETAP 5 |
| Zamrożone etapy | ETAP 1, ETAP 2, ETAP 3, ETAP 4, ETAP 5 |
| Ostatni commit | `2311de6` (HEAD -> master) |
| Branch | `master` |
| Data ostatniego commita | 22.07.2026 |
| Liczba testów backendu | **28** plików testowych w `tests/` |
| Liczba testów frontendu | **10** plików testowych w `dashboard/src/` (w podkatalogach `api/__tests__/`, `components/__tests__/`, `hooks/__tests__/`, `views/__tests__/`, `__tests__/`) |

## Status modułów

| Moduł | Status | Uwagi |
|-------|--------|-------|
| **Backend (Python)** | ✅ Zamrożony | Kompletna architektura 7 silników + warstwa aplikacyjna |
| **Frontend (React)** | ✅ Zamrożony | SPA w `dashboard/`, zaimplementowane widoki DashboardView, MarketEventsView, HealthView, komponenty UI |
| **API (FastAPI)** | ✅ Zamrożony | REST API na porcie 8000, endpointy: /health, /api/v1/dashboard, /api/v1/market-events, /api/v1/cycles, /api/v1/tickers |
| **Runtime** | ✅ Zamrożony | Cykliczne uruchamianie pipeline'u MasterEngine przez Scheduler |
| **Scheduler** | ✅ Zamrożony | Interval-based scheduling cykli analizy |
| **SQLite** | ✅ Zamrożony | Baza danych z WAL mode, współdzielona między Runtime a API |
| **Dashboard** | ✅ Zamrożony | DashboardReadService z agregacjami po stronie SQLite |
| **AI Engine** | ✅ Zamrożony | DecisionEngine, Pipeline, Analyzer, AIProvider, PromptBuilder |
| **Technical Engine** | ✅ Zamrożony | Wskaźniki: SMA, EMA, RSI, MACD, ATR, BB, OBV, VWAP, RVOL, Fibonacci + detekcja formacji świecowych |
| **News Engine** | ✅ Zamrożony | Pipeline, cleaner, filter, cache |
| **Ranking Engine** | ✅ Zamrożony | Ocena i rankingowanie danych |
| **Risk Engine** | ✅ Zamrożony | Ocena ryzyka: risk_score, risk_level, stop_loss, take_profit |
| **Hunter Engine** | ✅ Zamrożony | Gromadzenie danych z Yahoo Finance |
| **Analyst Engine** | ✅ Zamrożony | Generowanie końcowej analizy |
| **Master Engine** | ✅ Zamrożony | Orkiestracja pipeline'u analizy |
| **Price Detector** | ✅ Zamrożony | Wykrywanie zdarzeń cenowych (w ramach TechnicalEngine) |
| **Volume Detector** | ✅ Zamrożony | Wykrywanie zdarzeń wolumenowych (w ramach TechnicalEngine) |
| **Universe** | ✅ Zamrożony | Lista dozwolonych instrumentów |
| **Market Scanner** | ✅ Zamrożony | Skanowanie rynku w poszukiwaniu kandydatów |
| **Opportunity Deduplicator** | ✅ Zamrożony | Deduplikacja zdarzeń |
| **Alert Builder** | ✅ Zamrożony | Decyzja o wysłaniu alertu |
| **Alert Dispatcher** | ✅ Zamrożony | Wysyłka alertów przez kanały |
| **Telegram Channel** | ✅ Zamrożony | Integracja z Telegram API |

## Zamrożone moduły (architektura rdzenia)

Wszystkie moduły powyżej są zamrożone zgodnie z zasadą zamrożenia architektury projektu.

## Lista zamrożonych modułów

- `application/` — cała warstwa aplikacyjna
- `config/` — wszystkie konfiguracje
- `data/` — modele danych, źródła danych
- `engines/` — wszystkie silniki (ai, analyst, hunter, master, news, price_detector, ranking, risk, technical, volume_detector)
- `tests/` — wszystkie testy (28 plików)
- `scripts/` — skrypty diagnostyczne
- `dashboard/` — cały frontend React

## Następny planowany etap

**ETAP 6** — szczegóły w `docs/ETAP_6_ARCHITEKTURA.md`

## Procedura kontroli regresji liczby testów

Przed uruchomieniem pełnego zestawu testów w każdym zadaniu należy wykonać:

```text
python -m pytest --collect-only -q
```

Liczbę zebranych testów należy porównać z wartością bazową z ostatniego zatwierdzonego kroku.

**Wartość bazowa po Kroku 1B**: `561 tests collected`, `561 passed`.

### Procedura

1. Odczytaj bazową liczbę testów z ostatniego zatwierdzonego raportu.
2. Uruchom `python -m pytest --collect-only -q`.
3. Porównaj liczbę zebranych testów.
4. **Jeżeli liczba spadła bez zgody właściciela** — natychmiast przerwij zadanie i zgłoś regresję kolekcji testów.
5. Jeżeli liczba jest równa lub większa — uruchom `python -m pytest`.
6. Zapisz obie liczby w raporcie końcowym.
7. Nowy zatwierdzony raport staje się bazą dla następnego kroku.

### Reguły

- **Wzrost** liczby testów (np. `561 → 570`) jest dozwolony, jeżeli nowe testy wynikają z bieżącego zadania.
- **Spadek** liczby testów (np. `561 → 550`) jest blokerem, chyba że właściciel projektu wydał wcześniej jednoznaczną zgodę na usunięcie testów, zastąpienie testów, zmianę kolekcji testów lub usunięcie funkcjonalności wraz z testami.
- Nie wystarczy wynik `python -m pytest` — kontrola musi opierać się najpierw na `python -m pytest --collect-only -q`.
- Nie używaj `python -m pytest tests/`.

## Daty

| Zdarzenie | Data |
|-----------|------|
| Ostatnia aktualizacja dokumentacji | 22.07.2026 |
| Zamrożenie ETAPU 5 | 22.07.2026 |