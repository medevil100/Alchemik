"""
Prompt Builder for AI Engine.

This module is responsible for constructing high-quality prompts for AI models based on
structured data received from Decision Engine.

Rules:
1. Only communicates through Public API
2. Uses only project data models
3. Follows Clean Code, SOLID, and Single Responsibility Principle
4. No hardcoded tickers or AI provider-specific logic
"""
from typing import Dict, Any
from data.models.ai_signal import AISignal  # Assuming this is the input model


class PromptBuilder:
    """
    Builds AI prompts from structured Decision Engine data.
    
    Responsibilities:
    - Receive structured data from Decision Engine
    - Construct high-quality prompts
    - Return prompts to AI Provider
    
    Does NOT:
    - Communicate with AI models
    - Perform technical analysis
    - Make investment decisions
    """

    def __init__(self):
        """Initialize prompt templates and validation rules."""
        self._validate_input_schema()

    def build_prompt(self, decision_data: AISignal) -> str:
        """
        Construct a prompt from Decision Engine data.
        
        Args:
            decision_data: Structured data from Decision Engine
            
        Returns:
            str: Complete prompt ready for AI model
            
        Raises:
            ValueError: If input data is invalid
        """
        self._validate_input(decision_data)
        return self._construct_prompt(decision_data)

    def _validate_input(self, data: AISignal) -> None:
        """Validate input data structure and content."""
        if not data:
            raise ValueError("Empty decision data received")
        # Add more validation as needed

    def _construct_prompt(self, data: AISignal) -> str:
        """Construct the actual prompt from validated data."""
        # Dynamic prompt construction based on input data
        # No hardcoded tickers or provider-specific logic
        prompt_parts = [
            f"Analysis request for financial instrument",
            f"Signal generated at: {data.generated_at}",
            f"Signal type: {data.signal_type}",
            f"Confidence: {data.confidence}",
            f"Reasoning: {data.reasoning}",
            "Provide comprehensive analysis considering the above factors"
        ]
        return '\n'.join(prompt_parts)

    def _validate_input_schema(self) -> None:
        """Validate that required data models are available."""
        try:
            from data.models.ai_signal import AISignal  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Required data model AISignal not found") from e


# Public API function
def create_prompt(decision_data: Dict[str, Any]) -> str:
    """
    Public API for prompt creation.
    
    Args:
        decision_data: Dictionary containing structured decision data
        
    Returns:
        str: Constructed prompt
    """
    try:
        # Convert dict to AISignal model (assuming proper validation)
        signal = AISignal(**decision_data)
        builder = PromptBuilder()
        return builder.build_prompt(signal)
    except Exception as e:
        raise ValueError(f"Prompt creation failed: {str(e)}")