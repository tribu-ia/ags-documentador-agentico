import sqlite3
import logging
from typing import Dict

from app.agents.researcher.domain.repositories.research_repository import ResearchRepository
from .research_queries import ResearchQueries

logger = logging.getLogger(__name__)

class SQLiteResearchRepository(ResearchRepository):
    def __init__(self, db_path: str = "research_state.db"):
        """Initialize SQLite repository"""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(ResearchQueries.CREATE_RESEARCH_STATE_TABLE)
            conn.execute(ResearchQueries.CREATE_ERROR_LOG_TABLE)
            conn.execute(ResearchQueries.CREATE_METRICS_TABLE)

    async def save_metrics(self, metrics: Dict) -> None:
        """Save performance metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(ResearchQueries.INSERT_METRICS, (str(metrics),))
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}") 

