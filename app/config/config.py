from functools import lru_cache
from typing import Optional, Any
from pydantic_settings import BaseSettings
from dataclasses import dataclass, field, fields
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
import os

# Cargar las variables del archivo .env
load_dotenv()


@dataclass(kw_only=True)
class LangGraphConfig:
    """Configuración específica para LangGraph"""
    number_of_queries: int = 2
    tavily_topic: str = "general"
    tavily_days: str = None

    @classmethod
    def from_runnable_config(
            cls, config: Optional[RunnableConfig] = None
    ) -> "LangGraphConfig":
        """Crear configuración desde RunnableConfig de LangGraph"""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})


class Settings(BaseSettings):
    tavily_api_key: str
    openai_api_key: str
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    # Azure OpenAI Settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_base: Optional[str] = None
    azure_openai_api_version: Optional[str] = "2024-02-15"
    azure_openai_deployment_name: Optional[str] = None
    # LLM Configuration
    default_llm_type: str = "gpt-4o-mini"
    default_temperature: float = 0
    # Monitoring Configuration
    langchain_project: str
    langsmith_tracing: bool = True
    langsmith_api_key: str
    langsmith_endpoint: str
    langsmith_project: str
    # Report configuration
    report_structure: str = """The report structure should focus on:

1. Introduction (no research needed)
   - Brief overview of the topic area

2. Main Body Sections:
   - Each section should focus on a key aspect
   - Include technical details and examples
   - Cite relevant sources

3. Conclusion
   - Synthesis of findings
   - Key takeaways
   - Future implications"""

    number_of_queries: int = 3
    tavily_topic: str = "general"
    tavily_days: Optional[int] = 7

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
