from app.utils.state import ReportState


def compile_report(state: ReportState):
    # Ensure all sections are properly compiled
    compiled_content = f"# Final Report: {state.topic}\n\n"
    for section in state.sections:
        compiled_content += f"## {section.name}\n{section.content if section.content else 'Content not available'}\n\n"
    state.final_report = compiled_content
    return state
