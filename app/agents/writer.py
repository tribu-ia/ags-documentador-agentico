from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send

from app.config.config import get_settings
from app.providers.llm import LLMType, get_llm
from app.utils.prompts import SECTION_WRITER
from app.utils.state import ReportState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def write_report(state: ReportState):
    settings = get_settings()
    sections = state["sections"]
    logger.debug(f"Sections: {sections}")
    # system_instructions = SECTION_WRITER.format(
    #     section_title=section.name,
    #     section_topic=section.description,
    #     context=section.content
    # )
    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
        logger.info(f"Using LLM: {llm_type}")
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)

    # Procesar cada sección
    final_content = []
    for section in sections:
        system_instructions = SECTION_WRITER.format(
            section_topic=section.description,
            context=section.content if section.content else "No content available yet."
        )

        section_content = llm.invoke([
            SystemMessage(content=system_instructions),
            HumanMessage(content="Generate a report section based on the provided sources.")
        ])

        # Actualizar el contenido de la sección
        section.content = section_content.content
        final_content.append(section_content.content)

    # section_content = llm.invoke([SystemMessage(content=system_instructions)] + [
    #     HumanMessage(content="Generate a report section based on the provided sources.")])
    # Write content to the section object
    #section.content = section_content.content
    # content = f"# {state.topic}\n\n"
    # for section in state.sections:
    #     content += f"## {section.name}\n{section.description}\n\n"
    # state.final_report = content
    #logger.debug(f"Final content: {final_content}")
    #print(f"Final content: {final_content}")
    #state["completed_sections"] = final_content
    return {"completed_sections": final_content}


def initiate_final_section_writing(state: ReportState):
    """ Write any final sections using the Send API to parallelize the process """

    # Kick off section writing in parallel via Send() API for any sections that do not require research
    return [
        Send("write_final_sections",
             {"section": s, "report_sections_from_research": state["report_sections_from_research"]})
        for s in state["sections"]
        if not s.research
    ]