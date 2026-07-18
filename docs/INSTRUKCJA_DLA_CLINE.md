# Uniwersalność projektu

ALCHEMIK jest uniwersalną platformą analizy instrumentów finansowych.

Przed rozpoczęciem każdej analizy, implementacji, refaktoryzacji lub projektowania należy obowiązkowo przeczytać dokumenty:

docs/FILOZOFIA_ALCHEMIKA.md
docs/ZASADY_PROJEKTU.md

Wszystkie decyzje projektowe muszą być zgodne z filozofią działania projektu oraz zasadami projektu.

W przypadku wykrycia sprzeczności pomiędzy implementacją a filozofią projektu należy najpierw zgłosić rozbieżność, a dopiero później proponować zmiany.

Projekt nie jest tworzony pod konkretne spółki ani konkretne rynki.

Kod ma działać identycznie dla wszystkich instrumentów obsługiwanych przez Yahoo Finance, między innymi:

- akcje GPW,
- akcje USA,
- ETF,
- indeksy,
- kryptowaluty,
- Forex,
- pozostałe instrumenty dostępne w Yahoo Finance.

Nie wolno projektować modułów pod konkretne spółki.

Nie wolno używać w kodzie, przykładach, dokumentacji ani testach domyślnych tickerów takich jak:

- AAPL
- MSFT
- TSLA
- NVDA
- META
- GOOG
- AMZN
- BTC-USD
- ETH-USD
- EURUSD=X

Jeżeli konieczne są przykłady lub testy, używaj wyłącznie sztucznych danych (mocków) lub danych przekazanych przez użytkownika.

Żaden moduł nie może zawierać na stałe wpisanych tickerów.

# Komunikacja pomiędzy silnikami

Silniki projektu ALCHEMIK są od siebie logicznie oddzielone.

Każdy silnik udostępnia wyłącznie publiczny interfejs (Public API).

Żaden silnik nie może korzystać z wewnętrznych modułów innego silnika.

Dozwolona jest wyłącznie komunikacja poprzez publiczny interfejs danego silnika.

Przykłady:

✔ Poprawnie:

from engines.technical import ...

from engines.news import ...

✘ Niepoprawnie:

from engines.technical.indicators ...

from engines.technical.utils ...

from engines.news.cache ...

from engines.news.filter ...

AI Engine, Ranking Engine, Risk Engine, Hunter Engine, Analyst Engine oraz wszystkie przyszłe moduły mają korzystać wyłącznie z publicznych interfejsów innych silników.

Wewnętrzna struktura silnika jest jego prywatną implementacją i nie może być wykorzystywana przez pozostałe moduły projektu.

Takie podejście zapewnia:

- luźne powiązanie modułów,
- łatwiejszą rozbudowę,
- możliwość wymiany implementacji bez wpływu na pozostałe silniki,
- zgodność z zasadami SOLID,
- stabilność architektury projektu.