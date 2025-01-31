from langgraph.graph import StateGraph

from app.graph.report_builder import ReportGraphBuilder
from app.graph.researcher_builder import ResearcherGraphBuilder


class GraphDirector:
    """Director que maneja la construcción de grafos"""

    @staticmethod
    def construct_researcher_graph() -> StateGraph:
        builder = ResearcherGraphBuilder()
        return builder.build()

    @staticmethod
    def construct_report_graph() -> StateGraph:
        builder = ReportGraphBuilder()
        return builder.build()
