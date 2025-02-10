import logging
import time
import asyncio
from dataclasses import dataclass
from typing import List

from app.utils.state import SectionState
from app.agents.researcher.domain.interfaces.language_model import LanguageModel
from app.agents.researcher.application.decorators.metrics_decorator import track_metrics

logger = logging.getLogger(__name__)

@dataclass
class GenerateInitialQueriesUseCase:
    language_model: LanguageModel

    @track_metrics
    async def _call_language_model(self, prompt: str) -> str:
        """Helper method to make language model API calls with retry logic."""
        try:
            logger.debug(f"Making language model API call with prompt length: {len(prompt)}")
            start_time = time.time()
            
            if len(prompt) > 30000:
                prompt = prompt[:30000] + "..."
                logger.debug("Prompt truncated due to length")
            
            response = await self.language_model.generate_content(
                prompt,
                config={
                    'temperature': 0.1,
                    'max_output_tokens': 8192,
                    'top_p': 0.8,
                    'top_k': 40
                }
            )
            
            duration = time.time() - start_time
            logger.debug(f"Language model API call completed in {duration:.2f} seconds")
            
            return response.strip() if response else ""
            
        except Exception as e:
            logger.error(f"Language model API call failed: {str(e)}")
            if "ResourceExhausted" in str(e):
                logger.error("Resource exhausted error - waiting longer before retry")
                await asyncio.sleep(10)
            raise

    async def execute(self, state: SectionState, number_of_queries: int) -> List[str]:
        """Generate initial queries using language model."""
        try:
            prompt = f"""
            Generate {number_of_queries} specific and diverse search queries for researching:
            Topic: {state["section"].name}
            Context: {state["section"].description}

            Requirements:
            - Each query should focus on a different aspect
            - Make queries specific and actionable
            - Avoid generic or overly broad queries
            - Include both factual and analytical queries

            Return only the numbered list of queries, one per line.
            Maximum number of queries: {number_of_queries}
            """
            
            response = await self._call_language_model(prompt)
            
            if not response:
                logger.warning("Empty response from language model after retries")
                return []
                
            queries = response.split('\n')
            queries = [q.strip() for q in queries if q.strip()][:number_of_queries]
            
            return queries

        except Exception as e:
            logger.error(f"Error in generate_initial_queries after retries: {str(e)}")
            return [] 