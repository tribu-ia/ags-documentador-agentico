# app/graph/researcher_graph.py
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agents.researcher import generate_queries, retrieve_documents, search_web, write_section
from app.utils.state import ResearchState, SectionState, SectionOutputState


# Define the researcher graph
def build_researcher_graph():
    graph = StateGraph(SectionState, output=SectionOutputState)
    graph.add_node("generate_queries", generate_queries)
    graph.add_node("search_web", search_web)
    graph.add_node("write_section", write_section)
    graph.add_edge(START, "generate_queries")
    graph.add_edge("generate_queries", "search_web")
    graph.add_edge("search_web", "write_section")
    graph.add_edge("write_section", END)
    return graph
