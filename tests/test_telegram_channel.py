import unittest
import requests
from unittest.mock import Mock, patch
from datetime import datetime

from application.channels.telegram_channel import TelegramChannel, ChannelSendResult
from application.alert_builder import AlertMessage


class TestTelegramChannel(unittest.TestCase):
    def setUp(self):
        self.bot_token = "mock_bot_token"
        self.chat_id = "mock_chat_id"
        self.alert_message = AlertMessage(
            alert_id="test_alert_id",
            symbol="TEST",
            market="TEST_MARKET",
            recommendation="BUY",
            final_score=0.8,
            confidence_level=0.9,
            risk_level="LOW",
            summary="Test summary",
            created_at=datetime.now(),
            formatted_message="Test alert message"
        )
        self.telegram_channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )

    def test_send_success(self):
        """Test successful message sending."""
        mock_result = ChannelSendResult(
            channel_name="TelegramChannel",
            success=True,
            message_id="123"
        )

        mock_http_client = Mock(return_value=mock_result)
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            http_client=mock_http_client
        )
        result = channel.send(self.alert_message)
        mock_http_client.assert_called_once()
        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "123")
        self.assertIsInstance(result, ChannelSendResult)

    def test_send_failure_ok_false(self):
        """Test when Telegram API returns ok=False."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "description": "Test error"
        }

        mock_http_client = Mock(return_value=mock_response)
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            http_client=mock_http_client
        )
        result = channel.send(self.alert_message)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Test error")

    def test_send_http_error(self):
        """Test HTTP error responses."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        mock_http_client = Mock(return_value=mock_response)
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            http_client=mock_http_client
        )
        result = channel.send(self.alert_message)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "HTTP 400: Bad request")

    def test_send_timeout(self):
        """Test timeout error."""
        mock_http_client = Mock(side_effect=requests.exceptions.Timeout("Request timed out"))
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            http_client=mock_http_client
        )
        result = channel.send(self.alert_message)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Request timed out")

    def test_send_connection_error(self):
        """Test connection error."""
        mock_http_client = Mock(side_effect=requests.exceptions.ConnectionError("Connection error"))
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            http_client=mock_http_client
        )
        result = channel.send(self.alert_message)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Connection error")

    def test_send_invalid_alert_message(self):
        """Test invalid alert message."""
        with self.assertRaises(ValueError):
            self.telegram_channel.send(None)

        with self.assertRaises(TypeError):
            self.telegram_channel.send("invalid_type")

        with self.assertRaises(ValueError):
            self.telegram_channel.send(AlertMessage(
                alert_id="test_alert_id",
                symbol="TEST",
                market="TEST_MARKET",
                recommendation="BUY",
                final_score=0.8,
                confidence_level=0.9,
                risk_level="LOW",
                summary="Test summary",
                created_at=datetime.now(),
                formatted_message=""
            ))

    def test_send_invalid_config(self):
        """Test invalid bot_token or chat_id."""
        with self.assertRaises(ValueError):
            TelegramChannel(bot_token="", chat_id=self.chat_id).send(self.alert_message)

        with self.assertRaises(ValueError):
            TelegramChannel(bot_token=self.bot_token, chat_id="").send(self.alert_message)

    def test_dependency_injection(self):
        """Test dependency injection for HTTP client."""
        mock_result = ChannelSendResult(
            channel_name="TelegramChannel",
            success=True,
            message_id="123"
        )
        
        mock_http_client = Mock(return_value=mock_result)
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            http_client=mock_http_client
        )
        result = channel.send(self.alert_message)
        mock_http_client.assert_called_once()
        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "123")
        self.assertIsInstance(result, ChannelSendResult)

    def test_parse_mode(self):
        """Test parse_mode parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}

        mock_http_client = Mock(return_value=mock_response)
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            parse_mode="Markdown",
            http_client=mock_http_client
        )
        channel.send(self.alert_message)
        payload = mock_http_client.call_args[1]["json"]
        self.assertEqual(payload["parse_mode"], "Markdown")

    def test_timeout(self):
        """Test timeout parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}

        mock_http_client = Mock(return_value=mock_response)
        channel = TelegramChannel(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            timeout=10,
            http_client=mock_http_client
        )
        channel.send(self.alert_message)
        timeout = mock_http_client.call_args[1]["timeout"]
        self.assertEqual(timeout, 10)

    def test_invalid_timeout(self):
        """Test invalid timeout parameter."""
        with self.assertRaises(ValueError):
            TelegramChannel(
                bot_token=self.bot_token,
                chat_id=self.chat_id,
                timeout=0
            )


if __name__ == "__main__":
    unittest.main()