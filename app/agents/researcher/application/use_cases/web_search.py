import logging
from typing import List, Dict
from app.services.jina_service import jina_search_async, deduplicate_and_format_sources
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics
from app.config.config import get_settings

logger = logging.getLogger(__name__)

class WebSearchUseCase:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.settings = get_settings()

    @track_metrics
    async def search(self, queries: List[str]) -> str:
        """Perform web searches based on generated queries."""
        try:
            logger.debug(f"Starting Jina web search with {len(queries)} queries")
            
            # Realizar búsquedas
            search_docs = await jina_search_async(
                queries,
                self.api_key
            )

            # Formatear y deduplicar resultados
            source_str = deduplicate_and_format_sources(
                search_docs,
                max_tokens_per_source=5000
            )

            logger.debug("Jina web search completed successfully")
            return source_str

        except Exception as e:
            logger.error(f"Error during Jina web search: {str(e)}")
            raise 