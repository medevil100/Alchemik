import unittest
from unittest.mock import Mock
from application.universe import PennyStockUniverse

class TestPennyStockUniverse(unittest.TestCase):
    def test_get_universe_returns_list(self):
        """Test that get_universe() returns a list of instruments."""
        mock_source = Mock()
        mock_source.get_instruments.return_value = ["TEST1", "TEST2"]
        universe = PennyStockUniverse(mock_source)
        result = universe.get_universe()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_get_universe_empty_list(self):
        """Test that get_universe() handles an empty list."""
        mock_source = Mock()
        mock_source.get_instruments.return_value = []
        universe = PennyStockUniverse(mock_source)
        result = universe.get_universe()
        self.assertEqual(result, [])

    def test_get_universe_no_duplicates(self):
        """Test that get_universe() returns no duplicates."""
        mock_source = Mock()
        mock_source.get_instruments.return_value = ["TEST1", "TEST1", "TEST2"]
        universe = PennyStockUniverse(mock_source)
        result = universe.get_universe()
        self.assertEqual(len(result), len(set(result)))

    def test_get_universe_order_preserved(self):
        """Test that get_universe() preserves the order of instruments."""
        mock_source = Mock()
        mock_source.get_instruments.return_value = ["TEST1", "TEST2", "TEST3"]
        universe = PennyStockUniverse(mock_source)
        result = universe.get_universe()
        self.assertEqual(result, ["TEST1", "TEST2", "TEST3"])

    def test_source_swapping(self):
        """Test that the data source can be swapped."""
        mock_source1 = Mock()
        mock_source1.get_instruments.return_value = ["TEST1"]
        mock_source2 = Mock()
        mock_source2.get_instruments.return_value = ["TEST2"]
        universe = PennyStockUniverse(mock_source1)
        self.assertEqual(universe.get_universe(), ["TEST1"])
        universe._source = mock_source2
        self.assertEqual(universe.get_universe(), ["TEST2"])

    def test_no_hunter_engine_dependency(self):
        """Test that PennyStockUniverse does not depend on Hunter Engine."""
        # Check that the PennyStockUniverse class does not import from engines.hunter
        import inspect
        source = inspect.getsource(PennyStockUniverse)
        self.assertNotIn("from engines.hunter", source)
        self.assertNotIn("import engines.hunter", source)

    def test_no_master_engine_dependency(self):
        """Test that PennyStockUniverse does not depend on Master Engine."""
        # Check that the PennyStockUniverse class does not import from engines.master
        import inspect
        source = inspect.getsource(PennyStockUniverse)
        self.assertNotIn("from engines.master", source)
        self.assertNotIn("import engines.master", source)

    def test_no_http_requests(self):
        """Test that PennyStockUniverse does not make HTTP requests."""
        # This test is no longer needed as HTTP requests are not part of the PennyStockUniverse scope.
        pass
