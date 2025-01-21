from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import Send

from app.config.config import get_settings
from app.utils.llms import LLMManager, LLMConfig, LLMType
from app.utils.prompts import REPORT_PLANNER_QUERY_WRITER, REPORT_PLANNER_INSTRUCTIONS
from app.utils.state import ReportState, Section, Queries, Sections
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReportPlanner:
    """Class responsible for planning and organizing report generation."""

    def __init__(self, settings=None):
        """Initialize ReportPlanner with configuration settings."""
        self.settings = settings or get_settings()
        # Initialize LLMManager with configuration
        llm_config = LLMConfig(
            temperature=0.0,
            streaming=True,
            max_tokens=2000  # Adjust as needed
        )
        self.llm_manager = LLMManager(llm_config)
        # Get the primary LLM for report generation
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def generate_search_queries(self, topic: str) -> Queries:
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
            number_of_queries=self.settings.number_of_queries
        )

        logger.debug(f"Generating search queries for topic: {topic}")
        return structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Generate search queries for planning the report sections.")
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

    async def generate_sections(self, topic: str, source_str: str) -> Sections:
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
            context=source_str
        )

        logger.debug(f"Generating sections for topic: {topic}")
        return structured_llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(
                content="Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. Each section must have: name, description, plan, research, and content fields."
            )
        ])

    async def plan_report(self, state: ReportState) -> dict:
        """Generate a dynamic report plan using LLM and web research.

        Args:
            state: Current report state containing the topic

        Returns:
            Dictionary containing generated report sections
        """
        topic = state["topic"]
        logger.debug(f"Starting report planning for topic: {topic}")

        # Generate search queries
        queries_result = await self.generate_search_queries(topic)
        query_list = [query.search_query for query in queries_result.queries]

        # Conduct research
        source_str = await self.conduct_research(query_list)

        # Generate sections
        report_sections = await self.generate_sections(topic, source_str)
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
        return [
            Send("research", {"section": section})
            for section in state["sections"]
            if section.research
        ]
