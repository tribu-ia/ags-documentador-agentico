from app.config.config import get_settings
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.utils.state import SectionState
from langchain_core.runnables import RunnableConfig


async def search_web(state: SectionState, config: RunnableConfig):
    """ Search the web for each query, then return a list of raw sources and a formatted string of sources."""

    # Get state
    settings = get_settings()

    # Extract queries
    query_list = [query.search_query for query in state.queries]

    # Perform searches
    search_results = await tavily_search_async(
        query_list,
        state.topic,
        state.days
    )

    # Format results
    formatted_results = deduplicate_and_format_sources(
        search_results,
        max_tokens_per_source=5000,
        include_raw_content=True
    )

    return {"source_str": source_str}
