import logging
from typing import Dict

from fastapi import WebSocket
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph.report_graph import (
    get_report_graph,  # Se mantiene la función actualizada
)

logger = logging.getLogger(__name__)


# --- Función get_report_graph ---
def get_report_graph(websocket=None):
    """
    Obtiene una instancia del grafo de reporte con websocket configurado y
    lo compila con un checkpointer (MemorySaver).
    """
    from app.graph.director import GraphDirector

    graph = GraphDirector.construct_report_graph(websocket=websocket)
    return graph.compile(checkpointer=MemorySaver())


# --- Clase WebSocketManager ---
class WebSocketManager:
    """Gestiona las conexiones WebSocket y el proceso de investigación"""

    def __init__(self):
        self.active_connections: Dict[
            WebSocket, dict
        ] = {}  # Estado del flujo para cada WebSocket
        self.running_graphs: Dict[
            WebSocket, object
        ] = {}  # Grafo en ejecución por WebSocket
        self.checkpoints: Dict[WebSocket, str] = {}  # Guarda el checkpoint_id usado

    async def connect(self, websocket: WebSocket):
        """Establece conexión con un cliente WebSocket"""
        await websocket.accept()
        self.active_connections[websocket] = None
        self.running_graphs[websocket] = None
        self.checkpoints[websocket] = None
        logger.info("Nueva conexión WebSocket establecida")

    async def disconnect(self, websocket: WebSocket):
        """Cierra la conexión WebSocket y elimina el estado asociado"""
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            del self.running_graphs[websocket]
            del self.checkpoints[websocket]
            logger.info("Conexión WebSocket cerrada")

    async def handle_research(self, websocket: WebSocket, data: dict):
        """Inicia el proceso de investigación usando el grafo de LangGraph con checkpointing."""
        try:
            assignment_id = data.get("assignmentId", "")
            title = data.get("title", "")
            description = data.get("description", "")
            user_requirements = data.get("userRequirements", "")

            if not title:
                raise ValueError("El campo 'title' es requerido")

            # Generar un identificador único para el checkpoint.
            checkpoint_id = f"checkpoint_{assignment_id}"

            # Definir la configuración que se pasará al grafo
            config = {
                "configurable": {"user_id": assignment_id, "thread_id": assignment_id}
            }

            # Construir el estado inicial, incluyendo la configuración.
            state = {
                "assignment_id": assignment_id,
                "topic": f"Research task: {title}\nContext: {description}\nInitial User Requirements:{user_requirements}",
                "sections": [],
                "final_report": "",
                "completed_sections": [],
                "report_sections_from_research": "",
                # "websocket": websocket,
                "checkpoint_id": checkpoint_id,
                "configurable": config["configurable"],
            }

            logger.info(f"Iniciando investigación para: {title}")

            # Enviar mensaje de inicio.
            await websocket.send_json(
                {
                    "type": "research_start",
                    "message": "Starting research process",
                    "data": {"title": title, "status": "started"},
                }
            )

            # Configurar el grafo y compilarlo con el checkpointer.
            chain = get_report_graph(websocket=websocket)

            # Almacenar el estado del grafo en ejecución y el checkpoint.
            self.running_graphs[websocket] = chain
            self.active_connections[websocket] = state
            self.checkpoints[websocket] = checkpoint_id

            # Ejecutar el grafo en modo streaming pasando la configuración.
            async for chunk in chain.astream(state, config=config):
                await self.handle_stream(chunk, websocket)

        except Exception as e:
            logger.error(f"Error en investigación: {str(e)}", exc_info=True)
            await websocket.send_json({"type": "error", "data": {"error": str(e)}})

    async def handle_human_review(self, websocket: WebSocket, data: dict):
        """Maneja la respuesta del usuario y reanuda el flujo en el nodo de human_review."""
        try:
            user_feedback = data.get("user_feedback", "").strip()

            if (
                websocket not in self.running_graphs
                or self.running_graphs[websocket] is None
            ):
                raise ValueError("No hay un flujo en ejecución para esta sesión")

            chain = self.running_graphs[websocket]

            assignment_id = data.get("assignmentId", "")
            # Configuración que se pasa para la reanudación.
            config = {
                "configurable": {"user_id": assignment_id, "thread_id": assignment_id}
            }

            # Reanudar el flujo desde el checkpoint, pasando tanto el feedback como la configuración.
            async for chunk in chain.astream(
                Command(
                    resume={
                        "user_feedback": user_feedback,
                        "checkpoint_id": assignment_id,
                    }
                ),
                config=config,
            ):
                await self.handle_stream(websocket, chunk)

        except Exception as e:
            logger.error(f"Error en human review: {str(e)}", exc_info=True)
            await websocket.send_json({"type": "error", "data": {"error": str(e)}})

    async def handle_message(self, websocket: WebSocket, data: dict):
        """Router de mensajes WebSocket: redirige según el tipo de mensaje recibido."""
        try:
            message_type = data.get("type")

            if message_type == "start_research":
                await self.handle_research(websocket, data)
            elif message_type == "user_response":
                await self.handle_human_review(websocket, data)
            else:
                logger.warning(f"Tipo de mensaje no soportado: {message_type}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {
                            "error": f"Tipo de mensaje no soportado: {message_type}"
                        },
                    }
                )

        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}", exc_info=True)
            await websocket.send_json({"type": "error", "data": {"error": str(e)}})

    # Configurar el streaming
    async def handle_stream(self, message, websocket: WebSocket):
        if isinstance(message, dict) and "type" in message:
            await websocket.send_json(message)
