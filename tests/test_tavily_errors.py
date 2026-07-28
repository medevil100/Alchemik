"""
Unit tests for the Tavily exception hierarchy (data/tavily/errors.py).

All tests use real instances — no mocks, no external dependencies.
"""
import unittest

from data.tavily.errors import (
    TavilyError,
    TavilyConfigError,
    TavilyAPIError,
    TavilyTimeoutError,
    TavilyRateLimitError,
    TavilyConnectionError,
    TavilyValidationError,
)


class TestTavilyErrorHierarchy(unittest.TestCase):
    """Tests for the Tavily exception class hierarchy and inheritance."""

    # ------------------------------------------------------------------
    # Inheritance chain
    # ------------------------------------------------------------------

    def test_tavily_error_inherits_from_exception(self):
        """TavilyError must inherit directly from Exception."""
        self.assertTrue(issubclass(TavilyError, Exception))

    def test_config_error_inherits_from_tavily_error(self):
        """TavilyConfigError must inherit from TavilyError."""
        self.assertTrue(issubclass(TavilyConfigError, TavilyError))

    def test_api_error_inherits_from_tavily_error(self):
        """TavilyAPIError must inherit from TavilyError."""
        self.assertTrue(issubclass(TavilyAPIError, TavilyError))

    def test_timeout_error_inherits_from_tavily_error(self):
        """TavilyTimeoutError must inherit from TavilyError."""
        self.assertTrue(issubclass(TavilyTimeoutError, TavilyError))

    def test_rate_limit_error_inherits_from_tavily_error(self):
        """TavilyRateLimitError must inherit from TavilyError."""
        self.assertTrue(issubclass(TavilyRateLimitError, TavilyError))

    def test_connection_error_inherits_from_tavily_error(self):
        """TavilyConnectionError must inherit from TavilyError."""
        self.assertTrue(issubclass(TavilyConnectionError, TavilyError))

    def test_validation_error_inherits_from_tavily_error(self):
        """TavilyValidationError must inherit from TavilyError."""
        self.assertTrue(issubclass(TavilyValidationError, TavilyError))

    # ------------------------------------------------------------------
    # Catch-as-base — every sub-exception must be catchable as TavilyError
    # ------------------------------------------------------------------

    def test_config_error_caught_as_tavily_error(self):
        """TavilyConfigError must be caught by 'except TavilyError'."""
        try:
            raise TavilyConfigError("missing api key")
        except TavilyError:
            pass
        else:
            self.fail("TavilyConfigError was not caught as TavilyError")

    def test_api_error_caught_as_tavily_error(self):
        """TavilyAPIError must be caught by 'except TavilyError'."""
        try:
            raise TavilyAPIError("HTTP 500")
        except TavilyError:
            pass
        else:
            self.fail("TavilyAPIError was not caught as TavilyError")

    def test_timeout_error_caught_as_tavily_error(self):
        """TavilyTimeoutError must be caught by 'except TavilyError'."""
        try:
            raise TavilyTimeoutError("request timed out")
        except TavilyError:
            pass
        else:
            self.fail("TavilyTimeoutError was not caught as TavilyError")

    def test_rate_limit_error_caught_as_tavily_error(self):
        """TavilyRateLimitError must be caught by 'except TavilyError'."""
        try:
            raise TavilyRateLimitError("rate limit exceeded")
        except TavilyError:
            pass
        else:
            self.fail("TavilyRateLimitError was not caught as TavilyError")

    def test_connection_error_caught_as_tavily_error(self):
        """TavilyConnectionError must be caught by 'except TavilyError'."""
        try:
            raise TavilyConnectionError("connection refused")
        except TavilyError:
            pass
        else:
            self.fail("TavilyConnectionError was not caught as TavilyError")

    def test_validation_error_caught_as_tavily_error(self):
        """TavilyValidationError must be caught by 'except TavilyError'."""
        try:
            raise TavilyValidationError("invalid json")
        except TavilyError:
            pass
        else:
            self.fail("TavilyValidationError was not caught as TavilyError")

    # ------------------------------------------------------------------
    # Not caught as other sub-exceptions — siblings must not mix
    # ------------------------------------------------------------------

    def test_specific_errors_do_not_cross_catch(self):
        """Sibling sub-exceptions must not inherit from each other."""
        siblings = [
            TavilyConfigError,
            TavilyAPIError,
            TavilyTimeoutError,
            TavilyRateLimitError,
            TavilyConnectionError,
            TavilyValidationError,
        ]
        for i, left in enumerate(siblings):
            for j, right in enumerate(siblings):
                if i == j:
                    continue
                with self.subTest(left=left.__name__, right=right.__name__):
                    self.assertFalse(
                        issubclass(left, right),
                        f"{left.__name__} must not inherit from {right.__name__}",
                    )

    # ------------------------------------------------------------------
    # Message and args preservation
    # ------------------------------------------------------------------

    def test_message_is_preserved(self):
        """The message passed to the constructor must be preserved in str(exc)."""
        exc = TavilyConfigError("api key not set")
        self.assertEqual(str(exc), "api key not set")

    def test_args_are_preserved(self):
        """Standard Exception.args must be preserved for all sub-exceptions."""
        for cls in (
            TavilyError,
            TavilyConfigError,
            TavilyAPIError,
            TavilyTimeoutError,
            TavilyRateLimitError,
            TavilyConnectionError,
            TavilyValidationError,
        ):
            with self.subTest(cls=cls.__name__):
                exc = cls("test-message", 42)
                self.assertEqual(exc.args, ("test-message", 42))

    def test_no_args_preserves_empty_tuple(self):
        """Exception with no arguments must have empty args."""
        exc = TavilyError()
        self.assertEqual(exc.args, ())

    # ------------------------------------------------------------------
    # Module isolation — no external dependencies
    # ------------------------------------------------------------------

    def test_module_has_no_side_imports(self):
        """The errors module must not require external packages."""
        import importlib
        import sys

        # Record modules already loaded
        before = set(sys.modules.keys())
        import data.tavily.errors  # noqa: F811
        after = set(sys.modules.keys())
        new_modules = after - before
        # Only the errors module and its parent packages should be new
        unexpected = [m for m in new_modules if "tavily" not in m]
        self.assertEqual(
            unexpected,
            [],
            f"Unexpected imports: {unexpected}",
        )


if __name__ == "__main__":
    unittest.main()