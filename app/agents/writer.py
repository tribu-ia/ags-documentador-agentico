import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send

from app.config.config import get_settings
from app.utils.llms import LLMConfig, LLMManager, LLMType
from app.utils.prompts import SECTION_WRITER
from app.utils.state import Section

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class WriterEvent:
    """Class to represent different writer events for streaming"""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = asyncio.get_event_loop().time()

    def to_json(self) -> str:
        return json.dumps(
            {"type": self.type, "data": self.data, "timestamp": self.timestamp}
        )


class ReportWriter:
    """Class responsible for writing and organizing report sections."""

    def __init__(self, settings=None, websocket=None):
        """Initialize ReportWriter with configuration settings.

        Args:
            settings: Optional application settings. If None, will load default settings.
            websocket: Optional websocket for streaming progress updates.
        """
        self.settings = settings or get_settings()
        self.websocket = websocket

        # Initialize LLM manager with specific configuration for report writing
        llm_config = LLMConfig(
            temperature=0.0,  # Use deterministic output for report writing
            streaming=True,
            max_tokens=2000,  # Adjust based on expected section lengths
        )
        self.llm_manager = LLMManager(llm_config)

        # Get primary LLM for report writing - using Claude for high-quality content generation
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def send_progress(self, message: str, data: dict = None):
        """Send progress updates through websocket"""
        if self.websocket:
            await self.websocket.send_json(
                {"type": "writing_progress", "message": message, "data": data}
            )

    async def write_section(
        self, section: Section, context: str = None
    ) -> AsyncGenerator[str, None]:
        """Write a single section with streaming progress"""
        try:
            logger.debug(f"Starting write_section for: {section.name}")
            await self.send_progress("Starting section", {"section_name": section.name})

            system_instructions = SECTION_WRITER.format(
                section_topic=section.description,
                context=context if context else section.content,
            )
            logger.debug(f"System instructions prepared for: {section.name}")

            content_buffer = []
            logger.debug(f"Starting streaming for section: {section.name}")
            async for chunk in self.primary_llm.astream(
                [
                    SystemMessage(content=system_instructions),
                    HumanMessage(content="Generate section content"),
                ]
            ):
                logger.debug(
                    f"Received chunk for {section.name}: {chunk.content[:50]}..."
                )
                content_buffer.append(chunk.content)
                await self.send_progress("content_chunk", {"content": chunk.content})
                yield chunk.content  # Yield each chunk for streaming

            logger.debug(f"Streaming completed for section: {section.name}")
            section.content = "".join(content_buffer)
            await self.send_progress(
                "section_complete",
                {"section_name": section.name, "content": section.content},
            )

        except Exception as e:
            logger.error(f"Error in write_section for {section.name}: {str(e)}")
            await self.send_progress("error", {"error": str(e)})
            raise

    async def write_report(self, state: dict) -> AsyncGenerator[Dict, None]:
        """Process and write all sections with streaming updates"""
        try:
            logger.debug("Starting write_report process")
            await self.send_progress(
                "report_start", {"total_sections": len(state["sections"])}
            )

            final_content = []
            for section in state["sections"]:
                logger.debug(f"Processing section in write_report: {section.name}")
                async for content in self.write_section(section):
                    logger.debug(
                        f"Yielding content from write_report for {section.name}"
                    )
                    yield {"section": section.name, "content": content}
                final_content.append(section.content)

            logger.debug("Completed write_report process")
            await self.send_progress(
                "report_complete", {"completed_sections": final_content}
            )

        except Exception as e:
            await self.send_progress("error", {"error": str(e)})
            raise

    async def initiate_final_section_writing(self, state: dict) -> list[Send]:
        """Initialize parallel section writing for final sections."""
        try:
            await self.send_progress("Initiating final section writing")
            research_context = state.get("report_sections_from_research", "")

            return [
                Send(
                    "write_final_sections",
                    {
                        "section": section,
                        "report_sections_from_research": research_context,
                        "completed_sections": state.get(
                            "completed_sections", []
                        ),  # Solo los campos necesarios
                    },
                )
                for section in state["sections"]
                if not section.research
            ]
        except Exception as e:
            await self.send_progress(
                "Error initiating final sections", {"error": str(e)}
            )
            raise

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()
