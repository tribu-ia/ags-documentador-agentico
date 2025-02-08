import google.generativeai as genai
from typing import Dict, Optional
import logging
from app.agents.researcher.domain.interfaces.language_model import LanguageModel

logger = logging.getLogger(__name__) 


class GeminiService(LanguageModel):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.grounding_config = {
            "google_search_retrieval": {
                "dynamic_retrieval_config": {
                    "mode": "unspecified",
                    "dynamic_threshold": 0.06
                }
            }
        }

    async def generate_content(self, prompt: str, config: Optional[Dict] = None) -> str:
        """Método original para mantener compatibilidad"""
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=config
            )
            return response.text.strip() if response else ""
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise

    async def generate_grounded_content(
            self,
            prompt: str,
            config: Optional[Dict] = None
    ) -> Dict[str, any]:
        """Genera contenido usando Google Search Grounding"""
        try:
            generation_config = config or {}

            response = await self.model.generate_content_async(
                contents=prompt,
                tools=self.grounding_config,
                generation_config=generation_config
            )

            result = {
                'content': response.text.strip() if response else "",
                'grounding_metadata': None
            }

            # Extraer metadata de grounding si está disponible
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'groundingMetadata'):
                    result['grounding_metadata'] = candidate.groundingMetadata

            return result

        except Exception as e:
            logger.error(f"Error generating grounded content: {str(e)}")
            raise