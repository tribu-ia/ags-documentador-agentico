import google.generativeai as genai
from typing import Dict
from app.agents.researcher.domain.interfaces.language_model import LanguageModel

class GeminiService(LanguageModel):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def generate_content(self, prompt: str, config: Dict) -> str:
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=config
            )
            return response.text.strip() if response else ""
        except Exception as e:
            raise Exception(f"Gemini API call failed: {str(e)}") 