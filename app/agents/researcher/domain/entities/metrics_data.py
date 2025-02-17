from dataclasses import dataclass
from typing import List, Dict
import time


@dataclass
class MetricsData:
    """Structure to store performance metrics"""
    start_time: float
    end_time: float = 0
    tokens_used: int = 0
    api_calls: int = 0
    errors: List[Dict] = None

    def __post_init__(self):
        self.errors = self.errors or []

    @property
    def duration(self) -> float:
        """Calculate duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary"""
        return {
            'duration_seconds': self.duration,
            'tokens_used': self.tokens_used,
            'api_calls': self.api_calls,
            'errors': self.errors
        }
