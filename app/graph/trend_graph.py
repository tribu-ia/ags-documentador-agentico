from app.graph.director import GraphDirector

def get_trend_graph(websocket=None):
    """Obtiene una instancia del grafo de análisis de tendencias con websocket configurado"""
    return GraphDirector.construct_trend_research_graph(websocket=websocket) 