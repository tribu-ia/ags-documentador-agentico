from typing import Annotated, TypedDict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import Send

from app.config.config import get_settings
from app.utils.llms import LLMManager, LLMConfig, LLMType
from app.utils.prompts import REPORT_PLANNER_QUERY_WRITER, REPORT_PLANNER_INSTRUCTIONS
#from app.utils.state import ReportState, Section, Queries, Sections
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
import logging

from app.utils.state import ReportState, Queries, Sections

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class CampaignPlanner:
    """Clase responsable de planear y organizar campañas de marketing digital."""

    def __init__(self, settings=None, websocket=None):
        """Initialize CampaignPlanner with configuration settings."""
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
        """Send progress updates through websocket"""
        if self.websocket:
            await self.websocket.send_json({
                "type": "planning_progress",
                "message": message,
                "data": data
            })

    async def generate_search_queries(self, product: str) -> Queries:
        """Genera queries de búsqueda para investigar tendencias del producto.

        Args:
            product: El producto para el cual se creará la campaña

        Returns:
            Queries object containing generated search queries
        """
        structured_llm = self.primary_llm.with_structured_output(Queries)
        system_instructions = """
        Genera queries de búsqueda para investigar las siguientes áreas sobre el producto {product}:
        1. Tendencias actuales en redes sociales
        2. Palabras clave populares relacionadas
        3. Campañas exitosas similares
        4. Demografía del público objetivo
        5. Insights del mercado actual
        """

        return structured_llm.invoke([
            SystemMessage(content=system_instructions.format(product=product)),
            HumanMessage(content="Genera queries de búsqueda para investigar el producto y sus tendencias.")
        ])

    async def conduct_research(self, queries: list[str]) -> str:
        """Conduct parallel web searches using provided queries.

        Args:
            queries: List of search queries to execute

        Returns:
            Formatted string of search results
        """
        logger.debug(f"Conducting research with queries: {queries}")
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

    async def generate_campaign_plan(self, product: str, source_str: str) -> dict:
        """Generate a dynamic campaign plan using LLM and web research.

        Args:
            product: The main product of the campaign
            source_str: Formatted string of research results

        Returns:
            Dictionary containing generated campaign sections
        """
        logger.debug(f"Starting campaign planning for product: {product}")

        # Generate search queries
        queries_result = await self.generate_search_queries(product)
        query_list = [query.search_query for query in queries_result.queries]

        # Conduct research
        source_str = await self.conduct_research(query_list)

        # Generate campaign plan
        campaign_plan = await self.generate_campaign_sections(product, source_str)
        logger.debug(f"Completed campaign planning for product: {product}")
        return {"campaign_plan": campaign_plan}

    async def generate_campaign_sections(self, product: str, source_str: str) -> dict:
        """Generate campaign sections based on research results.

        Args:
            product: The main product of the campaign
            source_str: Formatted string of research results

        Returns:
            Dictionary containing generated campaign sections
        """
        structured_llm = self.primary_llm.with_structured_output(Sections)
        system_instructions = REPORT_PLANNER_INSTRUCTIONS.format(
            topic=product,
            report_organization=self.settings.report_structure,
            context=source_str
        )

        logger.debug(f"Generating sections for product: {product}")
        return structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(
                content="Generate the sections of the campaign. Your response must include a 'sections' field containing a list of sections. Each section must have: name, description, plan, research, and content fields."
            )
        ])

    @staticmethod
    def initiate_trend_research(state: CampaignState) -> list[Send]:
        """Inicializa la investigación de tendencias para el producto.

        Args:
            state: Estado actual de la campaña

        Returns:
            List of Send objects for parallel processing
        """
        return [Send("search_product_trends", {"product": state["product"]})]


class TrendResearchPlanner:
    """Clase responsable de planear la investigación de tendencias de productos."""

    async def generate_search_queries(self, product: str) -> Queries:
        """Genera queries de búsqueda para investigar tendencias del producto."""
        structured_llm = self.primary_llm.with_structured_output(Queries)
        system_instructions = """
        Para el producto {product}, genera queries para investigar:
        1. Tendencias actuales en redes sociales
        2. Volumen de búsquedas y keywords
        3. Sentimiento del mercado
        4. Competencia y benchmarks
        5. Estacionalidad y ciclos de demanda
        6. Demografía interesada
        7. Precios y rangos de mercado
        """

        return structured_llm.invoke([
            SystemMessage(content=system_instructions.format(product=product)),
            HumanMessage(content="Genera queries de investigación de tendencias.")
        ])

    async def plan_product_research(self, state: dict) -> dict:
        """Genera un plan de investigación para múltiples productos."""
        products = state["products"]
        research_plans = []

        for product in products:
            queries = await self.generate_search_queries(product)
            research_plans.append({
                "product": product,
                "queries": queries.queries,
                "priority": "high"  # Podría ser dinámico basado en alguna lógica
            })

        return {"research_plans": research_plans}