from typing import List

from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.utils.llms import LLMConfig, LLMManager, LLMType
from app.utils.prompts import FINAL_SECTION_WRITER, FINAL_REPORT_FORMAT
from app.utils.state import ReportState, Section, SectionState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReportCompiler:
    """Class responsible for compiling and formatting the final report."""

    def __init__(self, settings=None):
        """Initialize ReportCompiler with configuration settings.

        Args:
            settings: Optional application settings. If None, will load default settings.
        """
        self.settings = settings or get_settings()

        # Initialize LLM manager with compilation-specific configuration
        llm_config = LLMConfig(
            temperature=0.0,  # Use deterministic output for compilation
            streaming=True,
            max_tokens=4000  # Larger context for final compilation
        )
        self.llm_manager = LLMManager(llm_config)

        # Get primary LLM for report compilation
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    def format_sections(self, sections: List[Section]) -> str:
        """Format a list of sections into a structured string.

        Args:
            sections: List of sections to format

        Returns:
            str: Formatted string representation of sections
        """
        formatted_str = ""
        for idx, section in enumerate(sections, 1):
            formatted_str += f"""
                            {'=' * 60}
                            Section {idx}: {section.name}
                            {'=' * 60}
                            Description:
                            {section.description}
                            Requires Research: 
                            {section.research}
                            
                            Content:
                            {section.content if section.content else '[Not yet written]'}
                            """
        return formatted_str

    def gather_completed_sections(self, state: ReportState) -> dict:
        """Gather and format completed sections for context.

        Args:
            state: Current report state containing completed sections

        Returns:
            dict: Dictionary containing formatted sections
        """
        try:
            logger.debug("Gathering completed sections")
            completed_sections = state["completed_sections"]
            formatted_sections = self.format_sections(completed_sections)

            return {
                "report_sections_from_research": formatted_sections
            }

        except Exception as e:
            logger.error(f"Error gathering completed sections: {str(e)}")
            raise

    async def write_final_sections(self, state: SectionState) -> dict:
        """Write final sections using completed research as context.

        Args:
            state: Current section state with research context

        Returns:
            dict: Dictionary containing completed sections
        """
        try:
            logger.debug(f"Writing final section: {state['section'].name}")
            section = state["section"]
            completed_report_sections = state["report_sections_from_research"]

            system_instructions = FINAL_SECTION_WRITER.format(
                section_title=section.name,
                section_topic=section.description,
                context=completed_report_sections
            )

            # Generate section content
            section_content = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ])

            # Update section
            section.content = section_content.content
            logger.debug(f"Completed writing final section: {section.name}")

            return {"completed_sections": [section]}

        except Exception as e:
            logger.error(f"Error writing final section: {str(e)}")
            raise

    def compile_sections(self, state: ReportState) -> dict:
        """Compile all sections into a unified structure.

        Args:
            state: Current report state containing all sections

        Returns:
            dict: Dictionary containing compiled sections
        """
        try:
            logger.debug("Compiling sections")
            sections = state["sections"]
            completed_sections = {
                s.name: s.content
                for s in state["completed_sections"]
            }

            # Update sections while maintaining order
            for section in sections:
                section.content = completed_sections[section.name]

            # Join sections
            all_sections = "\n\n".join([s.content for s in sections])

            return {"final_report": all_sections}

        except Exception as e:
            logger.error(f"Error compiling sections: {str(e)}")
            raise

    async def compile_final_report(self, state: ReportState) -> dict:
        """Generate the final formatted report.

        Args:
            state: Current report state with all sections

        Returns:
            dict: Dictionary containing the final formatted report
        """
        try:
            logger.debug("Generating final report")

            # First compile all sections
            compiled_sections = self.compile_sections(state)
            all_sections = compiled_sections["final_report"]

            # Format system instructions for final compilation
            system_instructions = FINAL_REPORT_FORMAT.format(
                all_sections=all_sections,
                report_organization=self.settings.report_structure
            )

            # Generate final report
            final_report = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a structured report.")
            ])

            logger.debug("Final report compilation completed")
            return {"final_report": final_report.content}

        except Exception as e:
            logger.error(f"Error compiling final report: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()
