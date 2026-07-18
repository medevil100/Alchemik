import unittest
from typing import List
from unittest.mock import Mock
from application.universe import PennyStockUniverse
from application.market_scanner import MarketScanner, ScanProvider

class TestMarketScanner(unittest.TestCase):
    def test_scan_flow(self):
        """Test the flow from Universe → Provider → candidates."""
        # Setup
        mock_universe = Mock(spec=PennyStockUniverse)
        mock_universe.get_universe.return_value = ["INSTR1", "INSTR2"]
        
        mock_provider = Mock(spec=ScanProvider)
        mock_provider.scan.return_value = [{"symbol": "INSTR1", "data": {}}]
        
        scanner = MarketScanner(mock_universe, mock_provider)
        
        # Execute
        result = scanner.scan()
        
        # Verify
        mock_universe.get_universe.assert_called_once()
        mock_provider.scan.assert_called_once_with(["INSTR1", "INSTR2"])
        self.assertEqual(result, [{"symbol": "INSTR1", "data": {}}])
    
    def test_empty_universe(self):
        """Test behavior with an empty Universe."""
        mock_universe = Mock(spec=PennyStockUniverse)
        mock_universe.get_universe.return_value = []
        
        mock_provider = Mock(spec=ScanProvider)
        mock_provider.scan.return_value = []
        
        scanner = MarketScanner(mock_universe, mock_provider)
        
        result = scanner.scan()
        
        mock_universe.get_universe.assert_called_once()
        mock_provider.scan.assert_called_once_with([])
        self.assertEqual(result, [])
    
    def test_empty_provider_result(self):
        """Test behavior with an empty result from Provider."""
        mock_universe = Mock(spec=PennyStockUniverse)
        mock_universe.get_universe.return_value = ["INSTR1", "INSTR2"]
        
        mock_provider = Mock(spec=ScanProvider)
        mock_provider.scan.return_value = []
        
        scanner = MarketScanner(mock_universe, mock_provider)
        
        result = scanner.scan()
        
        mock_universe.get_universe.assert_called_once()
        mock_provider.scan.assert_called_once_with(["INSTR1", "INSTR2"])
        self.assertEqual(result, [])
    
    def test_order_preservation(self):
        """Test that the order of candidates is preserved."""
        mock_universe = Mock(spec=PennyStockUniverse)
        mock_universe.get_universe.return_value = ["INSTR1", "INSTR2"]
        
        mock_provider = Mock(spec=ScanProvider)
        mock_provider.scan.return_value = [{"symbol": "INSTR2", "data": {}}, {"symbol": "INSTR1", "data": {}}]
        
        scanner = MarketScanner(mock_universe, mock_provider)
        
        result = scanner.scan()
        
        self.assertEqual(result, [{"symbol": "INSTR2", "data": {}}, {"symbol": "INSTR1", "data": {}}])
    
    def test_provider_swap(self):
        """Test that the Provider can be swapped."""
        mock_universe = Mock(spec=PennyStockUniverse)
        mock_universe.get_universe.return_value = ["INSTR1", "INSTR2"]
        
        mock_provider1 = Mock(spec=ScanProvider)
        mock_provider1.scan.return_value = [{"symbol": "INSTR1", "data": {}}]
        
        mock_provider2 = Mock(spec=ScanProvider)
        mock_provider2.scan.return_value = [{"symbol": "INSTR2", "data": {}}]
        
        scanner = MarketScanner(mock_universe, mock_provider1)
        result1 = scanner.scan()
        
        scanner = MarketScanner(mock_universe, mock_provider2)
        result2 = scanner.scan()
        
        self.assertEqual(result1, [{"symbol": "INSTR1", "data": {}}])
        self.assertEqual(result2, [{"symbol": "INSTR2", "data": {}}])
    
    def test_no_hunter_engine_dependency(self):
        """Test that Hunter Engine is not used."""
        mock_universe = Mock(spec=PennyStockUniverse)
        mock_provider = Mock(spec=ScanProvider)
        
        scanner = MarketScanner(mock_universe, mock_provider)
        
        # Verify no Hunter Engine imports or calls
        self.assertNotIn("Hunter", str(scanner.__class__))
        self.assertNotIn("Hunter", str(mock_provider.__class__))