from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.providers.llm import LLMType, get_llm
from app.utils.prompts import FINAL_SECTION_WRITER, FINAL_REPORT_FORMAT
from app.utils.state import ReportState, Section, SectionState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def compile_report(state: ReportState):
    # Ensure all sections are properly compiled
    # compiled_content = f"# Final Report: {state.topic}\n\n"
    # for section in state.sections:
    #     compiled_content += f"## {section.name}\n{section.content if section.content else 'Content not available'}\n\n"
    # state.final_report = compiled_content
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}
    # Update sections with completed content while maintaining original order
    for section in sections:
        section.content = completed_sections[section.name]

        # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])

    return {"final_report": all_sections}


def gather_completed_sections(state: ReportState):
    """ Gather completed sections from research and format them as context for writing the final sections """

    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    completed_report_sections = format_sections(completed_sections)

    return {"report_sections_from_research": completed_report_sections}


def format_sections(sections: list[Section]) -> str:
    """ Format a list of sections into a string """
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


def write_final_sections(state: SectionState):
    """ Write final sections of the report, which do not require web search and use the completed sections as context """

    # Get state
    section = state["section"]
    completed_report_sections = state["report_sections_from_research"]

    # Format system instructions
    system_instructions = FINAL_SECTION_WRITER.format(section_title=section.name,
                                                      section_topic=section.description,
                                                      context=completed_report_sections)
    settings = get_settings()
    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)
    # Generate section
    section_content = llm.invoke([SystemMessage(content=system_instructions)] + [
        HumanMessage(content="Generate a report section based on the provided sources.")])

    # Write content to section
    section.content = section_content.content

    # Write the updated section to completed sections
    return {"completed_sections": [section]}


def compile_final_report(state: ReportState):
    """ Compile the final report """

    # Get sections
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}

    # Update sections with completed content while maintaining original order
    for section in sections:
        section.content = completed_sections[section.name]

    # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])
    # Prompt para estructurar el reporte final

    settings = get_settings()
    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)

        # Format system instructions
    system_instructions = FINAL_REPORT_FORMAT.format(all_sections=all_sections)

    # Generar el reporte final usando el modelo
    final_report = llm.invoke(
        [
            SystemMessage(system_instructions),
            HumanMessage(content="Generate a structured report."),
        ]
    )
    return {"final_report": final_report.content}
