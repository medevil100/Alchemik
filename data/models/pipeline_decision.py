"""
PipelineDecision — model decyzji pipeline'u dla DecisionEngine.

Prosty kontener danych określający, które etapy pipeline'u mają zostać
uruchomione dla danego MarketEvent na podstawie jego quality_level.

Zgodny z ETAPEM 7.4, sekcja 7.4 docs/ETAP_7_PLAN.md.
"""

from dataclasses import dataclass


@dataclass
class PipelineDecision:
    """
    Decyzja o uruchomieniu kolejnych etapów pipeline'u.

    Attributes:
        run_news: Czy uruchomić NewsPipeline.
        run_tavily: Czy uruchomić wyszukiwanie Tavily.
        run_ai: Czy uruchomić analizę AI.
        reason: Opis słowny uzasadniający podjętą decyzję.
    """

    run_news: bool = False
    run_tavily: bool = False
    run_ai: bool = False
    reason: str = ""