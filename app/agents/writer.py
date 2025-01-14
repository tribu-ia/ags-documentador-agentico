from app.utils.state import ReportState


def write_report(state: ReportState):
    content = f"# {state.topic}\n\n"
    for section in state.sections:
        content += f"## {section.name}\n{section.description}\n\n"
    state.final_report = content
    return state
