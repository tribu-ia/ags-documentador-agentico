from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agents.researcher import ResearchManager
from app.graph.builder.base import GraphBuilder
from app.utils.state import ReportState
from app.agents.planner import ReportPlanner
from app.agents.compiler import (
    ReportCompiler
)
from app.agents.writer import ReportWriter


class ReportGraphBuilder(GraphBuilder):
    """Constructor del grafo de reportes"""

    def __init__(self):
        super().__init__()
        self.researcher_graph = None
        self.planner = ReportPlanner()
        self.writer = ReportWriter()
        self.research_manager = ResearchManager()
        self.compiler = ReportCompiler()

    def init_graph(self) -> None:
        self.graph = StateGraph(ReportState)
        # Inicializa y compila el grafo de investigación
        from .researcher_builder import ResearcherGraphBuilder
        researcher_builder = ResearcherGraphBuilder()
        self.researcher_graph = researcher_builder.build().compile()

    def add_nodes(self) -> None:
        self.graph.add_node("plan", self.planner.plan_report)
        self.graph.add_node("research", self.researcher_graph)
        self.graph.add_node("gather_completed_sections", self.compiler.gather_completed_sections)
        self.graph.add_node("write_final_sections", self.compiler.write_final_sections)
        self.graph.add_node("compile_final_report", self.compiler.compile_final_report)

    def add_edges(self) -> None:
        self.graph.add_edge(START, "plan")
        self.graph.add_conditional_edges(
            "plan",
            ReportPlanner.initiate_section_writing,
            ["research"]
        )
        self.graph.add_edge("research", "gather_completed_sections")
        self.graph.add_conditional_edges(
            "gather_completed_sections",
            self.writer.initiate_final_section_writing,
            ["write_final_sections"]
        )
        self.graph.add_edge("write_final_sections", "compile_final_report")
        self.graph.add_edge("compile_final_report", END)
