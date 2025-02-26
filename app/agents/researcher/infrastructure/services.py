from typing import List, Dict
import google.generativeai as genai
from starlette.websockets import WebSocket

from ..domain.interfaces import WebSocketNotifier

class WebSocketProgressNotifier(WebSocketNotifier):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send_progress(self, message: str, data: Dict = None):
        if self.websocket:
            await self.websocket.send_json({
                "type": "research_progress",
                "message": message,
                "data": data
            })

class GeminiService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def generate_content(self, prompt: str) -> str:
        response = await self.model.generate_content_async(
            prompt,
            generation_config={
                'temperature': 0.1,
                'max_output_tokens': 8192,
                'top_p': 0.8,
                'top_k': 40
            }
        )
        return response.text.strip() if response else ""

class TavilyService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, queries: List[str], topic: str, days: int) -> List[Dict]:
        # Implement Tavily search logic here
        pass

    def format_sources(self, search_docs: List[Dict]) -> str:
        # Implement source formatting logic here
        pass 