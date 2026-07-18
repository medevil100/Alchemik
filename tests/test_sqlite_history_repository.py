import unittest
import tempfile
import os
import json
from datetime import datetime
from application.sqlite_history_repository import SQLiteHistoryRepository

class TestSQLiteHistoryRepository(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for the database
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db_file.name
        self.temp_db_file.close()
        
        # Initialize the repository with the temporary database
        self.repo = SQLiteHistoryRepository(self.db_path)
        
        # Sample cycle data
        self.cycle_id = "test_cycle_1"
        self.cycle_data = {
            "execution_time": 123.45,
            "candidates_count": 10,
            "success_count": 8,
            "error_count": 2,
            "report": {"key": "value"}
        }
    
    def tearDown(self):
        # Ensure all connections are closed
        if hasattr(self, 'repo'):
            # Close any open connections (SQLite may keep them open)
            if hasattr(self.repo, '_connection'):
                self.repo._connection.close()
        # Clean up the temporary file
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass  # Skip if file is still locked
    
    def test_save_and_get_cycle(self):
        """Test saving and retrieving a cycle."""
        # Save the cycle
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        
        # Retrieve the cycle
        retrieved_data = self.repo.get_cycle(self.cycle_id)
        
        # Verify the data
        self.assertEqual(retrieved_data["cycle_id"], self.cycle_id)
        self.assertEqual(retrieved_data["execution_time"], self.cycle_data["execution_time"])
        self.assertEqual(retrieved_data["candidates_count"], self.cycle_data["candidates_count"])
        self.assertEqual(retrieved_data["success_count"], self.cycle_data["success_count"])
        self.assertEqual(retrieved_data["error_count"], self.cycle_data["error_count"])
        self.assertEqual(retrieved_data["report"], self.cycle_data["report"])
        self.assertIsNotNone(retrieved_data["created_at"])
    
    def test_list_cycles(self):
        """Test listing all cycles."""
        # Save multiple cycles
        cycle_ids = ["cycle_1", "cycle_2"]
        for cycle_id in cycle_ids:
            self.repo.save_cycle(cycle_id, self.cycle_data)
        
        # List cycles
        listed_cycles = self.repo.list_cycles()
        
        # Verify the list
        self.assertEqual(set(listed_cycles), set(cycle_ids))
    
    def test_delete_cycle(self):
        """Test deleting a cycle."""
        # Save the cycle
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        
        # Delete the cycle
        self.repo.delete_cycle(self.cycle_id)
        
        # Verify the cycle is deleted
        self.assertIsNone(self.repo.get_cycle(self.cycle_id))
    
    def test_count(self):
        """Test counting cycles."""
        # Verify initial count is 0
        self.assertEqual(self.repo.count(), 0)
        
        # Save a cycle
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        
        # Verify count is 1
        self.assertEqual(self.repo.count(), 1)
    
    def test_empty_repository(self):
        """Test operations on an empty repository."""
        # Verify initial state
        self.assertEqual(self.repo.count(), 0)
        self.assertEqual(self.repo.list_cycles(), [])
        self.assertIsNone(self.repo.get_cycle("nonexistent_cycle"))
    
    def test_overwrite_cycle(self):
        """Test overwriting a cycle with the same ID."""
        # Save initial cycle
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        
        # Update the cycle data
        updated_data = {
            "execution_time": 678.90,
            "candidates_count": 20,
            "success_count": 15,
            "error_count": 5,
            "report": {"key": "updated_value"}
        }
        self.repo.save_cycle(self.cycle_id, updated_data)
        
        # Verify the cycle is updated
        retrieved_data = self.repo.get_cycle(self.cycle_id)
        self.assertEqual(retrieved_data["execution_time"], updated_data["execution_time"])
        self.assertEqual(retrieved_data["report"], updated_data["report"])
    
    def test_persistence(self):
        """Test data persistence after repository reinitialization."""
        # Save a cycle
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        
        # Reinitialize the repository with the same database file
        new_repo = SQLiteHistoryRepository(self.db_path)
        
        # Verify the cycle is still there
        retrieved_data = new_repo.get_cycle(self.cycle_id)
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data["cycle_id"], self.cycle_id)
    
    def test_datetime_serialization(self):
        """Test datetime serialization and deserialization."""
        # Save the cycle
        self.repo.save_cycle(self.cycle_id, self.cycle_data)
        
        # Retrieve the cycle
        retrieved_data = self.repo.get_cycle(self.cycle_id)
        
        # Verify the created_at field is a valid ISO 8601 string
        try:
            datetime.fromisoformat(retrieved_data["created_at"])
        except ValueError:
            self.fail("created_at is not a valid ISO 8601 datetime string")

if __name__ == "__main__":
    unittest.main()