from abc import ABC, abstractmethod
from langgraph.graph import StateGraph


class GraphBuilder(ABC):
    """Clase base abstracta para los constructores de grafos"""

    def __init__(self):
        self.graph = None

    @abstractmethod
    def init_graph(self) -> None:
        """Inicializa el grafo con su configuración base"""
        pass

    @abstractmethod
    def add_nodes(self) -> None:
        """Añade los nodos al grafo"""
        pass

    @abstractmethod
    def add_edges(self) -> None:
        """Añade las conexiones entre nodos"""
        pass

    def get_graph(self) -> StateGraph:
        """Retorna el grafo construido"""
        return self.graph

    def build(self) -> StateGraph:
        """Construye y retorna el grafo completo"""
        self.init_graph()
        self.add_nodes()
        self.add_edges()
        return self.get_graph()
