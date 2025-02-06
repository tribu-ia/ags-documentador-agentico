from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from .entities import Section, MetricsData

class ResearchRepository(ABC):
    @abstractmethod
    async def save_state(self, section_id: str, state: Dict) -> None:
        pass

    @abstractmethod
    async def load_state(self, section_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def log_error(self, section_id: str, error_message: str) -> None:
        pass

    @abstractmethod
    async def save_metrics(self, metrics: Dict) -> None:
        pass

class WebSocketNotifier(ABC):
    @abstractmethod
    async def send_progress(self, message: str, data: Optional[Dict] = None) -> None:
        pass 