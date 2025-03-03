import asyncio
import logging
from typing import Dict, List

import aiohttp

logger = logging.getLogger(__name__)

async def jina_search_async(queries: List[str], api_key: str) -> List[Dict]:
    """Perform web searches using Jina API."""
    results = []
    
    async with aiohttp.ClientSession() as session:
        for query in queries:
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "jina-deepsearch-v1",
                    "messages": [
                        {
                            "role": "user",
                            "content": query
                        }
                    ],
                    "stream": False,
                    "reasoning_effort": "low"
                }
                
                async with session.post(
                    "https://deepsearch.jina.ai/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return "\n".join(
                            [f"{data}\n{source}" for data, source in zip(result["choices"], result["readURLs"])]
                        )

                    else:
                        logger.error(f"Jina API error: {response.status}")
            except asyncio.TimeoutError:
                logger.error(f"Request timed out for query: {query}")
         
            except Exception as e:
                logger.error(f"Error in Jina search: {str(e)}")
                continue
                
    return results

def deduplicate_and_format_sources(search_results: List[Dict], max_tokens_per_source: int = 5000) -> str:
    """Format and deduplicate search results."""
    seen_urls = set()
    formatted_sources = []
    
    for result in search_results:
        url = result.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            formatted_source = f"""
            Title: {title}
            URL: {url}
            Content: {snippet}
            ---
            """
            
            formatted_sources.append(formatted_source)
            
    return "\n".join(formatted_sources) 