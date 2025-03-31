from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.constants import Send

from app.config.config import get_settings
from app.utils.llms import LLMManager, LLMConfig, LLMType
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.utils.state import TrendResearchState, ProductQueries
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrendResearchPlanner:
    """Clase responsable de planear la investigación de tendencias de productos."""

    def __init__(self, settings=None, websocket=None):
        """Inicializa el planificador de investigación de tendencias."""
        self.settings = settings or get_settings()
        self.websocket = websocket
        
        llm_config = LLMConfig(
            temperature=0.0,
            streaming=True,
            max_tokens=2000
        )
        self.llm_manager = LLMManager(llm_config)
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def send_progress(self, message: str, data: dict = None):
        """Envía actualizaciones de progreso a través del websocket"""
        if self.websocket:
            await self.websocket.send_json({
                "type": "trend_research_progress",
                "message": message,
                "data": data
            })

    async def generate_search_queries(self, product: str) -> ProductQueries:
        """Genera queries de búsqueda para investigar tendencias del producto."""
        structured_llm = self.primary_llm.with_structured_output(ProductQueries)
        system_instructions = """
        Para el producto {product}, genera queries específicas para investigar:
        1. Tendencias actuales en redes sociales
        2. Volumen de búsquedas y keywords populares
        3. Sentimiento del mercado hacia este tipo de productos
        4. Competencia y benchmarks de productos similares
        5. Estacionalidad y ciclos de demanda
        6. Demografía más interesada en este producto
        7. Precios y rangos de mercado
        8. Oportunidades de marketing digital
        """

        await self.send_progress(f"Generando queries para investigar: {product}")
        
        return structured_llm.invoke([
            SystemMessage(content=system_instructions.format(product=product)),
            HumanMessage(content="Genera queries precisas para investigar tendencias de mercado.")
        ])

    async def conduct_research(self, queries: list[str]) -> str:
        """Realiza búsquedas en internet usando las queries proporcionadas."""
        logger.debug(f"Realizando investigación con queries: {queries}")
        await self.send_progress("Realizando búsquedas en internet")
        
        search_docs = await tavily_search_async(
            queries,
            self.settings.tavily_topic,
            self.settings.tavily_days
        )

        return deduplicate_and_format_sources(
            search_docs,
            max_tokens_per_source=1000,
            include_raw_content=False
        )

    async def plan_product_research(self, state: TrendResearchState) -> dict:
        """Genera un plan de investigación para el producto."""
        product = state["product"]
        logger.debug(f"Iniciando planificación de investigación para: {product}")
        await self.send_progress(f"Planificando investigación para: {product}")

        # Generar queries de búsqueda
        queries_result = await self.generate_search_queries(product)
        query_list = [query.search_query for query in queries_result.queries]

        # Realizar investigación preliminar
        source_str = await self.conduct_research(query_list)

        # Crear plan de investigación detallado
        research_plan = {
            "product": product,
            "queries": query_list,
            "preliminary_data": source_str
        }

        await self.send_progress("Plan de investigación completado")
        return {"research_plan": research_plan}

    @staticmethod
    def initiate_trend_research(state: TrendResearchState) -> list[Send]:
        """Inicia la investigación de tendencias para el producto."""
        return [Send("search_trends", {"product": state["product"], "research_plan": state["research_plan"]})] 