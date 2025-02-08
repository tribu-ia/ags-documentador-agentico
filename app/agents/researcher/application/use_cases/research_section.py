import logging
from typing import Optional, Dict
from app.utils.state import Section
from app.agents.researcher.application.use_cases.initialize_research import InitializeResearchUseCase
from app.agents.researcher.application.use_cases.manage_research_state import ManageResearchStateUseCase
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier

logger = logging.getLogger(__name__)

class ResearchSectionUseCase:
    """Caso de uso para iniciar la investigación de una sección"""
    
    def __init__(
        self,
        initializer: InitializeResearchUseCase,
        state_manager: ManageResearchStateUseCase,
        progress_notifier: ProgressNotifier
    ):
        self.initializer = initializer
        self.state_manager = state_manager
        self.progress_notifier = progress_notifier

    async def execute(self, section: Section) -> Optional[Dict]:
        """
        Inicia el proceso de investigación para una sección.
        
        Args:
            section: La sección a investigar
            
        Returns:
            Optional[Dict]: El estado inicial de la investigación
            
        Raises:
            ValueError: Si la sección no es válida
            Exception: Si ocurre un error durante el proceso
        """
        try:
            # Validar sección
            self.initializer.validate_section(section)
            
            # Cargar o inicializar estado
            state = await self.state_manager.load_state(section.id)
            if not state:
                state = self.initializer.initialize_state(section)
                await self.state_manager.save_state(section.id, state)
                
            return state

        except ValueError as e:
            await self.progress_notifier.send_progress("Invalid section data", {"error": str(e)})
            raise
        except Exception as e:
            await self.state_manager.log_error(section.id, str(e))
            raise 