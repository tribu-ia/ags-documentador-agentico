from langgraph.graph import END, START, StateGraph

from app.agents.compiler import compile_report, gather_completed_sections
from app.agents.planner import plan_report, initiate_section_writing
from app.agents.writer import write_report
from app.graph.researcher_graph import build_researcher_graph
from app.utils.state import ReportState


# Define the report graph
def build_report_graph():
    graph = StateGraph(ReportState)
    graph.add_node("plan", plan_report)
    graph.add_node("research", build_researcher_graph().compile())
    graph.add_node("gather_completed_sections", gather_completed_sections)
    graph.add_node("write", write_report)
    graph.add_node("compile", compile_report)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", initiate_section_writing, ["research"])
    graph.add_edge("research", "gather_completed_sections")
    graph.add_edge("gather_completed_sections", END)
    return graph
