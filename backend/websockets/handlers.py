from typing import Dict, Any
from fastapi import WebSocket
import logging

from .manager import WebSocketManager

logger = logging.getLogger(__name__)

async def handle_start_research(websocket: WebSocket, data: Dict[str, Any], manager: WebSocketManager):
    """Manejador para iniciar investigación"""
    await manager.start_research(websocket, data)

async def handle_message(websocket: WebSocket, data: Dict[str, Any], manager: WebSocketManager):
    """Router principal de mensajes"""
    message_type = data.get("type")
    
    handlers = {
        "start_research": handle_start_research,
        # Agregar más handlers según necesidad
    }

    handler = handlers.get(message_type)
    if handler:
        await handler(websocket, data, manager)
    else:
        logger.warning(f"Tipo de mensaje no soportado: {message_type}")
        await websocket.send_json({
            "type": "error",
            "data": {"error": f"Unsupported message type: {message_type}"}
        }) 