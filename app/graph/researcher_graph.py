# app/graph/researcher_graph.py
from langgraph.graph import StateGraph

from app.agents.researcher import generate_queries, retrieve_documents
from app.utils.state import ResearchState


# Define the researcher graph
def build_researcher_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("generate_queries", generate_queries)
    graph.add_node("retrieve_documents", retrieve_documents)
    graph.add_edge("START", "generate_queries")
    graph.add_edge("generate_queries", "retrieve_documents")
    graph.add_edge("retrieve_documents", "END")
    return graph
