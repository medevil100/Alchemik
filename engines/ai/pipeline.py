from typing import Dict, Any, Optional, List
import os
from data.models.ai_signal import AISignal
from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem
from engines.ai.analyzer import NewsAnalyzer
from engines.ai.decision_engine import DecisionEngine
from engines.ai.prompt_builder import PromptBuilder
from .ai_provider import AIProvider
from .ai_provider import AIProviderConfig
from engines.technical.engine import TechnicalEngine
from engines.news.pipeline import NewsPipeline


class AIPipeline:
    """
    Coordinates the flow of data between AI Engine modules.
    
    Responsibilities:
    - Orchestrates the sequence: Technical Analyzer → News Analyzer → Decision Engine → Prompt Builder → AI Provider.
    - Handles exceptions and provides clear error messages.
    - Returns results as AISignal.
    """

    def __init__(self):
        self.news_analyzer = NewsAnalyzer()
        self.decision_engine = DecisionEngine()
        self.prompt_builder = PromptBuilder()
        self.technical_engine = TechnicalEngine()
        self.news_pipeline = NewsPipeline(filter_config=None)
        
        # Load configuration from secrets
        config = AIProviderConfig(
            api_key=os.getenv("API_KEY"),
            model_name=os.getenv("MODEL_NAME"),
            api_endpoint=os.getenv("API_ENDPOINT")
        )
        self.ai_provider = AIProvider(config)

    def run_pipeline(self, company: CompanyInfo, market_data: List[MarketData], news: List[NewsItem]) -> AISignal:
        """
        Executes the AI Pipeline workflow.
        
        Args:
            company: Information about the instrument.
            market_data: Historical market data.
            news: Relevant news items.
        
        Returns:
            AISignal: The final result from the AI Provider.
        
        Raises:
            Exception: If any step fails, includes the stage where the error occurred.
        """
        try:
            # Step 1: Analyze technical data
            technical_result = self.technical_engine.analyze(market_data)
            
            # Step 2: Analyze news data
            news_result = self.news_pipeline.process(news)
            
            # Step 3: Process combined data in Decision Engine
            decision_data = self.decision_engine.process_data({
                "technical_analysis": technical_result,
                "news_analysis": news_result
            })
            
            # Step 4: Build prompt
            prompt = self.prompt_builder.build_prompt(decision_data)
            
            # Step 5: Send prompt to AI Provider
            ai_signal = self.ai_provider.send_prompt(prompt)
            
            return ai_signal
            
        except Exception as e:
            error_msg = f"Pipeline failed at stage: {e.__class__.__name__}"
            raise Exception(error_msg) from e
