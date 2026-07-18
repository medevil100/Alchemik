class HistoryRepository:
    def __init__(self):
        self._cycles = {}

    def save_cycle(self, cycle_id, cycle_data):
        """
        Save a cycle report.

        Args:
            cycle_id: Unique identifier for the cycle.
            cycle_data: Data to be stored for the cycle.
        """
        self._cycles[cycle_id] = cycle_data

    def get_cycle(self, cycle_id):
        """
        Retrieve a cycle report by its ID.

        Args:
            cycle_id: Unique identifier for the cycle.

        Returns:
            The cycle data if found, None otherwise.
        """
        return self._cycles.get(cycle_id)

    def list_cycles(self):
        """
        List all stored cycle reports.

        Returns:
            A list of cycle IDs.
        """
        return list(self._cycles.keys())

    def delete_cycle(self, cycle_id):
        """
        Delete a cycle report by its ID.

        Args:
            cycle_id: Unique identifier for the cycle.
        """
        if cycle_id in self._cycles:
            del self._cycles[cycle_id]

    def count(self):
        """
        Count the number of stored cycle reports.

        Returns:
            The number of cycles stored.
        """
        return len(self._cycles)