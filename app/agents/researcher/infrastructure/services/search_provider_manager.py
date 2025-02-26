import logging
import asyncio
from typing import List, Optional, Dict
from app.agents.researcher.domain.interfaces.search_provider import SearchProvider

logger = logging.getLogger(__name__)

class SearchProviderManager:
    def __init__(self, timeout: int = 30):
        self._providers: List[SearchProvider] = []
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(3)  # Límite de búsquedas concurrentes

    def register_provider(self, provider: SearchProvider) -> None:
        """Registra un nuevo proveedor de búsqueda"""
        self._providers.append(provider)
        # Ordenar por prioridad
        self._providers.sort(key=lambda x: x.priority)

    async def search(self, query: str) -> Optional[str]:
        """Ejecuta la búsqueda usando los proveedores disponibles"""
        async with self._semaphore:
            for provider in self._providers:
                try:
                    logger.debug(f"Attempting search with provider: {provider.name}")
                    async with asyncio.timeout(self._timeout):
                        result = await provider.search(query)
                        if result:
                            logger.debug(f"Search successful with provider: {provider.name}")
                            return result
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout with provider: {provider.name}")
                    continue
                except Exception as e:
                    logger.error(f"Error with provider {provider.name}: {str(e)}")
                    continue

        logger.warning("All search providers failed")
        return None

    def get_provider_status(self) -> Dict[str, bool]:
        """Retorna el estado actual de los proveedores"""
        return {provider.name: True for provider in self._providers} 