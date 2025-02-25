import logging
from typing import List

from fastapi import WebSocket

from app.graph.report_graph import get_report_graph

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Gestiona las conexiones WebSocket y el proceso de investigación"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Nueva conexión WebSocket establecida")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Conexión WebSocket cerrada")

    async def handle_research(self, websocket: WebSocket, data: dict):
        """Maneja el proceso de investigación usando el grafo de LangGraph"""
        try:
            assignment_id = data.get("assignmentId", "")
            title = data.get("title", "")
            assignmentId = data.get("assignmentId", "")
            description = data.get("description", "")
            if not title:
                raise ValueError("El campo 'title' es requerido")

            # Construir el topic combinando título y descripción
            topic = f"Tarea de Investigación: {title}\nContexto: {description}"

            # Crear estado inicial completo
            state = {
                "assignment_id": assignment_id,
                "topic": topic,
                "sections": [],
                "final_report": "",
                "completed_sections": [],
                "report_sections_from_research": "",  # Inicializar vacío
                "websocket": websocket,
            }

            logger.info(f"Iniciando investigación para: {title}")

            # Enviar mensaje de inicio
            await websocket.send_json(
                {
                    "type": "research_start",
                    "message": "Iniciando proceso de Investigación.",
                    "data": {"title": title, "status": "started"},
                }
            )

            # Configurar el streaming
            async def handle_stream(message):
                if isinstance(message, dict) and "type" in message:
                    await websocket.send_json(message)

            # Ejecutar el grafo con streaming
            graph = get_report_graph(websocket=websocket)
            chain = graph.compile()
            async for chunk in chain.astream(state):  # Usar astream en lugar de ainvoke
                await handle_stream(chunk)

            # Mensaje final
            await websocket.send_json(
                {
                    "type": "research_complete",
                    "message": "Investigación finalizada satisfactoriamente.",
                    "data": {"title": title, "status": "completed"},
                }
            )

        except Exception as e:
            logger.error(f"Error en investigación: {str(e)}", exc_info=True)
            await websocket.send_json({"type": "error", "data": {"error": str(e)}})

    async def handle_message(self, websocket: WebSocket, data: dict):
        """Router de mensajes WebSocket"""
        try:
            message_type = data.get("type")

            if message_type == "start_research":
                await self.handle_research(websocket, data)
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
