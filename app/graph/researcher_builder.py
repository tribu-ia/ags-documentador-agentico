from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agents.researcher import ResearchManager
from app.graph.builder.base import GraphBuilder
from app.utils.state import SectionState, SectionOutputState


class ResearcherGraphBuilder(GraphBuilder):
    """Constructor del grafo de investigación"""

    def __init__(self, websocket=None):
        super().__init__()
        self.research_manager = ResearchManager(websocket=websocket)

    def init_graph(self) -> None:
        self.graph = StateGraph(SectionState, output=SectionOutputState)

    def add_nodes(self) -> None:
        self.graph.add_node("generate_queries", self.research_manager.generate_queries)
        self.graph.add_node("search_web", self.research_manager.search_web)
        self.graph.add_node("write_section", self.research_manager.write_section)

    def add_edges(self) -> None:
        self.graph.add_edge(START, "generate_queries")
        self.graph.add_edge("generate_queries", "search_web")
        self.graph.add_edge("search_web", "write_section")
        self.graph.add_edge("write_section", END)
