from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class ResearchStatus(Enum):
    NOT_STARTED = "not_started"
    GENERATING_QUERIES = "generating_queries"
    SEARCHING = "searching"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"

class SearchEngine(Enum):
    TAVILY = "tavily"
    GEMINI = "gemini"
    DEEP_RESEARCH = "deep_research"


@dataclass
class Section:
    id: str
    name: str
    description: str
    content: Optional[str] = None


@dataclass
class SearchQuery:
    search_query: str


@dataclass
class QueryValidation:
    specificity: float
    relevance: float
    clarity: float
    
    @property
    def overall_score(self) -> float:
        return (self.specificity + self.relevance + self.clarity) / 3


@dataclass
class MetricsData:
    start_time: float
    end_time: float = 0
    tokens_used: int = 0
    api_calls: int = 0
    errors: List[Dict] = None

    def __post_init__(self):
        self.errors = self.errors or []

    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> Dict:
        return {
            'duration_seconds': self.duration,
            'tokens_used': self.tokens_used,
            'api_calls': self.api_calls,
            'errors': self.errors
        }
