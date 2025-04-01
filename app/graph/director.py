from langgraph.graph import StateGraph

from app.graph.report_builder import ReportGraphBuilder
from app.graph.researcher_builder import ResearcherGraphBuilder


class GraphDirector:
    """Director que maneja la construcción y ejecución de grafos"""

    @staticmethod
    def construct_researcher_graph(websocket=None) -> StateGraph:
        builder = ResearcherGraphBuilder(websocket=websocket)
        return builder.build()

    @staticmethod
    def construct_report_graph(websocket=None) -> StateGraph:
        builder = ReportGraphBuilder(websocket=websocket)
        return builder.build()
