from typing import Optional

class IndicatorsConfig:
    """
    Configuration class for technical indicators.
    
    Attributes:
        relative_volume_period (Optional[int]): Period for Relative Volume calculation.
            Must be provided in the project configuration.
    """
    relative_volume_period: Optional[int] = 14
