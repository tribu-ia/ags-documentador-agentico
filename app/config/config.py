from pydantic import BaseSettings

from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()


class Settings(BaseSettings):
    tavily_api_key: str
    openai_api_key: str
    report_structure: str = "The report should include:\n1. Introduction\n2. Body\n3. Conclusion"
    number_of_queries: int = 3
    tavily_topic: str = "general"
    tavily_days: int = 7
    log_level: str = "info"


settings = Settings()
