"""Testy jednostkowe TradingCalendar."""

import pytest
from datetime import date, datetime, timezone, timedelta

from engines.outcome.calendar import (
    TradingCalendar,
    CalendarExpiredError,
    _easter_sunday_gauss,
)


class TestEasterSundayGauss:
    """Testy algorytmu Gaussa dla Wielkanocy."""

    def test_easter_2025(self):
        assert _easter_sunday_gauss(2025) == date(2025, 4, 20)

    def test_easter_2026(self):
        assert _easter_sunday_gauss(2026) == date(2026, 4, 5)

    def test_easter_2027(self):
        assert _easter_sunday_gauss(2027) == date(2027, 3, 28)

    def test_easter_2028(self):
        assert _easter_sunday_gauss(2028) == date(2028, 4, 16)

    def test_easter_2029(self):
        assert _easter_sunday_gauss(2029) == date(2029, 4, 1)

    def test_easter_2030(self):
        assert _easter_sunday_gauss(2030) == date(2030, 4, 21)


class TestIsTradingDay:
    """Testy metody is_trading_day()."""

    @pytest.fixture
    def calendar(self):
        return TradingCalendar()

    # --- GPW ---

    def test_gpw_normal_trading_day(self, calendar):
        """Zwykły poniedziałek GPW jest dniem handlowym."""
        assert calendar.is_trading_day(date(2026, 8, 3), "GPW") is True

    def test_gpw_weekend_saturday(self, calendar):
        """Sobota nie jest dniem handlowym GPW."""
        assert calendar.is_trading_day(date(2026, 8, 1), "GPW") is False

    def test_gpw_weekend_sunday(self, calendar):
        """Niedziela nie jest dniem handlowym GPW."""
        assert calendar.is_trading_day(date(2026, 8, 2), "GPW") is False

    def test_gpw_christmas(self, calendar):
        """Boże Narodzenie GPW nie jest dniem handlowym."""
        assert calendar.is_trading_day(date(2026, 12, 25), "GPW") is False

    def test_gpw_new_year(self, calendar):
        """Nowy Rok GPW nie jest handlowy."""
        assert calendar.is_trading_day(date(2026, 1, 1), "GPW") is False

    def test_gpw_easter_sunday(self, calendar):
        """Wielkanoc GPW nie jest handlowa."""
        assert calendar.is_trading_day(date(2026, 4, 5), "GPW") is False

    def test_gpw_easter_monday(self, calendar):
        """Poniedziałek Wielkanocny GPW nie jest handlowy."""
        assert calendar.is_trading_day(date(2026, 4, 6), "GPW") is False

    def test_gpw_corpus_christi(self, calendar):
        """Boże Ciało GPW nie jest handlowe."""
        assert calendar.is_trading_day(date(2026, 6, 4), "GPW") is False  # 2026-05-14? Wait, Easter 2026-04-05 + 60 = 2026-06-04
        # Recalculate: Wielkanoc 2026-04-05, +60 = 2026-06-04
        assert calendar.is_trading_day(date(2026, 6, 4), "GPW") is False

    def test_gpw_christmas_eve_handlowy(self, calendar):
        """Wigilia GPW jest dniem handlowym (sesja skrócona)."""
        assert calendar.is_trading_day(date(2026, 12, 24), "GPW") is True

    def test_gpw_new_years_eve_handlowy(self, calendar):
        """Sylwester GPW jest dniem handlowym (gdy w dzień roboczy)."""
        assert calendar.is_trading_day(date(2026, 12, 31), "GPW") is True

    def test_gpw_may_first(self, calendar):
        """1 maja GPW nie jest handlowy."""
        assert calendar.is_trading_day(date(2026, 5, 1), "GPW") is False

    def test_gpw_may_third(self, calendar):
        """3 maja GPW nie jest handlowy."""
        assert calendar.is_trading_day(date(2026, 5, 3), "GPW") is False

    # --- US ---

    def test_us_normal_trading_day(self, calendar):
        assert calendar.is_trading_day(date(2026, 8, 3), "US") is True

    def test_us_weekend(self, calendar):
        assert calendar.is_trading_day(date(2026, 8, 1), "US") is False

    def test_us_christmas(self, calendar):
        assert calendar.is_trading_day(date(2026, 12, 25), "US") is False

    def test_us_new_year(self, calendar):
        assert calendar.is_trading_day(date(2026, 1, 1), "US") is False

    def test_us_good_friday(self, calendar):
        """Good Friday US nie jest handlowy."""
        # Wielkanoc 2026-04-05, Good Friday = 2026-04-03
        assert calendar.is_trading_day(date(2026, 4, 3), "US") is False

    def test_us_thanksgiving(self, calendar):
        """Thanksgiving US nie jest handlowy."""
        assert calendar.is_trading_day(date(2026, 11, 26), "US") is False

    def test_us_black_friday_handlowy(self, calendar):
        """Black Friday US jest dniem handlowym (sesja skrócona)."""
        assert calendar.is_trading_day(date(2026, 11, 27), "US") is True

    def test_us_independence_day(self, calendar):
        """4 lipca — Independence Day observed w 2026 (sobota → piątek)."""
        # 2026-07-04 is Saturday → observed Friday 2026-07-03
        assert calendar.is_trading_day(date(2026, 7, 4), "US") is False  # sobota
        assert calendar.is_trading_day(date(2026, 7, 3), "US") is False  # observed

    # --- NYSE / NASDAQ ---

    def test_nyse_alias(self, calendar):
        """NYSE używa kalendarza US."""
        assert calendar.is_trading_day(date(2026, 12, 25), "NYSE") is False
        assert calendar.is_trading_day(date(2026, 8, 3), "NYSE") is True

    def test_nasdaq_alias(self, calendar):
        """NASDAQ używa kalendarza US."""
        assert calendar.is_trading_day(date(2026, 12, 25), "NASDAQ") is False
        assert calendar.is_trading_day(date(2026, 8, 3), "NASDAQ") is True

    # --- Błędy ---

    def test_unsupported_market_raises(self, calendar):
        """Nieobsługiwany rynek rzuca ValueError."""
        with pytest.raises(ValueError, match="Unsupported market"):
            calendar.is_trading_day(date(2026, 8, 3), "LSE")


class TestResolveSessionDate:
    """Testy metody resolve_session_date()."""

    @pytest.fixture
    def calendar(self):
        return TradingCalendar()

    def test_simple_next_session(self, calendar):
        """Horyzont +1 dla poniedziałku to wtorek."""
        dt = datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc)  # poniedziałek
        result = calendar.resolve_session_date(dt, 1, "GPW")
        assert result.date() == date(2026, 8, 4)  # wtorek

    def test_skip_weekend_gpw(self, calendar):
        """Horyzont +1 z piątku GPW to poniedziałek."""
        dt = datetime(2026, 7, 31, 14, 30, tzinfo=timezone.utc)  # piątek
        result = calendar.resolve_session_date(dt, 1, "GPW")
        assert result.date() == date(2026, 8, 3)  # poniedziałek

    def test_horizon_plus_3(self, calendar):
        """Horyzont +3 z piątku GPW."""
        dt = datetime(2026, 7, 31, 14, 30, tzinfo=timezone.utc)  # piątek
        result = calendar.resolve_session_date(dt, 3, "GPW")
        # +1 = pon 8/3, +2 = wt 8/4, +3 = śr 8/5
        assert result.date() == date(2026, 8, 5)

    def test_horizon_plus_5(self, calendar):
        """Horyzont +5 z piątku GPW."""
        dt = datetime(2026, 7, 31, 14, 30, tzinfo=timezone.utc)
        result = calendar.resolve_session_date(dt, 5, "GPW")
        # +1 = pon 8/3, +2 = wt 8/4, +3 = śr 8/5, +4 = czw 8/6, +5 = pt 8/7
        assert result.date() == date(2026, 8, 7)

    def test_skip_holiday_gpw(self, calendar):
        """Horyzont +1 gdy następny dzień to święto."""
        # 2026-05-01 is Friday (Święto Pracy)
        dt = datetime(2026, 4, 30, 14, 30, tzinfo=timezone.utc)  # czwartek
        # piątek 5/1 = święto, sobota/niedziela = weekend
        # → poniedziałek 5/4
        result = calendar.resolve_session_date(dt, 1, "GPW")
        # 2026-05-03 is Sunday (Święto Konstytucji) — ale niedziela i tak niehandlowa
        # 2026-05-04 is Monday
        assert result.date() == date(2026, 5, 4)

    def test_calendar_expired_raises(self, calendar):
        """Data poza 2030 rzuca CalendarExpiredError."""
        dt = datetime(2030, 12, 31, 14, 30, tzinfo=timezone.utc)
        with pytest.raises(CalendarExpiredError):
            calendar.resolve_session_date(dt, 5, "GPW")

    def test_unsupported_market_raises_valueerror(self, calendar):
        dt = datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Unsupported market"):
            calendar.resolve_session_date(dt, 1, "LSE")

    def test_result_is_timezone_aware_utc(self, calendar):
        dt = datetime(2026, 8, 3, 14, 30, tzinfo=timezone.utc)
        result = calendar.resolve_session_date(dt, 1, "GPW")
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_deterministic(self, calendar):
        """Ten sam input → ten sam output."""
        dt = datetime(2026, 8, 1, tzinfo=timezone.utc)
        r1 = calendar.resolve_session_date(dt, 2, "GPW")
        r2 = calendar.resolve_session_date(dt, 2, "GPW")
        assert r1 == r2