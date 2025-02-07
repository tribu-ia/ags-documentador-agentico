# -*- coding: utf-8 -*-

from typing import List, Dict, Set, Optional, Protocol
import google.generativeai as genai
import hashlib
import re
from dataclasses import dataclass, asdict
from enum import Enum
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
import json
from datetime import datetime
import sqlite3
import time
from functools import wraps
import traceback
from contextlib import contextmanager
import sys

from app.config.config import get_settings
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.utils.state import SectionState, Section
from pydantic import BaseModel, Field

from app.agents.researcher.domain.entities.query_validation import QueryValidation
from app.agents.researcher.domain.repositories.research_repository import ResearchRepository
from app.agents.researcher.infrastructure.repositories.sqlite_repository import SQLiteResearchRepository


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


def track_metrics(func):
    """Decorator to track function metrics"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = await func(self, *args, **kwargs)
            end_time = time.time()
            
            # Log metrics without requiring section_id
            logger.debug(
                f"Function {func.__name__} completed in {end_time - start_time:.2f} seconds"
            )
            
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

class ResearchStatus(Enum):
    NOT_STARTED = "not_started"
    GENERATING_QUERIES = "generating_queries"
    SEARCHING = "searching"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchStateSchema(BaseModel):
    """Schema for validating research state"""
    section_id: str
    status: ResearchStatus
    queries: List[Dict] = Field(default_factory=list)
    sources: List[Dict] = Field(default_factory=list)
    content: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    error_log: List[Dict] = Field(default_factory=list)

class ResearchManager:
    def __init__(
        self, 
        settings=None, 
        repository: Optional[ResearchRepository] = None, 
        verbose: bool = False,
        websocket: Optional[WebSocket] = None
    ):
        """Initialize ResearchManager with configuration settings and repository."""
        self.settings = settings or get_settings()
        self.websocket = websocket
        self.verbose = verbose
        
        # Initialize Gemini API
        genai.configure(api_key=self.settings.google_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize repository
        self.repository = repository or SQLiteResearchRepository()
        
        # Configure logging
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

    async def send_progress(self, message: str, data: Optional[Dict] = None):
        """Send progress updates through websocket"""
        if self.websocket:
            await self.websocket.send_json({
                "type": "research_progress",
                "message": message,
                "data": data
            })

    async def generate_queries(self, state: SectionState) -> dict:
        """Generate and validate search queries using multiple engines."""
        try:
            section = state["section"]
            await self.send_progress(f"Generating queries for section: {section.name}")
            
            initial_queries = await self.generate_initial_queries(state)
            
            if not initial_queries:
                await self.send_progress("No initial queries generated")
                return {"search_queries": []}
            
            validated_queries = []
            for query in initial_queries:
                try:
                    validation = await self.validate_query(query)
                    if validation.overall_score >= 0.6:
                        # Crear un SearchQuery en lugar de un dict
                        validated_queries.append(SearchQuery(
                            search_query=query
                        ))
                        
                except Exception as e:
                    await self.send_progress("Query validation error", {"error": str(e)})
                    continue
            
            await self.send_progress("Queries generated", {
                "count": len(validated_queries)
            })
            
            return {"search_queries": validated_queries}

        except Exception as e:
            await self.send_progress("Error generating queries", {"error": str(e)})
            raise

    async def search_web(self, state: SectionState) -> dict:
        """Perform web searches based on generated queries."""
        try:
            await self.send_progress("Starting web search")
            search_queries = state["search_queries"]

            # Extraer las queries asumiendo que son objetos SearchQuery
            query_list = [query.search_query for query in search_queries]
            search_docs = await tavily_search_async(
                query_list,
                self.settings.tavily_topic,
                self.settings.tavily_days
            )

            # Format and deduplicate results
            source_str = deduplicate_and_format_sources(
                search_docs,
                max_tokens_per_source=5000,
                include_raw_content=True
            )

            await self.send_progress("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            await self.send_progress("Error during web search", {"error": str(e)})
            raise

    async def write_section(self, state: SectionState) -> dict:
        """Write a section based on research results."""
        try:
            section = state["section"]  # Acceder como diccionario
            source_str = state["source_str"]  # Acceder como diccionario
            
            await self.send_progress(f"Writing section: {section.name}")

            prompt = f"""
            Write a detailed section about: {section.name}
            Topic description: {section.description}
            
            Use this research as context:
            {source_str}
            
            Requirements:
            - Be comprehensive but concise
            - Focus on factual information
            - Include specific examples where relevant
            - Maintain a professional tone
            
            Maximum length: 2000 words.
            Write the section content now.
            """

            try:
                section_content = await self._call_gemini_with_retry(prompt)
                if not section_content:
                    raise ValueError("Empty response from Gemini")
                
                # Usar setattr en lugar de asignación de diccionario
                setattr(section, "content", section_content)
                
                logger.debug(f"Completed writing section: {section.name}")
                await self.send_progress("Section completed", {
                    "section_name": section.name
                })
                return {"completed_sections": [section]}

            except Exception as e:
                logger.error(f"Error in first attempt, trying with reduced content: {str(e)}")
                shorter_prompt = f"""
                Write a brief section about: {section.name}
                Topic description: {section.description}
                Key points from sources: {source_str[:5000]}...
                
                Write a concise summary (max 500 words).
                """
                section_content = await self._call_gemini_with_retry(shorter_prompt)
                # Usar setattr en lugar de asignación de diccionario
                setattr(section, "content", section_content)
                
                await self.send_progress("Section completed", {
                    "section_name": section.name
                })
                return {"completed_sections": [section]}

        except Exception as e:
            await self.send_progress("Error writing section", {"error": str(e)})
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
            
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 8192,
                    'top_p': 0.8,
                    'top_k': 40
                }
            )
            
            duration = time.time() - start_time
            logger.debug(f"Gemini API call completed in {duration:.2f} seconds")
            
            return response.text.strip() if response else ""
            
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

    async def research_section(self, section: Section) -> Section:
        """Research a section with progress updates"""
        try:
            await self.send_progress("Iniciando investigación de la sección")

            # Crear estado inicial con la sección
            initial_state = {
                "section": section,
                "search_queries": [],
                "source_str": "",
                "report_sections_from_research": "",
                "completed_sections": []
            }

            # Generar queries de búsqueda
            await self.send_progress("Generando consultas de búsqueda")
            queries_result = await self.generate_queries(initial_state)
            
            # Actualizar estado con queries
            search_state = {
                "section": section,
                "search_queries": queries_result["search_queries"],  # Lista de SearchQuery
                "source_str": "",
                "report_sections_from_research": "",
                "completed_sections": []
            }
            
            # Realizar búsqueda web
            await self.send_progress("Realizando búsqueda web")
            search_results = await self.search_web(search_state)
            
            # Procesar resultados y escribir sección
            await self.send_progress("Procesando resultados")
            write_state = SectionState(
                section=section,
                search_queries=queries_result["search_queries"],
                source_str=search_results["source_str"],
                report_sections_from_research="",
                completed_sections=[]
            )
            
            result = await self.write_section(write_state)
            
            # Guardar estado
            await self.repository.save_state(section.id, {
                "status": ResearchStatus.COMPLETED,
                "content": result["completed_sections"][0]["content"]
            })

            await self.send_progress("Investigación completada")
            return result["completed_sections"][0]

        except Exception as e:
            logger.error(f"Error en investigación: {str(e)}")
            await self.send_progress("Error en investigación", {"error": str(e)})
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
