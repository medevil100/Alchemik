"""TradingCalendar — statyczny kalendarz sesji handlowych dla GPW i US."""

from datetime import date, datetime, timedelta, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Święta giełdowe — dane statyczne
# ---------------------------------------------------------------------------

_HOLIDAYS: dict[str, dict[int, set[str]]] = {
    "GPW": {
        2025: {
            "2025-01-01", "2025-01-06",
            "2025-04-20", "2025-04-21",
            "2025-05-01", "2025-05-03",
            "2025-06-19",
            "2025-08-15",
            "2025-11-01", "2025-11-11",
            "2025-12-25", "2025-12-26",
        },
        2026: {
            "2026-01-01", "2026-01-06",
            "2026-04-05", "2026-04-06",
            "2026-05-01", "2026-05-03",
            "2026-05-14",
            "2026-08-15",
            "2026-11-01", "2026-11-11",
            "2026-12-25", "2026-12-26",
        },
        2027: {
            "2027-01-01", "2027-01-06",
            "2027-03-28", "2027-03-29",
            "2027-05-01", "2027-05-03",
            "2027-05-27",
            "2027-08-15",
            "2027-11-01", "2027-11-11",
            "2027-12-25", "2027-12-26",
        },
        2028: {
            "2028-01-01", "2028-01-06",
            "2028-04-16", "2028-04-17",
            "2028-05-01", "2028-05-03",
            "2028-06-15",
            "2028-08-15",
            "2028-11-01", "2028-11-11",
            "2028-12-25", "2028-12-26",
        },
        2029: {
            "2029-01-01", "2029-01-06",
            "2029-04-01", "2029-04-02",
            "2029-05-01", "2029-05-03",
            "2029-05-31",
            "2029-08-15",
            "2029-11-01", "2029-11-11",
            "2029-12-25", "2029-12-26",
        },
        2030: {
            "2030-01-01", "2030-01-06",
            "2030-04-21", "2030-04-22",
            "2030-05-01", "2030-05-03",
            "2030-06-20",
            "2030-08-15",
            "2030-11-01", "2030-11-11",
            "2030-12-25", "2030-12-26",
        },
    },
    "US": {
        2025: {
            "2025-01-01", "2025-01-20", "2025-02-17",
            "2025-04-18", "2025-05-26", "2025-06-19",
            "2025-07-04", "2025-09-01", "2025-11-27",
            "2025-12-25",
        },
        2026: {
            "2026-01-01", "2026-01-19", "2026-02-16",
            "2026-04-03", "2026-05-25", "2026-06-19",
            "2026-07-03", "2026-09-07", "2026-11-26",
            "2026-12-25",
        },
        2027: {
            "2027-01-01", "2027-01-18", "2027-02-15",
            "2027-03-26", "2027-05-31", "2027-06-18",
            "2027-07-05", "2027-09-06", "2027-11-25",
            "2027-12-24",
        },
        2028: {
            "2028-01-01", "2028-01-17", "2028-02-21",
            "2028-04-14", "2028-05-29", "2028-06-19",
            "2028-07-04", "2028-09-04", "2028-11-23",
            "2028-12-25",
        },
        2029: {
            "2029-01-01", "2029-01-15", "2029-02-19",
            "2029-03-30", "2029-05-28", "2029-06-19",
            "2029-07-04", "2029-09-03", "2029-11-22",
            "2029-12-25",
        },
        2030: {
            "2030-01-01", "2030-01-21", "2030-02-18",
            "2030-04-19", "2030-05-27", "2030-06-19",
            "2030-07-04", "2030-09-02", "2030-11-28",
            "2030-12-25",
        },
    },
}


# Mapowanie identyfikatorów rynku na klucze kalendarza
_MARKET_CALENDAR_MAP: dict[str, str] = {
    "GPW": "GPW",
    "NYSE": "US",
    "NASDAQ": "US",
    "US": "US",
}


class CalendarExpiredError(Exception):
    """Data wykracza poza obsługiwany zakres kalendarza."""


def _easter_sunday_gauss(year: int) -> date:
    """Wyznacza datę Wielkanocy algorytmem Gaussa (działa dla lat 1900–2099)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _generate_movable_holidays(year: int, market: str) -> set[str]:
    """Generuje zbiór dat świąt ruchomych dla danego roku i rynku."""
    result: set[str] = set()
    easter = _easter_sunday_gauss(year)
    if market == "GPW":
        result.add(easter.isoformat())                         # Wielkanoc
        result.add((easter + timedelta(days=1)).isoformat())   # Poniedziałek Wielkanocny
        result.add((easter + timedelta(days=60)).isoformat())  # Boże Ciało
    elif market == "US":
        result.add((easter - timedelta(days=2)).isoformat())   # Good Friday
    return result


class TradingCalendar:
    """Kalendarz sesji handlowych dla obsługiwanych rynków."""

    SUPPORTED_MARKETS: tuple[str, ...] = ("GPW", "US")

    def __init__(self, holidays_override: Optional[dict[str, set[str]]] = None):
        self._holidays: dict[str, set[date]] = {}
        for market_key in ("GPW", "US"):
            holiday_dates: set[date] = set()
            for year in range(2025, 2031):
                for date_str in _HOLIDAYS.get(market_key, {}).get(year, set()):
                    holiday_dates.add(date.fromisoformat(date_str))
                for date_str in _generate_movable_holidays(year, market_key):
                    holiday_dates.add(date.fromisoformat(date_str))
            self._holidays[market_key] = holiday_dates
        if holidays_override:
            for market_key, dates_str in holidays_override.items():
                override_dates = {date.fromisoformat(d) for d in dates_str}
                if market_key in self._holidays:
                    self._holidays[market_key] |= override_dates
                else:
                    self._holidays[market_key] = override_dates

    def _get_calendar_key(self, market: str) -> str:
        calendar_key = _MARKET_CALENDAR_MAP.get(market)
        if calendar_key is None:
            raise ValueError(f"Unsupported market: {market}")
        return calendar_key

    def is_trading_day(self, d: date, market: str) -> bool:
        """True jeśli Pon-Pt i data nie jest świętem. ValueError dla nieobsługiwanego rynku."""
        calendar_key = self._get_calendar_key(market)
        if d.weekday() >= 5:  # sobota lub niedziela
            return False
        return d not in self._holidays.get(calendar_key, set())

    def resolve_session_date(
        self,
        detection_timestamp: datetime,
        horizon_offset: int,
        market: str,
    ) -> datetime:
        """Wyznacza datę horyzontu po N sesjach handlowych."""
        calendar_key = self._get_calendar_key(market)
        current_date = detection_timestamp.date()
        sessions_found = 0
        max_date = date(2030, 12, 31)
        while sessions_found < horizon_offset:
            current_date += timedelta(days=1)
            if current_date > max_date:
                raise CalendarExpiredError(
                    f"Calendar expired: date {current_date} exceeds 2030-12-31"
                )
            if current_date.weekday() < 5 and current_date not in self._holidays.get(
                calendar_key, set()
            ):
                sessions_found += 1
        return datetime(
            current_date.year, current_date.month, current_date.day,
            tzinfo=timezone.utc,
        )