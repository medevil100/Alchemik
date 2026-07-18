import unittest
from application.history_repository import HistoryRepository

class TestHistoryRepository(unittest.TestCase):
    def setUp(self):
        self.repo = HistoryRepository()

    def test_save_and_get_cycle(self):
        """Test saving and retrieving a cycle."""
        cycle_id = "cycle_1"
        cycle_data = {"key": "value"}
        self.repo.save_cycle(cycle_id, cycle_data)
        retrieved_data = self.repo.get_cycle(cycle_id)
        self.assertEqual(retrieved_data, cycle_data)

    def test_list_cycles(self):
        """Test listing all cycles."""
        cycle_ids = ["cycle_1", "cycle_2"]
        for cycle_id in cycle_ids:
            self.repo.save_cycle(cycle_id, {"key": "value"})
        listed_cycles = self.repo.list_cycles()
        self.assertEqual(set(listed_cycles), set(cycle_ids))

    def test_delete_cycle(self):
        """Test deleting a cycle."""
        cycle_id = "cycle_1"
        self.repo.save_cycle(cycle_id, {"key": "value"})
        self.repo.delete_cycle(cycle_id)
        self.assertIsNone(self.repo.get_cycle(cycle_id))

    def test_count(self):
        """Test counting cycles."""
        self.assertEqual(self.repo.count(), 0)
        self.repo.save_cycle("cycle_1", {"key": "value"})
        self.assertEqual(self.repo.count(), 1)

    def test_empty_repository(self):
        """Test operations on an empty repository."""
        self.assertEqual(self.repo.count(), 0)
        self.assertEqual(self.repo.list_cycles(), [])
        self.assertIsNone(self.repo.get_cycle("nonexistent_cycle"))

    def test_overwrite_cycle(self):
        """Test overwriting a cycle with the same ID."""
        cycle_id = "cycle_1"
        initial_data = {"key": "old_value"}
        updated_data = {"key": "new_value"}
        self.repo.save_cycle(cycle_id, initial_data)
        self.repo.save_cycle(cycle_id, updated_data)
        self.assertEqual(self.repo.get_cycle(cycle_id), updated_data)

if __name__ == "__main__":
    unittest.main()