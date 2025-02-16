import logging
import hashlib
import re
from typing import List, Dict, Optional
from functools import wraps
import time
import asyncio

from ..domain.entities import (
    Section, SearchQuery, QueryValidation, MetricsData, ResearchStatus
)
from ..domain.interfaces import ResearchRepository, WebSocketNotifier

logger = logging.getLogger(__name__)

def track_metrics(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = await func(self, *args, **kwargs)
            end_time = time.time()
            logger.debug(
                f"Function {func.__name__} completed in {end_time - start_time:.2f} seconds"
            )
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

class ResearchUseCase:
    def __init__(
        self,
        repository: ResearchRepository,
        gemini_service,
        tavily_service,
        notifier: WebSocketNotifier,
        settings: dict,
        verbose: bool = False
    ):
        self.repository = repository
        self.gemini_service = gemini_service
        self.tavily_service = tavily_service
        self.notifier = notifier
        self.settings = settings
        self.verbose = verbose

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

    async def research_section(self, section: Section) -> Section:
        try:
            await self.notifier.send_progress("Iniciando investigación de la sección")

            initial_state = {
                "section": section,
                "search_queries": [],
                "source_str": "",
                "report_sections_from_research": "",
                "completed_sections": []
            }

            await self.notifier.send_progress("Generando consultas de búsqueda")
            queries_result = await self.generate_queries(initial_state)
            
            search_state = {
                "section": section,
                "search_queries": queries_result["search_queries"],
                "source_str": "",
                "report_sections_from_research": "",
                "completed_sections": []
            }
            
            await self.notifier.send_progress("Realizando búsqueda web")
            search_results = await self.search_web(search_state)
            
            await self.notifier.send_progress("Procesando resultados")
            write_state = {
                "section": section,
                "search_queries": queries_result["search_queries"],
                "source_str": search_results["source_str"],
                "report_sections_from_research": "",
                "completed_sections": []
            }
            
            result = await self.write_section(write_state)
            
            await self.repository.save_state(section.id, {
                "status": ResearchStatus.COMPLETED,
                "content": result["completed_sections"][0].content
            })

            await self.notifier.send_progress("Investigación completada")
            return result["completed_sections"][0]

        except Exception as e:
            logger.error(f"Error en investigación: {str(e)}")
            await self.notifier.send_progress("Error en investigación", {"error": str(e)})
            raise

    async def generate_queries(self, state: dict) -> dict:
        try:
            section = state["section"]
            await self.notifier.send_progress(f"Generating queries for section: {section.name}")
            
            initial_queries = await self.generate_initial_queries(state)
            
            if not initial_queries:
                await self.notifier.send_progress("No initial queries generated")
                return {"search_queries": []}
            
            validated_queries = []
            for query in initial_queries:
                try:
                    validation = await self.validate_query(query)
                    if validation.overall_score >= 0.6:
                        validated_queries.append(SearchQuery(
                            search_query=query
                        ))
                        
                except Exception as e:
                    await self.notifier.send_progress("Query validation error", {"error": str(e)})
                    continue
            
            await self.notifier.send_progress("Queries generated", {
                "count": len(validated_queries)
            })
            
            return {"search_queries": validated_queries}

        except Exception as e:
            await self.notifier.send_progress("Error generating queries", {"error": str(e)})
            raise

    async def search_web(self, state: dict) -> dict:
        try:
            await self.notifier.send_progress("Starting web search")
            search_queries = state["search_queries"]

            query_list = [query.search_query for query in search_queries]
            search_docs = await self.tavily_service.search(
                query_list,
                self.settings.tavily_topic,
                self.settings.tavily_days
            )

            source_str = self.tavily_service.format_sources(search_docs)

            await self.notifier.send_progress("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            await self.notifier.send_progress("Error during web search", {"error": str(e)})
            raise

    @track_metrics
    async def write_section(self, state: dict) -> dict:
        try:
            section = state["section"]
            source_str = state["source_str"]
            
            await self.notifier.send_progress(f"Writing section: {section.name}")

            prompt = self._create_section_prompt(section, source_str)

            try:
                section_content = await self._call_gemini_with_retry(prompt)
                if not section_content:
                    raise ValueError("Empty response from Gemini")
                
                section.content = section_content
                
                logger.debug(f"Completed writing section: {section.name}")
                await self.notifier.send_progress("Section completed", {
                    "section_name": section.name
                })
                return {"completed_sections": [section]}

            except Exception as e:
                logger.error(f"Error in first attempt, trying with reduced content: {str(e)}")
                shorter_prompt = self._create_shorter_prompt(section, source_str)
                section_content = await self._call_gemini_with_retry(shorter_prompt)
                section.content = section_content
                
                await self.notifier.send_progress("Section completed", {
                    "section_name": section.name
                })
                return {"completed_sections": [section]}

        except Exception as e:
            await self.notifier.send_progress("Error writing section", {"error": str(e)})
            raise

    def _create_section_prompt(self, section: Section, source_str: str) -> str:
        return f"""
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

    def _create_shorter_prompt(self, section: Section, source_str: str) -> str:
        return f"""
        Write a brief section about: {section.name}
        Topic description: {section.description}
        Key points from sources: {source_str[:5000]}...
        
        Write a concise summary (max 500 words).
        """

    @track_metrics
    async def _call_gemini_with_retry(self, prompt: str) -> str:
        try:
            logger.debug(f"Making Gemini API call with prompt length: {len(prompt)}")
            start_time = time.time()
            
            if len(prompt) > 30000:
                prompt = prompt[:30000] + "..."
                logger.debug("Prompt truncated due to length")
            
            response = await self.gemini_service.generate_content(prompt)
            
            duration = time.time() - start_time
            logger.debug(f"Gemini API call completed in {duration:.2f} seconds")
            
            return response
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            if "ResourceExhausted" in str(e):
                logger.error("Resource exhausted error - waiting longer before retry")
                await asyncio.sleep(10)
            raise 