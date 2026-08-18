# Models for the application layer
from typing import List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field


class CycleKind:
    """Jawne wyniki cyklu Runtime (Krok 4/8).

    Addytywny, minimalny kontrakt wyniku cyklu:
      * BASELINE_INITIALIZED — pierwszy cykl utworzył matrycę/baseline bez sygnałów;
      * SUBSEQUENT_CYCLE      — cykl porównawczy z istniejącą matrycą;
      * SOURCE_ERROR         — błąd źródła discovery; poprzednia matryca zachowana.
    """

    BASELINE_INITIALIZED = "BASELINE_INITIALIZED"
    SUBSEQUENT_CYCLE = "SUBSEQUENT_CYCLE"
    SOURCE_ERROR = "SOURCE_ERROR"

@dataclass
class CycleReport:
    """
    Report for a single cycle of the ALCHEMIK runtime.
    """
    start_time: datetime
    end_time: datetime
    candidates_count: int
    success_count: int
    error_count: int
    results: List['FinalAnalysisResult']  # Import from data.models
    errors: List['CandidateError']
    alerts_count: int = 0
    alert_success_count: int = 0
    alert_error_count: int = 0
    diagnostics: dict = field(default_factory=dict)

@dataclass
class CandidateError:
    """
    Error details for a single candidate.
    """
    candidate_id: str
    stage: str
    message: str

@dataclass
class ChannelSendResult:
    """
    Result of sending an alert via a channel.
    
    Attributes:
        channel_name (str): Name of the channel.
        success (bool): Whether the send operation succeeded.
        message_id (Optional[str]): ID of the sent message if available.
        error_message (Optional[str]): Error message if any.
        sent_at (str): Timestamp when the message was sent.
    """
    channel_name: str
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[str] = None
