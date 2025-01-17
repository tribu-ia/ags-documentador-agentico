from app.utils.state import ReportState, Section


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
