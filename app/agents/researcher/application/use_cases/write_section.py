import logging
from typing import Dict, Optional
from app.agents.researcher.domain.interfaces.language_model import LanguageModel
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics
from app.utils.state import Section

logger = logging.getLogger(__name__)

class WriteSectionUseCase:
    def __init__(self, language_model: LanguageModel):
        self.language_model = language_model
        self.default_config = {
            'temperature': 0.1,
            'top_p': 0.8,
            'top_k': 40
        }

    @track_metrics
    async def write(self, section: Section, source_str: str) -> Optional[str]:
        """Write a section based on research results."""
        try:
            # Primer intento con contenido completo
            content = await self._try_full_content(section, source_str)
            if content:
                return content

            # Si falla, intentar con contenido reducido
            logger.info("Attempting with reduced content")
            return await self._try_reduced_content(section, source_str)

        except Exception as e:
            logger.error(f"Error writing section: {str(e)}")
            raise

    async def _try_full_content(self, section: Section, source_str: str) -> Optional[str]:
        """Intenta escribir la sección con todo el contenido."""
        try:
            prompt = self._create_full_prompt(section, source_str)
            config = self._get_generation_config(max_tokens=8192)
            
            content = await self.language_model.generate_content(prompt, config)
            if not content:
                raise ValueError("Empty response from language model")
            
            return content

        except Exception as e:
            logger.error(f"Error in full content attempt: {str(e)}")
            return None

    async def _try_reduced_content(self, section: Section, source_str: str) -> str:
        """Intenta escribir una versión reducida de la sección."""
        prompt = self._create_reduced_prompt(section, source_str)
        config = self._get_generation_config(max_tokens=2048)
        
        return await self.language_model.generate_content(prompt, config)

    def _create_full_prompt(self, section: Section, source_str: str) -> str:
        """Crea el prompt para la versión completa."""
        return f"""
        Write a detailed section about: {section.name}
        Topic description: {section.description}
        
        Use this research as context:
        {source_str}
        
        Requirements:
        - Be comprehensive but concise
        - Focus on factual information
        - Include specific examples where relevant
        - Maintain a professional tone
        
        Maximum length: 2000 words.
        Write the section content now.
        """

    def _create_reduced_prompt(self, section: Section, source_str: str) -> str:
        """Crea el prompt para la versión reducida."""
        return f"""
        Write a brief section about: {section.name}
        Topic description: {section.description}
        Key points from sources: {source_str[:5000]}...
        
        Write a concise summary (max 500 words).
        """

    def _get_generation_config(self, max_tokens: int) -> Dict:
        """Obtiene la configuración para la generación de contenido."""
        return {
            **self.default_config,
            'max_output_tokens': max_tokens
        } 