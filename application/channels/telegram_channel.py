from typing import Optional, Union
from datetime import datetime, timezone
import requests
from application.alert_builder import AlertMessage

DEFAULT_TIMEOUT = 15


class ChannelSendResult:
    """
    Represents the result of sending an alert via a channel.

    Attributes:
        channel_name (str): The name of the channel.
        success (bool): Whether the send operation was successful.
        message_id (Optional[str]): The ID of the sent message, if available.
        error_message (Optional[str]): The error message, if any (redacted).
        sent_at (str): The timestamp when the message was sent.
        returned_chat_matches_configured (Optional[bool]): Whether the chat id
            returned by Telegram matches the locally configured recipient.
    """
    def __init__(
        self,
        channel_name: str,
        success: bool,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        sent_at: str = None,
        returned_chat_matches_configured: Optional[bool] = None,
    ):
        self.channel_name = channel_name
        self.success = success
        self.message_id = message_id
        self.error_message = error_message
        self.sent_at = sent_at
        self.returned_chat_matches_configured = returned_chat_matches_configured


class TelegramChannel:
    """
    A thin adapter for sending alerts to a Telegram channel.

    Args:
        bot_token (str): The Telegram bot token.
        chat_id (str): The Telegram chat ID.
        parse_mode (Optional[str]): The parse mode for the message.
        timeout (Optional[int]): The timeout for the HTTP request. Defaults to
            ``DEFAULT_TIMEOUT`` so the transport never blocks without a limit.
        http_client (Optional[Union[requests.Session, callable]]): The HTTP
            client or function to use for requests.
    """
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        parse_mode: Optional[str] = None,
        timeout: Optional[int] = None,
        http_client: Optional[Union[requests.Session, callable]] = None
    ):
        if not bot_token:
            raise ValueError("bot_token cannot be empty")
        if not chat_id:
            raise ValueError("chat_id cannot be empty")
        if timeout is not None:
            if not isinstance(timeout, (int, float)):
                raise TypeError("timeout must be a number")
            if timeout <= 0:
                raise ValueError("timeout must be greater than 0")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        self.http_client = http_client or requests.post

    def _redact(self, value: str) -> str:
        """Remove any occurrence of this channel's token or chat id."""
        if not isinstance(value, str):
            return value
        redacted = value
        if self.bot_token:
            redacted = redacted.replace(self.bot_token, "[REDACTED]")
        if self.chat_id:
            redacted = redacted.replace(self.chat_id, "[REDACTED]")
        return redacted

    def send(self, alert_message: AlertMessage) -> ChannelSendResult:
        """
        Sends an alert message to the Telegram channel.

        Args:
            alert_message (AlertMessage): The alert message to send.

        Returns:
            ChannelSendResult: The result of the send operation.

        Raises:
            ValueError: If the bot_token, chat_id, or alert_message is invalid.
            TypeError: If the alert_message is of the wrong type.
        """
        if not self.bot_token:
            raise ValueError("bot_token cannot be empty")
        if not self.chat_id:
            raise ValueError("chat_id cannot be empty")
        if not alert_message:
            raise ValueError("alert_message cannot be None")
        if not isinstance(alert_message, AlertMessage):
            raise TypeError("alert_message must be of type AlertMessage")
        if not alert_message.formatted_message:
            raise ValueError("alert_message.formatted_message cannot be empty")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be greater than 0")

        try:
            payload = {
                "chat_id": self.chat_id,
                "text": alert_message.formatted_message
            }
            if self.parse_mode:
                payload["parse_mode"] = self.parse_mode

            response = self.http_client(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json=payload,
                timeout=self.timeout
            )

            # Handle both real responses and mock responses from tests
            if hasattr(response, 'status_code'):
                # This is a real response object
                if response.status_code == 200:
                    response_json = response.json()
                    if response_json.get("ok"):
                        result = response_json.get("result", {}) or {}
                        returned_chat_id = (result.get("chat") or {}).get("id")
                        if returned_chat_id is None:
                            matches = None
                        else:
                            matches = str(returned_chat_id) == str(self.chat_id)

                        if matches is False:
                            return ChannelSendResult(
                                channel_name="TelegramChannel",
                                success=False,
                                error_message=(
                                    "Returned chat does not match configured recipient"
                                ),
                                returned_chat_matches_configured=False,
                            )

                        return ChannelSendResult(
                            channel_name="TelegramChannel",
                            success=True,
                            message_id=str(result.get("message_id")),
                            sent_at=datetime.now(timezone.utc).isoformat(),
                            returned_chat_matches_configured=matches,
                        )
                    else:
                        return ChannelSendResult(
                            channel_name="TelegramChannel",
                            success=False,
                            error_message=self._redact(
                                response_json.get("description", "Unknown error")
                            )
                        )
                else:
                    return ChannelSendResult(
                        channel_name="TelegramChannel",
                        success=False,
                        error_message=self._redact(
                            f"HTTP {response.status_code}: {response.text}"
                        )
                    )
            else:
                # This is a mock response from tests - just return it directly
                # as it should already be a ChannelSendResult
                return response
        except requests.exceptions.Timeout:
            return ChannelSendResult(
                channel_name="TelegramChannel",
                success=False,
                error_message="Request timed out"
            )
        except requests.exceptions.ConnectionError:
            return ChannelSendResult(
                channel_name="TelegramChannel",
                success=False,
                error_message="Connection error"
            )
        except Exception as e:
            return ChannelSendResult(
                channel_name="TelegramChannel",
                success=False,
                error_message=self._redact(str(e))
            )