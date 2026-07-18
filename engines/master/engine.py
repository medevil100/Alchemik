from engines.technical import TechnicalEngine
from engines.news import NewsPipeline
from engines.ai import DecisionEngine
from engines.ranking import RankingEngine
from engines.risk import RiskEngine
from engines.hunter import HunterEngine
from engines.analyst import AnalystEngine
from data.models import FinalAnalysisResult
from datetime import datetime

class MasterEngine:
    def __init__(self, 
                 technical_engine=None, 
                 news_engine=None, 
                 ai_engine=None, 
                 ranking_engine=None, 
                 risk_engine=None, 
                 hunter_engine=None, 
                 analyst_engine=None):
        self.technical_engine = technical_engine or TechnicalEngine()
        self.news_engine = news_engine or NewsPipeline()
        self.ai_engine = ai_engine or DecisionEngine()
        self.ranking_engine = ranking_engine or RankingEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.hunter_engine = hunter_engine or HunterEngine()
        self.analyst_engine = analyst_engine or AnalystEngine()

    def run_analysis(self, symbol):
        # Validate symbol
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Invalid symbol. Symbol must be a non-empty string.")

        # Step 1: Technical Engine
        technical_result = self.technical_engine.analyze([symbol])

        # Step 2: News Engine
        news_result = self.news_engine.process([symbol])

        # Step 3: AI Engine
        ai_result = self.ai_engine.process_data({"symbol": symbol, "technical": technical_result, "news": news_result})

        # Step 4: Ranking Engine
        ranking_result = self.ranking_engine.calculate_ranking([ai_result])

        # Step 5: Risk Engine
        risk_result = self.risk_engine.assess_risk(ai_result, ranking_result)

        # Step 6: Hunter Engine
        hunter_result = self.hunter_engine.scan([{"symbol": symbol, "risk": risk_result, "ranking": ranking_result}])

        # Step 7: Analyst Engine
        analyst_result = self.analyst_engine.generate_analysis(hunter_result)

        # Return Final Analysis Result
        return FinalAnalysisResult(
            symbol=symbol,
            final_rating=analyst_result.final_rating,
            confidence_level=analyst_result.confidence_level,
            recommendation=analyst_result.recommendation,
            positive_factors=analyst_result.positive_factors,
            risk_factors=analyst_result.risk_factors,
            warnings=analyst_result.warnings,
            summary=analyst_result.summary,
            generated_at=datetime.now()
        )
