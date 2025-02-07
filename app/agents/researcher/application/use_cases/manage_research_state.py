import logging
from typing import Dict, Optional
from app.agents.researcher.domain.repositories.research_repository import ResearchRepository
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics

logger = logging.getLogger(__name__)

class ManageResearchStateUseCase:
    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    @track_metrics
    async def save_state(self, section_id: str, state: Dict) -> None:
        """Guarda el estado de la investigación"""
        try:
            await self.repository.save_state(section_id, state)
            logger.debug(f"State saved for section: {section_id}")
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            raise

    @track_metrics
    async def load_state(self, section_id: str) -> Optional[Dict]:
        """Carga el estado de la investigación"""
        try:
            state = await self.repository.load_state(section_id)
            if state:
                logger.debug(f"State loaded for section: {section_id}")
            else:
                logger.debug(f"No state found for section: {section_id}")
            return state
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            raise

    @track_metrics
    async def log_error(self, section_id: str, error_message: str) -> None:
        """Registra un error en la investigación"""
        try:
            await self.repository.log_error(section_id, error_message)
            logger.error(f"Error logged for section {section_id}: {error_message}")
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")
            raise

    @track_metrics
    async def save_metrics(self, metrics: Dict) -> None:
        """Guarda métricas de rendimiento"""
        try:
            await self.repository.save_metrics(metrics)
            logger.debug("Performance metrics saved")
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")
            raise 