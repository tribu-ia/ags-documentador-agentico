import logging
from typing import List
from fastapi import WebSocket

from app.graph.director import GraphDirector
from app.utils.state import ReportState
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
            title = data.get("title", "")
            description = data.get("description", "")
            if not title:
                raise ValueError("El campo 'title' es requerido")

            # Construir el topic combinando título y descripción
            topic = f"Research task: {title}\nContext: {description}"

            # Crear estado inicial completo
            state = {
                "topic": topic,
                "sections": [],
                "final_report": "",
                "completed_sections": [],
                "report_sections_from_research": "",  # Inicializar vacío
                "websocket": websocket
            }

            logger.info(f"Iniciando investigación para: {title}")
            
            # Obtener el grafo con websocket configurado
            graph = get_report_graph(websocket=websocket)
            
            # Ejecutar el grafo
            chain = graph.compile()
            result = await chain.ainvoke(state)

            # Notificar finalización
            await websocket.send_json({
                "type": "complete",
                "data": {
                    "report": result
                }
            })

        except Exception as e:
            logger.error(f"Error en investigación: {str(e)}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)}
            })

    async def handle_message(self, websocket: WebSocket, data: dict):
        """Router de mensajes WebSocket"""
        try:
            message_type = data.get("type")
            
            if message_type == "start_research":
                await self.handle_research(websocket, data)
            else:
                logger.warning(f"Tipo de mensaje no soportado: {message_type}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": f"Tipo de mensaje no soportado: {message_type}"}
                })

        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)}
            })
