from langgraph.graph import END, START, StateGraph

from app.agents.compiler import compile_report
from app.agents.planner import plan_report
from app.agents.writer import write_report
from app.utils.state import ReportState


# Define the report graph
def build_report_graph():
    graph = StateGraph(ReportState)
    graph.add_node("plan", plan_report)
    graph.add_node("write", write_report)
    graph.add_node("compile", compile_report)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "write")
    graph.add_edge("write", "compile")
    graph.add_edge("compile", END)
    return graph
