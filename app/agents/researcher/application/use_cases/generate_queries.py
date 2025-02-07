import logging
from typing import List
from app.agents.researcher.domain.interfaces.language_model import LanguageModel
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics

logger = logging.getLogger(__name__)

class GenerateQueriesUseCase:
    def __init__(self, language_model: LanguageModel):
        self.language_model = language_model

    @track_metrics
    async def generate(self, section_name: str, section_description: str, max_queries: int = 3) -> List[str]:
        """Generate initial queries using Gemini with retry logic."""
        try:
            prompt = f"""
            Generate {max_queries} specific and diverse search queries for researching:
            Topic: {section_name}
            Context: {section_description}

            Requirements:
            - Each query should focus on a different aspect
            - Make queries specific and actionable
            - Avoid generic or overly broad queries
            - Include both factual and analytical queries

            Return only the numbered list of queries, one per line.
            Maximum number of queries: {max_queries}
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
                
            queries = response.split('\n')
            return [q.strip() for q in queries if q.strip()][:max_queries]

        except Exception as e:
            logger.error(f"Error generating queries: {str(e)}")
            return [] 