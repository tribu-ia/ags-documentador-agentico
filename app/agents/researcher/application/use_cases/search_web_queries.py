import asyncio
import logging
from functools import partial
from typing import Dict

import aiohttp
from duckduckgo_search import DDGS

from app.agents.researcher.application.use_cases.web_search import WebSearchUseCase
from app.agents.researcher.infrastructure.services.gemini_service import GeminiService
from app.agents.researcher.infrastructure.services.progress_notifier import (
    ProgressNotifier,
)
from app.agents.researcher.infrastructure.services.search_complexity_evaluator import (
    SearchComplexityEvaluator,
)
from app.agents.researcher.infrastructure.services.search_provider_manager import (
    SearchProviderManager,
)
from app.agents.researcher.infrastructure.services.search_providers import (
    DuckDuckGoProvider,
    GeminiGroundingProvider,
    GeminiNormalProvider,
    JinaProvider,
    SerpProvider,
)
from app.config.config import get_settings
from app.utils.state import SectionState

# Configuración del logger
logger = logging.getLogger(__name__)


class SearchWebQueriesUseCase:
    def __init__(
        self,
        web_searcher: WebSearchUseCase,
        progress_notifier: ProgressNotifier,
        complexity_evaluator: SearchComplexityEvaluator,
    ):
        self.web_searcher = web_searcher
        self.progress_notifier = progress_notifier
        self.complexity_evaluator = complexity_evaluator
        self.settings = get_settings()

        # Inicializar GeminiService para búsquedas avanzadas
        self.gemini_service = GeminiService(self.settings.google_api_key)

        # Configuraciones de resiliencia
        self.search_semaphore = asyncio.Semaphore(3)
        self.timeout_config = {"search": 30, "default": 20}
        self.fallback_services = [
            self._search_with_jina,  # API de Búsqueda Web principal (Jina)
            self._search_with_serp,  # API de Búsqueda Web primer Respaldo
            self._search_with_duckduckgo,  # API de Búsqueda Web Segundo Respaldo
        ]

        # Nuevo sistema de proveedores
        self.provider_manager = SearchProviderManager(
            timeout=self.timeout_config["search"]
        )

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
        self.provider_manager.register_provider(DuckDuckGoProvider())

    async def execute(self, state: SectionState) -> Dict:
        """Perform web searches based on generated queries."""
        try:
            await self.progress_notifier.send_progress("Starting web search")
            search_queries = state["search_queries"]
            query_list = [query.search_query for query in search_queries]
            # Calcular la complejidad de cada query
            for query in query_list:
                print(
                    f"Evaluating complexity {query} in search_web_queries in execute to search_web_queries"
                )
                complexity_score = await self.complexity_evaluator.evaluate(query)

                # Intentar primero con el nuevo sistema de proveedores
                source_str = ""
                try:
                    # Usar Gemini para queries complejas
                    if complexity_score >= 0.7:
                        result = await self._search_with_gemini_grounding(query)
                    else:
                        result = await self._search_with_gemini_flash(query)

                    if result:
                        source_str += f"\n{result}"
                        continue

                    # Fallback al sistema original si Gemini falla
                    for search_service in self.fallback_services:
                        try:
                            result = await self._execute_with_bulkhead(
                                partial(self._search_with_timeout, search_service),
                                query,
                            )
                            if result:
                                source_str += f"\n{result}"
                                break
                        except Exception as e:
                            logger.error(f"Search service failed: {str(e)}")
                            continue

                except Exception as e:
                    logger.error(f"Search failed for query {query}: {str(e)}")
                    continue

            await self.progress_notifier.send_progress("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error during web search", {"error": str(e)}
            )
            raise

    async def _search_with_gemini_grounding(self, query: str) -> str:
        """Búsqueda usando Gemini con grounding para queries complejas"""
        try:
            prompt = f"""
            Realiza una búsqueda profunda y detallada sobre:
            {query}
            
            Proporciona información precisa y actualizada, citando fuentes cuando sea posible.
            """
            response = await self.gemini_service.generate_content(
                prompt, {"temperature": 0.3, "top_k": 40, "top_p": 0.95}
            )
            return response
        except Exception as e:
            logger.error(f"Gemini grounding search failed: {str(e)}")
            return ""

    async def _search_with_gemini_flash(self, query: str) -> str:
        """Búsqueda usando gemini-1.5-flash para queries simples"""
        try:
            prompt = f"""
            Busca información concisa sobre:
            {query}
            """
            response = await self.gemini_service.generate_content(
                prompt, {"temperature": 0.7, "top_k": 20, "top_p": 0.8}
            )
            return response
        except Exception as e:
            logger.error(f"Gemini flash search failed: {str(e)}")
            return ""

    async def _search_with_jina(self, query: str) -> str:
        """Búsqueda principal usando Jina"""
        return await self.web_searcher.search([query])

    async def _search_with_serp(self, query: str) -> str:
        """Servicio de búsqueda alternativo usando SERP API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-KEY": self.settings.serp_api_key,
                    "Content-Type": "application/json",
                }
                data = {
                    "q": query.replace('"', "").replace("'", ""),
                    "num": 10,
                    "hl": "es",  # Buscar en español
                    "tbs": "qdr:m",  # Traer los resultados del ultimo mes
                }
                async with session.post(
                    "https://google.serper.dev/search", headers=headers, json=data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("organic", [])
                        return "\n".join(
                            f"{results.get('title', '')}\n{results.get('snippet', '')}\n{results.get('link', '')}"
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
                query.replace("'", "").replace('"', ""),
                region="wt-wt",
                safesearch="off",
                max_results=10,
            )

            return "\n".join(
                f"{result.get('title', '')}\n{result.get('body', '')}\n{result.get('href', '')}"
                for result in results
            )

        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            raise

    async def _search_with_timeout(self, search_func, *args, timeout=None):
        try:
            timeout = timeout or self.timeout_config["default"]
            async with asyncio.timeout(timeout):
                return await search_func(*args)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout executing {search_func.__name__}")
            raise

    async def _execute_with_bulkhead(self, search_func, *args):
        async with self.search_semaphore:
            return await search_func(*args)
