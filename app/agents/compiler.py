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

    def __init__(self, settings=None, websocket=None):
        """Initialize ReportCompiler with configuration settings.

        Args:
            settings: Optional application settings. If None, will load default settings.
            websocket: Optional websocket for streaming updates.
        """
        self.settings = settings or get_settings()
        self.websocket = websocket

        # Initialize LLM manager with compilation-specific configuration
        llm_config = LLMConfig(
            temperature=0.0,  # Use deterministic output for compilation
            streaming=True,
            max_tokens=4000  # Larger context for final compilation
        )
        self.llm_manager = LLMManager(llm_config)
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

    async def send_progress(self, message: str, data: dict = None):
        """Send progress updates through websocket"""
        if self.websocket:
            await self.websocket.send_json({
                "type": "compiler_progress",
                "message": message,
                "data": data
            })

    async def gather_completed_sections(self, state: dict) -> dict:
        """Gather and format completed sections for context."""
        try:
            await self.send_progress("Gathering completed sections")
            completed_sections = state.get("completed_sections", [])
            formatted_sections = self.format_sections(completed_sections)

            # Retornar estado completo actualizado
            return {
                **state,  # Mantener estado existente
                "report_sections_from_research": formatted_sections
            }

        except Exception as e:
            await self.send_progress("Error gathering sections", {"error": str(e)})
            raise

    async def write_final_sections(self, state: dict) -> dict:
        """Write final sections using completed research as context."""
        try:
            section = state["section"]
            context = state.get("report_sections_from_research", "")
            
            await self.send_progress(f"Writing final section: {section.name}")

            system_instructions = FINAL_SECTION_WRITER.format(
                section_title=section.name,
                section_topic=section.description,
                context=context
            )

            section_content = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ])

            section.content = section_content.content
            
            # Solo retornar los campos que necesitamos actualizar
            return {
                "completed_sections": state.get("completed_sections", []) + [section]
            }

        except Exception as e:
            await self.send_progress("Error writing section", {"error": str(e)})
            raise

    def compile_sections(self, state: dict) -> dict:
        """Compile all sections into a unified structure."""
        try:
            logger.debug("Compiling sections")
            sections = state["sections"]  # Acceder como diccionario
            completed_sections = {
                s.name: s.content
                for s in state["completed_sections"]  # Acceder como diccionario
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

    async def compile_final_report(self, state: dict) -> dict:
        """Generate the final formatted report."""
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
