"""OutcomeComputer — komponent obliczeniowy dla rezultatów zdarzeń rynkowych."""

from .engine import OutcomeComputer
from .calendar import TradingCalendar

__all__ = ["OutcomeComputer", "TradingCalendar"]