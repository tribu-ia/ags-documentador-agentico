from dataclasses import dataclass
from typing import Dict, List

from app.utils.state import SectionState
from app.agents.researcher.application.use_cases.web_search import WebSearchUseCase
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier

@dataclass
class SearchWebQueriesUseCase:
    web_searcher: WebSearchUseCase
    progress_notifier: ProgressNotifier

    async def execute(self, state: SectionState) -> Dict:
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