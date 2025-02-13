import asyncio
from dataclasses import dataclass
from functools import partial
from typing import Dict, List
import logging

import aiohttp
from pybreaker import CircuitBreaker
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.utils.state import SectionState
from app.agents.researcher.application.use_cases.web_search import WebSearchUseCase
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier

# Configuración del logger
logger = logging.getLogger(__name__)

class SearchWebQueriesUseCase:
    def __init__(self, web_searcher: WebSearchUseCase, progress_notifier: ProgressNotifier):
        self.web_searcher = web_searcher
        self.progress_notifier = progress_notifier
        self.settings = web_searcher.settings  # Access settings through web_searcher

        
        # Configuraciones de resiliencia
        self.search_semaphore = asyncio.Semaphore(3)
        self.timeout_config = {'search': 30, 'default': 20}
        self.fallback_services = [
            self._search_with_tavily, # API de Búsqueda Web principal
            self._search_with_serp, # API de Búsqueda Web primer Respaldo
            self._search_with_duckduckgo # API de Búsqueda Web Segundo Respaldo
        ]

    async def execute(self, state: SectionState) -> Dict:
        """Perform web searches based on generated queries."""
        try:
            await self.progress_notifier.send_progress("Starting web search")
            search_queries = state["search_queries"]

            # Extraer las queries
            query_list = [query.search_query for query in search_queries]
            
            # Realizar búsquedas con resiliencia
            source_str = ""
            for query in query_list:
                search_success = False
                for search_service in self.fallback_services:
                    try:
                        result = await self._execute_with_bulkhead(
                            partial(self._search_with_timeout, search_service),
                            query
                        )
                        if result:
                            source_str += f"\n{result}"
                            search_success = True
                            break
                    except Exception as e:
                        logger.error(f"Error with {search_service.__name__}: {str(e)}")
                        continue
                
                if not search_success:
                    logger.warning(f"All search services failed for query: {query}")

            await self.progress_notifier.send_progress("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error during web search",
                {"error": str(e)}
            )
            raise

    async def _search_with_tavily(self, query: str) -> str:
        """Búsqueda principal usando Tavily"""
        return await self.web_searcher.search(query)

    async def _search_with_serp(self, query: str) -> str:
        """Servicio de búsqueda alternativo usando SERP API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'api_key': self.settings.serp_api_key,
                    'q': query,
                    'num': 10
                }
                async with session.get('https://serpapi.com/search', params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('organic_results', [])
                        return "\n".join(
                            f"{result.get('title', '')}\n{result.get('snippet', '')}"
                            for result in results
                        )
            return ""
        except Exception as e:
            logger.error(f"SERP API search failed: {str(e)}")
            raise

    async def _search_with_duckduckgo(self, query: str) -> str:
        """Servicio de búsqueda alternativo usando DuckDuckGo"""
        try:
            from duckduckgo_search import AsyncDDGS
            
            ddgs = AsyncDDGS()
            results = await ddgs.text(query, max_results=10)
            
            return "\n".join(
                f"{result.get('title', '')}\n{result.get('body', '')}"
                for result in results
            )
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            raise

    async def _search_with_timeout(self, search_func, *args, timeout=None):
        try:
            timeout = timeout or self.timeout_config['default']
            async with asyncio.timeout(timeout):
                return await search_func(*args)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout executing {search_func.__name__}")
            raise

    async def _execute_with_bulkhead(self, search_func, *args):
        async with self.search_semaphore:
            return await search_func(*args)