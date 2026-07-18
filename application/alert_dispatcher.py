from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

@dataclass
class DispatchReport:
    """
    Report for dispatching alerts to channels.
    """
    alert_id: str
    channels_count: int
    success_count: int
    error_count: int
    successful_channels: List[str]
    failed_channels: Dict[str, str]  # channel_name: error_message
    started_at: datetime
    finished_at: datetime


class AlertDispatcher:
    """
    Dispatches AlertMessage to one or multiple channels.
    """

    def dispatch(self, alert_message: Any, channels: List[Any]) -> DispatchReport:
        """
        Dispatch an alert message to the provided channels.

        Args:
            alert_message: The alert message to dispatch.
            channels: List of channels to dispatch the alert to.

        Returns:
            DispatchReport: Report of the dispatch operation.

        Raises:
            TypeError: If alert_message is not of the correct type.
            ValueError: If channels are invalid.
        """
        if not alert_message or not hasattr(alert_message, "alert_id"):
            raise TypeError("Invalid AlertMessage type")

        if not isinstance(channels, list):
            raise ValueError("Channels must be a list")

        for channel in channels:
            if not hasattr(channel, "send"):
                raise ValueError(f"Channel {channel} does not have a 'send' method")

        report = DispatchReport(
            alert_id=alert_message.alert_id,
            channels_count=len(channels),
            success_count=0,
            error_count=0,
            successful_channels=[],
            failed_channels={},
            started_at=datetime.now(),
            finished_at=datetime.now(),
        )

        for channel in channels:
            try:
                channel.send(alert_message)
                report.success_count += 1
                report.successful_channels.append(str(channel))
            except Exception as e:
                report.error_count += 1
                report.failed_channels[str(channel)] = str(e)

        report.finished_at = datetime.now()
        return report

    def dispatch_many(self, alert_messages: List[Any], channels: List[Any]) -> List[DispatchReport]:
        """
        Dispatch multiple alert messages to the provided channels.

        Args:
            alert_messages: List of alert messages to dispatch.
            channels: List of channels to dispatch the alerts to.

        Returns:
            List[DispatchReport]: Reports for each dispatch operation.
        """
        return [self.dispatch(alert, channels) for alert in alert_messages]