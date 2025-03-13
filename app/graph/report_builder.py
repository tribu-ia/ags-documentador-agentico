from langgraph.constants import END, START
from langgraph.graph import StateGraph

from app.agents.compiler import ReportCompiler
from app.agents.human_reviewer import HumanReviewer
from app.agents.planner import ReportPlanner
from app.agents.researcher import ResearchManager
from app.agents.writer import ReportWriter
from app.graph.builder.base import GraphBuilder
from app.utils.state import ReportState


class ReportGraphBuilder(GraphBuilder):
    """Constructor del grafo de reportes"""

    def __init__(self, websocket=None):
        super().__init__()
        self.websocket = websocket
        self.researcher_graph = None
        self.planner = ReportPlanner(websocket=websocket)
        self.writer = ReportWriter(websocket=websocket)
        self.research_manager = ResearchManager(websocket=websocket)
        self.compiler = ReportCompiler(websocket=websocket)
        self.human_reviewer = HumanReviewer(websocket=websocket)

    def build(self) -> StateGraph:
        """Construye y retorna el grafo de estados."""
        self.init_graph()
        self.add_nodes()
        self.add_edges()
        return self.graph

    def init_graph(self) -> None:
        self.graph = StateGraph(ReportState)
        from .researcher_builder import ResearcherGraphBuilder

        researcher_builder = ResearcherGraphBuilder(websocket=self.websocket)
        self.researcher_graph = researcher_builder.build().compile()

    def add_nodes(self) -> None:
        self.graph.add_node("plan", self.planner.plan_report)
        self.graph.add_node("human_review", self.human_reviewer.request_review)
        self.graph.add_node("research", self.researcher_graph)
        self.graph.add_node(
            "gather_completed_sections", self.compiler.gather_completed_sections
        )
        self.graph.add_node("write_final_sections", self.compiler.write_final_sections)
        self.graph.add_node("compile_final_report", self.compiler.compile_final_report)

    def add_edges(self) -> None:
        # 1. Plan -> human_review
        self.graph.add_edge(START, "plan")
        self.graph.add_edge("plan", "human_review")

        # 2. "human_review" -> (approved -> research) o (rejected -> plan)
        self.graph.add_conditional_edges(
            "human_review",
            self.validate_and_initiate_sections,
            {"research": "research", "plan": "plan"},
        )

        # 3. Investigación -> Recopilar secciones
        self.graph.add_edge("research", "gather_completed_sections")

        # 4. Recopilación -> Escritura final
        self.graph.add_conditional_edges(
            "gather_completed_sections",
            self.writer.initiate_final_section_writing,
            ["write_final_sections"],
        )

        # 5. Escritura final -> Compilación
        self.graph.add_edge("write_final_sections", "compile_final_report")
        self.graph.add_edge("compile_final_report", END)

    async def _send_limit_reached_notification(self):
        """Envía una notificación al usuario cuando se alcanza el límite de revisiones."""
        if self.websocket:
            limit_message = {
                "type": "limit_notification",
                "message": """
                **Límite de Revisiones Alcanzado**
                
                Has alcanzado el límite máximo de 3 revisiones para este plan.
                El sistema procederá con el plan actual para evitar ciclos infinitos.
                
                Si deseas realizar cambios adicionales, podrás hacerlo en una etapa posterior
                del proceso o iniciar un nuevo reporte.
                """,
            }
            await self.websocket.send_json(limit_message)

    def validate_and_initiate_sections(
        self, state: ReportState
    ) -> tuple[str, ReportState]:
        """
        1. Llama a human_reviewer.validate_input(state) para ver si es 'approved' o 'rejected'.
        2. Si es 'approved', llama a ReportPlanner.initiate_section_writing(state)
           para mapear las secciones a investigar.
        3. Retorna la cadena 'research' o 'plan' para dirigir el flujo, junto con el estado actualizado.
        4. Si se alcanza el límite de revisiones (3), fuerza la aprobación y continúa con 'research'.
        """
        # Validate input y actualizar decision
        decision = self.human_reviewer.validate_input(state)

        review_count = state.get("review_count", 0)

        if decision == "approved":
            # El usuario aprobó -> procedemos con la investigación
            return "research"
        # si initiate_section_writing siempre retorna "research", devuélvelo
        elif review_count >= 3:
            # Alcanzado el límite de revisiones -> forzar aprobación y continuar
            # Enviamos notificación de límite alcanzado (no bloqueante)
            import asyncio

            asyncio.create_task(self._send_limit_reached_notification())

            # Forzar la continuación como si fuera aprobado
            return "research"

        else:
            # El usuario rechazó y no se ha alcanzado el límite -> volvemos a 'plan'
            return "plan"
