from dataclasses import dataclass
from typing import Dict

from app.utils.state import SectionState, SearchQuery
from app.agents.researcher.infrastructure.services.prompt_generation_service import PromptGenerationService
from app.agents.researcher.application.use_cases.validate_query import ValidateQueryUseCase
from app.agents.researcher.infrastructure.services.progress_notifier import ProgressNotifier

@dataclass
class GenerateQueriesUseCase:
    prompt_generator: PromptGenerationService
    query_validator: ValidateQueryUseCase
    progress_notifier: ProgressNotifier
    number_of_queries: int

    async def execute(self, state: SectionState) -> Dict:
        """Generate and validate search queries using multiple engines."""
        try:
            section = state["section"]
            await self.progress_notifier.send_progress(f"Generating queries for section: {section.name}")
            
            initial_queries = await self.prompt_generator.generate(
                section.name, 
                section.description,
                self.number_of_queries
            )
            
            if not initial_queries:
                await self.progress_notifier.send_progress("No initial queries generated")
                return {"search_queries": []}
            
            validated_queries = []
            for query in initial_queries:
                try:
                    validation = await self.query_validator.validate(query)
                    if validation.overall_score >= 0.6:
                        validated_queries.append(SearchQuery(
                            search_query=query
                        ))
                        
                except Exception as e:
                    await self.progress_notifier.send_progress(
                        "Query validation error", 
                        {"error": str(e)}
                    )
                    continue
            
            await self.progress_notifier.send_progress(
                "Queries generated", 
                {"count": len(validated_queries)}
            )
            
            return {"search_queries": validated_queries}

        except Exception as e:
            await self.progress_notifier.send_progress(
                "Error generating queries", 
                {"error": str(e)}
            )
            raise 