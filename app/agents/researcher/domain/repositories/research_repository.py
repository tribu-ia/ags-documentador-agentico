from typing import Dict, Optional, Protocol

class ResearchRepository(Protocol):
    """Interface for research state persistence"""
    async def save_state(self, section_id: str, state: Dict) -> None:
        """Save research state"""
        pass

    async def load_state(self, section_id: str) -> Optional[Dict]:
        """Load research state"""
        pass

    async def log_error(self, section_id: str, error_message: str) -> None:
        """Log error message"""
        pass

    async def save_metrics(self, metrics: Dict) -> None:
        """Save performance metrics"""
        pass 