import logging
from typing import Optional, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ProgressNotifier:
    """Servicio para manejar notificaciones de progreso"""
    
    def __init__(self, websocket: Optional[WebSocket] = None, verbose: bool = False):
        self.websocket = websocket
        self.verbose = verbose

    async def send_progress(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Envía una actualización de progreso a través de WebSocket y/o logs
        
        Args:
            message: Mensaje principal de progreso
            data: Datos adicionales opcionales
        """
        try:
            if self.websocket:
                await self._send_websocket_message(message, data)
            
            if self.verbose:
                self._log_progress(message, data)
                
        except Exception as e:
            logger.error(f"Error sending progress: {str(e)}")

    async def _send_websocket_message(self, message: str, data: Optional[Dict] = None) -> None:
        """Envía mensaje a través de WebSocket"""
        try:
            payload = {
                "type": "research_progress",
                "message": message,
                "data": data or {}
            }
            await self.websocket.send_json(payload)
            
        except Exception as e:
            logger.error(f"WebSocket send error: {str(e)}")

    def _log_progress(self, message: str, data: Optional[Dict] = None) -> None:
        """Registra el progreso en los logs"""
        log_message = f"Progress: {message}"
        if data:
            log_message += f" | Data: {data}"
        logger.info(log_message) 