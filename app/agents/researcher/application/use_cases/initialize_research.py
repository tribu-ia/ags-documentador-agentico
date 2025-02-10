import logging
from typing import Dict
from datetime import datetime
from app.utils.state import ResearchState, SectionState, Section
from app.agents.researcher.domain.entities.research_status import ResearchStatus

logger = logging.getLogger(__name__)

class InitializeResearchUseCase:
    def initialize_state(self, section: Section) -> Dict:
        """
        Inicializa el estado de investigación para una sección.
        
        Args:
            section: Sección a investigar
            
        Returns:
            Dict con el estado inicial
        """
        try:
            logger.debug(f"Initializing research state for section: {section.name}")
            
            return {
                "section": section,
                "status": ResearchStatus.NOT_STARTED,
                "start_time": datetime.utcnow().isoformat(),
                "search_queries": [],
                "source_str": "",
                "completed_sections": []
            }
            
        except Exception as e:
            logger.error(f"Error initializing research state: {str(e)}")
            raise

    def validate_section(self, section: Section) -> None:
        """
        Valida que la sección tenga los campos requeridos.
        
        Args:
            section: Sección a validar
            
        Raises:
            ValueError: Si la sección no es válida
        """
        if not section.name or not section.description:
            raise ValueError(
                f"Invalid section data. Name and description are required. "
                f"Got name: {section.name}, description: {section.description}"
            ) 