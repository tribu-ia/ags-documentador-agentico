import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send

from app.config.config import get_settings

# from app.utils.state import ReportState, Section, Queries, Sections
from app.services.tavilyService import (
    deduplicate_and_format_sources,
    tavily_search_async,
)
from app.utils.llms import LLMConfig, LLMManager, LLMType
from app.utils.prompts import REPORT_PLANNER_INSTRUCTIONS, REPORT_PLANNER_QUERY_WRITER
from app.utils.state import Queries, ReportState, Sections

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReportPlanner:
    """Class responsible for planning and organizing report generation."""

    def __init__(self, settings=None, websocket=None):
        """Initialize ReportPlanner with configuration settings."""
        self.settings = settings or get_settings()
        self.websocket = websocket

        # Initialize LLMManager with configuration
        llm_config = LLMConfig(temperature=0.0, streaming=True, max_tokens=2000)
        self.llm_manager = LLMManager(llm_config)
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def send_progress(self, message: str, data: dict = None):
        """Send progress updates through websocket"""
        if self.websocket:
            await self.websocket.send_json(
                {"type": "planning_progress", "message": message, "data": data}
            )

    async def generate_search_queries(self, topic: str, user_feedback: str) -> Queries:
        """Generate initial search queries for the report topic.

        Args:
            topic: The main topic of the report

        Returns:
            Queries object containing generated search queries
        """
        structured_llm = self.primary_llm.with_structured_output(Queries)
        system_instructions = REPORT_PLANNER_QUERY_WRITER.format(
            topic=topic,
            report_organization=self.settings.report_structure,
            number_of_queries=self.settings.number_of_queries,
        )

        # Add user feedback to instructions if it exists
        if user_feedback:
            feedback_context = f"""
            RETROALIMENTACIÓN DEL USUARIO:
            El usuario ha proporcionado la siguiente retroalimentación sobre la versión anterior del plan:
            
            "{user_feedback}"
            
            Por favor, asegúrate de incorporar esta retroalimentación en la nueva versión del plan.
            Ajusta las queries existentes, añade nuevas si es necesario, o elimina/modifica las que
            no se alinean con la retroalimentación del usuario.
            """
            system_instructions += feedback_context

        logger.debug(f"Generating sections for topic: {topic}")

        human_message_content = (
            "Generate search queries for planning the report sections."
        )
        if user_feedback:
            human_message_content += (
                " Incorporate the user feedback to improve the search queries."
            )

        logger.debug(f"Generating search queries for topic: {topic}")
        return structured_llm.invoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(content=human_message_content),
            ]
        )

    async def conduct_research(self, queries: list[str]) -> str:
        """Conduct parallel web searches using provided queries.

        Args:
            queries: List of search queries to execute

        Returns:
            Formatted string of search results
        """
        logger.debug(f"Conducting research with queries: {queries}")
        search_docs = await tavily_search_async(
            queries, self.settings.tavily_topic, self.settings.tavily_days
        )

        return deduplicate_and_format_sources(
            search_docs, max_tokens_per_source=1000, include_raw_content=False
        )

    async def generate_sections(
        self, topic: str, source_str: str, user_feedback: str
    ) -> Sections:
        """Generate report sections based on research results.

        Args:
            topic: The main topic of the report
            source_str: Formatted string of research results

        Returns:
            Sections object containing generated report sections
        """
        structured_llm = self.primary_llm.with_structured_output(Sections)
        system_instructions = REPORT_PLANNER_INSTRUCTIONS.format(
            topic=topic,
            report_organization=self.settings.report_structure,
            context=source_str,
        )

        # Add user feedback to instructions if it exists
        if user_feedback:
            feedback_context = f"""
            RETROALIMENTACIÓN DEL USUARIO:
            El usuario ha proporcionado la siguiente retroalimentación sobre la versión anterior del plan:
            
            "{user_feedback}"
            
            Por favor, asegúrate de incorporar esta retroalimentación en la nueva versión del plan.
            Ajusta las secciones existentes, añade nuevas si es necesario, o elimina/modifica las que
            no se alinean con la retroalimentación del usuario.
            """
            system_instructions += feedback_context

        logger.debug(f"Generating sections for topic: {topic}")

        human_message_content = "Generate the sections of the report."
        if user_feedback:
            human_message_content += (
                " Incorporate the user feedback to improve the plan."
            )

        logger.debug(f"Generating sections for topic: {topic}")
        return structured_llm.invoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(content=human_message_content),
            ]
        )

    async def plan_report(self, state: ReportState) -> dict:
        """Generate a dynamic report plan using LLM and web research.

        Args:
            state: Current report state containing the topic and potentially user feedback

        Returns:
            Dictionary containing generated report sections
        """
        # Use defensive state access with defaults
        topic = state.get("topic", "")
        user_feedback = state.get("user_feedback", "")
        review_count = state.get("review_count", 0)

        if not topic:
            logger.warning("No topic found in state, using empty string")

        logger.debug(
            f"Starting report planning for topic: {topic}, review iteration: {review_count}"
        )

        # Si hay feedback del usuario y no es la primera iteración, informarlo
        if user_feedback and review_count > 0:
            await self.send_progress(
                "Incorporando feedback del usuario en la regeneración del plan",
                {"feedback": user_feedback, "review_count": review_count},
            )
            logger.debug(f"Incorporating user feedback: {user_feedback}")

        # Generate search queries
        queries_result = await self.generate_search_queries(topic, user_feedback)
        query_list = [query.search_query for query in queries_result.queries]

        # Conduct research
        source_str = await self.conduct_research(query_list)

        # Generate sections
        report_sections = await self.generate_sections(topic, source_str, user_feedback)

        logger.debug(f"Completed report planning for topic: {topic}")
        return {"sections": report_sections.sections}

    @staticmethod
    def initiate_section_writing(state: ReportState) -> list[Send]:
        """Initialize parallel section writing for sections requiring research.

        Args:
            state: Current report state containing sections

        Returns:
            List of Send objects for parallel processing
        """
        # Use defensive state access with empty list default
        sections = state.get("sections", [])
        if not sections:
            logger.warning("No sections found in state, returning empty list")
            return []

        return [
            Send("research", {"section": section})
            for section in sections
            if section.research
        ]
