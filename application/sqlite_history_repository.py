import sqlite3
import json
from datetime import datetime

class SQLiteHistoryRepository:
    def __init__(self, db_path=None):
        """
        Initialize the SQLite repository.
        
        Args:
            db_path (str, optional): Path to the SQLite database file. If None, uses an in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self._initialize_database()

    def _initialize_database(self):
        """Initialize the database with the required table."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cycles (
                    cycle_id TEXT PRIMARY KEY,
                    execution_time REAL,
                    candidates_count INTEGER,
                    success_count INTEGER,
                    error_count INTEGER,
                    report_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save_cycle(self, cycle_id, cycle_data):
        """
        Save a cycle report to the database.
        
        Args:
            cycle_id (str): Unique identifier for the cycle.
            cycle_data (dict): Data to be stored for the cycle.
        """
        report_json = json.dumps(cycle_data.get("report", {}))
        created_at = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cycles (
                    cycle_id, execution_time, candidates_count, 
                    success_count, error_count, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cycle_id,
                cycle_data.get("execution_time"),
                cycle_data.get("candidates_count"),
                cycle_data.get("success_count"),
                cycle_data.get("error_count"),
                report_json,
                created_at
            ))
            conn.commit()
        finally:
            conn.close()

    def get_cycle(self, cycle_id):
        """
        Retrieve a cycle report by its ID.
        
        Args:
            cycle_id (str): Unique identifier for the cycle.
        
        Returns:
            dict: The cycle data if found, None otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    cycle_id, execution_time, candidates_count, 
                    success_count, error_count, report_json, created_at
                FROM cycles
                WHERE cycle_id = ?
            """, (cycle_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "cycle_id": row[0],
                    "execution_time": row[1],
                    "candidates_count": row[2],
                    "success_count": row[3],
                    "error_count": row[4],
                    "report": json.loads(row[5]),
                    "created_at": row[6]
                }
            return None
        finally:
            conn.close()

    def list_cycles(self):
        """
        List all stored cycle reports.
        
        Returns:
            list: A list of cycle IDs.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT cycle_id FROM cycles ORDER BY created_at")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def delete_cycle(self, cycle_id):
        """
        Delete a cycle report by its ID.
        
        Args:
            cycle_id (str): Unique identifier for the cycle.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cycles WHERE cycle_id = ?", (cycle_id,))
            conn.commit()
        finally:
            conn.close()

    def count(self):
        """
        Count the number of stored cycle reports.
        
        Returns:
            int: The number of cycles stored.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cycles")
            return cursor.fetchone()[0]
        finally:
            conn.close()
