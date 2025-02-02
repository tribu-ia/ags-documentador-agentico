from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send
from typing import AsyncGenerator, Dict, Any
import asyncio
import json

from app.config.config import get_settings
from app.utils.llms import LLMConfig, LLMManager, LLMType

from app.utils.prompts import SECTION_WRITER
from app.utils.state import ReportState, Section
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WriterEvent:
    """Class to represent different writer events for streaming"""
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = asyncio.get_event_loop().time()

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        })

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
            max_tokens=2000  # Adjust based on expected section lengths
        )
        self.llm_manager = LLMManager(llm_config)

        # Get primary LLM for report writing - using Claude for high-quality content generation
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def stream_progress(self, event: WriterEvent):
        """Stream progress events through websocket if available"""
        if self.websocket:
            await self.websocket.send_text(event.to_json())

    async def write_section(self, section: Section, context: str = None) -> AsyncGenerator[str, None]:
        """Write a single section with streaming progress"""
        try:
            await self.stream_progress(WriterEvent(
                "section_start",
                {"section_name": section.name}
            ))

            logger.debug(f"Writing section: {section.name}")

            system_instructions = SECTION_WRITER.format(
                section_topic=section.description,
                context=context if context else (section.content or "No content available yet.")
            )

            # Stream the writing process
            content_buffer = []
            async for chunk in self.primary_llm.astream([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ]):
                content_buffer.append(chunk.content)
                # Stream each chunk
                await self.stream_progress(WriterEvent(
                    "content_chunk",
                    {"content": chunk.content}
                ))
                yield chunk.content

            final_content = "".join(content_buffer)
            section.content = final_content

            await self.stream_progress(WriterEvent(
                "section_complete",
                {
                    "section_name": section.name,
                    "content": final_content
                }
            ))

        except Exception as e:
            logger.error(f"Error writing section {section.name}: {str(e)}")
            await self.stream_progress(WriterEvent(
                "error",
                {"error": str(e), "section": section.name}
            ))
            raise

    async def write_report(self, state: ReportState) -> AsyncGenerator[Dict, None]:
        """Process and write all sections with streaming updates"""
        try:
            await self.stream_progress(WriterEvent(
                "report_start",
                {"total_sections": len(state["sections"])}
            ))

            logger.debug("Starting report writing process")
            sections = state["sections"]
            final_content = []

            for section in sections:
                async for content in self.write_section(section):
                    yield {
                        "section": section.name,
                        "content": content
                    }
                final_content.append(section.content)

            logger.debug("Completed writing all sections")
            await self.stream_progress(WriterEvent(
                "report_complete",
                {"completed_sections": final_content}
            ))

        except Exception as e:
            logger.error(f"Error during report writing: {str(e)}")
            await self.stream_progress(WriterEvent(
                "error",
                {"error": str(e)}
            ))
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

