from abc import ABC, abstractmethod
from typing import Dict, Optional

class SearchProvider:
    @abstractmethod
    async def search(self, query: str) -> Optional[str]:
        """Execute search and return results"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Provider priority (lower is higher priority)"""
        pass 