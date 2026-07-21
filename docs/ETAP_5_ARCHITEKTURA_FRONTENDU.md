# ALCHEMIK — ETAP 5: ARCHITEKTURA RESPONSYWNEGO FRONTENDU

## DOKUMENT PROJEKTOWY

Data: 21.07.2026
Wersja: 1.0
Status: Dokument projektowy — architektura frontendu Etapu 5
Bazuje na: docs/API_README.md, docs/Kontrakt_Zdarzen_Rynkowych.md, docs/FILOZOFIA_ALCHEMIKA.md

---

## SPIS TREŚCI

1. [Stan zastany](#1-stan-zastany)
2. [Wymagania i ograniczenia](#2-wymagania-i-ograniczenia)
3. [Rekomendowana technologia](#3-rekomendowana-technologia)
4. [Uzasadnienie decyzji](#4-uzasadnienie-decyzji)
5. [Granice odpowiedzialności](#5-granice-odpowiedzialności)
6. [Przepływ danych](#6-przepływ-danych)
7. [Struktura katalogów](#7-struktura-katalogów)
8. [Projekt warstwy API frontendu](#8-projekt-warstwy-api-frontendu)
9. [Projekt widoków](#9-projekt-widoków)
10. [Zasady responsywności](#10-zasady-responsywności)
11. [Strategia obsługi błędów i stanów aplikacji](#11-strategia-obsługi-błędów-i-stanów-aplikacji)
12. [Strategia testów](#12-strategia-testów)
13. [Sposób lokalnego uruchamiania](#13-sposób-lokalnego-uruchamiania)
14. [Przygotowanie architektury do przyszłego VPS](#14-przygotowanie-architektury-do-przyszłego-vps)
15. [Szczegółowy podział Etapu 5 na małe, zamykane kroki](#15-szczegółowy-podział-etapu-5-na-małe-zamykane-kroki)
16. [Ryzyka i sposoby ich ograniczenia](#16-ryzyka-i-sposoby-ich-ograniczenia)
17. [Kryteria ukończenia całego Etapu 5](#17-kryteria-ukończenia-całego-etapu-5)

---

## 1. STAN ZASTANY

### 1.1 Istniejąca architektura backendu

Projekt ALCHEMIK posiada w pełni działający backend z następującą architekturą:

```
Runtime → SQLite → Read Service → FastAPI → HTTP
```

**Runtime** — cyklicznie uruchamiany proces (Scheduler), który:
- uruchamia MasterEngine,
- wykonuje pełny pipeline analizy (Hunter → Technical → News → AI → Ranking → Risk → Analyst),
- zapisuje wyniki do SQLite (cykle + MarketEvents).

**SQLite** — baza danych z WAL mode, współdzielona między Runtime a API. Zawiera cykle i MarketEvents.

**Read Service** (`RuntimeReadService`) — warstwa tylko do odczytu, która:
- używa `SQLiteHistoryRepository` wewnętrznie,
- zwraca JSON-serializowalne słowniki,
- nie uruchamia silników,
- nie zapisuje do bazy.

**DashboardReadService** — warstwa agregująca dane dashboardowe:
- wykonuje agregacje po stronie SQLite (nie ładuje pełnych tabel),
- zwraca gotową strukturę JSON dla widoku głównego,
- obsługuje pustą bazę danych (zwraca `is_empty: true`).

**FastAPI** (`api_entrypoint.py`) — serwer REST API:
- host: `0.0.0.0`, port: 8000,
- uruchamiany przez `uvicorn`,
- niezależny proces od RuntimeService,
- nie zawiera logiki BUY/SELL,
- nie ujawnia ścieżek systemowych ani stack trace.

### 1.2 Istniejące endpointy API

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| GET | `/health` | Status API i bazy danych |
| GET | `/api/v1/runtime/statistics` | Statystyki Runtime (liczba cykli, eventów, ostatni cykl) |
| GET | `/api/v1/cycles` | Lista cykli (paginated, bez pełnego raportu) |
| GET | `/api/v1/cycles/{cycle_id}` | Pojedynczy cykl z pełnym raportem |
| GET | `/api/v1/dashboard` | Zagregowany widok dashboardu (główny ekran) |
| GET | `/api/v1/market-events` | Lista MarketEvents z filtrami |
| GET | `/api/v1/market-events/{event_id}` | Pojedynczy MarketEvent |
| GET | `/api/v1/tickers/{ticker}/market-events` | Eventy dla konkretnego tickera |

### 1.3 Struktura odpowiedzi dashboardu

Endpoint `/api/v1/dashboard` zwraca:
- `generated_at` — timestamp ISO 8601
- `system` — status API, bazy, journal_mode, schema_version
- `runtime` — cycle_count, event_count, last_cycle, is_empty
- `recent_activity` — events_in_last_cycle, events_last_24h, unique_tickers, last_event_at
- `top_tickers` — lista najaktywniejszych tickerów
- `event_breakdown` — podział według event_family, event_type, priority
- `latest_events` — najnowsze MarketEvents (ograniczone)

### 1.4 Istniejące zależności (requirements.txt)

Projekt zawiera obecnie zależności backendowe (FastAPI, yfinance, openai, tavily-python, itp.) oraz Streamlit, który był pierwotnie używany do prototypowania interfejsu. W requirements.txt znajdują się również biblioteki数据分析 (pandas, numpy, plotly), które mogą być użyteczne w frontendzie, ale nie są wymagane.

### 1.5 Istniejący katalog `dashboard/`

W projekcie istnieje pusty katalog `dashboard/__init__.py`. Katalog ten był prawdopodobnie przeznaczony na przyszły frontend. Obecnie jest pusty.

---

## 2. WYMAGANIA I OGRANICZENIA

### 2.1 Wymagania funkcjonalne

1. Frontend musi wyświetlać dane z istniejącego REST API (tylko do odczytu).
2. Główny widok to dashboard z podsumowaniem aktywności systemu.
3. Frontend musi umożliwiać przeglądanie listy MarketEvents z filtrowaniem.
4. Frontend musi umożliwiać przeglądanie szczegółów pojedynczego MarketEvent.
5. Frontend musi umożliwiać przeglądanie listy cykli Runtime.
6. Frontend musi umożliwiać przeglądanie szczegółów pojedynczego cyklu.
7. Frontend musi prezentować dane dla konkretnego tickera.
8. Frontend musi działać w trybie 24/7 (automatyczne odświeżanie danych).

### 2.2 Wymagania niefunkcjonalne

1. Responsywność: aplikacja musi działać na laptopie, tablecie i telefonie.
2. System docelowo ma działać 24/7 na VPS.
3. Frontend nie może komunikować się bezpośrednio z SQLite.
4. Frontend komunikuje się wyłącznie przez REST API.
5. Runtime nie może być uruchamiany ani sterowany przez frontend.
6. Dashboard pozostaje warstwą tylko do odczytu.
7. Architektura rdzenia pozostaje zamrożona.
8. Prosta wdrożenie na VPS.
9. Łatwość utrzymania.
10. Niski koszt rozwoju.

### 2.3 Ograniczenia

1. Backend nie wspiera WebSocket ani Server-Sent Events.
2. Backend nie wspiera CORS (konieczna będzie konfiguracja po stronie backendu lub proxy).
3. Backend nie wymaga autoryzacji.
4. Wszystkie dane są read-only.
5. Brak wsparcia dla real-time updates (dane są odświeżane przez polling).
6. API zwraca dane w formacie JSON, paginowane.

---

## 3. REKOMENDOWANA TECHNOLOGIA

### 3.1 Rekomendacja: React + Vite + TypeScript + CSS Modules

| Warstwa | Technologia | Wersja (min) |
|---------|-------------|---------------|
| Framework UI | React | 18.x |
| Bundler/dev server | Vite | 5.x |
| Język | TypeScript | 5.x |
| Stylowanie | CSS Modules + CSS Grid/Flexbox | - |
| Klient HTTP | fetch (natywny) | - |
| Testy jednostkowe | Vitest | 1.x |
| Testy komponentów | React Testing Library | 14.x |
| Linter | ESLint | 8.x |
| Formatter | Prettier | 3.x |

### 3.2 Dlaczego właśnie ten stos?

**React + Vite + TypeScript**:
- React jest najbardziej dojrzałym frameworkiem frontendowym z największym ekosystemem.
- Vite zapewnia szybki development server i prosty build produkcyjny (jeden komend: `npm run build` → gotowy katalog `dist/`).
- TypeScript zapewnia type safety, co jest kluczowe przy mapowaniu danych z API (unikamy błędów runtime).
- Zero dodatkowych kosztów licencyjnych.

**CSS Modules zamiast Tailwind CSS**:
- CSS Modules są wbudowane w Vite, nie wymagają dodatkowej konfiguracji.
- Dają izolację styli (scoped CSS) bez narzutu Tailwinda.
- CSS Grid i Flexbox są w pełni wystarczające do responsywnego layoutu.
- Brak zależności od zewnętrznego frameworka CSS.
- Łatwiejsze utrzymanie w długim okresie (czysty CSS zamiast klas utility).

**Brak zewnętrznych bibliotek komponentów** (Material UI, Ant Design, Chakra):
- Unikamy zbędnych zależności.
- Mniejszy bundle produkcyjny.
- Pełna kontrola nad wyglądem i responsywnością.
- Łatwiejsze dostosowanie do wąskich ekranów (telefon).

**Natywny `fetch` zamiast Axios**:
- fetch jest wbudowany w przeglądarki i Node.js.
- Brak dodatkowej zależności.
- Wystarczający dla prostych zapytań GET.

### 3.3 Czego NIE używamy

- **Next.js** — nie potrzebujemy SSR, aplikacja jest jednostronicowa (SPA) dla systemu 24/7.
- **React Router** — nie jest potrzebny dla tak prostego zestawu widoków; stan aplikacji może być zarządzany przez prosty stan komponentu nadrzędnego.
- **Redux / Zustand / Context API** — stan aplikacji jest prosty (listy danych z API), nie potrzeba globalnego store.
- **Socket.IO / WebSocket** — backend nie wspiera, użyjemy prostego pollingu.
- **PWA** — na tym etapie nie jest potrzebne; system działa na VPS, dostęp przez przeglądarkę.
- **Docker** — nie w tym kroku (zgodnie z zakresem zadania).

---

## 4. UZASADNIENIE DECYZJI

### 4.1 Dlaczego SPA, a nie MPA lub SSR?

System ALCHEMIK to dashboard monitorujący — użytkownik otwiera go i trzyma otwartego przez dłuższy czas. SPA jest naturalnym wyborem:
- Raz załadowana aplikacja działa w tle.
- Polling danych odbywa się bez przeładowywania strony.
- Brak potrzeby SEO (system wewnętrzny, niedostępny publicznie).
- Mniejszy koszt hostingu (statyczne pliki + API).

### 4.2 Dlaczego brak frameworka CSS?

Responsywność w ALCHEMIK nie wymaga skomplikowanych układów. Większość widoków to:
- Karty dashboardowe (grid).
- Tabele danych (na desktopie) + lista kart (na telefonie).
- Formularze filtrów.
- Panel nawigacji.

CSS Grid + Flexbox + media queries w pełni pokrywają te potrzeby. CSS Modules zapewniają izolację bez narzutu.

### 4.3 Dlaczego brak routingu?

System ma 4 podstawowe widoki:
1. Dashboard (główny).
2. Lista MarketEvents.
3. Szczegóły MarketEvent.
4. Lista cykli.
5. Szczegóły cyklu.

Przy tak małej liczbie widoków routing poprzez zmianę stanu w komponencie nadrzędnym jest prostszy i tańszy niż React Router. Jeśli w przyszłości liczba widoków wzrośnie, React Router można dodać bez zmiany architektury.

---

## 5. GRANICE ODPOWIEDZIALNOŚCI

### 5.1 Runtime

**Odpowiada za:**
- Ciągłe monitorowanie rynku (24/7).
- Uruchamianie MasterEngine w cyklach.
- Wykrywanie zdarzeń rynkowych.
- Analizę (Technical, News, AI, Ranking, Risk, Analyst).
- Wysyłanie alertów Telegram.
- Zapis danych do SQLite.

**Nie odpowiada za:**
- Serwowanie danych na żądanie.
- Interfejs użytkownika.
- Uruchamianie przez frontend.

### 5.2 SQLite

**Odpowiada za:**
- Trwałe przechowywanie cykli i MarketEvents.
- Współbieżny dostęp (WAL mode) dla Runtime i API.

**Nie odpowiada za:**
- Bezpośrednią komunikację z frontendem.
- Agregacje dla frontendu (to rola DashboardReadService).

### 5.3 Read Service / DashboardReadService

**Odpowiada za:**
- Odczyt danych z SQLite.
- Agregacje danych (w SQLite, nie w Pythonie).
- Zwracanie JSON-serializowalnych struktur.
- Obsługę pustej bazy danych.
- Czyszczenie wewnętrznych pól z odpowiedzi.

**Nie odpowiada za:**
- Modyfikację danych.
- Uruchamianie silników.
- Logikę biznesową (BUY/SELL).

### 5.4 API (FastAPI)

**Odpowiada za:**
- Serwowanie endpointów REST.
- Walidację parametrów zapytań.
- Obsługę błędów (400, 404, 422, 500, 503).
- Paginację.
- Bezpieczeństwo (brak ścieżek systemowych, stack trace).

**Nie odpowiada za:**
- Generowanie danych.
- Uruchamianie Runtime.
- Łączenie się bezpośrednio z innymi warstwami niż Read Service.
- Autoryzację (na tym etapie).

### 5.5 Frontend

**Odpowiada za:**
- Prezentację danych z API.
- Responsywny interfejs (laptop, tablet, telefon).
- Obsługę stanów: ładowanie, pusty wynik, błąd, niedostępność backendu.
- Automatyczne odświeżanie danych (polling).
- Filtrowanie po stronie klienta (opcjonalnie, dla już pobranych danych).

**NIE WOLNO frontendowi:**
- Komunikować się bezpośrednio z SQLite.
- Komunikować się bezpośrednio z Runtime.
- Uruchamiać ani zatrzymywać Runtime.
- Modyfikować danych w API (tylko GET).
- Przechowywać logiki inwestycyjnej (BUY/SELL).
- Zawierać kluczy API (API keys) backendu.

---

## 6. PRZEPŁYW DANYCH

### 6.1 Pełny przepływ: Runtime → SQLite → Read Service → API → Frontend

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (Python)                                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  RUNTIME (24/7)                                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │   │
│  │  │ Scheduler │→ │MasterEng │→ │Pipeline  │→ │AlertDispatcher│   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │   │
│  │         │                                                      │   │
│  │         ▼                                                      │   │
│  │  ┌────────────────────────────────────────────────────────┐    │   │
│  │  │           SQLite (WAL mode)                            │    │   │
│  │  │  • cycles table   • market_events table                │    │   │
│  │  └────────────────────────────────────────────────────────┘    │   │
│  │         ▲                                                     │   │
│  └─────────┼─────────────────────────────────────────────────────┘   │
│            │                                                         │
│  ┌─────────┴─────────────────────────────────────────────────────┐   │
│  │  API (FastAPI, niezależny proces)                             │   │
│  │  ┌────────────────────┐  ┌────────────────────────────┐      │   │
│  │  │ RuntimeReadService │  │ DashboardReadService       │      │   │
│  │  │ • odczyt cykli     │  │ • agregacje w SQLite       │      │   │
│  │  │ • odczyt eventów   │  │ • struktura dashboardu     │      │   │
│  │  └────────┬───────────┘  └───────────┬────────────────┘      │   │
│  │           │                          │                        │   │
│  │           ▼                          ▼                        │   │
│  │  ┌────────────────────────────────────────────────────────┐   │   │
│  │  │           FastAPI Endpoints (REST)                     │   │   │
│  │  │  GET /health                                           │   │   │
│  │  │  GET /api/v1/dashboard                                 │   │   │
│  │  │  GET /api/v1/market-events                             │   │   │
│  │  │  GET /api/v1/market-events/{event_id}                  │   │   │
│  │  │  GET /api/v1/cycles                                    │   │   │
│  │  │  GET /api/v1/cycles/{cycle_id}                         │   │   │
│  │  │  GET /api/v1/runtime/statistics                        │   │   │
│  │  │  GET /api/v1/tickers/{ticker}/market-events            │   │   │
│  │  └───────────────────────┬────────────────────────────────┘   │   │
│  └──────────────────────────┼────────────────────────────────────┘   │
│                             │ HTTP JSON                              │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React SPA)                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  API Client Layer (src/api/)                                    │   │
│  │  • centralna konfiguracja adresu API                            │   │
│  │  • mapowanie endpointów                                         │   │
│  │  • obsługa błędów                                               │   │
│  │  • timeouty                                                     │   │
│  │  • typy danych (TypeScript interfaces)                          │   │
│  └────────────────────────┬────────────────────────────────────────┘   │
│                           │                                            │
│                           ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Views (src/views/)                                            │   │
│  │  ┌──────────────┐ ┌─────────────────┐ ┌────────────────────┐   │   │
│  │  │ DashboardView│ │ MarketEventsView│ │ MarketEventDetail  │   │   │
│  │  └──────┬───────┘ └───────┬─────────┘ └────────┬───────────┘   │   │
│  │  ┌──────────────┐ ┌─────────────────┐                          │   │
│  │  │ CyclesView   │ │ CycleDetail     │                          │   │
│  │  └──────┬───────┘ └───────┬─────────┘                          │   │
│  └─────────┼─────────────────┼────────────────────────────────────┘   │
│            │                 │                                         │
│            ▼                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Components (src/components/)                                   │   │
│  │  • LoadingSpinner, ErrorBanner, EmptyState                      │   │
│  │  • DataCard (karta z danymi)                                    │   │
│  │  • DataTable (tabela danych)                                    │   │
│  │  • FilterBar (pasek filtrów)                                    │   │
│  │  • Navigation (pasek nawigacji)                                 │   │
│  │  • StatusIndicator (status API)                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Stan aplikacji: proste useState w App.tsx                              │
│  - activeView: aktualnie wybrany widok                                  │
│  - selectedEventId: do przejścia do szczegółów                          │
│  - selectedCycleId: do przejścia do szczegółów                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Sposób pobierania danych

1. Frontend uruchamia okresowy polling endpointu `/api/v1/dashboard` (co 30-60 sekund).
2. Przy pierwszym załadowaniu pobiera pełny dashboard.
3. Przy zmianie widoku (np. lista eventów) wykonuje osobne zapytanie.
4. Polling jest wyłączany, gdy użytkownik jest na widoku szczegółowym (oszczędność transferu).
5. Polling jest wznawiany przy powrocie do dashboardu.

### 6.3 Format danych

Wszystkie odpowiedzi API są w formacie JSON. Frontend otrzymuje:
- **Dashboard**: pre-agregowany obiekt z sekcjami (system, runtime, recent_activity, top_tickers, event_breakdown, latest_events).
- **MarketEvents**: lista z paginacją (`items`, `limit`, `offset`, `returned`).
- **Szczegóły eventu**: pojedynczy obiekt MarketEvent.
- **Cykle**: lista z paginacją.
- **Szczegóły cyklu**: pojedynczy obiekt cyklu.

### 6.4 Obsługa stanów

#### Stan ładowania
- Przy każdym zapytaniu API frontend ustawia stan `loading = true`.
- Podczas ładowania wyświetlany jest komponent `LoadingSpinner`.
- Dla list z paginacją: przy zmianie strony spiner zastępuje tylko zawartość listy (nie cały widok).

#### Stan pustych wyników
- API zwraca `is_empty: true` dla pustej bazy danych.
- Dla list: `items: []` z `returned: 0`.
- Frontend wyświetla `EmptyState` z komunikatem: "Brak danych. System oczekuje na pierwszy cykl Runtime."
- Dla pustej listy tickerów: "Brak zdarzeń dla tego instrumentu."

#### Stan błędów API
- Błędy 4xx: wyświetlany jest komunikat o nieprawidłowych parametrach.
- Błędy 5xx: wyświetlany jest `ErrorBanner` z komunikatem "Błąd serwera. Spróbuj ponownie."
- Błąd sieciowy (niedostępność backendu): wyświetlany jest `ErrorBanner` "Backend niedostępny. Sprawdź połączenie."
- Automatyczna ponowna próba po 30 sekundach (polling sam wznawia zapytanie).

#### Stan niedostępności backendu
- `/health` zwraca `503` przy niedostępnej bazie.
- Frontend wykrywa brak odpowiedzi (timeout lub network error).
- Wyświetlany jest trwały banner na górze strony: "Backend niedostępny — dane nie są aktualizowane."
- Polling kontynuuje próby (automatyczne odzyskanie po restarcie backendu).
- Istniejące dane pozostają widoczne (ostatnia pełna odpowiedź).

### 6.5 Odświeżanie danych

- Dashboard: polling co 30 sekund.
- Lista eventów: polling co 60 sekund (tylko jeśli widok jest aktywny).
- Lista cykli: polling co 60 sekund (tylko jeśli widok jest aktywny).
- Szczegóły eventu/cyklu: brak pollingu (dane historyczne).
- Przy powrocie do widoku listy: ręczne odświeżenie (przycisk "Odśwież").
- Automatyczne odświeżenie po błędzie: przy kolejnym cyklu pollingu.

### 6.6 Brak bezpośredniej komunikacji z Runtime i SQLite

Frontend NIGDY nie:
- Łączy się z SQLite (brak dostępu do portu bazy, brak zapytań SQL).
- Łączy się z procesem Runtime.
- Uruchamia procesów backendowych.
- Zapomina o tych zasadach ze względu na prostotę implementacji.

---

## 7. STRUKTURA KATALOGÓW

Poniższa struktura jest projektem docelowym. Zostanie utworzona w Kroku 2 implementacji.

```
dashboard/
├── index.html                    # Wejściowy plik HTML (Vite)
├── package.json                  # Zależności npm
├── tsconfig.json                 # Konfiguracja TypeScript
├── vite.config.ts                # Konfiguracja Vite
├── eslint.config.js              # ESLint flat config
├── .prettierrc                   # Prettier config
│
├── public/
│   └── favicon.ico               # Ikona aplikacji
│
├── src/
│   ├── main.tsx                  # Entry point React
│   ├── App.tsx                   # Główny komponent (stan aplikacji, routing przez stan)
│   ├── App.module.css            # Style głównego komponentu
│   ├── vite-env.d.ts             # Deklaracje typów Vite
│   │
│   ├── api/
│   │   ├── client.ts             # Centralny klient HTTP (fetch wrapper)
│   │   ├── config.ts             # Adres API, timeouty, endpointy
│   │   ├── api.ts                # Funkcje mapujące endpointy
│   │   └── types.ts              # TypeScript interfejsy dla danych API
│   │
│   ├── views/
│   │   ├── DashboardView.tsx     # Widok głównego dashboardu
│   │   ├── DashboardView.module.css
│   │   ├── MarketEventsView.tsx  # Lista MarketEvents z filtrami
│   │   ├── MarketEventsView.module.css
│   │   ├── MarketEventDetail.tsx # Szczegóły pojedynczego eventu
│   │   ├── MarketEventDetail.module.css
│   │   ├── CyclesView.tsx        # Lista cykli Runtime
│   │   ├── CyclesView.module.css
│   │   ├── CycleDetail.tsx       # Szczegóły pojedynczego cyklu
│   │   └── CycleDetail.module.css
│   │
│   ├── components/
│   │   ├── Navigation.tsx        # Pasek nawigacji (widoczny na wszystkich widokach)
│   │   ├── Navigation.module.css
│   │   ├── StatusBar.tsx         # Pasek statusu API (online/offline, last update)
│   │   ├── StatusBar.module.css
│   │   ├── LoadingSpinner.tsx    # Komponent ładowania
│   │   ├── LoadingSpinner.module.css
│   │   ├── ErrorBanner.tsx       # Komponent błędu
│   │   ├── ErrorBanner.module.css
│   │   ├── EmptyState.tsx        # Komponent pustego wyniku
│   │   ├── EmptyState.module.css
│   │   ├── DataTable.tsx         # Tabela danych (responsywna)
│   │   ├── DataTable.module.css
│   │   ├── DataCard.tsx          # Karta z danymi (dla małych ekranów)
│   │   ├── DataCard.module.css
│   │   ├── DashboardCard.tsx     # Pojedyncza karta dashboardu (KPI)
│   │   ├── DashboardCard.module.css
│   │   ├── FilterBar.tsx         # Pasek filtrów dla list
│   │   ├── FilterBar.module.css
│   │   ├── Pagination.tsx        # Paginacja (oparta o limit/offset)
│   │   └── Pagination.module.css
│   │
│   ├── hooks/
│   │   ├── useApi.ts             # Hook do zapytań API (loading, error, data)
│   │   ├── usePolling.ts         # Hook do pollingu (interwał, start, stop)
│   │   └── useDocumentTitle.ts   # Hook do tytułu strony
│   │
│   └── styles/
│       ├── global.css            # Reset CSS, zmienne CSS, font, breakpointy
│       ├── variables.css         # Zmienne CSS (kolory, spacing, breakpointy)
│       └── utilities.css         # Klasy pomocnicze (np. sr-only)
│
└── tests/
    ├── setup.ts                  # Konfiguracja testów (Vitest)
    ├── api/
    │   ├── client.test.ts        # Testy klienta HTTP
    │   ├── api.test.ts           # Testy mapowania endpointów
    │   └── types.test.ts         # Testy typów (runtime type checks)
    ├── components/
    │   ├── LoadingSpinner.test.tsx
    │   ├── ErrorBanner.test.tsx
    │   ├── EmptyState.test.tsx
    │   ├── DataTable.test.tsx
    │   ├── DataCard.test.tsx
    │   ├── DashboardCard.test.tsx
    │   ├── FilterBar.test.tsx
    │   ├── Pagination.test.tsx
    │   ├── Navigation.test.tsx
    │   └── StatusBar.test.tsx
    └── views/
        ├── DashboardView.test.tsx
        ├── MarketEventsView.test.tsx
        ├── MarketEventDetail.test.tsx
        ├── CyclesView.test.tsx
        └── CycleDetail.test.tsx
```

### 7.1 Uzasadnienie struktury

- **api/**: Centralizacja komunikacji z backendem. Wszystkie zapytania HTTP przechodzą przez `client.ts`. Żaden komponent nie wykonuje bezpośrednio `fetch()`.
- **views/**: Każdy widok to kompletny ekran. Nie ma zagnieżdżonych widoków (płaska struktura).
- **components/**: Współdzielone komponenty UI. Każdy komponent ma własny plik CSS Module.
- **hooks/**: Niestandardowe hooki React. `useApi` i `usePolling` są kluczowe dla całej aplikacji.
- **styles/**: Globalne style i zmienne CSS. Brak preprocesora (czysty CSS z CSS Modules).

---

## 8. PROJEKT WARSTWY API FRONTENDU

### 8.1 Centralna konfiguracja adresu API (`src/api/config.ts`)

```typescript
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000',
  TIMEOUT_MS: 10_000,
  POLLING_INTERVAL_MS: 30_000,
  LIST_POLLING_INTERVAL_MS: 60_000,
  DEFAULT_PAGE_LIMIT: 50,
  MAX_PAGE_LIMIT: 200,
};

export const ENDPOINTS = {
  HEALTH: '/health',
  DASHBOARD: '/api/v1/dashboard',
  MARKET_EVENTS: '/api/v1/market-events',
  MARKET_EVENT_BY_ID: (id: string) => `/api/v1/market-events/${id}`,
  CYCLES: '/api/v1/cycles',
  CYCLE_BY_ID: (id: string) => `/api/v1/cycles/${id}`,
  RUNTIME_STATISTICS: '/api/v1/runtime/statistics',
  TICKER_EVENTS: (ticker: string) => `/api/v1/tickers/${ticker}/market-events`,
} as const;
```

Adres API (`BASE_URL`) będzie konfigurowalny przez zmienną środowiskową `VITE_API_URL` w Vite.

### 8.2 Klient HTTP (`src/api/client.ts`)

```typescript
// Abstrakcja nad fetch z timeoutem, parsowaniem błędów, typowaniem.
// - Każde zapytanie ma timeout (AbortController + setTimeout).
// - Błędy sieciowe są rzucane jako ApiNetworkError.
// - Błędy HTTP (4xx, 5xx) są rzucane jako ApiHttpError z kodem i komunikatem.
// - Sukces zwraca sparsowany JSON z typem generycznym T.
```

Klient nie używa zewnętrznych bibliotek. Wystarczy prosty wrapper na `fetch`:
- Timeout: `AbortController` + `setTimeout`.
- Obsługa błędów: rozróżnienie `TypeError` (network error) od odpowiedzi HTTP.
- Automatyczne parsowanie JSON.
- Żadnych interceptors, żadnego cache (dane są zawsze świeże z API).

### 8.3 Mapowanie endpointów (`src/api/api.ts`)

```typescript
// Funkcje, które wywołują klienta dla konkretnych endpointów.
// Każda funkcja:
// - przyjmuje parametry (opcjonalne),
// - buduje URL z parametrami,
// - wywołuje client.get<T>(url),
// - zwraca Promise<T>.
//
// Funkcje:
// - fetchDashboard(params?: DashboardParams): Promise<DashboardResponse>
// - fetchMarketEvents(params?: EventListParams): Promise<PaginatedResponse<MarketEvent>>
// - fetchMarketEventById(id: string): Promise<MarketEvent>
// - fetchCycles(params?: ListParams): Promise<PaginatedResponse<CycleSummary>>
// - fetchCycleById(id: string): Promise<CycleDetail>
// - fetchRuntimeStatistics(): Promise<RuntimeStats>
// - fetchTickerEvents(ticker: string, params?: ListParams): Promise<PaginatedResponse<MarketEvent>>
// - fetchHealth(): Promise<HealthResponse>
```

### 8.4 Walidacja odpowiedzi

- Typy TypeScript są jedyną formą walidacji (compile-time).
- Runtime: zakładamy, że API zwraca dane zgodne z udokumentowanym schematem.
- W testach: mockujemy odpowiedzi API i testujemy zachowanie komponentów dla różnych scenariuszy.
- W razie niezgodności: TypeScript zgłosi błąd przy próbie dostępu do nieistniejącego pola.

### 8.5 Obsługa błędów

- **Network error** (fetch nie otrzymał odpowiedzi): `ApiNetworkError` — użytkownik widzi "Backend niedostępny".
- **Timeout**: `ApiTimeoutError` — użytkownik widzi "Przekroczono czas oczekiwania".
- **HTTP 4xx**: `ApiHttpError` z kodem — użytkownik widzi komunikat o błędzie parametrów.
- **HTTP 5xx**: `ApiHttpError` z kodem 500 — użytkownik widzi "Błąd serwera".
- **HTTP 503**: `ApiHttpError` z kodem 503 — użytkownik widzi "Baza danych niedostępna".

Wszystkie błędy są łapane w hooku `useApi` i przekazywane do komponentu przez stan `error`.

### 8.6 Timeouty

- Każde zapytanie: 10 sekund (config.TIMEOUT_MS).
- Timeout jest realizowany przez `AbortController` po stronie klienta.
- Po timeoutie: komponent wyświetla błąd, a polling kontynuuje przy kolejnej próbie.

### 8.7 Zasady odświeżania danych

- Dashboard: polling co 30 sekund (stały interwał, nie zależny od czasu odpowiedzi).
- Lista eventów/cykli: polling co 60 sekund, tylko gdy widok jest aktywny.
- Polling jest wyłączany:
  - Gdy użytkownik przechodzi do widoku szczegółowego.
  - Gdy backend jest niedostępny (ale próby są kontynuowane w tle).
- Polling jest wznawiany:
  - Przy powrocie do widoku listy/dashboardu.
  - Automatycznie po odzyskaniu dostępności backendu.

### 8.8 Sposób uniknięcia rozproszenia zapytań HTTP

**Centralizacja**: Wszystkie zapytania przechodzą przez:
1. `api/client.ts` — jeden wrapper fetch z timeoutem i obsługą błędów.
2. `api/api.ts` — jedna funkcja na endpoint.
3. `hooks/useApi.ts` — jeden hook do zarządzania stanem (data, loading, error).

Żaden komponent ani widok nie wywołuje bezpośrednio `fetch()` ani `axios.get()`.

---

## 9. PROJEKT WIDOKÓW

### 9.1 DashboardView (widok główny)

**Cel**: Prezentacja podsumowania aktywności systemu ALCHEMIK w czasie rzeczywistym.

**Dane z API**: `GET /api/v1/dashboard` z parametrami domyślnymi.

**Elementy interfejsu**:
1. **Nagłówek**: nazwa systemu "ALCHEMIK", status API (online/offline), timestamp ostatniej aktualizacji.
2. **Sekcja systemowa** (karta): stan bazy, journal_mode, schema_version.
3. **Sekcja runtime** (karta): liczba cykli, liczba eventów, ostatni cykl, flag is_empty.
4. **Sekcja aktywności** (karta): eventy w ostatnim cyklu, eventy w ostatnich 24h, unikalne tickery.
5. **Top tickers** (karty lub tabela): najaktywniejsze tickery z liczbą eventów.
6. **Event breakdown**: podział według rodzin, typów i priorytetów (słupki lub lista).
7. **Latest events** (lista): najnowsze eventy z minimalnymi informacjami.
8. **Przycisk odświeżania**: ręczne odświeżenie danych.

**Zachowanie na telefonie**:
- Karty układają się w jednej kolumnie.
- Top tickers: lista rozwijana (accordion) zamiast tabeli.
- Event breakdown: tylko najważniejsze rodziny (PRICE, VOLUME) widoczne od razu, reszta w rozwijanym panelu.
- Latest events: tylko 3-5 ostatnich, z możliwością rozwinięcia.

**Zachowanie na tablecie**:
- Karty w dwóch kolumnach (2x2 grid).
- Top tickers: tabela z przewijaniem poziomym.
- Event breakdown: widoczne wszystkie rodziny.

**Zachowanie na komputerze**:
- Karty w 4 kolumnach (4x2 grid).
- Top tickers: pełna tabela.
- Event breakdown: pełny widok.
- Latest events: lista do 10 pozycji.

**Stany**:
- Ładowanie: `LoadingSpinner` na środku ekranu.
- Puste: `EmptyState` z komunikatem "System oczekuje na pierwszy cykl Runtime. To może potrwać do 15 minut od uruchomienia."
- Błąd: `ErrorBanner` nad dashboardem, dane z ostatniego udanego odświeżenia pozostają widoczne.

### 9.2 MarketEventsView (lista MarketEvents)

**Cel**: Przeglądanie i filtrowanie wszystkich wykrytych zdarzeń rynkowych.

**Dane z API**: `GET /api/v1/market-events` z opcjonalnymi filtrami (ticker, market, event_family, event_type, priority, date_from, date_to).

**Elementy interfejsu**:
1. **FilterBar**: pola filtrów (ticker, rodzina, typ, priorytet, zakres dat).
2. **DataTable**: tabela z kolumnami: timestamp, ticker, rodzina, typ, priorytet, confidence.
3. **Pagination**: przyciski poprzednia/następna strona, informacja o liczbie wyników.
4. **Przycisk "Szczegóły"**: w każdym wierszu, prowadzi do MarketEventDetail.
5. **Przycisk "Odśwież"**: ręczne odświeżenie listy.

**Zachowanie na telefonie**:
- Zamiast tabeli: lista kart (`DataCard`).
- Filtry: rozwijany panel (accordion) z domyślnie zwinięty.
- Paginacja: "Załaduj więcej" zamiast numerów stron.
- Mniej kolumn: tylko ticker, typ, priorytet.

**Zachowanie na tablecie**:
- Tabela z przewijaniem poziomym (wszystkie kolumny).
- Filtry: widoczne, ale w węższej formie.
- Standardowa paginacja.

**Zachowanie na komputerze**:
- Pełna tabela ze wszystkimi kolumnami.
- Filtry: widoczne w poziomym pasku nad tabelą.
- Standardowa paginacja z numerami stron.

**Stany**:
- Ładowanie: `LoadingSpinner` nad tabelą.
- Puste: `EmptyState` "Brak zdarzeń spełniających kryteria."
- Błąd: `ErrorBanner` "Nie udało się pobrać listy zdarzeń."

### 9.3 MarketEventDetail (szczegóły zdarzenia)

**Cel**: Pełne informacje o pojedynczym zdarzeniu rynkowym.

**Dane z API**: `GET /api/v1/market-events/{event_id}`.

**Elementy interfejsu**:
1. **Nagłówek**: event_id, timestamp, ticker.
2. **Sekcja klasyfikacji**: rodzina, kategoria, typ, podkategoria.
3. **Sekcja priorytetu**: priority_raw, priority_final, confidence_level, quality_level.
4. **Sekcja źródła**: detection_source, event_owner.
5. **Sekcja kontekstu** (jeśli dostępna): price_data, volume_data, technical_context.
6. **Sekcja news/AI** (jeśli dostępna): news_context, ai_context, tavily_context.
7. **Historia zdarzenia**: lista wpisów z timestampem i opisem.
8. **Przycisk "Powrót do listy"**.

**Zachowanie na telefonie**:
- Wszystkie sekcje w jednej kolumnie.
- Sekcje kontekstu: rozwijane (accordion).
- Historia: tylko ostatnie 5 wpisów, reszta "pokaż więcej".

**Zachowanie na tablecie**:
- Klasyfikacja i priorytet obok siebie (2 kolumny).
- Kontekst: rozwijany.
- Historia: przewijana lista.

**Zachowanie na komputerze**:
- Klasyfikacja i priorytet obok siebie.
- Kontekst: widoczny od razu (jeśli dostępny).
- Historia: pełna lista z przewijaniem.

**Stany**:
- Ładowanie: `LoadingSpinner`.
- Nie znaleziono: `EmptyState` "Zdarzenie nie zostało znalezione."
- Błąd: `ErrorBanner`.

### 9.4 CyclesView (lista cykli Runtime)

**Cel**: Przeglądanie historii cykli Runtime.

**Dane z API**: `GET /api/v1/cycles`.

**Elementy interfejsu**:
1. **DataTable**: kolumny: cycle_id, execution_time, candidates, success, errors, status.
2. **Pagination**: standardowa.
3. **Przycisk "Szczegóły"**: w każdym wierszu, prowadzi do CycleDetail.
4. **Status w kolorze**: completed (zielony), error (czerwony), running (niebieski).

**Zachowanie na telefonie**: analogicznie do MarketEventsView — lista kart zamiast tabeli.

**Stany**: analogicznie do MarketEventsView.

### 9.5 CycleDetail (szczegóły cyklu)

**Cel**: Pełny raport z pojedynczego cyklu Runtime.

**Dane z API**: `GET /api/v1/cycles/{cycle_id}`.

**Elementy interfejsu**:
1. **Nagłówek**: cycle_id, timestamp, status.
2. **Sekcja wykonania**: execution_time, candidates_count, success_count, error_count.
3. **Sekcja raportu**: pełny raport JSON (sformatowany).
4. **Lista eventów w tym cyklu**: lista MarketEvents (jeśli dostępna w raporcie).
5. **Przycisk "Powrót do listy"**.

**Stany**: analogicznie do MarketEventDetail.

---

## 10. ZASADY RESPONSYWNOŚCI

### 10.1 Breakpointy

```css
/* Zmienne CSS */
--breakpoint-phone: 480px;
--breakpoint-tablet: 768px;
--breakpoint-desktop: 1024px;
--breakpoint-wide: 1440px;
```

| Zakres | Urządzenie | Layout |
|--------|-----------|--------|
| < 480px | Telefon | 1 kolumna, nawigacja dolna, accordiony, karty zamiast tabel |
| 480px - 768px | Telefon (landscape) / mały tablet | 1-2 kolumny, nawigacja górna, karty |
| 768px - 1024px | Tablet | 2 kolumny, nawigacja boczna (wąska), tabele z przewijaniem |
| 1024px - 1440px | Laptop | 3-4 kolumny, nawigacja boczna, pełne tabele |
| > 1440px | Duży monitor | 4+ kolumn, maksymalna szerokość 1600px dla treści |

### 10.2 Układ nawigacji

- **Telefon (< 768px)**: pasek nawigacji na dole ekranu (fixed bottom). 4-5 ikon z etykietami.
- **Tablet (768-1024px)**: pasek nawigacji u góry (horizontal tabs).
- **Desktop (> 1024px)**: panel boczny (sidebar) z ikonami i etykietami.

### 10.3 Zachowanie tabel

- **Desktop**: pełne tabele ze wszystkimi kolumnami, przewijanie poziome tylko przy bardzo szerokich tabelach.
- **Tablet**: tabele z przewijaniem poziomym. Najważniejsze kolumny są fixed (pierwsze 2-3).
- **Telefon**: tabele są zastępowane listą kart (`DataCard`). Każda karta zawiera najważniejsze pola.

### 10.4 Zachowanie kart i paneli

- Karty dashboardowe: układają się w grid, który automatycznie zmniejsza liczbę kolumn.
- Panele filtrów: na telefonie domyślnie zwinięte (accordion), na desktopie widoczne.
- Panele z danymi kontekstowymi: na telefonie zwinięte, na desktopie widoczne.

### 10.5 Minimalne szerokości

- Aplikacja nie ma minimalnej szerokości — działa na każdym ekranie.
- Na bardzo wąskich ekranach (< 360px):
  - Nawigacja dolna z ikonami bez etykiet.
  - Karty bez paddingów.
  - Czcionka 14px zamiast 16px.

### 10.6 Sposób prezentacji dużej ilości danych na małym ekranie

1. **Priorytetyzacja**: pokazujemy tylko najważniejsze informacje.
2. **Progresywne ujawnianie**: "pokaż więcej" zamiast wszystko naraz.
3. **Filtry**: pozwalają użytkownikowi zawęzić dane do interesującego go zakresu.
4. **Paginacja**: na telefonie "załaduj więcej" zamiast numerowanych stron.
5. **Sortowanie**: po kliknięciu w nagłówek kolumny (na desktopie) lub ikonę sortowania (na telefonie).

---

## 11. STRATEGIA OBSŁUGI BŁĘDÓW I STANÓW APLIKACJI

### 11.1 Hierarchia stanów aplikacji

```
IDLE → LOADING → SUCCESS (dane wyświetlone)
               → EMPTY (pusta baza/puste wyniki)
               → ERROR (błąd API/sieci)
                     → retry (automatyczny lub ręczny) → LOADING
```

### 11.2 Globalne stany

| Stan | Komponent | Zachowanie |
|------|-----------|------------|
| Backend niedostępny | `StatusBar` (globalny) | Czerwony pasek u góry: "Backend niedostępny — dane nie są aktualizowane od HH:MM" |
| Backend dostępny | `StatusBar` (globalny) | Zielony pasek: "System online — ostatnia aktualizacja HH:MM" |
| Pusta baza | `DashboardView` | Specjalny widok: "ALCHEMIK uruchomiony. Oczekiwanie na pierwszy cykl..." z animacją |
| Błąd krytyczny | `ErrorBanner` (globalny) | "Wystąpił błąd krytyczny. Odśwież stronę." z przyciskiem "Odśwież" |

### 11.3 Lokalne stany (per widok)

Każdy widok zarządza własnymi stanami poprzez `useApi`:
- `data: T | null` — ostatnie pomyślnie pobrane dane.
- `loading: boolean` — trwa zapytanie.
- `error: string | null` — komunikat błędu.
- `lastUpdated: Date | null` — timestamp ostatniej udanej aktualizacji.

### 11.4 Obsługa błędów sieciowych

- `useApi` zwraca `error` w postaci stringa.
- `ErrorBanner` wyświetla komunikat.
- Po 30 sekundach polling automatycznie ponawia zapytanie.
- Jeśli zapytanie się powiedzie: `ErrorBanner` znika, dane są aktualizowane.
- Jeśli backend pozostaje niedostępny: użytkownik widzi stare dane + banner błędu.

### 11.5 Obsługa przekroczenia limitu czasu

- Timeout 10 sekund.
- `useApi` zwraca `error: "Przekroczono czas oczekiwania na odpowiedź serwera."`.
- Polling kontynuuje.

### 11.6 Obsługa błędów walidacji (4xx)

- API zwraca `detail` z opisem błędu.
- Frontend wyświetla `ErrorBanner` z `detail`.
- Dla filtrów: błąd walidacji jest wyświetlany przy konkretnym polu.

### 11.7 Obsługa błędów serwera (5xx)

- API zwraca "Internal server error" (bez szczegółów).
- Frontend wyświetla `ErrorBanner` z ogólnym komunikatem.
- Automatyczna ponowna próba przy kolejnym pollingu.

---

## 12. STRATEGIA TESTÓW

### 12.1 Testy warstwy API frontendu

**Zakres**:
- `api/client.test.ts`: testy klienta HTTP (timeout, błędy sieciowe, odpowiedzi HTTP).
- `api/api.test.ts`: testy mapowania endpointów (poprawne URL-e, parametry).
- `api/types.test.ts`: testy typów (kompilacja TypeScript, zgodność z mockami).

**Narzędzia**: Vitest + `vi.fn()` do mockowania fetch.

### 12.2 Testy komponentów

**Zakres**:
- Każdy komponent w `src/components/` (10 komponentów).
- Testy renderowania (komponent się renderuje bez błędów).
- Testy props: dla różnych wartości props komponent renderuje się poprawnie.
- Testy stanów: loading, error, empty, success.
- Testy interakcji: kliknięcie przycisku, zmiana wartości.

**Narzędzia**: Vitest + React Testing Library + `@testing-library/jest-dom`.

### 12.3 Testy widoków

**Zakres**:
- Każdy widok w `src/views/` (5 widoków).
- Testy renderowania: widok renderuje się z mockowanymi danymi.
- Testy stanów: loading → spiner, error → banner, empty → empty state.
- Testy interakcji: filtrowanie, paginacja, nawigacja między widokami.

**Narzędzia**: Vitest + React Testing Library + mockowanie `api/api.ts`.

### 12.4 Testy obsługi błędów

**Zakres**:
- Testy `useApi`: symulacja błędów sieciowych, timeoutów, HTTP 4xx, HTTP 5xx.
- Testy `ErrorBanner`: renderowanie dla różnych komunikatów.
- Testy automatycznego retry: czy polling wznawia zapytanie po błędzie.

### 12.5 Testy responsywności (w zakresie automatyzacji)

**Zakres**:
- Testy CSS Modules: czy klasy są poprawnie aplikowane (testy snapshot).
- Testy media queries: symulacja różnych rozmiarów ekranu (Vitest + `window.resizeTo` lub mock `matchMedia`).
- Testy layoutu: czy komponenty nie wychodzą poza kontener.

**Ograniczenia**:
- Testy wizualne (czy coś wygląda dobrze) pozostają poza zakresem automatyzacji.
- Responsywność będzie weryfikowana manualnie przez zmianę rozmiaru okna.

### 12.6 Test integracji z istniejącym API

**Zakres**:
- Test, który uruchamia API (lokalnie) i wykonuje rzeczywiste zapytania.
- Sprawdza, czy odpowiedzi API są zgodne z TypeScript interfejsami.
- Weryfikuje, czy paginacja działa poprawnie.
- Weryfikuje obsługę pustej bazy.

**Narzędzia**: Vitest + faktyczne API (wymaga uruchomienia `python -m application.api_entrypoint` przed testami).

---

## 13. SPOSÓB LOKALNEGO URUCHAMIANIA

### 13.1 Wymagania lokalne

- Node.js 18+ (zalecane 20 LTS)
- npm 9+ lub yarn 1.22+
- Python 3.12+ (dla backendu API)
- Git

### 13.2 Uruchomienie backendu API

```bash
# Z katalogu głównego projektu (c:\alchemik)
python -m application.api_entrypoint
# API dostępne na http://localhost:8000
```

### 13.3 Uruchomienie frontendu (development)

```bash
# Z katalogu dashboard/
cd dashboard

# Instalacja zależności (jednorazowo)
npm install

# Uruchomienie serwera deweloperskiego
npm run dev
# Frontend dostępny na http://localhost:5173
```

### 13.4 Zmienna środowiskowa VITE_API_URL

Domyślnie: `http://localhost:8000`.

Zmiana:
```bash
# Windows (CMD)
set VITE_API_URL=http://192.168.1.100:8000
npm run dev

# Windows (PowerShell)
$env:VITE_API_URL="http://192.168.1.100:8000"
npm run dev
```

### 13.5 Budowanie wersji produkcyjnej

```bash
npm run build
# Gotowe pliki w katalogu dashboard/dist/
# Można serwować przez dowolny serwer statyczny (nginx, caddy, python http.server)
```

### 13.6 Uruchomienie testów

```bash
# Testy jednostkowe
npm run test

# Testy z pokryciem
npm run test -- --coverage

# Tryb watch (przy开发ie)
npm run test -- --watch
```

---

## 14. PRZYGOTOWANIE ARCHITEKTURY DO PRZYSZŁEGO VPS

### 14.1 Co robimy teraz (Etap 5)

1. Frontend jest SPA — po zbudowaniu to statyczne pliki (HTML, JS, CSS).
2. Backend API uruchamiany jako osobny proces (uvicorn).
3. Brak zależności od Docker, reverse proxy, HTTPS, domeny.

### 14.2 Co przygotowujemy na przyszłość

1. **Sposób serwowania**: `vite build` produkuje katalog `dist/`, który może być serwowany przez nginx.
2. **Konfiguracja API URL**: zmienna `VITE_API_URL` pozwala na łatwą zmianę adresu backendu bez przebudowy.
3. **CORS**: backend będzie wymagał konfiguracji CORS dla produkcji (dodanie `fastapi.middleware.cors` w `api_entrypoint.py`).
4. **Struktura katalogów**: `dashboard/` jest oddzielnym katalogiem, co ułatwia deployment jako osobny serwis.

### 14.3 Czego NIE robimy teraz

- Nie wdrażamy Dockera.
- Nie konfigurujemy reverse proxy (nginx).
- Nie kupujemy domeny.
- Nie konfigurujemy HTTPS.
- Nie automatyzujemy deploymentu.
- Nie ustawiamy monitoringu.

---

## 15. SZCZEGÓŁOWY PODZIAŁ ETAPU 5 NA MAŁE, ZAMYKANE KROKI

### Krok 1: Projekt architektury frontendu (bieżący krok)

**Zakres**:
- Analiza stanu istniejącego API.
- Wybór technologii.
- Zaprojektowanie architektury, widoków, przepływu danych.
- Dokument: `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md`.

**Rezultat**: Zatwierdzony dokument architektoniczny.

**Weryfikacja**: Porównanie z dokumentacją projektu, zgodność z API.

**Kryterium zakończenia**: Dokument zawiera wszystkie wymagane sekcje i jest zgodny ze stanem faktycznym repozytorium.

---

### Krok 2: Inicjalizacja projektu frontendowego i warstwa API

**Zakres**:
- Utworzenie katalogu `dashboard/` ze strukturą.
- Inicjalizacja Vite + React + TypeScript.
- Konfiguracja ESLint, Prettier.
- Implementacja `src/api/client.ts`, `src/api/config.ts`, `src/api/api.ts`, `src/api/types.ts`.
- Implementacja `src/hooks/useApi.ts`, `src/hooks/usePolling.ts`.
- Implementacja `src/styles/global.css`, `src/styles/variables.css`.
- Testy warstwy API.

**Rezultat**: Działająca warstwa komunikacji z backendem. Można wywołać `fetchDashboard()` i zobaczyć w konsoli odpowiedź z API.

**Weryfikacja**:
- `npm run dev` uruchamia się bez błędów.
- Testy warstwy API przechodzą.
- Ręczne sprawdzenie: `console.log(await fetchDashboard())` w przeglądarkowym devtools.

**Kryterium zakończenia**: Wszystkie funkcje API zwracają poprawne dane z lokalnego backendu.

---

### Krok 3: Komponenty wspólne i układ aplikacji

**Zakres**:
- Implementacja `Navigation.tsx` (responsywny pasek nawigacji).
- Implementacja `StatusBar.tsx` (status API online/offline).
- Implementacja `LoadingSpinner.tsx`.
- Implementacja `ErrorBanner.tsx`.
- Implementacja `EmptyState.tsx`.
- Implementacja `DataTable.tsx` (z responsywnością: tabela na desktopie, karty na telefonie).
- Implementacja `DataCard.tsx`.
- Implementacja `DashboardCard.tsx`.
- Implementacja `FilterBar.tsx`.
- Implementacja `Pagination.tsx`.
- Implementacja `App.tsx` z layoutem i stanem widoku.
- Style responsywne dla wszystkich komponentów.
- Testy komponentów.

**Rezultat**: Działający szkielet aplikacji z nawigacją i wszystkimi komponentami UI. Przełączanie między widokami (na razie puste strony z tytułami).

**Weryfikacja**:
- Testy komponentów przechodzą.
- Ręczne sprawdzenie: nawigacja działa, przełączanie widoków, zmiana rozmiaru okna zmienia layout.

**Kryterium zakończenia**: Wszystkie komponenty są zaimplementowane, ostylowane i przetestowane.

---

### Krok 4: DashboardView

**Zakres**:
- Implementacja `DashboardView.tsx`.
- Podział na sekcje (karty) zgodnie z projektem.
- Obsługa stanów: loading, empty, error, success.
- Poling danych co 30 sekund.
- Responsywność: grid z automatyczną liczbą kolumn.
- Testy widoku.

**Rezultat**: Działający widok dashboardu z danymi z API.

**Weryfikacja**:
- Dashboard wyświetla poprawne dane z API.
- Po 30 sekundach dane się odświeżają.
- Pusta baza wyświetla odpowiedni komunikat.
- Błąd API wyświetla banner.
- Testy przechodzą.

**Kryterium zakończenia**: DashboardView w pełni działa z rzeczywistym API.

---

### Krok 5: MarketEventsView

**Zakres**:
- Implementacja `MarketEventsView.tsx`.
- Implementacja `FilterBar` z filtrami (ticker, rodzina, typ, priorytet, data).
- Implementacja `DataTable` dla listy eventów.
- Implementacja paginacji (poprzednia/następna).
- Obsługa stanów: loading, empty, error.
- Responsywność: tabela na desktopie, karty na telefonie.
- Testy widoku.

**Rezultat**: Działający widok listy MarketEvents z filtrowaniem i paginacją.

**Weryfikacja**:
- Lista ładuje się z API.
- Filtry zawężają wyniki.
- Paginacja działa.
- Testy przechodzą.

**Kryterium zakończenia**: MarketEventsView w pełni działa z rzeczywistym API.

---

### Krok 6: MarketEventDetail i TickerEvents

**Zakres**:
- Implementacja `MarketEventDetail.tsx`.
- Sekcje: klasyfikacja, priorytet, źródło, kontekst, historia.
- Obsługa stanów: loading, not found, error.
- Responsywność: accordiony na telefonie.
- Implementacja przejścia z listy do szczegółów (kliknięcie w wiersz).
- Implementacja widoków tickera (kliknięcie w ticker na dashboardzie lub liście → lista eventów dla tego tickera).
- Testy widoku.

**Rezultat**: Działający widok szczegółów zdarzenia.

**Weryfikacja**:
- Kliknięcie w event na liście otwiera szczegóły.
- Dane się zgadzają z API.
- Testy przechodzą.

**Kryterium zakończenia**: MarketEventDetail działa z rzeczywistym API.

---

### Krok 7: CyclesView i CycleDetail

**Zakres**:
- Implementacja `CyclesView.tsx`.
- Implementacja `CycleDetail.tsx`.
- Obsługa stanów.
- Responsywność.
- Testy widoków.

**Rezultat**: Działające widoki cykli.

**Weryfikacja**:
- Lista cykli ładuje się z API.
- Kliknięcie w cykl otwiera szczegóły.
- Testy przechodzą.

**Kryterium zakończenia**: CyclesView i CycleDetail działają z rzeczywistym API.

---

### Krok 8: Testy integracyjne i końcowe

**Zakres**:
- Test integracji frontendu z API (uruchomione lokalnie).
- Testy responsywności (manualne, na różnych rozmiarach okna).
- Testy na prawdziwych danych (jeśli baza zawiera dane).
- Testy na pustej bazie.
- Testy na błędach (zatrzymanie backendu, sprawdzenie zachowania frontendu).
- Optymalizacja wydajności (minifikacja, lazy loading, rozmiar bundle).
- Końcowe czytanie kodu (code review).
- Aktualizacja `struktura_alchemik.txt` (jeśli wymagane, ale na tym etapie nie — to nie jest zmiana architektury rdzenia).

**Rezultat**: W pełni przetestowany, działający frontend.

**Weryfikacja**:
- Wszystkie testy jednostkowe przechodzą.
- Test integracyjny przechodzi.
- Frontend działa na telefonie, tablecie i komputerze.
- Frontend poprawnie obsługuje pustą bazę.
- Frontend poprawnie obsługuje niedostępny backend.

**Kryterium zakończenia**: Wszystkie testy przechodzą, frontend jest gotowy do użytku.

---

## 16. RYZYKA I SPOSOBY ICH OGRANICZENIA

### 16.1 Backend nie obsługuje CORS

**Ryzyko**: Przeglądarka zablokuje zapytania frontendu do API ze względu na CORS (różne porty/originy).

**Ograniczenie**: Podczas developmentu użyjemy Vite proxy (`vite.config.ts`):
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
```

**Docelowo**: Backend API musi dodać middleware CORS:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
```

**Decyzja**: Na potrzeby developmentu proxy Vite jest wystarczające. Backend CORS zostanie dodany przed deploymentem na VPS (Krok 8 lub osobny krok).

### 16.2 Duża liczba MarketEvents

**Ryzyko**: API może zwracać wiele rekordów, co wpływa na czas odpowiedzi i renderowania.

**Ograniczenie**: API ma wbudowaną paginację (limit/offset) i clamping (max 200). Frontend zawsze używa paginacji. Dashboard używa pre-agregowanych danych z SQLite.

### 16.3 Niedostępność API (Runtime wyłączony)

**Ryzyko**: Runtime może być wyłączony (aktualizacja, błąd), co oznacza brak nowych danych.

**Ograniczenie**: Frontend kontynuuje polling i wyświetla ostatnie dostępne dane. Użytkownik widzi banner "Backend niedostępny". Po restarcie Runtime dane automatycznie wracają.

### 16.4 Pusta baza danych

**Ryzyko**: Nowa instalacja, brak danych.

**Ograniczenie**: API zwraca `is_empty: true` z poprawną strukturą. Frontend wyświetla specjalny widok "Oczekiwanie na pierwszy cykl".

### 16.5 Zmiana struktury API

**Ryzyko**: W przyszłości API może się zmienić (dodanie pól, zmiana nazw).

**Ograniczenie**: TypeScript zapewnia compile-time safety. Jeśli API się zmieni, TypeScript zgłosi błędy przy próbie dostępu do nieistniejących pól. Wszystkie typy są w jednym pliku (`api/types.ts`), co ułatwia aktualizację.

### 16.6 Przyrost liczby widoków

**Ryzyko**: W przyszłości może być więcej widoków (np. szczegółowa analiza tickera, wykresy).

**Ograniczenie**: Architektura jest przygotowana na rozszerzenie. Nowe widoki dodajemy jako nowe pliki w `src/views/`. Jeśli liczba widoków przekroczy 10, warto dodać React Router.

---

## 17. KRYTERIA UKOŃCZENIA CAŁEGO ETAPU 5

Etap 5 jest ukończony, gdy:

1. **Dokumentacja**: `docs/ETAP_5_ARCHITEKTURA_FRONTENDU.md` zawiera kompletną architekturę i podział na kroki.

2. **Implementacja**:
   - Frontend jest w pełni działającą aplikacją React SPA.
   - Wszystkie widoki (Dashboard, MarketEvents, MarketEventDetail, Cycles, CycleDetail) są zaimplementowane.
   - Wszystkie stany (loading, empty, error, success) są obsłużone.
   - Responsywność działa na telefonie, tablecie i komputerze.

3. **Testy**:
   - Wszystkie testy jednostkowe przechodzą.
   - Testy komponentów przechodzą.
   - Test integracji z API przechodzi.

4. **Brak naruszeń rdzenia**:
   - Nie zmieniono Runtime.
   - Nie zmieniono istniejących detektorów.
   - Nie zmieniono SQLite.
   - Nie zmieniono Read Service.
   - Nie zmieniono API.
   - Frontend komunikuje się wyłącznie przez API.
   - Frontend nie uruchamia Runtime.
   - Dashboard jest tylko do odczytu.

5. **Repozytorium**:
   - Wszystkie zmiany są w katalogu `dashboard/` (z wyjątkiem dokumentacji w `docs/`).
   - Żaden plik poza `dashboard/` i `docs/` nie został zmodyfikowany.
   - Repozytorium jest gotowe do commita (ale commit nie jest wykonany na tym etapie).

6. **Uruchomienie**:
   - `npm run dev` uruchamia frontend bez błędów.
   - `npm run build` produkuje katalog `dist/`.
   - `npm run test` przechodzi wszystkie testy.
   - Backend API (`python -m application.api_entrypoint`) działa niezależnie.

---

## KONIEC DOKUMENTU

Data utworzenia: 21.07.2026
Wersja: 1.0
Autor: Cline (asystent AI)
Status: Dokument projektowy — architektura frontendu Etapu 5
Bazuje na: stanie faktycznym repozytorium ALCHEMIK (commit 96d194e)