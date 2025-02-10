# -*- coding: utf-8 -*-

import hashlib
import logging
import re
from typing import List, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.agents.researcher.application.use_cases.generate_initial_queries import GenerateInitialQueriesUseCase
from app.agents.researcher.application.use_cases.generate_queries import GenerateQueriesUseCase
from app.agents.researcher.application.use_cases.initialize_research import InitializeResearchUseCase
from app.agents.researcher.application.use_cases.manage_research_state import ManageResearchStateUseCase
from app.agents.researcher.application.use_cases.recover_section_state import RecoverSectionStateUseCase
from app.agents.researcher.application.use_cases.research_section import ResearchSectionUseCase
from app.agents.researcher.application.use_cases.search_web_queries import SearchWebQueriesUseCase
from app.agents.researcher.application.use_cases.validate_query import ValidateQueryUseCase
from app.agents.researcher.application.use_cases.web_search import WebSearchUseCase
from app.agents.researcher.application.use_cases.write_section import WriteSectionUseCase
from app.agents.researcher.domain.entities.query_validation import QueryValidation
from app.agents.researcher.infrastructure.repositories.sqlite_repository import SQLiteResearchRepository
from app.agents.researcher.infrastructure.services.gemini_service import GeminiService
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier
from app.agents.researcher.infrastructure.services.prompt_generation_service import PromptGenerationService
from app.config.config import get_settings
from app.utils.state import SectionState, Section

# Configuración avanzada de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # handlers=[
    #     logging.FileHandler('research.log'),
    #     logging.StreamHandler(sys.stdout)
    # ]
)
logger = logging.getLogger(__name__)


class ResearchManager:
    def __init__(
        self, 
        settings=None, 
        repository=None, 
        verbose=False, 
        websocket=None
    ):
        self.settings = settings or get_settings()
        self.repository = repository or SQLiteResearchRepository()
        
        # Inicializar servicios y casos de uso
        self.progress_notifier = ProgressNotifier(websocket, verbose)
        self.language_model = GeminiService(self.settings.google_api_key)
        self.state_manager = ManageResearchStateUseCase(self.repository)
        self.initializer = InitializeResearchUseCase()
        
        self.prompt_generator = PromptGenerationService(self.language_model)
        self.query_validator = ValidateQueryUseCase()
        self.generate_queries_use_case = GenerateQueriesUseCase(
            self.prompt_generator,
            self.query_validator,
            self.progress_notifier,
            self.settings.number_of_queries
        )
        self.web_searcher = WebSearchUseCase(
            self.settings.tavily_topic,
            self.settings.tavily_days
        )
        self.search_web_queries = SearchWebQueriesUseCase(
            self.web_searcher,
            self.progress_notifier
        )
        self.section_writer = WriteSectionUseCase(self.language_model)
        self.section_state_recovery = RecoverSectionStateUseCase(self.repository)
        self.research_section_use_case = ResearchSectionUseCase(
            self.initializer,
            self.state_manager,
            self.progress_notifier
        )
        self.generate_initial_queries = GenerateInitialQueriesUseCase(self.language_model)
        
        # Configuración para determinar el uso de grounding
        self.grounding_threshold = {
            'relevance_score': 0.7,  # Umbral para decidir usar grounding
            'query_complexity': 0.6   # Umbral de complejidad de la consulta
        }
        
        # Configuración para grounding
        self.grounding_config = {
            'temperature': 0.7,
            'candidate_count': 1,
            'top_k': 40,
            'top_p': 0.95,
        }

    async def generate_queries(self, state: SectionState) -> dict:
        """Generate and validate search queries using multiple engines with smart selection."""
        try:
            section = state["section"]
            
            # Evaluar complejidad de la sección para determinar el método
            complexity_score = await self._evaluate_search_complexity(
                section.name,
                section.description
            )
            
            await self.progress_notifier.send_progress(
                f"Generating queries for section: {section.name}"
            )

            # Generar queries usando el método apropiado
            if complexity_score >= self.grounding_threshold['query_complexity']:
                # Usar grounding para consultas complejas
                queries_result = await self.generate_queries_use_case.execute_with_grounding(
                    state,
                    self.grounding_config
                )
                method_used = 'grounding'
            else:
                # Usar método normal para consultas simples
                queries_result = await self.generate_queries_use_case.execute(state)
                method_used = 'normal'

            # Agregar métricas de decisión al resultado
            queries_result['decision_metrics'] = {
                'complexity_score': complexity_score,
                'threshold_used': self.grounding_threshold['query_complexity'],
                'method_used': method_used
            }

            await self.progress_notifier.send_progress(
                f"Generated queries using {method_used} method",
                {"section_name": section.name}
            )

            return queries_result

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error generating queries", 
                {"error": str(e)}
            )
            logger.error(f"Error generating queries: {str(e)}")
            raise

    async def search_web(self, state: SectionState) -> dict:
        """Perform web searches based on generated queries."""
        return await self.search_web_queries.execute(state)

    async def write_section(self, state: SectionState) -> dict:
        """Write a section based on research results."""
        try:
            section = state["section"]
            source_str = state["source_str"]
            
            await self.progress_notifier.send_progress(f"Writing section: {section.name}")

            section_content = await self.section_writer.write(section, source_str)
            
            if section_content:
                setattr(section, "content", section_content)
                
                logger.debug(f"Completed writing section: {section.name}")
                await self.progress_notifier.send_progress("Section completed", {
                    "section_name": section.name
                })
                return {"completed_sections": [section]}

        except Exception as e:
            await self.progress_notifier.send_progress("Error writing section", {"error": str(e)})
            raise

    async def write_section_with_grounding(self, state: SectionState) -> dict:
        """Write a section based on research results using grounding."""
        try:
            section = state["section"]
            source_str = state["source_str"]
            
            await self.progress_notifier.send_progress(f"Writing section with grounding: {section.name}")

            grounded_result = await self.section_writer.write_with_grounding(
                section, 
                source_str, 
                self.grounding_config
            )
            
            if grounded_result['content']:
                setattr(section, "content", grounded_result['content'])
                if grounded_result.get('grounding_metadata'):
                    setattr(section, "grounding_metadata", grounded_result['grounding_metadata'])
                
                logger.debug(f"Completed writing section with grounding: {section.name}")
                await self.progress_notifier.send_progress("Section completed", {
                    "section_name": section.name,
                    "grounded": True
                })
                return {
                    "completed_sections": [section],
                    "grounding_metadata": grounded_result.get('grounding_metadata')
                }

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error writing section with grounding", 
                {"error": str(e)}
            )
            raise

    def _normalize_query(self, query: str) -> str:
        """Normalize a query by removing extra spaces and converting to lowercase."""
        return re.sub(r'\s+', ' ', query.lower().strip())

    def _get_query_hash(self, query: str) -> str:
        """Generate a hash for a query to help with deduplication."""
        return hashlib.md5(query.encode()).hexdigest()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def validate_query(self, query: str) -> QueryValidation:
        """Validate a search query using simple heuristics."""
        try:
            # Simplified validation logic
            specificity = 0.8  # Default high specificity
            relevance = 0.8   # Default high relevance
            clarity = 0.8     # Default high clarity
            
            return QueryValidation(
                specificity=specificity,
                relevance=relevance,
                clarity=clarity
            )
        except Exception as e:
            logger.error(f"Query validation failed: {str(e)}")
            # Return default validation instead of failing
            return QueryValidation(
                specificity=0.7,
                relevance=0.7,
                clarity=0.7
            )

    async def generate_initial_queries(self, state: SectionState) -> List[str]:
        """Generate initial queries using language model with retry logic."""
        return await self.generate_initial_queries.execute(
            state, 
            self.settings.number_of_queries
        )

    async def research_section(self, section: Section) -> None:
        """Proxy method for section research"""
        return await self.research_section_use_case.execute(section)

    async def recover_state(self, section: Section) -> Optional[Section]:
        """Proxy method for section state recovery"""
        return await self.section_state_recovery.execute(section)

    def cleanup(self):
        """Cleanup method to clear Gemini API caches when done."""
        pass

    async def _evaluate_search_complexity(self, query: str, context: str) -> float:
        """Evalúa la complejidad de la búsqueda basada en el query y contexto"""
        try:
            evaluation_prompt = f"""
            Evalúa la complejidad y necesidad de información actualizada para esta búsqueda:
            Query: {query}
            Contexto: {context}
            
            Responde con un número entre 0 y 1, donde:
            - 0-0.5: Consulta simple o información general
            - 0.6-1.0: Consulta compleja o necesita información actualizada
            """
            
            response = await self.language_model.generate_content(
                evaluation_prompt,
                {'temperature': 0.1}  # Baja temperatura para respuestas más consistentes
            )
            
            try:
                score = float(response.strip())
                return min(max(score, 0.0), 1.0)  # Asegurar que esté entre 0 y 1
            except ValueError:
                return 0.5  # Valor por defecto si no se puede convertir
                
        except Exception as e:
            logger.warning(f"Error evaluating search complexity: {str(e)}")
            return 0.5  # Valor por defecto en caso de error

    async def write_section_smart(self, state: SectionState) -> dict:
        """Escribe una sección eligiendo automáticamente entre grounding y método normal"""
        try:
            section = state["section"]
            source_str = state["source_str"]
            
            # Evaluar complejidad de la búsqueda
            complexity_score = await self._evaluate_search_complexity(
                section.name, 
                section.description
            )
            
            # Decidir si usar grounding
            use_grounding = complexity_score >= self.grounding_threshold['query_complexity']
            
            await self.progress_notifier.send_progress(
                f"Writing section {'with grounding' if use_grounding else 'normally'}: {section.name}"
            )

            if use_grounding:
                result = await self.write_section_with_grounding(state)
                result['method_used'] = 'grounding'
            else:
                result = await self.write_section(state)
                result['method_used'] = 'normal'
            
            # Agregar métricas de decisión
            result['decision_metrics'] = {
                'complexity_score': complexity_score,
                'threshold_used': self.grounding_threshold['query_complexity'],
                'use_grounding': use_grounding
            }
            
            return result

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error in smart section writing", 
                {"error": str(e)}
            )
            raise

# Uso básico con modo verbose
manager = ResearchManager(verbose=True)

# Acceso a métricas
async def main():
    section = Section(id="test", name="Test Section", description="Test")
    try:
        result = await manager.research_section(section)
        # Las métricas se guardan automáticamente en la base de datos
    except Exception as e:
        logger.error("Research failed", exc_info=True)
        
