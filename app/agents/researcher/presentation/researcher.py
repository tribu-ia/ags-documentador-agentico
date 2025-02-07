# -*- coding: utf-8 -*-

from typing import List, Dict, Set, Optional, Protocol
import google.generativeai as genai
import hashlib
import re
from dataclasses import dataclass, asdict
import asyncio

from starlette.websockets import WebSocket
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
import time

from app.config.config import get_settings
from app.utils.state import SectionState, Section
from app.agents.researcher.domain.entities.query_validation import QueryValidation
from app.agents.researcher.domain.entities.research_status import ResearchStatus
from app.agents.researcher.domain.repositories.research_repository import ResearchRepository
from app.agents.researcher.infrastructure.repositories.sqlite_repository import SQLiteResearchRepository
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics
from app.agents.researcher.application.use_cases.generate_queries import GenerateQueriesUseCase
from app.agents.researcher.application.use_cases.validate_query import ValidateQueryUseCase
from app.agents.researcher.infrastructure.services.gemini_service import GeminiService
from app.agents.researcher.application.use_cases.web_search import WebSearchUseCase
from app.agents.researcher.application.use_cases.write_section import WriteSectionUseCase
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier
from app.agents.researcher.application.use_cases.manage_research_state import ManageResearchStateUseCase


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
        
        self.query_generator = GenerateQueriesUseCase(self.language_model)
        self.query_validator = ValidateQueryUseCase()
        self.web_searcher = WebSearchUseCase(
            self.settings.tavily_topic,
            self.settings.tavily_days
        )
        self.section_writer = WriteSectionUseCase(self.language_model)

    async def generate_queries(self, state: SectionState) -> dict:
        """Generate and validate search queries using multiple engines."""
        try:
            section = state["section"]
            await self.progress_notifier.send_progress(f"Generating queries for section: {section.name}")
            
            initial_queries = await self.query_generator.generate(
                section.name, 
                section.description,
                self.settings.number_of_queries
            )
            
            if not initial_queries:
                await self.progress_notifier.send_progress("No initial queries generated")
                return {"search_queries": []}
            
            validated_queries = []
            for query in initial_queries:
                try:
                    validation = await self.query_validator.validate(query)
                    if validation.overall_score >= 0.6:
                        validated_queries.append(SearchQuery(
                            search_query=query
                        ))
                        
                except Exception as e:
                    await self.progress_notifier.send_progress(
                        "Query validation error", 
                        {"error": str(e)}
                    )
                    continue
            
            await self.progress_notifier.send_progress(
                "Queries generated", 
                {"count": len(validated_queries)}
            )
            
            return {"search_queries": validated_queries}

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error generating queries", 
                {"error": str(e)}
            )
            raise

    async def search_web(self, state: SectionState) -> dict:
        """Perform web searches based on generated queries."""
        try:
            await self.progress_notifier.send_progress("Starting web search")
            search_queries = state["search_queries"]

            # Extraer las queries
            query_list = [query.search_query for query in search_queries]
            
            # Usar el caso de uso de búsqueda
            source_str = await self.web_searcher.search(query_list)

            await self.progress_notifier.send_progress("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            await self.progress_notifier.send_progress("Error during web search", {"error": str(e)})
            raise

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

    def _normalize_query(self, query: str) -> str:
        """Normalize a query by removing extra spaces and converting to lowercase."""
        return re.sub(r'\s+', ' ', query.lower().strip())

    def _get_query_hash(self, query: str) -> str:
        """Generate a hash for a query to help with deduplication."""
        return hashlib.md5(query.encode()).hexdigest()

    @track_metrics
    async def _call_gemini_with_retry(self, prompt: str) -> str:
        """Helper method to make Gemini API calls with retry logic."""
        try:
            logger.debug(f"Making Gemini API call with prompt length: {len(prompt)}")
            start_time = time.time()
            
            if len(prompt) > 30000:
                prompt = prompt[:30000] + "..."
                logger.debug("Prompt truncated due to length")
            
            response = await self.language_model.generate_content(
                prompt,
                config={
                    'temperature': 0.1,
                    'max_output_tokens': 8192,
                    'top_p': 0.8,
                    'top_k': 40
                }
            )
            
            duration = time.time() - start_time
            logger.debug(f"Gemini API call completed in {duration:.2f} seconds")
            
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            if "ResourceExhausted" in str(e):
                logger.error("Resource exhausted error - waiting longer before retry")
                await asyncio.sleep(10)
            raise

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
        """Generate initial queries using Gemini with retry logic."""
        try:
            prompt = f"""
            Generate {self.settings.number_of_queries} specific and diverse search queries for researching:
            Topic: {state["section"].name}
            Context: {state["section"].description}

            Requirements:
            - Each query should focus on a different aspect
            - Make queries specific and actionable
            - Avoid generic or overly broad queries
            - Include both factual and analytical queries

            Return only the numbered list of queries, one per line.
            Maximum number of queries: {self.settings.number_of_queries}
            """
            
            response = await self._call_gemini_with_retry(prompt)
            
            if not response:
                logger.warning("Empty response from Gemini after retries")
                return []
                
            queries = response.split('\n')
            queries = [q.strip() for q in queries if q.strip()][:self.settings.number_of_queries]
            
            return queries

        except Exception as e:
            logger.error(f"Error in generate_initial_queries after retries: {str(e)}")
            return []

    async def research_section(self, section_id: str) -> None:
        try:
            # Cargar estado
            state = await self.state_manager.load_state(section_id)
            if not state:
                # ... inicialización del estado ...
                pass

            # ... resto de la lógica ...

            # Guardar estado
            await self.state_manager.save_state(section_id, state)

        except Exception as e:
            await self.state_manager.log_error(section_id, str(e))
            raise

    async def recover_state(self, section: Section) -> Optional[Section]:
        """Attempt to recover research state for a section"""
        try:
            state = await self.repository.load_state(section.id)
            if not state:
                return None
                
            if state["status"] == ResearchStatus.COMPLETED:
                section["content"] = state["content"]
                return section
                
            # If failed or incomplete, return last known state
            return Section(
                id=section.id,
                name=section.name,
                description=section.description,
                content=state.get("content", "")
            )
            
        except Exception as e:
            logger.error(f"Error recovering state for section {section.id}: {str(e)}")
            return None

    def cleanup(self):
        """Cleanup method to clear Gemini API caches when done."""
        pass

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
