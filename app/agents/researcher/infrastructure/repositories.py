import sqlite3
from typing import Dict, Optional
import logging
from datetime import datetime
import json

from ...domain.interfaces import ResearchRepository

logger = logging.getLogger(__name__)

class SQLiteResearchRepository(ResearchRepository):
    def __init__(self, db_path: str = "research_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_state (
                    section_id TEXT PRIMARY KEY,
                    state_json TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id TEXT,
                    error_message TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metrics_json TEXT,
                    timestamp TIMESTAMP
                )
            """)

    async def save_state(self, section_id: str, state: Dict) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO research_state 
                    (section_id, state_json, created_at, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (section_id, json.dumps(state)))
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            raise

    async def load_state(self, section_id: str) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT state_json FROM research_state 
                    WHERE section_id = ?
                """, (section_id,))
                row = cursor.fetchone()
                return json.loads(row[0]) if row else None
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            return None

    async def log_error(self, section_id: str, error_message: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO error_log (section_id, error_message, timestamp)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (section_id, error_message))
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")

    async def save_metrics(self, metrics: Dict) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO performance_metrics (metrics_json, timestamp)
                    VALUES (?, CURRENT_TIMESTAMP)
                """, (json.dumps(metrics),))
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}") 