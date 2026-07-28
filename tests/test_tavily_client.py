"""
Unit tests for TavilyClient (data/tavily/client.py).

All tests use deterministic mocks — no internet, no real API key.
Only the transport boundary (``requests.post``) is mocked.
"""
import unittest
from unittest.mock import Mock, patch

import requests as requests_lib

from data.tavily.client import TavilyClient
from data.tavily.config import TavilyConfig
from data.tavily.errors import (
    TavilyAPIError,
    TavilyConfigError,
    TavilyConnectionError,
    TavilyRateLimitError,
    TavilyTimeoutError,
    TavilyValidationError,
)
from data.tavily.models import TavilyQueryRequest


def _make_response(json_body: object, status_code: int = 200) -> Mock:
    """Factory for a mock ``requests.Response``."""
    resp = Mock()
    resp.json.return_value = json_body
    resp.status_code = status_code
    return resp


# ===================================================================
# TavilyClient — Constructor
# ===================================================================


class TestTavilyClientConstructor(unittest.TestCase):
    """Constructor behaviour."""

    def test_constructor_with_valid_config(self):
        """Constructor must not raise for a valid TavilyConfig."""
        config = TavilyConfig(api_key="k")
        client = TavilyClient(config)
        self.assertIsInstance(client, TavilyClient)

    def test_constructor_with_invalid_type(self):
        """Constructor must raise TypeError for a non-TavilyConfig."""
        with self.assertRaises(TypeError):
            TavilyClient("not a config")  # type: ignore[arg-type]

    def test_constructor_makes_no_network_call(self):
        """The constructor must NOT perform any HTTP request."""
        with patch("data.tavily.client.requests.post") as mock_post:
            TavilyClient(TavilyConfig(api_key="k"))
        mock_post.assert_not_called()


# ===================================================================
# TavilyClient.search — argument validation
# ===================================================================


class TestTavilyClientSearchArgumentValidation(unittest.TestCase):
    """Type checks on the *request* argument."""

    def setUp(self) -> None:
        self.client = TavilyClient(TavilyConfig(api_key="k"))

    def test_search_with_invalid_request_type(self):
        """search() must raise TypeError for a non-TavilyQueryRequest."""
        with self.assertRaises(TypeError):
            self.client.search({"query": "x"})  # type: ignore[arg-type]

    def test_search_when_disabled(self):
        """search() must raise TavilyConfigError when enabled=False."""
        config = TavilyConfig(api_key="k", enabled=False)
        client = TavilyClient(config)
        request = TavilyQueryRequest(query="test")
        with self.assertRaises(TavilyConfigError):
            client.search(request)

    def test_disabled_never_calls_post(self):
        """When disabled, no HTTP request must be sent."""
        config = TavilyConfig(api_key="k", enabled=False)
        client = TavilyClient(config)
        request = TavilyQueryRequest(query="test")
        with patch("data.tavily.client.requests.post") as mock_post:
            with self.assertRaises(TavilyConfigError):
                client.search(request)
        mock_post.assert_not_called()


# ===================================================================
# TavilyClient.search — successful request
# ===================================================================


class TestTavilyClientSearchSuccess(unittest.TestCase):
    """Happy-path tests with a 200 response."""

    def setUp(self) -> None:
        self.config = TavilyConfig(api_key="test-key")
        self.client = TavilyClient(self.config)

    def test_search_returns_dict_unchanged(self):
        """search() must return the JSON dict as-is."""
        body = {"results": [{"title": "News"}]}
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response(body, 200)
            result = self.client.search(TavilyQueryRequest(query="q"))
        self.assertEqual(result, body)
        self.assertIs(result, body)

    def test_search_uses_correct_url(self):
        """The URL must be built from base_url + '/search' without double slash."""
        config = TavilyConfig(api_key="k", base_url="https://api.tavily.com/")
        client = TavilyClient(config)
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 200)
            client.search(TavilyQueryRequest(query="q"))
        url_arg = mock_post.call_args[0][0]
        self.assertEqual(url_arg, "https://api.tavily.com/search")

    def test_search_uses_config_timeout(self):
        """The timeout must equal config.timeout_seconds."""
        config = TavilyConfig(api_key="k", timeout_seconds=42.0)
        client = TavilyClient(config)
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 200)
            client.search(TavilyQueryRequest(query="q"))
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 42.0)

    def test_search_payload_mandatory_fields(self):
        """The mandatory fields must be present in the JSON payload."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 200)
            self.client.search(
                TavilyQueryRequest(query="q", max_results=7, search_depth="advanced")
            )
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["api_key"], "test-key")
        self.assertEqual(payload["query"], "q")
        self.assertEqual(payload["max_results"], 7)
        self.assertEqual(payload["search_depth"], "advanced")

    def test_search_domains_converted_to_lists(self):
        """Tuple domains must be converted to lists in the payload."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 200)
            self.client.search(
                TavilyQueryRequest(
                    query="q",
                    include_domains=("a.com", "b.com"),
                    exclude_domains=("x.com",),
                )
            )
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["include_domains"], ["a.com", "b.com"])
        self.assertEqual(payload["exclude_domains"], ["x.com"])

    def test_empty_domains_omitted(self):
        """Empty domain tuples must be omitted from the payload."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 200)
            self.client.search(TavilyQueryRequest(query="q"))
        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("include_domains", payload)
        self.assertNotIn("exclude_domains", payload)

    def test_single_http_request(self):
        """search() must call requests.post exactly once."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 200)
            self.client.search(TavilyQueryRequest(query="q"))
        mock_post.assert_called_once()


# ===================================================================
# TavilyClient.search — transport errors
# ===================================================================


class TestTavilyClientSearchTransportErrors(unittest.TestCase):
    """Network-level and HTTP errors."""

    def setUp(self) -> None:
        self.client = TavilyClient(TavilyConfig(api_key="k"))
        self.request = TavilyQueryRequest(query="q")

    def test_timeout_raises_tavily_timeout_error(self):
        """requests.Timeout must be mapped to TavilyTimeoutError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.side_effect = requests_lib.Timeout()
            with self.assertRaises(TavilyTimeoutError):
                self.client.search(self.request)

    def test_connection_error_raises_tavily_connection_error(self):
        """requests.ConnectionError must be mapped to TavilyConnectionError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.side_effect = requests_lib.ConnectionError()
            with self.assertRaises(TavilyConnectionError):
                self.client.search(self.request)

    def test_http_429_raises_tavily_rate_limit_error(self):
        """HTTP 429 must be mapped to TavilyRateLimitError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 429)
            with self.assertRaises(TavilyRateLimitError):
                self.client.search(self.request)

    def test_http_4xx_raises_tavily_api_error(self):
        """HTTP 404 (other 4xx) must be mapped to TavilyAPIError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 404)
            with self.assertRaises(TavilyAPIError):
                self.client.search(self.request)

    def test_http_5xx_raises_tavily_api_error(self):
        """HTTP 500 must be mapped to TavilyAPIError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 500)
            with self.assertRaises(TavilyAPIError):
                self.client.search(self.request)

    def test_invalid_json_raises_validation_error(self):
        """A response with invalid JSON must raise TavilyValidationError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            resp = Mock()
            resp.status_code = 200
            resp.json.side_effect = requests_lib.exceptions.JSONDecodeError(
                "msg", "", 0
            )
            mock_post.return_value = resp
            with self.assertRaises(TavilyValidationError):
                self.client.search(self.request)

    def test_non_dict_json_raises_validation_error(self):
        """A JSON list (not dict) must raise TavilyValidationError."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response(["item1", "item2"], 200)
            with self.assertRaises(TavilyValidationError):
                self.client.search(self.request)


# ===================================================================
# TavilyClient — no retry
# ===================================================================


class TestTavilyClientNoRetry(unittest.TestCase):
    """Verify that search() never retries."""

    def setUp(self) -> None:
        self.client = TavilyClient(TavilyConfig(api_key="k"))
        self.request = TavilyQueryRequest(query="q")

    def test_no_retry_on_timeout(self):
        """A timeout must result in exactly one HTTP call (no retry)."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.side_effect = requests_lib.Timeout()
            with self.assertRaises(TavilyTimeoutError):
                self.client.search(self.request)
        mock_post.assert_called_once()

    def test_no_retry_on_connection_error(self):
        """A connection error must result in exactly one HTTP call."""
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.side_effect = requests_lib.ConnectionError()
            with self.assertRaises(TavilyConnectionError):
                self.client.search(self.request)
        mock_post.assert_called_once()


# ===================================================================
# TavilyClient — api_key must NOT leak
# ===================================================================


class TestTavilyClientNoApiKeyLeak(unittest.TestCase):
    """The api_key value must never appear in error messages."""

    SECRET = "sk-very-secret-key-12345"

    def setUp(self) -> None:
        self.config = TavilyConfig(api_key=self.SECRET)
        self.client = TavilyClient(self.config)
        self.request = TavilyQueryRequest(query="q")

    def _assert_key_not_in_message(self, exception: BaseException) -> None:
        msg = str(exception)
        self.assertNotIn(
            self.SECRET,
            msg,
            f"API key leaked in {type(exception).__name__}: {msg!r}",
        )

    def test_api_key_not_in_timeout_error(self):
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.side_effect = requests_lib.Timeout()
            with self.assertRaises(TavilyTimeoutError) as ctx:
                self.client.search(self.request)
            self._assert_key_not_in_message(ctx.exception)

    def test_api_key_not_in_connection_error(self):
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.side_effect = requests_lib.ConnectionError()
            with self.assertRaises(TavilyConnectionError) as ctx:
                self.client.search(self.request)
            self._assert_key_not_in_message(ctx.exception)

    def test_api_key_not_in_rate_limit_error(self):
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 429)
            with self.assertRaises(TavilyRateLimitError) as ctx:
                self.client.search(self.request)
            self._assert_key_not_in_message(ctx.exception)

    def test_api_key_not_in_api_error(self):
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response({}, 500)
            with self.assertRaises(TavilyAPIError) as ctx:
                self.client.search(self.request)
            self._assert_key_not_in_message(ctx.exception)

    def test_api_key_not_in_validation_error_invalid_json(self):
        with patch("data.tavily.client.requests.post") as mock_post:
            resp = Mock()
            resp.status_code = 200
            resp.json.side_effect = requests_lib.exceptions.JSONDecodeError(
                "msg", "", 0
            )
            mock_post.return_value = resp
            with self.assertRaises(TavilyValidationError) as ctx:
                self.client.search(self.request)
            self._assert_key_not_in_message(ctx.exception)

    def test_api_key_not_in_validation_error_non_dict(self):
        with patch("data.tavily.client.requests.post") as mock_post:
            mock_post.return_value = _make_response([1, 2, 3], 200)
            with self.assertRaises(TavilyValidationError) as ctx:
                self.client.search(self.request)
            self._assert_key_not_in_message(ctx.exception)

    def test_api_key_not_in_config_error_disabled(self):
        config = TavilyConfig(api_key=self.SECRET, enabled=False)
        client = TavilyClient(config)
        with self.assertRaises(TavilyConfigError) as ctx:
            client.search(self.request)
        self._assert_key_not_in_message(ctx.exception)


if __name__ == "__main__":
    unittest.main()