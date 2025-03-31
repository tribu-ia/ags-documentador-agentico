from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.graph.builder.base import GraphBuilder
from app.utils.state import TrendResearchState
from app.agents.trend_agents.planner import TrendResearchPlanner
from app.agents.trend_agents.compiler import TrendAnalysisCompiler
from app.agents.researcher import ResearchManager
import logging

logger = logging.basicConfig(level=logging.DEBUG)

class TrendResearchGraphBuilder(GraphBuilder):
    """Constructor del grafo para investigación de tendencias de productos"""

    def __init__(self, websocket=None):
        super().__init__()
        self.websocket = websocket
        self.researcher_graph = None
        self.planner = TrendResearchPlanner(websocket=websocket)
        self.compiler = TrendAnalysisCompiler(websocket=websocket)
        self.research_manager = ResearchManager(websocket=websocket)

    def build(self) -> StateGraph:
        """Construye y retorna el grafo de estados"""
        # Inicializar el grafo
        self.init_graph()
        
        # Agregar nodos y edges
        self.add_nodes()
        self.add_edges()
        
        return self.graph

    def init_graph(self) -> None:
        """Inicializa el grafo y sus componentes"""
        self.graph = StateGraph(TrendResearchState)
        # Inicializar el grafo del investigador si es necesario
        from app.graph.researcher_builder import ResearcherGraphBuilder
        researcher_builder = ResearcherGraphBuilder(websocket=self.websocket)
        self.researcher_graph = researcher_builder.build().compile()

    def add_nodes(self) -> None:
        """Agrega los nodos al grafo"""
        self.graph.add_node("plan_research", self.planner.plan_product_research)
        self.graph.add_node("search_trends", self.researcher_graph)
        self.graph.add_node("gather_trend_data", self.compiler.gather_trend_data)
        self.graph.add_node("analyze_opportunities", self.compiler.analyze_opportunities)
        self.graph.add_node("compile_trend_report", self.compiler.compile_trend_report)

    def add_edges(self) -> None:
        """Configura las conexiones entre nodos"""
        # 1. Inicio -> Plan de investigación
        self.graph.add_edge(START, "plan_research")
        
        # 2. Plan -> Búsqueda de tendencias
        self.graph.add_conditional_edges(
            "plan_research",
            TrendResearchPlanner.initiate_trend_research,
            ["search_trends"]
        )

        # 3. Búsqueda -> Recopilación de datos
        self.graph.add_edge("search_trends", "gather_trend_data")
        
        # 4. Recopilación -> Análisis de oportunidades
        self.graph.add_edge("gather_trend_data", "analyze_opportunities")

        # 5. Análisis -> Compilación del reporte
        self.graph.add_edge("analyze_opportunities", "compile_trend_report")
        
        # 6. Compilación -> Fin
        self.graph.add_edge("compile_trend_report", END) 