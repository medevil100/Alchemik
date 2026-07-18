import unittest
from unittest.mock import Mock
from datetime import datetime
from application.alert_dispatcher import AlertDispatcher, DispatchReport


class TestAlertDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = AlertDispatcher()
        self.mock_alert = Mock()
        self.mock_alert.alert_id = "test_alert_1"

    def test_dispatch_single_channel(self):
        """Test dispatching to a single channel."""
        mock_channel = Mock()
        report = self.dispatcher.dispatch(self.mock_alert, [mock_channel])

        self.assertEqual(report.alert_id, "test_alert_1")
        self.assertEqual(report.channels_count, 1)
        self.assertEqual(report.success_count, 1)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(len(report.successful_channels), 1)
        self.assertEqual(len(report.failed_channels), 0)
        mock_channel.send.assert_called_once_with(self.mock_alert)

    def test_dispatch_multiple_channels(self):
        """Test dispatching to multiple channels."""
        mock_channel1 = Mock()
        mock_channel2 = Mock()
        report = self.dispatcher.dispatch(self.mock_alert, [mock_channel1, mock_channel2])

        self.assertEqual(report.channels_count, 2)
        self.assertEqual(report.success_count, 2)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(len(report.successful_channels), 2)
        self.assertEqual(len(report.failed_channels), 0)
        mock_channel1.send.assert_called_once_with(self.mock_alert)
        mock_channel2.send.assert_called_once_with(self.mock_alert)

    def test_dispatch_channel_error(self):
        """Test error handling when a channel fails."""
        mock_channel1 = Mock()
        mock_channel2 = Mock()
        mock_channel2.send.side_effect = Exception("Channel error")
        report = self.dispatcher.dispatch(self.mock_alert, [mock_channel1, mock_channel2])

        self.assertEqual(report.channels_count, 2)
        self.assertEqual(report.success_count, 1)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(len(report.successful_channels), 1)
        self.assertEqual(len(report.failed_channels), 1)
        self.assertEqual(report.failed_channels[str(mock_channel2)], "Channel error")
        mock_channel1.send.assert_called_once_with(self.mock_alert)
        mock_channel2.send.assert_called_once_with(self.mock_alert)

    def test_dispatch_no_channels(self):
        """Test dispatching with no channels."""
        report = self.dispatcher.dispatch(self.mock_alert, [])

        self.assertEqual(report.channels_count, 0)
        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(len(report.successful_channels), 0)
        self.assertEqual(len(report.failed_channels), 0)

    def test_dispatch_invalid_alert(self):
        """Test dispatching with an invalid alert."""
        with self.assertRaises(TypeError):
            self.dispatcher.dispatch(None, [Mock()])

    def test_dispatch_invalid_channel(self):
        """Test dispatching with an invalid channel."""
        with self.assertRaises(ValueError):
            self.dispatcher.dispatch(self.mock_alert, ["not_a_channel"])

    def test_dispatch_many(self):
        """Test dispatching multiple alerts."""
        mock_channel = Mock()
        mock_alert2 = Mock()
        mock_alert2.alert_id = "test_alert_2"
        reports = self.dispatcher.dispatch_many([self.mock_alert, mock_alert2], [mock_channel])

        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0].alert_id, "test_alert_1")
        self.assertEqual(reports[1].alert_id, "test_alert_2")
        self.assertEqual(mock_channel.send.call_count, 2)