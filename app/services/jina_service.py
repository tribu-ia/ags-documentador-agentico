import logging
from typing import List, Dict
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
                    "query": query,
                    "top_k": 10,  # Número de resultados a retornar
                }
                
                async with session.post(
                    "https://api.jina.ai/v1/search",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        results.extend(result.get('data', []))
                    else:
                        logger.error(f"Jina API error: {response.status}")
                        
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