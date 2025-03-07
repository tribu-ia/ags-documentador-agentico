import logging
import aiohttp
from typing import Optional, Dict
from duckduckgo_search import DDGS

from app.agents.researcher.domain.interfaces.search_provider import SearchProvider
from app.agents.researcher.infrastructure.services.gemini_service import GeminiService
from app.config.config import get_settings

logger = logging.getLogger(__name__)

class GeminiGroundingProvider(SearchProvider):
    def __init__(self, gemini_service: GeminiService, config: Dict = None):
        self._gemini = gemini_service
        self._config = config or {
            'temperature': 0.7,
            'candidate_count': 1,
            'top_k': 40,
            'top_p': 0.95,
        }

    async def search(self, query: str) -> Optional[str]:
        try:
            result = await self._gemini.generate_grounded_content(query, self._config)
            return result.get('content')
        except Exception as e:
            logger.error(f"Gemini grounding search failed: {str(e)}")
            return None

    @property
    def name(self) -> str:
        return "gemini_grounding"

    @property
    def priority(self) -> int:
        return 1

class GeminiNormalProvider(SearchProvider):
    def __init__(self, gemini_service: GeminiService):
        self._gemini = gemini_service

    async def search(self, query: str) -> Optional[str]:
        try:
            return await self._gemini.generate_content(query)
        except Exception as e:
            logger.error(f"Gemini normal search failed: {str(e)}")
            return None

    @property
    def name(self) -> str:
        return "gemini_normal"

    @property
    def priority(self) -> int:
        return 2

class JinaProvider(SearchProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str) -> Optional[str]:
        try:
            from app.services.jina_service import jina_search_async, deduplicate_and_format_sources
            results = await jina_search_async([query], self._api_key)
            return deduplicate_and_format_sources(results, max_tokens_per_source=5000)
        except Exception as e:
            logger.error(f"Jina search failed: {str(e)}")
            return None

    @property
    def name(self) -> str:
        return "jina"

    @property
    def priority(self) -> int:
        return 3

class SerpProvider(SearchProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'api_key': self._api_key,
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
            return None
        except Exception as e:
            logger.error(f"SERP API search failed: {str(e)}")
            return None

    @property
    def name(self) -> str:
        return "serp"

    @property
    def priority(self) -> int:
        return 4

class DuckDuckGoProvider(SearchProvider):
    async def search(self, query: str) -> Optional[str]:
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
            return None

    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def priority(self) -> int:
        return 5 