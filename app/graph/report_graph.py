from app.graph.director import GraphDirector

def get_report_graph(websocket=None):
    """Obtiene una instancia del grafo de reporte con websocket configurado"""
    return GraphDirector.construct_report_graph(websocket=websocket)
