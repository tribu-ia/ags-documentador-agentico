from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agents.researcher import ResearchManager
from app.graph.builder.base import GraphBuilder
from app.utils.state import CampaignState
from app.agents.planner import CampaignPlanner
from app.agents.compiler import (
    CampaignCompiler
)
from app.agents.writer import CampaignWriter

class CampaignGraphBuilder(GraphBuilder):
    """Constructor del grafo para campañas de marketing digital"""

    def __init__(self, websocket=None):
        super().__init__()
        self.websocket = websocket
        self.researcher_graph = None
        self.planner = CampaignPlanner(websocket=websocket)
        self.writer = CampaignWriter(websocket=websocket)
        self.research_manager = ResearchManager(websocket=websocket)
        self.compiler = CampaignCompiler(websocket=websocket)

    def add_nodes(self) -> None:
        self.graph.add_node("plan_campaign", self.planner.plan_campaign)
        self.graph.add_node("search_product_trends", self.researcher_graph)
        self.graph.add_node("generate_copy", self.compiler.generate_copy)
        self.graph.add_node("create_campaign_assets", self.compiler.create_campaign_assets)
        self.graph.add_node("compile_final_campaign", self.compiler.compile_final_campaign)

    def add_edges(self) -> None:
        # 1. Plan -> Search Product Trends
        self.graph.add_edge(START, "plan_campaign")
        self.graph.add_conditional_edges(
            "plan_campaign",
            CampaignPlanner.initiate_trend_research,
            ["search_product_trends"]
        )

        # 2. Research -> Generate Copy
        self.graph.add_edge("search_product_trends", "generate_copy")
        
        # 3. Copy -> Create Assets
        self.graph.add_edge("generate_copy", "create_campaign_assets")

        # 4. Assets -> Compile Campaign
        self.graph.add_edge("create_campaign_assets", "compile_final_campaign")
        self.graph.add_edge("compile_final_campaign", END) 