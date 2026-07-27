"""
from .engine import AIEngine

Public interface for the AI Engine.

This module exposes the unified public API for the AI Engine, ensuring all modules
are accessible from a single entry point while maintaining loose coupling and
compliance with project architecture.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import os

from data.models.ai_signal import AISignal
from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem

# Import all modules for public API
from .analyzer import NewsAnalyzer
from .decision_engine import DecisionEngine
from .pipeline import AIPipeline
from .prompt_builder import PromptBuilder
from data.models.pipeline_decision import PipelineDecision


@dataclass
class AIProviderConfig:
    """
    Configuration for the AI Provider.
    
    Attributes:
        api_key (str): API key for the AI provider
        model_name (str): Name of the AI model to use
        api_endpoint (str): Base URL for the API
    """
    api_key: str
    model_name: str
    api_endpoint: str


class AIProvider:
    """
    Handles communication with an AI model provider.
    
    This class is responsible for:
    - Sending prompts to the AI model
    - Receiving and parsing responses
    - Converting responses into project data models
    
    It does NOT:
    - Analyze technical data
    - Build prompts
    - Make investment decisions
    """

    def __init__(self, config: AIProviderConfig):
        """Initialize with provider configuration."""
        self.config = config

    def send_prompt(self, prompt: str) -> AISignal:
        """
        Send a prompt to the AI model and return the response as an AISignal.
        
        Args:
            prompt (str): The complete prompt to send
            
        Returns:
            AISignal: The parsed response from the AI model
            
        Raises:
            AIProviderError: If the request fails or response is invalid
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                self.config.api_endpoint,
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            
            response_data = response.json()
            return AISignal(
                signal_type=response_data.get("signal_type", "unknown"),
                confidence=response_data.get("confidence", 0.0),
                generated_at=datetime.now(),
                reasoning=response_data.get("reasoning"),
                model_version=self.config.model_name
            )
            
        except requests.exceptions.RequestException as e:
            raise AIProviderError(f"AI request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            raise AIProviderError(f"Invalid AI response: {str(e)}")


class AIProviderError(Exception):
    """Custom exception for AI Provider errors."""
    pass


# Public API functions
def run_ai_analysis(company: CompanyInfo, market_data: List[MarketData], news: List[NewsItem]) -> AISignal:
    """
    Public API function to run the AI analysis pipeline.
    
    Args:
        company: Information about the instrument.
        market_data: Historical market data.
        news: Relevant news items.
    
    Returns:
        AISignal: The final result from the AI Provider.
    
    Raises:
        Exception: If any step fails, includes the stage where the error occurred.
    """
    pipeline = AIPipeline()
