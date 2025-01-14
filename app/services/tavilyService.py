import asyncio
from typing import List, Optional
from tavily import AsyncTavilyClient

from app.config.config import get_settings

settings = get_settings()
tavily_async_client = AsyncTavilyClient(api_key=settings.tavily_api_key)


async def tavily_search_async(
        search_queries: List[str],
        topic: str = "general",
        days: Optional[int] = None
):
    """Perform parallel web searches using Tavily API"""
    search_tasks = []

    for query in search_queries:
        search_params = {
            "query": query,
            "max_results": 5,
            "include_raw_content": True,
            "topic": topic
        }

        if topic == "news" and days is not None:
            search_params["days"] = days

        # Use the async client's search method
        search_tasks.append(
            tavily_async_client.search(**search_params)
        )

    # Now gather will work correctly with the coroutines
    return await asyncio.gather(*search_tasks)


def deduplicate_and_format_sources(search_response, max_tokens_per_source, include_raw_content=True):
    """Format and deduplicate search results"""
    # Convert to list of results
    if isinstance(search_response, dict):
        sources_list = search_response['results']
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and 'results' in response:
                sources_list.extend(response['results'])
            else:
                sources_list.extend(response)

    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source['url'] not in unique_sources:
            unique_sources[source['url']] = source

    # Format output
    formatted_text = "Sources:\n\n"
    for source in unique_sources.values():
        formatted_text += f"Source {source['title']}:\n"
        formatted_text += f"URL: {source['url']}\n"
        formatted_text += f"Content: {source['content']}\n\n"

        if include_raw_content:
            raw_content = source.get('raw_content', '')
            if raw_content:
                char_limit = max_tokens_per_source * 4
                if len(raw_content) > char_limit:
                    raw_content = raw_content[:char_limit] + "..."
                formatted_text += f"Full content: {raw_content}\n\n"

    return formatted_text.strip()