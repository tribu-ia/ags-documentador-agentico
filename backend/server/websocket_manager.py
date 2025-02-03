import asyncio
import logging
from typing import Dict, List, Any
from fastapi import WebSocket
from datetime import datetime

from app.agents.researcher import ResearchManager
from app.agents.writer import ReportWriter
from app.utils.state import Section, ReportState

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
        """Maneja el proceso de investigación y escritura"""
        try:
            # Inicializar componentes con websocket
            researcher = ResearchManager(verbose=True, websocket=websocket)
            writer = ReportWriter(websocket=websocket)

            # Crear sección
            section = Section(
                id=data.get("section_id", str(datetime.now().timestamp())),
                name=data.get("title", ""),
                description=data.get("description", "")
            )

            # Realizar investigación
            researched_section = await researcher.research_section(section)

            # Escribir reporte
            async for content in writer.write_report({
                "sections": [researched_section]
            }):
                await websocket.send_json({
                    "type": "content_update",
                    "data": content
                })

            # Notificar finalización
            await websocket.send_json({
                "type": "complete",
                "data": {
                    "message": "Proceso completado",
                    "section_id": section.id
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
