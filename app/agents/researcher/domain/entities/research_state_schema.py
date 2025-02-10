from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .research_status import ResearchStatus


class ResearchStateSchema(BaseModel):
    """Schema for validating research state"""
    section_id: str
    status: ResearchStatus
    queries: List[Dict] = Field(default_factory=list)
    sources: List[Dict] = Field(default_factory=list)
    content: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    error_log: List[Dict] = Field(default_factory=list) 