from langgraph.graph import StateGraph

from app.graph.report_builder import ReportGraphBuilder
from app.graph.researcher_builder import ResearcherGraphBuilder
from app.graph.trend_research_builder import TrendResearchGraphBuilder


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
    
    @staticmethod
    def construct_trend_research_graph(websocket=None) -> StateGraph:
        """Construye y retorna el grafo para investigación de tendencias"""
        builder = TrendResearchGraphBuilder(websocket=websocket)
        return builder.build()
