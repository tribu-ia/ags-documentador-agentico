import logging
from typing import List
from app.agents.researcher.domain.interfaces.language_model import LanguageModel
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics

logger = logging.getLogger(__name__)

class PromptGenerationService:
    def __init__(self, language_model: LanguageModel):
        self.language_model = language_model

    @track_metrics
    async def generate(self, section_name: str, section_description: str, max_prompts: int = 3) -> List[str]:
        """Generate search prompts using Gemini with retry logic."""
        try:
            prompt = f"""
            Generate {max_prompts} specific and diverse search prompts for exploring:
            Topic: {section_name}
            Context: {section_description}

            Requirements:
            - Each prompt should focus on a different aspect
            - Make prompts specific and actionable
            - Avoid generic or overly broad statements
            - Include both factual and analytical approaches

            Return only the numbered list of prompts, one per line.
            Maximum number of prompts: {max_prompts}
            """
            
            response = await self.language_model.generate_content(
                prompt,
                config={
                    'temperature': 0.1,
                    'max_output_tokens': 8192,
                    'top_p': 0.8,
                    'top_k': 40
                }
            )
            
            if not response:
                logger.warning("Empty response from language model")
                return []
                
            prompts = response.split('\n')
            return [p.strip() for p in prompts if p.strip()][:max_prompts]

        except Exception as e:
            logger.error(f"Error generating prompts: {str(e)}")
            return [] 