import asyncio
import logging
from .application.use_cases import ResearchUseCase
from .infrastructure.repositories import SQLiteResearchRepository
from .infrastructure.services import GeminiService, TavilyService, WebSocketProgressNotifier
from .domain.entities import Section
from app.config.config import get_settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    settings = get_settings()
    
    # Initialize services
    repository = SQLiteResearchRepository()
    gemini_service = GeminiService(settings.google_api_key)
    tavily_service = TavilyService(settings.tavily_api_key)
    notifier = WebSocketProgressNotifier(None)  # No WebSocket in this example

    # Initialize use case
    research_use_case = ResearchUseCase(
        repository=repository,
        gemini_service=gemini_service,
        tavily_service=tavily_service,
        notifier=notifier,
        settings=settings,
        verbose=True
    )

    # Create test section
    section = Section(id="test", name="Test Section", description="Test")
    
    try:
        result = await research_use_case.research_section(section)
        print(f"Research completed successfully: {result.content[:100]}...")
    except Exception as e:
        logger.error("Research failed", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 