from app.utils.state import ResearchState


def generate_queries(state: ResearchState):
    # Logic to generate search queries based on the topic
    state.documents = [f"Query for: {state.query}"]
    return state


def retrieve_documents(state: ResearchState):
    # Logic to retrieve documents from a search
    state.documents.append("Retrieved document 1")
    state.documents.append("Retrieved document 2")
    return state
