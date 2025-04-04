from functools import lru_cache
from typing import Optional, Any
from pydantic_settings import BaseSettings
from dataclasses import dataclass, field, fields
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
import os
from pydantic import Field

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
    google_api_key: str
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    # Azure OpenAI Settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_base: Optional[str] = None
    azure_openai_api_version: Optional[str] = "2024-02-15"
    azure_openai_deployment_name: Optional[str] = None
    # LLM Configuration
    default_llm_type: str = "gpt-4o-mini"
    GPT_4O_MINI: str = "gpt-4o-mini"
    default_temperature: float = 0
    # Monitoring Configuration
    langchain_project: str
    langsmith_tracing: bool = True
    langsmith_api_key: str
    langsmith_endpoint: str
    langsmith_project: str
    # Report configuration
    report_structure: str = """The report structure should focus on:
1. Introduction:
    - Brief description of the agent: What is it, and what is it for?
    - Links to official documentation or the product's website.
    - Context on why this agent was chosen.

2. Research/Testing Objectives:
    - What was expected to be learned or validated with the agent?
    - Specific scope and goals.

3. Key Features:
    - Main functionalities.
    - Problems it solves.
    - Integrations with other tools or APIs.

4. Prerequisites:
    - Languages, libraries, accounts, or subscriptions required.
    - Recommended technical knowledge.

5. Installation/Initial Setup:
    - Step-by-step instructions (clear commands).
    - Environment variables, API keys, account access, etc.

6. Practical Examples/Use Cases:
    - Simple reproducible case with clear instructions.
    - Code snippets, screenshots, or diagrams (if applicable).

7. Advantages and Limitations:
    - Strengths (e.g., ease, performance, scalability).
    - Weaknesses (e.g., complexity, technical limitations, costs).

8. Lessons Learned and Best Practices:
    - Tips for using the tool more effectively.
    - Challenges encountered and how they were overcome.

9. Next Steps/Future Development:
    - Extension ideas, new use cases, or possible improvements.

10. References and Resources:
    - Official documentation.
    - Links to external tutorials, forums, and communities.
    
"""

    number_of_queries: int = 3
    tavily_topic: str = "general"
    tavily_days: Optional[int] = 7
    jina_api_key: str = Field(..., env='JINA_API_KEY')
    serp_api_key: str = Field(..., env='SERP_API_KEY')  # Para el servicio de fallback
    store_mardown_endpoint: str = Field(..., env='STORE_MARDOWN_ENDPOINT')
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
