from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.utils.llms import LLMConfig, LLMManager, LLMType
from app.utils.prompts import RESEARCH_QUERY_WRITER, SECTION_WRITER
from app.utils.state import ResearchState, SectionState, Queries, Section
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ResearchManager:
    """Class responsible for managing research operations including query generation,
    web searching, and section writing."""

    def __init__(self, settings=None):
        """Initialize ResearchManager with configuration settings.

        Args:
            settings: Optional application settings. If None, will load default settings.
        """
        self.settings = settings or get_settings()

        # Initialize LLM manager with research-specific configuration
        llm_config = LLMConfig(
            temperature=0.0,  # Use deterministic output for research
            streaming=True,
            max_tokens=2000  # Adjust based on expected response lengths
        )
        self.llm_manager = LLMManager(llm_config)

        # Get primary LLM for research operations
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def generate_queries(self, state: SectionState) -> dict:
        """Generate search queries for a section.

        Args:
            state: Current section state containing the section details

        Returns:
            dict: Dictionary containing generated search queries
        """
        try:
            logger.debug(f"Generating queries for section: {state['section'].name}")
            section = state["section"]

            structured_llm = self.primary_llm.with_structured_output(Queries)

            system_instructions = RESEARCH_QUERY_WRITER.format(
                section_topic=section.description,
                number_of_queries=self.settings.number_of_queries
            )

            queries = await structured_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate search queries on the provided topic.")
            ])

            logger.debug(f"Generated {len(queries.queries)} queries")
            return {"search_queries": queries.queries}

        except Exception as e:
            logger.error(f"Error generating queries: {str(e)}")
            raise

    async def search_web(self, state: SectionState) -> dict:
        """Perform web searches based on generated queries.

        Args:
            state: Current section state containing search queries

        Returns:
            dict: Dictionary containing formatted search results
        """
        try:
            logger.debug("Starting web search")
            search_queries = state["search_queries"]

            # Extract queries and perform searches
            query_list = [query.search_query for query in search_queries]
            search_docs = await tavily_search_async(
                query_list,
                self.settings.tavily_topic,
                self.settings.tavily_days
            )

            # Format and deduplicate results
            source_str = deduplicate_and_format_sources(
                search_docs,
                max_tokens_per_source=5000,
                include_raw_content=True
            )

            logger.debug("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            logger.error(f"Error during web search: {str(e)}")
            raise

    async def write_section(self, state: SectionState) -> dict:
        """Write a section based on research results.

        Args:
            state: Current section state containing the section and source material

        Returns:
            dict: Dictionary containing the completed section
        """
        try:
            logger.debug(f"Writing section: {state['section'].name}")
            section = state["section"]
            source_str = state["source_str"]

            system_instructions = SECTION_WRITER.format(
                section_title=section.name,
                section_topic=section.description,
                context=source_str
            )

            # Generate section content
            section_content = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ])

            # Update section content
            section.content = section_content.content
            logger.debug(f"Completed writing section: {section.name}")

            return {"completed_sections": [section]}

        except Exception as e:
            logger.error(f"Error writing section: {str(e)}")
            raise

    async def research_section(self, section: Section) -> Section:
        """Perform complete research process for a single section.

        Args:
            section: Section to research

        Returns:
            Section: Completed section with research content
        """
        try:
            # Initialize state
            state = SectionState(section=section)

            # Generate queries
            state.update(await self.generate_queries(state))

            # Perform web search
            state.update(await self.search_web(state))

            # Write section
            result = await self.write_section(state)

            return result["completed_sections"][0]

        except Exception as e:
            logger.error(f"Error researching section {section.name}: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()
