from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import logging

from app.utils.state import ReportState
from backend.server.websocket_manager import WebSocketManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI
app = FastAPI(title="Research API")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear instancia del WebSocket Manager
websocket_manager = WebSocketManager()

@app.on_event("startup")
async def startup_event():
    logger.info("Aplicación iniciada")

@app.get("/")
async def root():
    return {"message": "Research API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para investigación en tiempo real"""
    logger.info("Nueva conexión WebSocket intentando conectar")
    await websocket_manager.connect(websocket)
    try:
        logger.info("WebSocket conectado exitosamente")
        while True:
            data = await websocket.receive_json()
            logger.info(f"Mensaje recibido: {data}")
            await websocket_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("WebSocket desconectado normalmente")
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error en WebSocket: {str(e)}", exc_info=True)
        if websocket in websocket_manager.active_connections:
            await websocket_manager.disconnect(websocket)

# NO ejecutes uvicorn aquí directamente
