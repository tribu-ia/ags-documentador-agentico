from app.utils.state import ReportState, Section


def plan_report(state: ReportState):
    state.sections = [
        Section(name="Introduction", description="Overview of the topic", research=False),
        Section(name="Body", description="Detailed exploration", research=True),
        Section(name="Conclusion", description="Summary and implications", research=False),
    ]
    return state
