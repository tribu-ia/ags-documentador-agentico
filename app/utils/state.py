import operator
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Section(BaseModel):
    """Modelo para una sección de investigación"""

    id: str
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the report."
    )
    content: str = Field(description="The content of the section.")


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query for web search.")


class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class ReportState(TypedDict):
    assignment_id: str
    topic: str
    sections: list[Section]
    final_report: str
    completed_sections: Annotated[list, operator.add]  # Send() API key
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    websocket: Optional[
        object
    ]  # Agregamos websocket manteniendo la estructura TypedDict


class ResearchState(BaseModel):
    query: str
    documents: List[str] = []


class SectionState(TypedDict):
    section: Section  # Report section
    search_queries: list[SearchQuery]  # List of search queries
    source_str: str  # String of formatted source content from web search
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API


class SectionOutputState(TypedDict):
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API
