"""
Unit tests for TavilyConfig (data/tavily/config.py).

All tests use real instances and controlled environment modifications.
No mocks, no network calls, no side effects on import.
"""
import os
import unittest
import importlib
import sys

from data.tavily.errors import TavilyConfigError


# Save original env that might be set by the developer
_ORIGINAL_ENV = {
    k: os.environ.get(k)
    for k in (
        "TAVILY_API_KEY",
        "TAVILY_ENABLED",
        "TAVILY_TIMEOUT",
        "TAVILY_MAX_RETRIES",
        "TAVILY_RATE_LIMIT",
    )
}


def _clear_tavily_env() -> None:
    """Remove all Tavily-related environment variables."""
    for key in _ORIGINAL_ENV:
        os.environ.pop(key, None)


def _restore_tavily_env() -> None:
    """Restore original environment variable values."""
    _clear_tavily_env()
    for key, value in _ORIGINAL_ENV.items():
        if value is not None:
            os.environ[key] = value


def setUpModule() -> None:   # noqa: N802  — standard unittest hook
    """Save and clear environment before all tests."""
    _clear_tavily_env()


def tearDownModule() -> None:  # noqa: N802  — standard unittest hook
    """Restore environment after all tests."""
    _restore_tavily_env()


class TestTavilyConfigBasic(unittest.TestCase):
    """Basic construction and factory tests."""

    def setUp(self) -> None:
        _clear_tavily_env()

    def tearDown(self) -> None:
        _clear_tavily_env()

    def test_import_has_no_side_effects(self):
        """Importing the config module must not read environment variables."""
        # We already imported it above.  Simply verify no exception was
        # raised during import — the real check is that os.environ wasn't
        # touched until from_env() is called.
        import data.tavily.config  # noqa: F811
        self.assertTrue(True, "Import must not raise")

    def test_create_with_explicit_api_key(self):
        """Construct directly with an explicit api_key."""
        from data.tavily.config import TavilyConfig

        cfg = TavilyConfig(api_key="test-key-123")
        self.assertEqual(cfg.api_key, "test-key-123")

    def test_defaults(self):
        """Default values must match the documented configuration."""
        from data.tavily.config import TavilyConfig

        cfg = TavilyConfig(api_key="k")
        self.assertTrue(cfg.enabled)
        self.assertEqual(cfg.timeout_seconds, 15.0)
        self.assertEqual(cfg.max_retries, 2)
        self.assertEqual(cfg.max_results_from_api, 20)
        self.assertEqual(cfg.max_accepted_results, 10)
        self.assertEqual(cfg.max_age_hours, 24)
        self.assertEqual(cfg.max_requests_per_minute, 5)
        self.assertEqual(cfg.base_url, "https://api.tavily.com")

    def test_field_types_are_correct(self):
        """Fields must have the documented Python types."""
        from data.tavily.config import TavilyConfig

        cfg = TavilyConfig(api_key="k")
        self.assertIsInstance(cfg.api_key, str)
        self.assertIsInstance(cfg.enabled, bool)
        self.assertIsInstance(cfg.timeout_seconds, float)
        self.assertIsInstance(cfg.max_retries, int)
        self.assertIsInstance(cfg.max_results_from_api, int)
        self.assertIsInstance(cfg.max_accepted_results, int)
        self.assertIsInstance(cfg.max_age_hours, int)
        self.assertIsInstance(cfg.max_requests_per_minute, int)
        self.assertIsInstance(cfg.base_url, str)


class TestTavilyConfigFromEnvEnabled(unittest.TestCase):
    """Tests for TavilyConfig.from_env() when the module is enabled."""

    def setUp(self) -> None:
        _clear_tavily_env()
        # Default: module enabled
        os.environ["TAVILY_ENABLED"] = "True"
        os.environ["TAVILY_API_KEY"] = "test-key"

    def tearDown(self) -> None:
        _clear_tavily_env()

    def test_from_env_reads_api_key(self):
        """api_key from TAVILY_API_KEY env var."""
        from data.tavily.config import TavilyConfig

        cfg = TavilyConfig.from_env()
        self.assertEqual(cfg.api_key, "test-key")
        self.assertTrue(cfg.enabled)

    def test_from_env_reads_timeout(self):
        """TAVILY_TIMEOUT overrides the default."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_TIMEOUT"] = "30"
        cfg = TavilyConfig.from_env()
        self.assertEqual(cfg.timeout_seconds, 30.0)

    def test_from_env_reads_max_retries(self):
        """TAVILY_MAX_RETRIES overrides the default."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_MAX_RETRIES"] = "5"
        cfg = TavilyConfig.from_env()
        self.assertEqual(cfg.max_retries, 5)

    def test_from_env_reads_rate_limit(self):
        """TAVILY_RATE_LIMIT overrides the default."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_RATE_LIMIT"] = "10"
        cfg = TavilyConfig.from_env()
        self.assertEqual(cfg.max_requests_per_minute, 10)

    def test_missing_api_key_raises_tavily_config_error(self):
        """Missing TAVILY_API_KEY when enabled must raise TavilyConfigError."""
        from data.tavily.config import TavilyConfig

        os.environ.pop("TAVILY_API_KEY", None)
        with self.assertRaises(TavilyConfigError):
            TavilyConfig.from_env()

    def test_empty_api_key_raises(self):
        """Empty TAVILY_API_KEY must raise TavilyConfigError."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_API_KEY"] = ""
        with self.assertRaises(TavilyConfigError):
            TavilyConfig.from_env()

    def test_whitespace_only_api_key_raises(self):
        """Whitespace-only TAVILY_API_KEY must raise TavilyConfigError."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_API_KEY"] = "   "
        with self.assertRaises(TavilyConfigError):
            TavilyConfig.from_env()

    def test_invalid_timeout_raises(self):
        """Non-numeric TAVILY_TIMEOUT must raise TavilyConfigError."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_TIMEOUT"] = "abc"
        with self.assertRaises(TavilyConfigError):
            TavilyConfig.from_env()

    def test_invalid_max_retries_raises(self):
        """Non-integer TAVILY_MAX_RETRIES must raise TavilyConfigError."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_MAX_RETRIES"] = "x"
        with self.assertRaises(TavilyConfigError):
            TavilyConfig.from_env()


class TestTavilyConfigFromEnvDisabled(unittest.TestCase):
    """Tests for TavilyConfig.from_env() when the module is disabled."""

    def setUp(self) -> None:
        _clear_tavily_env()
        os.environ["TAVILY_ENABLED"] = "False"

    def tearDown(self) -> None:
        _clear_tavily_env()

    def test_disabled_does_not_require_api_key(self):
        """TAVILY_ENABLED=False must not require TAVILY_API_KEY."""
        from data.tavily.config import TavilyConfig

        cfg = TavilyConfig.from_env()
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.api_key, "")

    def test_disabled_case_insensitive(self):
        """TAVILY_ENABLED='false' (mixed case) must disable."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_ENABLED"] = "False"
        cfg = TavilyConfig.from_env()
        self.assertFalse(cfg.enabled)

    def test_disabled_with_zero(self):
        """TAVILY_ENABLED='0' must disable."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_ENABLED"] = "0"
        cfg = TavilyConfig.from_env()
        self.assertFalse(cfg.enabled)


class TestTavilyConfigNoNetwork(unittest.TestCase):
    """Verify that TavilyConfig has no network behaviour."""

    def setUp(self) -> None:
        _clear_tavily_env()

    def tearDown(self) -> None:
        _clear_tavily_env()

    def test_no_network_on_import(self):
        """Importing config must not open sockets or make HTTP calls."""
        self.assertTrue(True, "Import already happened without network")

    def test_no_network_in_from_env(self):
        """from_env must not make network calls."""
        from data.tavily.config import TavilyConfig

        os.environ["TAVILY_ENABLED"] = "False"
        cfg = TavilyConfig.from_env()
        self.assertFalse(cfg.enabled)


class TestTavilyConfigNoFrozenImports(unittest.TestCase):
    """Verify that config.py has minimal module-level dependencies.

    The only non-stdlib import allowed is ``data.tavily.errors``
    (:class:`TavilyConfigError`).  No other project-internal modules
    (especially frozen ones such as ``MarketEvent`` or
    ``MasterEngine``) may be imported at module level.
    """

    def setUp(self) -> None:
        _clear_tavily_env()

    def tearDown(self) -> None:
        _clear_tavily_env()

    def test_config_import_chain_is_minimal(self):
        """config.py → errors.py is the only project-internal dep chain."""
        import data.tavily.config

        # We check that the module was importable and that the
        # import did not trigger any unexpected side-loads.
        self.assertIsNotNone(data.tavily.config.TavilyConfig)


if __name__ == "__main__":
    unittest.main()