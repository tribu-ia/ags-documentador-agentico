from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send

from app.config.config import get_settings
from app.utils.llms import LLMConfig, LLMManager, LLMType

from app.utils.prompts import SECTION_WRITER
from app.utils.state import ReportState, Section
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReportWriter:
    """Class responsible for writing and organizing report sections."""

    def __init__(self, settings=None):
        """Initialize ReportWriter with configuration settings.

        Args:
            settings: Optional application settings. If None, will load default settings.
        """
        self.settings = settings or get_settings()

        # Initialize LLM manager with specific configuration for report writing
        llm_config = LLMConfig(
            temperature=0.0,  # Use deterministic output for report writing
            streaming=True,
            max_tokens=2000  # Adjust based on expected section lengths
        )
        self.llm_manager = LLMManager(llm_config)

        # Get primary LLM for report writing - using Claude for high-quality content generation
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def write_section(self, section: Section, context: str = None) -> str:
        """Write a single section of the report.

        Args:
            section: Section object containing the section details
            context: Optional additional context for the section

        Returns:
            str: The generated content for the section
        """
        try:
            logger.debug(f"Writing section: {section.name}")

            system_instructions = SECTION_WRITER.format(
                section_topic=section.description,
                context=context if context else (section.content or "No content available yet.")
            )

            response = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ])

            return response.content

        except Exception as e:
            logger.error(f"Error writing section {section.name}: {str(e)}")
            raise

    async def write_report(self, state: ReportState) -> dict:
        """Process and write all sections of the report.

        Args:
            state: Current report state containing sections to process

        Returns:
            dict: Dictionary containing completed sections
        """
        try:
            logger.debug("Starting report writing process")
            sections = state["sections"]
            final_content = []

            for section in sections:
                # Write section content
                content = await self.write_section(section)

                # Update section and add to final content
                section.content = content
                final_content.append(content)

            logger.debug("Completed writing all sections")
            return {"completed_sections": final_content}

        except Exception as e:
            logger.error(f"Error during report writing: {str(e)}")
            raise

    @staticmethod
    def initiate_final_section_writing(state: ReportState) -> list[Send]:
        """Initialize parallel writing for sections that don't require research.

        Args:
            state: Current report state containing sections

        Returns:
            list[Send]: List of Send objects for parallel processing
        """
        return [
            Send(
                "write_final_sections",
                {
                    "section": section,
                    "report_sections_from_research": state["report_sections_from_research"]
                }
            )
            for section in state["sections"]
            if not section.research
        ]

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()

