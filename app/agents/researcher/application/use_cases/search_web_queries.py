import asyncio
from dataclasses import dataclass
from functools import partial
from typing import Dict
import logging
import aiohttp
from duckduckgo_search import DDGS

from app.utils.state import SectionState
from app.agents.researcher.application.use_cases.web_search import WebSearchUseCase
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier
from app.agents.researcher.infrastructure.services.search_provider_manager import SearchProviderManager
from app.agents.researcher.infrastructure.services.search_providers import (
    GeminiGroundingProvider,
    GeminiNormalProvider,
    JinaProvider,
    SerpProvider,
    DuckDuckGoProvider
)
from app.agents.researcher.infrastructure.services.gemini_service import GeminiService
from app.config.config import get_settings

# Configuración del logger
logger = logging.getLogger(__name__)

class SearchWebQueriesUseCase:
    def __init__(self, web_searcher: WebSearchUseCase, progress_notifier: ProgressNotifier):
        self.web_searcher = web_searcher
        self.progress_notifier = progress_notifier
        self.settings = get_settings()  # Obtenemos settings directamente

        # Inicializar GeminiService
        self.gemini_service = GeminiService(self.settings.google_api_key)

        # Configuraciones de resiliencia
        self.search_semaphore = asyncio.Semaphore(3)
        self.timeout_config = {'search': 30, 'default': 20}
        self.fallback_services = [
            self._search_with_jina,     # API de Búsqueda Web principal (Jina)
            self._search_with_serp,     # API de Búsqueda Web primer Respaldo
            self._search_with_duckduckgo # API de Búsqueda Web Segundo Respaldo
        ]

        # Nuevo sistema de proveedores
        self.provider_manager = SearchProviderManager(timeout=self.timeout_config['search'])
        
        # Registrar proveedores en orden de prioridad
        self.provider_manager.register_provider(
            GeminiGroundingProvider(self.gemini_service)
        )
        self.provider_manager.register_provider(
            GeminiNormalProvider(self.gemini_service)
        )
        self.provider_manager.register_provider(
            JinaProvider(self.settings.jina_api_key)
        )
        self.provider_manager.register_provider(
            SerpProvider(self.settings.serp_api_key)
        )
        self.provider_manager.register_provider(
            DuckDuckGoProvider()
        )

    async def execute(self, state: SectionState) -> Dict:
        """Perform web searches based on generated queries."""
        try:
            await self.progress_notifier.send_progress("Starting web search")
            search_queries = state["search_queries"]
            query_list = [query.search_query for query in search_queries]
            
            # Intentar primero con el nuevo sistema de proveedores
            source_str = ""
            for query in query_list:
                try:
                    result = await self.provider_manager.search(query)
                    if result:
                        source_str += f"\n{result}"
                        continue

                    # Si el nuevo sistema falla, usar el sistema de fallback original
                    logger.debug("Provider manager failed, falling back to original system")
                    fallback_result = await self._execute_fallback_search(query)
                    if fallback_result:
                        source_str += f"\n{fallback_result}"
                        
                except Exception as e:
                    logger.error(f"Search failed for query {query}: {str(e)}")
                    continue

            await self.progress_notifier.send_progress("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error during web search",
                {"error": str(e)}
            )
            raise

    async def _execute_fallback_search(self, query: str) -> str:
        """Execute search using original fallback system"""
        search_success = False
        result = ""
        
        for search_service in self.fallback_services:
            try:
                result = await self._execute_with_bulkhead(
                    partial(self._search_with_timeout, search_service),
                    query
                )
                if result:
                    search_success = True
                    break
            except Exception as e:
                logger.error(f"Error with {search_service.__name__}: {str(e)}")
                continue
        
        if not search_success:
            logger.warning(f"All search services failed for query: {query}")
            
        return result

    async def _search_with_jina(self, query: str) -> str:
        """Búsqueda principal usando Jina"""
        return await self.web_searcher.search([query])

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
            ddgs = DDGS()
            results = ddgs.text(
                query, 
                region='wt-wt',
                safesearch='off',
                max_results=10
            )
            
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
