from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict
import json
from datetime import datetime

from app.agents.writer import ReportWriter
from app.agents.researcher import ResearchManager
from app.utils.state import Section
from backend.server.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringe esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear instancia del WebSocketManager
websocket_manager = WebSocketManager()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await websocket_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Endpoint para pruebas de investigación vía HTTP
@app.post("/api/research/test")
async def test_research():
    return {
        "message": "Para usar la investigación en tiempo real, conecta vía WebSocket a /ws",
        "example_payload": {
            "type": "start_research",
            "section_id": "test-section-1",
            "title": "Inteligencia Artificial",
            "description": "Historia y evolución de la Inteligencia Artificial"
        }
    }