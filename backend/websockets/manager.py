from typing import List, Dict, Any
from fastapi import WebSocket
import logging
import asyncio
from datetime import datetime

from app.graph.report_graph import report_graph
from app.utils.state import ReportState

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.research_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Nueva conexión WebSocket establecida")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            # Cancelar tareas pendientes
            for task_id, task in self.research_tasks.items():
                if not task.done():
                    task.cancel()
            logger.info("Conexión WebSocket cerrada")

    async def stream_research_progress(self, websocket: WebSocket, state: ReportState):
        """Stream del progreso de investigación y escritura"""
        try:
            build = report_graph.compile()
            
            async for update in build.astream(state):
                await websocket.send_json({
                    "type": "progress",
                    "timestamp": datetime.now().isoformat(),
                    "data": update
                })

        except Exception as e:
            logger.error(f"Error en streaming: {str(e)}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)}
            })
            raise

    async def start_research(self, websocket: WebSocket, data: Dict[str, Any]):
        """Iniciar proceso de investigación"""
        try:
            # Crear estado inicial
            state = ReportState(
                topic=data["topic"],
                section_id=data.get("section_id"),
                description=data.get("description")
            )

            # Crear y registrar tarea
            task = asyncio.create_task(
                self.stream_research_progress(websocket, state)
            )
            self.research_tasks[state.section_id] = task

            # Esperar resultado
            await task

        except Exception as e:
            logger.error(f"Error iniciando investigación: {str(e)}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)}
            }) 