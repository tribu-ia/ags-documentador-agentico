import logging
from typing import Optional
from app.utils.state import Section
from app.agents.researcher.domain.entities.research_status import ResearchStatus
from app.agents.researcher.domain.repositories.research_repository import ResearchRepository

logger = logging.getLogger(__name__)

class RecoverSectionStateUseCase:
    """Caso de uso para recuperar el estado de una sección de investigación"""
    
    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    async def execute(self, section: Section) -> Optional[Section]:
        """
        Intenta recuperar el estado de una sección de investigación.
        
        Args:
            section: La sección cuyo estado se quiere recuperar
            
        Returns:
            Optional[Section]: La sección con su estado recuperado o None si no hay estado
        """
        try:
            state = await self.repository.load_state(section.id)
            if not state:
                return None
                
            if state["status"] == ResearchStatus.COMPLETED:
                section["content"] = state["content"]
                return section
                
            # Si falló o está incompleto, retornar el último estado conocido
            return Section(
                id=section.id,
                name=section.name,
                description=section.description,
                content=state.get("content", "")
            )
            
        except Exception as e:
            logger.error(f"Error recovering state for section {section.id}: {str(e)}")
            return None 