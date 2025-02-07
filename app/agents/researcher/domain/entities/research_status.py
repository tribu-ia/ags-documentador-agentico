from enum import Enum

class ResearchStatus(Enum):
    """Estados posibles de una investigación"""
    NOT_STARTED = "not_started"
    GENERATING_QUERIES = "generating_queries"
    SEARCHING = "searching"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed" 