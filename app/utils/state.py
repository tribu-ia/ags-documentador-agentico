from pydantic import BaseModel
from typing import List, Optional


class Section(BaseModel):
    name: str
    description: str
    research: bool
    content: Optional[str] = ""


class ReportState(BaseModel):
    topic: str
    sections: List[Section] = []
    final_report: Optional[str] = ""


class ResearchState(BaseModel):
    query: str
    documents: List[str] = []
