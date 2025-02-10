import logging
from typing import List
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics

logger = logging.getLogger(__name__)

class WebSearchUseCase:
    def __init__(self, topic: str, days: int):
        self.topic = topic
        self.days = days

    @track_metrics
    async def search(self, queries: List[str]) -> str:
        """Perform web searches based on generated queries."""
        try:
            logger.debug(f"Starting web search with {len(queries)} queries")
            
            # Realizar búsquedas
            search_docs = await tavily_search_async(
                queries,
                self.topic,
                self.days
            )

            # Formatear y deduplicar resultados
            source_str = deduplicate_and_format_sources(
                search_docs,
                max_tokens_per_source=5000,
                include_raw_content=True
            )

            logger.debug("Web search completed successfully")
            return source_str

        except Exception as e:
            logger.error(f"Error during web search: {str(e)}")
            raise 